from __future__ import annotations

from dataclasses import dataclass, field

from backend.profiles import clone_macro_profiles, default_profile_stats


@dataclass
class AppState:
    toggle_hotkey: str
    target_key: str
    theme_name: str
    performance_mode: bool
    overlay_enabled: bool
    close_to_tray: bool
    minimize_to_tray: bool
    selected_macro_profile_id: str
    macro_profiles: list[dict]
    active_macro_profile_id: str = ""
    session_profile_stats: dict[str, dict] = field(default_factory=dict)
    macro_hotkey: str = ""
    macro_interval_seconds: float = 78
    macro_steps: list[dict] = field(default_factory=list)
    macro_run_condition: dict = field(default_factory=dict)
    macro_notes: str = ""
    macro_stats: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "AppState":
        state = cls(
            toggle_hotkey=config["toggle_hotkey"],
            target_key=config["target_key"],
            theme_name=config["theme_name"],
            performance_mode=config["performance_mode"],
            overlay_enabled=config["overlay_enabled"],
            close_to_tray=config["close_to_tray"],
            minimize_to_tray=config["minimize_to_tray"],
            selected_macro_profile_id=config["selected_macro_profile_id"],
            macro_profiles=clone_macro_profiles(config["macro_profiles"]),
            session_profile_stats={
                profile["id"]: {"session_loops": 0, "session_runtime_seconds": 0.0}
                for profile in config["macro_profiles"]
            },
        )
        state.sync_active_profile_fields()
        return state

    def get_profile_by_id(self, profile_id: str) -> dict:
        for profile in self.macro_profiles:
            if profile["id"] == profile_id:
                return profile
        return self.macro_profiles[0]

    def get_selected_profile(self) -> dict:
        return self.get_profile_by_id(self.selected_macro_profile_id)

    def sync_active_profile_fields(self) -> None:
        profile = self.get_selected_profile()
        self.macro_hotkey = profile["hotkey"]
        self.macro_interval_seconds = profile["interval_seconds"]
        self.macro_steps = [step.copy() for step in profile["steps"]]
        self.macro_run_condition = profile["run_condition"].copy()
        self.macro_notes = profile["notes"]
        self.macro_stats = profile["stats"].copy()

    def sync_session_profile_stats(self) -> None:
        updated = {}
        for profile in self.macro_profiles:
            updated[profile["id"]] = self.session_profile_stats.get(
                profile["id"],
                {"session_loops": 0, "session_runtime_seconds": 0.0},
            )
        self.session_profile_stats = updated

    def to_config_payload(self) -> dict:
        selected_profile = self.get_selected_profile()
        return {
            "toggle_hotkey": self.toggle_hotkey,
            "target_key": self.target_key,
            "theme_name": self.theme_name,
            "performance_mode": self.performance_mode,
            "overlay_enabled": self.overlay_enabled,
            "close_to_tray": self.close_to_tray,
            "minimize_to_tray": self.minimize_to_tray,
            "selected_macro_profile_id": self.selected_macro_profile_id,
            "macro_profiles": self.macro_profiles,
            "macro_hotkey": selected_profile["hotkey"],
            "macro_interval_seconds": selected_profile["interval_seconds"],
            "macro_steps": selected_profile["steps"],
        }

    def get_profile_stats(self, profile: dict | None = None) -> dict:
        target_profile = profile or self.get_selected_profile()
        return target_profile.get("stats", default_profile_stats())
