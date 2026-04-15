import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestValidatorTracksTriggers(unittest.TestCase):
    def test_last_triggered_at_is_updated_on_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            patterns_path = os.path.join(tmp, "active.json")
            pattern = {
                "id": "test_block_and",
                "category": "learned",
                "tool": "Bash",
                "match": {"type": "regex", "pattern": r".*&&.*"},
                "message": "&& blocked",
                "learned_fix": "use ;",
                "confidence": 90,
                "error_count": 1,
                "last_triggered_at": None,
            }
            json.dump({"patterns": [pattern]}, open(patterns_path, "w"))

            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = ROOT
            env["ERROR_LEARNING_PATTERNS_PATH"] = patterns_path

            payload = {"tool_name": "Bash", "tool_input": {"command": "echo a && echo b"}}
            subprocess.run(
                [sys.executable, os.path.join(ROOT, "hooks", "command-validator.py")],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )
            updated = json.load(open(patterns_path))
            stored = updated["patterns"][0]
            self.assertIsNotNone(stored["last_triggered_at"])


if __name__ == "__main__":
    unittest.main()
