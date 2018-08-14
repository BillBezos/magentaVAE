from collections import defaultdict, namedtuple
from itertools import groupby, chain
import sys
# pylint: disable=g-import-not-at-top
if sys.version_info.major <= 2:
    from cStringIO import StringIO
else:
    from io import BytesIO
import tempfile
import google
import os
import re
import pdb
import bisect

# internal imports
import pretty_midi
import tensorflow as tf

from magenta.music import constants
from mods.protobuf import music_pb2
from mods.music.chord_symbols_lib import pitches_to_chord_symbol, ChordSymbolException

# pylint: enable=g-import-not-at-top

# Allow pretty_midi to read MIDI files with absurdly high tick rates.
# Useful for reading the MAPS dataset.
# https://github.com/craffel/pretty-midi/issues/112
pretty_midi.pretty_midi.MAX_TICK = 1e10

# The offset used to change the mode of a key from major to minor when
# generating a PrettyMIDI KeySignature.
_PRETTY_MIDI_MAJOR_TO_MINOR_OFFSET = 12

ARPEGGIO = 5

class MIDIConversionError(Exception):
    pass

# def tsrange005(key):
#   if key == 'c':
#     return 0

#   dsa = {'c':  0,
#          'db': 1,  'c#': 1,
#          'd':  2,
#          'eb': 3,  'd#': 3,
#          'e':  4,
#          'f':  5,
#          'gb': 6,  'f#': 6,
#          'g':  7,
#          'ab': 8,  'g#': 8,
#          'a':  9,
#          'bb': 10, 'a#': 10,
#          'b':  11,}

#   amt = dsa[key] if dsa[key] < abs(dsa[key]-12) else dsa[key]-12
#   return amt

def transpose(pm):
    """Transposes all instruments to new key based on new_key_number.
    Adds a new key signature event if no event is present.
    Parameters
    ----------
    new_key_number: int
    key number accordingly to [0,11] Major, [12,23] minor
    For example, 0 is C Major, 12 is C minorTimes to map from
    """
    # Add default key signature of C major if none is present.
    if not pm.key_signature_changes:
      default_key_signature = pretty_midi.KeySignature(0, 0)
      pm.key_signature_changes.append(default_key_signature)

    for i in range(len(pm.key_signature_changes)):
      key_sig = pm.key_signature_changes[i]
      if key_sig.key_number != 0:
        start_time = key_sig.time
        # Look ahead to next key signature event, if any, to get end time.
        if i < len(pm.key_signature_changes) - 1:
          end_time = pm.key_signature_changes[i + 1].time
        else:
          end_time = float('inf')


        # key_offset = new_key_number - key_sig.key_number
        key_offset = -(key_sig.key_number%12)
        # Move up or down based on which yields a smaller delta.
        if key_offset < -6:
          key_offset += 12
        if key_offset > 6:
          key_offset -= 1
        for instrument in pm.instruments:
          if not instrument.is_drum:
            for note in instrument.notes:
              if note.start >= start_time and note.start < end_time:
                note.pitch += key_offset
        # Update the key signature number.
        key_sig.key_number = 0

def midi_to_sequence_proto(midi_data):
    """Convert MIDI file contents to a tensorflow.magenta.NoteSequence proto.
    Converts a MIDI file encoded as a string into a
    tensorflow.magenta.NoteSequence proto. Decoding errors are very common when
    working with large sets of MIDI files, so be sure to handle
    MIDIConversionError exceptions.
    Args:
      midi_data: A string containing the contents of a MIDI file or populated
          pretty_midi.PrettyMIDI object.
    Returns:
      A tensorflow.magenta.NoteSequence proto.
    Raises:
      MIDIConversionError: An improper MIDI mode was supplied.
    """

    # In practice many MIDI files cannot be decoded with pretty_midi. Catch all
    # errors here and try to log a meaningful message. So many different
    # exceptions are raised in pretty_midi.PrettyMidi that it is cumbersome to
    # catch them all only for the purpose of error logging.
    # pylint: disable=bare-except
    if isinstance(midi_data, pretty_midi.PrettyMIDI):
        midi = midi_data
    else:
        try:
            midi = pretty_midi.PrettyMIDI(BytesIO(midi_data))
        except:
            raise MIDIConversionError('Midi decoding error %s: %s' %
                                      (sys.exc_info()[0], sys.exc_info()[1]))
    # pylint: enable=bare-except
    # transpose(midi)
    #midi.instruments[0].notes = midi.instruments[0].notes[:17]

    sequence = music_pb2.NoteSequence()

    # Populate header.
    sequence.ticks_per_quarter = midi.resolution
    sequence.source_info.parser = music_pb2.NoteSequence.SourceInfo.PRETTY_MIDI
    sequence.source_info.encoding_type = (
        music_pb2.NoteSequence.SourceInfo.MIDI)

    # Populate time signatures.
    for midi_time in midi.time_signature_changes:
        time_signature = sequence.time_signatures.add()
        time_signature.time = midi_time.time
        time_signature.numerator = midi_time.numerator
        try:
            # Denominator can be too large for int32.
            time_signature.denominator = midi_time.denominator
        except ValueError:
            raise MIDIConversionError('Invalid time signature denominator %d' %
                                      midi_time.denominator)

    # Populate key signatures.
    for midi_key in midi.key_signature_changes:
        key_signature = sequence.key_signatures.add()
        key_signature.time = midi_key.time
        # key_signature.key = midi_key.key_number % 12
        key_signature.key = 0
        midi_mode = midi_key.key_number // 12
        if midi_mode == 0:
            key_signature.mode = key_signature.MAJOR
        elif midi_mode == 1:
            key_signature.mode = key_signature.MINOR
        else:
            raise MIDIConversionError('Invalid midi_mode %i' % midi_mode)

    # Populate tempo changes.
    tempo_times, tempo_qpms = midi.get_tempo_changes()
    for time_in_seconds, tempo_in_qpm in zip(tempo_times, tempo_qpms):
        tempo = sequence.tempos.add()
        tempo.time = time_in_seconds
        tempo.qpm = tempo_in_qpm

    # Populate notes by gathering them all from the midi's instruments.
    # Also set the sequence.total_time as the max end time in the notes.
    midi_notes = []
    midi_pitch_bends = []
    midi_control_changes = []
    for num_instrument, midi_instrument in enumerate(midi.instruments):
        for midi_note in midi_instrument.notes:
            if not sequence.total_time or midi_note.end > sequence.total_time:
                sequence.total_time = midi_note.end
            midi_notes.append((midi_instrument.program, num_instrument,
                               midi_instrument.is_drum, midi_note))
        for midi_pitch_bend in midi_instrument.pitch_bends:
            midi_pitch_bends.append(
                (midi_instrument.program, num_instrument,
                 midi_instrument.is_drum, midi_pitch_bend))
        for midi_control_change in midi_instrument.control_changes:
            midi_control_changes.append(
                (midi_instrument.program, num_instrument,
                 midi_instrument.is_drum, midi_control_change))


    def add_notes(midi_notes, min_steps):
        groups = []
        uniquekeys = []
        data = sorted(midi_notes, key=lambda x: x[3].start)
        for k,g in groupby(data, key=lambda x: x[3].start):
            groups.append(list(g))
            uniquekeys.append(k)

        orns = sequence.Ornament.OrnType.items()

        def find_ornament(diffs, idx=0, progress=0):        
            # recursive
            if not diffs:        
                return (idx+progress, orns[progress-1]) 
            if diffs[0] > min_steps:        
                return (idx+progress, orns[progress])
            else:        
                progress += 1
                return find_ornament(diffs[1:], idx, progress)

        def add_orn(idx, orn_type):
            _idx = idx+1    
            steps_to_prev = orns.index(orn_type)+1
            _groups = groups[_idx-steps_to_prev:_idx]
            orn_start_grp = _groups[0]
            orn_next_grp = _groups[1]
            orn_end_grp = _groups[-1]
            orn_notes = []

            if len(orn_start_grp) != 1:
                if len(orn_next_grp) != 1:
                    raise '1st and 2nd are both chords?'
                else:
                    data = [elm[3].pitch for elm in orn_start_grp]
                    location = bisect.bisect_left(data, orn_next_grp[0][3].pitch)
                    result = orn_start_grp[location-1]
                    orn_notes.append([result])
            else:
                orn_notes.append(orn_start_grp)

            for i,g in enumerate(_groups[1:]):
                if len(g) != 1:
                    data = [elm[3].pitch for elm in g]
                    location = bisect.bisect_left(data, _groups[i][0][3].pitch)
                    result = g[location]
                    orn_notes.append([result])
                else:
                    orn_notes.append(g)

            orn_notes = list(chain.from_iterable(orn_notes))

            rolled_chord = None
            if len(_groups) >= 3:
                try:
                    rolled_chord = pitches_to_chord_symbol(sorted([o[3].pitch for o in orn_notes]))
                    print(rolled_chord)
                    rolled_start = min(orn_notes, key=lambda o: o[3].start)[3].start
                    rolled_end   = max(orn_notes, key=lambda o: o[3].end)[3].end
                    for onoe in orn_notes:
                        onoe[3].start = rolled_start
                        onoe[3].end   = rolled_end
                except ChordSymbolException:
                    pass

            program, instrument, is_drum, midi_note = orn_notes[0]
            orn = sequence.ornaments.add()
            orn.orn_type = orns[5][1] if rolled_chord else orns[len(orn_notes)-1][1]
            orn.program = program
            orn.instrument = instrument
            orn.is_drum = is_drum 
            orn.start_time = midi_note.start
            orn.end_time = orn_notes[-1][3].end # should be minus 1 quantization steps from end note start
            orn.start_pitch = midi_note.pitch
            orn.end_pitch = orn_notes[-1][3].pitch
            orn.velocity = midi_note.velocity
            #orn.notes.extend([o[3] for o in orn_notes])

            return orn, orn_notes, rolled_chord

        def add_note(note_group):
            for note in note_group:
                program, instrument, is_drum, midi_note = note
                note = sequence.notes.add()
                note.instrument = instrument
                note.program = program
                note.start_time = midi_note.start
                note.end_time = midi_note.end
                note.pitch = midi_note.pitch
                note.velocity = midi_note.velocity
                note.is_drum = is_drum

            return sequence.notes[-len(note_group):]

        idx = 0
        while idx < len(groups)-1:    
            start = groups[idx:idx+5]
            diffs = [(s2[0][3].start - s1[0][3].start) for s1,s2 in zip(start,start[1:])]
            idx, ornament = find_ornament(diffs, idx)        
            if not ornament[1]:        
                add_note(groups[idx])
                idx += 1
            else:        
                o, ons, rc = add_orn(idx, ornament)
                if o.orn_type == ARPEGGIO:
                    add_note(ons)
                else:
                    add_note(groups[idx])
                idx += 1

    add_notes(midi_notes, 0.1)
    # for program, instrument, is_drum, midi_note in midi_notes:
    #     note = sequence.notes.add()
    #     note.instrument = instrument
    #     note.program = program
    #     note.start_time = midi_note.start
    #     note.end_time = midi_note.end
    #     note.pitch = midi_note.pitch
    #     note.velocity = midi_note.velocity
    #     note.is_drum = is_drum

    for program, instrument, is_drum, midi_pitch_bend in midi_pitch_bends:
        pitch_bend = sequence.pitch_bends.add()
        pitch_bend.instrument = instrument
        pitch_bend.program = program
        pitch_bend.time = midi_pitch_bend.time
        pitch_bend.bend = midi_pitch_bend.pitch
        pitch_bend.is_drum = is_drum

    for program, instrument, is_drum, midi_control_change in midi_control_changes:
        control_change = sequence.control_changes.add()
        control_change.instrument = instrument
        control_change.program = program
        control_change.time = midi_control_change.time
        control_change.control_number = midi_control_change.number
        control_change.control_value = midi_control_change.value
        control_change.is_drum = is_drum

    # TODO(douglaseck): Estimate note type (e.g. quarter note) and populate
    # note.numerator and note.denominator.

    return sequence


def sequence_proto_to_pretty_midi(
        sequence, drop_events_n_seconds_after_last_note=None):
    """Convert tensorflow.magenta.NoteSequence proto to a PrettyMIDI.
    Time is stored in the NoteSequence in absolute values (seconds) as opposed to
    relative values (MIDI ticks). When the NoteSequence is translated back to
    PrettyMIDI the absolute time is retained. The tempo map is also recreated.
    Args:
      sequence: A tensorfow.magenta.NoteSequence proto.
      drop_events_n_seconds_after_last_note: Events (e.g., time signature changes)
          that occur this many seconds after the last note will be dropped. If
          None, then no events will be dropped.
    Returns:
      A pretty_midi.PrettyMIDI object or None if sequence could not be decoded.
    """

    ticks_per_quarter = (sequence.ticks_per_quarter if sequence.ticks_per_quarter
                         else constants.STANDARD_PPQ)

    max_event_time = None
    if drop_events_n_seconds_after_last_note is not None:
        max_event_time = (max([n.end_time for n in sequence.notes] or [0]) +
                          drop_events_n_seconds_after_last_note)

    # Try to find a tempo at time zero. The list is not guaranteed to be in order.
    initial_seq_tempo = None
    for seq_tempo in sequence.tempos:
        if seq_tempo.time == 0:
            initial_seq_tempo = seq_tempo
            break

    kwargs = {}
    kwargs['initial_tempo'] = (initial_seq_tempo.qpm if initial_seq_tempo
                               else constants.DEFAULT_QUARTERS_PER_MINUTE)
    pm = pretty_midi.PrettyMIDI(resolution=ticks_per_quarter, **kwargs)

    # Create an empty instrument to contain time and key signatures.
    instrument = pretty_midi.Instrument(0)
    pm.instruments.append(instrument)

    # Populate time signatures.
    for seq_ts in sequence.time_signatures:
        if max_event_time and seq_ts.time > max_event_time:
            continue
        time_signature = pretty_midi.containers.TimeSignature(
            seq_ts.numerator, seq_ts.denominator, seq_ts.time)
        pm.time_signature_changes.append(time_signature)

    # Populate key signatures.
    for seq_key in sequence.key_signatures:
        if max_event_time and seq_key.time > max_event_time:
            continue
        key_number = seq_key.key
        if seq_key.mode == seq_key.MINOR:
            key_number += _PRETTY_MIDI_MAJOR_TO_MINOR_OFFSET
        key_signature = pretty_midi.containers.KeySignature(
            key_number, seq_key.time)
        pm.key_signature_changes.append(key_signature)

    # Populate tempos.
    # TODO(douglaseck): Update this code if pretty_midi adds the ability to
    # write tempo.
    for seq_tempo in sequence.tempos:
        # Skip if this tempo was added in the PrettyMIDI constructor.
        if seq_tempo == initial_seq_tempo:
            continue
        if max_event_time and seq_tempo.time > max_event_time:
            continue
        tick_scale = 60.0 / (pm.resolution * seq_tempo.qpm)
        tick = pm.time_to_tick(seq_tempo.time)
        # pylint: disable=protected-access
        pm._tick_scales.append((tick, tick_scale))
        pm._update_tick_to_time(0)
        # pylint: enable=protected-access

    # Populate instrument events by first gathering notes and other event types
    # in lists then write them sorted to the PrettyMidi object.
    instrument_events = defaultdict(lambda: defaultdict(list))
    for seq_note in sequence.notes:
        instrument_events[(seq_note.instrument, seq_note.program,
                           seq_note.is_drum)]['notes'].append(
                               pretty_midi.Note(
                                   seq_note.velocity, seq_note.pitch,
                                   seq_note.start_time, seq_note.end_time))
    for seq_bend in sequence.pitch_bends:
        if max_event_time and seq_bend.time > max_event_time:
            continue
        instrument_events[(seq_bend.instrument, seq_bend.program,
                           seq_bend.is_drum)]['bends'].append(
                               pretty_midi.PitchBend(seq_bend.bend, seq_bend.time))
    for seq_cc in sequence.control_changes:
        if max_event_time and seq_cc.time > max_event_time:
            continue
        instrument_events[(seq_cc.instrument, seq_cc.program,
                           seq_cc.is_drum)]['controls'].append(
                               pretty_midi.ControlChange(
                                   seq_cc.control_number,
                                   seq_cc.control_value, seq_cc.time))

    for (instr_id, prog_id, is_drum) in sorted(instrument_events.keys()):
        # For instr_id 0 append to the instrument created above.
        if instr_id > 0:
            instrument = pretty_midi.Instrument(prog_id, is_drum)
            pm.instruments.append(instrument)
        instrument.program = prog_id
        instrument.notes = instrument_events[
            (instr_id, prog_id, is_drum)]['notes']
        instrument.pitch_bends = instrument_events[
            (instr_id, prog_id, is_drum)]['bends']
        instrument.control_changes = instrument_events[
            (instr_id, prog_id, is_drum)]['controls']

    return pm


def midi_file_to_sequence_proto(midi_file):
    """Converts MIDI file to a tensorflow.magenta.NoteSequence proto.
    Args:
      midi_file: A string path to a MIDI file.
    Returns:
      A tensorflow.magenta.Sequence proto.
    Raises:
      MIDIConversionError: Invalid midi_file.
    """
    with tf.gfile.Open(midi_file, 'r') as f:
        midi_as_string = f.read()
        return midi_to_sequence_proto(midi_as_string)


def sequence_proto_to_midi_file(sequence, output_file,
                                drop_events_n_seconds_after_last_note=None):
    """Convert tensorflow.magenta.NoteSequence proto to a MIDI file on disk.
    Time is stored in the NoteSequence in absolute values (seconds) as opposed to
    relative values (MIDI ticks). When the NoteSequence is translated back to
    MIDI the absolute time is retained. The tempo map is also recreated.
    Args:
      sequence: A tensorfow.magenta.NoteSequence proto.
      output_file: String path to MIDI file that will be written.
      drop_events_n_seconds_after_last_note: Events (e.g., time signature changes)
          that occur this many seconds after the last note will be dropped. If
          None, then no events will be dropped.
    """
    pretty_midi_object = sequence_proto_to_pretty_midi(
        sequence, drop_events_n_seconds_after_last_note)
    with tempfile.NamedTemporaryFile() as temp_file:
        pretty_midi_object.write(temp_file.name)
        tf.gfile.Copy(temp_file.name, output_file, overwrite=True)


def quantized_sequence_to_midi(sequence_path, model, model_dir):
    solver = music_pb2.NoteSequence()
    with open(sequence_path, 'r') as f:
        ns = google.protobuf.text_format.Merge(str(f.read()), solver)
    dirname = os.path.join(model_dir, 'midi')
    if not tf.gfile.Exists(dirname):
        tf.gfile.MakeDirs(dirname)
    original_midi_name = str(ns.filename)
    original_midi_name = re.search('(.*?).mid', original_midi_name).group(1)
    quantized_midi_name = f'{original_midi_name}_{model}_quantized.mid'
    output_file = os.path.join(dirname, quantized_midi_name)
    sequence_proto_to_midi_file(ns, output_file)
    return output_file

def play_midi(midi_file, sample_rate=44100, sf2_path=None):
    pm = pretty_midi.PrettyMIDI(midi_file)
    return pm.fluidsynth(fs=sample_rate, sf2_path=None)

