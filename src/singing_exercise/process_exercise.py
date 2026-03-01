"""
Process exercise: load YAML, resolve key sequence, expand to modulations.
No audio/MIDI/WAV output.
"""
from .keys import key_sequence_to_names, waypoints_to_key_sequence
from .raw_exercise import RawExercise, FeedbackEntry
from .scale import parse_scale_degrees, slots_to_midi, slots_to_note_names


def expand_exercise_to_modulations(exercise: RawExercise):
    """
    For each key in the resolved sequence, compute (pitch, duration) list and pause.
    Returns list of dicts: { "key_name", "pitches", "midi_notes", "durations_sec", "pause_ms" }.
    midi_notes may contain None for rest slots; durations_sec has one entry per slot.
    """
    keys = waypoints_to_key_sequence(exercise.modulation_waypoints)
    key_names = key_sequence_to_names(keys)
    slots = parse_scale_degrees(exercise.scale_degrees)
    durations_sec = exercise.get_durations_seconds()

    modulations = []
    for (pc, oct), key_name in zip(keys, key_names):
        midi_notes = slots_to_midi(pc, oct, slots)
        pitches = slots_to_note_names(pc, oct, slots)
        modulations.append({
            "key_name": key_name,
            "pitches": pitches,
            "midi_notes": midi_notes,
            "durations_sec": durations_sec,
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
