# Claude Error Learning System

Automated error detection and prevention for Claude Code via hooks.

**Repo:** https://github.com/jonathondouglasyager-debug/claude-error-learning
**Location:** `C:\Users\jonat\Desktop\SUPER_POWERS_PROJECT`

---

## What This Project Does

1. **Detects** - Automatically captures every tool failure to `data/errors.jsonl`
2. **Logs** - Stores error context (tool, command, error message, session ID)
3. **Prevents** - Blocks known-bad patterns BEFORE execution with helpful messages

**Result:** 70-90% token reduction per prevented error. No more wasted iterations.

---

## Architecture

```
PostToolUseFailure hook → error-logger.py → data/errors.jsonl
PreToolUse hook (Bash)  → command-validator.py → patterns/known-errors.json
```

| Component | File | Purpose |
|-----------|------|---------|
| Error Logger | `hooks/error-logger.py` | Captures all tool failures |
| Command Validator | `hooks/command-validator.py` | Blocks known-bad commands |
| Error Log | `data/errors.jsonl` | Raw error records (local, not tracked in git) |
| Patterns | `patterns/known-errors.json` | Curated patterns for prevention |
| Config | `.claude/settings.json` | Hook configuration |

---

## Current Patterns

Located in `patterns/known-errors.json`:

| ID | What it blocks | Suggestion |
|----|----------------|------------|
| `windows_bash_chaining` | `&&` in commands | Use `;` or run separately |
| `bash_rm_command` | `rm` command | Use `Remove-Item` |
| `bash_del_command` | `del` without quotes | Use `Remove-Item "path"` |
| `bash_ls_flags` | `ls -flags` | Use `Get-ChildItem` or `dir` |

---

## How to Add New Patterns

1. Review `data/errors.jsonl` for recurring errors
2. Identify the pattern (what command keeps failing?)
3. Add to `patterns/known-errors.json`:

```json
{
  "id": "unique_id",
  "name": "Human readable name",
  "category": "syntax_error",
  "tool": "Bash",
  "match": {
    "type": "contains",
    "pattern": "the bad pattern"
  },
  "message": "BLOCKED: Explanation of why and what to do instead.",
  "suggestion": "correct command",
  "added": "YYYY-MM-DD",
  "occurrences": 0
}
```

**Match types:**
- `contains` - Simple substring match
- `regex` - Regular expression
- `exact` - Exact string match

---

## Deployment Status

| Scope | Status |
|-------|--------|
| This project folder | Active (`.claude/settings.json`) |
| Global (all projects) | Not yet - promote to `~/.claude/settings.json` when stable |

**To promote to global:**
1. Merge hooks config into `C:\Users\jonat\.claude\settings.json`
2. Update paths in hook commands if needed

---

## Future Phases

### Phase 3: Error Curator Agent
Agent that reads `errors.jsonl`, clusters similar errors, and proposes patterns for approval.

### Phase 4: Outcome-Based Scoring
Track which patterns actually help. High-scoring patterns surface first.

### Phase 5: Context Injection
`SessionStart` hook injects top patterns into Claude's context proactively.

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/plans/2026-01-28-error-learning-system-design.md` | Full design document |
| `docs/plans/2026-01-28-error-learning-implementation.md` | Implementation plan |
| `README.md` | Public documentation |

---

## Working With This Project

**To review errors:**
```
Read data/errors.jsonl
```

**To add a pattern:**
Edit `patterns/known-errors.json` and add new pattern object.

**To test prevention:**
Try running a command that matches a pattern - it should be blocked with a message.

**To check hook status:**
Review `.claude/settings.json` - hooks should be configured under `PostToolUseFailure` and `PreToolUse`.

---

## Known Limitations

- `error` and `working_dir` fields sometimes empty in logged records (Claude Code payload structure differs from docs)
- Only Bash commands validated currently (can expand to Edit, Write later)
- Manual pattern curation until Phase 3 agent is built

---

*Created: 2026-01-28*
