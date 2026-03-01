"""Raw exercise model: load YAML and represent unprocessed exercise."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import yaml

from .timing import is_tied_from_previous, note_duration_seconds


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
    scale_degrees: list[Union[int, str]]  # int (any degree) or str "1"-"8", "9", "-1", "R", "b3", "#5"
    modulation_waypoints: list[str]
    bpm: int
    note_value: str
    pause_between_keys_ms: int
    feedback: list[FeedbackEntry]
    demo: bool = False
    note_values: list[Union[int, str]] | None = None  # optional per-slot durations (2,4,8,16 or "8th" etc.)

    def get_durations_seconds(self) -> list[float]:
        """
        Return one duration in seconds per scale_degree slot.
        Uses note_values when present (length must match scale_degrees), else note_value for all.
        """
        n = len(self.scale_degrees)
        if self.note_values is not None:
            if len(self.note_values) != n:
                raise ValueError(
                    f"note_values length ({len(self.note_values)}) must match scale_degrees length ({n})"
                )
            return [
                note_duration_seconds(self.bpm, nv)
                for nv in self.note_values
            ]
        dur = note_duration_seconds(self.bpm, self.note_value)
        return [dur] * n

    def get_tie_from_previous(self) -> list[bool]:
        """
        Return one bool per scale_degree slot: True if that slot is tied from the previous
        (notation has leading ~, e.g. "~8t", "~8t~"). Only defined when note_values is present.
        """
        if self.note_values is None:
            return [False] * len(self.scale_degrees)
        return [is_tied_from_previous(nv) for nv in self.note_values]

    @classmethod
    def from_yaml_path(cls, path: Path) -> "RawExercise":
        """Load raw exercise from a YAML file. Includes feedback for Phase 3."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def load_all_from_yaml_path(cls, path: Path) -> tuple[list["RawExercise"], int]:
        """
        Load a session from a YAML file.

        The file must use the session format: top-level key "exercises" (list of
        exercise dicts). Optional top-level "pause_between_exercises_ms" (default 3000).

        Returns (list of RawExercise, pause_between_exercises_ms).
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "exercises" not in data:
            return [], 3000
        exercises = [cls.from_dict(ex) for ex in data["exercises"]]
        pause_ms = int(data.get("pause_between_exercises_ms", 3000))
        return exercises, pause_ms

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
        scale_degrees = data.get("scale_degrees", [])
        note_values = data.get("note_values")
        if note_values is not None and len(note_values) != len(scale_degrees):
            raise ValueError(
                f"note_values length ({len(note_values)}) must match scale_degrees length ({len(scale_degrees)})"
            )
        return cls(
            name=data.get("name", "Unnamed"),
            scale_degrees=scale_degrees,
            modulation_waypoints=data.get("modulation_waypoints", []),
            bpm=data.get("bpm", 70),
            note_value=data.get("note_value", "8th"),
            pause_between_keys_ms=data.get("pause_between_keys_ms", 2000),
            feedback=feedback,
            demo=bool(data.get("demo", False)),
            note_values=note_values,
        )
