"""Note duration from BPM and note value (e.g. 8th note at 70 BPM)."""


def note_duration_seconds(bpm: int, note_value: str) -> float:
    """
    Duration in seconds of one note for the given BPM and note value.
    note_value: "8th" (half a beat) or "quarter" (one beat). Default 8th.
    """
    beat_duration_sec = 60.0 / bpm
    nv = (note_value or "8th").strip().lower()
    if nv == "8th":
        return beat_duration_sec * 0.5
    if nv in ("quarter", "quarter note", "4th"):
        return beat_duration_sec
    # Default to 8th
    return beat_duration_sec * 0.5
