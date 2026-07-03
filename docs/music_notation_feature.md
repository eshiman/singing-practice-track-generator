# Plan: Phrase Encoding with Rhythm, Rests, and Accidentals

**Status:** Implemented. The pipeline supports `note_values`, rest `"R"`, and accidentals `b`/`#` in scale degrees.

## Goal

Encode musical phrases in the exercise YAML so we can generate exercises that incorporate **rhythm** (per-note durations), **rests**, and **accidentals** (flat/sharp on scale degrees). This turns the format from “scale-degree patterns with one global note value” into a small phrase notation.

---

## Summary of the Three Features

| Feature | Description |
|--------|-------------|
| **1. `note_values` list** | Optional list of durations, one per scale-degree slot (including rests). Numeric: `8` = eighth, `4` = quarter, `2` = half, `16` = sixteenth. Add a trailing dot for dotted notes: `"4."` = dotted quarter (1.5×), `"8."` = dotted eighth, etc. **Triplets:** `"8t"` = eighth-note triplet (3 in the time of one quarter), `"4t"` = quarter-note triplet (3 in the time of a half), `"16t"` = sixteenth-note triplet (3 in the time of one eighth). **Ties:** Use `~` to tie notes: preceding note ends with `~` (e.g. `"4~"`), following note starts with `~` (e.g. `"~8t"`); a middle note in a tie is `"~8t~"`. Tied slots become one sustained note. When present, overrides the single `note_value` for that exercise. |
| **2. Rest "R"** | Allow `"R"` in the scale-degrees list to mean a rest. The rest’s duration comes from the corresponding entry in `note_values`, or from `note_value` when `note_values` is not used. |
| **3. Accidentals b / #** | Allow scale degrees to be written with `b` (flat) or `#` (sharp) **before** the degree, e.g. `"b3"`, `"#5"` (standard music convention). These adjust the diatonic pitch by one semitone down or up. |

**Backward compatibility:** Existing YAML that uses only `scale_degrees` (integers 1–8) and a single `note_value` continues to work unchanged. For the new phrase format, **all scale-degree entries are written as quoted strings** (e.g. `"8"`, `"5"`, `"R"`, `"b3"`, `"1"`) for consistency.

---

## Current State (What Exists Today)

- **`scale_degrees`**: List of integers 1–8 only. Parsed in `RawExercise.from_dict`, used in `process_exercise.expand_exercise_to_modulations`, and mapped to MIDI in `scale.scale_degrees_to_midi`.
- **`note_value`**: Single string per exercise (e.g. `"8th"`). One duration is computed in `timing.note_duration_seconds(bpm, note_value)` and applied to every note in the pattern.
- **Rests / accidentals**: Not implemented. No "R" and no "b3"/"#5" style parsing.

So none of the three features are implemented yet; the plan below is the path to add them.

---

## Design Choices and Suggestions

### 1. `note_values` vs `note_value`

- **Rule:** If `note_values` is present, it **must** have the same length as `scale_degrees`. Each index is the duration for that slot (note or rest). If only `note_value` is present, keep current behavior: one duration for all slots.
- **Numeric vs string:** Using numbers (`8`, `4`, `2`, `16`) keeps YAML compact and matches your spec. We can support both numeric and string (e.g. `"8th"`, `"quarter"`) in the implementation for readability; the plan below uses numeric as the canonical form and maps 2→half, 4→quarter, 8→eighth, 16→sixteenth.

### 2. Scale-degree list: all entries as quoted strings

- In YAML, `scale_degrees` entries are **all quoted strings**: `"1"`–`"8"` for natural degrees, `"R"` for rest, and `"b3"`, `"#5"` etc. for accidentals (accidental **before** the degree, as in standard music notation). The internal representation is a list of “slots,” each slot being either a (degree, accidental) or a rest. Parsing normalizes so that e.g. `"8"` → degree 8 natural; for backward compatibility, bare integers 1–8 from existing YAML can still be accepted and treated the same.

### 3. Rest "R"

- "R" is a rest: no pitch, but it still occupies time. Duration comes from:
  - the same-index entry in `note_values` when `note_values` is used, or  
  - the single `note_value` when it’s not.
- In the (pitch, duration) pipeline, a rest is represented as a slot with **no MIDI note** (e.g. `None`) and a duration. The MIDI renderer advances time by that duration without emitting note_on/note_off.

### 4. Accidentals b / # (before the degree)

- **Meaning:** In the key’s major scale, degree N has a diatonic pitch. `"bN"` = one semitone lower, `"#N"` = one semitone higher (accidental **before** the degree, standard in music). Example: in C, `"3"` = E, `"b3"` = Eb, `"#3"` = E# (F).
- **Representation:** After parsing, each non-rest slot is (degree 1–8, accidental: natural / flat / sharp). The scale module then computes MIDI as: diatonic pitch + (−1 for flat, +1 for sharp).

### 5. Optional: allow `note_value` as fallback when `note_values` is partial

- **Recommendation:** Keep the rule strict: either use **only** `note_value` (same duration for all), or **only** `note_values` (length must match `scale_degrees`). No mixing (e.g. “note_values for some, note_value for the rest”) in v1 to avoid ambiguity. We can relax later if needed.

---

## Step-by-Step Implementation Plan

### Step 1: Extend timing to support numeric note values

**File:** `src/singing_exercise/timing.py`

- Add a function (or extend `note_duration_seconds`) so that a **numeric** note value is supported:
  - Input: `bpm`, and either a number (e.g. `8`, `4`, `2`, `16`) or the existing string (`"8th"`, `"quarter"`, etc.).
  - Convention: number = denominator of the note type in 4/4: `2` → half note (2 beats), `4` → quarter (1 beat), `8` → eighth (0.5 beats), `16` → sixteenth (0.25 beats).
- Keep backward compatibility: when the exercise uses only `note_value` (string), existing call sites continue to work.

**Checklist:** Unit test or manual check: for a given BPM, `2` gives double the duration of `4`, and `4` double that of `8`.

---

### Step 2: Parse and normalize `scale_degrees` (rest + accidentals)

**Files:** `src/singing_exercise/raw_exercise.py`, and a small shared parser (e.g. `scale_degree_parser` or inside `scale.py`).

- **YAML:** Each element of `scale_degrees` is a string (all in quotes): `"1"`–`"8"` → natural scale degree; `"R"` → rest; `"b3"`, `"#5"` → degree with flat or sharp (accidental before the number). For backward compatibility, accept bare integers 1–8 and treat as natural.
- **Internal representation:** Two options:
  - **Option A:** Keep a single list of “slots”: each slot is either `("R", None)` or `(degree: int, accidental: "natural" | "flat" | "sharp")`. Downstream code branches on rest vs pitch.
  - **Option B:** Keep a list of pitch slots only for “notes” and a separate structure for rest positions; this gets messy when we also have per-slot durations, so **Option A is recommended**.
- **Parsing function:** e.g. `parse_scale_degree_entry(entry) -> ("rest", None) | ("degree", degree_int, accidental)`.
- **RawExercise:** Continue to store `scale_degrees` as the list as loaded from YAML (mixed int/str). Add a helper or property that returns the list of parsed slots so the rest of the codebase uses one canonical form.

**Checklist:** Parsing tests for `"8"`, `"R"`, `"b3"`, `"#5"`, and invalid input (e.g. `"9"`, `"3x"`) with clear errors.

---

### Step 3: Resolve durations per slot (`note_value` vs `note_values`)

**File:** `src/singing_exercise/raw_exercise.py` (and possibly a small helper in `timing.py`).

- When loading an exercise:
  - If `note_values` is present: validate `len(note_values) == len(scale_degrees)`. Store `note_values` (list of numbers or strings).
  - If only `note_value` is present: keep current behavior; we’ll derive one duration per slot in Step 4.
- Add a method or function that, given `bpm`, `note_value`, optional `note_values`, and the length of `scale_degrees`, returns a list of **durations in seconds** (one per slot). When `note_values` is used, convert each entry (e.g. 2, 4, 8, 16) to seconds using the extended timing logic from Step 1.

**Checklist:** For an exercise with `scale_degrees: ["8", "5", "R", "1"]` and `note_values: [8, 4, 4, 2]`, the duration list is four elements: eighth, quarter, quarter (rest), half.

---

### Step 4: Scale module: from parsed slots to MIDI (and optional note names)

**File:** `src/singing_exercise/scale.py`.

- **Input:** List of parsed slots (rest or (degree, accidental)), plus key (pitch_class, octave).
- **Output:** A list that aligns with the slots: for each slot either `None` (rest) or a MIDI note number (int). So length of output = length of input.
- Logic:
  - Rest slot → append `None`.
  - Degree + accidental → compute diatonic MIDI from existing `MAJOR_SCALE_OFFSETS`, then add −1 for flat, +1 for sharp; append that MIDI note.
- Optionally, a similar function that returns note-name strings (e.g. `"Rest"` or `None` for rest, and `"D5"`, `"Eb4"`, etc. for notes) for logging/debug. The pipeline that builds MIDI only needs the list of MIDI-or-None.

**Checklist:** In key C4, degree `b3` → Eb4 (MIDI 63); degree `#5` → G#4 (MIDI 68). Rest → None.

---

### Step 5: Process exercise: use slots + per-slot durations

**File:** `src/singing_exercise/process_exercise.py`.

- **Expand modulations:** For each key in the resolved key sequence:
  - Parse `scale_degrees` into slots (using the parser from Step 2).
  - Resolve durations (using Step 3): one duration per slot.
  - Call the updated scale module (Step 4) to get a list of MIDI-or-None (one per slot).
  - Build `midi_notes`: list of int | None (None = rest). Build `durations_sec`: list of float (same length).
- Pass these to the existing MIDI builder; the next step will make the MIDI builder accept `None` for rests.

**Checklist:** For one key, output `midi_notes` and `durations_sec` with the same length; rest slots have `None` and a duration.

---

### Step 6: MIDI renderer: handle rest (None) slots

**File:** `src/singing_exercise/render_midi.py`.

- **Current behavior:** `modulation_to_midi_bytes(midi_notes, durations_sec, bpm)` zips notes and durations and emits note_on/note_off for each.
- **Change:** Allow `midi_notes[i]` to be `None`. For such slots, do **not** emit note_on/note_off; only advance time by `durations_sec[i]` (e.g. by adding delta_ticks to the next message’s `time` or by emitting a “silent” delta). So the timeline stays correct and rests are the right length.

**Checklist:** A pattern like [60, None, 62] with durations [0.5, 0.5, 0.5] produces: note 60 for 0.5, silence 0.5, note 62 for 0.5.

---

### Step 7: RawExercise model and YAML loading

**File:** `src/singing_exercise/raw_exercise.py`.

- Add optional `note_values: list[int] | list[str] | None` to the dataclass (default `None`).
- In `from_dict`: if `note_values` is present, load it and validate `len(note_values) == len(data.get("scale_degrees", []))` after parsing. If lengths don’t match, raise a clear error.
- Ensure `scale_degrees` is stored as given (list of int/str) and that the parser from Step 2 is used wherever we need to interpret slots (e.g. in `process_exercise` and scale module).

**Checklist:** Loading a YAML with `note_values` and `scale_degrees` of the same length succeeds; loading with mismatched length fails with a helpful message.

---

### Step 8: Documentation and examples

**Files:** `docs/new_feature.md` (this file), `docs/SINGING_EXERCISE_AUDIO_PLAN.md` (optional short subsection), and an example YAML.

- Add an “Example with phrase and rhythm” to this doc or to the plan doc: `scale_degrees` with one rest and mixed note values and accidentals.
- Optionally add a “Phrase format” subsection to the main plan that references this doc and summarizes: `note_values` (optional), "R", and "b"/"#".

**Checklist:** New user can copy-paste an example YAML and generate a WAV that has different note lengths and a rest.

---

## Example YAML Snippet

```yaml
- name: "Phrase with rhythm and rest"
  scale_degrees: ["8", "5", "R", "b3", "1"]
  note_values: [8, 4, 4, 4, 2]   # eighth, quarter, quarter (rest), quarter, half
  modulation_waypoints: ["C4", "G4"]
  bpm: 70
  pause_between_keys_ms: 1500
  # note_value is ignored when note_values is present
```

This plays in each key: degree 8 (eighth), degree 5 (quarter), rest (quarter), degree 3 flat (quarter), degree 1 (half).

---

## Dependency Order

1. **Step 1** (timing) – no dependency.  
2. **Step 2** (parsing scale_degrees) – no dependency.  
3. **Step 3** (durations per slot) – depends on Step 1.  
4. **Step 4** (scale → MIDI with rest/accidentals) – depends on Step 2.  
5. **Step 5** (process_exercise) – depends on Steps 2, 3, 4.  
6. **Step 6** (render_midi rest) – depends on Step 5’s output shape.  
7. **Step 7** (RawExercise + YAML) – can be done in parallel with 2/3; needed for 5.  
8. **Step 8** – after the pipeline works.

---

## Summary

- **note_values list:** Optional; when present, one duration per scale-degree slot (numeric 2/4/8/16 or dotted strings like "4.", "8."), with timing module extended to support these.  
- **Rest "R":** Parsed in `scale_degrees`; represented as `None` in the MIDI list; duration from `note_values` or `note_value`; MIDI renderer advances time without a note.  
- **Accidentals b/#:** Parsed from strings with accidental **before** the degree: `"b3"`, `"#5"`; scale module applies ±1 semitone to the diatonic pitch. **Scale degrees in the phrase format are all quoted strings** (e.g. `"8"`, `"5"`, `"R"`, `"b3"`, `"1"`).  

All three are additive and backward compatible. Implementing in the order above will let you encode musical phrases with rhythm in YAML and generate exercises that reflect them in the rendered WAV.
