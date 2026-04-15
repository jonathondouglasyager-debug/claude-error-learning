"""Render patterns as compact natural-language rules with a token cap."""

_HEADER = (
    "Learned rules from this project's prior errors. Prefer the suggested "
    "fix when you would otherwise run a matching command:"
)


def estimate_tokens(text):
    """Rough heuristic: ~4 chars per token."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def truncate_to_tokens(text, max_tokens):
    if max_tokens <= 0 or not text:
        return ""
    lines = text.splitlines()
    out = []
    running = 0
    for line in lines:
        cost = estimate_tokens(line) + 1
        if running + cost > max_tokens:
            break
        out.append(line)
        running += cost
    return "\n".join(out)


def render_as_natural_language(patterns, max_tokens=None):
    if not patterns:
        return ""
    lines = [_HEADER, ""]
    for p in patterns:
        msg = (p.get("message") or "").strip().rstrip(".")
        fix = (p.get("learned_fix") or "").strip().rstrip(".")
        if not msg and not fix:
            continue
        if msg and fix:
            lines.append(f"- {msg}. Fix: {fix}.")
        else:
            lines.append(f"- {msg or fix}.")
    body = "\n".join(lines)
    if max_tokens is not None:
        body = truncate_to_tokens(body, max_tokens)
    return body
