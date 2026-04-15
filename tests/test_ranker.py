import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.ranker import build_idf, score_pattern, top_k


SAMPLE_PATTERNS = [
    {
        "id": "bash_and_chain",
        "match": {"pattern": r".*&&.*"},
        "message": "&& doesn't work in Windows cmd",
        "learned_fix": "Use ; or separate commands",
    },
    {
        "id": "ls_bad_flag_xyz",
        "match": {"pattern": r"^ls\s.*--xyz"},
        "message": "ls: --xyz is not valid",
        "learned_fix": "Remove --xyz or use -l",
    },
    {
        "id": "rm_rf_root",
        "match": {"pattern": r"^rm\s+-rf\s+/"},
        "message": "destructive",
        "learned_fix": "Use a more specific path",
    },
]


class TestRanker(unittest.TestCase):
    def test_idf_contains_all_tokens(self):
        idf = build_idf(SAMPLE_PATTERNS)
        self.assertIn("ls", idf)
        self.assertIn("rm", idf)
        self.assertGreater(idf["ls"], 0)

    def test_idf_rarer_tokens_score_higher(self):
        idf = build_idf(SAMPLE_PATTERNS)
        self.assertGreater(idf["xyz"], idf.get("use", 0))

    def test_score_ranks_exact_match_high(self):
        idf = build_idf(SAMPLE_PATTERNS)
        score_ls = score_pattern("how do I ls --xyz", SAMPLE_PATTERNS[1], idf)
        score_rm = score_pattern("how do I ls --xyz", SAMPLE_PATTERNS[2], idf)
        self.assertGreater(score_ls, score_rm)

    def test_top_k_returns_requested_count(self):
        result = top_k("ls --xyz flag", SAMPLE_PATTERNS, k=2)
        self.assertEqual(len(result), 2)

    def test_top_k_respects_min_score(self):
        result = top_k("totally unrelated phrase about kittens", SAMPLE_PATTERNS, k=3, min_score=0.01)
        self.assertLessEqual(len(result), 1)

    def test_top_k_handles_empty_patterns(self):
        self.assertEqual(top_k("anything", [], k=5), [])


if __name__ == "__main__":
    unittest.main()
