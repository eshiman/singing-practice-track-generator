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


## Running the script
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