#!/usr/bin/env python3
"""
Interactive Pattern Pack Manager
Double-click to run - no coding required!
"""

import json
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
PACKS_DIR = BASE_DIR / "patterns" / "packs"
ACTIVE_FILE = BASE_DIR / "patterns" / "active.json"


def load_config():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"enabled_packs": ["common", "learned", "custom"]}


def save_config(config):
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_pack(name):
    try:
        with (PACKS_DIR / f"{name}.json").open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"patterns": []}


def get_packs():
    return sorted([f.stem for f in PACKS_DIR.glob("*.json")])


def merge_packs(enabled):
    patterns = []
    seen = set()
    for name in enabled:
        pack = load_pack(name)
        for p in pack.get("patterns", []):
            if p.get("id") not in seen:
                patterns.append(p)
                seen.add(p.get("id"))

    from datetime import datetime
    data = {
        "description": "Merged active patterns",
        "generated_at": datetime.now().isoformat(),
        "enabled_packs": enabled,
        "patterns": patterns
    }
    with ACTIVE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return len(patterns)


def clear_screen():
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    while True:
        clear_screen()
        config = load_config()
        enabled = config.get("enabled_packs", [])
        packs = get_packs()

        print()
        print("=" * 55)
        print("       ERROR LEARNING - PATTERN PACK MANAGER")
        print("=" * 55)
        print()

        for i, name in enumerate(packs, 1):
            pack = load_pack(name)
            count = len(pack.get("patterns", []))
            desc = pack.get("description", "")[:40]
            status = "[*]" if name in enabled else "[ ]"
            print(f"  {i}. {status} {name:<12} ({count} patterns)")
            print(f"       {desc}...")
            print()

        total = sum(len(load_pack(p).get("patterns", [])) for p in enabled)
        print("-" * 55)
        print(f"  Active patterns: {total}")
        print("-" * 55)
        print()
        print("  Enter number to toggle, or:")
        print("    R = Refresh    Q = Quit")
        print()

        choice = input("  Your choice: ").strip().lower()

        if choice == 'q':
            print("\n  Goodbye!\n")
            break
        elif choice == 'r':
            continue
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(packs):
                name = packs[idx]
                if name in enabled:
                    enabled.remove(name)
                    action = "Disabled"
                else:
                    enabled.append(name)
                    action = "Enabled"
                config["enabled_packs"] = enabled
                save_config(config)
                count = merge_packs(enabled)
                print(f"\n  {action} '{name}' - {count} total patterns active")
                input("  Press Enter to continue...")
        else:
            print("\n  Invalid choice")
            input("  Press Enter to continue...")


if __name__ == "__main__":
    main()
