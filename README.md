# singing-exercise-track-generator
An llm-generated script that turns your vocal exercises into a practice track

---

## Dependencies

I did this using Homebrew on macos:

```bash
brew install fluid-synth
brew install rubberband
```

**Python:**

```bash
python -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

You need also need a `.sf2` piano soundfont. I used [General User GS](https://schristiancollins.com/generaluser.php) (S. Christian Collins). Set its path via environment or CLI (see below).


## YAML format

Input is a **session file**: one YAML file with an `exercises` list. The program generates one long WAV containing all exercises in order. Optional top-level key:

- `pause_between_exercises_ms` — silence between exercises (default 3000)

### Simple example (one exercise, uniform rhythm)

One exercise with a scale pattern, a modulation path, and a single note duration for every note:

```yaml
# Optional: silence (ms) between exercises when you have more than one (default 3000)
pause_between_exercises_ms: 3000

exercises:
  - name: "Wee 8-5-3-1 (down)"
    # Scale degrees: 1=tonic, 8=octave; pattern is played in every key along the waypoints
    scale_degrees: [8, 5, 3, 1]
    # Keys to visit in order; path goes by semitones between waypoints (D4→…→G3→…→Bb4→…→F3)
    modulation_waypoints: ["D4", "G3", "Bb4", "F3"]
    bpm: 70
    # One duration for all notes: "8th", "quarter", etc.
    note_value: 8th
    # Pause (ms) after each key before the next
    pause_between_keys_ms: 2000
```

### Full-featured example (multiple exercises, rhythm, rests, accidentals, feedback, demo)

```yaml
pause_between_exercises_ms: 4000

exercises:
  # --- Exercise 1: per-note rhythm, dotted/triplets, rest, accidentals, spoken feedback, voice demo ---
  - name: "Phrase with rhythm and rest"
    # Quoted strings allow rest "R" and accidentals: "b3" (flat), "#5" (sharp)
    scale_degrees: ["8", "7", "5", "R", "3", "5", "6", "b7", "8", "b7"]
    # One duration per slot: 4=quarter, 8=eighth, 2=half; "4."=dotted quarter; "8t"=eighth triplet
    note_values: [4, 4, 4, 8, 8, 8, 8, 8, 8, 2]
    modulation_waypoints: ["Ab3", "E4", "Ab3"]
    bpm: 90
    pause_between_keys_ms: 2000
    # If true, prompts you to record a voice demo before this exercise; demo is inserted in the track
    demo: true
    # Spoken (TTS) feedback after a specific key/occurrence in the modulation sequence
    feedback:
      - key: "Ab3"
        which_occurrence: 1   # after the 1st time we play in Ab3
        text: "Smoother transition into the next phrase."
      - key: "E4"
        which_occurrence: 1
        text: "Open the mouth more as you reach the top."

  # --- Exercise 2: simple scale run, uniform 8th notes ---
  - name: "Scale 1-8-1"
    scale_degrees: [1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 5, 4, 3, 2, 1]
    modulation_waypoints: ["C4", "G4", "C4"]
    bpm: 72
    note_value: 8th
    pause_between_keys_ms: 2500
```

### Repeating specific modulations

You can optionally repeat selected keys in the resolved modulation sequence using `repeated_modulations`.
Each rule duplicates the matched key immediately after itself, preserving the exact musical content
(same pitches, durations, and pause handling).

Fields:

- `key` (required) - note name like `E4`
- `extra_repeats` (required) - integer `>= 0`
- `which_occurrence` (optional) - integer `>= 1`, defaults to `1`

If a modulation is repeated, spoken feedback is only evaluated on original (non-repeat-copy) modulations.
Repeat copies never trigger feedback.

```yaml
exercises:
  - name: "Pattern with repeated peak key"
    scale_degrees: [1, 3, 5, 8]
    modulation_waypoints: ["C#4", "G3", "E4", "C#4"]
    repeated_modulations:
      - key: "E4"
        extra_repeats: 3
      - key: "D4"
        extra_repeats: 1
    bpm: 70
    note_value: 8th
    pause_between_keys_ms: 2000
```

## Running the script

```bash
# Use the run script (adds src to path)
python scripts/run_generate_practice_track.py exercises/session_example.yaml
# -> output/session_example.wav
```

**Soundfont:** Either set the path once:

```bash
export SOUNDFONT=/path/to/your/piano.sf2
```

or pass it each run:

```bash
python scripts/run_generate_practice_track.py exercises/session_example.yaml --soundfont /path/to/piano.sf2
```

**Output:** By default the WAV is written to `output/<yaml_stem>.wav`. Override with `-o`:
