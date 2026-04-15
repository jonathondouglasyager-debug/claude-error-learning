import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.renderer import render_as_natural_language, estimate_tokens, truncate_to_tokens


SAMPLE = [
    {
        "id": "bash_and_chain",
        "message": "&& doesn't work in Windows cmd",
        "learned_fix": "Use ; to separate commands",
    },
    {
        "id": "ls_bad_flag_xyz",
        "message": "ls: --xyz is not a valid option",
        "learned_fix": "Remove --xyz or use -l instead",
    },
]


class TestRenderer(unittest.TestCase):
    def test_render_produces_bullet_list(self):
        out = render_as_natural_language(SAMPLE)
        self.assertIn("- ", out)
        self.assertIn("&&", out)
        self.assertIn("ls", out)

    def test_render_includes_fix(self):
        out = render_as_natural_language(SAMPLE[:1])
        self.assertIn("Use ;", out)

    def test_render_empty_returns_empty_string(self):
        self.assertEqual(render_as_natural_language([]), "")

    def test_estimate_tokens_is_roughly_chars_over_4(self):
        self.assertAlmostEqual(estimate_tokens("a" * 400), 100, delta=20)

    def test_truncate_keeps_under_cap(self):
        text = "line one\nline two\nline three\nline four\nline five"
        out = truncate_to_tokens(text, max_tokens=4)
        self.assertLess(estimate_tokens(out), 6)

    def test_truncate_preserves_whole_lines(self):
        text = "first line\nsecond line\nthird line"
        out = truncate_to_tokens(text, max_tokens=3)
        for line in out.splitlines():
            self.assertIn(line, text)


if __name__ == "__main__":
    unittest.main()
