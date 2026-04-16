"""Opt-in LLM curation via Anthropic API. stdlib urllib, no extra deps.

Sends a compact list of patterns (id + message + learned_fix) to Haiku
and asks for merge / prune suggestions. Does NOT apply changes directly;
returns suggestions for the caller to present to the user.
"""
import json
import os
import urllib.request

_MODEL = os.environ.get("ERROR_LEARNING_CURATION_MODEL", "claude-haiku-4-5-20251001")
_API_URL = "https://api.anthropic.com/v1/messages"
_TIMEOUT = 30

_PROMPT = (
    "You are curating a list of learned error-blocking patterns from a Claude "
    "Code plugin. For each pair of patterns that describe the same underlying "
    "mistake, return a merge suggestion. For any pattern that is too vague or "
    "environment-specific to be useful, suggest pruning it. Respond with a "
    "SINGLE JSON object and nothing else, shape: "
    '{"merges": [["id_a","id_b"], ...], "prune": ["id_c", ...], "notes": "..."}'
)


def _call_anthropic(payload):
    api_key = os.environ["ANTHROPIC_API_KEY"]
    req = urllib.request.Request(
        _API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())


def llm_curate(patterns):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required for llm_curate")
    if not patterns:
        return {"merges": [], "prune": [], "notes": "no-patterns"}
    compact = [
        {
            "id": p.get("id"),
            "message": (p.get("message") or "")[:200],
            "fix": (p.get("learned_fix") or "")[:200],
        }
        for p in patterns
    ]
    payload = {
        "model": _MODEL,
        "max_tokens": 1024,
        "system": _PROMPT,
        "messages": [
            {"role": "user", "content": json.dumps({"patterns": compact})}
        ],
    }
    resp = _call_anthropic(payload)
    try:
        text = next(b["text"] for b in resp.get("content", []) if b.get("type") == "text")
        parsed = json.loads(text)
        return {
            "merges": list(parsed.get("merges", [])),
            "prune": list(parsed.get("prune", [])),
            "notes": str(parsed.get("notes", "")),
        }
    except (StopIteration, json.JSONDecodeError, KeyError, TypeError):
        return {"merges": [], "prune": [], "notes": "parse-failure"}
