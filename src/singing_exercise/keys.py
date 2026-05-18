"""Key representation and resolution: waypoints → full key sequence by semitones."""
import re
from typing import List, Tuple

# Pitch class 0-11: C=0, C#/Db=1, D=2, ..., B=11
# Note names for display (flat for 1,3,6,8,10 to match common keys)
PITCH_CLASS_NAMES = [
    "C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
]

# Alternative sharp names for parsing
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

NOTE_NAME_PATTERN = re.compile(
    r"^([A-G])([b#])?\s*(\d+)\s*$", re.IGNORECASE
)


def parse_note(note_str: str) -> Tuple[int, int]:
    """
    Parse a note string like 'D4', 'Db4', 'F#3', 'Bb4' to (pitch_class, octave).
    pitch_class 0-11 (C=0), octave as integer (e.g. 4 for middle octave).
    """
    m = NOTE_NAME_PATTERN.match(note_str.strip())
    if not m:
        raise ValueError(f"Invalid note name: {note_str!r}")
    letter, accidental, oct_str = m.groups()
    letter = letter.upper()
    octave = int(oct_str)

    # Base pitch class: C=0, D=2, E=4, F=5, G=7, A=9, B=11
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
    if accidental == "#":
        base = (base + 1) % 12
    elif accidental == "b":
        base = (base - 1) % 12
    return (base, octave)


def note_to_midi(pitch_class: int, octave: int) -> int:
    """Convert (pitch_class, octave) to MIDI note number. C4 = 60."""
    return 12 * (octave + 1) + pitch_class


def midi_to_note(midi: int) -> Tuple[int, int]:
    """Convert MIDI note number to (pitch_class, octave)."""
    pitch_class = midi % 12
    octave = (midi // 12) - 1
    return (pitch_class, octave)


def note_name(pitch_class: int, octave: int) -> str:
    """Format (pitch_class, octave) as note name (e.g. 'D4', 'Bb4')."""
    return f"{PITCH_CLASS_NAMES[pitch_class]}{octave}"


def waypoints_to_key_sequence(waypoints: List[str]) -> List[Tuple[int, int]]:
    """
    Resolve modulation waypoints to full key sequence.
    Between consecutive waypoints we step by semitones (up or down).
    Waypoints are not duplicated at modulation boundaries (each key appears once in order).
    Returns list of (pitch_class, octave) for each key.
    """
    if not waypoints:
        return []
    if len(waypoints) == 1:
        return [parse_note(waypoints[0])]

    result: List[Tuple[int, int]] = []
    for i in range(len(waypoints) - 1):
        from_pc, from_oct = parse_note(waypoints[i])
        to_pc, to_oct = parse_note(waypoints[i + 1])
        from_midi = note_to_midi(from_pc, from_oct)
        to_midi = note_to_midi(to_pc, to_oct)

        if from_midi <= to_midi:
            step = 1
            midi_list = list(range(from_midi, to_midi + 1, step))
        else:
            step = -1
            midi_list = list(range(from_midi, to_midi - 1, step))

        # First modulation: add all keys. Later modulations: skip first (same as last of previous).
        start = 1 if i > 0 else 0
        for midi in midi_list[start:]:
            result.append(midi_to_note(midi))
    return result


def key_sequence_to_names(keys: List[Tuple[int, int]]) -> List[str]:
    """Convert list of (pitch_class, octave) to note name strings."""
    return [note_name(pc, oct) for pc, oct in keys]


def offsets_to_offset_sequence(offsets: List[int]) -> List[int]:
    """
    Resolve modulation offset waypoints to a full offset sequence.
    Between consecutive offsets we step by one semitone (up or down).
    Waypoints are not duplicated at boundaries (same rule as waypoints_to_key_sequence).
    """
    if not offsets:
        return []
    if len(offsets) == 1:
        return [offsets[0]]

    result: List[int] = []
    for i in range(len(offsets) - 1):
        from_off = offsets[i]
        to_off = offsets[i + 1]
        if from_off <= to_off:
            off_list = list(range(from_off, to_off + 1))
        else:
            off_list = list(range(from_off, to_off - 1, -1))
        start = 1 if i > 0 else 0
        for off in off_list[start:]:
            result.append(off)
    return result
