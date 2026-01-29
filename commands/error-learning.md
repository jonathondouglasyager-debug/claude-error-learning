---
name: error-learning
description: Manage error learning patterns - view stats, review pending patterns, manage packs
arguments:
  - name: action
    description: "Action: status, review, packs, add"
    required: false
    type: string
  - name: arg
    description: "Argument for the action (pack name or pattern)"
    required: false
    type: string
---

# Error Learning Management

You are helping manage the error learning system. Based on the action requested, perform the appropriate task.

## Available Actions

### /error-learning (or /error-learning status)
Show current status and statistics:
1. Read `config.json` to show enabled packs
2. Read `patterns/active.json` to count active patterns
3. Read `data/errors.jsonl` to count errors and fixes
4. Display summary with:
   - Number of active patterns
   - Number of errors logged
   - Number of fixes captured
   - Enabled pattern packs

### /error-learning review
Review pending patterns for approval:
1. Run: `python hooks/error-curator.py --review`
2. Show the output which lists:
   - All error signatures found
   - Which are NEW vs EXISTS
   - Sample error and fix commands
   - Instructions for adding patterns

### /error-learning packs
List available pattern packs and their status:
1. Read `config.json` to get enabled_packs
2. List all .json files in `patterns/packs/`
3. For each pack, show:
   - Pack name
   - Enabled/disabled status
   - Number of patterns
   - Description

### /error-learning packs enable <pack>
Enable a pattern pack:
1. Read `config.json`
2. Add pack name to `enabled_packs` if not present
3. Write updated `config.json`
4. Run: `python hooks/error-curator.py --merge`
5. Confirm the change

### /error-learning packs disable <pack>
Disable a pattern pack:
1. Read `config.json`
2. Remove pack name from `enabled_packs`
3. Write updated `config.json`
4. Run: `python hooks/error-curator.py --merge`
5. Confirm the change

### /error-learning add "<pattern>"
Manually add a pattern:
1. Parse the pattern description
2. Read `patterns/packs/custom.json`
3. Create a new pattern entry with:
   - Unique ID based on description
   - Match type (contains, regex, or exact)
   - Block message
   - Learned fix (if provided)
4. Append to custom.json patterns array
5. Run: `python hooks/error-curator.py --merge`
6. Confirm the addition

## Example Outputs

### Status Output
```
Error Learning Status
=====================
Active Patterns: 12
  - common: 5 patterns
  - windows: 4 patterns
  - learned: 3 patterns

Error Log: 47 errors, 23 fixes (49% fix rate)

Enabled Packs: common, learned, custom
```

### Packs Output
```
Available Pattern Packs
=======================
[ENABLED]  common   - 5 patterns - Universal tool preferences
[ENABLED]  learned  - 3 patterns - Auto-learned from errors
[ENABLED]  custom   - 0 patterns - User-defined patterns
[DISABLED] windows  - 7 patterns - Windows/PowerShell patterns
[DISABLED] linux    - 1 patterns - Linux/bash patterns
```

## Important Notes

- The plugin root is: `${CLAUDE_PLUGIN_ROOT}`
- Patterns are stored in `patterns/packs/*.json`
- Active merged patterns are in `patterns/active.json`
- Error log is at `data/errors.jsonl`
- Config is at `config.json`

When making changes:
1. Always read before writing
2. Run --merge after pack changes
3. Confirm changes to the user
