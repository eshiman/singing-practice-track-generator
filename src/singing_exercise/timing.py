"""Note duration from BPM and note value (e.g. 8th note at 70 BPM)."""

from typing import Union

# Numeric note values: denominator in 4/4 (2=half, 4=quarter, 8=eighth, 16=sixteenth)
NUMERIC_TO_BEATS = {2: 2.0, 4: 1.0, 8: 0.5, 16: 0.25}


def note_duration_seconds(bpm: int, note_value: Union[int, str]) -> float:
    """
    Duration in seconds of one note for the given BPM and note value.

    note_value can be:
    - int: 2=half, 4=quarter, 8=eighth, 16=sixteenth (beats in 4/4)
    - str: "8th", "quarter", "4th", "half", "16th", etc.
    """
    beat_duration_sec = 60.0 / bpm
    if isinstance(note_value, int):
        beats = NUMERIC_TO_BEATS.get(note_value)
        if beats is None:
            raise ValueError(
                f"Invalid numeric note value {note_value}; use 2, 4, 8, or 16"
            )
        return beat_duration_sec * beats
    nv = (note_value or "8th").strip().lower()
    if nv == "8th":
        return beat_duration_sec * 0.5
    if nv in ("quarter", "quarter note", "4th"):
        return beat_duration_sec
    if nv in ("half", "half note", "2nd"):
        return beat_duration_sec * 2.0
    if nv in ("16th", "sixteenth", "sixteenth note"):
        return beat_duration_sec * 0.25
    # Default to 8th
    return beat_duration_sec * 0.5
