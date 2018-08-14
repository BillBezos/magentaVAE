import os

# internal imports

import tensorflow as tf

from mods.models.polyphony_rnn import polyphony_lib
from mods.models.polyphony_rnn import polyphony_model
from mods.music import sequences_lib, chord_symbols_lib
from mods.music import encoder_decoder
from mods.music import midi_io
from mods.pipelines import dag_pipeline
from mods.pipelines import pipeline
from mods.pipelines import note_sequence_pipelines
from mods.pipelines import pipelines_common
from magenta.pipelines import statistics
from magenta.pipelines.pipeline import _guarantee_dict
from mods.protobuf import music_pb2


class PolyphonicSequenceExtractor(pipeline.Pipeline):
    """Extracts polyphonic tracks from a quantized NoteSequence."""

    def __init__(self, min_steps, max_steps, name=None):
        super(PolyphonicSequenceExtractor, self).__init__(
            input_type=music_pb2.NoteSequence,
            output_type=polyphony_lib.PolyphonicSequence,
            name=name)
        self._min_steps = min_steps
        self._max_steps = max_steps

    def transform(self, quantized_sequence):
        poly_seqs, stats = polyphony_lib.extract_polyphonic_sequences(
            quantized_sequence,
            min_steps_discard=self._min_steps,
            max_steps_discard=self._max_steps,
            mod_writer=self.mw)
        self._set_stats(stats)
        return poly_seqs


def get_pipeline(config, min_steps, max_steps, eval_ratio):
    #transposition_range = range(-4, 5)
    transposition_range = [0]

    partitioner = pipelines_common.RandomPartition(
        music_pb2.NoteSequence,
        ['eval_poly_tracks', 'training_poly_tracks'],
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
        poly_extractor = PolyphonicSequenceExtractor(
            min_steps=min_steps, max_steps=max_steps, name='PolyExtractor_' + mode)
        encoder_pipeline = encoder_decoder.EncoderPipeline(
            polyphony_lib.PolyphonicSequence, config.encoder_decoder,
            name='EncoderPipeline_' + mode)

        dag[time_change_splitter] = partitioner[mode + '_poly_tracks']
        dag[quantizer] = time_change_splitter
        dag[transposition_pipeline] = quantizer
        dag[poly_extractor] = transposition_pipeline
        dag[encoder_pipeline] = poly_extractor
        dag[dag_pipeline.DagOutput(mode + '_poly_tracks')] = encoder_pipeline

    return dag_pipeline.DAGPipeline(dag, config.mod_writer)


def run_pipeline_serial(pipeline_instance, input_iterator,
                        output_dir, output_file_base=None):
    
    pipeline.run_pipeline_serial(pipeline_instance,
                                 input_iterator,
                                 output_dir,
                                 output_file_base=None)

def save_quantized_midi(sequence_path, model, model_dir):
    return midi_io.quantized_sequence_to_midi(sequence_path, model, model_dir)



