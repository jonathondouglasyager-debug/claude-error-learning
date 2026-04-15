"""Sanitize error text before it becomes learned-pattern content.

Auto-learned patterns are a prompt-injection supply-chain surface: a crafted
error message could poison learned.json and later be injected into Claude's
context. We scrub URLs, common instruction-style phrases, and cap length.
"""
import re

MAX_LEN = 2048

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_INSTRUCTION_RES = [
    re.compile(r"\bignore\s+(previous|above|prior|all)\s+instruction", re.IGNORECASE),
    re.compile(r"\b(system|assistant|user)\s*:\s*.+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bnew\s+instruction", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"\bdeveloper\s+mode", re.IGNORECASE),
]


def sanitize_error_text(text):
    if not text:
        return ""
    clean = _URL_RE.sub("[url]", text)
    for pat in _INSTRUCTION_RES:
        clean = pat.sub("[redacted]", clean)
    if len(clean) > MAX_LEN:
        clean = clean[:MAX_LEN] + "...[truncated]"
    return clean
