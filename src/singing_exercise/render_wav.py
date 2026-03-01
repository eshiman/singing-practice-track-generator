"""
Render MIDI to WAV (FluidSynth) and concatenate WAV segments into one file.
Supports mixed sequences: piano, silence, and TTS segments (Phase 3).
"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List

logger = logging.getLogger(__name__)

# Segment descriptor: {"type": "piano", "midi": bytes} | {"type": "silence", "ms": int} | {"type": "tts", "text": str}
SegmentDescriptor = dict


def _db_to_linear_gain(db: float) -> float:
    """Convert dB to linear gain. FluidSynth -g expects 0 < gain < 10."""
    gain = 10 ** (db / 20.0)
    return max(0.01, min(10.0, gain))


def midi_to_wav(
    midi_bytes: bytes,
    soundfont_path: Path,
    output_wav_path: Path,
    sample_rate: int = 44100,
    gain: float | None = None,
) -> None:
    """
    Render MIDI to WAV using FluidSynth (CLI).
    Requires fluidsynth on PATH and a .sf2 soundfont file.
    gain: linear master gain (0 < gain <= 10). If None, FluidSynth default (0.2) is used.
    """
    output_wav_path = Path(output_wav_path).resolve()
    soundfont_path = soundfont_path.resolve()
    with tempfile.NamedTemporaryFile(suffix=".midi", delete=False) as f:
        f.write(midi_bytes)
        midi_path = Path(f.name)
    cmd = [
        "fluidsynth",
        "-ni",
        "-F",
        str(output_wav_path),
        "-r",
        str(sample_rate),
    ]
    if gain is not None:
        cmd.extend(["-g", str(gain)])
    cmd.extend([str(soundfont_path), str(midi_path)])
    try:
        # FluidSynth requires [options] first, then [SoundFonts], then [midifiles].
        result = subprocess.run(
            cmd,
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
    music_volume_db: float = 0.0,
) -> None:
    """
    Render each segment MIDI to WAV, insert silence between segments,
    concatenate, and write to output_path.
    music_volume_db: target level in dB for piano segments (e.g. -6 quieter).
    """
    gain = _db_to_linear_gain(music_volume_db)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ordered: List[Path] = []
        for i, midi_bytes in enumerate(segments_midi):
            seg_wav = tmp / f"seg_{i}.wav"
            midi_to_wav(midi_bytes, soundfont_path, seg_wav, sample_rate, gain=gain)
            ordered.append(seg_wav)
            if i < len(segments_midi) - 1:
                silence = silence_wav(pause_ms, sample_rate)
                silence_path = tmp / f"silence_{i}.wav"
                silence.export(str(silence_path), format="wav")
                ordered.append(silence_path)
        concatenate_wavs(ordered, output_path)


def render_sequence_to_wav(
    sequence: List[SegmentDescriptor],
    soundfont_path: Path,
    output_path: Path,
    tts_generator: Callable[[str, Path], None],
    sample_rate: int = 44100,
    music_volume_db: float = 0.0,
) -> None:
    """
    Render a sequence of piano, silence, and TTS segments into one WAV.
    Each descriptor is {"type": "piano", "midi": bytes} or
    {"type": "silence", "ms": int} or {"type": "tts", "text": str}.
    tts_generator(text, output_path) must write the TTS WAV to output_path.
    music_volume_db: target level in dB for piano segments.
    """
    gain = _db_to_linear_gain(music_volume_db)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ordered: List[Path] = []
        for i, item in enumerate[SegmentDescriptor](sequence):
            kind = item.get("type")
            if kind == "piano":
                midi_bytes = item["midi"]
                seg_wav = tmp / f"piano_{i}.wav"
                midi_to_wav(midi_bytes, soundfont_path, seg_wav, sample_rate, gain=gain)
                ordered.append(seg_wav)
            elif kind == "silence":
                duration_ms = item["ms"]
                silence = silence_wav(duration_ms, sample_rate)
                silence_path = tmp / f"silence_{i}.wav"
                silence.export(str(silence_path), format="wav")
                ordered.append(silence_path)
            elif kind == "tts":
                text = item.get("text", "")
                tts_path = tmp / f"tts_{i}.wav"
                tts_generator(text, tts_path)
                ordered.append(tts_path)
            else:
                raise ValueError(f"Unknown segment type: {kind!r}")
        concatenate_wavs(ordered, output_path)
