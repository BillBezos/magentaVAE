import tensorflow as tf
import magenta, google, abc, pretty_midi, pprint, IPython
from pathlib import Path
import pickle

import sys, os, six, collections, copy, pdb, itertools, re
sys.path.insert(0, os.path.abspath('..'))
import numpy as np
from six.moves import range

from mods.convert_dir_to_note_sequences import convert_directory
from mods.mod_writer import ModWriter, DIRS_DICT

from mods.music import encoder_decoder
from mods.music import sequences_lib
from mods.music import chord_symbols_lib
from mods.music import midi_io

from mods.models.polyphony_rnn import (
    polyphony_model as poly_model,
    polyphony_rnn_create_dataset as poly_create,
)

from mods.models.pianoroll_rnn_nade import (
    pianoroll_rnn_nade_model as nade_model,
    pianoroll_rnn_nade_create_dataset as nade_create,
)

from mods.models.performance_rnn import (
    performance_model as perf_model,
    performance_rnn_create_dataset as perf_create,
    performance_rnn_train as perf_train, 
)

from mods.pipelines import pipeline

poly_get_pipeline = poly_create.get_pipeline
poly_run_pipeline = poly_create.run_pipeline_serial
poly_save_qmidi = poly_create.save_quantized_midi

nade_get_pipeline = nade_create.get_pipeline
nade_run_pipeline = nade_create.run_pipeline_serial
nade_save_qmidi = nade_create.save_quantized_midi

perf_get_pipeline = perf_create.get_pipeline
perf_run_pipeline = perf_create.run_pipeline_serial
perf_save_qmidi = perf_create.save_quantized_midi
perf_train_main = perf_train.main_wrapper

MODEL_FUNCTIONS = {
    'POLY': {'g': poly_get_pipeline, 'r': poly_run_pipeline, 'm': poly_save_qmidi},
    'NADE': {'g': nade_get_pipeline, 'r': nade_run_pipeline, 'm': nade_save_qmidi},
    'PERF': {'g': perf_get_pipeline, 'r': perf_run_pipeline, 'm': perf_save_qmidi,
             't': perf_train_main}
}

from mods.music.performance_encoder_decoder import NoteDensityOneHotEncoding


def get_args_pack(function, config=None, instance=None):
    mw = config.mod_writer
    dirs = mw.dirs_dct

    kwargs = {}
    if function == 'get':
        kwargs.update({'config': config})
        if mw.model == 'PERF':
            kwargs.update({'min_events': 80})
            kwargs.update({'max_events': 5512})
        else:
            kwargs.update({'min_steps': 80})
            kwargs.update({'max_steps': 5512})
        kwargs.update({'eval_ratio': 0.0})
        return kwargs
    
    if function == 'run':
        iterator = pipeline.tf_record_iterator(
                    dirs['TFRC_FULL'], instance.input_type)
        kwargs.update({'pipeline_instance': instance})
        kwargs.update({'input_iterator': iterator})
        kwargs.update({'output_dir': dirs['SEQS_DIR']})
        kwargs.update({'output_file_base': None})
        return kwargs
    
    if function == 'mid':
        mw_hist = mw.history
        qs = re.compile('.*quantized_.*_ns.txt')
        path = [p for p in mw_hist if qs.match(p)][0]
        model = mw.model
        model_dir = mw.dirs_dct[mw.model_dir]
        model_dir = os.path.join(model_dir, mw.config)

        kwargs.update({'sequence_path': path})
        kwargs.update({'model': model})
        kwargs.update({'model_dir': model_dir})
        return kwargs

    if function == 'trn':
        model_dir = mw.dirs_dct[mw.model_dir]
        model_dir = os.path.join(model_dir, mw.config)
        run_dir = os.path.join(model_dir, 'logdir/run1')

        seqs_dir = mw.dirs_dct['SEQS_DIR']
        seqs = f'training_{config.details.id}_performances.tfrecord'
        seqs_path = os.path.join(seqs_dir, seqs)
        kwargs.update({'config': mw.config})
        kwargs.update({'run_dir': run_dir})
        kwargs.update({'sequences': seqs_path})
        def define_flags(main_wrapper, flags):
            FLAGS = perf_train.FLAGS
            FLAGS.mark_as_parsed()
            FLAGS.config = flags['config']
            FLAGS.run_dir = flags['run_dir']
            FLAGS.sequence_example_file = flags['sequences']
            return main_wrapper(FLAGS)

        return kwargs, define_flags

def run_models(convert_midi=False, 
        models=[ (perf_model, ['performance',]), ]):

    configs = []
    for model, confs in models:
        for c in confs:
            new_c = model.default_configs[c]
            mw_model = new_c.mod_writer.model
            new_c.mod_writer = ModWriter(DIRS_DICT)
            new_c.mod_writer.set_model(mw_model)
            new_c.mod_writer.set_config(c)
            configs.append(new_c)

    qmidi_paths = {}
    for c in configs:
        mw = c.mod_writer
        
        get_args = get_args_pack('get', config=c)
        pipeline_instance = MODEL_FUNCTIONS[mw.model]['g'](**get_args)

        run_args = get_args_pack('run', config=c,
                            instance=pipeline_instance)
        MODEL_FUNCTIONS[mw.model]['r'](**run_args)

        mid_args = get_args_pack('mid', config=c)
        qmidi_path = MODEL_FUNCTIONS[mw.model]['m'](**mid_args)

        # trn_args, wrapper = get_args_pack('trn', config=c)
        # wrapper(MODEL_FUNCTIONS[mw.model]['t'], trn_args)

        if mw.model not in qmidi_paths.keys():
            qmidi_paths.update({mw.model: [qmidi_path]})
        else:
            qmidi_paths[mw.model].append(qmidi_path)

    return qmidi_paths

def delete_output(qmidi_paths):
    pattern = re.compile('(.*/nade/.*|.*/perf/.*|.*/poly/.*)/midi')
    model_dirs = []
    for p_list in qmidi_paths.values():
        for p in p_list:
            model_dirs.append(pattern.match(p).group(1))
    for model in model_dirs:
        for p in Path(model).glob('*.txt'):
            p.unlink()

def hack(pretty_stacks):
    s = '06_optional_multiconditioned_performance_with_dynamics'
    tmp_keys = list(pretty_stacks[s].keys())
    for k in tmp_keys:
        tmp_vals = pretty_stacks[s][k].copy()
        pretty_stacks[s][k] = {k_:v for k_,v in tmp_vals.items() if k_ != 'EncoderPipeline2'}
    return pretty_stacks

def prettify_stacks(stacks):
    pretty_stacks = {}
    for k, v in stacks.items():
        pretty_stacks[k] = {}
        for stack in v:
            nk = ''
            if 'events_to_input' in stack:
                nk += 'e2i'
            if 'events_to_label' in stack:
                nk += 'e2l'
            if 'NoteDensityOneHotEncoding' in stack:
                nk += '_nd'
            else:
                nk += '_perf'
            pretty_stacks[k][nk] = {}
            nk2 = ''
            for i, elm in enumerate(stack):
                if i % 3 == 0:
                    if nk2 == elm:
                        if elm[-1].isdigit():
                            nk2 = f'{elm}{int(elm[-1])+1}'
                        else:
                            nk2 = f'{elm}2'
                    else:
                        nk2 = elm
                    pretty_stacks[k][nk][nk2] = []
                else:
                    pretty_stacks[k][nk][nk2].append(elm)
    pretty_stacks = hack(pretty_stacks)
    return pretty_stacks

def inspect_stacks(models):
    stacks = {}
    model = f'{models[0][0].mw.model}_DIR'
    model_dir = DIRS_DICT[model]
    stacks_dir = os.path.join(model_dir, 'stack')
    stack_files = os.listdir(stacks_dir)
    for model, confs in models:
        for c in confs:
            regex = re.compile(f'.*{c}$')
            matching_stacks = [s for s in stack_files if regex.match(s)]
            stack_paths = [os.path.join(stacks_dir, s)
                           for s in matching_stacks]
            stacks[c] = []
            for p in stack_paths:
                with open(p, 'rb') as f:
                    l = pickle.load(f)
                    i = l.index('write_stack')
                    stacks[c].append(l[:i-1])
    pretty_stacks = prettify_stacks(stacks)
    write_stacks(pretty_stacks, stacks_dir)
    return pretty_stacks

def write_stacks(pretty_stacks, stacks_dir):
    ps = pretty_stacks
    keys = list(ps.keys())
    for k in keys:
        if len(ps[k]) == 3:
            e2i_nd, e2i_perf, e2l_nd = ps[k]
            zipped = zip(['e2i_nd', 'e2i_perf', 'e2l_nd'], 
                         [e2i_nd, e2i_perf, e2l_nd])
            for s_name, s in zipped:
                content = ''
                for k_, vs_ in ps[k][s].items():
                    content += str(k_) + '\n'
                    for v_ in vs_:
                        content += str(v_) + '\n'
                with open(os.path.join(stacks_dir, f'{k}_{s_name}'), 'w') as f:
                    f.write(content)
        else:
            e2i_perf, e2l_perf = ps[k]
            zipped = zip(['e2i_perf', 'e2l_perf'], 
                         [e2i_perf, e2l_perf])
            for s_name, s in zipped:
                content = ''
                for k_, vs_ in ps[k][s].items():
                    content += str(k_) + '\n'
                    for v_ in vs_:
                        content += str(v_) + '\n'
                with open(os.path.join(stacks_dir, f'{k}_{s_name}'), 'w') as f:
                    f.write(content)

