#!/usr/bin/env python3
"""Generate practice track WAV from exercise YAML (piano + pauses). Requires fluidsynth and a .sf2 soundfont."""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from singing_exercise.generate_practice_track import main

if __name__ == "__main__":
    main()
