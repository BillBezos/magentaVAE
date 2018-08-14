# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Create a dataset of SequenceExamples from NoteSequence protos.

This script will extract polyphonic tracks from NoteSequence protos and save
them to TensorFlow's SequenceExample protos for input to the performance RNN
models. It will apply data augmentation, stretching and transposing each
NoteSequence within a limited range.
"""

import os, pdb, inspect, pickle

# internal imports

import tensorflow as tf
import magenta

from mods.models.performance_rnn import performance_model
from mods.music import performance_lib
from mods.music import performance_encoder_decoder
from mods.music import midi_io
from mods.pipelines import dag_pipeline
from mods.pipelines import note_sequence_pipelines
from mods.pipelines import pipeline
from mods.pipelines import pipelines_common
from mods.protobuf import music_pb2
from mods.pipelines.note_sequence_pipelines import tsrange005


class EncoderPipeline(pipeline.Pipeline):
  """A Pipeline that converts performances to a model specific encoding."""

  def __init__(self, config, name):
    """Constructs an EncoderPipeline.

    Args:
      config: A PerformanceRnnConfig that specifies the encoder/decoder and
          note density conditioning behavior.
      name: A unique pipeline name.
    """
    super(EncoderPipeline, self).__init__(
        input_type=performance_lib.Performance,
        output_type=tf.train.SequenceExample,
        name=name)
    self._encoder_decoder = config.encoder_decoder
    self._density_bin_ranges = config.density_bin_ranges
    self._density_window_size = config.density_window_size
    self._pitch_histogram_window_size = config.pitch_histogram_window_size
    self._optional_conditioning = config.optional_conditioning

  def transform(self, performance):
    if (self._density_bin_ranges is not None or
        self._pitch_histogram_window_size is not None):
      # Encode conditional on note density and/or pitch class histogram.
      with open('performance.p', 'wb') as handle:
        pickle.dump(performance, handle)
      control_sequences = []
      if self._density_bin_ranges is not None:
        control_sequences.append(
            performance_lib.performance_note_density_sequence(
                performance, self._density_window_size))
      self.mw.write(self.mw.model_dir, 'control_sequence0', control_sequences)
      if self._pitch_histogram_window_size is not None:
        control_sequences.append(
            performance_lib.performance_pitch_histogram_sequence(
                performance, self._pitch_histogram_window_size))
      self.mw.write(self.mw.model_dir, 'control_sequence1', control_sequences)
      control_sequence = list(zip(*control_sequences))
      if self._optional_conditioning:
        # Create two copies, one with and one without conditioning.
        self.mw.write(self.mw.model_dir, 'control_sequence', control_sequence)
        encoded = [
          self._encoder_decoder.encode(
              list(zip([disable] * len(control_sequence), control_sequence)),
              performance, self.mw)
          for disable in [False, True]]
      else:
        encoded = [self._encoder_decoder.encode(
            control_sequence, performance, self.mw)]
    else:
      # Encode unconditional.
      encoded = [self._encoder_decoder.encode(performance, self.mw)]

    return encoded


class PerformanceExtractor(pipeline.Pipeline):
  """Extracts polyphonic tracks from a quantized NoteSequence."""

  def __init__(self, min_events, max_events, num_velocity_bins, name=None):
    super(PerformanceExtractor, self).__init__(
        input_type=music_pb2.NoteSequence,
        output_type=performance_lib.Performance,
        name=name)
    self._min_events = min_events
    self._max_events = max_events
    self._num_velocity_bins = num_velocity_bins

  def transform(self, quantized_sequence):
    performances, stats = performance_lib.extract_performances(
        quantized_sequence,
        min_events_discard=self._min_events,
        max_events_truncate=self._max_events,
        num_velocity_bins=self._num_velocity_bins,
        mod_writer=self.mw)
    self._set_stats(stats)
    return performances


def get_pipeline(config, min_events, max_events, eval_ratio):
  """Returns the Pipeline instance which creates the RNN dataset.

  Args:
    config: A PerformanceRnnConfig.
    min_events: Minimum number of events for an extracted sequence.
    max_events: Maximum number of events for an extracted sequence.
    eval_ratio: Fraction of input to set aside for evaluation set.

  Returns:
    A pipeline.Pipeline instance.
  """
  # Stretch by -5%, -2.5%, 0%, 2.5%, and 5%.
  # stretch_factors = [0.95, 0.975, 1.0, 1.025, 1.05]
  stretch_factors = [1.0]
  pdb.set_trace()
  # Transpose no more than a major third.
  transposition_range = [0]

  def _filenames(x):
    args = x.split('_')
    return f'{args[0]}_{config.details.id}_{"_".join(args[1:])}'

  partitioner = pipelines_common.RandomPartition(
      music_pb2.NoteSequence,
      list(map(_filenames, ['eval_performances', 'training_performances'])),
      [eval_ratio],
      mod_writer=config.mod_writer)
  dag = {partitioner: dag_pipeline.DagInput(music_pb2.NoteSequence)}

  for mode in ['eval', 'training']:
    sustain_pipeline = note_sequence_pipelines.SustainPipeline(
        name='SustainPipeline_' + mode)
    stretch_pipeline = note_sequence_pipelines.StretchPipeline(
        stretch_factors if mode == 'training' else [1.0],
        name='StretchPipeline_' + mode)
    splitter = note_sequence_pipelines.Splitter(
        hop_size_seconds=30.0, name='Splitter_' + mode)
    quantizer = note_sequence_pipelines.Quantizer(
        steps_per_second=config.steps_per_second, name='Quantizer_' + mode)
    transposition_pipeline = note_sequence_pipelines.TranspositionPipeline(
        transposition_range if mode == 'training' else [0],
        name='TranspositionPipeline_' + mode)
    perf_extractor = PerformanceExtractor(
        min_events=min_events, max_events=max_events,
        num_velocity_bins=config.num_velocity_bins,
        name='PerformanceExtractor_' + mode)
    encoder_pipeline = EncoderPipeline(config, name='EncoderPipeline_' + mode)

    dag[sustain_pipeline] = partitioner[f'{mode}_{config.details.id}_performances']
    dag[stretch_pipeline] = sustain_pipeline
    dag[splitter] = stretch_pipeline
    dag[quantizer] = splitter
    dag[transposition_pipeline] = quantizer
    dag[perf_extractor] = transposition_pipeline
    dag[encoder_pipeline] = perf_extractor
    dag[dag_pipeline.DagOutput(f'{mode}_{config.details.id}_performances')] = encoder_pipeline

  return dag_pipeline.DAGPipeline(dag, config.mod_writer)


def run_pipeline_serial(pipeline_instance, input_iterator,
                        output_dir, output_file_base=None):

    pipeline.run_pipeline_serial(pipeline_instance,
                                 input_iterator,
                                 output_dir,
                                 output_file_base=None)


def save_quantized_midi(sequence_path, model, model_dir):
    return midi_io.quantized_sequence_to_midi(sequence_path, model, model_dir)

