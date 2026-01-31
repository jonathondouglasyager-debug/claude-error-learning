#!/usr/bin/env python3
"""
Command Validator Hook for Claude Code
Triggered by: PreToolUse (Bash only)
Blocks commands matching known error patterns and shows learned fixes.
"""

import json
import re
import sys
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
PATTERNS_DIR = BASE_DIR / "patterns"
ACTIVE_FILE = PATTERNS_DIR / "active.json"
ALLOWLIST_FILE = PATTERNS_DIR / "allowlist.json"
LEGACY_FILE = PATTERNS_DIR / "known-errors.json"  # Fallback for migration
CONFIG_FILE = BASE_DIR / "config.json"


def load_config():
    """Load plugin configuration."""
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"show_confidence": True}


def load_allowlist():
    """Load allowlist patterns - commands that should never be blocked."""
    if not ALLOWLIST_FILE.exists():
        return []
    try:
        with ALLOWLIST_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("patterns", [])
    except json.JSONDecodeError:
        return []


def is_allowed(command: str, allowlist: list) -> bool:
    """Check if command matches any allowlist pattern."""
    for pattern in allowlist:
        match_type = pattern.get("type", "prefix")
        match_pattern = pattern.get("pattern", "")

        if not match_pattern:
            continue

        if match_type == "prefix":
            if command.startswith(match_pattern):
                return True
        elif match_type == "exact":
            if command == match_pattern:
                return True
        elif match_type == "contains":
            if match_pattern in command:
                return True
        elif match_type == "regex":
            try:
                if re.search(match_pattern, command):
                    return True
            except re.error:
                pass

    return False


def load_patterns():
    """Load active patterns from merged active.json or fallback to legacy file."""
    # Try active.json first (new pattern packs system)
    if ACTIVE_FILE.exists():
        try:
            with ACTIVE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                patterns = data.get("patterns", [])
                if patterns:
                    return patterns
        except json.JSONDecodeError:
            pass

    # Fallback to legacy known-errors.json
    if LEGACY_FILE.exists():
        try:
            with LEGACY_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("patterns", [])
        except json.JSONDecodeError:
            pass

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


def format_block_message(pattern: dict, config: dict) -> str:
    """Format the block message with learned fix information."""
    message = pattern.get("message", "Command blocked by known error pattern.")
    learned_fix = pattern.get("learned_fix", pattern.get("suggestion", ""))
    confidence = pattern.get("confidence", 0)
    show_confidence = config.get("show_confidence", True)

    output = message

    if learned_fix:
        if show_confidence and confidence > 0:
            output += f"\nLEARNED FIX ({confidence}% confidence): {learned_fix}"
        else:
            output += f"\nLEARNED FIX: {learned_fix}"

    return output


def main():
    try:
        # Load config
        config = load_config()

        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract command from tool input
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if not command:
            # No command to validate, allow
            sys.exit(0)

        # Check allowlist first - if command is allowed, skip all blocking
        allowlist = load_allowlist()
        if is_allowed(command, allowlist):
            sys.exit(0)

        # Load blocking patterns
        patterns = load_patterns()

        # Check command against each pattern
        for pattern in patterns:
            if check_pattern(command, pattern):
                # Found a match - block the command
                message = format_block_message(pattern, config)

                # Write to stderr (Claude will see this)
                print(message, file=sys.stderr)

                # Exit 2 = block command and show stderr to Claude
                sys.exit(2)

        # No patterns matched - allow command
        sys.exit(0)

    except Exception:
        # On error, allow command (fail open, don't block Claude)
        sys.exit(0)


if __name__ == "__main__":
    main()
