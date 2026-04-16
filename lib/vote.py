"""Vote tracking and outcome-based promote/demote.

A pattern with >= down_threshold down-votes is auto-disabled. Up-votes
feed into the injector's ranking via error_count + fix_count + vote_up.
"""


def record_vote(pattern, direction):
    if direction not in ("up", "down"):
        raise ValueError(f"vote direction must be 'up' or 'down', got {direction!r}")
    key = "vote_up" if direction == "up" else "vote_down"
    pattern[key] = (pattern.get(key) or 0) + 1
    return pattern


def apply_vote_thresholds(patterns, down_threshold=3):
    disabled = []
    for p in patterns:
        if not p.get("enabled", True):
            continue
        if (p.get("vote_down") or 0) >= down_threshold:
            p["enabled"] = False
            disabled.append(p.get("id", "<unknown>"))
    return disabled
