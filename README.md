# Claude Error Learning System

Automated error detection and prevention for Claude Code via hooks.

## Problem

Claude Code makes mistakes (wrong commands, syntax errors) and iterates until the correct command works. The same mistakes happen across sessions because there's no feedback loop. Each failed iteration wastes tokens and time.

## Solution

Two Python hooks that automatically:
1. **Detect & Log** - Capture all tool failures to `data/errors.jsonl`
2. **Prevent** - Block known-bad command patterns before execution

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    PREVENTION LAYER                      │
│  PreToolUse Hook checks commands BEFORE execution        │
│  Blocks known-bad patterns with helpful message          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    DETECTION LAYER                       │
│  PostToolUseFailure Hook captures ALL failures           │
│  Appends to errors.jsonl for pattern discovery           │
└─────────────────────────────────────────────────────────┘
```

## Installation

1. Clone this repo
2. Copy `.claude/settings.json` to your project (or merge with existing)
3. Update the paths in settings.json to point to your clone location

Or copy hooks globally:
```json
// ~/.claude/settings.json
{
  "hooks": {
    "PostToolUseFailure": [...],
    "PreToolUse": [...]
  }
}
```

## Files

| File | Purpose |
|------|---------|
| `hooks/error-logger.py` | Captures all tool failures to JSONL |
| `hooks/command-validator.py` | Blocks known-bad commands before execution |
| `patterns/known-errors.json` | Curated patterns for prevention |
| `data/errors.jsonl` | Raw error log (append-only) |
| `.claude/settings.json` | Hook configuration |

## Initial Patterns

| Pattern | Blocks |
|---------|--------|
| `windows_bash_chaining` | Commands containing `&&` |
| `bash_rm_command` | Commands starting with `rm ` |
| `bash_del_command` | Commands starting with `del ` (unquoted) |
| `bash_ls_flags` | Commands starting with `ls -` |

## Adding Patterns

Edit `patterns/known-errors.json`:

```json
{
  "id": "unique_id",
  "name": "Human readable name",
  "category": "syntax_error",
  "tool": "Bash",
  "match": {
    "type": "contains",  // or "regex" or "exact"
    "pattern": "pattern to match"
  },
  "message": "BLOCKED: Explanation shown to Claude",
  "suggestion": "Correct way to do it"
}
```

## Token Savings

Without prevention: ~210-610 tokens per error (attempt + full error + reasoning + retry)

With prevention: ~60 tokens (block message + retry)

**Net effect:** 70-90% token reduction per prevented error.

## Future Work

- Error curator agent to auto-propose patterns
- Outcome-based pattern scoring
- SessionStart context injection for proactive prevention
