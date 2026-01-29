#!/usr/bin/env python3
"""
Fix Tracker Hook for Claude Code
Triggered by: PostToolUse (Bash)
Captures successful commands that follow errors, linking them as fixes.

Logic:
1. Check if the tool use was successful (not an error)
2. Read last error entry from errors.jsonl
3. If awaiting_fix=true AND same session AND same tool type
4. Log this as the fix, linked to the error ID
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERRORS_FILE = DATA_DIR / "errors.jsonl"
CONFIG_FILE = BASE_DIR / "config.json"


def load_config():
    """Load plugin configuration."""
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"track_fixes": True}


def generate_fix_id():
    """Generate unique fix ID based on timestamp."""
    now = datetime.now()
    return f"fix_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond // 1000:03d}"


def get_last_error():
    """Get the last error entry from errors.jsonl."""
    if not ERRORS_FILE.exists():
        return None

    last_error = None
    with ERRORS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "error":
                        last_error = entry
                except json.JSONDecodeError:
                    continue
    return last_error


def update_error_awaiting_fix(error_id, linked_fix_id):
    """Update the error entry to mark it as fixed and no longer awaiting."""
    if not ERRORS_FILE.exists():
        return

    entries = []
    with ERRORS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("id") == error_id:
                        entry["awaiting_fix"] = False
                        entry["linked_fix"] = linked_fix_id
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

    # Rewrite the file with updated entries
    with ERRORS_FILE.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def main():
    try:
        # Check if fix tracking is enabled
        config = load_config()
        if not config.get("track_fixes", True):
            sys.exit(0)

        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract fields from Claude Code hook payload
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")
        session_id = input_data.get("session_id", "unknown")

        # Check if this was a failure - if so, skip (PostToolUseFailure handles it)
        # PostToolUse fires for both success and failure, but we only want successes
        if isinstance(tool_response, dict):
            response_text = str(tool_response)
        else:
            response_text = str(tool_response)

        # Common error indicators that suggest this was a failure
        error_indicators = [
            "error:", "Error:", "ERROR:",
            "not recognized", "not found", "cannot find",
            "permission denied", "access denied",
            "failed", "Failed", "FAILED",
            "exception", "Exception",
            "command not found",
            "No such file or directory"
        ]

        if any(indicator in response_text for indicator in error_indicators):
            # This looks like a failure, not a success - skip
            sys.exit(0)

        # Get the command that succeeded
        command = tool_input.get("command", "")
        if not command:
            sys.exit(0)

        # Get the last error entry
        last_error = get_last_error()
        if not last_error:
            sys.exit(0)

        # Check if conditions match for linking this as a fix
        if not last_error.get("awaiting_fix", False):
            sys.exit(0)

        if last_error.get("session_id") != session_id:
            sys.exit(0)

        if last_error.get("tool") != tool_name:
            sys.exit(0)

        # This looks like a fix! Log it
        fix_id = generate_fix_id()
        fix_record = {
            "id": fix_id,
            "type": "fix",
            "linked_error": last_error.get("id"),
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": session_id,
            "tool": tool_name,
            "command": command
        }

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Append fix record to JSONL file
        with ERRORS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fix_record) + "\n")

        # Update the original error to mark it as fixed
        update_error_awaiting_fix(last_error.get("id"), fix_id)

        # Exit 0 = success, non-blocking
        sys.exit(0)

    except Exception:
        # Fail silently - don't interrupt Claude
        sys.exit(0)


if __name__ == "__main__":
    main()
