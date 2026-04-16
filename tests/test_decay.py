import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.decay import demote_stale_patterns


def _iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


class TestDecay(unittest.TestCase):
    def test_stale_pattern_demoted(self):
        patterns = [
            {"id": "fresh", "last_triggered_at": _iso(5), "injection_eligible": True},
            {"id": "stale", "last_triggered_at": _iso(60), "injection_eligible": True},
        ]
        demoted = demote_stale_patterns(patterns, max_age_days=30)
        by_id = {p["id"]: p for p in patterns}
        self.assertFalse(by_id["stale"]["injection_eligible"])
        self.assertTrue(by_id["fresh"]["injection_eligible"])
        self.assertEqual(demoted, ["stale"])

    def test_never_triggered_pattern_left_alone(self):
        patterns = [{"id": "new", "last_triggered_at": None, "injection_eligible": True}]
        demoted = demote_stale_patterns(patterns, max_age_days=30)
        self.assertEqual(demoted, [])
        self.assertTrue(patterns[0]["injection_eligible"])

    def test_already_demoted_not_touched(self):
        patterns = [{"id": "x", "last_triggered_at": _iso(100), "injection_eligible": False}]
        demoted = demote_stale_patterns(patterns, max_age_days=30)
        self.assertEqual(demoted, [])

    def test_custom_age(self):
        patterns = [{"id": "x", "last_triggered_at": _iso(10), "injection_eligible": True}]
        self.assertEqual(demote_stale_patterns(patterns, max_age_days=7), ["x"])


if __name__ == "__main__":
    unittest.main()
