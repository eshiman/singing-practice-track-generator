"""Raw YouTube clip model: load from session YAML."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def parse_mm_ss(timestamp: str) -> float:
    """Parse mm:ss or mm:ss.fff (e.g. '0:32', '1:05', '0:50.5') to seconds."""
    text = timestamp.strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected mm:ss timestamp, got {timestamp!r}")
    minutes_str, seconds_str = parts
    try:
        minutes = int(minutes_str)
        seconds = float(seconds_str)
    except ValueError as exc:
        raise ValueError(f"Invalid mm:ss timestamp: {timestamp!r}") from exc
    if minutes < 0 or seconds < 0 or seconds >= 60:
        raise ValueError(f"Invalid mm:ss timestamp: {timestamp!r}")
    return minutes * 60 + seconds


@dataclass
class RawYoutubeClip:
    """YouTube clip segment from session YAML."""

    name: str
    link: str
    start_time: str
    end_time: str
    modulation_offsets: list[int]
    demo: bool = False
    pause_between_keys_ms: int = 2000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawYoutubeClip":
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("youtube_clips[].name is required")
        link = (data.get("link") or "").strip()
        if not link:
            raise ValueError(f"youtube_clips[{name!r}].link is required")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if not start_time or not end_time:
            raise ValueError(f"youtube_clips[{name!r}].start_time and end_time are required")
        offsets_raw = data.get("modulation_offsets")
        if offsets_raw is None:
            raise ValueError(f"youtube_clips[{name!r}].modulation_offsets is required")
        if not isinstance(offsets_raw, list) or not offsets_raw:
            raise ValueError(
                f"youtube_clips[{name!r}].modulation_offsets must be a non-empty list"
            )
        modulation_offsets = []
        for off in offsets_raw:
            if not isinstance(off, int) or isinstance(off, bool):
                raise ValueError(
                    f"youtube_clips[{name!r}].modulation_offsets must be integers, got {off!r}"
                )
            modulation_offsets.append(off)
        pause_ms = int(data.get("pause_between_keys_ms", 2000))
        return cls(
            name=name,
            link=link,
            start_time=str(start_time),
            end_time=str(end_time),
            modulation_offsets=modulation_offsets,
            demo=bool(data.get("demo", False)),
            pause_between_keys_ms=pause_ms,
        )

    @classmethod
    def load_all_from_yaml_path(cls, path: Path) -> list["RawYoutubeClip"]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "youtube_clips" not in data:
            return []
        return [cls.from_dict(entry) for entry in data["youtube_clips"]]
