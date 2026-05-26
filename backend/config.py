from __future__ import annotations

import json
from pathlib import Path

from backend.profiles import build_default_config, clone_config, normalize_loaded_config


APP_DIR = Path(__file__).resolve().parent.parent
USER_DATA_DIR = Path.home() / "AppData" / "Local" / "InputLab"
CONFIG_PATH = USER_DATA_DIR / "config.json"
LEGACY_CONFIG_PATH = APP_DIR / "config.json"


def ensure_user_data_dir() -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_config_payload(payload: dict) -> None:
    ensure_user_data_dir()
    CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_config_file(path: Path, default_theme_name: str, allowed_theme_names: set[str]) -> dict | None:
    if not path.exists():
        return None

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    return normalize_loaded_config(raw_data, default_theme_name, allowed_theme_names)


def load_config(default_theme_name: str, allowed_theme_names: set[str]) -> dict:
    default_config = clone_config(build_default_config(default_theme_name))
    ensure_user_data_dir()

    if not CONFIG_PATH.exists():
        legacy_config = load_config_file(LEGACY_CONFIG_PATH, default_theme_name, allowed_theme_names)
        if legacy_config is not None:
            write_config_payload(legacy_config)
            return legacy_config

        write_config_payload(default_config)
        return default_config

    loaded_config = load_config_file(CONFIG_PATH, default_theme_name, allowed_theme_names)
    if loaded_config is not None:
        return loaded_config

    write_config_payload(default_config)
    return default_config

