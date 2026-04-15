"""TF-IDF ranking over learned patterns. Stdlib only.

Concatenates each pattern's message + learned_fix + match.pattern as the
'document'. At query time, tokenizes the user's prompt and scores each
pattern by summed tf*idf for shared tokens.
"""
from collections import Counter
from math import log

from lib.tokenizer import tokenize


def _pattern_tokens(pattern):
    parts = [
        pattern.get("message", ""),
        pattern.get("learned_fix", ""),
        (pattern.get("match") or {}).get("pattern", ""),
        pattern.get("name", ""),
    ]
    return tokenize(" ".join(str(p) for p in parts if p))


def build_idf(patterns):
    n = len(patterns) or 1
    df = Counter()
    for p in patterns:
        for tok in set(_pattern_tokens(p)):
            df[tok] += 1
    return {tok: log((n + 1) / (count + 1)) + 1 for tok, count in df.items()}


def score_pattern(query, pattern, idf):
    q = set(tokenize(query))
    if not q:
        return 0.0
    doc_tokens = _pattern_tokens(pattern)
    if not doc_tokens:
        return 0.0
    doc_counter = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0
    for tok in q:
        if tok in doc_counter:
            tf = doc_counter[tok] / doc_len
            score += tf * idf.get(tok, 0.0)
    return score


def top_k(query, patterns, k=10, min_score=0.0):
    if not patterns or k <= 0:
        return []
    idf = build_idf(patterns)
    scored = [(score_pattern(query, p, idf), p) for p in patterns]
    scored.sort(key=lambda sp: sp[0], reverse=True)
    
    # Return top k results
    top_results = scored[:k]
    
    # If min_score is specified, filter the results
    if min_score > 0:
        top_results = [(s, p) for s, p in top_results if s > min_score]
    
    return [p for _s, p in top_results]
