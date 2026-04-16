import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.vote import record_vote, apply_vote_thresholds


class TestVote(unittest.TestCase):
    def test_record_up_vote_increments(self):
        p = {"id": "x", "vote_up": 0, "vote_down": 0}
        record_vote(p, "up")
        self.assertEqual(p["vote_up"], 1)
        self.assertEqual(p["vote_down"], 0)

    def test_record_down_vote_increments(self):
        p = {"id": "x", "vote_up": 0, "vote_down": 0}
        record_vote(p, "down")
        self.assertEqual(p["vote_down"], 1)

    def test_record_invalid_raises(self):
        with self.assertRaises(ValueError):
            record_vote({}, "sideways")

    def test_apply_disables_pattern_with_negative_ratio(self):
        patterns = [
            {"id": "bad", "vote_up": 0, "vote_down": 5, "enabled": True},
            {"id": "good", "vote_up": 5, "vote_down": 0, "enabled": True},
        ]
        disabled = apply_vote_thresholds(patterns, down_threshold=3)
        by_id = {p["id"]: p for p in patterns}
        self.assertFalse(by_id["bad"]["enabled"])
        self.assertTrue(by_id["good"]["enabled"])
        self.assertEqual(disabled, ["bad"])

    def test_apply_ignores_insufficient_signal(self):
        patterns = [{"id": "x", "vote_up": 0, "vote_down": 1, "enabled": True}]
        disabled = apply_vote_thresholds(patterns, down_threshold=3)
        self.assertEqual(disabled, [])


if __name__ == "__main__":
    unittest.main()
