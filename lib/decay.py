"""Decay: mark patterns stale beyond max_age_days as ineligible for injection."""
from datetime import datetime, timedelta, timezone


def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def demote_stale_patterns(patterns, max_age_days=30):
    """Mutates `patterns` in place. Returns IDs demoted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    demoted = []
    for p in patterns:
        if not p.get("injection_eligible", True):
            continue
        ts = _parse_iso(p.get("last_triggered_at"))
        if ts is None:
            continue
        if ts < cutoff:
            p["injection_eligible"] = False
            demoted.append(p.get("id", "<unknown>"))
    return demoted
