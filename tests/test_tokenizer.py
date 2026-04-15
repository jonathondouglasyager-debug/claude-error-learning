import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.tokenizer import tokenize


class TestTokenizer(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(tokenize("LS --Bad-Flag"), ["ls", "bad", "flag"])

    def test_strips_stopwords(self):
        self.assertEqual(tokenize("the quick brown fox"), ["quick", "brown", "fox"])

    def test_handles_camel_and_kebab(self):
        tokens = tokenize("use runProcess not run-Process")
        self.assertIn("run", tokens)
        self.assertIn("process", tokens)

    def test_preserves_short_meaningful_tokens(self):
        self.assertIn("rm", tokenize("rm -rf /"))

    def test_dedupes(self):
        self.assertEqual(tokenize("ls ls ls"), ["ls"])

    def test_handles_empty(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize(None), [])


if __name__ == "__main__":
    unittest.main()
