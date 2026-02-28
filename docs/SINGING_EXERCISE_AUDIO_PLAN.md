# Plan: Singing Exercise Audio Generator

## Overview

A script (or small application) that turns structured singing exercises into audio files. Each exercise defines scale-degree patterns (e.g. 8-5-3-1), a modulation path (waypoints; the pattern is played in every key along the path, by semitones between waypoints), timing, and optional spoken feedback. The output is a single audio file: piano playing the pattern in each key, with pauses and (later) TTS cues.

---

## 1. Exercise Model & Input Format

### 1.1 What We Need to Represent

From your example, an exercise has:

- **Pitch pattern**: scale degrees in order (e.g. `8, 5, 3, 1`) and direction (↑ ↘ ↘ ↓).
- **Syllable / vowel**: e.g. "Wee" (for display/lyrics; optional for audio).
- **Modulation path (waypoints)**: an ordered list of keys that define a path. The exercise is played in **every key along that path**: from waypoint 1 to waypoint 2 by semitones (down or up), then from waypoint 2 to waypoint 3, and so on. Example: `["D4", "G3", "Bb4", "F3"]` means play from D4 down to G3 (D4, Db4, C4, … G3), then from G3 up to Bb4, then from Bb4 down to F3—many keys in total, not just four.
- **Timing**: **BPM** (beats per minute) within a single iteration of the pattern, with notes as **8th notes** (default 70 BPM); plus **pause duration** between key changes (or after each full run).
- **Feedback cues** (phase 2): text plus placement by key and occurrence in the resolved key sequence (e.g. after the 1st time we play D4, after the 1st time we play Db4).

### 1.2 Proposed Input Format

- **Option A – Structured text YAML**  
  - Define: `scale_degrees`, `syllable`, `modulation_waypoints` (ordered list of **waypoints**; full key sequence = semitone steps between consecutive waypoints, down or up), `bpm` (default 70), `note_value` (default 8th note), `pause_between_keys_ms`, and `feedback` list. Each feedback entry: `key`, `which_occurrence` (Nth time that key appears in the resolved sequence), `text`.

**Example input YAML** for the exercise (↑ ↘ ↘ ↓, 8-5-3-1, Wee, with feedback). Here `modulation_waypoints` is a list of **waypoints**: the exercise is played in every key along the path (semitones between waypoints)—e.g. D4 down to G3, then G3 up to Bb4, then Bb4 down to F3.

```yaml
name: "Wee 8-5-3-1 (down)"
scale_degrees: [8, 5, 3, 1]
syllable: "Wee"
# Waypoints: path = D4 → … → G3 → … → Bb4 → … → F3 (semitones between each pair)
modulation_waypoints: ["D4", "G3", "Bb4", "F3"]
bpm: 70
note_value: 8th
pause_between_keys_ms: 2000

feedback:
  - key: "D4"
    which_occurrence: 1
    text: |
      Don't push so much, open a little more but not much. Lower intensity.
      To get the ees you need to do 3 things: drop the jaw a bit, keep the tongue in the right position feel the yawny space come in and not so loud!
  - key: "Db4"
    which_occurrence: 1
    text: "Still lower the intensity a bit."
```

---

## 2. Music Logic

### 2.1 Scale Degrees → Pitches

- **Scale degrees**: 1 = tonic, 2–7 = scale steps, 8 = octave above tonic.
- **Mapping**: For a given key (e.g. D4), build a major (or chosen) scale and map each degree to a pitch (e.g. 8 → D5, 5 → A4, 3 → F#4, 1 → D4).
- **Octave**: “8” is typically the octave above the stated key (e.g. D5 if key is D4); degrees 1–7 in the same octave as the key, unless you add explicit octave rules.

### 2.2 Key and Modulation

- **Key representation**: Use a standard encoding (e.g. note name + accidental + octave: `D4`, `Db4`, `F#3`).
- **Modulation waypoints**: The `modulation_waypoints` field is an ordered list of **waypoints**. The full key sequence is built by walking **by semitones** between consecutive waypoints (down or up as needed). Example: `["D4", "G3", "Bb4", "F3"]` → segment 1: D4 down to G3 (D4, Db4, C4, B3, Bb3, A3, Ab3, G3); segment 2: G3 up to Bb4; segment 3: Bb4 down to F3. The exercise is played once in **every** key in that resolved sequence.
- **Same pattern in each key**: For each key in the resolved sequence, generate the same scale-degree → pitch sequence, then concatenate with a pause.

### 2.3 Rhythm and Timing

- **Tempo (BPM)**: Beats per minute apply to **one iteration** of the exercise (one run through the pattern, e.g. 8 → 5 → 3 → 1). Default: **70 BPM**.
- **Note value**: Notes in the pattern are **8th notes** by default (each note = half a beat in 4/4). So at 70 BPM, each 8th note = (60 / 70) × 0.5 ≈ 0.43 s. The note value can be overridden per exercise if needed (e.g. quarter notes).
- **Pause**: Single “pause between keys” (or “pause after each run”) in ms or seconds—unchanged by BPM; still an absolute duration.
- **Order**: For each key: play the pattern at the given BPM with 8th-note rhythm, then insert the pause, then next key.

---

## 3. Audio Generation

### 3.1 Piano Sound

- **MIDI + soundfont**: Generate MIDI (note on/off, pitch, duration) then render to WAV using a soundfont (e.g. FluidSynth, or a library that wraps it). Gives good piano quality and small representation.

### 3.2 Pipeline: Segment-Based (Multiple MIDI → WAV → Concatenate)

Use **one MIDI (and thus one WAV) per logical segment** (e.g. per key, or per key + pause), then **concatenate** the WAVs into the final file. This keeps spacing adjustable and makes it straightforward to insert TTS clips between segments.

1. **Load** exercise from the YAML file (§1.2).
2. **Resolve keys**: Expand `modulation_waypoints` into the full key sequence by stepping by semitones between consecutive waypoints (e.g. ["D4", "G3", "Bb4", "F3"] → D4, Db4, …, G3, …, Bb4, …, F3).
3. **For each key** (each segment):  
   - Map scale degrees (8,5,3,1) to MIDI note numbers (or frequencies).  
   - Build a sequence of (pitch, duration) for that key only.  
   - **Option A**: One MIDI per key (notes only) → one WAV per key; generate a separate “silence” WAV of length `pause_between_keys_ms` and concatenate [key1.wav, silence.wav, key2.wav, silence.wav, …].  
   - **Option B**: One MIDI per key that includes a rest/pause at the end → one WAV per key (notes + pause), then concatenate [key1.wav, key2.wav, …].  
   - In both cases, **spacing is programmable**: change pause length by regenerating only the silence segment or the “with pause” MIDI, or by editing the assembly list.
4. **Render each segment**:  
   - Convert each key’s (pitch, duration) list to a MIDI file, then MIDI → WAV (soundfont).
5. **Assembly**:  
   - Build an ordered list of WAV segments (e.g. `[key1.wav, silence.wav, key2.wav, silence.wav, …]`).  
   - Concatenate with an audio library (e.g. `pydub`) into one WAV.
6. **Export**: Write one final audio file (e.g. WAV or MP3) per exercise.

**Why segment-based?**  
- **Spacing**: Pause duration can be changed without rebuilding one long MIDI; you only regenerate silence or the per-key MIDIs that include the rest.  
- **TTS insertion**: The final assembly is a list of segments. To add voice feedback, insert TTS WAV clips at the right positions in that list (e.g. after key N’s segment), then concatenate. No need to mix speech into a single MIDI timeline.

### 3.3 Future: Spoken Feedback (TTS)

- **Model**: The `feedback` list: each entry has `key`, `which_occurrence` (after the Nth time that key appears in the resolved key sequence), and `text`.
- **Placement**: When building the segment list for assembly, insert a TTS WAV after the Nth occurrence of the given key. Each feedback item → generate TTS for this text → get short WAV → add to the segment list at that position.
- **TTS**: Use a system or cloud TTS (e.g. macOS `say`, or a Python TTS library, or an API). Input: feedback text; output: short WAV. Normalize level so it’s audible but not overwhelming.
- **Assembly**: Concatenate the segment list (piano WAV | pause WAV | TTS WAV in order) into one final WAV so the file has piano, then pause, then spoken feedback where specified, then next key, etc.

---

## 4. Implementation Phases

**Input**: The exercise is always defined by the YAML file format described in §1.2 (no custom parsers or other input formats). Each phase can be validated independently.

**Phases 1 and 2** must ignore the `feedback` section of the YAML; only Phase 3 reads and uses it.

---

### Phase 1 – Load YAML and Log the Generation Plan

**Goal**: Validate that the exercise model, key resolution, and segment plan are correct—without generating any audio. Input: path to the YAML file. Output: logs that describe exactly what would be generated and how it would be assembled.

1. **Load YAML**: Read the exercise file (e.g. with `PyYAML`) into the exercise model. Use only: `name`, `scale_degrees`, `syllable`, `modulation_waypoints`, `bpm`, `note_value`, `pause_between_keys_ms`. Ignore `feedback` entirely.
2. **Resolve key sequence**: From `modulation_waypoints`, compute the full ordered list of keys (semitones between consecutive waypoints). Log that list (e.g. `D4, Db4, C4, …, G3, …, Bb4, …, F3`).
3. **Key/scale logic**: For a given key (e.g. D4), map scale degrees 1–8 to concrete pitches (MIDI note numbers or note names). No MIDI or WAV files yet—this is used only to describe what will be played.
4. **Per-key segment description**: For each key in the resolved sequence, compute note duration from BPM + note value (e.g. 8th note at 70 BPM) and produce a *description* of that segment: which pitches, durations, and the pause length after it. Do not write MIDI or WAV.
5. **Log the full plan**: Print (or write to a log) something like:
   - Total number of keys (segments).
   - For each segment: key name; list of (pitch, duration) for the pattern; pause duration after this segment.
   - Final assembly order: e.g. `[segment_1, silence_1, segment_2, silence_2, …]` (or “segment N = key N notes + pause” if pause is baked per segment).

**Validation**: Run the script on an example YAML. Inspect the logs to confirm the key sequence, the pitch list per key, and the assembly order match the intended exercise. No sound libraries (FluidSynth, pydub) are required in Phase 1.

---

### Phase 2 – MIDI → WAV and Concatenation

**Goal**: Add the Python sound-processing stack. Input: same YAML file (still ignoring `feedback`). Output: a single WAV file with piano playing the pattern in each key and pauses between keys.

1. **Reuse Phase 1**: Load YAML, resolve keys, and build the per-key (pitch, duration) lists and pause durations. No change to the model or key resolution.
2. **MIDI generation**: For each key segment, turn its (pitch, duration) list into a MIDI file (one track, piano). Optionally generate a separate “silence” WAV of length `pause_between_keys_ms` (or bake the rest into each key’s MIDI and render one WAV per key that includes the pause).
3. **MIDI → WAV**: Use a soundfont renderer (e.g. FluidSynth / `pyfluidsynth` or subprocess to `fluidsynth` CLI) to render each MIDI segment to a WAV file.
4. **Assembly**: Build the ordered list of WAV segments (key1.wav, silence.wav, key2.wav, … or key1_with_pause.wav, key2_with_pause.wav, …) and concatenate them into one WAV using an audio library (e.g. `pydub`).
5. **CLI**: Input = path to exercise YAML (and optionally output path); output = one final audio file (e.g. WAV).

**Validation**: Run on the same example YAML. Confirm the output WAV contains the correct number of key segments, correct timing (BPM, pause length), and no spoken feedback. The segment-based pipeline is in place for Phase 3.

---

### Phase 3 – Spoken Feedback (TTS)

**Goal**: Read the `feedback` section from the YAML and produce a final WAV that includes spoken cues at the right positions.

1. **Load feedback**: When loading the YAML, now also read the `feedback` list (each entry: `key`, `which_occurrence`, `text`).
2. **Placement**: When building the segment list for assembly, for each feedback item insert a TTS WAV *after* the Nth occurrence of the given key in the resolved key sequence (e.g. after the 1st time we play D4).
3. **TTS**: For each feedback item, generate speech from `text` (e.g. macOS `say`, or `pyttsx3`, or a cloud TTS API) and save a short WAV. Normalize level so it is audible but not overwhelming.
4. **Assembly with speech**: Build the segment list as (piano WAV | pause WAV | TTS WAV as needed). Insert each TTS WAV at the correct position (after the corresponding key’s segment), then concatenate all segments into one final WAV with the same library used in Phase 2.

**Validation**: Run on an exercise YAML that includes `feedback` entries. Confirm the output WAV has piano, pauses, and spoken feedback at the expected keys/occurrences.

---

### Phase 4 – Nice-to-haves

- **Config**: Default soundfont path, default TTS voice, output directory.

---

## 5. Tech Stack Suggestions

- **Language**: Python is a good fit (MIDI libs, audio I/O, YAML/JSON, TTS bindings).
- **MIDI**: `mido` or `midiutil` for creating MIDI.
- **MIDI → WAV**: FluidSynth (e.g. `pyfluidsynth`) or subprocess to `fluidsynth` CLI; need one piano soundfont (e.g. from MuseScore or FluidSynth project).
- **Audio assembly**: `pydub` for concatenating and mixing WAV segments (piano + silence + TTS).
- **TTS (later)**: `pyttsx3` (offline), or `gTTS` / cloud API for more natural voice.

---

## 6. File and Repo Layout (Suggested)

- **Config**: Default paths for soundfont, output dir, TTS voice.
- **Exercise format**: One directory for exercise files (YAML/JSON and/or .txt in your format); one schema or example per format.
- **Output**: Generated audio files (e.g. `output/<exercise_name>_<timestamp>.wav`).
- **Docs**: This plan; later, a short “exercise format reference” and “how to add feedback” guide.

---

## 7. Example Exercise (Structured)

A simpler example: two waypoints so the path is a single run down by semitones (D4 down to B3).

```yaml
name: "Wee 8-5-3-1"
scale_degrees: [8, 5, 3, 1]
syllable: "Wee"
# Waypoints: path = D4 down to B3 (D4, Db4, C4, B3)
modulation_waypoints: ["D4", "B3"]
bpm: 70
note_value: 8th
pause_between_keys_ms: 2000

feedback:
  - key: "D4"
    which_occurrence: 1
    text: "Don't push so much, open a little more but not much. Lower intensity."
  - key: "Db4"
    which_occurrence: 1
    text: "Still lower the intensity a bit."
```

This would yield: piano playing 8-5-3-1 in D4 → pause → Db4 → pause → C4 → pause → B3, with spoken lines after the first D4 and after the first Db4 once TTS is implemented.

---

## 8. Success Criteria

- **Phase 1**: Running the script on a YAML exercise file produces logs that correctly list the resolved key sequence, the (pitch, duration) plan per key, and the assembly order—with no audio output. Validating the logs confirms the music logic.
- **Phase 2**: Running on the same YAML (without using `feedback`) produces a single WAV with piano and pauses in the correct order and timing.
- **Phase 3**: Running on a YAML that includes `feedback` entries produces a WAV that includes spoken feedback at the right key/occurrence positions.

Next step: implement Phase 1 (load YAML, resolve keys, log the generation plan) in this repo.
