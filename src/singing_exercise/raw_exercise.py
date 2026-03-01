"""Raw exercise model: load YAML and represent unprocessed exercise."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FeedbackEntry:
    """One spoken feedback cue: after Nth occurrence of a key, speak this text."""

    key: str
    which_occurrence: int
    text: str


@dataclass
class RawExercise:
    """Raw exercise definition from YAML (used as input for plan generation)."""

    name: str
    scale_degrees: list[int]
    syllable: str
    modulation_waypoints: list[str]
    bpm: int
    note_value: str
    pause_between_keys_ms: int
    feedback: list[FeedbackEntry]

    @classmethod
    def from_yaml_path(cls, path: Path) -> "RawExercise":
        """Load raw exercise from a YAML file. Includes feedback for Phase 3."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawExercise":
        """Build RawExercise from dict. Parses feedback list when present."""
        feedback_raw = data.get("feedback") or []
        feedback = [
            FeedbackEntry(
                key=entry.get("key", ""),
                which_occurrence=int(entry.get("which_occurrence", 1)),
                text=(entry.get("text") or "").strip(),
            )
            for entry in feedback_raw
        ]
        return cls(
            name=data.get("name", "Unnamed"),
            scale_degrees=data.get("scale_degrees", []),
            syllable=data.get("syllable", ""),
            modulation_waypoints=data.get("modulation_waypoints", []),
            bpm=data.get("bpm", 70),
            note_value=data.get("note_value", "8th"),
            pause_between_keys_ms=data.get("pause_between_keys_ms", 2000),
            feedback=feedback,
        )
