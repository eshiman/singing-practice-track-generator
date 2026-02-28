"""Scale degree to pitch mapping (major scale)."""
from typing import List, Tuple

from .keys import midi_to_note, note_name, note_to_midi

# Major scale semitone offsets from tonic: degree 1..8
MAJOR_SCALE_OFFSETS = [0, 2, 4, 5, 7, 9, 11, 12]


def scale_degrees_to_midi(
    key_pitch_class: int,
    key_octave: int,
    scale_degrees: List[int],
) -> List[int]:
    """
    Map scale degrees (1-8) to MIDI note numbers in the given key (major scale).
    Degree 1 = tonic in key octave, degree 8 = octave above tonic.
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
