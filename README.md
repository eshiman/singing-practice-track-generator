# singing-exercise-track-generator
An llm-generated script that turns your vocal exercises into a practice track

---

## Dependencies

I did this using Homebrew on macos:

```bash
brew install fluid-synth
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

Example `exercises/session_example.yaml`:

```yaml
pause_between_exercises_ms: 4000
exercises:
  - name: "Wee 8-5-3-1 (down)"
    scale_degrees: [8, 5, 3, 1]
    modulation_waypoints: ["D4", "G3", "Bb4", "F3"]
    bpm: 70
    note_value: 8th
    pause_between_keys_ms: 2000
    feedback: [...]
  - name: "Wee 5-3-1 (simple)"
    scale_degrees: [5, 3, 1]
    ...
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

```bash
python scripts/run_generate_practice_track.py exercises/session_example.yaml -o my_track.wav
```

**Config and volume:** Optional `config.yaml` in the project root (or current directory) can set default volumes:

```yaml
# Volume in dB. Lower = quieter.
tts_volume_db: -6    # spoken feedback (when exercise has feedback section)
music_volume_db: 0   # piano
```

CLI overrides: `--tts-volume-db` and `--music-volume-db` override the config for a single run.

**Spoken feedback (Phase 3):** If the exercise YAML includes a `feedback` list (each entry: `key`, `which_occurrence`, `text`), the script inserts spoken cues after the specified key/occurrence. TTS uses macOS `say` on macOS, or `pyttsx3` on other platforms (`pip install pyttsx3`).

**Voice demo:** Set `demo: true` on an exercise to record a voice demo before that exercise. When you run the script, it will prompt you to record from your default microphone; press Enter when finished. The recording is inserted at the start of that exercise in the output WAV (with a short pause after it). Requires **PyAudio** (`pip install PyAudio`); on macOS you may need `brew install portaudio` first.