"""
Process exercise: load YAML, resolve key sequence, expand to segments.
No audio/MIDI/WAV output.
"""
from .keys import key_sequence_to_names, waypoints_to_key_sequence
from .raw_exercise import RawExercise
from .scale import scale_degrees_to_midi, scale_degrees_to_note_names
from .timing import note_duration_seconds


def expand_exercise_to_segments(exercise: RawExercise):
    """
    For each key in the resolved sequence, compute (pitch, duration) list and pause.
    Returns list of dicts: { "key_name", "pitches", "midi_notes", "durations_sec", "pause_ms" }.
    """
    keys = waypoints_to_key_sequence(exercise.modulation_waypoints)
    key_names = key_sequence_to_names(keys)
    note_dur = note_duration_seconds(
        exercise.bpm,
        exercise.note_value,
    )

    segments = []
    for (pc, oct), key_name in zip(keys, key_names):
        pitches = scale_degrees_to_note_names(pc, oct, exercise.scale_degrees)
        midi_notes = scale_degrees_to_midi(pc, oct, exercise.scale_degrees)
        # Same duration for each note in the pattern (8th notes)
        durations = [note_dur] * len(pitches)
        segments.append({
            "key_name": key_name,
            "pitches": pitches,
            "midi_notes": midi_notes,
            "durations_sec": durations,
            "pause_ms": exercise.pause_between_keys_ms,
        })
    return segments
