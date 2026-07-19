"""Tests for FeedbackEntry.generated field parsing."""
import unittest

from singing_exercise.raw_exercise import RawExercise


def _exercise_dict() -> dict:
    return {
        "name": "test",
        "scale_degrees": [1],
        "modulation_waypoints": ["C4", "E4"],
        "bpm": 70,
        "note_value": "8th",
        "pause_between_keys_ms": 1000,
    }


class FeedbackGeneratedParsingTests(unittest.TestCase):
    def test_generated_defaults_to_true(self) -> None:
        data = _exercise_dict()
        data["feedback"] = [{"key": "C4", "which_occurrence": 1, "text": "Open up."}]
        exercise = RawExercise.from_dict(data)
        self.assertEqual(len(exercise.feedback), 1)
        self.assertTrue(exercise.feedback[0].generated)

    def test_generated_explicit_true(self) -> None:
        data = _exercise_dict()
        data["feedback"] = [
            {"key": "C4", "which_occurrence": 1, "text": "Open up.", "generated": True}
        ]
        exercise = RawExercise.from_dict(data)
        self.assertTrue(exercise.feedback[0].generated)

    def test_generated_explicit_false(self) -> None:
        data = _exercise_dict()
        data["feedback"] = [
            {"key": "C4", "which_occurrence": 1, "text": "Recorded line.", "generated": False}
        ]
        exercise = RawExercise.from_dict(data)
        self.assertFalse(exercise.feedback[0].generated)

    def test_mixed_generated_entries(self) -> None:
        data = _exercise_dict()
        data["feedback"] = [
            {"key": "C4", "which_occurrence": 1, "text": "TTS line."},
            {"key": "Db4", "which_occurrence": 1, "text": "Recorded line.", "generated": False},
        ]
        exercise = RawExercise.from_dict(data)
        self.assertTrue(exercise.feedback[0].generated)
        self.assertFalse(exercise.feedback[1].generated)

    def test_other_fields_unaffected_by_generated(self) -> None:
        data = _exercise_dict()
        data["feedback"] = [
            {"key": "E4", "which_occurrence": 2, "text": "Lift the soft palate.", "generated": False}
        ]
        exercise = RawExercise.from_dict(data)
        fb = exercise.feedback[0]
        self.assertEqual(fb.key, "E4")
        self.assertEqual(fb.which_occurrence, 2)
        self.assertEqual(fb.text, "Lift the soft palate.")
        self.assertFalse(fb.generated)


if __name__ == "__main__":
    unittest.main()
