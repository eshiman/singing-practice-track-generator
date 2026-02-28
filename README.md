# singing-exercise-track-generator
an llm-generated script that turns your vocal exercises into a practice track


Generates **practice-track WAV files** from singing exercises defined in YAML. Each exercise specifies a scale-degree pattern (e.g. 8-5-3-1), a modulation path (waypoints), and timing. The app plays the pattern on piano in every key along that path, with configurable pauses between keys—so you can sing along without touching an instrument.

## What it does

- **Input**: Exercise YAML files (see `exercises/`) with scale degrees, modulation waypoints, BPM, note value, and pause duration.
- **Output**: A single WAV file: piano plays the pattern in each key (semitones between waypoints), with silence between key changes.
- **Pipeline**: YAML → expanded segments (keys + MIDI notes) → MIDI per segment → render to WAV via FluidSynth → concatenate with pauses.

Feedback cues in the YAML are parsed but not yet used for audio (e.g. TTS); the current focus is piano-only practice tracks.

---

## How to run

### 1. Dependencies

- **Python 3** with packages from `requirements.txt`
- **FluidSynth** (for MIDI → WAV)
- A **piano soundfont** (`.sf2`)

**macOS (Homebrew):**

```bash
brew install fluid-synth
```

**Python:**

```bash
python -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

You need a `.sf2` piano soundfont. A good free option is [General User GS](https://schristiancollins.com/generaluser.php) (S. Christian Collins); see also [FluidSynth soundfonts](https://github.com/FluidSynth/fluidsynth/wiki/SoundFont). Set its path via environment or CLI (see below).

### 2. Generate a practice track

From the project root:

```bash
# Use the run script (adds src to path)
python scripts/run_generate_practice_track.py exercises/wee_8-5-3-1_down.yaml
```

**Soundfont:** Either set the path once:

```bash
export SOUNDFONT=/path/to/your/piano.sf2
```

or pass it each run:

```bash
python scripts/run_generate_practice_track.py exercises/wee_8-5-3-1_down.yaml --soundfont /path/to/piano.sf2
```

**Output:** By default the WAV is written to `output/<exercise_name>.wav`. Override with `-o`:

```bash
python scripts/run_generate_practice_track.py exercises/wee_8-5-3-1_down.yaml -o my_track.wav
```