"""
Record a voice demo from the default microphone until the user presses Enter.
Used when an exercise has demo=True: the recording is inserted before the exercise in the track.
Prompts for Enter when ready to start, then Enter again when done. Uses PyAudio and wave.
"""
import logging
import math
import sys
import threading
import time
from array import array
from pathlib import Path
from struct import pack

import pyaudio
import wave

from .keys import parse_note, note_to_midi

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100
CHANNELS = 1
THRESHOLD = 300  # trim: treat samples below this as silence
TARGET_PEAK = int(32768 * 0.9)  # only scale down if peak above this (Option A: never scale up)


def _trim_one_side(snd_data: array) -> array:
    r = array("h")
    started = False
    for i in snd_data:
        if not started and abs(i) > THRESHOLD:
            started = True
        if started:
            r.append(i)
    return r


def trim(snd_data: array) -> array:
    snd_data = _trim_one_side(snd_data)
    snd_data = array("h", reversed(snd_data))
    snd_data = _trim_one_side(snd_data)
    snd_data = array("h", reversed(snd_data))
    return snd_data


def scale_down_if_needed(snd_data: array) -> array:
    if len(snd_data) == 0:
        return snd_data
    peak = max(abs(i) for i in snd_data)
    if peak <= TARGET_PEAK:
        return snd_data
    factor = TARGET_PEAK / peak
    return array("h", (int(i * factor) for i in snd_data))


def add_silence(snd_data: array, seconds: float) -> array:
    silence_len = int(seconds * RATE)
    silence = array("h", [0] * silence_len)
    r = array("h", silence)
    r.extend(snd_data)
    r.extend(silence)
    return r


def _midi_to_hz(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _play_major_triad_cue(
    key_name: str,
    duration_sec: float = 1.0,
    sample_rate: int = RATE,
) -> None:
    """
    Play a short major-triad cue rooted at key_name through default output.
    """
    pc, octv = parse_note(key_name)
    root_midi = note_to_midi(pc, octv)
    freqs = [_midi_to_hz(root_midi + interval) for interval in (0, 4, 7)]
    n_samples = max(1, int(sample_rate * duration_sec))
    fade_len = max(1, int(sample_rate * 0.03))
    amplitude = 0.25

    samples = array("h")
    for i in range(n_samples):
        t = i / sample_rate
        sample = sum(math.sin(2 * math.pi * freq * t) for freq in freqs) / len(freqs)

        # Short fade-in/out prevents clicks at the boundaries.
        env = 1.0
        if i < fade_len:
            env = i / fade_len
        elif i > n_samples - fade_len:
            env = max(0.0, (n_samples - i) / fade_len)

        value = int(max(-1.0, min(1.0, sample * amplitude * env)) * 32767)
        samples.append(value)

    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=sample_rate,
        output=True,
    )
    try:
        stream.write(samples.tobytes())
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def record_demo(
    exercise_name: str,
    output_path: Path,
    sample_rate: int = RATE,
    first_modulation_waypoint: str | None = None,
) -> Path:
    """
    Prompt the user to press Enter when ready, then record from the default microphone until they press Enter again,
    and save as WAV at output_path. Returns output_path.

    Uses PyAudio. Trims leading/trailing silence and pads with 0.5 s silence; only scales down if clipping.
    """
    if sample_rate != RATE:
        raise ValueError(f"record_demo expects sample_rate={RATE}, got {sample_rate}")
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if first_modulation_waypoint:
        print(f'Playing starting-key triad cue: {first_modulation_waypoint}', flush=True)
        try:
            _play_major_triad_cue(first_modulation_waypoint, sample_rate=sample_rate)
        except Exception:
            logger.exception("Failed to play starting-key triad cue; continuing.")

    print(f'Record a demo for "{exercise_name}". Press Enter when ready to start.', flush=True)
    sys.stdout.flush()
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

    stop_event = threading.Event()
    chunks: list[bytes] = []
    record_error: list = []

    def record_worker() -> None:
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            while not stop_event.is_set():
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if stop_event.is_set():
                    break
                chunks.append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            record_error.append(e)

    thread = threading.Thread(target=record_worker, daemon=True)
    thread.start()
    time.sleep(0.4)

    msg = "Recording... Press Enter when done."
    print(msg, flush=True)
    sys.stdout.flush()

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    stop_event.set()
    thread.join(timeout=5.0)

    if record_error:
        raise RuntimeError(
            "Microphone recording failed. Ensure a default input device is available."
        ) from record_error[0]

    if not chunks:
        empty = array("h", [0] * (RATE // 10))
        data = pack("<" + "h" * len(empty), *empty)
    else:
        raw = b"".join(chunks)
        snd_data = array("h")
        snd_data.frombytes(raw)
        snd_data = trim(snd_data)
        snd_data = scale_down_if_needed(snd_data)
        snd_data = add_silence(snd_data, 0.5)
        data = pack("<" + "h" * len(snd_data), *snd_data)

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(data)

    logger.info("Saved demo to %s", output_path)
    return output_path
