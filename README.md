# Claude Error Learning Plugin

Automated error detection, fix tracking, and prevention for Claude Code. Learns from mistakes and teaches future sessions the fixes.

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
     │                              │                               │
     ▼                              ▼                               ▼
errors.jsonl                 errors.jsonl                   learned.json
{cmd, error}                {fix, linked_to}               {block, learned_fix}
```

**Result:** Claude makes mistake once → learns the fix → never makes that mistake again.

## Installation

### As a Claude Code Plugin

```bash
# Install from GitHub
claude plugins install github:jonathondouglasyager-debug/claude-error-learning
```

### Manual Installation

1. Clone this repo to your preferred location
2. Add the plugin to your `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "error-learning": "path/to/error-learning"
  }
}
```

## Quick Start

After installation, the plugin works automatically:

1. **Errors are captured** when any tool fails
2. **Fixes are tracked** when a successful command follows a failed one
3. **Patterns are learned** at session end (if seen 2+ times)
4. **Commands are blocked** in future sessions with the learned fix shown

Use the slash command to manage:

```
/error-learning          # Show status and stats
/error-learning review   # Review pending patterns
/error-learning packs    # List available pattern packs
```

## Pattern Packs

Patterns are organized into packs that can be enabled/disabled:

| Pack | Description | Default |
|------|-------------|---------|
| `common` | Universal patterns (use Read not cat, etc.) | Enabled |
| `windows` | Windows/PowerShell patterns | Disabled |
| `linux` | Linux/bash patterns | Disabled |
| `learned` | Auto-learned from your errors | Enabled |
| `custom` | Your manual additions | Enabled |

### Managing Packs

**Interactive (no coding):**
- Double-click `manage-packs.py` or use Desktop shortcut
- Type a number to toggle packs on/off

**CLI:**
```bash
python hooks/error-curator.py --packs           # List all packs
python hooks/error-curator.py --enable windows  # Enable a pack
python hooks/error-curator.py --disable linux   # Disable a pack
```

**Slash command:**
```
/error-learning packs                    # List all packs
/error-learning packs enable windows     # Enable Windows patterns
/error-learning packs disable linux      # Disable Linux patterns
```

**Or edit `config.json` directly:**

```json
{
  "enabled_packs": ["common", "windows", "learned", "custom"],
  "auto_curate": true,
  "curate_threshold": 2,
  "show_confidence": true
}
```

## How It Works

### Hooks

| Hook | File | Purpose |
|------|------|---------|
| PostToolUseFailure | `error-logger.py` | Captures errors with `awaiting_fix` flag |
| PostToolUse (Bash) | `fix-tracker.py` | Links successful commands to prior errors |
| PreToolUse (Bash) | `command-validator.py` | Blocks known-bad commands, shows fix |
| SessionEnd | `error-curator.py` | Pairs errors with fixes, updates patterns |

### Error → Fix Pairing

When an error occurs:
1. `error-logger.py` logs it with `awaiting_fix: true`
2. When a successful command follows (same session, same tool)
3. `fix-tracker.py` logs it as a fix linked to the error
4. At session end, `error-curator.py` pairs them and extracts patterns

### Blocking with Learned Fix

When a blocked command is detected:

```
BLOCKED: '&&' doesn't work here.
LEARNED FIX (87% confidence): Use "cmd1; cmd2" instead
```

The confidence score is based on how often the fix worked.

## Plugin Structure

```
error-learning/
├── plugin.json                    # Plugin manifest
├── config.json                    # User settings
├── manage-packs.py                # Interactive pack manager (double-click!)
├── hooks/
│   ├── error-logger.py            # PostToolUseFailure
│   ├── fix-tracker.py             # PostToolUse (Bash)
│   ├── command-validator.py       # PreToolUse (Bash)
│   └── error-curator.py           # SessionEnd + CLI commands
├── patterns/
│   ├── active.json                # Merged patterns (auto-generated)
│   └── packs/
│       ├── common.json            # Universal patterns
│       ├── windows.json           # Windows/PowerShell
│       ├── linux.json             # Linux/bash
│       ├── learned.json           # Auto-learned
│       └── custom.json            # User additions
├── commands/
│   └── error-learning.md          # Slash command
└── data/                          # gitignored
    ├── errors.jsonl               # Error + fix log
    └── curator.log                # Curation activity
```

## Manual Pattern Management

### Review Pending Patterns

```bash
python hooks/error-curator.py --review
```

Shows all error signatures, their occurrence count, and sample commands.

### Add All Patterns

```bash
python hooks/error-curator.py --add-all
```

Adds all detected patterns to `learned.json`.

### Add Specific Pattern

```bash
python hooks/error-curator.py --add bash_and_chaining
```

### Merge Packs

```bash
python hooks/error-curator.py --merge
```

Regenerates `active.json` from enabled packs.

## Adding Custom Patterns

Use the slash command:

```
/error-learning add "rm command should use Remove-Item"
```

Or edit `patterns/packs/custom.json`:

```json
{
  "id": "my_custom_pattern",
  "name": "My Custom Pattern",
  "category": "custom",
  "tool": "Bash",
  "match": {
    "type": "contains",
    "pattern": "bad command"
  },
  "message": "BLOCKED: Explanation",
  "learned_fix": "Use this instead",
  "confidence": 100,
  "source": "manual"
}
```

Match types: `contains`, `regex`, `exact`

## Token Savings

| Scenario | Tokens |
|----------|--------|
| Without prevention | ~210-610 per error |
| With prevention | ~60 per error |
| **Savings** | **70-90%** |

## Contributing

1. Fork this repo
2. Add patterns to the appropriate pack
3. Submit a PR

Pattern contributions welcome for:
- Platform-specific gotchas
- Common tool misuse patterns
- Language-specific errors

## License

MIT
