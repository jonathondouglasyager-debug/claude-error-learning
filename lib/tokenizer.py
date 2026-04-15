"""Lightweight tokenizer for TF-IDF scoring - stdlib only."""
import re

STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in",
    "is", "it", "not", "of", "on", "or", "that", "the", "this", "to", "with",
})

_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+")
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize(text):
    if not text:
        return []
    pre = _CAMEL_RE.sub(" ", text)
    raw = _SPLIT_RE.split(pre.lower())
    seen, out = set(), []
    for tok in raw:
        if not tok or tok in STOPWORDS:
            continue
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out
