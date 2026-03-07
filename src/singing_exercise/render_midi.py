"""
Build MIDI from modulation (pitch, duration) data for piano playback.
One track, piano program; used for rendering to WAV via FluidSynth.
"""
import io
from pathlib import Path
from typing import List, Optional, Union

try:
    import mido
except ImportError:
    mido = None

# Default ticks per quarter note (matches many MIDI files)
TICKS_PER_QUARTER = 480


def _ticks_per_second(bpm: int) -> float:
    """Ticks per second at given BPM (480 ticks per quarter)."""
    return TICKS_PER_QUARTER * (bpm / 60.0)


# Per-slot: single pitch (int), rest (None), or chord (list of int)
MidiSlot = Optional[Union[int, List[int]]]


def modulation_to_midi_bytes(
    midi_notes: List[MidiSlot],
    durations_sec: List[float],
    bpm: int,
    tie_from_previous: Optional[List[bool]] = None,
) -> bytes:
    """
    Build a one-track piano MIDI file in memory.
    midi_notes may contain None (rest), int (single note), or list of int (chord).
    When tie_from_previous[i] is True and the previous slot was the same pitch/chord, the note(s)
    are merged (no new note_on; duration is added to the previous).
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

    def _notes_list(slot: MidiSlot) -> Optional[List[int]]:
        if slot is None:
            return None
        return [slot] if isinstance(slot, int) else slot

    pending_ticks = 0
    for i, (note_slot, dur) in enumerate(zip(midi_notes, durations_sec)):
        delta_ticks = int(round(dur * tps))
        tied = tie_from_previous[i] if i < len(tie_from_previous) else False
        notes = _notes_list(note_slot)

        if notes is not None:
            # Tie: extend previous chord/note only if same set of pitches
            if tied and track and pending_ticks == 0 and notes:
                last_notes: List[int] = []
                for msg in reversed(track):
                    if msg.type == "note_off":
                        last_notes.append(msg.note)
                    elif msg.type == "note_on" and msg.velocity > 0:
                        break
                if sorted(last_notes) == sorted(notes):
                    count = 0
                    for j in range(len(track) - 1, -1, -1):
                        if track[j].type == "note_off" and track[j].note in notes:
                            track[j].time += delta_ticks
                            count += 1
                            if count == len(notes):
                                break
                    continue
            # Note on: all chord notes at once (only first message gets pending_ticks; rest delta 0)
            for j, note in enumerate(notes):
                track.append(mido.Message("note_on", note=note, velocity=72, time=pending_ticks if j == 0 else 0))
            # Note off: all stop together (only first message gets delta_ticks; rest delta 0)
            for j, note in enumerate(notes):
                track.append(mido.Message("note_off", note=note, velocity=0, time=delta_ticks if j == 0 else 0))
            pending_ticks = 0
        else:
            pending_ticks += delta_ticks

    buf = io.BytesIO()
    midi.save(file=buf)
    return buf.getvalue()


def write_modulation_midi(
    output_path: Path,
    midi_notes: List[MidiSlot],
    durations_sec: List[float],
    bpm: int,
    tie_from_previous: Optional[List[bool]] = None,
) -> None:
    """Write a modulation's MIDI to a file."""
    data = modulation_to_midi_bytes(
        midi_notes, durations_sec, bpm, tie_from_previous=tie_from_previous
    )
    output_path.write_bytes(data)
