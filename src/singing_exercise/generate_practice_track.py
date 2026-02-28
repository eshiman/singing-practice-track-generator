"""
Generate a practice track from an exercise YAML: MIDI per segment, render to WAV, concatenate.
Requires: mido, pydub, fluidsynth CLI, and a piano soundfont (.sf2).
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from .render_wav import render_segments_to_wav
from .render_midi import segment_to_midi_bytes
from .raw_exercise import RawExercise
from .process_exercise import expand_exercise_to_segments

logger = logging.getLogger(__name__)


def generate_wav(
    yaml_path: Path,
    output_path: Path,
    soundfont_path: Path,
    sample_rate: int = 44100,
) -> None:
    """
    Load raw exercise from YAML, expand to segments, build segment MIDIs, render to WAV, concatenate with pauses.
    """
    exercise = RawExercise.from_yaml_path(yaml_path)
    segments = expand_exercise_to_segments(exercise)
    if not segments:
        logger.warning("No segments (empty key sequence); output will be empty.")

    segments_midi = []
    for seg in segments:
        data = segment_to_midi_bytes(
            seg["midi_notes"],
            seg["durations_sec"],
            exercise.bpm,
        )
        segments_midi.append(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    render_segments_to_wav(
        segments_midi,
        pause_ms=exercise.pause_between_keys_ms,
        soundfont_path=soundfont_path,
        output_path=output_path,
        sample_rate=sample_rate,
    )
    logger.info("Wrote %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a practice track WAV from an exercise YAML (piano + pauses)."
    )
    parser.add_argument("yaml_path", type=Path, help="Path to exercise YAML file")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output WAV path (default: output/<exercise_name>.wav)",
    )
    parser.add_argument(
        "--soundfont",
        type=Path,
        default=None,
        help="Path to .sf2 piano soundfont (or set SOUNDFONT env)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    if not args.yaml_path.exists():
        logger.error("File not found: %s", args.yaml_path)
        sys.exit(1)

    soundfont = args.soundfont or (os.environ.get("SOUNDFONT") and Path(os.environ["SOUNDFONT"]))
    if not soundfont or not Path(soundfont).exists():
        logger.error(
            "Soundfont required. Set SOUNDFONT env or pass --soundfont path/to/piano.sf2"
        )
        sys.exit(1)
    soundfont_path = Path(soundfont)

    output = args.output
    if output is None:
        exercise = RawExercise.from_yaml_path(args.yaml_path)
        output = Path("output") / f"{exercise.name}.wav"

    generate_wav(
        yaml_path=args.yaml_path,
        output_path=output,
        soundfont_path=soundfont_path,
    )


if __name__ == "__main__":
    main()
