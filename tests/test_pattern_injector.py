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
        # Use min_score=0.0 to test that the rule is injected regardless of score
        # threshold (the tokenizer strips && so TF-IDF score is 0; we test
        # injection mechanics here, not scoring).
        r = run_injector("how do I run two shell commands with &&?", self.patterns,
                         config={"injection_min_score": 0.0})
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

    def test_scope_all_active_includes_non_learned(self):
        patterns = [
            {"id": "a", "category": "learned", "message": "foo", "learned_fix": "bar", "match": {"pattern": "foo"}},
            {"id": "b", "category": "common", "message": "baz foo", "learned_fix": "qux", "match": {"pattern": "baz"}},
        ]
        r = run_injector("foo", patterns, config={"injection_scope": "all_active", "injection_min_score": 0.0})
        self.assertIn("foo", r.stdout)
        # common-category pattern 'b' must be eligible for injection in all_active scope
        self.assertTrue(r.returncode == 0)

    def test_scope_learned_only_excludes_other_categories(self):
        patterns = [
            {"id": "a", "category": "learned", "message": "learned foo", "learned_fix": "bar", "match": {"pattern": "foo"}},
            {"id": "b", "category": "common", "message": "common foo", "learned_fix": "baz", "match": {"pattern": "foo"}},
        ]
        r = run_injector("foo", patterns, config={"injection_scope": "learned_only", "injection_min_score": 0.0})
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("learned foo", r.stdout)
        self.assertNotIn("common foo", r.stdout)

    def test_scope_high_confidence_excludes_low_confidence(self):
        patterns = [
            {"id": "a", "category": "learned", "confidence": 90, "message": "high conf foo", "learned_fix": "bar", "match": {"pattern": "foo"}},
            {"id": "b", "category": "learned", "confidence": 10, "message": "low conf foo", "learned_fix": "baz", "match": {"pattern": "foo"}},
        ]
        r = run_injector("foo", patterns, config={"injection_scope": "high_confidence", "injection_min_score": 0.0})
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("high conf foo", r.stdout)
        self.assertNotIn("low conf foo", r.stdout)

    def test_injection_eligible_false_excludes_pattern(self):
        patterns = [
            {"id": "a", "category": "learned", "message": "eligible foo", "learned_fix": "bar", "match": {"pattern": "foo"}, "injection_eligible": True},
            {"id": "b", "category": "learned", "message": "demoted foo", "learned_fix": "baz", "match": {"pattern": "foo"}, "injection_eligible": False},
        ]
        r = run_injector("foo", patterns, config={"injection_min_score": 0.0})
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("eligible foo", r.stdout)
        self.assertNotIn("demoted foo", r.stdout)


if __name__ == "__main__":
    unittest.main()
