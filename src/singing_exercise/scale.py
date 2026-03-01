"""Scale degree to pitch mapping (major scale)."""
import re
from typing import List, Literal, Tuple, Union

from .keys import midi_to_note, note_name, note_to_midi

# Major scale semitone offsets from tonic: degree 1..8
MAJOR_SCALE_OFFSETS = [0, 2, 4, 5, 7, 9, 11, 12]

# Parsed slot: ("rest",) or ("degree", degree_1_8, "natural"|"flat"|"sharp")
ScaleDegreeSlot = Union[
    Tuple[Literal["rest"]],
    Tuple[Literal["degree"], int, Literal["natural", "flat", "sharp"]],
]

# Pattern: optional b or #, then digit 1-8
_DEGREE_PATTERN = re.compile(r"^(b|#)?([1-8])$", re.IGNORECASE)


def parse_scale_degree_entry(entry: Union[int, str]) -> ScaleDegreeSlot:
    """
    Parse one scale_degrees entry from YAML.
    Returns ("rest",) for "R", or ("degree", degree_int, accidental) for pitches.
    Accepts: int 1-8 (natural), str "1"-"8", "R", "b3", "#5".
    """
    if isinstance(entry, int):
        if 1 <= entry <= 8:
            return ("degree", entry, "natural")
        raise ValueError(f"Scale degree must be 1-8, got {entry}")
    s = str(entry).strip()
    if s.upper() == "R":
        return ("rest",)
    m = _DEGREE_PATTERN.match(s)
    if not m:
        raise ValueError(
            f"Invalid scale degree entry {entry!r}; use 1-8, 'R', 'b3', '#5', etc."
        )
    acc_char, num = m.group(1), int(m.group(2))
    accidental: Literal["natural", "flat", "sharp"] = (
        "flat" if acc_char and acc_char.lower() == "b" else "sharp" if acc_char == "#" else "natural"
    )
    return ("degree", num, accidental)


def parse_scale_degrees(scale_degrees: List[Union[int, str]]) -> List[ScaleDegreeSlot]:
    """Parse full scale_degrees list into a list of slots (rest or degree+accidental)."""
    return [parse_scale_degree_entry(e) for e in scale_degrees]


def slots_to_midi(
    key_pitch_class: int,
    key_octave: int,
    slots: List[ScaleDegreeSlot],
) -> List[Union[int, None]]:
    """
    Map parsed slots to MIDI note numbers (or None for rest).
    Output length equals input length; rest slots yield None.
    """
    base_midi = note_to_midi(key_pitch_class, key_octave)
    result: List[Union[int, None]] = []
    for slot in slots:
        if slot[0] == "rest":
            result.append(None)
            continue
        _, degree, accidental = slot
        offset = MAJOR_SCALE_OFFSETS[degree - 1]
        if accidental == "flat":
            offset -= 1
        elif accidental == "sharp":
            offset += 1
        result.append(base_midi + offset)
    return result


def slots_to_note_names(
    key_pitch_class: int,
    key_octave: int,
    slots: List[ScaleDegreeSlot],
) -> List[Union[str, None]]:
    """Map parsed slots to note name strings (or None for rest). For logging/debug."""
    midi_list = slots_to_midi(key_pitch_class, key_octave, slots)
    return [None if m is None else note_name(*midi_to_note(m)) for m in midi_list]


def scale_degrees_to_midi(
    key_pitch_class: int,
    key_octave: int,
    scale_degrees: List[int],
) -> List[int]:
    """
    Map scale degrees (1-8) to MIDI note numbers in the given key (major scale).
    Degree 1 = tonic in key octave, degree 8 = octave above tonic.
    (Legacy: use parse_scale_degrees + slots_to_midi for rest/accidentals.)
    """
    base_midi = note_to_midi(key_pitch_class, key_octave)
    result = []
    for d in scale_degrees:
        if not 1 <= d <= 8:
            raise ValueError(f"Scale degree must be 1-8, got {d}")
        offset = MAJOR_SCALE_OFFSETS[d - 1]
        result.append(base_midi + offset)
    return result


def scale_degrees_to_note_names(
    key_pitch_class: int,
    key_octave: int,
    scale_degrees: List[int],
) -> List[str]:
    """Map scale degrees to note name strings (e.g. 'D5', 'A4') in the given key."""
    midi_notes = scale_degrees_to_midi(key_pitch_class, key_octave, scale_degrees)
    return [note_name(*midi_to_note(m)) for m in midi_notes]
