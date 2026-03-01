"""
Generate a practice track from an exercise YAML: MIDI per segment, render to WAV, concatenate.
Phase 3: optional spoken feedback (TTS) at key/occurrence positions.
Requires: mido, pydub, fluidsynth CLI, and a piano soundfont (.sf2).
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from .config import load_config
from .render_wav import render_segments_to_wav, render_sequence_to_wav
from .render_midi import segment_to_midi_bytes
from .raw_exercise import RawExercise
from .process_exercise import expand_exercise_to_segments, feedback_after_segment
from . import generate_voice

logger = logging.getLogger(__name__)


def _build_sequence(exercise: RawExercise, segments: list, segments_midi: list) -> list:
    """
    Build ordered list of segment descriptors: TTS (feedback) before each key, then piano, then silence.
    """
    feedback_by_segment = feedback_after_segment(segments, exercise.feedback)
    sequence = []
    for i, midi_bytes in enumerate(segments_midi):
        for text in feedback_by_segment[i]:
            sequence.append({"type": "tts", "text": text})
        sequence.append({"type": "piano", "midi": midi_bytes})
        if i < len(segments_midi) - 1:
            sequence.append({"type": "silence", "ms": exercise.pause_between_keys_ms})
    return sequence


def generate_wav(
    yaml_path: Path,
    output_path: Path,
    soundfont_path: Path,
    sample_rate: int = 44100,
    tts_volume_db: float | None = None,
    music_volume_db: float | None = None,
) -> None:
    """
    Load raw exercise from YAML, expand to segments, build segment MIDIs and (if feedback) TTS,
    then render sequence to one WAV (piano + pauses + spoken feedback at key/occurrence).
    tts_volume_db / music_volume_db: when None, use values from config (see config.yaml).
    """
    config = load_config()
    tts_db = tts_volume_db if tts_volume_db is not None else config["tts_volume_db"]
    music_db = music_volume_db if music_volume_db is not None else config["music_volume_db"]

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

    if exercise.feedback:
        sequence = _build_sequence(exercise, segments, segments_midi)
        def tts_generator(text: str, out_path: Path) -> None:
            generate_voice.text_to_wav(text, out_path, normalize=True, sample_rate=sample_rate, target_dbfs=tts_db)
        render_sequence_to_wav(
            sequence,
            soundfont_path=soundfont_path,
            output_path=output_path,
            tts_generator=tts_generator,
            sample_rate=sample_rate,
            music_volume_db=music_db,
        )
    else:
        render_segments_to_wav(
            segments_midi,
            pause_ms=exercise.pause_between_keys_ms,
            soundfont_path=soundfont_path,
            output_path=output_path,
            sample_rate=sample_rate,
            music_volume_db=music_db,
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
    parser.add_argument(
        "--tts-volume-db",
        type=float,
        default=None,
        metavar="DB",
        help="Override TTS volume in dB (default: from config.yaml)",
    )
    parser.add_argument(
        "--music-volume-db",
        type=float,
        default=None,
        metavar="DB",
        help="Override music/piano volume in dB (default: from config.yaml)",
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
        tts_volume_db=args.tts_volume_db,
        music_volume_db=args.music_volume_db,
    )


if __name__ == "__main__":
    main()
