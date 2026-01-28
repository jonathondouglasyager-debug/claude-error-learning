# Error Learning System Design

**Date:** 2026-01-28
**Status:** Approved
**Goal:** Reduce wasted time and tokens by automatically detecting, logging, and preventing repeated Claude Code errors.

---

## Problem Statement

Claude Code makes mistakes (wrong commands, syntax errors) and iterates until the correct command works. The same mistakes happen across sessions because there's no feedback loop. Each failed iteration wastes tokens and time.

**Desired outcome:** Errors are caught once, logged, and prevented from recurring in all future sessions.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DETECTION LAYER                          │
│  PostToolUseFailure Hook (automatic, real-time)             │
│  - Fires when ANY tool fails                                │
│  - Captures full error context                              │
│  - Appends to errors.jsonl                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LOGGING LAYER                           │
│  data/errors.jsonl (append-only raw log)                    │
│  - One JSON object per line                                 │
│  - Machine-parseable, scriptable                            │
│  - No Obsidian dependency                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PREVENTION LAYER                          │
│  PreToolUse Hook + patterns/known-errors.json               │
│  - Checks commands BEFORE execution                         │
│  - Blocks known-bad patterns with helpful message           │
│  - Claude sees message, retries correctly                   │
│  - 70-90% token reduction per prevented error               │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
SUPER_POWERS_PROJECT/
├── hooks/
│   ├── error-logger.py      # PostToolUseFailure hook
│   └── command-validator.py # PreToolUse hook (prevention)
├── data/
│   └── errors.jsonl         # Raw error log
├── patterns/
│   └── known-errors.json    # Curated patterns for prevention
├── docs/
│   └── plans/
│       └── 2026-01-28-error-learning-system-design.md
└── .claude/
    └── settings.json        # Hook configuration (sandboxed)
```

---

## Component Specifications

### 1. Error Record Format (errors.jsonl)

Each line is one JSON object:

```json
{
  "id": "err_20260128_124532_001",
  "timestamp": "2026-01-28T12:45:32.123Z",
  "session_id": "abc123",
  "category": "action_error",
  "tool": "Bash",
  "input": {
    "command": "cmd1 && cmd2",
    "description": "Chain two commands"
  },
  "error": "The token '&&' is not a valid statement separator",
  "context": {
    "working_dir": "C:\\Users\\jonat\\Projects\\FlowCapture",
    "project": "FlowCapture"
  }
}
```

**Fields:**
| Field | Purpose |
|-------|---------|
| `id` | Unique identifier for deduplication |
| `timestamp` | When error occurred (ISO 8601) |
| `session_id` | Links errors to specific sessions |
| `category` | Error type: action_error, syntax_error, path_error, permission_error |
| `tool` | Which Claude Code tool failed |
| `input` | What Claude tried to do |
| `error` | The actual error message |
| `context` | Where it happened (project, directory) |

---

### 2. Error Logger Hook (error-logger.py)

**Trigger:** `PostToolUseFailure` (after any tool fails)

**Input from Claude Code (stdin):**
```json
{
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": {
    "command": "cmd1 && cmd2",
    "description": "Chain commands"
  },
  "tool_response": "Error: The token '&&' is not valid...",
  "session_id": "abc123",
  "project_dir": "C:\\Users\\jonat\\Projects\\FlowCapture"
}
```

**Behavior:**
- Reads JSON from stdin
- Transforms to error record format
- Appends to `data/errors.jsonl`
- Exits 0 (silent, non-blocking)
- Fails silently if hook itself errors

**Context impact:** Zero tokens (runs outside conversation)

---

### 3. Known Patterns File (known-errors.json)

Curated patterns that the prevention hook checks against:

```json
{
  "version": 1,
  "patterns": [
    {
      "id": "windows_bash_chaining",
      "name": "Bash && chaining on Windows",
      "category": "syntax_error",
      "tool": "Bash",
      "match": {
        "type": "regex",
        "pattern": "&&(?![^\"]*\")"
      },
      "message": "Use ';' or run commands separately on Windows. '&&' is bash syntax.",
      "suggestion": "cmd1; cmd2",
      "added": "2026-01-28",
      "occurrences": 3
    }
  ]
}
```

**Match types:**
- `regex` - Regular expression match
- `contains` - Simple substring match
- `exact` - Exact string match

---

### 4. Command Validator Hook (command-validator.py)

**Trigger:** `PreToolUse` with matcher `Bash`

**Behavior:**
1. Read command from stdin
2. Load `patterns/known-errors.json`
3. Check command against all patterns
4. If match: exit 2 + message to stderr (blocks command)
5. If no match: exit 0 (allow command)

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | Allow - command proceeds |
| 2 | Block - stderr shown to Claude |

**Context impact:** ~30 tokens when blocking (just the message)

---

### 5. Hook Configuration (.claude/settings.json)

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

**Deployment:** Project-level (sandboxed in SUPER_POWERS_PROJECT) until proven, then promote to global `~/.claude/settings.json`.

---

## Token Impact Analysis

**Without prevention (current state):**
```
Claude tries bad command      →  ~30 tokens
Full error output             →  ~100-500 tokens
Claude reasons about error    →  ~50 tokens
Claude retries correctly      →  ~30 tokens
TOTAL                         →  ~210-610 tokens
```

**With prevention hook:**
```
Hook blocks with short message →  ~30 tokens
Claude retries correctly       →  ~30 tokens
TOTAL                          →  ~60 tokens
```

**Net effect:** 70-90% token reduction per prevented error.

---

## Future Phases

### Phase 3: Error Curator Agent

An agent that automates pattern curation:
- Reads `errors.jsonl`
- Clusters similar errors
- Proposes patterns for `known-errors.json`
- User approves/rejects proposals
- Agent writes approved patterns to file

**Trigger:** Manual invocation or `SessionEnd` hook

---

### Phase 4: Outcome-Based Scoring

Track pattern effectiveness:
- Log when prevention fires
- Score +1 if Claude succeeds immediately after
- Score -1 if Claude still struggles
- High-scoring patterns surface first

---

### Phase 5: Context Injection

`SessionStart` hook that:
- Reads top 5 most-triggered patterns
- Injects brief reminders into Claude's context
- Proactive prevention before Claude even tries

---

## Implementation Checklist

- [x] Create `hooks/error-logger.py`
- [x] Create `hooks/command-validator.py`
- [x] Create `patterns/known-errors.json` with initial patterns
- [x] Create `.claude/settings.json` with hook configuration
- [x] Test error logging (trigger a deliberate failure)
- [x] Test prevention (trigger a known-bad pattern)
- [x] Document testing results
- [ ] Promote to global settings when stable

---

## Testing Results (2026-01-28)

### Error Logging Test
- **Method:** Ran nonexistent command `nonexistent-command-xyz-12345`
- **Result:** Error captured in `data/errors.jsonl`
- **Verified fields:** session_id, tool (Bash), command input, category (action_error)
- **Note:** `error` and `working_dir` fields were empty - Claude Code may pass these differently in the hook payload. Core logging works.

### Prevention Test
- **Method:** Attempted `echo test && echo test2`
- **Result:** Command BLOCKED before execution
- **Message shown:** "BLOCKED: Use ';' or run commands separately on Windows. '&&' is bash syntax, not PowerShell."
- **Suggestion shown:** "cmd1; cmd2"
- **Verified:** No error logged for blocked command (correct - it never executed)

### Initial Patterns Deployed
| Pattern ID | Blocks |
|------------|--------|
| windows_bash_chaining | Commands containing `&&` |
| bash_rm_command | Commands starting with `rm ` |
| bash_del_command | Commands starting with `del ` (unquoted) |
| bash_ls_flags | Commands starting with `ls -` |

### Next Steps
1. Use system for several sessions to collect real errors
2. Review `errors.jsonl` for recurring patterns
3. Add valuable patterns to `known-errors.json`
4. When stable, promote hooks to global `~/.claude/settings.json`

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| JSONL over Obsidian | Machine-parseable, no dependencies, can generate Obsidian later if needed |
| Python for hooks | Cross-platform, good JSON handling, already installed |
| Append-only logging | Never lose data, simple to implement |
| Manual curation (Phase 1) | Not every error is a pattern; human judgment needed initially |
| Sandboxed deployment | Test safely before going system-wide |
| Bash-only prevention (initially) | Most common error source; expand later if needed |

---

## Success Criteria

1. **Detection:** Every tool failure is logged to `errors.jsonl`
2. **Logging:** Records contain enough context to identify patterns
3. **Prevention:** Known patterns are blocked before execution
4. **Token savings:** Measurable reduction in wasted iterations
5. **Usability:** System runs silently, doesn't interrupt workflow
