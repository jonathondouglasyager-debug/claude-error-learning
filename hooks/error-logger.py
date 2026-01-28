#!/usr/bin/env python3
"""
Error Logger Hook for Claude Code
Triggered by: PostToolUseFailure
Appends error records to data/errors.jsonl
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERRORS_FILE = DATA_DIR / "errors.jsonl"


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
        tool_response = input_data.get("tool_response", "")
        session_id = input_data.get("session_id", "unknown")
        project_dir = input_data.get("project_dir", "")

        # Convert tool_response to string if it's not already
        if isinstance(tool_response, dict):
            error_text = json.dumps(tool_response)
        else:
            error_text = str(tool_response)

        # Build error record
        error_record = {
            "id": generate_error_id(),
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": session_id,
            "category": categorize_error(error_text),
            "tool": tool_name,
            "input": tool_input,
            "error": error_text[:2000],  # Truncate very long errors
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
