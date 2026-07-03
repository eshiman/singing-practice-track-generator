"""Expand audio clip definitions to modulation offset passes."""
from .keys import offsets_to_offset_sequence
from .raw_audio_clip import RawAudioClip


def expand_audio_clip_to_offsets(clip: RawAudioClip) -> list[int]:
    """Return ordered semitone offsets to play for this clip."""
    return offsets_to_offset_sequence(clip.modulation_offsets)
