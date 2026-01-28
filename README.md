# Claude Error Learning System

Automated error detection, learning, and prevention for Claude Code via hooks.

## Problem

Claude Code makes mistakes (wrong commands, syntax errors) and iterates until the correct command works. The same mistakes happen across sessions because there's no feedback loop. Each failed iteration wastes tokens and time.

## Solution

A complete feedback loop that:
1. **Detects** - Captures all tool failures to `data/errors.jsonl`
2. **Learns** - Auto-curates recurring errors into prevention patterns
3. **Prevents** - Blocks known-bad commands before execution

## The Complete Loop

```
Claude uses wrong command
        ↓
Command FAILS
        ↓
[PostToolUseFailure] error-logger.py → data/errors.jsonl
        ↓
Session ends
        ↓
[SessionEnd] error-curator.py → patterns/known-errors.json
        ↓
Next session, Claude tries same mistake
        ↓
[PreToolUse] command-validator.py → BLOCKED
        ↓
Claude uses correct syntax immediately
```

**Result:** Errors are caught once, learned automatically, prevented forever.

## Installation

1. Clone this repo
2. Copy `.claude/settings.json` to your project (or merge with existing)
3. Update the paths in settings.json to point to your clone location

Or for global installation, merge hooks into `~/.claude/settings.json`.

## Files

| File | Purpose |
|------|---------|
| `hooks/error-logger.py` | Captures all tool failures to JSONL |
| `hooks/error-curator.py` | Auto-promotes recurring errors to patterns |
| `hooks/command-validator.py` | Blocks known-bad commands before execution |
| `patterns/known-errors.json` | Curated patterns for prevention |
| `data/errors.jsonl` | Raw error log (local, not tracked) |
| `.claude/settings.json` | Hook configuration |

## Hooks Configuration

```json
{
  "hooks": {
    "PostToolUseFailure": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "python path/to/error-logger.py" }] }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "python path/to/command-validator.py" }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "python path/to/error-curator.py --auto" }] }
    ]
  }
}
```

## Initial Patterns (Windows/PowerShell)

| Pattern | Blocks | Suggestion |
|---------|--------|------------|
| `windows_bash_chaining` | `&&` in commands | Use `;` or run separately |
| `bash_rm_command` | `rm` command | Use `Remove-Item` |
| `bash_del_command` | `del` unquoted | Use `Remove-Item "path"` |
| `bash_ls_flags` | `ls -flags` | Use `Get-ChildItem` |

## Manual Curation

```bash
# Review all potential patterns
python hooks/error-curator.py --review

# Add all new patterns
python hooks/error-curator.py --add-all

# Add specific pattern
python hooks/error-curator.py --add <signature>
```

## Adding Custom Patterns

Edit `patterns/known-errors.json`:

```json
{
  "id": "unique_id",
  "name": "Human readable name",
  "category": "syntax_error",
  "tool": "Bash",
  "match": {
    "type": "contains",
    "pattern": "pattern to match"
  },
  "message": "BLOCKED: Explanation shown to Claude",
  "suggestion": "Correct way to do it"
}
```

Match types: `contains`, `regex`, `exact`

## Token Savings

| Scenario | Tokens |
|----------|--------|
| Without prevention | ~210-610 per error |
| With prevention | ~60 per error |
| **Savings** | **70-90%** |

## How It Works

- **error-logger.py**: Receives JSON from Claude Code on tool failure, extracts command and error, appends to JSONL
- **error-curator.py**: Analyzes error log, groups by command signature, promotes patterns with 2+ occurrences
- **command-validator.py**: Loads patterns, checks incoming commands, blocks matches with helpful message

## Future Work

- Outcome-based pattern scoring (track which patterns actually help)
- SessionStart context injection (proactive prevention)
- Cross-platform pattern sets (Linux, macOS)

## License

MIT
