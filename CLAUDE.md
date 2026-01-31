# Claude Error Learning Plugin

Automated error detection, fix tracking, and prevention for Claude Code via hooks.

**Repo:** https://github.com/jonathondouglasyager-debug/claude-error-learning
**Location:** `C:\Users\jonat\Desktop\SUPER_POWERS_PROJECT`

---

## The Complete Loop

```
ERROR OCCURS                    FIX APPLIED                    FUTURE SESSIONS
     │                              │                               │
     ▼                              ▼                               ▼
┌──────────┐                  ┌──────────┐                    ┌──────────┐
│ Capture  │                  │ Capture  │                    │ Prevent  │
│  Error   │────────────────▶│   Fix    │─────────────────▶  │ + Teach  │
│          │  same session    │          │   curator pairs    │          │
└──────────┘  same tool type  └──────────┘   error → fix      └──────────┘
```

**Result:** Claude makes mistake once → learns the fix → never makes that mistake again. 70-90% token reduction per prevented error.

---

## Smart Detection (v2)

The curator analyzes **error messages** to create precise blocking rules:

| Error Type | Signature | Blocked | Example |
|------------|-----------|---------|---------|
| Bad flag | `bad_flag_ls_--xyz` | Only that flag | `ls --xyz` blocked, `ls -la` works |
| Command not found | `cmd_not_found_choco` | Only that command | `choco` blocked |
| Path not found | `path_not_found_*` | **SKIPPED** | Won't learn (environmental) |
| Permission denied | `permission_*` | **SKIPPED** | Won't learn (environmental) |

This prevents false positives like blocking all `ls` commands when only one bad flag failed.

---

## Plugin Architecture

| Component | File | Hook | Purpose |
|-----------|------|------|---------|
| Error Logger | `hooks/error-logger.py` | PostToolUseFailure | Captures errors with `awaiting_fix` flag |
| Fix Tracker | `hooks/fix-tracker.py` | PostToolUse (Bash) | Links fixes to prior errors |
| Command Validator | `hooks/command-validator.py` | PreToolUse (Bash) | Blocks + shows learned fix |
| Error Curator | `hooks/error-curator.py` | SessionEnd | Pairs errors with fixes |
| Slash Command | `commands/error-learning.md` | - | Management interface |

---

## Pattern Packs

Patterns are organized into packs in `patterns/packs/`:

| Pack | File | Description | Default |
|------|------|-------------|---------|
| common | `common.json` | Universal (use Read not cat, etc.) | Enabled |
| windows | `windows.json` | Windows/PowerShell patterns | Disabled |
| linux | `linux.json` | Linux/bash patterns | Disabled |
| learned | `learned.json` | Auto-learned from errors | Enabled |
| custom | `custom.json` | User additions | Enabled |

**Merged output:** `patterns/active.json` (auto-generated, do not edit)

### Enable/Disable Packs

Edit `config.json`:

```json
{
  "enabled_packs": ["common", "windows", "learned", "custom"],
  "auto_curate": true,
  "curate_threshold": 2,
  "show_confidence": true
}
```

Or use: `/error-learning packs enable windows`

---

## Slash Command

```
/error-learning              # Show status + stats
/error-learning review       # Show pending patterns
/error-learning packs        # List available packs
/error-learning packs enable <pack>   # Enable a pack
/error-learning packs disable <pack>  # Disable a pack
/error-learning add "<pattern>"       # Add manual pattern
```

---

## Pack Management (No Coding!)

**Desktop Shortcut:** Double-click "Error Learning Packs" on Desktop for interactive menu.

**CLI Commands:**
```
python hooks/error-curator.py --packs           # List all packs
python hooks/error-curator.py --enable windows  # Enable a pack
python hooks/error-curator.py --disable linux   # Disable a pack
```

---

## CLI Commands

| Action | Command |
|--------|---------|
| **List packs** | `python hooks/error-curator.py --packs` |
| **Enable pack** | `python hooks/error-curator.py --enable <pack>` |
| **Disable pack** | `python hooks/error-curator.py --disable <pack>` |
| Review pending patterns | `python hooks/error-curator.py --review` |
| Add all patterns | `python hooks/error-curator.py --add-all` |
| Add specific pattern | `python hooks/error-curator.py --add <sig>` |
| Merge enabled packs | `python hooks/error-curator.py --merge` |
| View error log | `Read data/errors.jsonl` |
| View curation log | `Read data/curated.log` |

### Allowlist Commands

| Action | Command |
|--------|---------|
| **List allowlist** | `python hooks/error-curator.py --allowlist` |
| **Allow prefix** | `python hooks/error-curator.py --allow "ls "` |
| **Allow exact** | `python hooks/error-curator.py --allow-exact "git status"` |
| **Allow regex** | `python hooks/error-curator.py --allow-regex "^npm (run|test)"` |
| **Remove** | `python hooks/error-curator.py --unallow "ls "` |

---

## Key Files

| File | Purpose |
|------|---------|
| `plugin.json` | Plugin manifest |
| `config.json` | User settings |
| `patterns/active.json` | Merged active patterns |
| `patterns/allowlist.json` | Commands that bypass blocking |
| `patterns/packs/*.json` | Individual pattern packs |
| `data/errors.jsonl` | Error + fix log |
| `data/curated.log` | Curation activity |

---

## Error Record Format

```json
{
  "id": "err_20260129_143022",
  "type": "error",
  "timestamp": "2026-01-29T14:30:22Z",
  "session_id": "abc123",
  "tool": "Bash",
  "input": {"command": "echo test && echo test2"},
  "error": "'&&' not recognized",
  "awaiting_fix": true
}
```

## Fix Record Format

```json
{
  "id": "fix_20260129_143025",
  "type": "fix",
  "linked_error": "err_20260129_143022",
  "timestamp": "2026-01-29T14:30:25Z",
  "session_id": "abc123",
  "tool": "Bash",
  "command": "echo test; echo test2"
}
```

## Learned Pattern Format

```json
{
  "id": "bad_flag_ls_--invalid-flag",
  "name": "Bad flag: ls --invalid-flag",
  "category": "learned",
  "tool": "Bash",
  "match": {"type": "regex", "pattern": "^ls\\s+.*\\-\\-invalid\\-flag"},
  "message": "BLOCKED: '--invalid-flag' is not a valid option for ls.",
  "learned_fix": "Remove or replace '--invalid-flag'",
  "confidence": 0,
  "error_count": 2,
  "fix_count": 0,
  "source": "auto_learned"
}
```

## Allowlist Pattern Format

```json
{
  "description": "Commands that bypass blocking",
  "version": 1,
  "patterns": [
    {"type": "prefix", "pattern": "ls "},
    {"type": "exact", "pattern": "git status"},
    {"type": "regex", "pattern": "^npm (run|test|install)"}
  ]
}
```

Match types: `prefix`, `exact`, `contains`, `regex`

---

## Deployment Status

| Scope | Status |
|-------|--------|
| This project | Active (plugin format) |
| Global | Promote by adding to `~/.claude/settings.json` |
| Registry | Not yet published |

---

## Future Phases

### Phase 4: Outcome-Based Scoring
Track which patterns actually prevent errors. High-scoring patterns surface first.

### Phase 5: Context Injection
`SessionStart` hook injects top patterns into Claude's context proactively.

### Phase 6: Plugin Registry
Publish to Claude Code plugin registry for easy installation.

---

*Created: 2026-01-28*
*Updated: 2026-01-29 - Converted to plugin format with fix tracking and pattern packs*
*Updated: 2026-01-31 - Smart error-message detection, allowlist override, environmental error skipping*
