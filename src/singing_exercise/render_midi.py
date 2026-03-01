"""
Build MIDI from modulation (pitch, duration) data for piano playback.
One track, piano program; used for rendering to WAV via FluidSynth.
"""
import io
from pathlib import Path
from typing import List, Optional

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
    midi_notes: List[Optional[int]],
    durations_sec: List[float],
    bpm: int,
    tie_from_previous: Optional[List[bool]] = None,
) -> bytes:
    """
    Build a one-track piano MIDI file in memory.
    midi_notes may contain None for rest slots; time advances by durations_sec without a note.
    When tie_from_previous[i] is True and the previous slot was the same pitch, the note is
    merged (no new note_on; duration is added to the previous note).
    Returns MIDI file as bytes (format 1, one track).
    """
    if mido is None:
        raise RuntimeError("mido is required for MIDI generation; install with: pip install mido")

    n = len(midi_notes)
    if tie_from_previous is None:
        tie_from_previous = [False] * n
    elif len(tie_from_previous) != n:
        tie_from_previous = [False] * n  # fallback if length mismatch

    midi = mido.MidiFile(type=1)
    track = mido.MidiTrack()
    midi.tracks.append(track)

    # Set tempo: microseconds per quarter note
    tempo = int(60_000_000 / bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    tps = _ticks_per_second(bpm)
    # Piano = program 0 on channel 0
    track.append(mido.Message("program_change", program=0, time=0))

    pending_ticks = 0
    for i, (note, dur) in enumerate(zip(midi_notes, durations_sec)):
        delta_ticks = int(round(dur * tps))
        tied = tie_from_previous[i] if i < len(tie_from_previous) else False

        if note is not None:
            # Merge with previous note only if tied and same pitch as last note_on
            if tied and track and pending_ticks == 0:
                # Find the last note_off for the same note and extend its time
                last_note = None
                for msg in reversed(track):
                    if msg.type == "note_on" and msg.velocity > 0:
                        last_note = msg.note
                        break
                if last_note == note:
                    # Extend previous note: change the delta of the last note_off
                    for j in range(len(track) - 1, -1, -1):
                        if track[j].type == "note_off" and track[j].note == note:
                            track[j].time += delta_ticks
                            break
                        if track[j].type == "note_on":
                            break
                    continue
            track.append(mido.Message("note_on", note=note, velocity=72, time=pending_ticks))
            track.append(mido.Message("note_off", note=note, velocity=0, time=delta_ticks))
            pending_ticks = 0
        else:
            pending_ticks += delta_ticks

    buf = io.BytesIO()
    midi.save(file=buf)
    return buf.getvalue()


def write_modulation_midi(
    output_path: Path,
    midi_notes: List[Optional[int]],
    durations_sec: List[float],
    bpm: int,
    tie_from_previous: Optional[List[bool]] = None,
) -> None:
    """Write a modulation's MIDI to a file."""
    data = modulation_to_midi_bytes(
        midi_notes, durations_sec, bpm, tie_from_previous=tie_from_previous
    )
    output_path.write_bytes(data)
