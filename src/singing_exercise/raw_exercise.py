"""Raw exercise model: load YAML and represent unprocessed exercise."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import yaml

from .keys import parse_note, note_name
from .timing import is_tied_from_previous, note_duration_seconds


@dataclass
class FeedbackEntry:
    """One spoken feedback cue: after Nth occurrence of a key, speak this text."""

    key: str
    which_occurrence: int
    text: str


@dataclass
class RepeatedModulationRule:
    """Duplicate a modulation key extra_repeats times for a specific occurrence."""

    key: str
    extra_repeats: int
    which_occurrence: int = 1


@dataclass
class RawExercise:
    """Raw exercise definition from YAML (used as input for plan generation)."""

    name: str
    scale_degrees: list[Union[int, str, list]]  # int/str for single note or "R"; list of int/str for chord e.g. [1, 3, 5]
    modulation_waypoints: list[str]
    bpm: int
    note_value: str
    pause_between_keys_ms: int
    feedback: list[FeedbackEntry]
    repeated_modulations: list[RepeatedModulationRule]
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
        from .session import load_session_from_yaml_path

        session = load_session_from_yaml_path(path)
        return session.exercises, session.pause_between_exercises_ms

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawExercise":
        """Build RawExercise from dict. Parses feedback list when present."""
        feedback_raw = data.get("feedback") or []
        feedback = []
        for entry in feedback_raw:
            raw_key = (entry.get("key") or "").strip()
            try:
                pc, octv = parse_note(raw_key)
                normalized_key = note_name(pc, octv)
            except ValueError as exc:
                raise ValueError(f"Invalid feedback key: {raw_key!r}") from exc
            feedback.append(FeedbackEntry(
                key=normalized_key,
                which_occurrence=int(entry.get("which_occurrence", 1)),
                text=(entry.get("text") or "").strip(),
            ))
        repeated_modulations_raw = data.get("repeated_modulations") or []
        repeated_modulations: list[RepeatedModulationRule] = []
        for entry in repeated_modulations_raw:
            raw_key = (entry.get("key") or "").strip()
            key = raw_key
            if not key:
                raise ValueError("repeated_modulations[].key is required")
            try:
                # Validate note syntax early; matching still happens in process phase.
                pc, octv = parse_note(key)
                # Normalize enharmonic spellings (e.g. C#4 -> Db4) to match key sequence names.
                key = note_name(pc, octv)
            except ValueError as exc:
                raise ValueError(f"Invalid repeated_modulations key: {raw_key!r}") from exc

            if "extra_repeats" not in entry:
                raise ValueError(f"repeated_modulations[{key}].extra_repeats is required")
            extra_repeats = int(entry["extra_repeats"])
            if extra_repeats < 0:
                raise ValueError(
                    f"repeated_modulations[{key}].extra_repeats must be >= 0, got {extra_repeats}"
                )

            which_occurrence = int(entry.get("which_occurrence", 1))
            if which_occurrence < 1:
                raise ValueError(
                    f"repeated_modulations[{key}].which_occurrence must be >= 1, got {which_occurrence}"
                )

            repeated_modulations.append(
                RepeatedModulationRule(
                    key=key,
                    extra_repeats=extra_repeats,
                    which_occurrence=which_occurrence,
                )
            )
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
            repeated_modulations=repeated_modulations,
            demo=bool(data.get("demo", False)),
            note_values=note_values,
        )
