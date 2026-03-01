"""Note duration from BPM and note value (e.g. 8th note at 70 BPM)."""

from typing import Union

# Numeric note values: denominator in 4/4 (2=half, 4=quarter, 8=eighth, 16=sixteenth)
NUMERIC_TO_BEATS = {2: 2.0, 4: 1.0, 8: 0.5, 16: 0.25}


def _beats_for_note_value(note_value: Union[int, str]) -> float:
    """Return beats (in 4/4) for a single undotted note value. Raises ValueError if invalid."""
    if isinstance(note_value, int):
        beats = NUMERIC_TO_BEATS.get(note_value)
        if beats is None:
            raise ValueError(
                f"Invalid numeric note value {note_value}; use 2, 4, 8, or 16"
            )
        return beats
    nv = (note_value or "8th").strip().lower()
    if nv in ("2", "4", "8", "16"):
        return NUMERIC_TO_BEATS[int(nv)]
    if nv == "8th":
        return 0.5
    if nv in ("quarter", "quarter note", "4th"):
        return 1.0
    if nv in ("half", "half note", "2nd"):
        return 2.0
    if nv in ("16th", "sixteenth", "sixteenth note"):
        return 0.25
    return 0.5  # default 8th


def note_duration_seconds(bpm: int, note_value: Union[int, str]) -> float:
    """
    Duration in seconds of one note for the given BPM and note value.

    note_value can be:
    - int: 2=half, 4=quarter, 8=eighth, 16=sixteenth (beats in 4/4)
    - str: "8th", "quarter", "4th", "half", "16th", etc.
    - str with trailing dot: dotted note (e.g. "4." = dotted quarter, "8." = dotted eighth).
      Dotted = 1.5 × base duration.
    """
    beat_duration_sec = 60.0 / bpm
    dotted = False
    if isinstance(note_value, str) and note_value.strip().endswith("."):
        note_value = note_value.strip()[:-1].strip() or "8th"
        dotted = True
    beats = _beats_for_note_value(note_value)
    if dotted:
        beats *= 1.5
    return beat_duration_sec * beats
