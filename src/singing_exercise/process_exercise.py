"""
Process exercise: load YAML, resolve key sequence, expand to modulations.
No audio/MIDI/WAV output.
"""
from .keys import key_sequence_to_names, waypoints_to_key_sequence
from .raw_exercise import RawExercise, FeedbackEntry
from .scale import scale_degrees_to_midi, scale_degrees_to_note_names
from .timing import note_duration_seconds


def expand_exercise_to_modulations(exercise: RawExercise):
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

    modulations = []
    for (pc, oct), key_name in zip(keys, key_names):
        pitches = scale_degrees_to_note_names(pc, oct, exercise.scale_degrees)
        midi_notes = scale_degrees_to_midi(pc, oct, exercise.scale_degrees)
        # Same duration for each note in the pattern (8th notes)
        durations = [note_dur] * len(pitches)
        modulations.append({
            "key_name": key_name,
            "pitches": pitches,
            "midi_notes": midi_notes,
            "durations_sec": durations,
            "pause_ms": exercise.pause_between_keys_ms,
        })
    return modulations


def feedback_after_modulation(
    modulations: list[dict],
    feedback_list: list[FeedbackEntry],
) -> list[list[str]]:
    """
    For each modulation index i, return the list of feedback texts to speak after that
    modulation (after the pause). Placement: after the Nth occurrence of the given key.
    Returns list of length len(modulations); each element is a list of text strings (may be empty).
    """
    result: list[list[str]] = [[] for _ in modulations]
    # Count occurrences of each key as we walk modulations
    occurrence: dict[str, int] = {}
    for i, mod in enumerate(modulations):
        key_name = mod["key_name"]
        occurrence[key_name] = occurrence.get(key_name, 0) + 1
        for fb in feedback_list:
            if fb.key == key_name and fb.which_occurrence == occurrence[key_name]:
                if fb.text:
                    result[i].append(fb.text)
    return result
