#!/usr/bin/env python3
"""
Error Curator for Claude Code
Pairs errors with their fixes and promotes recurring patterns to learned.json.

Can run as:
  A) SessionEnd hook (automatic) - conservative, only adds patterns seen 2+ times
  B) Manual invocation - interactive, proposes all potential patterns

Usage:
  Automatic (SessionEnd): python error-curator.py --auto
  Manual review:          python error-curator.py --review
  Add all patterns:       python error-curator.py --add-all
  Add specific pattern:   python error-curator.py --add <signature>
  Merge packs:            python error-curator.py --merge

Pack Management (no coding required!):
  List packs:             python error-curator.py --packs
  Enable a pack:          python error-curator.py --enable <pack>
  Disable a pack:         python error-curator.py --disable <pack>
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERRORS_FILE = DATA_DIR / "errors.jsonl"
CURATED_LOG = DATA_DIR / "curated.log"
CONFIG_FILE = BASE_DIR / "config.json"

# Pattern files
PATTERNS_DIR = BASE_DIR / "patterns"
PACKS_DIR = PATTERNS_DIR / "packs"
LEARNED_FILE = PACKS_DIR / "learned.json"
ACTIVE_FILE = PATTERNS_DIR / "active.json"


def load_config():
    """Load plugin configuration."""
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "enabled_packs": ["common", "learned", "custom"],
            "auto_curate": True,
            "curate_threshold": 2,
            "show_confidence": True,
            "track_fixes": True
        }


def save_config(config):
    """Save plugin configuration."""
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_errors():
    """Load all entries from JSONL file."""
    entries = []
    if not ERRORS_FILE.exists():
        return entries

    with ERRORS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def load_pack(pack_name):
    """Load a pattern pack by name."""
    pack_file = PACKS_DIR / f"{pack_name}.json"
    if not pack_file.exists():
        return {"pack": pack_name, "patterns": []}

    try:
        with pack_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"pack": pack_name, "patterns": []}


def save_pack(pack_name, data):
    """Save a pattern pack."""
    pack_file = PACKS_DIR / f"{pack_name}.json"
    with pack_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_existing_pattern_ids(pack_data):
    """Get set of existing pattern IDs from a pack."""
    return {p["id"] for p in pack_data.get("patterns", [])}


def extract_error_signature(entry):
    """
    Extract a signature from an error entry for grouping similar errors.
    """
    if entry.get("type") != "error":
        return None

    tool_input = entry.get("input", {})
    command = tool_input.get("command", "")
    if not command:
        return None

    # Common patterns to normalize
    patterns = [
        (r'.*&&.*', 'bash_and_chaining'),
        (r'^rm\s+', 'bash_rm_command'),
        (r'^del\s+', 'bash_del_command'),
        (r'^ls\s+-', 'bash_ls_flags'),
        (r'^cat\s+', 'bash_cat_command'),
        (r'^grep\s+', 'bash_grep_command'),
        (r'^find\s+', 'bash_find_command'),
        (r'^echo\s+.*>', 'bash_echo_redirect'),
        (r'^touch\s+', 'bash_touch_command'),
        (r'^mkdir\s+(?!-p)', 'bash_mkdir_command'),
        (r'^cp\s+', 'bash_cp_command'),
        (r'^mv\s+', 'bash_mv_command'),
        (r'^sed\s+', 'bash_sed_command'),
    ]

    for pattern, signature in patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return signature

    # Default: use first word as signature
    first_word = command.split()[0] if command.split() else None
    return f"cmd_{first_word}" if first_word else None


def pair_errors_with_fixes(entries):
    """
    Pair errors with their linked fixes.
    Returns dict: {error_id: {"error": entry, "fix": entry or None}}
    """
    paired = {}
    fixes_by_linked = {}

    # First pass: collect all fixes by linked_error
    for entry in entries:
        if entry.get("type") == "fix":
            linked = entry.get("linked_error")
            if linked:
                fixes_by_linked[linked] = entry

    # Second pass: pair errors with fixes
    for entry in entries:
        if entry.get("type") == "error":
            error_id = entry.get("id")
            paired[error_id] = {
                "error": entry,
                "fix": fixes_by_linked.get(error_id)
            }

    return paired


def analyze_error_patterns(entries):
    """
    Analyze errors and group by signature, including associated fixes.
    Returns dict: {signature: {"errors": [...], "fixes": [...], "commands": [...], "fix_commands": [...]}}
    """
    grouped = defaultdict(lambda: {
        "errors": [],
        "fixes": [],
        "commands": [],
        "fix_commands": []
    })

    paired = pair_errors_with_fixes(entries)

    for error_id, pair in paired.items():
        error = pair["error"]
        fix = pair["fix"]

        signature = extract_error_signature(error)
        if not signature:
            continue

        tool_input = error.get("input", {})
        command = tool_input.get("command", "")

        grouped[signature]["errors"].append(error)
        grouped[signature]["commands"].append(command)

        if fix:
            grouped[signature]["fixes"].append(fix)
            grouped[signature]["fix_commands"].append(fix.get("command", ""))

    return grouped


def generate_learned_pattern(signature, data):
    """Generate a learned pattern entry with fix information."""
    sample_command = data["commands"][0] if data["commands"] else ""
    sample_fix = data["fix_commands"][0] if data["fix_commands"] else ""
    error_count = len(data["errors"])
    fix_count = len(data["fixes"])

    # Calculate confidence based on how often fixes worked
    confidence = int((fix_count / error_count) * 100) if error_count > 0 else 0

    # Pattern templates based on signature
    templates = {
        'bash_and_chaining': {
            "match": {"type": "contains", "pattern": "&&"},
            "message": "BLOCKED: '&&' doesn't work here."
        },
        'bash_rm_command': {
            "match": {"type": "regex", "pattern": "^rm\\s+"},
            "message": "BLOCKED: 'rm' is bash syntax."
        },
        'bash_del_command': {
            "match": {"type": "regex", "pattern": "^del\\s+"},
            "message": "BLOCKED: Use quoted paths with Remove-Item."
        },
        'bash_ls_flags': {
            "match": {"type": "regex", "pattern": "^ls\\s+-[a-zA-Z]"},
            "message": "BLOCKED: 'ls -flags' is bash syntax."
        },
        'bash_cat_command': {
            "match": {"type": "regex", "pattern": "^cat\\s+"},
            "message": "BLOCKED: Use the Read tool instead."
        },
        'bash_grep_command': {
            "match": {"type": "regex", "pattern": "^grep\\s+"},
            "message": "BLOCKED: Use the Grep tool instead."
        },
        'bash_find_command': {
            "match": {"type": "regex", "pattern": "^find\\s+"},
            "message": "BLOCKED: Use the Glob tool instead."
        },
        'bash_echo_redirect': {
            "match": {"type": "regex", "pattern": "^echo\\s+.*>"},
            "message": "BLOCKED: Use the Write tool instead."
        },
        'bash_touch_command': {
            "match": {"type": "regex", "pattern": "^touch\\s+"},
            "message": "BLOCKED: 'touch' is bash syntax."
        },
        'bash_mkdir_command': {
            "match": {"type": "regex", "pattern": "^mkdir\\s+(?!-p)"},
            "message": "BLOCKED: Use New-Item or mkdir -p equivalent."
        },
        'bash_cp_command': {
            "match": {"type": "regex", "pattern": "^cp\\s+"},
            "message": "BLOCKED: 'cp' is bash syntax."
        },
        'bash_mv_command': {
            "match": {"type": "regex", "pattern": "^mv\\s+"},
            "message": "BLOCKED: 'mv' is bash syntax."
        },
        'bash_sed_command': {
            "match": {"type": "regex", "pattern": "^sed\\s+"},
            "message": "BLOCKED: Use the Edit tool instead."
        },
    }

    template = templates.get(signature, {
        "match": {"type": "contains", "pattern": sample_command.split()[0] if sample_command else ""},
        "message": f"BLOCKED: This command pattern has failed {error_count} times."
    })

    # Determine learned fix
    learned_fix = sample_fix if sample_fix else "Check error log for alternatives"

    return {
        "id": signature,
        "name": signature.replace("_", " ").title(),
        "category": "learned",
        "tool": "Bash",
        "match": template["match"],
        "message": template["message"],
        "learned_fix": learned_fix,
        "confidence": confidence,
        "error_count": error_count,
        "fix_count": fix_count,
        "first_seen": data["errors"][0].get("timestamp", "")[:10] if data["errors"] else "",
        "last_seen": data["errors"][-1].get("timestamp", "")[:10] if data["errors"] else "",
        "source": "auto_learned"
    }


def merge_packs():
    """Merge all enabled packs into active.json."""
    config = load_config()
    enabled = config.get("enabled_packs", ["common", "learned", "custom"])

    merged_patterns = []
    seen_ids = set()

    for pack_name in enabled:
        pack = load_pack(pack_name)
        for pattern in pack.get("patterns", []):
            pattern_id = pattern.get("id")
            if pattern_id and pattern_id not in seen_ids:
                merged_patterns.append(pattern)
                seen_ids.add(pattern_id)

    active_data = {
        "description": "Merged active patterns from enabled packs. Auto-generated - do not edit directly.",
        "generated_at": datetime.now().isoformat(),
        "enabled_packs": enabled,
        "patterns": merged_patterns
    }

    with ACTIVE_FILE.open("w", encoding="utf-8") as f:
        json.dump(active_data, f, indent=2)

    return len(merged_patterns)


def auto_curate():
    """
    Automatic curation (SessionEnd hook).
    Only adds patterns that have occurred 2+ times and have fixes.
    """
    config = load_config()
    if not config.get("auto_curate", True):
        sys.exit(0)

    threshold = config.get("curate_threshold", 2)
    entries = load_errors()
    if not entries:
        sys.exit(0)

    learned = load_pack("learned")
    existing_ids = get_existing_pattern_ids(learned)
    grouped = analyze_error_patterns(entries)

    added = []
    for signature, data in grouped.items():
        # Skip if already exists
        if signature in existing_ids:
            continue

        # Only auto-add if threshold met
        if len(data["errors"]) >= threshold:
            pattern = generate_learned_pattern(signature, data)
            learned["patterns"].append(pattern)
            added.append(signature)

    if added:
        save_pack("learned", learned)

        # Also merge packs to update active.json
        merge_packs()

        # Log what was added
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with CURATED_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat()}] Auto-curated {len(added)} patterns: {', '.join(added)}\n")

    # Exit silently (non-blocking for SessionEnd)
    sys.exit(0)


def manual_review():
    """
    Manual review mode.
    Outputs proposed patterns for user review.
    """
    entries = load_errors()
    if not entries:
        print("No entries found in errors.jsonl")
        return

    # Count errors and fixes
    errors = [e for e in entries if e.get("type") == "error"]
    fixes = [e for e in entries if e.get("type") == "fix"]

    learned = load_pack("learned")
    existing_ids = get_existing_pattern_ids(learned)
    grouped = analyze_error_patterns(entries)

    print(f"\n=== Error Curator Review ===")
    print(f"Total errors: {len(errors)}")
    print(f"Total fixes: {len(fixes)}")
    print(f"Existing learned patterns: {len(existing_ids)}")
    print(f"Error signatures found: {len(grouped)}\n")

    new_patterns = []
    for signature, data in sorted(grouped.items(), key=lambda x: -len(x[1]["errors"])):
        error_count = len(data["errors"])
        fix_count = len(data["fixes"])
        status = "EXISTS" if signature in existing_ids else "NEW"

        fix_info = f" ({fix_count} fixes)" if fix_count > 0 else " (no fixes)"
        print(f"[{status}] {signature}: {error_count} error(s){fix_info}")

        if status == "NEW":
            if data["commands"]:
                print(f"    Error cmd: {data['commands'][0][:60]}...")
            if data["fix_commands"]:
                print(f"    Fix cmd:   {data['fix_commands'][0][:60]}...")
            new_patterns.append((signature, data))

    if new_patterns:
        print(f"\n--- {len(new_patterns)} new patterns can be added ---")
        print("\nTo add all new patterns, run:")
        print("  python error-curator.py --add-all")
        print("\nOr add specific pattern:")
        print("  python error-curator.py --add <signature>")
    else:
        print("\nNo new patterns to add.")


def add_all_patterns():
    """Add all new patterns to learned.json."""
    entries = load_errors()
    learned = load_pack("learned")
    existing_ids = get_existing_pattern_ids(learned)
    grouped = analyze_error_patterns(entries)

    added = []
    for signature, data in grouped.items():
        if signature not in existing_ids:
            pattern = generate_learned_pattern(signature, data)
            learned["patterns"].append(pattern)
            added.append(signature)

    if added:
        save_pack("learned", learned)
        merge_packs()
        print(f"Added {len(added)} patterns: {', '.join(added)}")
    else:
        print("No new patterns to add.")


def add_pattern(signature):
    """Add a specific pattern by signature."""
    entries = load_errors()
    learned = load_pack("learned")
    existing_ids = get_existing_pattern_ids(learned)
    grouped = analyze_error_patterns(entries)

    if signature in existing_ids:
        print(f"Pattern '{signature}' already exists.")
        return

    if signature not in grouped:
        print(f"Pattern '{signature}' not found in errors.")
        return

    data = grouped[signature]
    pattern = generate_learned_pattern(signature, data)
    learned["patterns"].append(pattern)
    save_pack("learned", learned)
    merge_packs()
    print(f"Added pattern: {signature}")


def get_available_packs():
    """Get list of all available pack names."""
    packs = []
    if PACKS_DIR.exists():
        for pack_file in PACKS_DIR.glob("*.json"):
            packs.append(pack_file.stem)
    return sorted(packs)


def list_packs():
    """List all available packs with their status."""
    config = load_config()
    enabled = config.get("enabled_packs", [])
    available = get_available_packs()

    print("\n" + "=" * 50)
    print("  ERROR LEARNING - PATTERN PACKS")
    print("=" * 50 + "\n")

    for pack_name in available:
        pack_data = load_pack(pack_name)
        pattern_count = len(pack_data.get("patterns", []))
        description = pack_data.get("description", "No description")
        status = "ENABLED" if pack_name in enabled else "disabled"
        marker = "[*]" if pack_name in enabled else "[ ]"

        print(f"  {marker} {pack_name}")
        print(f"      {pattern_count} patterns - {description[:50]}...")
        print()

    print("-" * 50)
    print("  Commands:")
    print("    --enable <pack>   Enable a pack")
    print("    --disable <pack>  Disable a pack")
    print("-" * 50 + "\n")


def enable_pack(pack_name):
    """Enable a pattern pack."""
    available = get_available_packs()

    if pack_name not in available:
        print(f"\nError: Pack '{pack_name}' not found.")
        print(f"Available packs: {', '.join(available)}")
        return False

    config = load_config()
    enabled = config.get("enabled_packs", [])

    if pack_name in enabled:
        print(f"\nPack '{pack_name}' is already enabled.")
        return True

    enabled.append(pack_name)
    config["enabled_packs"] = enabled
    save_config(config)

    # Re-merge patterns
    count = merge_packs()

    print(f"\n[OK] Enabled pack: {pack_name}")
    print(f"     Active patterns: {count}")
    return True


def disable_pack(pack_name):
    """Disable a pattern pack."""
    config = load_config()
    enabled = config.get("enabled_packs", [])

    if pack_name not in enabled:
        print(f"\nPack '{pack_name}' is not currently enabled.")
        print(f"Enabled packs: {', '.join(enabled)}")
        return False

    enabled.remove(pack_name)
    config["enabled_packs"] = enabled
    save_config(config)

    # Re-merge patterns
    count = merge_packs()

    print(f"\n[OK] Disabled pack: {pack_name}")
    print(f"     Active patterns: {count}")
    return True


def main():
    if len(sys.argv) < 2:
        print("\nError Learning Plugin - Pattern Curator")
        print("=" * 40)
        print("\nPack Management (no coding!):")
        print("  --packs              List all packs and their status")
        print("  --enable <pack>      Enable a pattern pack")
        print("  --disable <pack>     Disable a pattern pack")
        print("\nPattern Curation:")
        print("  --review             Review pending patterns")
        print("  --add-all            Add all new patterns")
        print("  --add <signature>    Add specific pattern")
        print("\nSystem:")
        print("  --merge              Rebuild active.json from enabled packs")
        print("  --auto               SessionEnd hook (internal)")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "--auto":
        auto_curate()
    elif mode == "--review":
        manual_review()
    elif mode == "--add-all":
        add_all_patterns()
    elif mode == "--add" and len(sys.argv) > 2:
        add_pattern(sys.argv[2])
    elif mode == "--merge":
        count = merge_packs()
        print(f"Merged {count} patterns to active.json")
    elif mode == "--packs":
        list_packs()
    elif mode == "--enable" and len(sys.argv) > 2:
        enable_pack(sys.argv[2])
    elif mode == "--disable" and len(sys.argv) > 2:
        disable_pack(sys.argv[2])
    elif mode in ("--enable", "--disable"):
        print(f"Error: {mode} requires a pack name")
        print("Use --packs to see available packs")
        sys.exit(1)
    else:
        print(f"Unknown command: {mode}")
        print("Run without arguments to see usage")
        sys.exit(1)


if __name__ == "__main__":
    main()
