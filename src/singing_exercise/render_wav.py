"""
Render MIDI to WAV (FluidSynth) and concatenate WAV segments into one file.
"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def midi_to_wav(
    midi_bytes: bytes,
    soundfont_path: Path,
    output_wav_path: Path,
    sample_rate: int = 44100,
) -> None:
    """
    Render MIDI to WAV using FluidSynth (CLI).
    Requires fluidsynth on PATH and a .sf2 soundfont file.
    """
    output_wav_path = Path(output_wav_path).resolve()
    soundfont_path = soundfont_path.resolve()
    with tempfile.NamedTemporaryFile(suffix=".midi", delete=False) as f:
        f.write(midi_bytes)
        midi_path = Path(f.name)
    try:
        # FluidSynth requires [options] first, then [SoundFonts], then [midifiles].
        # -F and -r are only valid before any soundfont/midi args.
        result = subprocess.run(
            [
                "fluidsynth",
                "-ni",
                "-F",
                str(output_wav_path),
                "-r",
                str(sample_rate),
                str(soundfont_path),
                str(midi_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(
            f"FluidSynth failed: {e.stderr or e.stdout or 'no output'}"
        ) from e
    finally:
        midi_path.unlink(missing_ok=True)

    if not output_wav_path.exists():
        stderr = (result.stderr or "").strip()
        raise FileNotFoundError(
            f"FluidSynth did not create {output_wav_path}. "
            "Ensure FluidSynth is built with libsndfile support (e.g. brew install fluid-synth). "
            f"stderr: {stderr}"
        )


def silence_wav(duration_ms: int, sample_rate: int = 44100) -> "AudioSegment":
    """Create a silent WAV segment of given duration in milliseconds."""
    from pydub import AudioSegment

    return AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)


def concatenate_wavs(
    wav_paths: List[Path],
    output_path: Path,
) -> None:
    """Concatenate WAV files in order and write to output_path."""
    from pydub import AudioSegment

    combined = None
    for p in wav_paths:
        seg = AudioSegment.from_wav(str(p))
        combined = seg if combined is None else combined + seg
    if combined is not None:
        combined.export(str(output_path), format="wav")


def render_segments_to_wav(
    segments_midi: List[bytes],
    pause_ms: int,
    soundfont_path: Path,
    output_path: Path,
    sample_rate: int = 44100,
) -> None:
    """
    Render each segment MIDI to WAV, insert silence between segments,
    concatenate, and write to output_path.
    """
    from pydub import AudioSegment

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ordered: List[Path] = []
        for i, midi_bytes in enumerate(segments_midi):
            seg_wav = tmp / f"seg_{i}.wav"
            midi_to_wav(midi_bytes, soundfont_path, seg_wav, sample_rate)
            ordered.append(seg_wav)
            if i < len(segments_midi) - 1:
                silence = silence_wav(pause_ms, sample_rate)
                silence_path = tmp / f"silence_{i}.wav"
                silence.export(str(silence_path), format="wav")
                ordered.append(silence_path)
        concatenate_wavs(ordered, output_path)
