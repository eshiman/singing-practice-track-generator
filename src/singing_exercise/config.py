"""Load app config from YAML. Config file is optional; defaults used when missing."""
from pathlib import Path
from typing import Any

DEFAULT_TTS_VOLUME_DB = -6.0
DEFAULT_MUSIC_VOLUME_DB = 0.0


def _config_paths() -> list[Path]:
    """Candidate paths for config.yaml: cwd, then repo root (parent of src)."""
    cwd = Path.cwd() / "config.yaml"
    # This file is src/singing_exercise/config.py -> parent.parent = src, parent.parent.parent = repo
    repo_root = Path(__file__).resolve().parent.parent.parent
    return [cwd, repo_root / "config.yaml"]


def load_config() -> dict[str, Any]:
    """
    Load config from config.yaml if present. Returns dict with at least
    tts_volume_db and music_volume_db (floats). Missing file or keys use defaults.
    """
    import yaml
    result: dict[str, Any] = {
        "tts_volume_db": DEFAULT_TTS_VOLUME_DB,
        "music_volume_db": DEFAULT_MUSIC_VOLUME_DB,
    }
    for path in _config_paths():
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "tts_volume_db" in data:
                    result["tts_volume_db"] = float(data["tts_volume_db"])
                if "music_volume_db" in data:
                    result["music_volume_db"] = float(data["music_volume_db"])
            except Exception:
                pass
            break
    return result
