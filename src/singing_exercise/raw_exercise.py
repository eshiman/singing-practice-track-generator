"""Raw exercise model: load YAML and represent unprocessed exercise (feedback ignored)."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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

    @classmethod
    def from_yaml_path(cls, path: Path) -> "RawExercise":
        """Load raw exercise from a YAML file. Ignores 'feedback' and any other extra keys."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawExercise":
        """Build RawExercise from dict. Uses plan-related fields only; ignores 'feedback'."""
        return cls(
            name=data.get("name", "Unnamed"),
            scale_degrees=data.get("scale_degrees", []),
            syllable=data.get("syllable", ""),
            modulation_waypoints=data.get("modulation_waypoints", []),
            bpm=data.get("bpm", 70),
            note_value=data.get("note_value", "8th"),
            pause_between_keys_ms=data.get("pause_between_keys_ms", 2000),
        )
