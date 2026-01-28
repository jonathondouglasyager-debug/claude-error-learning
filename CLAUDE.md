# Claude Error Learning System

Automated error detection, logging, curation, and prevention for Claude Code via hooks.

**Repo:** https://github.com/jonathondouglasyager-debug/claude-error-learning
**Location:** `C:\Users\jonat\Desktop\SUPER_POWERS_PROJECT`

---

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
[SessionEnd] error-curator.py --auto → patterns/known-errors.json
        ↓
Next session, Claude tries same mistake
        ↓
[PreToolUse] command-validator.py → BLOCKED with helpful message
        ↓
Claude uses correct syntax immediately
```

**Result:** Errors are caught once, learned automatically, prevented forever. 70-90% token reduction per prevented error.

---

## Architecture

| Component | File | Hook | Purpose |
|-----------|------|------|---------|
| Error Logger | `hooks/error-logger.py` | PostToolUseFailure | Captures all tool failures |
| Error Curator | `hooks/error-curator.py` | SessionEnd (auto) | Promotes recurring errors to patterns |
| Command Validator | `hooks/command-validator.py` | PreToolUse (Bash) | Blocks known-bad commands |
| Error Log | `data/errors.jsonl` | - | Raw error records (local) |
| Patterns | `patterns/known-errors.json` | - | Curated patterns for prevention |
| Config | `.claude/settings.json` | - | Hook configuration |

---

## Automatic vs Manual Curation

### Option A: Automatic (SessionEnd Hook)

Runs every time a session ends. Conservative - only adds patterns seen 2+ times.

```
Session ends → error-curator.py --auto runs → patterns with 2+ occurrences added
```

**No action needed.** Patterns accumulate automatically.

### Option B: Manual Review

Review all potential patterns, including one-offs:

```bash
python hooks/error-curator.py --review    # See all potential patterns
python hooks/error-curator.py --add-all   # Add all new patterns
python hooks/error-curator.py --add <id>  # Add specific pattern
```

Use this when you want to manually curate or review what's been logged.

---

## Current Patterns

Located in `patterns/known-errors.json`:

| ID | What it blocks | Suggestion |
|----|----------------|------------|
| `windows_bash_chaining` | `&&` in commands | Use `;` or run separately |
| `bash_rm_command` | `rm` command | Use `Remove-Item` |
| `bash_del_command` | `del` without quotes | Use `Remove-Item "path"` |
| `bash_ls_flags` | `ls -flags` | Use `Get-ChildItem` or `dir` |

New patterns added automatically when they occur 2+ times.

---

## Pattern Template

For manual additions to `patterns/known-errors.json`:

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
| This project folder | Active (full loop working) |
| Global (all projects) | Not yet - promote to `~/.claude/settings.json` when stable |

**To promote to global:**
1. Merge hooks config into `C:\Users\jonat\.claude\settings.json`
2. Keep hook scripts in this project folder (paths are absolute)
3. All projects will benefit from accumulated patterns

---

## Commands Reference

| Action | Command |
|--------|---------|
| Review error log | `Read data/errors.jsonl` |
| Review potential patterns | `python hooks/error-curator.py --review` |
| Add all new patterns | `python hooks/error-curator.py --add-all` |
| Add specific pattern | `python hooks/error-curator.py --add <signature>` |
| Check curation log | `Read data/curated.log` |
| Test prevention | Try a blocked command like `echo test && echo test2` |

---

## Future Phases

### Phase 3: Error Curator Agent ✅ COMPLETE

- `error-curator.py` with --auto and --review modes
- SessionEnd hook for automatic curation
- Threshold-based pattern promotion (2+ occurrences)

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
| `data/curated.log` | Log of auto-curated patterns |

---

## Known Limitations

- `error` and `working_dir` fields sometimes empty in logged records (Claude Code payload structure differs from docs)
- Only Bash commands validated currently (can expand to Edit, Write later)
- Auto-curation requires 2+ occurrences (one-offs need manual review)

---

*Created: 2026-01-28*
*Updated: 2026-01-28 - Added complete feedback loop with error-curator.py*
