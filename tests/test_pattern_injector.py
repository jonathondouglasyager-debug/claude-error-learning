import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_injector(prompt, patterns, config=None):
    with tempfile.TemporaryDirectory() as tmp:
        patterns_path = os.path.join(tmp, "active.json")
        json.dump({"patterns": patterns}, open(patterns_path, "w"))
        config = config or {}
        config_path = os.path.join(tmp, "config.json")
        json.dump(config, open(config_path, "w"))

        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = ROOT
        env["ERROR_LEARNING_PATTERNS_PATH"] = patterns_path
        env["ERROR_LEARNING_CONFIG_PATH"] = config_path

        payload = {"prompt": prompt, "session_id": "test"}
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "hooks", "pattern-injector.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )


class TestPatternInjector(unittest.TestCase):
    patterns = [
        {
            "id": "bash_and_chain",
            "category": "learned",
            "message": "&& doesn't work in Windows cmd",
            "learned_fix": "Use ;",
            "match": {"pattern": r".*&&.*"},
            "confidence": 80,
            "error_count": 3,
        },
        {
            "id": "ls_xyz",
            "category": "learned",
            "message": "ls --xyz is invalid",
            "learned_fix": "Remove --xyz",
            "match": {"pattern": r"^ls.*--xyz"},
            "confidence": 60,
            "error_count": 2,
        },
    ]

    def test_relevant_prompt_injects_relevant_rule(self):
        r = run_injector("how do I run two shell commands with &&?", self.patterns)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("&&", r.stdout)

    def test_unrelated_prompt_injects_nothing(self):
        r = run_injector("tell me a joke about cats", self.patterns,
                         config={"injection_min_score": 0.05})
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_respects_token_cap(self):
        r = run_injector("ls --xyz and &&", self.patterns, config={"injection_token_cap": 5})
        self.assertLessEqual(len(r.stdout), 40)

    def test_malformed_patterns_does_not_crash(self):
        r = run_injector("anything", [{"id": "broken"}])
        self.assertEqual(r.returncode, 0, msg=r.stderr)


if __name__ == "__main__":
    unittest.main()
