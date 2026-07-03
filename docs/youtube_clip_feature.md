# Feature: YouTube clips in practice sessions

**Status:** Implemented. Trim uses inclusive start, exclusive end (`start_time` included, `end_time` excluded). Audio is downloaded via `yt-dlp`, pitch-shifted with pydub (frame-rate resampling).

## Goal

Let singers practice **real musical phrases** taken from YouTube at **different transpositions**, in the same spirit as scale exercises that move through keys. Each clip is trimmed to a segment of a video, then played multiple times at semitone offsets along a path (stepping one semitone at a time between waypoints), with optional pauses and an optional voice demo—similar to exercises, but the backing audio is the clip (pitch-shifted), not generated piano.

---

## Session file layout

Lesson YAML files may include two top-level lists:

- `exercises:` — existing behavior (unchanged).
- `youtube_clips:` — new; optional.

When both are present, the generator processes **all exercises first**, then **all youtube clips**, in list order. (Session-level pauses between the exercise block and the clip block can be added later if needed.)

---

## `youtube_clips` entry fields

Each item in `youtube_clips` is an object with:

| Field | Required | Description |
|--------|----------|-------------|
| `name` | yes | Label for logging and demo recording prompts. |
| `link` | yes | URL to the YouTube video (audio source). |
| `start_time` | yes | Where the clip begins, as `mm:ss` or `mm:ss.fff` (e.g. `"0:32"`, `"0:50.5"`, `"0:50.250"`). |
| `end_time` | yes | Where the clip ends, same format (e.g. `"0:48"`). **Inclusive start, exclusive end** — audio at `end_time` is not included. Trim precision is 1 ms. |
| `modulation_offsets` | yes | Ordered list of **semitone offsets** relative to the clip at its **original pitch** (see below). |
| `demo` | no (default `false`) | If `true`, prompt to record a voice demo once before this clip’s modulation passes (same idea as exercises). **No starting-key triad** for clips. |
| `pause_between_keys_ms` | no (default TBD or match exercises) | Silence between consecutive modulation passes, in milliseconds (same role as on exercises). |

### Offset semantics (`modulation_offsets`)

- Values are **integers**: semitones up (positive) or down (negative) from the **trimmed clip at original pitch**. Offset `0` is the recording as trimmed—not a named key like `"Ab3"`.
- The **first playback uses the first offset in the list**; there is no implicit “play at 0 first” unless `0` appears in the list.
- Between consecutive offsets, the tool walks **one semitone at a time** (same stepping behavior as exercise `modulation_waypoints`, but using offsets instead of note names).

**Example:** `modulation_offsets: [5, -3]`

→ Play the clip at **+5** semitones, then at +4, +3, …, 0, …, **-3**, with `pause_between_keys_ms` between each pass.

**Example:** `modulation_offsets: [0, 5, -3]`

→ Start at original pitch, then step semitonally up to +5, then down to -3.

Use YAML integers (negative values are fine): `[5, -3]`, not strings, unless a future extension requires otherwise.

### Timestamp format (`start_time` / `end_time`)

- Two colon-separated parts: minutes and seconds.
- Seconds may be a whole number (`"0:32"`) or include a fractional part for sub-second precision (`"0:50.5"`, `"0:50.250"`).
- Seconds must be in `[0, 60)` (i.e. less than 60, including fractional values such as `59.999`).

---

## What this feature is not (v1)

- No requirement to label the song’s key (`source_key` is out of scope).
- No piano accompaniment for clip segments.
- No triad cue before demo recording.

Optional exercise parity (`feedback`, `repeated_modulations`, etc.) is **not** part of v1 unless added explicitly later.

---

## Example lesson YAML (illustrative)

```yaml
pause_between_exercises_ms: 4000

exercises:
  - name: "Wee wee wee wee"
    scale_degrees: [[1, 3, 5]]
    note_value: 4
    demo: true
    modulation_waypoints: ["C#4", "G3", "E4", "C#4"]
    bpm: 100
    pause_between_keys_ms: 1500

youtube_clips:
  - name: "Bridge phrase"
    link: "https://www.youtube.com/watch?v=EXAMPLE"
    start_time: "0:32"
    end_time: "0:48"
    modulation_offsets: [5, -3]
    demo: true
    pause_between_keys_ms: 2000
```

---

## Success criteria (behavioral)

- A single practice WAV can be built from a lesson file that contains exercises and/or youtube clips.
- For each clip: use only the audio between `start_time` and `end_time`; for each resolved offset in the path, play that segment transposed by that many semitones; honor `pause_between_keys_ms` between passes; if `demo` is true, include one recorded demo before that clip’s passes (no triad).
- Clips run only after all exercises in the same file have been rendered.
