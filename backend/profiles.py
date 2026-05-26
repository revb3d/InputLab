from __future__ import annotations

from copy import deepcopy


def safe_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def safe_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def default_macro_steps() -> list[dict]:
    return [
        {"button": "X", "hold_ms": 100, "delay_ms": 1000},
        {"button": "A", "hold_ms": 90, "delay_ms": 13000},
        {"button": "A", "hold_ms": 90, "delay_ms": 1000},
        {"button": "A", "hold_ms": 90, "delay_ms": 1000},
    ]


def default_run_condition() -> dict:
    return {
        "window_title": "",
        "process_name": "",
    }


def default_profile_stats() -> dict:
    return {
        "total_loops": 0,
        "total_runtime_seconds": 0.0,
        "last_run_at": "",
        "last_run_duration_seconds": 0.0,
    }


def build_macro_profile(
    profile_id: str,
    name: str,
    hotkey: str = "f3",
    interval_seconds: float = 78,
    steps: list[dict] | None = None,
    run_condition: dict | None = None,
    notes: str = "",
    stats: dict | None = None,
) -> dict:
    base_stats = default_profile_stats()
    loaded_stats = stats or {}
    for key in base_stats:
        if key in loaded_stats:
            base_stats[key] = loaded_stats[key]
    return {
        "id": profile_id,
        "name": name,
        "hotkey": hotkey,
        "interval_seconds": interval_seconds,
        "steps": [step.copy() for step in (steps if steps is not None else default_macro_steps())],
        "run_condition": {
            "window_title": str((run_condition or default_run_condition()).get("window_title", "")).strip(),
            "process_name": str((run_condition or default_run_condition()).get("process_name", "")).strip().lower(),
        },
        "notes": str(notes).strip(),
        "stats": {
            "total_loops": int(base_stats.get("total_loops", 0) or 0),
            "total_runtime_seconds": float(base_stats.get("total_runtime_seconds", 0.0) or 0.0),
            "last_run_at": str(base_stats.get("last_run_at", "") or ""),
            "last_run_duration_seconds": float(base_stats.get("last_run_duration_seconds", 0.0) or 0.0),
        },
    }


def clone_macro_profile(profile: dict) -> dict:
    cloned = profile.copy()
    cloned["steps"] = [step.copy() for step in profile.get("steps", [])]
    cloned["run_condition"] = dict(profile.get("run_condition", {}))
    cloned["stats"] = dict(profile.get("stats", {}))
    return cloned


def clone_macro_profiles(profiles: list[dict]) -> list[dict]:
    return [clone_macro_profile(profile) for profile in profiles]


def build_default_config(default_theme_name: str) -> dict:
    return {
        "toggle_hotkey": "f2",
        "target_key": "w",
        "theme_name": default_theme_name,
        "performance_mode": True,
        "overlay_enabled": False,
        "close_to_tray": True,
        "minimize_to_tray": True,
        "selected_macro_profile_id": "main",
        "macro_profiles": [
            build_macro_profile("main", "Main Macro"),
        ],
    }


def normalize_macro_steps(raw_steps) -> list[dict]:
    normalized_steps = []
    fallback_steps = default_macro_steps()
    source_steps = raw_steps if isinstance(raw_steps, list) and raw_steps else fallback_steps
    for index, raw_step in enumerate(source_steps):
        base_step = fallback_steps[index].copy() if index < len(fallback_steps) else {
            "button": "",
            "hold_ms": 90,
            "delay_ms": 120,
        }
        if isinstance(raw_step, dict):
            loaded_step = raw_step
            base_step["button"] = str(loaded_step.get("button", base_step["button"])).upper()
            base_step["hold_ms"] = safe_int(loaded_step.get("hold_ms"), base_step["hold_ms"])
            base_step["delay_ms"] = safe_int(loaded_step.get("delay_ms"), base_step["delay_ms"])
        normalized_steps.append(base_step)
    return normalized_steps


def normalize_macro_profile(raw_profile, index: int) -> dict | None:
    if not isinstance(raw_profile, dict):
        return None

    profile_id = str(raw_profile.get("id", "")).strip() or f"profile-{index}"
    profile_name = str(raw_profile.get("name", "")).strip() or f"Profile {index}"
    hotkey = str(raw_profile.get("hotkey", "f3")).strip().lower()
    interval_seconds = safe_float(raw_profile.get("interval_seconds"), 78)
    steps = normalize_macro_steps(raw_profile.get("steps", []))
    run_condition = raw_profile.get("run_condition", {})
    if not isinstance(run_condition, dict):
        run_condition = {}
    notes = str(raw_profile.get("notes", "")).strip()
    stats = raw_profile.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}
    return build_macro_profile(profile_id, profile_name, hotkey, interval_seconds, steps, run_condition, notes, stats)


def normalize_loaded_config(raw_data: dict, default_theme_name: str, allowed_theme_names: set[str]) -> dict:
    config = build_default_config(default_theme_name)
    config["macro_profiles"] = clone_macro_profiles(config["macro_profiles"])

    config["toggle_hotkey"] = str(raw_data.get("toggle_hotkey", config["toggle_hotkey"])).lower()
    config["target_key"] = str(raw_data.get("target_key", config["target_key"])).lower()
    config["theme_name"] = str(raw_data.get("theme_name", config["theme_name"])).strip() or config["theme_name"]
    config["performance_mode"] = bool(raw_data.get("performance_mode", config["performance_mode"]))
    config["overlay_enabled"] = bool(raw_data.get("overlay_enabled", config["overlay_enabled"]))
    config["close_to_tray"] = bool(raw_data.get("close_to_tray", config["close_to_tray"]))
    config["minimize_to_tray"] = bool(raw_data.get("minimize_to_tray", config["minimize_to_tray"]))

    if config["theme_name"] == "Graphite + Electric Lime":
        config["theme_name"] = default_theme_name
    if config["theme_name"] not in allowed_theme_names:
        config["theme_name"] = default_theme_name

    raw_profiles = raw_data.get("macro_profiles")
    normalized_profiles = []
    if isinstance(raw_profiles, list) and raw_profiles:
        for index, raw_profile in enumerate(raw_profiles, start=1):
            normalized = normalize_macro_profile(raw_profile, index)
            if normalized is not None:
                normalized_profiles.append(normalized)

    if not normalized_profiles:
        legacy_steps = normalize_macro_steps(raw_data.get("macro_steps", []))
        normalized_profiles = [
            build_macro_profile(
                "main",
                "Main Macro",
                hotkey=str(raw_data.get("macro_hotkey", "f3")).lower(),
                interval_seconds=safe_float(raw_data.get("macro_interval_seconds"), 78),
                steps=legacy_steps,
            )
        ]

    config["macro_profiles"] = normalized_profiles
    selected_profile_id = str(raw_data.get("selected_macro_profile_id", normalized_profiles[0]["id"])).strip()
    if not any(profile["id"] == selected_profile_id for profile in normalized_profiles):
        selected_profile_id = normalized_profiles[0]["id"]
    config["selected_macro_profile_id"] = selected_profile_id
    return config


def clone_config(config: dict) -> dict:
    cloned = deepcopy(config)
    cloned["macro_profiles"] = clone_macro_profiles(cloned.get("macro_profiles", []))
    return cloned

