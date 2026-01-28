#!/usr/bin/env python3
"""
Error Curator for Claude Code
Can run as:
  A) SessionEnd hook (automatic) - conservative, only adds patterns seen 2+ times
  B) Manual invocation - interactive, proposes all potential patterns

Usage:
  Automatic (SessionEnd): python error-curator.py --auto
  Manual review:          python error-curator.py --review
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERRORS_FILE = DATA_DIR / "errors.jsonl"
PATTERNS_FILE = BASE_DIR / "patterns" / "known-errors.json"
CURATED_LOG = DATA_DIR / "curated.log"

# Minimum occurrences for auto-curation
AUTO_THRESHOLD = 2


def load_errors():
    """Load all errors from JSONL file."""
    errors = []
    if not ERRORS_FILE.exists():
        return errors

    with ERRORS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    errors.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return errors


def load_patterns():
    """Load existing patterns."""
    if not PATTERNS_FILE.exists():
        return {"version": 1, "patterns": []}

    with PATTERNS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_patterns(data):
    """Save patterns to file."""
    with PATTERNS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_existing_pattern_ids(patterns_data):
    """Get set of existing pattern IDs."""
    return {p["id"] for p in patterns_data.get("patterns", [])}


def extract_command_signature(command):
    """
    Extract a signature from a command for grouping similar errors.
    Removes variable parts like paths, filenames, arguments.
    """
    if not command:
        return None

    # Common patterns to normalize
    patterns = [
        # && chaining
        (r'.*&&.*', 'bash_and_chaining'),
        # rm command
        (r'^rm\s+', 'bash_rm_command'),
        # del command
        (r'^del\s+', 'bash_del_command'),
        # ls with flags
        (r'^ls\s+-', 'bash_ls_flags'),
        # cat command
        (r'^cat\s+', 'bash_cat_command'),
        # grep command (should use Grep tool)
        (r'^grep\s+', 'bash_grep_command'),
        # find command (should use Glob tool)
        (r'^find\s+', 'bash_find_command'),
        # echo for file writing
        (r'^echo\s+.*>', 'bash_echo_redirect'),
        # touch command
        (r'^touch\s+', 'bash_touch_command'),
        # mkdir without -p equivalent
        (r'^mkdir\s+(?!-p)', 'bash_mkdir_command'),
    ]

    for pattern, signature in patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return signature

    # Default: use first word as signature
    first_word = command.split()[0] if command.split() else None
    return f"cmd_{first_word}" if first_word else None


def generate_pattern_entry(signature, commands, errors):
    """Generate a pattern entry for known-errors.json."""
    # Analyze the commands to find common patterns
    sample_command = commands[0]
    sample_error = errors[0] if errors else ""

    # Pattern templates based on signature
    templates = {
        'bash_and_chaining': {
            "match": {"type": "contains", "pattern": "&&"},
            "message": "BLOCKED: Use ';' or run commands separately on Windows. '&&' is bash syntax.",
            "suggestion": "cmd1; cmd2"
        },
        'bash_rm_command': {
            "match": {"type": "regex", "pattern": "^rm\\s+"},
            "message": "BLOCKED: Use 'Remove-Item' instead of 'rm' on Windows.",
            "suggestion": "Remove-Item \"path\""
        },
        'bash_del_command': {
            "match": {"type": "regex", "pattern": "^del\\s+"},
            "message": "BLOCKED: Use 'Remove-Item \"path\"' instead of 'del'.",
            "suggestion": "Remove-Item \"path\""
        },
        'bash_ls_flags': {
            "match": {"type": "regex", "pattern": "^ls\\s+-[a-zA-Z]"},
            "message": "BLOCKED: Use 'Get-ChildItem' or 'dir' instead of 'ls -flags'.",
            "suggestion": "Get-ChildItem or dir"
        },
        'bash_cat_command': {
            "match": {"type": "regex", "pattern": "^cat\\s+"},
            "message": "BLOCKED: Use the Read tool instead of 'cat' for reading files.",
            "suggestion": "Use Read tool"
        },
        'bash_grep_command': {
            "match": {"type": "regex", "pattern": "^grep\\s+"},
            "message": "BLOCKED: Use the Grep tool instead of 'grep' command.",
            "suggestion": "Use Grep tool"
        },
        'bash_find_command': {
            "match": {"type": "regex", "pattern": "^find\\s+"},
            "message": "BLOCKED: Use the Glob tool instead of 'find' command.",
            "suggestion": "Use Glob tool"
        },
        'bash_echo_redirect': {
            "match": {"type": "regex", "pattern": "^echo\\s+.*>"},
            "message": "BLOCKED: Use the Write tool instead of 'echo >' for creating files.",
            "suggestion": "Use Write tool"
        },
        'bash_touch_command': {
            "match": {"type": "regex", "pattern": "^touch\\s+"},
            "message": "BLOCKED: Use 'New-Item' or Write tool instead of 'touch'.",
            "suggestion": "New-Item \"path\" -ItemType File"
        },
        'bash_mkdir_command': {
            "match": {"type": "regex", "pattern": "^mkdir\\s+(?!-p)"},
            "message": "BLOCKED: Use 'New-Item -ItemType Directory -Force' or mkdir -p equivalent.",
            "suggestion": "New-Item -ItemType Directory -Force -Path \"path\""
        },
    }

    template = templates.get(signature, {
        "match": {"type": "contains", "pattern": sample_command.split()[0] if sample_command else ""},
        "message": f"BLOCKED: This command pattern has failed {len(commands)} times. Review and fix.",
        "suggestion": "Check error log for details"
    })

    return {
        "id": signature,
        "name": signature.replace("_", " ").title(),
        "category": "syntax_error",
        "tool": "Bash",
        "match": template["match"],
        "message": template["message"],
        "suggestion": template["suggestion"],
        "added": datetime.now().strftime("%Y-%m-%d"),
        "occurrences": len(commands),
        "auto_curated": True
    }


def analyze_errors(errors):
    """Analyze errors and group by signature."""
    grouped = defaultdict(lambda: {"commands": [], "errors": []})

    for error in errors:
        tool_input = error.get("input", {})
        command = tool_input.get("command", "")
        error_msg = error.get("error", "")

        if not command:
            continue

        signature = extract_command_signature(command)
        if signature:
            grouped[signature]["commands"].append(command)
            grouped[signature]["errors"].append(error_msg)

    return grouped


def auto_curate():
    """
    Automatic curation (SessionEnd hook).
    Only adds patterns that have occurred 2+ times.
    """
    errors = load_errors()
    if not errors:
        return

    patterns_data = load_patterns()
    existing_ids = get_existing_pattern_ids(patterns_data)
    grouped = analyze_errors(errors)

    added = []
    for signature, data in grouped.items():
        # Skip if already exists
        if signature in existing_ids:
            continue

        # Only auto-add if threshold met
        if len(data["commands"]) >= AUTO_THRESHOLD:
            pattern = generate_pattern_entry(signature, data["commands"], data["errors"])
            patterns_data["patterns"].append(pattern)
            added.append(signature)

    if added:
        save_patterns(patterns_data)

        # Log what was added
        with CURATED_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat()}] Auto-curated {len(added)} patterns: {', '.join(added)}\n")

    # Exit silently (non-blocking for SessionEnd)
    sys.exit(0)


def manual_review():
    """
    Manual review mode.
    Outputs proposed patterns for user review.
    """
    errors = load_errors()
    if not errors:
        print("No errors found in errors.jsonl")
        return

    patterns_data = load_patterns()
    existing_ids = get_existing_pattern_ids(patterns_data)
    grouped = analyze_errors(errors)

    print(f"\n=== Error Curator Review ===")
    print(f"Total errors in log: {len(errors)}")
    print(f"Existing patterns: {len(existing_ids)}")
    print(f"Error signatures found: {len(grouped)}\n")

    new_patterns = []
    for signature, data in sorted(grouped.items(), key=lambda x: -len(x[1]["commands"])):
        count = len(data["commands"])
        status = "EXISTS" if signature in existing_ids else "NEW"

        print(f"[{status}] {signature}: {count} occurrence(s)")
        if status == "NEW":
            print(f"    Sample: {data['commands'][0][:80]}...")
            new_patterns.append((signature, data))

    if new_patterns:
        print(f"\n--- {len(new_patterns)} new patterns can be added ---")
        print("\nTo add all new patterns, run:")
        print("  python error-curator.py --add-all")
        print("\nOr add specific pattern:")
        print("  python error-curator.py --add <signature>")
    else:
        print("\nNo new patterns to add.")


def add_all_patterns():
    """Add all new patterns to known-errors.json."""
    errors = load_errors()
    patterns_data = load_patterns()
    existing_ids = get_existing_pattern_ids(patterns_data)
    grouped = analyze_errors(errors)

    added = []
    for signature, data in grouped.items():
        if signature not in existing_ids:
            pattern = generate_pattern_entry(signature, data["commands"], data["errors"])
            patterns_data["patterns"].append(pattern)
            added.append(signature)

    if added:
        save_patterns(patterns_data)
        print(f"Added {len(added)} patterns: {', '.join(added)}")
    else:
        print("No new patterns to add.")


def add_pattern(signature):
    """Add a specific pattern by signature."""
    errors = load_errors()
    patterns_data = load_patterns()
    existing_ids = get_existing_pattern_ids(patterns_data)
    grouped = analyze_errors(errors)

    if signature in existing_ids:
        print(f"Pattern '{signature}' already exists.")
        return

    if signature not in grouped:
        print(f"Pattern '{signature}' not found in errors.")
        return

    data = grouped[signature]
    pattern = generate_pattern_entry(signature, data["commands"], data["errors"])
    patterns_data["patterns"].append(pattern)
    save_patterns(patterns_data)
    print(f"Added pattern: {signature}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python error-curator.py --auto      # Automatic (SessionEnd hook)")
        print("  python error-curator.py --review    # Manual review")
        print("  python error-curator.py --add-all   # Add all new patterns")
        print("  python error-curator.py --add <sig> # Add specific pattern")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "--auto":
        auto_curate()
    elif mode == "--review":
        manual_review()
    elif mode == "--add-all":
        add_all_patterns()
    elif mode == "--add" and len(sys.argv) > 2:
        add_pattern(sys.argv[2])
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
