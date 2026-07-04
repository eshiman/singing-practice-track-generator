"""
Text-to-speech: generate a WAV from feedback text.
Uses macOS `say` when available, otherwise pyttsx3.
"""
import logging
import platform
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def text_to_wav(
    text: str,
    output_path: Path,
    voice: str | None = None,
    normalize: bool = True,
    sample_rate: int = 44100,
    target_dbfs: float = -6.0,
) -> None:
    """
    Generate speech from text and write a WAV file.
    target_dbfs: peak level in dB when normalize=True (e.g. -6 quieter, -3 louder).
    """
    if not text.strip():
        # Empty text: write a minimal silent WAV so concatenation still works
        from pydub import AudioSegment
        silent = AudioSegment.silent(duration=100, frame_rate=sample_rate)
        silent.export(str(output_path), format="wav")
        return

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Darwin":
        _text_to_wav_say(text, output_path, voice=voice, normalize=normalize, sample_rate=sample_rate, target_dbfs=target_dbfs)
    else:
        _text_to_wav_pyttsx3(text, output_path, normalize=normalize, sample_rate=sample_rate, target_dbfs=target_dbfs)


def _text_to_wav_say(
    text: str,
    output_path: Path,
    voice: str | None = None,
    normalize: bool = True,
    sample_rate: int = 44100,
    target_dbfs: float = -6.0,
) -> None:
    """Use macOS `say` to generate speech, then convert to WAV and optionally normalize."""
    from pydub import AudioSegment

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        text_file = tmp / "feedback.txt"
        aiff_path = tmp / "speech.aiff"
        text_file.write_text(text, encoding="utf-8")

        # macOS 26+ broke the no-voice default for file output; always specify one.
        effective_voice = voice or "Ava (Enhanced)"
        cmd = [
            "say",
            "-v", effective_voice,
            "-o", str(aiff_path),
            "--data-format", f"BEI16@{sample_rate}",
            "-f", str(text_file),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        seg = AudioSegment.from_file(str(aiff_path), format="aiff")
        if seg.frame_rate != sample_rate:
            seg = seg.set_frame_rate(sample_rate)
        if normalize and seg.dBFS > -40:
            change = target_dbfs - seg.dBFS
            seg = seg.apply_gain(change)
        seg.export(str(output_path), format="wav")


def _text_to_wav_pyttsx3(
    text: str,
    output_path: Path,
    normalize: bool = True,
    sample_rate: int = 44100,
    target_dbfs: float = -6.0,
) -> None:
    """Use pyttsx3 to generate speech, then convert to WAV and optionally normalize."""
    from pydub import AudioSegment

    try:
        import pyttsx3
    except ImportError:
        raise RuntimeError(
            "TTS requires pyttsx3 on non-macOS. Install with: pip install pyttsx3"
        ) from None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        wav_tmp = tmp / "speech.wav"
        engine = pyttsx3.init()
        engine.save_to_file(text, str(wav_tmp))
        engine.runAndWait()

        seg = AudioSegment.from_wav(str(wav_tmp))
        if seg.frame_rate != sample_rate:
            seg = seg.set_frame_rate(sample_rate)
        if normalize and seg.dBFS > -40:
            change = target_dbfs - seg.dBFS
            seg = seg.apply_gain(change)
        seg.export(str(output_path), format="wav")
