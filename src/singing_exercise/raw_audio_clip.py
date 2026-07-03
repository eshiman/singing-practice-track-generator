"""Raw audio clip model: load from session YAML."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RawAudioClip:
    """Local audio clip segment from session YAML."""

    name: str
    filename: str
    start_time: str
    end_time: str
    modulation_offsets: list[int]
    demo: bool = False
    pause_between_keys_ms: int = 2000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawAudioClip":
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("audio_clips[].name is required")
        filename = (data.get("filename") or "").strip()
        if not filename:
            raise ValueError(f"audio_clips[{name!r}].filename is required")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if not start_time or not end_time:
            raise ValueError(f"audio_clips[{name!r}].start_time and end_time are required")
        offsets_raw = data.get("modulation_offsets")
        if offsets_raw is None:
            raise ValueError(f"audio_clips[{name!r}].modulation_offsets is required")
        if not isinstance(offsets_raw, list) or not offsets_raw:
            raise ValueError(
                f"audio_clips[{name!r}].modulation_offsets must be a non-empty list"
            )
        modulation_offsets = []
        for off in offsets_raw:
            if not isinstance(off, int) or isinstance(off, bool):
                raise ValueError(
                    f"audio_clips[{name!r}].modulation_offsets must be integers, got {off!r}"
                )
            modulation_offsets.append(off)
        pause_ms = int(data.get("pause_between_keys_ms", 2000))
        return cls(
            name=name,
            filename=filename,
            start_time=str(start_time),
            end_time=str(end_time),
            modulation_offsets=modulation_offsets,
            demo=bool(data.get("demo", False)),
            pause_between_keys_ms=pause_ms,
        )

    @classmethod
    def load_all_from_yaml_path(cls, path: Path) -> list["RawAudioClip"]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "audio_clips" not in data:
            return []
        return [cls.from_dict(entry) for entry in data["audio_clips"]]
