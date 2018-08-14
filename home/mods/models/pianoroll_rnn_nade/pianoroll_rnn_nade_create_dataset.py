

import os

# internal imports

import tensorflow as tf

from mods.models.pianoroll_rnn_nade import pianoroll_rnn_nade_model
from mods.music import encoder_decoder
from mods.music import pianoroll_lib
from mods.music import pianoroll_encoder_decoder
from mods.music import midi_io
from mods.pipelines import dag_pipeline
from mods.pipelines import note_sequence_pipelines
from mods.pipelines import pipeline
from mods.pipelines import pipelines_common
from mods.protobuf import music_pb2




class PianorollSequenceExtractor(pipeline.Pipeline):
    """Extracts pianoroll tracks from a quantized NoteSequence."""

    def __init__(self, min_steps, max_steps, name=None):
        super(PianorollSequenceExtractor, self).__init__(
            input_type=music_pb2.NoteSequence,
            output_type=pianoroll_lib.PianorollSequence,
            name=name)
        self._min_steps = min_steps
        self._max_steps = max_steps

    def transform(self, quantized_sequence):
        pianoroll_seqs, stats = pianoroll_lib.extract_pianoroll_sequences(
            quantized_sequence,
            min_steps_discard=self._min_steps,
            max_steps_truncate=self._max_steps,
            mod_writer=self.mw)
        self._set_stats(stats)
        return pianoroll_seqs


def get_pipeline(config, min_steps, max_steps, eval_ratio):
    transposition_range = [0]

    partitioner = pipelines_common.RandomPartition(
        music_pb2.NoteSequence,
        ['eval_pianoroll_tracks', 'training_pianoroll_tracks'],
        [eval_ratio],
        mod_writer=config.mod_writer)
    dag = {partitioner: dag_pipeline.DagInput(music_pb2.NoteSequence)}

    for mode in ['eval', 'training']:
        time_change_splitter = note_sequence_pipelines.TimeChangeSplitter(
            name='TimeChangeSplitter_' + mode)
        quantizer = note_sequence_pipelines.Quantizer(
            steps_per_quarter=config.steps_per_quarter, name='Quantizer_' + mode)
        transposition_pipeline = note_sequence_pipelines.TranspositionPipeline(
            transposition_range, name='TranspositionPipeline_' + mode)
        pianoroll_extractor = PianorollSequenceExtractor(
            min_steps=min_steps, max_steps=max_steps,
            name='PianorollExtractor_' + mode)
        encoder_pipeline = encoder_decoder.EncoderPipeline(
            pianoroll_lib.PianorollSequence, config.encoder_decoder,
            name='EncoderPipeline_' + mode)

        dag[time_change_splitter] = partitioner[mode + '_pianoroll_tracks']
        dag[quantizer] = time_change_splitter
        dag[transposition_pipeline] = quantizer
        dag[pianoroll_extractor] = transposition_pipeline
        dag[encoder_pipeline] = pianoroll_extractor
        dag[dag_pipeline.DagOutput(
            mode + '_pianoroll_tracks')] = encoder_pipeline

    return dag_pipeline.DAGPipeline(dag, config.mod_writer)

def run_pipeline_serial(pipeline_instance, input_iterator,
                        output_dir, output_file_base=None):

    pipeline.run_pipeline_serial(pipeline_instance,
                                 input_iterator,
                                 output_dir,
                                 output_file_base=None)

def save_quantized_midi(sequence_path, model, model_dir):
    return midi_io.quantized_sequence_to_midi(sequence_path, model, model_dir)

