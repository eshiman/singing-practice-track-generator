import unittest

from singing_exercise.process_exercise import (
    expand_exercise_to_modulations,
    feedback_after_modulation,
)
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


class RepeatedModulationsTests(unittest.TestCase):
    def test_no_repeats_keeps_original_behavior(self) -> None:
        exercise = RawExercise.from_dict(_exercise_dict())
        modulations = expand_exercise_to_modulations(exercise)
        self.assertEqual([m["key_name"] for m in modulations], ["C4", "Db4", "D4", "Eb4", "E4"])
        self.assertTrue(all(not m["is_repeat_copy"] for m in modulations))

    def test_repeat_one_key(self) -> None:
        data = _exercise_dict()
        data["repeated_modulations"] = [{"key": "E4", "extra_repeats": 2}]
        exercise = RawExercise.from_dict(data)
        modulations = expand_exercise_to_modulations(exercise)
        keys = [m["key_name"] for m in modulations]
        repeat_flags = [m["is_repeat_copy"] for m in modulations]
        self.assertEqual(keys, ["C4", "Db4", "D4", "Eb4", "E4", "E4", "E4"])
        self.assertEqual(repeat_flags, [False, False, False, False, False, True, True])

    def test_multiple_repeat_rules(self) -> None:
        data = _exercise_dict()
        data["repeated_modulations"] = [
            {"key": "Db4", "extra_repeats": 1},
            {"key": "E4", "extra_repeats": 2},
        ]
        exercise = RawExercise.from_dict(data)
        modulations = expand_exercise_to_modulations(exercise)
        self.assertEqual(
            [m["key_name"] for m in modulations],
            ["C4", "Db4", "Db4", "D4", "Eb4", "E4", "E4", "E4"],
        )
        self.assertEqual(
            [m["is_repeat_copy"] for m in modulations],
            [False, False, True, False, False, False, True, True],
        )

    def test_occurrence_specific_repeat_rule(self) -> None:
        data = _exercise_dict()
        data["modulation_waypoints"] = ["C4", "D4", "C4"]
        data["repeated_modulations"] = [
            {"key": "Db4", "extra_repeats": 1, "which_occurrence": 2}
        ]
        exercise = RawExercise.from_dict(data)
        modulations = expand_exercise_to_modulations(exercise)
        self.assertEqual(
            [m["key_name"] for m in modulations],
            ["C4", "Db4", "D4", "Db4", "Db4", "C4"],
        )
        self.assertEqual(
            [m["is_repeat_copy"] for m in modulations],
            [False, False, False, False, True, False],
        )

    def test_feedback_only_on_original_not_repeat_copies(self) -> None:
        data = _exercise_dict()
        data["modulation_waypoints"] = ["C4", "D4", "C4"]
        data["repeated_modulations"] = [{"key": "Db4", "extra_repeats": 2}]
        data["feedback"] = [
            {"key": "Db4", "which_occurrence": 1, "text": "first"},
            {"key": "Db4", "which_occurrence": 2, "text": "second"},
        ]
        exercise = RawExercise.from_dict(data)
        modulations = expand_exercise_to_modulations(exercise)
        feedback = feedback_after_modulation(modulations, exercise.feedback)
        self.assertEqual([m["key_name"] for m in modulations], ["C4", "Db4", "Db4", "Db4", "D4", "Db4", "C4"])
        self.assertEqual(feedback[1], ["first"])
        self.assertEqual(feedback[2], [])
        self.assertEqual(feedback[3], [])
        self.assertEqual(feedback[5], ["second"])

    def test_invalid_repeat_configs_raise(self) -> None:
        with self.assertRaises(ValueError):
            RawExercise.from_dict({**_exercise_dict(), "repeated_modulations": [{"key": "E4", "extra_repeats": -1}]})
        with self.assertRaises(ValueError):
            RawExercise.from_dict(
                {**_exercise_dict(), "repeated_modulations": [{"key": "E4", "extra_repeats": 1, "which_occurrence": 0}]}
            )
        with self.assertRaises(ValueError):
            RawExercise.from_dict({**_exercise_dict(), "repeated_modulations": [{"key": "H4", "extra_repeats": 1}]})
        with self.assertRaises(ValueError):
            RawExercise.from_dict({**_exercise_dict(), "repeated_modulations": [{"extra_repeats": 1}]})
        with self.assertRaises(ValueError):
            RawExercise.from_dict({**_exercise_dict(), "repeated_modulations": [{"key": "E4"}]})


if __name__ == "__main__":
    unittest.main()
