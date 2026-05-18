"""
Generate a practice track from an exercise YAML: MIDI per modulation, render to WAV, concatenate.
Phase 3: optional spoken feedback (TTS) at key/occurrence positions.
Requires: mido, pydub, fluidsynth CLI, and a piano soundfont (.sf2).
"""
import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

from .config import load_config
from .gather_audio_clips import gather_audio_clips
from .render_wav import concatenate_wavs
from .render_midi import modulation_to_midi_bytes
from .raw_exercise import RawExercise
from .process_exercise import expand_exercise_to_modulations, feedback_after_modulation
from .record_demo import record_demo

logger = logging.getLogger(__name__)


def _build_sequence(exercise: RawExercise, modulations: list, modulations_midi: list) -> list:
    """
    Build ordered list of segment descriptors: TTS (feedback) before each key, then piano, then silence.
    """
    feedback_by_modulation = feedback_after_modulation(modulations, exercise.feedback)
    sequence = []
    for i, midi_bytes in enumerate(modulations_midi):
        for text in feedback_by_modulation[i]:
            sequence.append({"type": "tts", "text": text})
        sequence.append({"type": "piano", "midi": midi_bytes})
        if i < len(modulations_midi) - 1:
            sequence.append({"type": "silence", "ms": exercise.pause_between_keys_ms})
    return sequence


def _exercise_to_sequence(exercise: RawExercise) -> list:
    """Build the full sequence (piano + pauses + optional TTS) for one exercise."""
    modulations = expand_exercise_to_modulations(exercise)
    if not modulations:
        return []
    modulations_midi = [
        modulation_to_midi_bytes(
            mod["midi_notes"],
            mod["durations_sec"],
            exercise.bpm,
            tie_from_previous=mod.get("tie_from_previous"),
        )
        for mod in modulations
    ]
    return _build_sequence(exercise, modulations, modulations_midi)


def generate_practice_track(
    yaml_path: Path,
    output_path: Path,
    soundfont_path: Path,
    sample_rate: int = 44100,
    tts_volume_db: float | None = None,
    music_volume_db: float | None = None,
) -> None:
    """
    Load a session from YAML and render to one WAV.

    The YAML must be a session file (top-level "exercises" list). All exercises
    are rendered in order into one long WAV, separated by pause_between_exercises_ms
    (default 3000 ms).

    tts_volume_db / music_volume_db: when None, use values from config (see config.yaml).
    """
    config = load_config()
    tts_db = tts_volume_db if tts_volume_db is not None else config["tts_volume_db"]
    music_db = music_volume_db if music_volume_db is not None else config["music_volume_db"]

    exercises, pause_between_exercises_ms = RawExercise.load_all_from_yaml_path(yaml_path)
    if not exercises:
        raise ValueError(f"No exercises in YAML: {yaml_path}")

    # Build one combined sequence: [ex1 modulations..., silence, ex2 modulations..., silence, ...]
    # For exercises with demo=True, record a voice demo first and prepend it (with a short silence).
    # Use a temp dir for all clip WAVs (demos + rendered segments) until we finish rendering.
    with tempfile.TemporaryDirectory() as clip_tmp:
        clip_dir = Path(clip_tmp)
        # full_sequence is the fully expanded processed exercise sequence, that includes
        # the step by steps of what to generate
        full_sequence = []
        for i, exercise in enumerate(exercises):
            if exercise.demo:
                demo_path = clip_dir / f"demo_{i}.wav"
                # recording all the demos before other audio is generated, so that we front-load any required user input
                first_waypoint = exercise.modulation_waypoints[0] if exercise.modulation_waypoints else None
                record_demo(
                    exercise.name,
                    demo_path,
                    sample_rate,
                    first_modulation_waypoint=first_waypoint,
                )
                full_sequence.append({"type": "audio", "path": demo_path})
                full_sequence.append({"type": "silence", "ms": 1500})
            seq = _exercise_to_sequence(exercise)
            if not seq:
                logger.warning("Exercise %r has no modulations; skipping.", exercise.name)
                continue
            full_sequence.extend(seq)
            if i < len(exercises) - 1 and pause_between_exercises_ms > 0:
                full_sequence.append({"type": "silence", "ms": pause_between_exercises_ms})

        if not full_sequence:
            logger.warning("No modulations from any exercise; output will be empty.")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            from .render_wav import silence_wav
            silence_wav(1, sample_rate).export(str(output_path), format="wav")
            logger.info("Wrote empty %s", output_path)
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        clip_paths = gather_audio_clips(
            full_sequence,
            clip_dir,
            soundfont_path=soundfont_path,
            sample_rate=sample_rate,
            music_volume_db=music_db,
            tts_volume_db=tts_db,
        )
        concatenate_wavs(clip_paths, output_path)
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
        help="Output WAV path (default: output/<yaml_stem>.wav)",
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
        output = Path("output") / f"{args.yaml_path.stem}.wav"

    generate_practice_track(
        yaml_path=args.yaml_path,
        output_path=output,
        soundfont_path=soundfont_path,
        tts_volume_db=args.tts_volume_db,
        music_volume_db=args.music_volume_db,
    )


if __name__ == "__main__":
    main()
