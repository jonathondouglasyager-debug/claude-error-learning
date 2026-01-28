# Error Learning System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build hooks that automatically detect, log, and prevent repeated Claude Code errors.

**Architecture:** Two Python hooks (error-logger + command-validator) with JSON data files. PostToolUseFailure captures all errors to JSONL. PreToolUse blocks known-bad Bash patterns before execution.

**Tech Stack:** Python 3, JSON/JSONL, Claude Code hooks system

---

## Task 1: Create the Error Logger Hook

**Files:**
- Create: `hooks/error-logger.py`

**Step 1: Create the error logger script**

```python
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
```

**Step 2: Verify the file was created**

Check that `hooks/error-logger.py` exists and has correct content.

**Step 3: Test the script standalone**

Run manually with test input to verify it works:

```powershell
echo '{"tool_name":"Bash","tool_input":{"command":"test && cmd"},"tool_response":"Error: token not valid","session_id":"test123","project_dir":"C:\\test"}' | python hooks/error-logger.py
```

**Step 4: Verify error was logged**

Check `data/errors.jsonl` contains the test record.

---

## Task 2: Create the Known Patterns File

**Files:**
- Create: `patterns/known-errors.json`

**Step 1: Create initial patterns file with common Windows/PowerShell errors**

```json
{
  "version": 1,
  "description": "Known error patterns for prevention. Curated from errors.jsonl.",
  "patterns": [
    {
      "id": "windows_bash_chaining",
      "name": "Bash && chaining on Windows",
      "category": "syntax_error",
      "tool": "Bash",
      "match": {
        "type": "contains",
        "pattern": "&&"
      },
      "message": "BLOCKED: Use ';' or run commands separately on Windows. '&&' is bash syntax, not PowerShell.",
      "suggestion": "cmd1; cmd2",
      "added": "2026-01-28",
      "occurrences": 0
    },
    {
      "id": "bash_rm_command",
      "name": "Using rm instead of Remove-Item",
      "category": "syntax_error",
      "tool": "Bash",
      "match": {
        "type": "regex",
        "pattern": "^rm\\s+"
      },
      "message": "BLOCKED: Use 'Remove-Item' instead of 'rm' on Windows PowerShell.",
      "suggestion": "Remove-Item \"path\"",
      "added": "2026-01-28",
      "occurrences": 0
    },
    {
      "id": "bash_del_command",
      "name": "Using del without quotes",
      "category": "syntax_error",
      "tool": "Bash",
      "match": {
        "type": "regex",
        "pattern": "^del\\s+[^\"']"
      },
      "message": "BLOCKED: Use 'Remove-Item \"path\"' instead of 'del' on Windows.",
      "suggestion": "Remove-Item \"path\"",
      "added": "2026-01-28",
      "occurrences": 0
    },
    {
      "id": "bash_ls_flags",
      "name": "Using ls with Unix flags",
      "category": "syntax_error",
      "tool": "Bash",
      "match": {
        "type": "regex",
        "pattern": "^ls\\s+-[a-zA-Z]"
      },
      "message": "BLOCKED: Use 'Get-ChildItem' or 'dir' instead of 'ls -flags' on Windows.",
      "suggestion": "Get-ChildItem or dir",
      "added": "2026-01-28",
      "occurrences": 0
    }
  ]
}
```

**Step 2: Verify the file was created**

Check that `patterns/known-errors.json` exists and is valid JSON.

---

## Task 3: Create the Command Validator Hook

**Files:**
- Create: `hooks/command-validator.py`

**Step 1: Create the command validator script**

```python
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
```

**Step 2: Verify the file was created**

Check that `hooks/command-validator.py` exists and has correct content.

**Step 3: Test the validator with a bad command**

```powershell
echo '{"tool_input":{"command":"git add . && git commit"}}' | python hooks/command-validator.py
```

Expected: Exit code 2, stderr shows "BLOCKED: Use ';' or run commands separately..."

**Step 4: Test the validator with a good command**

```powershell
echo '{"tool_input":{"command":"git status"}}' | python hooks/command-validator.py
```

Expected: Exit code 0, no output.

---

## Task 4: Create the Hook Configuration

**Files:**
- Create: `.claude/settings.json` (in SUPER_POWERS_PROJECT)

**Step 1: Create the .claude directory**

```powershell
New-Item -ItemType Directory -Force -Path ".claude"
```

**Step 2: Create the settings.json file**

```json
{
  "hooks": {
    "PostToolUseFailure": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:\\Users\\jonat\\Desktop\\SUPER_POWERS_PROJECT\\hooks\\error-logger.py\""
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:\\Users\\jonat\\Desktop\\SUPER_POWERS_PROJECT\\hooks\\command-validator.py\""
          }
        ]
      }
    ]
  }
}
```

**Step 3: Verify the configuration file**

Check that `.claude/settings.json` exists and is valid JSON.

---

## Task 5: Create Empty Data File

**Files:**
- Create: `data/errors.jsonl`

**Step 1: Create empty JSONL file**

Create an empty file (or with a comment line) at `data/errors.jsonl`.

This ensures the data directory structure exists for the logger.

---

## Task 6: Integration Test - Error Logging

**Purpose:** Verify the error logger captures real failures.

**Step 1: Open Claude Code in SUPER_POWERS_PROJECT directory**

The project-level `.claude/settings.json` should activate.

**Step 2: Trigger a deliberate error**

Ask Claude to run a command that will fail, like:
```
Run: nonexistent-command-xyz
```

**Step 3: Check errors.jsonl**

Verify `data/errors.jsonl` contains a new error record with:
- Correct tool name
- The failed command
- Error message captured

---

## Task 7: Integration Test - Prevention

**Purpose:** Verify the command validator blocks known-bad patterns.

**Step 1: Trigger a pattern match**

Ask Claude to run:
```
Run: echo test && echo test2
```

**Step 2: Observe behavior**

Expected:
- Command is BLOCKED before execution
- Claude sees the message: "BLOCKED: Use ';' or run commands separately..."
- Claude retries with correct syntax

**Step 3: Verify no error logged**

Since the command was blocked (never executed), it should NOT appear in `errors.jsonl`.

---

## Task 8: Document Results

**Files:**
- Update: `docs/plans/2026-01-28-error-learning-system-design.md`

**Step 1: Update implementation checklist**

Mark completed items in the design doc:
- [x] Create `hooks/error-logger.py`
- [x] Create `hooks/command-validator.py`
- [x] Create `patterns/known-errors.json` with initial patterns
- [x] Create `.claude/settings.json` with hook configuration
- [x] Test error logging
- [x] Test prevention
- [x] Document testing results

**Step 2: Add testing notes**

Document what worked, any issues found, and next steps.

---

## Summary

| Task | Component | Purpose |
|------|-----------|---------|
| 1 | error-logger.py | Captures all tool failures to JSONL |
| 2 | known-errors.json | Stores curated patterns for prevention |
| 3 | command-validator.py | Blocks known-bad commands before execution |
| 4 | .claude/settings.json | Activates hooks for this project |
| 5 | errors.jsonl | Empty data file for logger output |
| 6 | Integration test | Verify logging works |
| 7 | Integration test | Verify prevention works |
| 8 | Documentation | Record results |

---

## After Implementation

Once all tasks pass:
1. Use the system for a few sessions
2. Review `errors.jsonl` for new patterns
3. Add valuable patterns to `known-errors.json`
4. When stable, promote hooks to global `~/.claude/settings.json`
