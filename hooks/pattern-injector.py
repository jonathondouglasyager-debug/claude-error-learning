#!/usr/bin/env python3
"""UserPromptSubmit hook: inject top-k learned rules as context.

Reads stdin JSON { "prompt": str, "session_id": str }. Writes the rendered
rule summary to stdout; Claude Code wraps stdout into the session context.
Exits 0 on success (injection or empty); non-zero only on truly unexpected errors.
"""
import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from lib.renderer import render_as_natural_language
from lib.ranker import top_k

_DEFAULT_CONFIG = {
    "injection_enabled": True,
    "injection_top_k": 10,
    "injection_token_cap": 400,
    "injection_min_score": 0.0,
    "injection_scope": "top_learned",
}


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _config():
    path = os.environ.get("ERROR_LEARNING_CONFIG_PATH") or os.path.join(_PLUGIN_ROOT, "config.json")
    cfg = dict(_DEFAULT_CONFIG)
    cfg.update(_load_json(path, {}))
    return cfg


def _patterns():
    path = os.environ.get("ERROR_LEARNING_PATTERNS_PATH") or os.path.join(
        _PLUGIN_ROOT, "patterns", "active.json"
    )
    raw = _load_json(path, {})
    if isinstance(raw, list):
        return raw
    return raw.get("patterns", [])


def _filter_by_scope(patterns, scope):
    # drop patterns flagged ineligible (Task 8 decay sets injection_eligible=False)
    patterns = [p for p in patterns if p.get("injection_eligible", True)]
    if scope == "all_active":
        return patterns
    if scope == "learned_only":
        return [p for p in patterns if p.get("category") == "learned"]
    if scope == "high_confidence":
        return [p for p in patterns if (p.get("confidence") or 0) >= 70]
    # "top_learned" default — ranked by triggers within the learned set
    learned = [p for p in patterns if p.get("category") == "learned"]
    learned.sort(key=lambda p: p.get("error_count", 0) + p.get("fix_count", 0), reverse=True)
    return learned


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0  # never block the user's prompt
    cfg = _config()
    if not cfg.get("injection_enabled", True):
        return 0

    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return 0

    scope_patterns = _filter_by_scope(_patterns(), cfg.get("injection_scope"))
    if not scope_patterns:
        return 0

    ranked = top_k(
        prompt,
        scope_patterns,
        k=cfg.get("injection_top_k", 10),
        min_score=cfg.get("injection_min_score", 0.0),
    )
    if not ranked:
        return 0

    rendered = render_as_natural_language(ranked, max_tokens=cfg.get("injection_token_cap", 400))
    if rendered.strip():
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
