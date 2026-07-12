"""
Download YouTube audio, trim to a segment, and pitch-shift for modulation passes.
"""
import hashlib
import logging
import numpy as np
import shutil
import subprocess
import sys
from pathlib import Path
import pyrubberband as rb

from pydub import AudioSegment

from .raw_audio_clip import RawAudioClip
from .raw_youtube_clip import RawYoutubeClip, parse_mm_ss

logger = logging.getLogger(__name__)


def _yt_dlp_executable() -> list[str]:
    """Command prefix to invoke yt-dlp (binary or python module)."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def _build_yt_dlp_cmd(link: str, output_template: str, browser: str | None = None) -> list[str]:
    cmd = [
        *_yt_dlp_executable(),
        "-x",
        "--audio-format", "wav",
        "-o", output_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]
    if browser:
        cmd += ["--cookies-from-browser", browser]
    cmd.append(link)
    return cmd


def download_youtube_audio(link: str, output_dir: Path) -> Path:
    """
    Download best available audio from a YouTube URL as WAV in output_dir.
    Returns path to the downloaded WAV file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "source.%(ext)s")

    # Try without cookies first, then fall back to common browsers.
    browsers_to_try: list[str | None] = [None, "chrome", "safari", "firefox"]
    last_exc: subprocess.CalledProcessError | None = None
    logger.info("Downloading audio from YouTube...")
    for browser in browsers_to_try:
        cmd = _build_yt_dlp_cmd(link, output_template, browser)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            last_exc = None
            break
        except subprocess.CalledProcessError as exc:
            last_exc = exc
            stderr = (exc.stderr or exc.stdout or "").strip()
            if "Sign in to confirm" in stderr or "bot" in stderr.lower():
                logger.debug("yt-dlp needs auth (browser=%s), retrying with next browser", browser)
                continue
            # Non-auth error — don't retry
            raise RuntimeError(
                "yt-dlp failed to download audio. Install yt-dlp "
                "(pip install yt-dlp or brew install yt-dlp)."
                + (f" Details: {stderr}" if stderr else "")
            ) from exc

    if last_exc is not None:
        stderr = (last_exc.stderr or last_exc.stdout or "").strip()
        raise RuntimeError(
            "yt-dlp failed: YouTube requires sign-in. Make sure Chrome, Safari, or Firefox "
            "is installed and you are logged in to YouTube in that browser. "
            + (f" Details: {stderr}" if stderr else "")
        ) from last_exc

    wav_files = sorted(output_dir.glob("source.*"))
    if not wav_files:
        raise RuntimeError(f"yt-dlp did not produce audio in {output_dir}")
    return wav_files[0]


def trim_clip(
    audio: AudioSegment,
    start_time: str,
    end_time: str,
) -> AudioSegment:
    """
    Slice audio between start_time and end_time (mm:ss or mm:ss.fff).

    start is inclusive; end is exclusive (audio at end_time is not included).
    """
    start_sec = parse_mm_ss(start_time)
    end_sec = parse_mm_ss(end_time)
    if end_sec <= start_sec:
        raise ValueError(
            f"end_time ({end_time}) must be after start_time ({start_time})"
        )
    start_ms = round(start_sec * 1000)
    end_ms = round(end_sec * 1000)
    if end_ms > len(audio):
        raise ValueError(
            f"end_time {end_time} ({end_ms} ms) exceeds audio length ({len(audio)} ms)"
        )
    return audio[start_ms:end_ms]


def pitch_shift(segment: AudioSegment, semitones: int) -> AudioSegment:
    if semitones == 0:
        return segment
    samples = np.array(segment.get_array_of_samples()).astype(np.float32)
    samples /= np.iinfo(segment.array_type).max
    shifted = rb.pitch_shift(samples, segment.frame_rate, semitones)
    shifted = np.clip(shifted, -1.0, 1.0)
    dtype = segment.array_type
    shifted_int = (shifted * np.iinfo(dtype).max).astype(dtype)
    return segment._spawn(shifted_int.tobytes())


def _clip_cache_key(clip: RawYoutubeClip) -> str:
    digest = hashlib.sha256(
        f"{clip.link}|{clip.start_time}|{clip.end_time}".encode()
    ).hexdigest()[:16]
    safe_name = "".join(c if c.isalnum() else "_" for c in clip.name)[:40]
    return f"{safe_name}_{digest}"


def prepare_trimmed_clip(clip: RawYoutubeClip, work_dir: Path) -> AudioSegment:
    """
    Download (if needed) and return the trimmed clip segment at original pitch.
    Caches trimmed WAV under work_dir.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _clip_cache_key(clip)
    trimmed_path = work_dir / f"{cache_key}_trimmed.wav"

    if trimmed_path.exists():
        return AudioSegment.from_wav(str(trimmed_path))

    download_dir = work_dir / f"{cache_key}_download"
    download_dir.mkdir(parents=True, exist_ok=True)
    source_path = download_youtube_audio(clip.link, download_dir)
    audio = AudioSegment.from_wav(str(source_path))
    trimmed = trim_clip(audio, clip.start_time, clip.end_time)
    trimmed = trimmed.set_channels(1)
    trimmed.export(str(trimmed_path), format="wav")
    logger.info("Trimmed clip %r -> %s", clip.name, trimmed_path)
    return trimmed


def prepare_trimmed_audio_clip(clip: RawAudioClip, audio_dir: Path, work_dir: Path) -> AudioSegment:
    """
    Load a local MP3 from audio_dir, trim to clip's start/end times, and cache the result.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    digest = hashlib.sha256(
        f"{clip.filename}|{clip.start_time}|{clip.end_time}".encode()
    ).hexdigest()[:16]
    safe_name = "".join(c if c.isalnum() else "_" for c in clip.name)[:40]
    cache_key = f"{safe_name}_{digest}"
    trimmed_path = work_dir / f"{cache_key}_trimmed.wav"

    if trimmed_path.exists():
        return AudioSegment.from_wav(str(trimmed_path))

    source_path = Path(audio_dir) / clip.filename
    if not source_path.exists():
        raise FileNotFoundError(f"Audio file not found: {source_path}")
    audio = AudioSegment.from_mp3(str(source_path))
    trimmed = trim_clip(audio, clip.start_time, clip.end_time)
    trimmed = trimmed.set_channels(1)
    trimmed.export(str(trimmed_path), format="wav")
    logger.info("Trimmed audio clip %r -> %s", clip.name, trimmed_path)
    return trimmed


def render_clip_at_offset(
    trimmed: AudioSegment,
    semitones: int,
    output_path: Path,
    sample_rate: int = 44100,
) -> Path:
    """Write pitch-shifted clip segment to output_path."""
    shifted = pitch_shift(trimmed, semitones)
    if shifted.frame_rate != sample_rate:
        shifted = shifted.set_frame_rate(sample_rate)
    if shifted.channels != 1:
        shifted = shifted.set_channels(1)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shifted.export(str(output_path), format="wav")
    return output_path
