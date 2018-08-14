from __future__ import division

import collections
import copy

# internal imports

from six.moves import range  # pylint: disable=redefined-builtin
import tensorflow as tf

from magenta.music import constants
from magenta.music import events_lib
from mods.music import sequences_lib
from magenta.pipelines import statistics
from mods.protobuf import music_pb2

DEFAULT_STEPS_PER_QUARTER = constants.DEFAULT_STEPS_PER_QUARTER
MAX_MIDI_PITCH = constants.MAX_MIDI_PITCH
MIN_MIDI_PITCH = constants.MIN_MIDI_PITCH
STANDARD_PPQ = constants.STANDARD_PPQ


class PolyphonicEvent(object):

    # Beginning of the sequence.
    START = 0
    # End of the sequence.
    END = 1
    # End of a step within the sequence.
    STEP_END = 2
    # Start of a new note.
    NEW_NOTE = 3
    # Continuation of a note.
    CONTINUED_NOTE = 4

    def __init__(self, event_type, pitch):
        if not (PolyphonicEvent.START <= event_type <=
                PolyphonicEvent.CONTINUED_NOTE):
            raise ValueError('Invalid event type: %s' % event_type)
        if not (pitch is None or MIN_MIDI_PITCH <= pitch <= MAX_MIDI_PITCH):
            raise ValueError('Invalid pitch: %s' % pitch)

        self.event_type = event_type
        self.pitch = pitch

    def __repr__(self):
        return 'PolyphonicEvent(%r, %r)' % (self.event_type, self.pitch)

    def __eq__(self, other):
        if not isinstance(other, PolyphonicEvent):
            return False
        return (self.event_type == other.event_type and
                self.pitch == other.pitch)


class PolyphonicSequence(events_lib.EventSequence):

    def __init__(self, quantized_sequence=None, steps_per_quarter=None,
                 start_step=0, mod_writer=None):

        assert (quantized_sequence, steps_per_quarter).count(None) == 1

        if quantized_sequence:
            sequences_lib.assert_is_relative_quantized_sequence(
                quantized_sequence)
            self._events = self._from_quantized_sequence(quantized_sequence,
                                                         start_step,
                                                         mod_writer)
            self._steps_per_quarter = (
                quantized_sequence.quantization_info.steps_per_quarter)
        else:
            self._events = [
                PolyphonicEvent(event_type=PolyphonicEvent.START, pitch=None)]
            self._steps_per_quarter = steps_per_quarter

        self._start_step = start_step

    @property
    def start_step(self):
        return self._start_step

    @property
    def steps_per_quarter(self):
        return self._steps_per_quarter

    def trim_trailing_end_events(self):
        while self._events[-1].event_type == PolyphonicEvent.END:
            del self._events[-1]

    def _append_silence_steps(self, num_steps):
        for _ in range(num_steps):
            self._events.append(
                PolyphonicEvent(event_type=PolyphonicEvent.STEP_END, pitch=None))

    def _trim_steps(self, num_steps):
        steps_trimmed = 0
        for i in reversed(range(len(self._events))):
            if self._events[i].event_type == PolyphonicEvent.STEP_END:
                if steps_trimmed == num_steps:
                    del self._events[i + 1:]
                    break
                steps_trimmed += 1
            elif i == 0:
                self._events = [
                    PolyphonicEvent(event_type=PolyphonicEvent.START, pitch=None)]
                break

    def set_length(self, steps, from_left=False):

        if from_left:
            raise NotImplementedError('from_left is not supported')

        # First remove any trailing end events.
        self.trim_trailing_end_events()
        # Then add an end step event, to close out any incomplete steps.
        self._events.append(
            PolyphonicEvent(event_type=PolyphonicEvent.STEP_END, pitch=None))
        # Then trim or pad as needed.
        if self.num_steps < steps:
            self._append_silence_steps(steps - self.num_steps)
        elif self.num_steps > steps:
            self._trim_steps(self.num_steps - steps)
        # Then add a trailing end event.
        self._events.append(
            PolyphonicEvent(event_type=PolyphonicEvent.END, pitch=None))
        assert self.num_steps == steps

    def append(self, event):

        if not isinstance(event, PolyphonicEvent):
            raise ValueError('Invalid polyphonic event: %s' % event)
        self._events.append(event)

    def __len__(self):

        return len(self._events)

    def __getitem__(self, i):
        return self._events[i]

    def __iter__(self):
        return iter(self._events)

    def __str__(self):
        strs = []
        for event in self:
            if event.event_type == PolyphonicEvent.START:
                strs.append('START')
            elif event.event_type == PolyphonicEvent.END:
                strs.append('END')
            elif event.event_type == PolyphonicEvent.STEP_END:
                strs.append('|||')
            elif event.event_type == PolyphonicEvent.NEW_NOTE:
                strs.append('(%s, NEW)' % event.pitch)
            elif event.event_type == PolyphonicEvent.CONTINUED_NOTE:
                strs.append('(%s, CONTINUED)' % event.pitch)
            else:
                raise ValueError('Unknown event type: %s' % event.event_type)
        return '\n'.join(strs)

    @property
    def end_step(self):
        return self.start_step + self.num_steps

    @property
    def num_steps(self):

        steps = 0
        for event in self:
            if event.event_type == PolyphonicEvent.STEP_END:
                steps += 1
        return steps

    @staticmethod
    def _from_quantized_sequence(quantized_sequence, start_step=0, mod_writer=None):

        mw = mod_writer

        pitch_start_steps = collections.defaultdict(list)
        pitch_end_steps = collections.defaultdict(list)

        for note in quantized_sequence.notes:
            if note.quantized_start_step < start_step:
                continue
            pitch_start_steps[note.quantized_start_step].append(note.pitch)
            pitch_end_steps[note.quantized_end_step].append(note.pitch)

        events = [PolyphonicEvent(
            event_type=PolyphonicEvent.START, pitch=None)]

        # Use a list rather than a set because one pitch may be active multiple
        # times.
        active_pitches = []
        for step in range(start_step,
                          quantized_sequence.total_quantized_steps):
            step_events = []

            for pitch in pitch_end_steps[step]:
                active_pitches.remove(pitch)

            for pitch in active_pitches:
                step_events.append(
                    PolyphonicEvent(event_type=PolyphonicEvent.CONTINUED_NOTE,
                                    pitch=pitch))

            for pitch in pitch_start_steps[step]:
                active_pitches.append(pitch)
                step_events.append(PolyphonicEvent(event_type=PolyphonicEvent.NEW_NOTE,
                                                   pitch=pitch))

            events.extend(
                sorted(step_events, key=lambda e: e.pitch, reverse=True))
            events.append(
                PolyphonicEvent(event_type=PolyphonicEvent.STEP_END, pitch=None))
            # print(events)
        events.append(PolyphonicEvent(
            event_type=PolyphonicEvent.END, pitch=None))

        mw.write(mw.model_dir, 'fq_polyphonic_events', events)
        return events

    def to_sequence(self,
                    velocity=100,
                    instrument=0,
                    program=0,
                    qpm=constants.DEFAULT_QUARTERS_PER_MINUTE,
                    base_note_sequence=None):

        seconds_per_step = 60.0 / qpm / self._steps_per_quarter

        sequence_start_time = self.start_step * seconds_per_step

        if base_note_sequence:
            sequence = copy.deepcopy(base_note_sequence)
            if sequence.tempos[0].qpm != qpm:
                raise ValueError(
                    'Supplied QPM (%d) does not match QPM of base_note_sequence (%d)'
                    % (qpm, sequence.tempos[0].qpm))
        else:
            sequence = music_pb2.NoteSequence()
            sequence.tempos.add().qpm = qpm
            sequence.ticks_per_quarter = STANDARD_PPQ

        step = 0
        # Use lists rather than sets because one pitch may be active multiple times.
        pitch_start_steps = []
        pitches_to_end = []
        for i, event in enumerate(self):
            if event.event_type == PolyphonicEvent.START:
                if i != 0:
                    tf.logging.debug(
                        'Ignoring START marker not at beginning of sequence at position '
                        '%d' % i)
            elif event.event_type == PolyphonicEvent.END and i < len(self) - 1:
                tf.logging.debug(
                    'Ignoring END maker before end of sequence at position %d' % i)
            elif event.event_type == PolyphonicEvent.NEW_NOTE:
                pitch_start_steps.append((event.pitch, step))
            elif event.event_type == PolyphonicEvent.CONTINUED_NOTE:
                try:
                    pitches_to_end.remove(event.pitch)
                except ValueError:
                    tf.logging.debug(
                        'Attempted to continue pitch %s at step %s, but pitch was not '
                        'active. Ignoring.' % (event.pitch, step))
            elif (event.event_type == PolyphonicEvent.STEP_END or
                  event.event_type == PolyphonicEvent.END):
                # Find active pitches that should end. Create notes for them, based on
                # when they started.
                # Make a copy of pitch_start_steps so we can remove things from it while
                # iterating.
                for pitch_start_step in list(pitch_start_steps):
                    if pitch_start_step[0] in pitches_to_end:
                        pitches_to_end.remove(pitch_start_step[0])
                        pitch_start_steps.remove(pitch_start_step)

                        note = sequence.notes.add()
                        note.start_time = (pitch_start_step[1] * seconds_per_step +
                                           sequence_start_time)
                        note.end_time = step * seconds_per_step + sequence_start_time
                        note.pitch = pitch_start_step[0]
                        note.velocity = velocity
                        note.instrument = instrument
                        note.program = program

                assert not pitches_to_end

                # Increment the step counter.
                step += 1

                # All active pitches are eligible for ending unless continued.
                pitches_to_end = [ps[0] for ps in pitch_start_steps]
            else:
                raise ValueError('Unknown event type: %s' % event.event_type)

        if pitch_start_steps:
            raise ValueError(
                'Sequence ended, but not all pitches were ended. This likely means '
                'the sequence was missing a STEP_END event before the end of the '
                'sequence. To ensure a well-formed sequence, call set_length first.')

        sequence.total_time = seconds_per_step * \
            (step - 1) + sequence_start_time
        if sequence.notes:
            assert sequence.total_time >= sequence.notes[-1].end_time

        return sequence


def extract_polyphonic_sequences(
        quantized_sequence, start_step=0, min_steps_discard=None,
        max_steps_discard=None, mod_writer=None):

    mw = mod_writer

    sequences_lib.assert_is_relative_quantized_sequence(quantized_sequence)

    stats = dict([(stat_name, statistics.Counter(stat_name)) for stat_name in
                  ['polyphonic_tracks_discarded_too_short',
                   'polyphonic_tracks_discarded_too_long',
                   'polyphonic_tracks_discarded_more_than_1_program']])

    steps_per_bar = sequences_lib.steps_per_bar_in_quantized_sequence(
        quantized_sequence)

    # Create a histogram measuring lengths (in bars not steps).
    stats['polyphonic_track_lengths_in_bars'] = statistics.Histogram(
        'polyphonic_track_lengths_in_bars',
        [0, 1, 10, 20, 30, 40, 50, 100, 200, 500, 1000])

    # Allow only 1 program.
    programs = set()
    for note in quantized_sequence.notes:
        programs.add(note.program)
    if len(programs) > 1:
        stats['polyphonic_tracks_discarded_more_than_1_program'].increment()
        return [], stats.values()

    filename = 'quantized_sequence'
    mw.write(mw.model_dir, filename, quantized_sequence)
    poly_seq = PolyphonicSequence(quantized_sequence,
                                  start_step=start_step,
                                  mod_writer=mw)
    quantized_poly_ns = poly_seq.to_sequence()
    quantized_poly_ns.filename = quantized_sequence.filename
    mw.write(mw.model_dir, 'quantized_poly_ns', quantized_poly_ns)
    
    poly_seqs = []
    num_steps = poly_seq.num_steps

    if min_steps_discard is not None and num_steps < min_steps_discard:
        stats['polyphonic_tracks_discarded_too_short'].increment()
    elif max_steps_discard is not None and num_steps > max_steps_discard:
        stats['polyphonic_tracks_discarded_too_long'].increment()
    else:
        poly_seqs.append(poly_seq)
        stats['polyphonic_track_lengths_in_bars'].increment(
            num_steps // steps_per_bar)
    # pdb.set_trace()
    return poly_seqs, stats.values()
