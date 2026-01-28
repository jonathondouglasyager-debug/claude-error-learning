#!/usr/bin/env python3
"""
Command Validator Hook for Claude Code
Triggered by: PreToolUse (Bash only)
Blocks commands matching known error patterns
"""

import json
import re
import sys
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
PATTERNS_FILE = BASE_DIR / "patterns" / "known-errors.json"


def load_patterns():
    """Load known error patterns from JSON file."""
    try:
        with PATTERNS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("patterns", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def check_pattern(command: str, pattern: dict) -> bool:
    """Check if command matches a pattern."""
    match_config = pattern.get("match", {})
    match_type = match_config.get("type", "contains")
    match_pattern = match_config.get("pattern", "")

    if not match_pattern:
        return False

    if match_type == "contains":
        return match_pattern in command
    elif match_type == "exact":
        return command == match_pattern
    elif match_type == "regex":
        try:
            return bool(re.search(match_pattern, command))
        except re.error:
            return False

    return False


def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract command from tool input
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if not command:
            # No command to validate, allow
            sys.exit(0)

        # Load patterns
        patterns = load_patterns()

        # Check command against each pattern
        for pattern in patterns:
            if check_pattern(command, pattern):
                # Found a match - block the command
                message = pattern.get("message", "Command blocked by known error pattern.")
                suggestion = pattern.get("suggestion", "")

                # Write to stderr (Claude will see this)
                print(f"{message}", file=sys.stderr)
                if suggestion:
                    print(f"Suggestion: {suggestion}", file=sys.stderr)

                # Exit 2 = block command and show stderr to Claude
                sys.exit(2)

        # No patterns matched - allow command
        sys.exit(0)

    except Exception as e:
        # On error, allow command (fail open, don't block Claude)
        sys.exit(0)


if __name__ == "__main__":
    main()
