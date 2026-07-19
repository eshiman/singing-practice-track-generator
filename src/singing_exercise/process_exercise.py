"""
Process exercise: load YAML, resolve key sequence, expand to modulations.
No audio/MIDI/WAV output.
"""
from .keys import key_sequence_to_names, waypoints_to_key_sequence
from .raw_exercise import RawExercise, FeedbackEntry, RepeatedModulationRule
from .scale import parse_scale_degrees, slots_to_midi, slots_to_note_names


def _expand_with_repeated_modulations(
    key_names: list[str],
    repeat_rules: list[RepeatedModulationRule],
) -> list[dict]:
    """Return expanded key entries with repeat-copy metadata applied."""
    if not repeat_rules:
        return [{"key_name": key_name, "is_repeat_copy": False} for key_name in key_names]

    rules_by_key_and_occurrence: dict[tuple[str, int], int] = {}
    for rule in repeat_rules:
        rules_by_key_and_occurrence[(rule.key, rule.which_occurrence)] = rule.extra_repeats

    occurrence_by_key: dict[str, int] = {}
    expanded: list[dict] = []
    for key_name in key_names:
        occurrence_by_key[key_name] = occurrence_by_key.get(key_name, 0) + 1
        occurrence = occurrence_by_key[key_name]
        expanded.append({"key_name": key_name, "is_repeat_copy": False})
        extra_repeats = rules_by_key_and_occurrence.get((key_name, occurrence), 0)
        for _ in range(extra_repeats):
            expanded.append({"key_name": key_name, "is_repeat_copy": True})
    return expanded


def expand_exercise_to_modulations(exercise: RawExercise):
    """
    For each key in the resolved sequence, compute (pitch, duration) list and pause.
    Returns list of dicts: { "key_name", "pitches", "midi_notes", "durations_sec", "tie_from_previous", "pause_ms" }.
    midi_notes may contain None (rest), int (single note), or list of int (chord); durations_sec has one entry per slot.
    tie_from_previous[i] is True when that slot is tied to the previous (sustain, no new note_on).
    """
    keys = waypoints_to_key_sequence(exercise.modulation_waypoints)
    key_names = key_sequence_to_names(keys)
    slots = parse_scale_degrees(exercise.scale_degrees)
    durations_sec = exercise.get_durations_seconds()
    tie_from_previous = exercise.get_tie_from_previous()

    modulations = []
    expanded_key_entries = _expand_with_repeated_modulations(
        key_names,
        exercise.repeated_modulations,
    )
    key_to_pitch = {
        key_name: (pc, oct)
        for (pc, oct), key_name in zip(keys, key_names)
    }
    for key_entry in expanded_key_entries:
        key_name = key_entry["key_name"]
        pc, oct = key_to_pitch[key_name]
        midi_notes = slots_to_midi(pc, oct, slots)
        pitches = slots_to_note_names(pc, oct, slots)
        modulations.append({
            "key_name": key_name,
            "is_repeat_copy": key_entry["is_repeat_copy"],
            "pitches": pitches,
            "midi_notes": midi_notes,
            "durations_sec": durations_sec,
            "tie_from_previous": tie_from_previous,
            "pause_ms": exercise.pause_between_keys_ms,
        })
    return modulations


def feedback_after_modulation(
    modulations: list[dict],
    feedback_list: list[FeedbackEntry],
) -> list[list[FeedbackEntry]]:
    """
    For each modulation index i, return the FeedbackEntry objects triggered after that
    modulation (after the pause). Placement: after the Nth occurrence of the given key.
    Returns list of length len(modulations); each element is a list of entries (may be empty).
    """
    result: list[list[FeedbackEntry]] = [[] for _ in modulations]
    # Only original passes (not repeat copies) count toward occurrence tracking and trigger feedback.
    occurrence: dict[str, int] = {}
    for i, mod in enumerate(modulations):
        key_name = mod["key_name"]
        is_repeat = mod.get("is_repeat_copy", False)
        if not is_repeat:
            occurrence[key_name] = occurrence.get(key_name, 0) + 1
        for fb in feedback_list:
            if not is_repeat and fb.key == key_name and fb.which_occurrence == occurrence[key_name]:
                if fb.text:
                    result[i].append(fb)
    return result
