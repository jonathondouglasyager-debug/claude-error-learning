import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import curation


SAMPLE = [
    {"id": "a", "message": "&& doesn't work in Windows", "learned_fix": "use ;"},
    {"id": "b", "message": "&& fails in cmd.exe", "learned_fix": "use semicolons"},
    {"id": "c", "message": "ls --xyz invalid", "learned_fix": "remove --xyz"},
]


class TestCuration(unittest.TestCase):
    def test_requires_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                curation.llm_curate(SAMPLE)

    def test_parses_merge_suggestions(self):
        fake_response = {
            "content": [
                {
                    "type": "text",
                    "text": '{"merges": [["a", "b"]], "prune": ["c"], "notes": "a and b duplicate"}',
                }
            ]
        }
        with mock.patch.object(curation, "_call_anthropic", return_value=fake_response):
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
                result = curation.llm_curate(SAMPLE)
        self.assertEqual(result["merges"], [["a", "b"]])
        self.assertEqual(result["prune"], ["c"])

    def test_handles_malformed_response(self):
        fake_response = {"content": [{"type": "text", "text": "not json at all"}]}
        with mock.patch.object(curation, "_call_anthropic", return_value=fake_response):
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
                result = curation.llm_curate(SAMPLE)
        self.assertEqual(result, {"merges": [], "prune": [], "notes": "parse-failure"})


if __name__ == "__main__":
    unittest.main()
