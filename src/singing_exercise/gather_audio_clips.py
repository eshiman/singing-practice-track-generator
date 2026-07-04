"""
Gather WAV clips from a sequence of descriptors.
Uses render_wav (MIDI, silence), generate_voice (TTS), and resamples audio clips.
Caller owns the clip_dir and must call concatenate_wavs after gathering.
"""
import logging
from pathlib import Path
from typing import List

from . import generate_voice
from .render_wav import (
    _db_to_linear_gain,
    midi_to_wav,
    silence_wav,
)

logger = logging.getLogger(__name__)


def gather_audio_clips(
    sequence: List[dict],
    clip_dir: Path,
    *,
    soundfont_path: Path | None,
    sample_rate: int = 44100,
    music_volume_db: float = 0.0,
    tts_volume_db: float = -6.0,
) -> List[Path]:
    """
    Turn each sequence item into a WAV file in clip_dir; return paths in order.

    Sequence items: {"type": "piano", "midi": bytes},
    {"type": "silence", "ms": int}, {"type": "tts", "text": str}, or
    {"type": "audio", "path": Path} (pre-recorded WAV, e.g. voice demo).
    """
    clip_dir = Path(clip_dir)
    gain = _db_to_linear_gain(music_volume_db)
    ordered: List[Path] = []

    for i, item in enumerate(sequence):
        kind = item.get("type")
        if kind == "piano":
            if soundfont_path is None:
                raise ValueError("soundfont_path is required for piano segments")
            midi_bytes = item["midi"]
            out_path = clip_dir / f"piano_{i}.wav"
            midi_to_wav(midi_bytes, soundfont_path, out_path, sample_rate, gain=gain)
            ordered.append(out_path)
        elif kind == "silence":
            duration_ms = item["ms"]
            silence = silence_wav(duration_ms, sample_rate)
            out_path = clip_dir / f"silence_{i}.wav"
            silence.export(str(out_path), format="wav")
            ordered.append(out_path)
        elif kind == "tts":
            text = item.get("text", "")
            out_path = clip_dir / f"tts_{i}.wav"
            try:
                generate_voice.text_to_wav(
                    text,
                    out_path,
                    normalize=True,
                    sample_rate=sample_rate,
                    target_dbfs=tts_volume_db,
                )
            except Exception as exc:
                logger.error("TTS generation failed for %r: %s", text, exc)
                silence = silence_wav(500, sample_rate)
                silence.export(str(out_path), format="wav")
            ordered.append(out_path)
        elif kind == "audio":
            from pydub import AudioSegment

            src_path = Path(item["path"])
            seg = AudioSegment.from_wav(str(src_path))
            if seg.frame_rate != sample_rate:
                seg = seg.set_frame_rate(sample_rate)
            if seg.channels != 1:
                seg = seg.set_channels(1)
            out_path = clip_dir / f"audio_{i}.wav"
            seg.export(str(out_path), format="wav")
            ordered.append(out_path)
        else:
            raise ValueError(f"Unknown segment type: {kind!r}")

    return ordered
