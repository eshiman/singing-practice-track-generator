"""
Build MIDI from modulation (pitch, duration) data for piano playback.
One track, piano program; used for rendering to WAV via FluidSynth.
"""
import io
from pathlib import Path
from typing import List

try:
    import mido
except ImportError:
    mido = None

# Default ticks per quarter note (matches many MIDI files)
TICKS_PER_QUARTER = 480


def _ticks_per_second(bpm: int) -> float:
    """Ticks per second at given BPM (480 ticks per quarter)."""
    return TICKS_PER_QUARTER * (bpm / 60.0)


def modulation_to_midi_bytes(
    midi_notes: List[int],
    durations_sec: List[float],
    bpm: int,
) -> bytes:
    """
    Build a one-track piano MIDI file in memory.
    Returns MIDI file as bytes (format 1, one track).
    """
    if mido is None:
        raise RuntimeError("mido is required for MIDI generation; install with: pip install mido")

    midi = mido.MidiFile(type=1)
    track = mido.MidiTrack()
    midi.tracks.append(track)

    # Set tempo: microseconds per quarter note
    tempo = int(60_000_000 / bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    tps = _ticks_per_second(bpm)
    # Piano = program 0 on channel 0
    track.append(mido.Message("program_change", program=0, time=0))

    for note, dur in zip(midi_notes, durations_sec):
        delta_ticks = int(round(dur * tps))
        track.append(mido.Message("note_on", note=note, velocity=72, time=0))
        track.append(mido.Message("note_off", note=note, velocity=0, time=delta_ticks))

    buf = io.BytesIO()
    midi.save(file=buf)
    return buf.getvalue()


def write_modulation_midi(
    output_path: Path,
    midi_notes: List[int],
    durations_sec: List[float],
    bpm: int,
) -> None:
    """Write a modulation's MIDI to a file."""
    data = modulation_to_midi_bytes(midi_notes, durations_sec, bpm)
    output_path.write_bytes(data)
