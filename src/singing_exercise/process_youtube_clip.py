"""Expand YouTube clip definitions to modulation offset passes."""
from .keys import offsets_to_offset_sequence
from .raw_youtube_clip import RawYoutubeClip


def expand_clip_to_offsets(clip: RawYoutubeClip) -> list[int]:
    """Return ordered semitone offsets to play for this clip."""
    return offsets_to_offset_sequence(clip.modulation_offsets)
