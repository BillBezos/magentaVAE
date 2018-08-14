from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc, pdb, os, pickle
import inspect
from inspect import getsource as gs
# internal imports

import numpy as np
from six.moves import range  # pylint: disable=redefined-builtin
import tensorflow as tf

from magenta.common import sequence_example_lib
from magenta.music import constants
from mods.pipelines import pipeline

DEFAULT_STEPS_PER_BAR = constants.DEFAULT_STEPS_PER_BAR
DEFAULT_LOOKBACK_DISTANCES = [DEFAULT_STEPS_PER_BAR, DEFAULT_STEPS_PER_BAR * 2]


class EncoderPipeline(pipeline.Pipeline):

    def __init__(self, input_type, encoder_decoder, name=None):
        super(EncoderPipeline, self).__init__(
            input_type=input_type,
            output_type=tf.train.SequenceExample,
            name=name)
        self._encoder_decoder = encoder_decoder

    def transform(self, seq):
        # ed1
        encoded = self._encoder_decoder.encode(seq, self.mw)
        return [encoded]


class EventSequenceEncoderDecoder(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def input_size(self):
        pass

    @abc.abstractproperty
    def num_classes(self):
        pass

    @abc.abstractproperty
    def default_event_label(self):
        pass

    @abc.abstractmethod
    def events_to_input(self, events, position):
        pass

    @abc.abstractmethod
    def events_to_label(self, events, position):
        pass

    @abc.abstractmethod
    def class_index_to_event(self, class_index, events):
        pass

    def labels_to_num_steps(self, labels):
        return len(labels)

    # ed2
    def encode(self, events, mw):
        inputs = []
        labels = []
        for i in range(len(events) - 1):
            inputs.append(self.events_to_input(events, i, mw))
            labels.append(self.events_to_label(events, i + 1, mw))
        #mw.write(mw.model_dir, 'ed2_events', str(events))
        mw.write(mw.model_dir, 'ed2_inputs', inputs)
        mw.write(mw.model_dir, 'ed2_labels', labels)
        return sequence_example_lib.make_sequence_example(inputs, labels)

    def get_inputs_batch(self, event_sequences, full_length=False):

        inputs_batch = []
        for events in event_sequences:
            inputs = []
            if full_length:
                for i in range(len(events)):
                    inputs.append(self.events_to_input(events, i))
            else:
                inputs.append(self.events_to_input(events, len(events) - 1))
            inputs_batch.append(inputs)
        return inputs_batch

    def extend_event_sequences(self, event_sequences, softmax):

        num_classes = len(softmax[0][0])
        chosen_classes = []
        for i in range(len(event_sequences)):
            chosen_class = np.random.choice(num_classes, p=softmax[i][-1])
            event = self.class_index_to_event(chosen_class, event_sequences[i])
            event_sequences[i].append(event)
            chosen_classes.append(chosen_class)
        return chosen_classes

    def evaluate_log_likelihood(self, event_sequences, softmax):

        all_loglik = []
        for i in range(len(event_sequences)):
            if len(softmax[i]) >= len(event_sequences[i]):
                raise ValueError(
                    'event sequence must be longer than softmax vector (%d events but '
                    'softmax vector has length %d)' % (len(event_sequences[i]),
                                                       len(softmax[i])))
            end_pos = len(event_sequences[i])
            start_pos = end_pos - len(softmax[i])
            loglik = 0.0
            for softmax_pos, position in enumerate(range(start_pos, end_pos)):
                index = self.events_to_label(event_sequences[i], position)
                loglik += np.log(softmax[i][softmax_pos][index])
            all_loglik.append(loglik)
        return all_loglik


class OneHotEventSequenceEncoderDecoder(EventSequenceEncoderDecoder):

    def __init__(self, one_hot_encoding):
        self._one_hot_encoding = one_hot_encoding

    @property
    def input_size(self):
        return self._one_hot_encoding.num_classes

    @property
    def num_classes(self):
        return self._one_hot_encoding.num_classes

    @property
    def default_event_label(self):
        return self._one_hot_encoding.encode_event(
            self._one_hot_encoding.default_event)

    # ed3a
    def events_to_input(self, events, position, mw=None):
        #print(self._one_hot_encoding)
        input_ = [0.0] * self.input_size
        input_[self._one_hot_encoding.encode_event(events[position])] = 1.0
        mw.write(mw.model_dir, 'e2i_target_encoder', input_, (True,''))
        return input_

    # ed3b
    def events_to_label(self, events, position, mw):
        return self._one_hot_encoding.encode_event(events[position])

    def class_index_to_event(self, class_index, events):
        return self._one_hot_encoding.decode_event(class_index)

    def labels_to_num_steps(self, labels):
        events = []
        for label in labels:
            events.append(self.class_index_to_event(label, events))
        return sum(self._one_hot_encoding.event_to_num_steps(event)
                   for event in events)


class OneHotEncoding(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def num_classes(self):
        pass

    @abc.abstractproperty
    def default_event(self):
        pass

    @abc.abstractmethod
    def encode_event(self, event):
        pass

    @abc.abstractmethod
    def decode_event(self, index):
        pass

    def event_to_num_steps(self, unused_event):

        return 1

    counter = 0

    def write_stack(self, prefix):
        stack = inspect.stack()
        new_stack = []
        for s in stack:
            if 'self' in s.frame.f_locals:
                class_ = s.frame.f_locals['self']
                class_name = class_.__class__.__name__
                if class_name == 'DAGPipeline':
                    mw = class_.mw
                    filename = f'{prefix}_{self.counter:02}_{mw.config}'
                    model_dir = mw.model_dir
                    model_path = mw.dirs_dct[model_dir]
                    dirname = os.path.join(model_path, 'stack')
                try:
                    source = gs(getattr(class_, s.function))
                except AttributeError:
                    try:
                        source = gs(inspect.getattr_static(class_, s.function))
                    except:
                        source = ''
                new_stack.append(source)
                new_stack.append(s.function)
                new_stack.append(class_name)
        new_stack.reverse()
        new_stack = new_stack[new_stack.index('DAGPipeline'):]
        if len(self._last_stack) == 0:
            with open(os.path.join(dirname, filename), 'wb') as f:
                pickle.dump(new_stack, f)
            self._last_stack.append(new_stack)
            self.counter += 1
        elif any([new_stack == old for old in self._last_stack]):
            pass
        else:
            with open(os.path.join(dirname, filename), 'wb') as f:
                pickle.dump(new_stack, f)
            self._last_stack.append(new_stack)
            self.counter += 1



class LookbackEventSequenceEncoderDecoder(EventSequenceEncoderDecoder):
    """An EventSequenceEncoderDecoder that encodes repeated events and meter."""

    def __init__(self, one_hot_encoding, lookback_distances=None,
                 binary_counter_bits=5):
        """Initializes the LookbackEventSequenceEncoderDecoder.
        Args:
          one_hot_encoding: A OneHotEncoding object that transforms events to and
             from integer indices.
          lookback_distances: A list of step intervals to look back in history to
             encode both the following event and whether the current step is a
             repeat. If None, use default lookback distances.
          binary_counter_bits: The number of input bits to use as a counter for the
             metric position of the next event.
        """
        self._one_hot_encoding = one_hot_encoding
        self._lookback_distances = (lookback_distances
                                    if lookback_distances is not None
                                    else DEFAULT_LOOKBACK_DISTANCES)
        self._binary_counter_bits = binary_counter_bits

    @property
    def input_size(self):
        one_hot_size = self._one_hot_encoding.num_classes
        num_lookbacks = len(self._lookback_distances)
        return (one_hot_size +                  # current event
                num_lookbacks * one_hot_size +  # next event for each lookback
                self._binary_counter_bits +     # binary counters
                num_lookbacks)                  # whether event matches lookbacks

    @property
    def num_classes(self):
        return self._one_hot_encoding.num_classes + len(self._lookback_distances)

    @property
    def default_event_label(self):
        return self._one_hot_encoding.encode_event(
            self._one_hot_encoding.default_event)

    def events_to_input(self, events, position):
        """Returns the input vector for the given position in the event sequence.
        Returns a self.input_size length list of floats. Assuming a one-hot
        encoding with 38 classes, two lookback distances, and five binary counters,
        self.input_size will = 121. Each index represents a different input signal
        to the model.
        Indices [0, 120]:
        [0, 37]: Event of current step.
        [38, 75]: Event of next step for first lookback.
        [76, 113]: Event of next step for second lookback.
        114: 16th note binary counter.
        115: 8th note binary counter.
        116: 4th note binary counter.
        117: Half note binary counter.
        118: Whole note binary counter.
        119: The current step is repeating (first lookback).
        120: The current step is repeating (second lookback).
        Args:
          events: A list-like sequence of events.
          position: An integer position in the event sequence.
        Returns:
          An input vector, an self.input_size length list of floats.
        """
        input_ = [0.0] * self.input_size
        offset = 0

        # Last event.
        index = self._one_hot_encoding.encode_event(events[position])
        input_[index] = 1.0
        offset += self._one_hot_encoding.num_classes

        # Next event if repeating N positions ago.
        for i, lookback_distance in enumerate(self._lookback_distances):
            lookback_position = position - lookback_distance + 1
            if lookback_position < 0:
                event = self._one_hot_encoding.default_event
            else:
                event = events[lookback_position]
            index = self._one_hot_encoding.encode_event(event)
            input_[offset + index] = 1.0
            offset += self._one_hot_encoding.num_classes

        # Binary time counter giving the metric location of the *next* event.
        n = position + 1
        for i in range(self._binary_counter_bits):
            input_[offset] = 1.0 if (n // 2 ** i) % 2 else -1.0
            offset += 1

        # Last event is repeating N bars ago.
        for i, lookback_distance in enumerate(self._lookback_distances):
            lookback_position = position - lookback_distance
            if (lookback_position >= 0 and
                    events[position] == events[lookback_position]):
                input_[offset] = 1.0
            offset += 1

        assert offset == self.input_size

        return input_

    def events_to_label(self, events, position):
        """Returns the label for the given position in the event sequence.
        Returns an integer in the range [0, self.num_classes). Indices in the range
        [0, self._one_hot_encoding.num_classes) map to standard events. Indices
        self._one_hot_encoding.num_classes and self._one_hot_encoding.num_classes +
        1 are signals to repeat events from earlier in the sequence. More distant
        repeats are selected first and standard events are selected last.
        Assuming a one-hot encoding with 38 classes and two lookback distances,
        self.num_classes = 40 and the values will be as follows.
        Values [0, 39]:
          [0, 37]: Event of the last step in the event sequence, if not repeating
                   any of the lookbacks.
          38: If the last event is repeating the first lookback, if not also
              repeating the second lookback.
          39: If the last event is repeating the second lookback.
        Args:
          events: A list-like sequence of events.
          position: An integer position in the event sequence.
        Returns:
          A label, an integer.
        """
        if (self._lookback_distances and
            position < self._lookback_distances[-1] and
                events[position] == self._one_hot_encoding.default_event):
            return (self._one_hot_encoding.num_classes +
                    len(self._lookback_distances) - 1)

        # If last step repeated N bars ago.
        for i, lookback_distance in reversed(
                list(enumerate(self._lookback_distances))):
            lookback_position = position - lookback_distance
            if (lookback_position >= 0 and
                    events[position] == events[lookback_position]):
                return self._one_hot_encoding.num_classes + i

        # If last step didn't repeat at one of the lookback positions, use the
        # specific event.
        return self._one_hot_encoding.encode_event(events[position])

    def class_index_to_event(self, class_index, events):
        """Returns the event for the given class index.
        This is the reverse process of the self.events_to_label method.
        Args:
          class_index: An int in the range [0, self.num_classes).
          events: The current event sequence.
        Returns:
          An event value.
        """
        # Repeat N bar ago.
        for i, lookback_distance in reversed(
                list(enumerate(self._lookback_distances))):
            if class_index == self._one_hot_encoding.num_classes + i:
                if len(events) < lookback_distance:
                    return self._one_hot_encoding.default_event
                return events[-lookback_distance]

        # Return the event for that class index.
        return self._one_hot_encoding.decode_event(class_index)

    def labels_to_num_steps(self, labels):
        """Returns the total number of time steps for a sequence of class labels.
        This method assumes the event sequence begins with the event corresponding
        to the first label, which is inconsistent with the `encode` method in
        EventSequenceEncoderDecoder that uses the second event as the first label.
        Therefore, if the label sequence includes a lookback to the very first event
        and that event is a different number of time steps than the default event,
        this method will give an incorrect answer.
        Args:
          labels: A list-like sequence of integers in the range
              [0, self.num_classes).
        Returns:
          The total number of time steps for the label sequence, as determined by
          the one-hot encoding.
        """
        events = []
        for label in labels:
            events.append(self.class_index_to_event(label, events))
        return sum(self._one_hot_encoding.event_to_num_steps(event)
                   for event in events)


class ConditionalEventSequenceEncoderDecoder(object):
    """An encoder/decoder for conditional event sequences.
    This class is similar to an EventSequenceEncoderDecoder but operates on
    *conditional* event sequences, where there is both a control event sequence
    and a target event sequence. The target sequence consists of events that are
    directly generated by the model, while the control sequence, known in advance,
    affects the inputs provided to the model. The event types of the two sequences
    can be different.
    Model inputs are determined by both control and target sequences, and are
    formed by concatenating the encoded control and target input vectors. Model
    outputs are determined by the target sequence only.
    This implementation assumes that the control event at position `i` is known
    when the target event at position `i` is to be generated.
    Properties:
      input_size: The length of the list returned by self.events_to_input.
      num_classes: The range of ints that can be returned by
          self.events_to_label.
    """

    def __init__(self, control_encoder_decoder, target_encoder_decoder):
        """Initialize a ConditionalEventSequenceEncoderDecoder object.
        Args:
          control_encoder_decoder: The EventSequenceEncoderDecoder to encode/decode
              the control sequence.
          target_encoder_decoder: The EventSequenceEncoderDecoder to encode/decode
              the target sequence.
        """
        self._control_encoder_decoder = control_encoder_decoder
        self._target_encoder_decoder = target_encoder_decoder

    @property
    def input_size(self):
        """The size of the concatenated control and target input vectors.
        Returns:
            An integer, the size of an input vector.
        """
        return (self._control_encoder_decoder.input_size +
                self._target_encoder_decoder.input_size)

    @property
    def num_classes(self):
        """The range of target labels used by this model.
        Returns:
            An integer, the range of integers that can be returned by
                self.events_to_label.
        """
        return self._target_encoder_decoder.num_classes

    @property
    def default_event_label(self):
        """The class label that represents a default target event.
        Returns:
          An integer, the class label that represents a default target event.
        """
        return self._target_encoder_decoder.default_event_label

    def events_to_input(self, control_events, target_events, position, mw=None):
        """Returns the input vector for the given position in the sequence pair.
        Returns the vector formed by concatenating the input vector for the control
        sequence and the input vector for the target sequence.
        Args:
          control_events: A list-like sequence of control events.
          target_events: A list-like sequence of target events.
          position: An integer event position in the event sequences. When
              predicting the target label at position `i + 1`, the input vector is
              the concatenation of the control input vector at position `i + 1` and
              the target input vector at position `i`.
        Returns:
          An input vector, a list of floats.
        """
        # return (
        #     self._control_encoder_decoder.events_to_input(
        #         control_events, position + 1) +
        #     self._target_encoder_decoder.events_to_input(target_events, position))
        a = self._control_encoder_decoder.events_to_input(control_events, position+1, mw)
        b = self._target_encoder_decoder.events_to_input(target_events, position, mw)
        mw.write(mw.model_dir, 'e2i_control', a, (True, ''))
        mw.write(mw.model_dir, 'e2i_target', b, (True, ''))
        return a+b

    def events_to_label(self, target_events, position, mw=None):
        """Returns the label for the given position in the target event sequence.
        Args:
          target_events: A list-like sequence of target events.
          position: An integer event position in the target event sequence.
        Returns:
          A label, an integer.
        """
        return self._target_encoder_decoder.events_to_label(target_events, position, mw)

    def class_index_to_event(self, class_index, target_events):
        """Returns the event for the given class index.
        This is the reverse process of the self.events_to_label method.
        Args:
          class_index: An integer in the range [0, self.num_classes).
          target_events: A list-like sequence of target events.
        Returns:
          A target event value.
        """
        return self._target_encoder_decoder.class_index_to_event(
            class_index, target_events)

    def labels_to_num_steps(self, labels):
        """Returns the total number of time steps for a sequence of class labels.
        Args:
          labels: A list-like sequence of integers in the range
              [0, self.num_classes).
        Returns:
          The total number of time steps for the label sequence, as determined by
          the target encoder/decoder.
        """
        return self._target_encoder_decoder.labels_to_num_steps(labels)

    def encode(self, control_events, target_events, mod_writer):
        """Returns a SequenceExample for the given event sequence pair.
        Args:
          control_events: A list-like sequence of control events.
          target_events: A list-like sequence of target events, the same length as
              `control_events`.
        Returns:
          A tf.train.SequenceExample containing inputs and labels.
        Raises:
          ValueError: If the control and target event sequences have different
              length.
        """
        mw = mod_writer
        #print(f'control: {control_events}')
        #print(f'target: {target_events}')
        mw.write(mw.model_dir, 'control_events', control_events)
        mw.write(mw.model_dir, 'target_events', str(target_events))
        if len(control_events) != len(target_events):
            raise ValueError('must have the same number of control and target events '
                             '(%d control events but %d target events)' % (
                                 len(control_events), len(target_events)))

        inputs = []
        labels = []
        for i in range(len(target_events) - 1):
            inputs.append(self.events_to_input(
                control_events, target_events, i, mw))
            labels.append(self.events_to_label(target_events, i + 1, mw))

        mw.write(mw.model_dir, 'cond_inputs', inputs)
        mw.write(mw.model_dir, 'cond_labels', labels)
        return sequence_example_lib.make_sequence_example(inputs, labels)

    def get_inputs_batch(self, control_event_sequences, target_event_sequences,
                         full_length=False):
        """Returns an inputs batch for the given control and target event sequences.
        Args:
          control_event_sequences: A list of list-like control event sequences.
          target_event_sequences: A list of list-like target event sequences, the
              same length as `control_event_sequences`. Each target event sequence
              must be shorter than the corresponding control event sequence.
          full_length: If True, the inputs batch will be for the full length of
              each control/target event sequence pair. If False, the inputs batch
              will only be for the last event of each target event sequence. A full-
              length inputs batch is used for the first step of extending the target
              event sequences, since the RNN cell state needs to be initialized with
              the priming target sequence. For subsequent generation steps, only a
              last-event inputs batch is used.
        Returns:
          An inputs batch. If `full_length` is True, the shape will be
          [len(target_event_sequences), len(target_event_sequences[0]), INPUT_SIZE].
          If `full_length` is False, the shape will be
          [len(target_event_sequences), 1, INPUT_SIZE].
        Raises:
          ValueError: If there are a different number of control and target event
              sequences, or if one of the control event sequences is not shorter
              than the corresponding control event sequence.
        """
        if len(control_event_sequences) != len(target_event_sequences):
            raise ValueError(
                '%d control event sequences but %d target event sequences' %
                (len(control_event_sequences, len(target_event_sequences))))

        inputs_batch = []
        for control_events, target_events in zip(
                control_event_sequences, target_event_sequences):
            if len(control_events) <= len(target_events):
                raise ValueError('control event sequence must be longer than target '
                                 'event sequence (%d control events but %d target '
                                 'events)' % (len(control_events), len(target_events)))
            inputs = []
            if full_length:
                for i in range(len(target_events)):
                    inputs.append(self.events_to_input(
                        control_events, target_events, i))
            else:
                inputs.append(self.events_to_input(
                    control_events, target_events, len(target_events) - 1))
            inputs_batch.append(inputs)
        return inputs_batch

    def extend_event_sequences(self, target_event_sequences, softmax):
        """Extends the event sequences by sampling the softmax probabilities.
        Args:
          target_event_sequences: A list of target EventSequence objects.
          softmax: A list of softmax probability vectors. The list of softmaxes
              should be the same length as the list of event sequences.
        Returns:
          A Python list of chosen class indices, one for each target event sequence.
        """
        return self._target_encoder_decoder.extend_event_sequences(
            target_event_sequences, softmax)

    def evaluate_log_likelihood(self, target_event_sequences, softmax):
        """Evaluate the log likelihood of multiple target event sequences.
        Args:
          target_event_sequences: A list of target EventSequence objects.
          softmax: A list of softmax probability vectors. The list of softmaxes
              should be the same length as the list of target event sequences. The
              softmax vectors are assumed to have been generated by a full-length
              inputs batch.
        Returns:
          A Python list containing the log likelihood of each target event sequence.
        """
        return self._target_encoder_decoder.evaluate_log_likelihood(
            target_event_sequences, softmax)


class OptionalEventSequenceEncoder(EventSequenceEncoderDecoder):
    """An encoder that augments a base encoder with a disable flag.
    This encoder encodes event sequences consisting of tuples where the first
    element is a disable flag. When set, the encoding consists of a 1 followed by
    a zero-encoding the size of the base encoder's input. When unset, the encoding
    consists of a 0 followed by the base encoder's encoding.
    """

    def __init__(self, encoder):
        """Initialize an OptionalEventSequenceEncoder object.
        Args:
          encoder: The base EventSequenceEncoderDecoder to use.
        """
        self._encoder = encoder

    @property
    def input_size(self):
        return 1 + self._encoder.input_size

    @property
    def num_classes(self):
        raise NotImplementedError

    #@property
    def default_event_label(self):
        raise NotImplementedError

    def events_to_input(self, events, position, mw=None):
        # The event sequence is a list of tuples where the first element is a
        # disable flag.
        #print(events)
        disable, _ = events[position]
        if disable:
            return [1.0] + [0.0] * self._encoder.input_size
        else:
            a = [0.0] + self._encoder.events_to_input(
                [event for _, event in events], position, mw)
            mw.write(mw.model_dir, 'e2i_opt', a, (True, ''))
            return a
            # return [0.0] + self._encoder.events_to_input(
            #     [event for _, event in events], position)

    def events_to_label(self, events, position):
        raise NotImplementedError

    def class_index_to_event(self, class_index, events):
        raise NotImplementedError


class MultipleEventSequenceEncoder(EventSequenceEncoderDecoder):
    """An encoder that concatenates multiple component encoders.
    This class, largely intended for use with control sequences for conditional
    encoder/decoders, encodes event sequences with multiple encoders and
    concatenates the encodings.
    Despite being an EventSequenceEncoderDecoder this class does not decode.
    """

    def __init__(self, encoders, encode_single_sequence=False):
        """Initialize a MultipleEventSequenceEncoder object.
        Args:
          encoders: A list of component EventSequenceEncoderDecoder objects whose
              output will be concatenated.
          encode_single_sequence: If True, at encoding time all of the encoders will
              be applied to a single event sequence. If False, each event of the
              event sequence should be a tuple with size the same as the number of
              encoders, each of which will be applied to the events in the
              corresponding position in the tuple, i.e. the first encoder will be
              applied to the first element of each event tuple, the second encoder
              will be applied to the second element, etc.
        """
        self._encoders = encoders
        self._encode_single_sequence = encode_single_sequence

    @property
    def input_size(self):
        return sum(encoder.input_size for encoder in self._encoders)

    @property
    def num_classes(self):
        raise NotImplementedError

    @property
    def default_event_label(self):
        raise NotImplementedError

    def events_to_input(self, events, position, mw=None):
        input_ = []
        if self._encode_single_sequence:
            # Apply all encoders to the event sequence.
            for encoder in self._encoders:
                input_ += encoder.events_to_input(events, position)
        else:
            # The event sequence is a list of tuples. Apply each encoder to the
            # elements in the corresponding tuple position.
            event_sequences = list(zip(*events))
            if len(event_sequences) != len(self._encoders):
                raise ValueError(
                    'Event tuple size must be the same as the number of encoders.')
            for encoder, event_sequence in zip(self._encoders, event_sequences):
                a = encoder.events_to_input(event_sequence, position, mw)
                mw.write(mw.model_dir, 'e2i_mult', a, (True, str(encoder)))
                input_ += a

        return input_

    def events_to_label(self, events, position):
        raise NotImplementedError

    def class_index_to_event(self, class_index, events):
        raise NotImplementedError
