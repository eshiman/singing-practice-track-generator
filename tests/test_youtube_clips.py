import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from singing_exercise.keys import offsets_to_offset_sequence
from singing_exercise.process_youtube_clip import expand_clip_to_offsets
from singing_exercise.raw_youtube_clip import RawYoutubeClip, parse_mm_ss
from singing_exercise.session import load_session_from_yaml_path
from singing_exercise.youtube_audio import pitch_shift, trim_clip


class OffsetSequenceTests(unittest.TestCase):
    def test_single_offset(self) -> None:
        self.assertEqual(offsets_to_offset_sequence([5]), [5])

    def test_two_offsets_down(self) -> None:
        self.assertEqual(offsets_to_offset_sequence([5, -3]), [5, 4, 3, 2, 1, 0, -1, -2, -3])

    def test_three_offsets(self) -> None:
        self.assertEqual(
            offsets_to_offset_sequence([0, 5, -3]),
            [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0, -1, -2, -3],
        )


class RawYoutubeClipTests(unittest.TestCase):
    def test_from_dict(self) -> None:
        clip = RawYoutubeClip.from_dict(
            {
                "name": "Bridge",
                "link": "https://www.youtube.com/watch?v=abc",
                "start_time": "0:32",
                "end_time": "0:48",
                "modulation_offsets": [5, -3],
                "demo": True,
                "pause_between_keys_ms": 2000,
            }
        )
        self.assertEqual(clip.name, "Bridge")
        self.assertEqual(clip.modulation_offsets, [5, -3])
        self.assertTrue(clip.demo)
        self.assertEqual(expand_clip_to_offsets(clip), [5, 4, 3, 2, 1, 0, -1, -2, -3])

    def test_requires_fields(self) -> None:
        with self.assertRaises(ValueError):
            RawYoutubeClip.from_dict({"name": "x"})
        with self.assertRaises(ValueError):
            RawYoutubeClip.from_dict(
                {
                    "name": "x",
                    "link": "https://youtu.be/x",
                    "start_time": "0:00",
                    "end_time": "0:10",
                    "modulation_offsets": ["5"],
                }
            )


class TimestampTests(unittest.TestCase):
    def test_parse_mm_ss(self) -> None:
        self.assertEqual(parse_mm_ss("0:32"), 32.0)
        self.assertEqual(parse_mm_ss("1:05"), 65.0)
        self.assertEqual(parse_mm_ss("0:50.5"), 50.5)
        self.assertEqual(parse_mm_ss("0:50.250"), 50.25)

    def test_parse_mm_ss_rejects_invalid(self) -> None:
        for bad in ("0:60", "0:-1", "1:05:00", "abc"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_mm_ss(bad)


class TrimAndPitchTests(unittest.TestCase):
    def test_trim_exclusive_end(self) -> None:
        audio = AudioSegment.silent(duration=5000, frame_rate=44100)
        trimmed = trim_clip(audio, "0:01", "0:03")
        self.assertEqual(len(trimmed), 2000)

    def test_trim_fractional_seconds(self) -> None:
        audio = AudioSegment.silent(duration=5000, frame_rate=44100)
        trimmed = trim_clip(audio, "0:01.5", "0:03.25")
        self.assertEqual(len(trimmed), 1750)

    def test_pitch_shift_zero_is_unchanged(self) -> None:
        audio = AudioSegment.silent(duration=1000, frame_rate=44100)
        shifted = pitch_shift(audio, 0)
        self.assertEqual(len(shifted), len(audio))
        self.assertEqual(shifted.frame_rate, audio.frame_rate)


class SessionLoaderTests(unittest.TestCase):
    def test_load_session_with_clips(self) -> None:
        yaml_text = """
pause_between_exercises_ms: 4000
exercises:
  - name: "Scale"
    scale_degrees: [1]
    modulation_waypoints: ["C4"]
    bpm: 70
    note_value: 8th
youtube_clips:
  - name: "Phrase"
    link: "https://www.youtube.com/watch?v=EXAMPLE"
    start_time: "0:10"
    end_time: "0:20"
    modulation_offsets: [0, 2]
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            path = Path(f.name)
        session = load_session_from_yaml_path(path)
        self.assertEqual(len(session.exercises), 1)
        self.assertEqual(len(session.youtube_clips), 1)
        self.assertEqual(session.pause_between_exercises_ms, 4000)
        path.unlink()


if __name__ == "__main__":
    unittest.main()
