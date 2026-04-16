"""Central config loader with Phase-5-era defaults."""
import json
import os

DEFAULTS = {
    "enabled_packs": ["common", "learned", "custom"],
    "auto_curate": True,
    "curate_threshold": 2,
    "show_confidence": True,
    "injection_enabled": True,
    "injection_top_k": 10,
    "injection_token_cap": 400,
    "injection_min_score": 0.05,
    "injection_scope": "top_learned",
    "decay_enabled": True,
    "decay_max_age_days": 30,
    "llm_curate_enabled": False,
    "vote_down_threshold": 3,
}


def load_config(user_overrides):
    merged = dict(DEFAULTS)
    if user_overrides:
        merged.update(user_overrides)
    return merged


def read_config_file(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def active_config():
    path = os.environ.get("ERROR_LEARNING_CONFIG_PATH") or os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT") or ".", "config.json"
    )
    return load_config(read_config_file(path))
