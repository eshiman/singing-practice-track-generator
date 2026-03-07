"""Scale degree to pitch mapping (major scale)."""
import re
from typing import List, Literal, Tuple, Union

from .keys import midi_to_note, note_name, note_to_midi

# Major scale semitone offsets from tonic: degree 1..8
MAJOR_SCALE_OFFSETS = [0, 2, 4, 5, 7, 9, 11, 12]

# Single degree slot: ("degree", degree_int, "natural"|"flat"|"sharp")
DegreeSlot = Tuple[Literal["degree"], int, Literal["natural", "flat", "sharp"]]
# Parsed slot: rest, single degree, or chord (list of degree slots)
ScaleDegreeSlot = Union[
    Tuple[Literal["rest"]],
    DegreeSlot,
    Tuple[Literal["chord"], List[DegreeSlot]],
]

# Pattern: optional b or #, then optional minus and digits (any integer degree)
_DEGREE_PATTERN = re.compile(r"^(b|#)?(-?\d+)$", re.IGNORECASE)


def _degree_to_offset(degree: int) -> int:
    """
    Map any scale degree to semitone offset from key tonic.
    Scale has 7 steps per octave; degree 8 = octave (same as 1 up). So degree 9 = step 2
    one octave up (whole step above 8), 10 = step 3 up, etc. 0,-1..-6 = octave down.
    """
    # Period is 7: 1-7 = steps, 8 = octave (step 1 + 12), 9 = step 2 + 12, ...
    step_1_7 = ((degree - 1) % 7) + 1  # 1..7
    octave_offset = (degree - 1) // 7
    return MAJOR_SCALE_OFFSETS[step_1_7 - 1] + 12 * octave_offset


def parse_scale_degree_entry(entry: Union[int, str, List[Union[int, str]]]) -> ScaleDegreeSlot:
    """
    Parse one scale_degrees entry from YAML.
    Returns ("rest",) for "R", ("degree", degree_int, accidental) for a single pitch,
    or ("chord", [degree_slots...]) for a list of degrees (e.g. [1, 3, 5] or [1, "b3", 5]).
    Accepts: any int (natural), str "1"-"8", "9", "-1", etc., "R", "b3", "#5".
    Degrees outside 1-8 map by octave: 9=2 up, 0=8 down, -1=7 down, etc.
    """
    if isinstance(entry, list):
        # Chord: list of degrees (no rest allowed inside a chord)
        degree_slots: List[DegreeSlot] = []
        for sub in entry:
            slot = parse_scale_degree_entry(sub)
            if slot[0] == "rest":
                raise ValueError(
                    f"Chord cannot contain rest; invalid entry {entry!r}"
                )
            if slot[0] == "chord":
                raise ValueError(
                    f"Nested chords not allowed; invalid entry {entry!r}"
                )
            degree_slots.append(slot)
        return ("chord", degree_slots)
    if isinstance(entry, int):
        return ("degree", entry, "natural")
    s = str(entry).strip()
    if s.upper() == "R":
        return ("rest",)
    m = _DEGREE_PATTERN.match(s)
    if not m:
        raise ValueError(
            f"Invalid scale degree entry {entry!r}; use an integer degree, 'R', 'b3', '#5', or a list for chord."
        )
    acc_char, num = m.group(1), int(m.group(2))
    accidental: Literal["natural", "flat", "sharp"] = (
        "flat" if acc_char and acc_char.lower() == "b" else "sharp" if acc_char == "#" else "natural"
    )
    return ("degree", num, accidental)


def parse_scale_degrees(scale_degrees: List[Union[int, str, List[Union[int, str]]]]) -> List[ScaleDegreeSlot]:
    """Parse full scale_degrees list into a list of slots (rest, single degree, or chord)."""
    return [parse_scale_degree_entry(e) for e in scale_degrees]


def _slot_to_midi_one(base_midi: int, slot: DegreeSlot) -> int:
    """Map a single degree slot to one MIDI note number."""
    _, degree, accidental = slot
    offset = _degree_to_offset(degree)
    if accidental == "flat":
        offset -= 1
    elif accidental == "sharp":
        offset += 1
    return base_midi + offset


def slots_to_midi(
    key_pitch_class: int,
    key_octave: int,
    slots: List[ScaleDegreeSlot],
) -> List[Union[int, List[int], None]]:
    """
    Map parsed slots to MIDI note numbers (or None for rest).
    Single degree -> one int; chord -> list of ints; rest -> None.
    Output length equals input length.
    """
    base_midi = note_to_midi(key_pitch_class, key_octave)
    result: List[Union[int, List[int], None]] = []
    for slot in slots:
        if slot[0] == "rest":
            result.append(None)
            continue
        if slot[0] == "chord":
            chord_midi = [_slot_to_midi_one(base_midi, s) for s in slot[1]]
            result.append(chord_midi)
            continue
        result.append(_slot_to_midi_one(base_midi, slot))
    return result


def slots_to_note_names(
    key_pitch_class: int,
    key_octave: int,
    slots: List[ScaleDegreeSlot],
) -> List[Union[str, List[str], None]]:
    """Map parsed slots to note name strings (or None for rest, or list of names for chord). For logging/debug."""
    midi_list = slots_to_midi(key_pitch_class, key_octave, slots)
    result: List[Union[str, List[str], None]] = []
    for m in midi_list:
        if m is None:
            result.append(None)
        elif isinstance(m, list):
            result.append([note_name(*midi_to_note(n)) for n in m])
        else:
            result.append(note_name(*midi_to_note(m)))
    return result


def scale_degrees_to_midi(
    key_pitch_class: int,
    key_octave: int,
    scale_degrees: List[int],
) -> List[int]:
    """
    Map scale degrees to MIDI note numbers in the given key (major scale).
    Degree 1 = tonic, 8 = octave above; 9+ and 0/-1/-2... extend by octaves.
    (Legacy: use parse_scale_degrees + slots_to_midi for rest/accidentals.)
    """
    base_midi = note_to_midi(key_pitch_class, key_octave)
    result = []
    for d in scale_degrees:
        offset = _degree_to_offset(d)
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
