"""Note duration from BPM and note value (e.g. 8th note at 70 BPM)."""

from typing import Union

# Numeric note values: denominator in 4/4 (1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth)
NUMERIC_TO_BEATS = {1: 4.0, 2: 2.0, 4: 1.0, 8: 0.5, 16: 0.25}

# Triplets: 3 in the time of 2 of the base note (in 4/4)
# 8t: 3 in 1 quarter → 1/3 beat each
# 4t: 3 in 1 half (2 beats) → 2/3 beat each
# 16t: 3 in 1 eighth (0.5 beat) → 1/6 beat each
TRIPLET_8T_BEATS = 1.0 / 3.0
TRIPLET_4T_BEATS = 2.0 / 3.0
TRIPLET_16T_BEATS = 1.0 / 6.0


def _strip_tie_markers(s: str) -> str:
    """Remove leading and trailing tie markers (~) for duration parsing."""
    s = s.strip()
    while s.startswith("~"):
        s = s[1:].strip()
    while s.endswith("~"):
        s = s[:-1].strip()
    return s


def _beats_for_note_value(note_value: Union[int, str]) -> float:
    """Return beats (in 4/4) for a single undotted note value. Raises ValueError if invalid.
    Tie markers (~) are stripped and do not affect duration.
    Triplets: "8t" = 1/3 beat, "4t" = 2/3 beat, "16t" = 1/6 beat.
    """
    if isinstance(note_value, int):
        beats = NUMERIC_TO_BEATS.get(note_value)
        if beats is None:
            raise ValueError(
                f"Invalid numeric note value {note_value}; use 1, 2, 4, 8, or 16"
            )
        return beats
    nv = (note_value or "8th").strip().lower()
    nv = _strip_tie_markers(nv)
    if not nv:
        nv = "8th"
    if nv == "8t":
        return TRIPLET_8T_BEATS
    if nv == "4t":
        return TRIPLET_4T_BEATS
    if nv == "16t":
        return TRIPLET_16T_BEATS
    if nv in ("1", "2", "4", "8", "16"):
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


def is_tied_from_previous(note_value: Union[int, str]) -> bool:
    """True if the note value string indicates a tie from the previous note (leading ~)."""
    if isinstance(note_value, int):
        return False
    return str(note_value).strip().startswith("~")


def note_duration_seconds(bpm: int, note_value: Union[int, str]) -> float:
    """
    Duration in seconds of one note for the given BPM and note value.

    note_value can be:
    - int: 1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth (beats in 4/4)
    - str: "8th", "quarter", "4th", "half", "16th", "8t"/"4t"/"16t" (triplets), etc.
    - str with leading/trailing ~: tie markers (e.g. "4~", "~8t", "~8t~"); ~ is ignored for duration.
    - str with trailing dot: dotted note (e.g. "4." = dotted quarter, "8." = dotted eighth).
      Dotted = 1.5 × base duration.
    """
    beat_duration_sec = 60.0 / bpm
    dotted = False
    if isinstance(note_value, str):
        nv = note_value.strip()
        nv = _strip_tie_markers(nv)
        if nv.endswith("."):
            nv = nv[:-1].strip() or "8th"
            dotted = True
        note_value = nv or "8th"
    beats = _beats_for_note_value(note_value)
    if dotted:
        beats *= 1.5
    return beat_duration_sec * beats
