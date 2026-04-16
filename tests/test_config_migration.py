import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.config import load_config, DEFAULTS


class TestConfigMigration(unittest.TestCase):
    def test_missing_new_keys_use_defaults(self):
        legacy = {"enabled_packs": ["common", "learned"], "auto_curate": True}
        merged = load_config(legacy)
        self.assertIn("injection_enabled", merged)
        self.assertIn("injection_top_k", merged)
        self.assertEqual(merged["enabled_packs"], ["common", "learned"])

    def test_user_keys_override_defaults(self):
        user = {"injection_top_k": 5}
        merged = load_config(user)
        self.assertEqual(merged["injection_top_k"], 5)

    def test_empty_config_uses_all_defaults(self):
        merged = load_config({})
        for k in DEFAULTS:
            self.assertEqual(merged[k], DEFAULTS[k])


if __name__ == "__main__":
    unittest.main()
