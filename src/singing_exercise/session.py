"""Session file: exercises, optional YouTube clips, and optional local audio clips."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from .raw_audio_clip import RawAudioClip
from .raw_exercise import RawExercise
from .raw_youtube_clip import RawYoutubeClip


@dataclass
class Session:
    exercises: list[RawExercise]
    youtube_clips: list[RawYoutubeClip]
    audio_clips: list[RawAudioClip]
    pause_between_exercises_ms: int = 3000


def load_session_from_yaml_path(path: Path) -> Session:
    """
    Load a practice session from YAML.

    Top-level keys: exercises (list), youtube_clips (optional list),
    audio_clips (optional list), pause_between_exercises_ms (optional, default 3000).
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    exercises = [RawExercise.from_dict(ex) for ex in data.get("exercises") or []]
    youtube_clips = [RawYoutubeClip.from_dict(ex) for ex in data.get("youtube_clips") or []]
    audio_clips = [RawAudioClip.from_dict(ex) for ex in data.get("audio_clips") or []]
    pause_ms = int(data.get("pause_between_exercises_ms", 3000))
    return Session(
        exercises=exercises,
        youtube_clips=youtube_clips,
        audio_clips=audio_clips,
        pause_between_exercises_ms=pause_ms,
    )
