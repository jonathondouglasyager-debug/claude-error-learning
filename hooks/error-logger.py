#!/usr/bin/env python3
"""
Error Logger Hook for Claude Code
Triggered by: PostToolUseFailure
Appends error records to data/errors.jsonl with awaiting_fix flag for fix-tracker pairing.
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


def generate_error_id():
    """Generate unique error ID based on timestamp."""
    now = datetime.now()
    return f"err_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond // 1000:03d}"


def categorize_error(error_text: str) -> str:
    """Categorize error based on error message content."""
    error_lower = error_text.lower()

    if any(kw in error_lower for kw in ["not recognized", "not found", "cannot find"]):
        return "path_error"
    elif any(kw in error_lower for kw in ["permission", "access denied", "not permitted"]):
        return "permission_error"
    elif any(kw in error_lower for kw in ["syntax", "token", "unexpected", "invalid"]):
        return "syntax_error"
    else:
        return "action_error"


def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract fields from Claude Code hook payload
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        # Claude Code sends error in "error" field for PostToolUseFailure
        error_text = input_data.get("error") or input_data.get("tool_response") or ""
        session_id = input_data.get("session_id", "unknown")
        project_dir = input_data.get("cwd", input_data.get("project_dir", ""))

        # Convert error_text to string if it's not already
        if isinstance(error_text, dict):
            error_text = json.dumps(error_text)
        else:
            error_text = str(error_text)

        # Load config
        config = load_config()
        track_fixes = config.get("track_fixes", True)

        # Build error record
        error_record = {
            "id": generate_error_id(),
            "type": "error",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": session_id,
            "category": categorize_error(error_text),
            "tool": tool_name,
            "input": tool_input,
            "error": error_text[:2000],  # Truncate very long errors
            "awaiting_fix": track_fixes,  # Signal fix-tracker to watch for fix
            "context": {
                "working_dir": project_dir,
                "project": Path(project_dir).name if project_dir else "unknown"
            }
        }

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Append to JSONL file
        with ERRORS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(error_record) + "\n")

        # Exit 0 = success, non-blocking
        sys.exit(0)

    except Exception:
        # Fail silently - don't interrupt Claude
        sys.exit(0)


if __name__ == "__main__":
    main()
