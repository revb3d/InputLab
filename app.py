import json
import ctypes
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import uuid
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import keyboard
from PIL import Image
try:
    import pystray
    from pystray import MenuItem as TrayMenuItem
except ImportError:
    pystray = None
    TrayMenuItem = None

try:
    import vgamepad as vg
except ImportError:
    vg = None


APP_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = Path.home() / "AppData" / "Local" / "InputLab"
CONFIG_PATH = USER_DATA_DIR / "config.json"
LEGACY_CONFIG_PATH = APP_DIR / "config.json"
APP_VERSION = "1.3.0"
DEFAULT_UPDATE_MANIFEST_URL = "https://api.github.com/repos/revb3d/InputLab/releases/latest"
LOGO_PNG_PATH = APP_DIR / "InputLabLogo.png"
LOGO_ICO_PATH = APP_DIR / "InputLabLogo.ico"
HIGH_PERFORMANCE_UI = True
THEME_PRESETS = {
    "Graphite + Electric Lime": {
        "app_bg": "#090c0f",
        "shell": "#10151a",
        "shell_high": "#161d24",
        "panel": "#121922",
        "panel_high": "#1a2430",
        "panel_low": "#0d1218",
        "field": "#16202a",
        "field_hover": "#1d2936",
        "border": "#2d3b4b",
        "border_soft": "#202b38",
        "text": "#f5fbff",
        "muted": "#9badbf",
        "faint": "#728195",
        "blue": "#89ff3d",
        "blue_hover": "#a6ff74",
        "green": "#5ce65c",
        "green_deep": "#287a35",
        "red": "#ff5a5a",
        "amber": "#f3c94a",
        "cyan": "#69f0c1",
    },
    "Midnight Navy + Amber": {
        "app_bg": "#070a10",
        "shell": "#0b1220",
        "shell_high": "#121c2d",
        "panel": "#10192a",
        "panel_high": "#172339",
        "panel_low": "#09111d",
        "field": "#132033",
        "field_hover": "#1b2b45",
        "border": "#273756",
        "border_soft": "#19253a",
        "text": "#f7f4ee",
        "muted": "#a8b5c9",
        "faint": "#7987a0",
        "blue": "#ffb443",
        "blue_hover": "#ffc96f",
        "green": "#f59e0b",
        "green_deep": "#9a5d11",
        "red": "#f87171",
        "amber": "#ffd166",
        "cyan": "#66c7ff",
    },
    "Carbon + Ice Blue": {
        "app_bg": "#06080b",
        "shell": "#0c1015",
        "shell_high": "#151b23",
        "panel": "#10161d",
        "panel_high": "#18212c",
        "panel_low": "#0a0f15",
        "field": "#141c26",
        "field_hover": "#1a2634",
        "border": "#2b394b",
        "border_soft": "#1d2735",
        "text": "#f4fbff",
        "muted": "#9caec2",
        "faint": "#71839a",
        "blue": "#61c8ff",
        "blue_hover": "#92dcff",
        "green": "#3fc4ff",
        "green_deep": "#1b7299",
        "red": "#ff6b6b",
        "amber": "#f7c65d",
        "cyan": "#b5f2ff",
    },
    "Gunmetal + Redline": {
        "app_bg": "#09090a",
        "shell": "#141416",
        "shell_high": "#1a1b1f",
        "panel": "#18191d",
        "panel_high": "#23252b",
        "panel_low": "#101114",
        "field": "#1d2026",
        "field_hover": "#292d35",
        "border": "#373c46",
        "border_soft": "#272b33",
        "text": "#fff7f7",
        "muted": "#b8a6ab",
        "faint": "#85777d",
        "blue": "#ff4d4d",
        "blue_hover": "#ff7878",
        "green": "#ff6464",
        "green_deep": "#9c2e2e",
        "red": "#ff3b3b",
        "amber": "#ff9f43",
        "cyan": "#ffb4b4",
    },
    "Obsidian + Emerald": {
        "app_bg": "#060a08",
        "shell": "#0d1411",
        "shell_high": "#142019",
        "panel": "#0f1a14",
        "panel_high": "#18261f",
        "panel_low": "#09120d",
        "field": "#132018",
        "field_hover": "#1a2d23",
        "border": "#2a4336",
        "border_soft": "#1b2c24",
        "text": "#f3fff8",
        "muted": "#9fbaa9",
        "faint": "#6f8a79",
        "blue": "#2ecc71",
        "blue_hover": "#58df91",
        "green": "#25c06d",
        "green_deep": "#196a43",
        "red": "#ff6f61",
        "amber": "#e7c15a",
        "cyan": "#7ef0c7",
    },
    "Slate + Violet": {
        "app_bg": "#090910",
        "shell": "#12131c",
        "shell_high": "#1a1d29",
        "panel": "#151824",
        "panel_high": "#202534",
        "panel_low": "#0d1018",
        "field": "#1a1f2d",
        "field_hover": "#242b3d",
        "border": "#3a4360",
        "border_soft": "#262d42",
        "text": "#f8f7ff",
        "muted": "#a7afca",
        "faint": "#757e9d",
        "blue": "#8b7dff",
        "blue_hover": "#a69bff",
        "green": "#7d6bff",
        "green_deep": "#4d3fa8",
        "red": "#ff6f91",
        "amber": "#f6c667",
        "cyan": "#cabfff",
    },
}
DEFAULT_THEME_NAME = "Graphite + Electric Lime"
THEME = THEME_PRESETS[DEFAULT_THEME_NAME].copy()


class GradientButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text: str,
        command,
        colors: tuple[str, str],
        hover_colors: tuple[str, str],
        width: int = 174,
        height: int = 48,
        corner_radius: int = 16,
        outline_color: str | None = None,
    ) -> None:
        parent_bg = THEME["panel_low"]
        try:
            raw_parent_bg = parent.cget("fg_color")
            if isinstance(raw_parent_bg, tuple):
                parent_bg = raw_parent_bg[1]
            elif isinstance(raw_parent_bg, str) and raw_parent_bg != "transparent":
                parent_bg = raw_parent_bg
        except Exception:
            pass

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent_bg,
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.colors = colors
        self.hover_colors = hover_colors
        self.button_width = width
        self.button_height = height
        self.corner_radius = corner_radius
        self.outline_color = outline_color
        self.current_colors = colors
        self.animation_after_id = None
        self.sheen_after_id = None
        self.sheen_x = -72
        self.is_hovering = False
        self.is_pressed = False
        self.radius = min(self.corner_radius, self.button_height // 2, self.button_width // 2)
        self.vertical_spans = self.build_vertical_spans()
        self.gradient_cache = {}
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.draw(self.colors)

    def on_enter(self, _event) -> None:
        self.is_hovering = True
        self.animate_to(self.hover_colors)
        self.start_sheen()

    def on_leave(self, _event) -> None:
        self.is_hovering = False
        self.is_pressed = False
        if self.sheen_after_id is not None:
            self.after_cancel(self.sheen_after_id)
            self.sheen_after_id = None
        self.sheen_x = -48
        self.animate_to(self.colors)

    def on_press(self, _event) -> None:
        self.is_pressed = True
        self.draw(self.darken_pair(self.current_colors, 0.9), pressed=True)

    def on_release(self, event) -> None:
        was_pressed = self.is_pressed
        self.is_pressed = False
        inside = 0 <= event.x <= self.button_width and 0 <= event.y <= self.button_height
        self.animate_to(self.hover_colors if self.is_hovering else self.colors)
        if was_pressed and inside:
            self.command()

    def animate_to(self, target_colors: tuple[str, str]) -> None:
        if self.animation_after_id is not None:
            self.after_cancel(self.animation_after_id)
            self.animation_after_id = None

        start_colors = self.current_colors
        frames = 3

        def step(frame: int) -> None:
            ratio = frame / frames
            colors = (
                self.mix_hex(start_colors[0], target_colors[0], ratio),
                self.mix_hex(start_colors[1], target_colors[1], ratio),
            )
            self.draw(colors)
            if frame < frames:
                self.animation_after_id = self.after(12, lambda: step(frame + 1))
            else:
                self.animation_after_id = None

        step(1)

    def draw(self, colors: tuple[str, str], pressed: bool = False) -> None:
        self.current_colors = colors
        self.delete("all")
        if not pressed:
            self.draw_shadow(self.radius)
        render_colors = self.darken_pair(colors, 0.72 if not pressed else 0.64)
        gradient = self.get_gradient(render_colors)
        for x, color in enumerate(gradient):
            top, bottom = self.vertical_spans[x]
            self.create_line(x, top, x, bottom, fill=color)
        if self.is_hovering and not HIGH_PERFORMANCE_UI:
            self.draw_sheen()
        if self.outline_color:
            self.draw_rounded_border(self.radius)
        self.create_text(
            self.button_width // 2,
            (self.button_height // 2) + (1 if pressed else 0),
            text=self.text,
            fill=THEME["text"],
            font=("Segoe UI Semibold", 15, "bold"),
        )

    def draw_shadow(self, radius: int) -> None:
        width = self.button_width - 2
        height = self.button_height - 2
        shadow = "#06101c"
        self.create_arc(2, 4, radius * 2 + 2, radius * 2 + 4, start=90, extent=90, style="arc", outline=shadow)
        self.create_arc(width - radius * 2, 4, width, radius * 2 + 4, start=0, extent=90, style="arc", outline=shadow)
        self.create_arc(2, height - radius * 2, radius * 2 + 2, height, start=180, extent=90, style="arc", outline=shadow)
        self.create_arc(width - radius * 2, height - radius * 2, width, height, start=270, extent=90, style="arc", outline=shadow)
        self.create_line(radius + 2, 4, width - radius, 4, fill=shadow)
        self.create_line(radius + 2, height, width - radius, height, fill=shadow)
        self.create_line(2, radius + 4, 2, height - radius, fill=shadow)
        self.create_line(width, radius + 4, width, height - radius, fill=shadow)

    def draw_sheen(self) -> None:
        band_width = 72
        center = band_width / 2
        gradient = self.get_gradient(self.current_colors)
        for offset in range(band_width):
            x = int(self.sheen_x + offset)
            if x < 0 or x >= self.button_width:
                continue
            alpha = max(0, 1 - abs(offset - center) / center)
            alpha = alpha * alpha
            color = self.mix_hex(gradient[x], THEME["shell_high"], alpha * 0.42)
            top, bottom = self.vertical_spans[x]
            taper = int(abs(offset - center) * 0.14)
            sheen_top = top + 3 + taper
            sheen_bottom = bottom - 3 - taper
            if sheen_top < sheen_bottom:
                self.create_line(x, sheen_top, x, sheen_bottom, fill=color)

    def start_sheen(self) -> None:
        if HIGH_PERFORMANCE_UI:
            return

        self.sheen_x = -60

        def step() -> None:
            if not self.is_hovering:
                self.sheen_after_id = None
                return
            self.sheen_x += 34
            self.draw(self.current_colors)
            if self.sheen_x < self.button_width + 52:
                self.sheen_after_id = self.after(8, step)
            else:
                self.sheen_after_id = self.after(320, self.restart_sheen)

        if self.sheen_after_id is None:
            step()

    def restart_sheen(self) -> None:
        self.sheen_after_id = None
        if self.is_hovering:
            self.start_sheen()

    def draw_rounded_border(self, radius: int) -> None:
        width = self.button_width - 1
        height = self.button_height - 1
        outline = self.outline_color or "#6ea8ff"
        self.create_arc(0, 0, radius * 2, radius * 2, start=90, extent=90, style="arc", outline=outline)
        self.create_arc(width - radius * 2, 0, width, radius * 2, start=0, extent=90, style="arc", outline=outline)
        self.create_arc(0, height - radius * 2, radius * 2, height, start=180, extent=90, style="arc", outline=outline)
        self.create_arc(
            width - radius * 2,
            height - radius * 2,
            width,
            height,
            start=270,
            extent=90,
            style="arc",
            outline=outline,
        )
        self.create_line(radius, 0, width - radius, 0, fill=outline)
        self.create_line(radius, height, width - radius, height, fill=outline)
        self.create_line(0, radius, 0, height - radius, fill=outline)
        self.create_line(width, radius, width, height - radius, fill=outline)

    def darken_pair(self, colors: tuple[str, str], factor: float) -> tuple[str, str]:
        return tuple(self.scale_hex(color, factor) for color in colors)

    def scale_hex(self, color: str, factor: float) -> str:
        red, green, blue = self.hex_to_rgb(color)
        return f"#{int(red * factor):02x}{int(green * factor):02x}{int(blue * factor):02x}"

    def mix_hex(self, left: str, right: str, ratio: float) -> str:
        left_rgb = self.hex_to_rgb(left)
        right_rgb = self.hex_to_rgb(right)
        values = [
            int(left_rgb[index] + (right_rgb[index] - left_rgb[index]) * ratio)
            for index in range(3)
        ]
        return f"#{values[0]:02x}{values[1]:02x}{values[2]:02x}"

    def build_vertical_spans(self) -> list[tuple[int, int]]:
        spans = []
        for x in range(self.button_width):
            top = 0
            bottom = self.button_height
            if x < self.radius:
                offset = self.radius - x
                inset = int(self.radius - (self.radius * self.radius - offset * offset) ** 0.5)
                top = inset
                bottom = self.button_height - inset
            elif x >= self.button_width - self.radius:
                offset = x - (self.button_width - self.radius - 1)
                inset = int(self.radius - (self.radius * self.radius - offset * offset) ** 0.5)
                top = inset
                bottom = self.button_height - inset
            spans.append((top, bottom))
        return spans

    def get_gradient(self, colors: tuple[str, str]) -> list[str]:
        if colors in self.gradient_cache:
            return self.gradient_cache[colors]

        left = self.hex_to_rgb(colors[0])
        right = self.hex_to_rgb(colors[1])
        gradient = []
        for x in range(self.button_width):
            ratio = x / max(self.button_width - 1, 1)
            values = [
                int(left[index] + (right[index] - left[index]) * ratio)
                for index in range(3)
            ]
            gradient.append(f"#{values[0]:02x}{values[1]:02x}{values[2]:02x}")
        self.gradient_cache[colors] = gradient
        return gradient

    @staticmethod
    def hex_to_rgb(color: str) -> tuple[int, int, int]:
        color = color.lstrip("#")
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
BUTTON_OPTIONS = [
    "A",
    "B",
    "X",
    "Y",
    "LB",
    "RB",
    "BACK",
    "START",
    "GUIDE",
    "L3",
    "R3",
    "DPAD_UP",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",
]
BUTTON_ENUM_NAMES = {
    "A": "XUSB_GAMEPAD_A",
    "B": "XUSB_GAMEPAD_B",
    "X": "XUSB_GAMEPAD_X",
    "Y": "XUSB_GAMEPAD_Y",
    "LB": "XUSB_GAMEPAD_LEFT_SHOULDER",
    "RB": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "BACK": "XUSB_GAMEPAD_BACK",
    "START": "XUSB_GAMEPAD_START",
    "GUIDE": "XUSB_GAMEPAD_GUIDE",
    "L3": "XUSB_GAMEPAD_LEFT_THUMB",
    "R3": "XUSB_GAMEPAD_RIGHT_THUMB",
    "DPAD_UP": "XUSB_GAMEPAD_DPAD_UP",
    "DPAD_DOWN": "XUSB_GAMEPAD_DPAD_DOWN",
    "DPAD_LEFT": "XUSB_GAMEPAD_DPAD_LEFT",
    "DPAD_RIGHT": "XUSB_GAMEPAD_DPAD_RIGHT",
}
RECORDER_KEY_TO_BUTTON = {
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "q": "LB",
    "e": "RB",
    "1": "BACK",
    "2": "START",
    "up": "DPAD_UP",
    "down": "DPAD_DOWN",
    "left": "DPAD_LEFT",
    "right": "DPAD_RIGHT",
}
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


DEFAULT_CONFIG = {
    "toggle_hotkey": "f2",
    "target_key": "w",
    "theme_name": DEFAULT_THEME_NAME,
    "overlay_enabled": False,
    "close_to_tray": True,
    "minimize_to_tray": True,
    "selected_macro_profile_id": "main",
    "macro_profiles": [
        build_macro_profile("main", "Main Macro"),
    ],
}


class KeyHoldApp:
    def __init__(self) -> None:
        self.configure_windows_dpi_awareness()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.apply_windows_app_id()

        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title("InputLab")
        self.root.geometry("1320x820")
        self.root.minsize(1100, 720)
        self.ensure_window_opaque()

        self.config = self.load_config()
        self.theme_name = self.config["theme_name"]
        self.apply_theme(self.theme_name)
        self.root.configure(fg_color=THEME["app_bg"])
        self.logo_image = None
        self.logo_photo = None
        self.apply_window_icon()
        self.startup_splash = None
        self.startup_status_var = tk.StringVar(value="Loading InputLab...")
        self.create_startup_splash()

        self.toggle_hotkey = self.config["toggle_hotkey"]
        self.target_key = self.config["target_key"]
        self.update_manifest_url = DEFAULT_UPDATE_MANIFEST_URL
        self.overlay_enabled = self.config["overlay_enabled"]
        self.close_to_tray = self.config["close_to_tray"]
        self.minimize_to_tray = self.config["minimize_to_tray"]
        self.macro_profiles = self.config["macro_profiles"]
        self.selected_macro_profile_id = self.config["selected_macro_profile_id"]
        self.active_macro_profile_id = ""
        self.profile_editor_ready = False
        self.sync_active_profile_fields()

        self.is_holding = False
        self.capture_target_hook = None
        self.key_hold_hotkey_handle = None
        self.macro_hotkey_handles = {}

        self.virtual_gamepad = None
        self.macro_thread = None
        self.macro_running = threading.Event()

        self.key_status_var = ctk.StringVar(value="Idle")
        self.key_detail_var = ctk.StringVar(
            value=f"Press {self.toggle_hotkey.upper()} to toggle {self.target_key.upper()}."
        )
        self.macro_status_var = ctk.StringVar(value="Ready")
        self.macro_detail_var = ctk.StringVar(
            value=f"Press {self.macro_hotkey.upper()} to start or stop the {self.get_selected_profile()['name']} controller macro."
        )
        self.macro_current_step_var = ctk.StringVar(value="Current step: None")
        self.macro_last_action_var = ctk.StringVar(value="Last action: None")
        self.macro_next_action_var = ctk.StringVar(value="Next action in: --")
        self.macro_loop_var = ctk.StringVar(value="Loop count: 0")
        self.current_view = ""
        self.update_status_var = ctk.StringVar(value=f"Version {APP_VERSION}")
        self.update_detail_var = ctk.StringVar(value="Update checks are manual.")
        self.latest_download_url = ""
        self.update_check_in_progress = False
        self.update_download_in_progress = False
        self.installing_update = False
        self.scroll_repaint_after_id = None
        self.last_keyboard_active = None
        self.last_macro_active = None
        self.key_status_pulse_after_ids = []
        self.macro_status_pulse_after_ids = []
        self.live_progress_pulse_after_id = None
        self.view_animation_after_ids = []
        self.ui_root = None
        self.section_transition_after_ids = []
        self.body_canvas_last_width = 0
        self.window_capture_after_id = None
        self.ignore_minimize_to_tray_once = False
        self.overlay_window = None
        self.overlay_labels = {}
        self.overlay_update_after_id = None
        self.tray_icon = None
        self.tray_thread = None
        self.exiting_to_system = False
        self.macro_run_started_at = 0.0
        self.active_macro_loop_count = 0
        self.session_profile_stats = {profile["id"]: {"session_loops": 0, "session_runtime_seconds": 0.0} for profile in self.macro_profiles}
        self.recorder_hook = None
        self.recorder_active = False
        self.recorder_key_down_times = {}
        self.recorder_steps = []
        self.recorder_last_release_at = None

        self.build_ui()
        self.root.after(0, self.show_centered_window)
        self.register_key_hold_hotkey(self.toggle_hotkey)
        self.register_macro_hotkeys()
        self.root.after(1200, self.auto_check_for_updates)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self.on_window_unmap)
        if self.overlay_enabled:
            self.root.after(900, self.enable_overlay_window)

    def load_config(self) -> dict:
        config = DEFAULT_CONFIG.copy()
        config["macro_profiles"] = [profile.copy() for profile in DEFAULT_CONFIG["macro_profiles"]]
        for profile in config["macro_profiles"]:
            profile["steps"] = [step.copy() for step in profile["steps"]]
            profile["run_condition"] = profile["run_condition"].copy()
            profile["stats"] = profile["stats"].copy()

        self.ensure_user_data_dir()

        if not CONFIG_PATH.exists():
            legacy_config = self.load_config_file(LEGACY_CONFIG_PATH)
            if legacy_config is not None:
                self.write_config_payload(legacy_config)
                return legacy_config

            self.write_config_payload(config)
            return config

        loaded_config = self.load_config_file(CONFIG_PATH)
        if loaded_config is not None:
            return loaded_config

        self.write_config_payload(config)
        return config

    def load_config_file(self, path: Path) -> dict | None:
        if not path.exists():
            return None

        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        config = DEFAULT_CONFIG.copy()
        config["macro_profiles"] = [profile.copy() for profile in DEFAULT_CONFIG["macro_profiles"]]
        for profile in config["macro_profiles"]:
            profile["steps"] = [step.copy() for step in profile["steps"]]
            profile["run_condition"] = profile["run_condition"].copy()
            profile["stats"] = profile["stats"].copy()

        config["toggle_hotkey"] = str(raw_data.get("toggle_hotkey", config["toggle_hotkey"])).lower()
        config["target_key"] = str(raw_data.get("target_key", config["target_key"])).lower()
        config["theme_name"] = str(raw_data.get("theme_name", config["theme_name"])).strip() or config["theme_name"]
        config["overlay_enabled"] = bool(raw_data.get("overlay_enabled", config["overlay_enabled"]))
        config["close_to_tray"] = bool(raw_data.get("close_to_tray", config["close_to_tray"]))
        config["minimize_to_tray"] = bool(raw_data.get("minimize_to_tray", config["minimize_to_tray"]))
        if config["theme_name"] not in THEME_PRESETS:
            config["theme_name"] = DEFAULT_THEME_NAME
        raw_profiles = raw_data.get("macro_profiles")
        normalized_profiles = []
        if isinstance(raw_profiles, list) and raw_profiles:
            for index, raw_profile in enumerate(raw_profiles, start=1):
                normalized = self.normalize_macro_profile(raw_profile, index)
                if normalized is not None:
                    normalized_profiles.append(normalized)

        if not normalized_profiles:
            legacy_steps = self.normalize_macro_steps(raw_data.get("macro_steps", []))
            normalized_profiles = [
                build_macro_profile(
                    "main",
                    "Main Macro",
                    hotkey=str(raw_data.get("macro_hotkey", "f3")).lower(),
                    interval_seconds=self.safe_float(raw_data.get("macro_interval_seconds"), 78),
                    steps=legacy_steps,
                )
            ]

        config["macro_profiles"] = normalized_profiles
        selected_profile_id = str(raw_data.get("selected_macro_profile_id", normalized_profiles[0]["id"])).strip()
        if not any(profile["id"] == selected_profile_id for profile in normalized_profiles):
            selected_profile_id = normalized_profiles[0]["id"]
        config["selected_macro_profile_id"] = selected_profile_id
        return config

    def ensure_user_data_dir(self) -> None:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def write_config_payload(self, payload: dict) -> None:
        self.ensure_user_data_dir()
        CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_config(self) -> None:
        self.sync_config_from_ui()
        selected_profile = self.get_selected_profile()
        payload = {
            "toggle_hotkey": self.toggle_hotkey,
            "target_key": self.target_key,
            "theme_name": self.theme_name,
            "overlay_enabled": self.overlay_enabled,
            "close_to_tray": self.close_to_tray,
            "minimize_to_tray": self.minimize_to_tray,
            "selected_macro_profile_id": self.selected_macro_profile_id,
            "macro_profiles": self.macro_profiles,
            "macro_hotkey": selected_profile["hotkey"],
            "macro_interval_seconds": selected_profile["interval_seconds"],
            "macro_steps": selected_profile["steps"],
        }
        self.write_config_payload(payload)

    def sync_config_from_ui(self) -> None:
        if hasattr(self, "hotkey_entry"):
            typed_hotkey = self.hotkey_entry.get().strip().lower()
            if typed_hotkey:
                self.toggle_hotkey = typed_hotkey

        if hasattr(self, "key_entry"):
            typed_target = self.key_entry.get().strip().lower()
            if typed_target:
                self.target_key = typed_target

        if self.profile_editor_ready and hasattr(self, "macro_hotkey_entry"):
            profile = self.get_selected_profile()
            typed_name = self.profile_name_entry.get().strip()
            if typed_name:
                profile["name"] = typed_name

            typed_macro_hotkey = self.macro_hotkey_entry.get().strip().lower()
            if typed_macro_hotkey:
                profile["hotkey"] = typed_macro_hotkey

            typed_interval = self.macro_interval_entry.get().strip()
            if typed_interval:
                profile["interval_seconds"] = self.safe_float(
                    typed_interval,
                    profile["interval_seconds"],
                )

            if hasattr(self, "macro_step_widgets"):
                profile["steps"] = self.collect_macro_steps(include_blank_steps=True)
            if hasattr(self, "macro_window_title_entry"):
                profile["run_condition"] = {
                    "window_title": self.macro_window_title_entry.get().strip(),
                    "process_name": self.macro_process_name_entry.get().strip().lower(),
                }
            if hasattr(self, "profile_notes_text"):
                profile["notes"] = self.profile_notes_text.get("1.0", "end").strip()

            if hasattr(self, "overlay_enabled_var"):
                self.overlay_enabled = bool(self.overlay_enabled_var.get())
            if hasattr(self, "close_to_tray_var"):
                self.close_to_tray = bool(self.close_to_tray_var.get())
            if hasattr(self, "minimize_to_tray_var"):
                self.minimize_to_tray = bool(self.minimize_to_tray_var.get())

            self.sync_active_profile_fields()

    def apply_theme(self, theme_name: str) -> None:
        selected_theme = THEME_PRESETS.get(theme_name, THEME_PRESETS[DEFAULT_THEME_NAME])
        THEME.clear()
        THEME.update(selected_theme)
        self.theme_name = theme_name if theme_name in THEME_PRESETS else DEFAULT_THEME_NAME

    def normalize_macro_steps(self, raw_steps) -> list[dict]:
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
                base_step["hold_ms"] = self.safe_int(loaded_step.get("hold_ms"), base_step["hold_ms"])
                base_step["delay_ms"] = self.safe_int(loaded_step.get("delay_ms"), base_step["delay_ms"])
            normalized_steps.append(base_step)
        return normalized_steps

    def normalize_macro_profile(self, raw_profile, index: int) -> dict | None:
        if not isinstance(raw_profile, dict):
            return None

        profile_id = str(raw_profile.get("id", "")).strip() or f"profile-{index}"
        profile_name = str(raw_profile.get("name", "")).strip() or f"Profile {index}"
        hotkey = str(raw_profile.get("hotkey", "f3")).strip().lower()
        interval_seconds = self.safe_float(raw_profile.get("interval_seconds"), 78)
        steps = self.normalize_macro_steps(raw_profile.get("steps", []))
        run_condition = raw_profile.get("run_condition", {})
        if not isinstance(run_condition, dict):
            run_condition = {}
        notes = str(raw_profile.get("notes", "")).strip()
        stats = raw_profile.get("stats", {})
        if not isinstance(stats, dict):
            stats = {}
        return build_macro_profile(profile_id, profile_name, hotkey, interval_seconds, steps, run_condition, notes, stats)

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

    def build_new_profile(self, name: str | None = None) -> dict:
        profile_number = len(self.macro_profiles) + 1
        return build_macro_profile(
            uuid.uuid4().hex,
            name or f"Profile {profile_number}",
            hotkey=self.next_available_macro_hotkey(),
        )

    def next_available_macro_hotkey(self, exclude_profile_id: str | None = None) -> str:
        used_hotkeys = {
            profile["hotkey"]
            for profile in self.macro_profiles
            if profile["id"] != exclude_profile_id
        }
        for number in range(3, 13):
            hotkey = f"f{number}"
            if hotkey not in used_hotkeys:
                return hotkey
        return ""

    def build_ui(self) -> None:
        self.update_startup_status("Building interface...")
        if self.ui_root is not None:
            self.ui_root.destroy()
            self.ui_root = None
        self.root.configure(fg_color=THEME["app_bg"])
        self.root.unbind_all("<MouseWheel>")

        outer = ctk.CTkFrame(
            self.root,
            fg_color=THEME["shell"],
            corner_radius=24,
            border_color=THEME["border"],
            border_width=1,
        )
        outer.pack(fill="both", expand=True, padx=18, pady=18)
        self.ui_root = outer

        header = ctk.CTkFrame(
            outer,
            fg_color=THEME["shell_high"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        header.pack(fill="x", padx=22, pady=(22, 14))

        self.add_accent_line(header, THEME["blue"], height=3, padx=18, pady=(16, 0))

        header_top = ctk.CTkFrame(header, fg_color="transparent")
        header_top.pack(fill="x", padx=18, pady=(12, 16))

        if LOGO_PNG_PATH.exists():
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(LOGO_PNG_PATH),
                dark_image=Image.open(LOGO_PNG_PATH),
                size=(58, 58),
            )
            logo_label = ctk.CTkLabel(header_top, text="", image=self.logo_image)
            logo_label.pack(side="left", padx=(0, 16))

        title_block = ctk.CTkFrame(header_top, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True)

        title = ctk.CTkLabel(
            title_block,
            text="InputLab",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=30, weight="bold"),
            text_color=THEME["text"],
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_block,
            text="Hotkeys, controller macros, profiles, and live action feedback in one focused control surface.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=THEME["muted"],
        )
        subtitle.pack(anchor="w", pady=(6, 0))

        version_chip = ctk.CTkLabel(
            header_top,
            text=f"v{APP_VERSION}",
            width=74,
            height=32,
            corner_radius=16,
            fg_color=THEME["field"],
            text_color=THEME["muted"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
        )
        version_chip.pack(side="right")

        scroll_host = ctk.CTkFrame(
            outer,
            fg_color=THEME["shell"],
            corner_radius=0,
        )
        scroll_host.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        self.body_canvas = tk.Canvas(
            scroll_host,
            bg=THEME["shell"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            insertborderwidth=0,
        )
        self.body_canvas.pack(side="left", fill="both", expand=True)

        self.body_scrollbar = ctk.CTkScrollbar(
            scroll_host,
            orientation="vertical",
            command=self.body_canvas.yview,
            width=10,
            button_color=THEME["field"],
            button_hover_color=THEME["field_hover"],
        )
        self.body_scrollbar.pack(side="right", fill="y", padx=(8, 0))
        self.body_canvas.configure(yscrollcommand=self.body_scrollbar.set)

        self.body_canvas_frame = tk.Frame(self.body_canvas, bg=THEME["shell"], bd=0, highlightthickness=0)
        self.body_canvas_window = self.body_canvas.create_window(
            (0, 0),
            window=self.body_canvas_frame,
            anchor="nw",
        )
        self.body_canvas_frame.bind("<Configure>", self.on_body_scroll_frame_configure)
        self.body_canvas.bind("<Configure>", self.on_body_canvas_configure)
        self.root.bind_all("<MouseWheel>", self.on_body_mousewheel, add="+")

        body = ctk.CTkFrame(self.body_canvas_frame, fg_color=THEME["shell"])
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(
            body,
            width=208,
            fg_color=THEME["panel_low"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 16))
        sidebar.pack_propagate(False)

        nav_title = ctk.CTkLabel(
            sidebar,
            text="Sections",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=16, weight="bold"),
            text_color=THEME["text"],
        )
        nav_title.pack(anchor="w", padx=18, pady=(18, 4))

        ctk.CTkLabel(
            sidebar,
            text="Live modules",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["faint"],
        ).pack(anchor="w", padx=18, pady=(0, 16))

        self.keyboard_nav_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.keyboard_nav_row.pack(fill="x", padx=14, pady=(0, 10))

        self.keyboard_activity_indicator = ctk.CTkLabel(
            self.keyboard_nav_row,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color=THEME["border"],
        )
        self.keyboard_activity_indicator.pack(side="left", padx=(2, 10))

        self.keyboard_nav_button = ctk.CTkButton(
            self.keyboard_nav_row,
            text="Keyboard Hold",
            height=48,
            corner_radius=16,
            anchor="w",
            fg_color=THEME["green_deep"],
            hover_color=THEME["green"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=lambda: self.show_view("keyboard"),
        )
        self.keyboard_nav_button.pack(side="left", fill="x", expand=True)

        self.macro_nav_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.macro_nav_row.pack(fill="x", padx=14)

        self.macro_activity_indicator = ctk.CTkLabel(
            self.macro_nav_row,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color=THEME["border"],
        )
        self.macro_activity_indicator.pack(side="left", padx=(2, 10))

        self.macro_nav_button = ctk.CTkButton(
            self.macro_nav_row,
            text="Controller Macro",
            height=48,
            corner_radius=16,
            anchor="w",
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=lambda: self.show_view("macro"),
        )
        self.macro_nav_button.pack(side="left", fill="x", expand=True)

        self.add_accent_line(sidebar, THEME["blue"], height=3, padx=18, pady=(18, 12))

        update_card = ctk.CTkFrame(
            sidebar,
            fg_color=THEME["panel"],
            corner_radius=18,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        update_card.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(
            update_card,
            text="Updates",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=14, pady=(14, 6))

        ctk.CTkLabel(
            update_card,
            textvariable=self.update_status_var,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
            wraplength=154,
            justify="left",
        ).pack(anchor="w", padx=14)

        ctk.CTkLabel(
            update_card,
            textvariable=self.update_detail_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=154,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(6, 12))

        self.check_updates_button = ctk.CTkButton(
            update_card,
            text="Check for updates",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.check_for_updates,
        )
        self.check_updates_button.pack(fill="x", padx=14, pady=(0, 8))

        self.open_update_button = ctk.CTkButton(
            update_card,
            text="Update now",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.download_and_install_update,
            state="disabled",
        )
        self.open_update_button.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(
            sidebar,
            text="App",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["faint"],
        ).pack(anchor="w", padx=18, pady=(0, 8))

        self.settings_nav_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.settings_nav_row.pack(fill="x", padx=14, pady=(0, 14))

        self.settings_nav_button = ctk.CTkButton(
            self.settings_nav_row,
            text="Settings",
            height=48,
            corner_radius=16,
            anchor="w",
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=lambda: self.show_view("settings"),
        )
        self.settings_nav_button.pack(fill="x", expand=True)

        self.content_area = ctk.CTkFrame(
            body,
            fg_color=THEME["panel_low"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        self.content_area.pack(side="left", fill="both", expand=True)

        self.workspace_accent = ctk.CTkFrame(
            self.content_area,
            fg_color=THEME["blue"],
            height=4,
        )
        self.workspace_accent.pack(fill="x", padx=20, pady=(18, 0))
        self.workspace_accent.pack_propagate(False)

        self.keyboard_view = ctk.CTkFrame(self.content_area, fg_color=THEME["panel_low"])
        self.macro_view = ctk.CTkFrame(self.content_area, fg_color=THEME["panel_low"])
        self.settings_view = ctk.CTkFrame(self.content_area, fg_color=THEME["panel_low"])
        self.section_transition_overlay = ctk.CTkFrame(
            self.content_area,
            fg_color=THEME["shell"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        self.section_transition_panel = ctk.CTkFrame(
            self.section_transition_overlay,
            fg_color=THEME["panel_high"],
            corner_radius=22,
            border_color=THEME["border_soft"],
            border_width=1,
            width=420,
            height=220,
        )
        self.section_transition_panel.place(relx=0.5, rely=0.5, anchor="center")
        self.section_transition_panel.pack_propagate(False)

        self.section_transition_title = ctk.CTkLabel(
            self.section_transition_panel,
            text="InputLab",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=24, weight="bold"),
            text_color=THEME["text"],
        )
        self.section_transition_title.pack(pady=(34, 10))

        self.section_transition_label = ctk.CTkLabel(
            self.section_transition_panel,
            text="",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=20, weight="bold"),
            text_color=THEME["text"],
        )
        self.section_transition_label.pack()

        self.section_transition_detail = ctk.CTkLabel(
            self.section_transition_panel,
            text="Preparing the interface...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
        )
        self.section_transition_detail.pack(pady=(8, 18))

        self.section_transition_bar_track = ctk.CTkFrame(
            self.section_transition_panel,
            fg_color=THEME["field"],
            corner_radius=6,
            width=248,
            height=8,
        )
        self.section_transition_bar_track.pack()
        self.section_transition_bar_track.pack_propagate(False)

        self.section_transition_bar = ctk.CTkFrame(
            self.section_transition_bar_track,
            fg_color=THEME["blue"],
            corner_radius=6,
            width=148,
            height=8,
        )
        self.section_transition_bar.place(relx=0, rely=0, relheight=1)

        self.update_startup_status("Loading sections...")
        self.build_keyboard_tab(self.keyboard_view)
        self.build_macro_tab(self.macro_view)
        self.build_settings_tab(self.settings_view)
        self.show_view(self.current_view if self.current_view in {"keyboard", "macro", "settings"} else "keyboard", instant=True)
        self.update_activity_indicators()

    def on_body_scroll_frame_configure(self, _event=None) -> None:
        self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))

    def on_body_canvas_configure(self, event) -> None:
        if event.width != self.body_canvas_last_width:
            self.body_canvas_last_width = event.width
            self.body_canvas.itemconfigure(self.body_canvas_window, width=event.width)

    def on_body_mousewheel(self, event) -> None:
        if not self.pointer_is_over_widget(self.body_canvas):
            return

        bbox = self.body_canvas.bbox("all")
        if bbox is None or bbox[3] <= self.body_canvas.winfo_height():
            return

        self.body_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.repaint_after_scroll()

    def repaint_after_scroll(self) -> None:
        if HIGH_PERFORMANCE_UI:
            return
        if self.scroll_repaint_after_id is not None:
            self.root.after_cancel(self.scroll_repaint_after_id)
        self.scroll_repaint_after_id = self.root.after(45, self.finish_scroll_repaint)

    def finish_scroll_repaint(self) -> None:
        self.scroll_repaint_after_id = None
        self.body_canvas.update_idletasks()

    @staticmethod
    def pointer_is_over_widget(widget) -> bool:
        pointer_x = widget.winfo_pointerx()
        pointer_y = widget.winfo_pointery()
        widget_x = widget.winfo_rootx()
        widget_y = widget.winfo_rooty()
        return (
            widget_x <= pointer_x <= widget_x + widget.winfo_width()
            and widget_y <= pointer_y <= widget_y + widget.winfo_height()
        )

    def show_view(self, view_name: str, instant: bool = False) -> None:
        if self.current_view == view_name:
            return

        if instant or not hasattr(self, "section_transition_overlay"):
            self.apply_view_switch(view_name)
            return

        self.start_section_transition(view_name)

    def apply_view_switch(self, view_name: str) -> None:
        self.current_view = view_name

        self.keyboard_view.pack_forget()
        self.macro_view.pack_forget()
        self.settings_view.pack_forget()

        if view_name == "keyboard":
            self.keyboard_view.pack(fill="both", expand=True)
            self.keyboard_nav_button.configure(
                fg_color=THEME["green_deep"],
                hover_color=THEME["green"],
                text_color=THEME["text"],
            )
            self.macro_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
            self.settings_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
        elif view_name == "macro":
            self.macro_view.pack(fill="both", expand=True)
            self.macro_nav_button.configure(
                fg_color=THEME["green_deep"],
                hover_color=THEME["green"],
                text_color=THEME["text"],
            )
            self.keyboard_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
            self.settings_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
        else:
            self.settings_view.pack(fill="both", expand=True)
            self.settings_nav_button.configure(
                fg_color=THEME["green_deep"],
                hover_color=THEME["green"],
                text_color=THEME["text"],
            )
            self.keyboard_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
            self.macro_nav_button.configure(
                fg_color=THEME["field"],
                hover_color=THEME["field_hover"],
                text_color="#dce7f8",
            )
        self.body_canvas.yview_moveto(0)
        self.update_activity_indicators()
        if not HIGH_PERFORMANCE_UI:
            self.animate_view_switch()

    def start_section_transition(self, view_name: str) -> None:
        for after_id in self.section_transition_after_ids:
            self.root.after_cancel(after_id)
        self.section_transition_after_ids = []

        labels = {
            "keyboard": "Loading Keyboard Hold...",
            "macro": "Loading Controller Macro...",
            "settings": "Loading Settings...",
        }
        self.section_transition_label.configure(text=labels.get(view_name, "Loading..."))
        self.section_transition_detail.configure(text="Applying layout and refreshing controls...")
        self.section_transition_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.section_transition_overlay.lift()

        self.section_transition_after_ids.append(
            self.root.after(0 if HIGH_PERFORMANCE_UI else 20, lambda: self.finish_section_transition(view_name))
        )

    def finish_section_transition(self, view_name: str) -> None:
        self.apply_view_switch(view_name)
        self.section_transition_after_ids.append(
            self.root.after(40 if HIGH_PERFORMANCE_UI else 90, self.hide_section_transition)
        )

    def hide_section_transition(self) -> None:
        self.section_transition_overlay.place_forget()
        self.section_transition_after_ids = []

    def animate_view_switch(self) -> None:
        for after_id in self.view_animation_after_ids:
            self.root.after_cancel(after_id)
        self.view_animation_after_ids = []

        frames = [
            (0, THEME["blue"], 4),
            (35, THEME["blue_hover"], 7),
            (80, THEME["cyan"], 5),
            (130, THEME["blue"], 4),
        ]
        for delay, color, height in frames:
            after_id = self.root.after(
                delay,
                lambda value=color, line_height=height: self.workspace_accent.configure(
                    fg_color=value,
                    height=line_height,
                ),
            )
            self.view_animation_after_ids.append(after_id)

    def build_keyboard_tab(self, tab) -> None:
        self.add_tab_heading(
            tab,
            "Keyboard Hold",
            "Toggle any keyboard key from a global hotkey while InputLab stays open in the background.",
        )

        status_card = self.build_status_card(
            tab,
            self.key_status_var,
            self.key_detail_var,
        )
        status_card.pack(fill="x", padx=20, pady=(0, 16))

        form = self.build_section_frame(tab)
        form.pack(fill="x", padx=20, pady=(0, 16))

        self.hotkey_entry = self.add_labeled_entry(
            form,
            "Toggle hotkey",
            "Example: f2, ctrl+shift+h",
            self.toggle_hotkey,
        )
        self.key_entry = self.add_labeled_entry(
            form,
            "Key to hold",
            "Example: m, space, left",
            self.target_key,
        )

        target_actions = ctk.CTkFrame(form, fg_color="transparent")
        target_actions.pack(fill="x", padx=18, pady=(0, 14))

        capture_target_button = ctk.CTkButton(
            target_actions,
            text="Capture Held Key",
            height=38,
            corner_radius=14,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            border_color=THEME["border"],
            border_width=1,
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=self.capture_target_key,
        )
        capture_target_button.pack(anchor="e")

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 8))

        apply_button = GradientButton(
            actions,
            text="Apply Keyboard Mapping",
            command=self.apply_keyboard_mapping,
            colors=(THEME["blue"], THEME["cyan"]),
            hover_colors=(THEME["blue_hover"], THEME["cyan"]),
            width=300,
            height=48,
        )
        apply_button.pack(side="left")

        release_button = ctk.CTkButton(
            actions,
            text="Release Held Key",
            height=46,
            corner_radius=16,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            border_color=THEME["border"],
            border_width=1,
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            command=self.force_release,
        )
        release_button.pack(side="left", padx=(12, 0))

        footer = ctk.CTkLabel(
            tab,
            text="The keyboard toggle keeps working globally while the app is open.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["faint"],
        )
        footer.pack(anchor="w", padx=24, pady=(6, 0))

        update_section = self.build_section_frame(tab)
        update_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            update_section,
            text="Automatic updates",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            update_section,
            text="This build is locked to the official InputLab update feed and checks automatically after launch.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=620,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            update_section,
            text=DEFAULT_UPDATE_MANIFEST_URL,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#9fb2cf",
            wraplength=620,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 16))

        self.key_status_badge = status_card.badge
        self.update_key_status()

    def build_macro_tab(self, tab) -> None:
        self.add_tab_heading(
            tab,
            "Controller Macro",
            "Build shareable Xbox-controller profiles with separate hotkeys, loops, and live step feedback.",
        )

        status_card = self.build_status_card(
            tab,
            self.macro_status_var,
            self.macro_detail_var,
        )
        status_card.pack(fill="x", padx=20, pady=(0, 16))

        progress_frame = self.build_section_frame(tab)
        progress_frame.pack(fill="x", padx=20, pady=(0, 16))

        progress_header_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_header_row.pack(fill="x", padx=18, pady=(16, 10))

        progress_header = ctk.CTkLabel(
            progress_header_row,
            text="Live progress",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        )
        progress_header.pack(side="left")

        self.live_progress_accent = ctk.CTkFrame(
            progress_header_row,
            height=5,
            fg_color=THEME["blue"],
            corner_radius=3,
            width=120,
        )
        self.live_progress_accent.pack(side="right", pady=(5, 0))
        self.live_progress_accent.pack_propagate(False)

        progress_metrics_grid = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_metrics_grid.pack(fill="x", padx=18, pady=(0, 16))
        progress_metrics_grid.grid_columnconfigure((0, 1), weight=1, uniform="progress")

        profile_section = self.build_section_frame(tab)
        profile_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            profile_section,
            text="Profiles",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 10))

        self.profile_tabs = ctk.CTkSegmentedButton(
            profile_section,
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            selected_color=THEME["green_deep"],
            selected_hover_color=THEME["green"],
            unselected_color=THEME["panel_high"],
            unselected_hover_color=THEME["field_hover"],
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.on_profile_tab_selected,
        )
        self.profile_tabs.pack(fill="x", padx=18, pady=(0, 10))

        profile_actions = ctk.CTkFrame(profile_section, fg_color="transparent")
        profile_actions.pack(fill="x", padx=18, pady=(0, 10))

        self.add_profile_button = ctk.CTkButton(
            profile_actions,
            text="Add Profile",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.add_macro_profile,
        )
        self.add_profile_button.pack(side="left")

        self.duplicate_profile_button = ctk.CTkButton(
            profile_actions,
            text="Duplicate Profile",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.duplicate_macro_profile,
        )
        self.duplicate_profile_button.pack(side="left", padx=(10, 0))

        self.reset_profile_button = ctk.CTkButton(
            profile_actions,
            text="Reset Profile",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.reset_macro_profile,
        )
        self.reset_profile_button.pack(side="left", padx=(10, 0))

        self.delete_profile_button = ctk.CTkButton(
            profile_actions,
            text="Delete Profile",
            height=38,
            corner_radius=12,
            fg_color="#25151a",
            hover_color="#3b1b23",
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.delete_macro_profile,
        )
        self.delete_profile_button.pack(side="left", padx=(10, 0))

        profile_share_actions = ctk.CTkFrame(profile_section, fg_color="transparent")
        profile_share_actions.pack(fill="x", padx=18, pady=(0, 16))

        self.import_profiles_button = ctk.CTkButton(
            profile_share_actions,
            text="Import Profiles",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.import_macro_profiles,
        )
        self.import_profiles_button.pack(side="left")

        self.export_profiles_button = ctk.CTkButton(
            profile_share_actions,
            text="Export Profiles",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.export_macro_profiles,
        )
        self.export_profiles_button.pack(side="left", padx=(10, 0))

        macro_body = ctk.CTkFrame(tab, fg_color=THEME["panel_low"])
        macro_body.pack(fill="x", padx=20, pady=(0, 16), anchor="w")

        macro_config_column = ctk.CTkFrame(macro_body, fg_color=THEME["panel_low"])
        macro_config_column.pack(fill="both", expand=True, anchor="n")

        setup = self.build_section_frame(macro_config_column)
        setup.pack(fill="x", pady=(0, 16))

        self.profile_name_entry = self.add_labeled_entry(
            setup,
            "Profile name",
            "Example: Farm Route 1",
            self.get_selected_profile()["name"],
            expand_entry=False,
            entry_width=300,
        )

        self.macro_hotkey_entry = self.add_labeled_entry(
            setup,
            "Macro hotkey",
            "Example: f3, ctrl+shift+m",
            self.macro_hotkey,
            expand_entry=False,
            entry_width=300,
        )
        self.macro_interval_entry = self.add_labeled_entry(
            setup,
            "Loop interval",
            "Example: 75",
            str(self.macro_interval_seconds),
            expand_entry=False,
            entry_width=300,
        )

        condition_card = ctk.CTkFrame(setup, fg_color=THEME["panel"])
        condition_card.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            condition_card,
            text="Run only when focused app matches",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", pady=(4, 8))

        self.macro_window_title_entry = self.add_labeled_entry(
            condition_card,
            "Window title",
            "Optional: Forza",
            self.macro_run_condition["window_title"],
            expand_entry=False,
            entry_width=300,
        )

        self.macro_process_name_entry = self.add_labeled_entry(
            condition_card,
            "Process name",
            "Optional: forza.exe",
            self.macro_run_condition["process_name"],
            expand_entry=False,
            entry_width=300,
        )

        capture_actions = ctk.CTkFrame(condition_card, fg_color=THEME["panel"])
        capture_actions.pack(fill="x", pady=(0, 4))

        self.capture_window_button = ctk.CTkButton(
            capture_actions,
            text="Capture In 3s",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.arm_window_capture,
        )
        self.capture_window_button.pack(side="left", padx=(18, 0))

        condition_hint = ctk.CTkLabel(
            condition_card,
            text="Leave both blank to let the profile run anywhere. If you use Capture In 3s, tab into the game before the countdown finishes.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=560,
            justify="left",
        )
        condition_hint.pack(anchor="w", padx=18, pady=(10, 4))

        macro_hint = ctk.CTkLabel(
            setup,
            text="Each step presses one virtual Xbox button, waits, releases it, then waits again before the next step. After the full sequence finishes, the macro waits for the loop interval before starting over.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=560,
            justify="left",
        )
        macro_hint.pack(anchor="w", padx=18, pady=(0, 10))

        steps_frame = self.build_section_frame(macro_config_column)
        steps_frame.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(steps_frame, fg_color=THEME["panel"])
        header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            header,
            text="Step",
            width=56,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["muted"],
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Button",
            width=120,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["muted"],
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="Hold (ms)",
            width=100,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["muted"],
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="Delay after (ms)",
            width=130,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["muted"],
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="",
            width=176,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["muted"],
        ).pack(side="left")

        self.macro_steps_rows_frame = ctk.CTkFrame(steps_frame, fg_color=THEME["panel"])
        self.macro_steps_rows_frame.pack(fill="x")
        self.macro_step_widgets = []
        self.render_macro_steps(self.macro_steps)

        step_actions = ctk.CTkFrame(steps_frame, fg_color=THEME["panel"])
        step_actions.pack(fill="x", padx=18, pady=(8, 16))

        self.add_step_button = ctk.CTkButton(
            step_actions,
            text="Add Step",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.add_macro_step,
        )
        self.add_step_button.pack(side="left")

        self.record_macro_button = ctk.CTkButton(
            step_actions,
            text="Start Recorder",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.toggle_macro_recorder,
        )
        self.record_macro_button.pack(side="left", padx=(10, 0))

        self.clear_steps_button = ctk.CTkButton(
            step_actions,
            text="Clear Steps",
            height=38,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.clear_macro_steps,
        )
        self.clear_steps_button.pack(side="left", padx=(10, 0))

        recorder_hint = ctk.CTkLabel(
            steps_frame,
            text="Recorder keys: A, B, X, Y, Q=LB, E=RB, 1=BACK, 2=START, arrows=DPAD. Start recorder, play the sequence on the keyboard, then stop recorder to replace the steps.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=760,
            justify="left",
        )
        recorder_hint.pack(anchor="w", padx=18, pady=(0, 16))

        notes_section = self.build_section_frame(macro_config_column)
        notes_section.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            notes_section,
            text="Profile notes",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 8))

        self.profile_notes_text = ctk.CTkTextbox(
            notes_section,
            height=92,
            corner_radius=14,
            border_width=1,
            border_color=THEME["border"],
            fg_color=THEME["field"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
        )
        self.profile_notes_text.pack(fill="x", padx=18, pady=(0, 16))

        stats_section = self.build_section_frame(macro_config_column)
        stats_section.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            stats_section,
            text="Run statistics",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 8))

        self.profile_stats_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            stats_section,
            textvariable=self.profile_stats_var,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=THEME["muted"],
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 16))

        for index, variable in enumerate((
            self.macro_current_step_var,
            self.macro_last_action_var,
            self.macro_next_action_var,
            self.macro_loop_var,
        )):
            metric = ctk.CTkLabel(
                progress_metrics_grid,
                textvariable=variable,
                height=40,
                corner_radius=12,
                fg_color=THEME["field"],
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color="#c6d2e5",
                anchor="w",
                justify="left",
                wraplength=360,
            )
            metric.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=5,
                pady=5,
            )

        actions = ctk.CTkFrame(macro_config_column, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 8))

        apply_button = GradientButton(
            actions,
            text="Apply Macro",
            command=self.apply_macro_mapping,
            colors=(THEME["blue"], THEME["cyan"]),
            hover_colors=(THEME["blue_hover"], THEME["cyan"]),
            width=174,
            height=48,
        )
        apply_button.pack(side="left")

        start_button = GradientButton(
            actions,
            text="Start Macro",
            command=self.start_macro,
            colors=(THEME["green_deep"], THEME["green"]),
            hover_colors=("#15803d", "#22c55e"),
            width=174,
            height=48,
        )
        start_button.pack(side="left", padx=(12, 0))

        stop_button = ctk.CTkButton(
            actions,
            text="Stop Macro",
            height=46,
            corner_radius=16,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            border_color=THEME["border"],
            border_width=1,
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            command=self.stop_macro,
        )
        stop_button.pack(side="left", padx=(12, 0))

        driver_note = ctk.CTkLabel(
            macro_config_column,
            text=(
                "This tab uses a virtual Xbox 360 controller. "
                "If it does not start, install the ViGEmBus driver when prompted by vgamepad."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["faint"],
            wraplength=560,
            justify="left",
        )
        driver_note.pack(anchor="w", padx=24, pady=(6, 0))

        self.macro_status_badge = status_card.badge
        self.profile_editor_ready = True
        self.refresh_profile_tabs()
        self.load_selected_profile_into_editor()
        self.update_macro_status()

    def build_settings_tab(self, tab) -> None:
        self.add_tab_heading(
            tab,
            "Settings",
            "Switch the full InputLab colorway, tray behavior, and overlay tools without touching your macro profiles.",
        )

        theme_section = self.build_section_frame(tab)
        theme_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            theme_section,
            text="Theme preset",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            theme_section,
            text="Each preset swaps the entire color system: accents, active states, cards, borders, and live progress surfaces.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 12))

        self.theme_buttons_frame = ctk.CTkFrame(theme_section, fg_color=THEME["panel"])
        self.theme_buttons_frame.pack(fill="x", padx=18, pady=(0, 16))

        self.theme_preset_buttons = {}
        for theme_name in THEME_PRESETS:
            button = ctk.CTkButton(
                self.theme_buttons_frame,
                text=theme_name,
                height=42,
                corner_radius=14,
                fg_color=THEME["green_deep"] if theme_name == self.theme_name else THEME["field"],
                hover_color=THEME["green"] if theme_name == self.theme_name else THEME["field_hover"],
                text_color=THEME["text"] if theme_name == self.theme_name else "#dce7f8",
                font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
                command=lambda value=theme_name: self.change_theme(value),
            )
            button.pack(fill="x", pady=5)
            self.theme_preset_buttons[theme_name] = button

        preview_section = self.build_section_frame(tab)
        preview_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            preview_section,
            text="Included presets",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 10))

        for title, detail in (
            ("Graphite + Electric Lime", "Dark graphite shell with sharp lime action states and a fast tool feel."),
            ("Midnight Navy + Amber", "Deep navy surfaces with amber highlights and a more premium dashboard tone."),
            ("Carbon + Ice Blue", "Cold carbon panels with icy blue accents and cleaner technical contrast."),
            ("Gunmetal + Redline", "Heavy gunmetal cards with redline accents for a more aggressive racing look."),
            ("Obsidian + Emerald", "Black-green control surface with darker emerald emphasis on active modules."),
            ("Slate + Violet", "Slate-gray framework with restrained violet accents for a more modern UI mood."),
        ):
            item = ctk.CTkFrame(preview_section, fg_color=THEME["panel_high"], corner_radius=14)
            item.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(
                item,
                text=title,
                font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
                text_color=THEME["text"],
            ).pack(anchor="w", padx=14, pady=(10, 2))
            ctk.CTkLabel(
                item,
                text=detail,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=THEME["muted"],
                wraplength=760,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(0, 10))

        behavior_section = self.build_section_frame(tab)
        behavior_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            behavior_section,
            text="App behavior",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 10))

        self.overlay_enabled_var = ctk.BooleanVar(value=self.overlay_enabled)
        self.close_to_tray_var = ctk.BooleanVar(value=self.close_to_tray)
        self.minimize_to_tray_var = ctk.BooleanVar(value=self.minimize_to_tray)

        for label_text, variable, command in (
            ("Enable always-on-top overlay", self.overlay_enabled_var, self.on_overlay_toggle_changed),
            ("Close to system tray instead of exiting", self.close_to_tray_var, self.on_tray_setting_changed),
            ("Minimize to system tray", self.minimize_to_tray_var, self.on_tray_setting_changed),
        ):
            toggle = ctk.CTkSwitch(
                behavior_section,
                text=label_text,
                variable=variable,
                onvalue=True,
                offvalue=False,
                progress_color=THEME["blue"],
                button_color=THEME["text"],
                button_hover_color=THEME["text"],
                text_color=THEME["text"],
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=command,
            )
            toggle.pack(anchor="w", padx=18, pady=6)

        hotkey_section = self.build_section_frame(tab)
        hotkey_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            hotkey_section,
            text="Registered profile hotkeys",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=18, pady=(16, 8))

        self.hotkey_summary_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            hotkey_section,
            textvariable=self.hotkey_summary_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["muted"],
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 16))
        self.refresh_hotkey_summary()

    def render_macro_steps(self, steps: list[dict]) -> None:
        if not hasattr(self, "macro_steps_rows_frame"):
            return

        for widget_set in getattr(self, "macro_step_widgets", []):
            widget_set["row"].destroy()
        self.macro_step_widgets = []

        rows = steps if steps else [{"button": "", "hold_ms": 90, "delay_ms": 120}]
        for step in rows:
            self.create_macro_step_row(step)
        self.refresh_macro_step_numbers()

    def create_macro_step_row(self, step: dict) -> None:
        row = ctk.CTkFrame(
            self.macro_steps_rows_frame,
            fg_color=THEME["panel_high"],
            corner_radius=16,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        row.pack(fill="x", padx=18, pady=6)

        number_label = ctk.CTkLabel(
            row,
            text="",
            width=42,
            height=34,
            corner_radius=17,
            fg_color=THEME["field"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color=THEME["text"],
        )
        number_label.pack(side="left", padx=(12, 14), pady=10)

        button_box = ctk.CTkComboBox(
            row,
            values=[""] + BUTTON_OPTIONS,
            width=120,
            height=38,
            corner_radius=12,
            border_color=THEME["border"],
            fg_color=THEME["field"],
            button_color=THEME["field_hover"],
            button_hover_color=THEME["blue"],
            dropdown_fg_color=THEME["field"],
            dropdown_hover_color="#1d293b",
            dropdown_text_color=THEME["text"],
        )
        button_box.pack(side="left", padx=(0, 10))
        button_box.set(str(step.get("button", "")).upper())

        hold_entry = ctk.CTkEntry(
            row,
            width=100,
            height=38,
            corner_radius=12,
            border_color=THEME["border"],
            fg_color=THEME["field"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        hold_entry.pack(side="left", padx=(0, 10))
        hold_entry.insert(0, str(step.get("hold_ms", 90)))

        delay_entry = ctk.CTkEntry(
            row,
            width=130,
            height=38,
            corner_radius=12,
            border_color=THEME["border"],
            fg_color=THEME["field"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        delay_entry.pack(side="left", padx=(0, 10))
        delay_entry.insert(0, str(step.get("delay_ms", 120)))

        widget_set = {
            "row": row,
            "number": number_label,
            "button": button_box,
            "hold_ms": hold_entry,
            "delay_ms": delay_entry,
        }

        move_up_button = ctk.CTkButton(
            row,
            text="Up",
            width=56,
            height=36,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=12, weight="bold"),
            command=lambda target=widget_set: self.move_macro_step(target, -1),
        )
        move_up_button.pack(side="left", padx=(0, 8))
        widget_set["up"] = move_up_button

        move_down_button = ctk.CTkButton(
            row,
            text="Down",
            width=64,
            height=36,
            corner_radius=12,
            fg_color=THEME["field"],
            hover_color=THEME["field_hover"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=12, weight="bold"),
            command=lambda target=widget_set: self.move_macro_step(target, 1),
        )
        move_down_button.pack(side="left", padx=(0, 8))
        widget_set["down"] = move_down_button

        remove_button = ctk.CTkButton(
            row,
            text="Remove",
            width=92,
            height=36,
            corner_radius=12,
            fg_color="#25151a",
            hover_color="#3b1b23",
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=12, weight="bold"),
            command=lambda target=widget_set: self.remove_macro_step(target),
        )
        remove_button.pack(side="left")
        widget_set["remove"] = remove_button

        self.macro_step_widgets.append(widget_set)

    def refresh_macro_step_numbers(self) -> None:
        for index, widget_set in enumerate(self.macro_step_widgets, start=1):
            widget_set["number"].configure(text=f"{index:02}")
            widget_set["remove"].configure(state="normal" if len(self.macro_step_widgets) > 1 else "disabled")
            widget_set["up"].configure(state="normal" if index > 1 else "disabled")
            widget_set["down"].configure(state="normal" if index < len(self.macro_step_widgets) else "disabled")

    def add_macro_step(self) -> None:
        self.create_macro_step_row({"button": "", "hold_ms": 90, "delay_ms": 120})
        self.refresh_macro_step_numbers()
        self.on_body_scroll_frame_configure()
        self.set_macro_status("Step added", "Added a new blank controller macro step.")

    def move_macro_step(self, widget_set: dict, direction: int) -> None:
        if widget_set not in self.macro_step_widgets:
            return
        index = self.macro_step_widgets.index(widget_set)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.macro_step_widgets):
            return
        self.macro_step_widgets[index], self.macro_step_widgets[new_index] = self.macro_step_widgets[new_index], self.macro_step_widgets[index]
        for item in self.macro_step_widgets:
            item["row"].pack_forget()
        for item in self.macro_step_widgets:
            item["row"].pack(fill="x", padx=18, pady=6)
        self.refresh_macro_step_numbers()
        self.set_macro_status("Step reordered", "Moved the selected controller macro step.")

    def remove_macro_step(self, widget_set: dict) -> None:
        if len(self.macro_step_widgets) <= 1:
            self.set_macro_status("Cannot delete", "Keep at least one controller macro step in the profile.")
            return

        if widget_set in self.macro_step_widgets:
            self.macro_step_widgets.remove(widget_set)
        widget_set["row"].destroy()
        self.refresh_macro_step_numbers()
        self.on_body_scroll_frame_configure()
        self.set_macro_status("Step removed", "Removed that controller macro step.")

    def clear_macro_steps(self) -> None:
        self.render_macro_steps([{"button": "", "hold_ms": 90, "delay_ms": 120}])
        self.set_macro_status("Steps cleared", "Reset the step editor to one blank macro row.")

    def toggle_macro_recorder(self) -> None:
        if self.recorder_active:
            self.stop_macro_recorder()
        else:
            self.start_macro_recorder()

    def start_macro_recorder(self) -> None:
        if self.recorder_active:
            return
        if self.recorder_hook is not None:
            keyboard.unhook(self.recorder_hook)
            self.recorder_hook = None

        self.recorder_active = True
        self.recorder_steps = []
        self.recorder_key_down_times = {}
        self.recorder_last_release_at = None
        self.record_macro_button.configure(text="Stop Recorder")
        self.set_macro_status(
            "Recording",
            "Recorder started. Use A, B, X, Y, Q, E, 1, 2, and arrow keys. Stop recorder when the sequence is complete.",
        )

        def on_event(event) -> None:
            key_name = str(event.name).lower()
            button_name = RECORDER_KEY_TO_BUTTON.get(key_name)
            if button_name is None:
                return
            event_time = time.perf_counter()
            if event.event_type == "down":
                self.recorder_key_down_times[key_name] = event_time
                return
            if event.event_type != "up":
                return
            pressed_at = self.recorder_key_down_times.pop(key_name, None)
            if pressed_at is None:
                pressed_at = event_time
            hold_ms = max(1, int((event_time - pressed_at) * 1000))
            delay_ms = 120
            if self.recorder_last_release_at is not None:
                delay_ms = max(0, int((pressed_at - self.recorder_last_release_at) * 1000))
            self.recorder_last_release_at = event_time
            self.recorder_steps.append(
                {
                    "button": button_name,
                    "hold_ms": hold_ms,
                    "delay_ms": delay_ms,
                }
            )
            self.root.after(
                0,
                lambda count=len(self.recorder_steps), name=button_name: self.set_macro_status(
                    "Recording",
                    f"Captured {count} step(s). Latest input: {name}. Stop recorder to load the captured sequence.",
                ),
            )

        self.recorder_hook = keyboard.hook(on_event)

    def stop_macro_recorder(self) -> None:
        if not self.recorder_active:
            return
        self.recorder_active = False
        self.record_macro_button.configure(text="Start Recorder")
        if self.recorder_hook is not None:
            keyboard.unhook(self.recorder_hook)
            self.recorder_hook = None
        self.recorder_key_down_times.clear()

        if not self.recorder_steps:
            self.set_macro_status("Recorder empty", "Recorder stopped without any usable inputs.")
            return

        self.render_macro_steps(self.recorder_steps)
        self.set_macro_status(
            "Recorder saved",
            f"Loaded {len(self.recorder_steps)} recorded step(s) into the selected profile. Click Apply Macro to save them.",
        )

    def build_status_card(self, parent, status_var, detail_var):
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["panel"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )

        badge = ctk.CTkLabel(
            card,
            textvariable=status_var,
            width=126,
            height=34,
            corner_radius=17,
            fg_color=THEME["field"],
            text_color=THEME["text"],
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
        )
        badge.pack(anchor="w", padx=18, pady=(18, 10))

        detail = ctk.CTkLabel(
            card,
            textvariable=detail_var,
            wraplength=620,
            justify="left",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#c6d2e5",
        )
        detail.pack(anchor="w", padx=18, pady=(0, 18))

        card.badge = badge
        return card

    def add_accent_line(self, parent, color: str, height: int, padx: int, pady) -> None:
        line = ctk.CTkFrame(parent, fg_color=color, height=height, corner_radius=height)
        line.pack(fill="x", padx=padx, pady=pady)
        line.pack_propagate(False)

    def add_tab_heading(self, parent, title_text: str, subtitle_text: str) -> None:
        heading = ctk.CTkFrame(parent, fg_color=THEME["panel_low"])
        heading.pack(fill="x", padx=20, pady=(20, 14))

        ctk.CTkLabel(
            heading,
            text=title_text,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=24, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            heading,
            text=subtitle_text,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=THEME["muted"],
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

    def build_section_frame(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=THEME["panel"],
            corner_radius=20,
            border_color=THEME["border_soft"],
            border_width=1,
        )

    def add_labeled_entry(
        self,
        parent,
        label_text: str,
        hint_text: str,
        value: str,
        expand_entry: bool = True,
        entry_width: int | None = None,
    ) -> ctk.CTkEntry:
        row = ctk.CTkFrame(parent, fg_color=THEME["panel"])
        row.pack(fill="x", padx=18, pady=14)

        label = ctk.CTkLabel(
            row,
            text=label_text,
            width=120,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color=THEME["text"],
        )
        label.pack(side="left", padx=(0, 14))

        entry_kwargs = {
            "height": 42,
            "corner_radius": 14,
            "border_color": THEME["border"],
            "fg_color": THEME["field"],
            "text_color": THEME["text"],
            "placeholder_text": hint_text,
            "font": ctk.CTkFont(family="Segoe UI", size=14),
        }
        if entry_width is not None:
            entry_kwargs["width"] = entry_width

        entry = ctk.CTkEntry(row, **entry_kwargs)
        entry.pack(side="left", fill="x" if expand_entry else "none", expand=expand_entry)
        entry.insert(0, value)
        return entry

    def create_startup_splash(self) -> None:
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg=THEME["app_bg"])
        splash.attributes("-topmost", True)

        container = tk.Frame(
            splash,
            bg=THEME["shell"],
            bd=1,
            highlightthickness=1,
            highlightbackground=THEME["border_soft"],
        )
        container.pack(fill="both", expand=True, padx=1, pady=1)

        header_line = tk.Frame(container, bg=THEME["blue"], height=4)
        header_line.pack(fill="x", padx=18, pady=(18, 0))

        if LOGO_PNG_PATH.exists():
            self.splash_logo_image = tk.PhotoImage(file=str(LOGO_PNG_PATH))
            tk.Label(
                container,
                image=self.splash_logo_image,
                text="",
                bg=THEME["shell"],
            ).pack(pady=(22, 12))

        tk.Label(
            container,
            text="InputLab",
            bg=THEME["shell"],
            fg=THEME["text"],
            font=("Segoe UI Semibold", 24, "bold"),
        ).pack()

        tk.Label(
            container,
            textvariable=self.startup_status_var,
            bg=THEME["shell"],
            fg=THEME["muted"],
            font=("Segoe UI", 11),
        ).pack(pady=(10, 8))

        tk.Label(
            container,
            text="Loading modules, profiles, and interface state...",
            bg=THEME["shell"],
            fg=THEME["faint"],
            font=("Segoe UI", 10),
        ).pack(pady=(0, 16))

        progress_track = tk.Frame(container, bg=THEME["field"], height=8)
        progress_track.pack(fill="x", padx=42, pady=(0, 10))

        progress_fill = tk.Frame(progress_track, bg=THEME["blue"], height=8, width=188)
        progress_fill.pack(side="left")

        tk.Label(
            container,
            text="Please wait",
            bg=THEME["shell"],
            fg=THEME["muted"],
            font=("Segoe UI Semibold", 10, "bold"),
        ).pack(pady=(0, 18))

        splash.update_idletasks()
        width = 420
        height = 290
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        splash.geometry(f"{width}x{height}+{x}+{y}")
        splash.deiconify()
        splash.update()
        self.startup_splash = splash

    def update_startup_status(self, message: str) -> None:
        if self.startup_status_var is not None:
            self.startup_status_var.set(message)
        if self.startup_splash is not None and not HIGH_PERFORMANCE_UI:
            self.startup_splash.update_idletasks()

    def apply_window_icon(self) -> None:
        if LOGO_ICO_PATH.exists():
            try:
                self.root.iconbitmap(str(LOGO_ICO_PATH))
                return
            except Exception:
                pass

        if LOGO_PNG_PATH.exists():
            try:
                self.logo_photo = tk.PhotoImage(file=str(LOGO_PNG_PATH))
                self.root.iconphoto(True, self.logo_photo)
            except Exception:
                self.logo_photo = None

    def apply_windows_app_id(self) -> None:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("revb3d.InputLab")
        except Exception:
            pass

    def configure_windows_dpi_awareness(self) -> None:
        try:
            dpi_context_per_monitor_v2 = ctypes.c_void_p(-4)
            if ctypes.windll.user32.SetProcessDpiAwarenessContext(dpi_context_per_monitor_v2):
                return
        except Exception:
            pass

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass

        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    def center_window(self) -> None:
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), self.root.winfo_reqwidth())
        height = max(self.root.winfo_height(), self.root.winfo_reqheight())
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def show_centered_window(self) -> None:
        self.update_startup_status("Finalizing layout...")
        self.center_window()
        self.ensure_window_opaque()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.startup_splash is not None:
            try:
                self.startup_splash.attributes("-topmost", False)
            except Exception:
                pass
            self.startup_splash.destroy()
            self.startup_splash = None
        self.root.after(60, self.ensure_window_opaque)
        self.root.after(220, self.ensure_window_opaque)

    def ensure_window_opaque(self) -> None:
        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            pass

        try:
            self.root.wm_attributes("-alpha", 1.0)
        except Exception:
            pass

        try:
            self.root.attributes("-transparentcolor", "")
        except Exception:
            pass

    def register_key_hold_hotkey(self, hotkey: str) -> None:
        if self.key_hold_hotkey_handle is not None:
            keyboard.remove_hotkey(self.key_hold_hotkey_handle)
            self.key_hold_hotkey_handle = None

        self.key_hold_hotkey_handle = keyboard.add_hotkey(
            hotkey,
            self.toggle_hold,
            suppress=False,
            trigger_on_release=False,
        )

    def register_macro_hotkeys(self) -> None:
        for handle in self.macro_hotkey_handles.values():
            keyboard.remove_hotkey(handle)
        self.macro_hotkey_handles = {}

        for profile in self.macro_profiles:
            hotkey = profile["hotkey"].strip().lower()
            if not hotkey:
                continue
            self.macro_hotkey_handles[profile["id"]] = keyboard.add_hotkey(
                hotkey,
                lambda profile_id=profile["id"]: self.toggle_macro(profile_id),
                suppress=False,
                trigger_on_release=False,
            )

    def capture_target_key(self) -> None:
        if self.capture_target_hook is not None:
            return

        self.set_key_status(
            "Waiting for key",
            "Press the key you want this app to hold down, then click Apply Keyboard Mapping.",
        )

        def on_event(event) -> None:
            if event.event_type != "down":
                return
            reserved_hotkeys = {self.toggle_hotkey} | {
                profile["hotkey"] for profile in self.macro_profiles if profile["hotkey"]
            }
            if event.name in reserved_hotkeys:
                return

            self.root.after(0, self.finish_target_capture, event.name)

        self.capture_target_hook = keyboard.hook(on_event)

    def finish_target_capture(self, key_name: str) -> None:
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, key_name)
        self.set_key_status(
            "Key captured",
            f"Captured {key_name.upper()}. Click Apply Keyboard Mapping to use it as the held key.",
        )

        if self.capture_target_hook is not None:
            keyboard.unhook(self.capture_target_hook)
            self.capture_target_hook = None

    def arm_window_capture(self) -> None:
        if self.window_capture_after_id is not None:
            self.root.after_cancel(self.window_capture_after_id)
            self.window_capture_after_id = None

        self.capture_window_button.configure(state="disabled", text="Capturing...")
        self.set_macro_status(
            "Window capture",
            "Switch to the game or app now. InputLab will capture the focused window in 3 seconds.",
        )
        self.ignore_minimize_to_tray_once = True
        self.root.iconify()
        self.window_capture_after_id = self.root.after(3000, self.capture_foreground_window_condition)

    def capture_foreground_window_condition(self) -> None:
        self.window_capture_after_id = None
        window_title, process_name = self.get_foreground_window_info()
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass

        self.capture_window_button.configure(state="normal", text="Capture In 3s")
        self.ignore_minimize_to_tray_once = False

        if not window_title and not process_name:
            self.set_macro_status(
                "Window capture failed",
                "InputLab could not read the focused app. Try again after opening the game window first.",
            )
            return

        self.macro_window_title_entry.delete(0, "end")
        self.macro_window_title_entry.insert(0, window_title)
        self.macro_process_name_entry.delete(0, "end")
        self.macro_process_name_entry.insert(0, process_name)
        self.sync_config_from_ui()
        self.save_config()
        self.set_macro_status(
            "Window captured",
            f"Saved a run condition for {process_name or 'the selected app'} so this profile only starts when that window is focused.",
        )

    def get_foreground_window_info(self) -> tuple[str, str]:
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "", ""

            title_length = user32.GetWindowTextLengthW(hwnd)
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
            window_title = title_buffer.value.strip()

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = ""
            if pid.value:
                process_handle = kernel32.OpenProcess(0x1000, False, pid.value)
                if process_handle:
                    try:
                        size = wintypes.DWORD(1024)
                        path_buffer = ctypes.create_unicode_buffer(size.value)
                        query_image_name = kernel32.QueryFullProcessImageNameW
                        query_image_name.argtypes = [
                            wintypes.HANDLE,
                            wintypes.DWORD,
                            wintypes.LPWSTR,
                            ctypes.POINTER(wintypes.DWORD),
                        ]
                        query_image_name.restype = wintypes.BOOL
                        if query_image_name(process_handle, 0, path_buffer, ctypes.byref(size)):
                            process_name = Path(path_buffer.value).name.lower()
                    finally:
                        kernel32.CloseHandle(process_handle)

            return window_title, process_name
        except Exception:
            return "", ""

    def check_profile_run_condition(self, profile: dict) -> tuple[bool, str]:
        run_condition = profile.get("run_condition", {})
        expected_title = str(run_condition.get("window_title", "")).strip().lower()
        expected_process = str(run_condition.get("process_name", "")).strip().lower()
        if not expected_title and not expected_process:
            return True, ""

        active_title, active_process = self.get_foreground_window_info()
        active_title_lower = active_title.lower()
        active_process_lower = active_process.lower()

        if expected_title and expected_title not in active_title_lower:
            return (
                False,
                f"{profile['name']} only runs when a window title containing \"{run_condition['window_title']}\" is focused. Current window: {active_title or 'Unknown'}.",
            )

        if expected_process and expected_process not in active_process_lower:
            return (
                False,
                f"{profile['name']} only runs when a process containing \"{run_condition['process_name']}\" is focused. Current process: {active_process or 'Unknown'}.",
            )

        return True, ""

    def apply_keyboard_mapping(self) -> None:
        new_hotkey = self.hotkey_entry.get().strip().lower()
        new_target = self.key_entry.get().strip().lower()

        if not new_hotkey or not new_target:
            self.set_key_status(
                "Missing input",
                "Both keyboard fields are required before the mapping can be applied.",
            )
            return

        try:
            keyboard.parse_hotkey(new_hotkey)
        except ValueError:
            self.set_key_status(
                "Invalid hotkey",
                "That hotkey format could not be registered. Try something like f2 or ctrl+shift+h.",
            )
            return

        try:
            keyboard.key_to_scan_codes(new_target)
        except ValueError:
            self.set_key_status(
                "Invalid key",
                "That target key is not recognized. Try something like m, space, left, or enter.",
            )
            return

        self.force_release()
        self.toggle_hotkey = new_hotkey
        self.target_key = new_target
        self.register_key_hold_hotkey(self.toggle_hotkey)
        self.save_config()

        self.set_key_status(
            "Mapping saved",
            f"Press {self.toggle_hotkey.upper()} to toggle holding {self.target_key.upper()}.",
        )

    def refresh_profile_tabs(self) -> None:
        if not hasattr(self, "profile_tabs"):
            return

        values = [profile["name"] for profile in self.macro_profiles]
        if not values:
            values = ["Main Macro"]
        self.profile_tabs.configure(values=values)
        self.profile_tabs.set(self.get_selected_profile()["name"])
        self.delete_profile_button.configure(state="normal" if len(self.macro_profiles) > 1 else "disabled")
        self.refresh_hotkey_summary()

    def load_selected_profile_into_editor(self) -> None:
        if not self.profile_editor_ready:
            return

        profile = self.get_selected_profile()
        self.profile_name_entry.delete(0, "end")
        self.profile_name_entry.insert(0, profile["name"])
        self.macro_hotkey_entry.delete(0, "end")
        self.macro_hotkey_entry.insert(0, profile["hotkey"])
        self.macro_window_title_entry.delete(0, "end")
        self.macro_window_title_entry.insert(0, profile["run_condition"]["window_title"])
        self.macro_process_name_entry.delete(0, "end")
        self.macro_process_name_entry.insert(0, profile["run_condition"]["process_name"])
        self.macro_interval_entry.delete(0, "end")
        self.macro_interval_entry.insert(0, f"{profile['interval_seconds']:g}")
        self.profile_notes_text.delete("1.0", "end")
        self.profile_notes_text.insert("1.0", profile.get("notes", ""))

        self.render_macro_steps(profile["steps"])

        self.sync_active_profile_fields()
        self.refresh_profile_stats_view(profile)
        self.macro_detail_var.set(
            f"Press {profile['hotkey'].upper()} to start or stop the {profile['name']} controller macro."
        )
        self.update_activity_indicators()

    def refresh_profile_stats_view(self, profile: dict | None = None) -> None:
        target_profile = profile or self.get_selected_profile()
        stats = target_profile.get("stats", default_profile_stats())
        session_stats = self.session_profile_stats.setdefault(
            target_profile["id"],
            {"session_loops": 0, "session_runtime_seconds": 0.0},
        )
        last_run_at = stats.get("last_run_at", "") or "Never"
        total_runtime = float(stats.get("total_runtime_seconds", 0.0) or 0.0)
        session_runtime = float(session_stats.get("session_runtime_seconds", 0.0) or 0.0)
        summary = (
            f"Session loops: {int(session_stats.get('session_loops', 0) or 0)}\n"
            f"Session runtime: {self.format_duration(session_runtime)}\n"
            f"Total loops: {int(stats.get('total_loops', 0) or 0)}\n"
            f"Total runtime: {self.format_duration(total_runtime)}\n"
            f"Last run: {last_run_at}\n"
            f"Last run length: {self.format_duration(float(stats.get('last_run_duration_seconds', 0.0) or 0.0))}"
        )
        self.profile_stats_var.set(summary)

    def change_theme(self, theme_name: str) -> None:
        if theme_name == self.theme_name:
            return

        self.sync_config_from_ui()
        self.apply_theme(theme_name)
        self.save_config()
        self.build_ui()
        self.show_view("settings")
        self.set_macro_status("Theme changed", f"Applied {theme_name}.")
        if self.overlay_enabled:
            self.enable_overlay_window(force_rebuild=True)

    def refresh_hotkey_summary(self) -> None:
        if not hasattr(self, "hotkey_summary_var"):
            return
        lines = [f"Keyboard hold: {self.toggle_hotkey.upper()}"]
        for profile in self.macro_profiles:
            lines.append(f"{profile['name']}: {profile['hotkey'].upper() if profile['hotkey'] else 'Unassigned'}")
        self.hotkey_summary_var.set("\n".join(lines))

    def on_overlay_toggle_changed(self) -> None:
        self.overlay_enabled = bool(self.overlay_enabled_var.get())
        self.save_config()
        if self.overlay_enabled:
            self.enable_overlay_window(force_rebuild=True)
        else:
            self.disable_overlay_window()

    def on_tray_setting_changed(self) -> None:
        self.close_to_tray = bool(self.close_to_tray_var.get())
        self.minimize_to_tray = bool(self.minimize_to_tray_var.get())
        self.save_config()

    def enable_overlay_window(self, force_rebuild: bool = False) -> None:
        if force_rebuild:
            self.disable_overlay_window()
        if self.overlay_window is not None:
            self.refresh_overlay_contents()
            return

        overlay = ctk.CTkToplevel(self.root)
        overlay.title("InputLab Overlay")
        overlay.geometry("320x170")
        overlay.resizable(False, False)
        overlay.attributes("-topmost", True)
        overlay.configure(fg_color=THEME["shell"])
        if self.logo_photo is not None:
            try:
                overlay.iconphoto(True, self.logo_photo)
            except Exception:
                pass

        shell = ctk.CTkFrame(
            overlay,
            fg_color=THEME["panel"],
            corner_radius=18,
            border_color=THEME["border_soft"],
            border_width=1,
        )
        shell.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            shell,
            text="InputLab Overlay",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color=THEME["text"],
        ).pack(anchor="w", padx=14, pady=(12, 6))

        for key in ("profile", "step", "next", "loops"):
            label = ctk.CTkLabel(
                shell,
                text="",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=THEME["muted"],
                anchor="w",
                justify="left",
            )
            label.pack(anchor="w", padx=14, pady=3)
            self.overlay_labels[key] = label

        overlay.protocol("WM_DELETE_WINDOW", self.on_overlay_closed)
        self.overlay_window = overlay
        self.refresh_overlay_contents()

    def on_overlay_closed(self) -> None:
        self.disable_overlay_window()
        if hasattr(self, "overlay_enabled_var"):
            self.overlay_enabled_var.set(False)
        self.overlay_enabled = False
        self.save_config()

    def disable_overlay_window(self) -> None:
        if self.overlay_update_after_id is not None:
            self.root.after_cancel(self.overlay_update_after_id)
            self.overlay_update_after_id = None
        if self.overlay_window is not None:
            try:
                self.overlay_window.destroy()
            except Exception:
                pass
            self.overlay_window = None
        self.overlay_labels = {}

    def refresh_overlay_contents(self) -> None:
        if self.overlay_window is None:
            return
        selected_profile = self.get_selected_profile()
        active_profile_name = self.get_profile_by_id(self.active_macro_profile_id)["name"] if self.active_macro_profile_id else selected_profile["name"]
        values = {
            "profile": f"Profile: {active_profile_name}",
            "step": self.macro_current_step_var.get(),
            "next": self.macro_next_action_var.get(),
            "loops": self.macro_loop_var.get(),
        }
        for key, label in self.overlay_labels.items():
            label.configure(text=values.get(key, ""))
        if self.overlay_update_after_id is not None:
            self.root.after_cancel(self.overlay_update_after_id)
        self.overlay_update_after_id = self.root.after(200, self.refresh_overlay_contents)

    def build_tray_image(self):
        try:
            if LOGO_PNG_PATH.exists():
                return Image.open(LOGO_PNG_PATH)
        except Exception:
            pass
        return Image.new("RGBA", (64, 64), THEME["panel"])

    def ensure_tray_icon(self) -> bool:
        if pystray is None or TrayMenuItem is None:
            self.set_macro_status("Tray unavailable", "Install pystray to use system tray mode in this build.")
            return False
        if self.tray_icon is not None:
            return True

        menu = pystray.Menu(
            TrayMenuItem("Show InputLab", lambda icon=None, item=None: self.root.after(0, self.restore_from_tray)),
            TrayMenuItem("Exit InputLab", lambda icon=None, item=None: self.root.after(0, self.exit_from_tray)),
        )
        self.tray_icon = pystray.Icon("InputLab", self.build_tray_image(), "InputLab", menu)

        def run_icon():
            try:
                self.tray_icon.run()
            except Exception:
                pass

        self.tray_thread = threading.Thread(target=run_icon, daemon=True)
        self.tray_thread.start()
        return True

    def hide_to_tray(self) -> bool:
        if not self.ensure_tray_icon():
            return False
        self.root.withdraw()
        self.set_macro_status("Tray mode", "InputLab is hidden in the system tray and still running.")
        return True

    def restore_from_tray(self) -> None:
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def exit_from_tray(self) -> None:
        self.exiting_to_system = True
        self.on_close()

    def stop_tray_icon(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.tray_thread = None

    def on_window_unmap(self, _event=None) -> None:
        if self.exiting_to_system:
            return
        if self.ignore_minimize_to_tray_once:
            return
        try:
            if self.root.state() == "iconic" and self.minimize_to_tray:
                self.root.after(120, self.hide_to_tray)
        except Exception:
            pass

    @staticmethod
    def format_duration(total_seconds: float) -> str:
        seconds = max(0, int(total_seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def on_profile_tab_selected(self, selected_name: str) -> None:
        if not self.profile_editor_ready:
            return

        self.sync_config_from_ui()
        for profile in self.macro_profiles:
            if profile["name"] == selected_name:
                self.selected_macro_profile_id = profile["id"]
                break
        self.load_selected_profile_into_editor()
        self.save_config()

    def add_macro_profile(self) -> None:
        self.sync_config_from_ui()
        new_profile = self.build_new_profile()
        self.macro_profiles.append(new_profile)
        self.session_profile_stats[new_profile["id"]] = {"session_loops": 0, "session_runtime_seconds": 0.0}
        self.selected_macro_profile_id = new_profile["id"]
        self.refresh_profile_tabs()
        self.load_selected_profile_into_editor()
        self.save_config()
        self.register_macro_hotkeys()
        self.set_macro_status("Profile added", f"{new_profile['name']} is ready. Give it a hotkey and steps, then apply it.")

    def duplicate_macro_profile(self) -> None:
        self.sync_config_from_ui()
        current_profile = self.get_selected_profile()
        duplicate_name = self.unique_profile_name(f"{current_profile['name']} Copy")
        duplicate_profile = build_macro_profile(
            uuid.uuid4().hex,
            duplicate_name,
            hotkey=self.next_available_macro_hotkey(),
            interval_seconds=current_profile["interval_seconds"],
            steps=current_profile["steps"],
            run_condition=current_profile["run_condition"],
            notes=current_profile.get("notes", ""),
        )

        self.macro_profiles.append(duplicate_profile)
        self.session_profile_stats[duplicate_profile["id"]] = {"session_loops": 0, "session_runtime_seconds": 0.0}
        self.selected_macro_profile_id = duplicate_profile["id"]
        self.refresh_profile_tabs()
        self.load_selected_profile_into_editor()
        self.save_config()
        self.register_macro_hotkeys()
        self.set_macro_status(
            "Profile duplicated",
            f"Duplicated {current_profile['name']} as {duplicate_profile['name']}.",
        )

    def reset_macro_profile(self) -> None:
        current_profile = self.get_selected_profile()
        if self.active_macro_profile_id == current_profile["id"]:
            self.stop_macro()

        current_profile["hotkey"] = self.next_available_macro_hotkey(current_profile["id"]) or current_profile["hotkey"]
        current_profile["interval_seconds"] = 78
        current_profile["steps"] = default_macro_steps()
        current_profile["run_condition"] = {"window_title": "", "process_name": ""}
        current_profile["notes"] = ""
        current_profile["stats"] = default_profile_stats()
        self.session_profile_stats[current_profile["id"]] = {"session_loops": 0, "session_runtime_seconds": 0.0}
        self.load_selected_profile_into_editor()
        self.save_config()
        self.register_macro_hotkeys()
        self.reset_macro_progress()
        self.set_macro_status(
            "Profile reset",
            f"{current_profile['name']} was reset to the built-in controller defaults.",
        )

    def unique_profile_name(self, base_name: str) -> str:
        existing_names = {profile["name"].lower() for profile in self.macro_profiles}
        if base_name.lower() not in existing_names:
            return base_name

        counter = 2
        while f"{base_name} {counter}".lower() in existing_names:
            counter += 1
        return f"{base_name} {counter}"

    def delete_macro_profile(self) -> None:
        if len(self.macro_profiles) <= 1:
            self.set_macro_status("Cannot delete", "InputLab keeps at least one controller macro profile available.")
            return

        current_profile = self.get_selected_profile()
        if self.active_macro_profile_id == current_profile["id"]:
            self.stop_macro()

        self.macro_profiles = [profile for profile in self.macro_profiles if profile["id"] != current_profile["id"]]
        self.session_profile_stats.pop(current_profile["id"], None)
        self.selected_macro_profile_id = self.macro_profiles[0]["id"]
        self.refresh_profile_tabs()
        self.load_selected_profile_into_editor()
        self.save_config()
        self.register_macro_hotkeys()
        self.set_macro_status("Profile deleted", f"Removed {current_profile['name']}.")

    def export_macro_profiles(self) -> None:
        self.sync_config_from_ui()
        export_path = filedialog.asksaveasfilename(
            title="Export InputLab profiles",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="InputLabProfiles.json",
        )
        if not export_path:
            return

        payload = {
            "selected_macro_profile_id": self.selected_macro_profile_id,
            "macro_profiles": self.macro_profiles,
        }
        Path(export_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.set_macro_status("Profiles exported", f"Saved your controller profiles to {Path(export_path).name}.")

    def import_macro_profiles(self) -> None:
        import_path = filedialog.askopenfilename(
            title="Import InputLab profiles",
            filetypes=[("JSON files", "*.json")],
        )
        if not import_path:
            return

        try:
            payload = json.loads(Path(import_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.set_macro_status("Import failed", f"Could not read that profile file: {exc}")
            return

        if isinstance(payload, list):
            raw_profiles = payload
        elif isinstance(payload.get("macro_profiles"), list):
            raw_profiles = payload.get("macro_profiles", [])
        else:
            raw_profiles = [payload]

        imported_profiles = []
        for index, raw_profile in enumerate(raw_profiles, start=1):
            normalized = self.normalize_macro_profile(raw_profile, index)
            if normalized is not None:
                normalized["id"] = uuid.uuid4().hex
                normalized["name"] = self.unique_profile_name(normalized["name"])

                imported_hotkey = normalized["hotkey"].strip().lower()
                try:
                    keyboard.parse_hotkey(imported_hotkey)
                except ValueError:
                    imported_hotkey = ""

                used_hotkeys = {
                    profile["hotkey"]
                    for profile in self.macro_profiles
                    if profile["hotkey"]
                }
                if not imported_hotkey or imported_hotkey in used_hotkeys:
                    imported_hotkey = self.next_available_macro_hotkey()
                normalized["hotkey"] = imported_hotkey

                self.macro_profiles.append(normalized)
                self.session_profile_stats[normalized["id"]] = {"session_loops": 0, "session_runtime_seconds": 0.0}
                imported_profiles.append(normalized)

        if not imported_profiles:
            self.set_macro_status("Import failed", "That file does not contain any usable controller macro profiles.")
            return

        self.selected_macro_profile_id = imported_profiles[0]["id"]
        self.refresh_profile_tabs()
        self.load_selected_profile_into_editor()
        self.save_config()
        self.register_macro_hotkeys()
        self.set_macro_status(
            "Profiles imported",
            f"Added {len(imported_profiles)} controller macro profile(s) without removing your existing profiles.",
        )

    def collect_macro_steps(self, include_blank_steps: bool = False):
        parsed_steps = []
        for widget_set in self.macro_step_widgets:
            button_name = widget_set["button"].get().strip().upper()
            hold_ms = self.safe_int(widget_set["hold_ms"].get(), 90)
            delay_ms = self.safe_int(widget_set["delay_ms"].get(), 120)

            if not button_name and not include_blank_steps:
                continue

            if button_name and button_name not in BUTTON_ENUM_NAMES:
                raise ValueError(f"Unsupported button: {button_name}")

            if hold_ms < 1 or delay_ms < 0:
                raise ValueError("Macro timing values must be positive.")

            parsed_steps.append(
                {
                    "button": button_name,
                    "hold_ms": hold_ms,
                    "delay_ms": delay_ms,
                }
            )
        return parsed_steps

    def apply_macro_mapping(self) -> None:
        profile = self.get_selected_profile()
        profile_name = self.profile_name_entry.get().strip()
        new_hotkey = self.macro_hotkey_entry.get().strip().lower()
        if not profile_name or not new_hotkey:
            self.set_macro_status("Missing input", "Add both a profile name and hotkey before applying the controller macro.")
            return

        try:
            keyboard.parse_hotkey(new_hotkey)
        except ValueError:
            self.set_macro_status(
                "Invalid hotkey",
                "That macro hotkey could not be registered. Try something like f3 or ctrl+shift+m.",
            )
            return

        try:
            parsed_steps = self.collect_macro_steps()
        except ValueError as exc:
            self.set_macro_status("Invalid macro", str(exc))
            return

        interval_seconds = self.safe_float(self.macro_interval_entry.get().strip(), -1)
        if interval_seconds < 0:
            self.set_macro_status(
                "Invalid macro",
                "Loop interval must be 0 or higher. Use 75 for a 75 second wait between loops.",
            )
            return

        if not parsed_steps:
            self.set_macro_status(
                "No steps",
                "Add at least one controller button step before applying the macro.",
            )
            return

        for other_profile in self.macro_profiles:
            if other_profile["id"] != profile["id"] and other_profile["name"].lower() == profile_name.lower():
                self.set_macro_status(
                    "Duplicate hotkey",
                    f"{profile_name} already exists. Give each controller profile a different name.",
                )
                return
            if other_profile["id"] != profile["id"] and other_profile["hotkey"] == new_hotkey:
                self.set_macro_status(
                    "Duplicate hotkey",
                    f"{new_hotkey.upper()} is already used by {other_profile['name']}. Give each macro profile its own hotkey.",
                )
                return

        self.stop_macro()
        profile["name"] = profile_name
        profile["hotkey"] = new_hotkey
        profile["interval_seconds"] = interval_seconds
        profile["steps"] = self.collect_macro_steps(include_blank_steps=True)
        profile["run_condition"] = {
            "window_title": self.macro_window_title_entry.get().strip(),
            "process_name": self.macro_process_name_entry.get().strip().lower(),
        }
        profile["notes"] = self.profile_notes_text.get("1.0", "end").strip()
        self.refresh_profile_tabs()
        self.register_macro_hotkeys()
        self.sync_active_profile_fields()
        self.save_config()
        self.reset_macro_progress()

        self.set_macro_status(
            "Macro saved",
            f"Press {profile['hotkey'].upper()} to start or stop {profile['name']}. It will wait {profile['interval_seconds']:g} seconds between loops.",
        )

    def toggle_hold(self) -> None:
        if self.is_holding:
            keyboard.release(self.target_key)
            self.is_holding = False
            self.root.after(
                0,
                lambda: self.on_keyboard_hold_released(),
            )
            return

        keyboard.press(self.target_key)
        self.is_holding = True
        self.root.after(
            0,
            lambda: self.on_keyboard_hold_started(),
        )

    def force_release(self) -> None:
        if self.is_holding:
            keyboard.release(self.target_key)
            self.is_holding = False
        self.update_activity_indicators()

        if self.key_status_var.get() not in {
            "Mapping saved",
            "Invalid hotkey",
            "Invalid key",
            "Missing input",
            "Waiting for key",
            "Key captured",
        }:
            self.set_key_status(
                "Idle",
                f"Press {self.toggle_hotkey.upper()} to toggle {self.target_key.upper()}.",
            )

    def ensure_gamepad(self) -> bool:
        if vg is None:
            self.set_macro_status(
                "Driver needed",
                "Install the Python package vgamepad and allow its ViGEmBus driver installer to run, then reopen the app.",
            )
            return False

        if self.virtual_gamepad is not None:
            return True

        try:
            self.virtual_gamepad = vg.VX360Gamepad()
            return True
        except Exception as exc:
            self.set_macro_status(
                "Driver needed",
                f"Could not create the virtual Xbox controller: {exc}",
            )
            return False

    def toggle_macro(self, profile_id: str | None = None) -> None:
        target_profile_id = profile_id or self.selected_macro_profile_id
        if self.macro_running.is_set() and self.active_macro_profile_id == target_profile_id:
            self.stop_macro()
        else:
            self.start_macro(target_profile_id)

    def start_macro(self, profile_id: str | None = None) -> None:
        target_profile = self.get_profile_by_id(profile_id or self.selected_macro_profile_id)
        if profile_id:
            self.selected_macro_profile_id = target_profile["id"]
            if self.profile_editor_ready:
                self.refresh_profile_tabs()
                self.load_selected_profile_into_editor()

        try:
            if self.profile_editor_ready and target_profile["id"] == self.selected_macro_profile_id:
                self.sync_config_from_ui()
            active_steps = [step.copy() for step in target_profile["steps"] if step["button"]]
        except ValueError as exc:
            self.set_macro_status("Invalid macro", str(exc))
            return

        if not active_steps:
            self.set_macro_status("No steps", "Add at least one controller button step before starting the macro.")
            return

        condition_ok, condition_message = self.check_profile_run_condition(target_profile)
        if not condition_ok:
            self.set_macro_status("Window mismatch", condition_message)
            return

        if not self.ensure_gamepad():
            return

        if self.macro_running.is_set():
            self.set_macro_status(
                "Running",
                f"{self.get_profile_by_id(self.active_macro_profile_id)['name']} is already running. Starting {target_profile['name']} will switch over.",
            )
            self.stop_macro()

        self.macro_running.set()
        self.active_macro_profile_id = target_profile["id"]
        self.macro_run_started_at = time.perf_counter()
        self.active_macro_loop_count = 0
        self.sync_active_profile_fields()
        self.reset_macro_progress()
        self.update_activity_indicators()
        self.macro_thread = threading.Thread(
            target=self.run_macro_loop,
            args=(target_profile, active_steps),
            daemon=True,
        )
        self.macro_thread.start()
        self.set_macro_status(
            "Running",
            f"{target_profile['name']} is looping now with a {target_profile['interval_seconds']:g} second interval. Press {target_profile['hotkey'].upper()} again to stop it.",
        )

    def stop_macro(self) -> None:
        stopped_profile = self.get_profile_by_id(self.active_macro_profile_id) if self.active_macro_profile_id else None
        if stopped_profile is not None and self.macro_run_started_at > 0:
            run_seconds = max(0.0, time.perf_counter() - self.macro_run_started_at)
            stopped_profile["stats"]["total_loops"] = int(stopped_profile["stats"].get("total_loops", 0) or 0) + self.active_macro_loop_count
            stopped_profile["stats"]["total_runtime_seconds"] = float(stopped_profile["stats"].get("total_runtime_seconds", 0.0) or 0.0) + run_seconds
            stopped_profile["stats"]["last_run_duration_seconds"] = run_seconds
            stopped_profile["stats"]["last_run_at"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            session_stats = self.session_profile_stats.setdefault(
                stopped_profile["id"],
                {"session_loops": 0, "session_runtime_seconds": 0.0},
            )
            session_stats["session_loops"] += self.active_macro_loop_count
            session_stats["session_runtime_seconds"] += run_seconds
            self.refresh_profile_stats_view(stopped_profile)
            self.save_config()

        self.macro_running.clear()

        if self.virtual_gamepad is not None:
            try:
                self.virtual_gamepad.reset()
                self.virtual_gamepad.update()
            except Exception:
                pass

        if self.macro_thread is not None and self.macro_thread.is_alive():
            self.macro_thread.join(timeout=0.3)
        self.macro_thread = None
        self.active_macro_profile_id = ""
        self.macro_run_started_at = 0.0
        self.active_macro_loop_count = 0
        self.reset_macro_progress()
        self.update_activity_indicators()

        if self.macro_status_var.get() not in {
            "Macro saved",
            "Invalid hotkey",
            "Invalid macro",
            "Missing input",
            "No steps",
            "Driver needed",
        }:
            self.set_macro_status(
                "Ready",
                f"Press {self.get_selected_profile()['hotkey'].upper()} to start or stop {self.get_selected_profile()['name']}.",
            )

    def run_macro_loop(self, profile: dict, steps) -> None:
        loop_count = 0
        while self.macro_running.is_set():
            loop_count += 1
            self.active_macro_loop_count = loop_count
            self.root.after(0, lambda lc=loop_count: self.macro_loop_var.set(f"Loop count: {lc}"))
            for index, step in enumerate(steps, start=1):
                if not self.macro_running.is_set():
                    break
                self.press_virtual_button(index, len(steps), step["button"], step["hold_ms"], step["delay_ms"])
            if self.macro_running.is_set() and profile["interval_seconds"] > 0:
                self.root.after(
                    0,
                    lambda lc=loop_count: self.macro_last_action_var.set(
                        f"Last action: Finished loop {lc}"
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.macro_current_step_var.set("Current step: Waiting for next loop"),
                )
                self.sleep_with_cancel(profile["interval_seconds"])

        self.root.after(
            0,
            self.on_macro_loop_complete,
        )

    def press_virtual_button(
        self,
        step_index: int,
        total_steps: int,
        button_name: str,
        hold_ms: int,
        delay_ms: int,
    ) -> None:
        if self.virtual_gamepad is None:
            return

        enum_name = BUTTON_ENUM_NAMES[button_name]
        button_enum = getattr(vg.XUSB_BUTTON, enum_name)

        self.root.after(
            0,
            lambda: self.macro_current_step_var.set(
                f"Current step: {step_index}/{total_steps} - {button_name}"
            ),
        )
        self.root.after(
            0,
            lambda: self.macro_last_action_var.set(
                f"Last action: Pressed {button_name} for {hold_ms} ms"
            ),
        )
        self.root.after(
            0,
            lambda: self.macro_next_action_var.set(f"Next action in: {hold_ms} ms"),
        )

        self.virtual_gamepad.press_button(button=button_enum)
        self.virtual_gamepad.update()
        self.sleep_with_cancel(hold_ms / 1000, "release", button_name)

        self.virtual_gamepad.release_button(button=button_enum)
        self.virtual_gamepad.update()
        self.root.after(
            0,
            lambda: self.macro_last_action_var.set(
                f"Last action: Released {button_name}"
            ),
        )
        if delay_ms > 0:
            self.root.after(
                0,
                lambda: self.macro_next_action_var.set(f"Next action in: {delay_ms} ms"),
            )
        self.sleep_with_cancel(delay_ms / 1000, "next step", button_name)

    def sleep_with_cancel(self, seconds: float, phase: str | None = None, button_name: str | None = None) -> None:
        end_time = time.perf_counter() + seconds
        while self.macro_running.is_set() and time.perf_counter() < end_time:
            remaining_ms = max(0, int((end_time - time.perf_counter()) * 1000))
            if phase == "release" and button_name:
                self.root.after(
                    0,
                    lambda ms=remaining_ms, name=button_name: self.macro_next_action_var.set(
                        f"Next action in: {ms} ms until {name} releases"
                    ),
                )
            elif phase == "next step":
                self.root.after(
                    0,
                    lambda ms=remaining_ms: self.macro_next_action_var.set(
                        f"Next action in: {ms} ms"
                    ),
                )
            elif phase is None and seconds > 0:
                self.root.after(
                    0,
                    lambda ms=remaining_ms: self.macro_next_action_var.set(
                        f"Next action in: {ms} ms"
                    ),
                )
            time.sleep(0.01)

    def on_macro_loop_complete(self) -> None:
        profile = self.get_selected_profile()
        self.refresh_profile_stats_view(profile)
        self.reset_macro_progress()
        self.update_activity_indicators()
        self.set_macro_status(
            "Ready",
            f"Press {profile['hotkey'].upper()} to start or stop {profile['name']}.",
        )

    def reset_macro_progress(self) -> None:
        self.macro_current_step_var.set("Current step: None")
        self.macro_last_action_var.set("Last action: None")
        self.macro_next_action_var.set("Next action in: --")
        self.macro_loop_var.set("Loop count: 0")
        self.refresh_overlay_contents()

    def on_keyboard_hold_started(self) -> None:
        self.update_activity_indicators()
        self.set_key_status(
            "Holding",
            f"{self.target_key.upper()} is being held down. Press {self.toggle_hotkey.upper()} again to release it.",
        )

    def on_keyboard_hold_released(self) -> None:
        self.update_activity_indicators()
        self.set_key_status(
            "Released",
            f"{self.target_key.upper()} is no longer held. Press {self.toggle_hotkey.upper()} to hold it again.",
        )

    def update_activity_indicators(self) -> None:
        keyboard_active = self.is_holding
        keyboard_color = THEME["red"] if keyboard_active else THEME["border"]
        macro_is_running = self.macro_running.is_set()
        macro_color = THEME["red"] if macro_is_running else THEME["border"]
        self.update_activity_dot(
            self.keyboard_activity_indicator,
            keyboard_active,
            keyboard_color,
            "last_keyboard_active",
        )
        self.update_activity_dot(
            self.macro_activity_indicator,
            macro_is_running,
            macro_color,
            "last_macro_active",
        )
        if hasattr(self, "live_progress_accent"):
            self.live_progress_accent.configure(fg_color=THEME["green"] if macro_is_running else THEME["blue"])
            self.update_live_progress_animation(macro_is_running)
        self.refresh_overlay_contents()

    def update_activity_dot(self, widget, active: bool, color: str, state_name: str) -> None:
        previous = getattr(self, state_name)
        setattr(self, state_name, active)
        if active and previous is not True and not HIGH_PERFORMANCE_UI:
            self.animate_activity_dot(widget, color)
            return
        widget.configure(fg_color=color)

    def animate_activity_dot(self, widget, color: str) -> None:
        frames = [THEME["border"], "#f97316", color, "#f97316", color]
        for index, frame_color in enumerate(frames):
            self.root.after(index * 45, lambda value=frame_color: widget.configure(fg_color=value))

    def update_live_progress_animation(self, macro_is_running: bool) -> None:
        if HIGH_PERFORMANCE_UI:
            if self.live_progress_pulse_after_id is not None:
                self.root.after_cancel(self.live_progress_pulse_after_id)
                self.live_progress_pulse_after_id = None
            self.live_progress_accent.configure(
                fg_color=THEME["green"] if macro_is_running else THEME["blue"],
                height=5,
            )
            return
        if not macro_is_running:
            if self.live_progress_pulse_after_id is not None:
                self.root.after_cancel(self.live_progress_pulse_after_id)
                self.live_progress_pulse_after_id = None
            self.live_progress_accent.configure(fg_color=THEME["blue"], height=5)
            return

        if self.live_progress_pulse_after_id is None:
            self.animate_live_progress_pulse(0)

    def animate_live_progress_pulse(self, frame: int) -> None:
        if not self.macro_running.is_set():
            self.live_progress_pulse_after_id = None
            self.live_progress_accent.configure(fg_color=THEME["blue"], height=5)
            return

        sequence = [
            (THEME["green_deep"], 5),
            (THEME["green"], 7),
            ("#22c55e", 5),
            (THEME["green"], 6),
        ]
        color, height = sequence[frame % len(sequence)]
        self.live_progress_accent.configure(fg_color=color, height=height)
        self.live_progress_pulse_after_id = self.root.after(
            260,
            lambda: self.animate_live_progress_pulse(frame + 1),
        )

    def pulse_status_badge(self, widget, base_color: str, after_ids: list) -> None:
        if HIGH_PERFORMANCE_UI:
            for after_id in after_ids:
                self.root.after_cancel(after_id)
            after_ids.clear()
            widget.configure(fg_color=base_color)
            return

        for after_id in after_ids:
            self.root.after_cancel(after_id)
        after_ids.clear()

        frames = [THEME["blue_hover"], base_color, THEME["cyan"], base_color]
        for index, color in enumerate(frames):
            after_id = self.root.after(
                index * 55,
                lambda value=color: widget.configure(fg_color=value),
            )
            after_ids.append(after_id)

    def set_key_status(self, status: str, detail: str) -> None:
        self.key_status_var.set(status)
        self.key_detail_var.set(detail)
        self.update_key_status()

    def set_macro_status(self, status: str, detail: str) -> None:
        self.macro_status_var.set(status)
        self.macro_detail_var.set(detail)
        self.update_macro_status()
        self.refresh_overlay_contents()

    def set_update_status(self, title: str, detail: str, has_download: bool = False) -> None:
        self.update_status_var.set(title)
        self.update_detail_var.set(detail)
        can_update = has_download and not self.update_download_in_progress
        button_text = "Downloading..." if self.update_download_in_progress else "Update now"
        self.open_update_button.configure(
            state="normal" if can_update else "disabled",
            text=button_text,
        )

    def check_for_updates(self) -> None:
        if self.update_check_in_progress:
            return

        self.update_manifest_url = DEFAULT_UPDATE_MANIFEST_URL
        if not self.update_manifest_url:
            self.set_update_status(
                f"Version {APP_VERSION}",
                "No update feed is configured for this build.",
            )
            return

        self.update_check_in_progress = True
        self.check_updates_button.configure(state="disabled", text="Checking...")
        self.set_update_status(f"Version {APP_VERSION}", "Checking for updates...")

        threading.Thread(target=self.run_update_check, daemon=True).start()

    def auto_check_for_updates(self) -> None:
        if not self.update_check_in_progress:
            self.check_for_updates()

    def run_update_check(self) -> None:
        try:
            manifest_url = self.build_uncached_url(self.update_manifest_url)
            request = urllib.request.Request(
                manifest_url,
                headers={
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "User-Agent": "InputLab-Updater",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            self.root.after(
                0,
                lambda: self.finish_update_check(
                    f"Version {APP_VERSION}",
                    f"Could not reach the update URL: {exc.reason}",
                    "",
                ),
            )
            return
        except (json.JSONDecodeError, TimeoutError, ValueError) as exc:
            self.root.after(
                0,
                lambda: self.finish_update_check(
                    f"Version {APP_VERSION}",
                    f"Update manifest is invalid: {exc}",
                    "",
                ),
            )
            return

        latest_version, download_url, notes = self.parse_update_payload(payload)

        if not latest_version:
            self.root.after(
                0,
                lambda: self.finish_update_check(
                    f"Version {APP_VERSION}",
                    "The update manifest is missing a version field.",
                    "",
                ),
            )
            return

        if self.compare_versions(latest_version, APP_VERSION) > 0 and download_url:
            detail = f"Update available: {latest_version}"
            if notes:
                detail = f"{detail}. {notes}"
            self.root.after(
                0,
                lambda: self.finish_update_check(
                    f"Update {latest_version}",
                    detail,
                    download_url,
                ),
            )
            return

        if self.compare_versions(latest_version, APP_VERSION) > 0:
            self.root.after(
                0,
                lambda: self.finish_update_check(
                    f"Update {latest_version}",
                    "A newer version exists, but the manifest does not include a download link.",
                    "",
                ),
            )
            return

        self.root.after(
            0,
            lambda: self.finish_update_check(
                f"Version {APP_VERSION}",
                "You already have the latest version.",
                "",
            ),
        )

    def finish_update_check(self, title: str, detail: str, download_url: str) -> None:
        self.latest_download_url = download_url
        self.update_check_in_progress = False
        self.check_updates_button.configure(state="normal", text="Check for updates")
        self.set_update_status(title, detail, has_download=bool(download_url))

    @staticmethod
    def parse_update_payload(payload: dict) -> tuple[str, str, str]:
        latest_version = str(payload.get("version", "")).strip()
        download_url = str(payload.get("download_url", "")).strip()
        notes = str(payload.get("notes", "")).strip()

        if latest_version:
            return latest_version, download_url, notes

        latest_version = str(payload.get("tag_name", "")).strip().lstrip("vV")
        notes = str(payload.get("body", "")).strip()
        for asset in payload.get("assets", []):
            if not isinstance(asset, dict):
                continue
            asset_name = str(asset.get("name", "")).lower()
            if asset_name == "inputlabsetup.exe":
                download_url = str(asset.get("browser_download_url", "")).strip()
                break

        return latest_version, download_url, notes

    def download_and_install_update(self) -> None:
        if self.update_download_in_progress or not self.latest_download_url:
            return

        self.update_download_in_progress = True
        self.open_update_button.configure(state="disabled", text="Downloading...")
        self.check_updates_button.configure(state="disabled")
        self.update_detail_var.set("Downloading the latest installer...")
        threading.Thread(target=self.run_update_download, daemon=True).start()

    def run_update_download(self) -> None:
        try:
            installer_path = self.download_update_installer(self.latest_download_url)
        except Exception as exc:
            self.root.after(0, lambda: self.finish_update_download_error(str(exc)))
            return

        self.root.after(0, lambda: self.finish_update_download_success(installer_path))

    def download_update_installer(self, download_url: str) -> Path:
        version_label = self.update_status_var.get().replace(" ", "_").replace(".", "_")
        installer_path = Path(tempfile.gettempdir()) / f"InputLab_{version_label}_Setup.exe"

        with urllib.request.urlopen(download_url, timeout=30) as response:
            total_bytes = int(response.headers.get("Content-Length", "0") or 0)
            bytes_read = 0
            with installer_path.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    handle.write(chunk)
                    bytes_read += len(chunk)
                    self.root.after(
                        0,
                        lambda read=bytes_read, total=total_bytes: self.update_download_progress(read, total),
                    )

        return installer_path

    def update_download_progress(self, bytes_read: int, total_bytes: int) -> None:
        if total_bytes > 0:
            percent = int((bytes_read / total_bytes) * 100)
            self.update_detail_var.set(f"Downloading the latest installer... {percent}%")
        else:
            self.update_detail_var.set("Downloading the latest installer...")

    def finish_update_download_error(self, message: str) -> None:
        self.update_download_in_progress = False
        self.check_updates_button.configure(state="normal", text="Check for updates")
        self.set_update_status(
            self.update_status_var.get(),
            f"Update download failed: {message}",
            has_download=bool(self.latest_download_url),
        )

    def finish_update_download_success(self, installer_path: Path) -> None:
        self.update_download_in_progress = False
        self.installing_update = True
        self.check_updates_button.configure(state="disabled", text="Updating...")
        self.update_status_var.set("Installing update")
        self.update_detail_var.set("Closing InputLab and launching the new installer...")
        self.open_update_button.configure(state="disabled", text="Launching...")
        self.launch_update_installer(installer_path)

    def launch_update_installer(self, installer_path: Path) -> None:
        launcher_path = installer_path.with_suffix(".cmd")
        launcher_path.write_text(
            "\n".join(
                [
                    "@echo off",
                    "ping 127.0.0.1 -n 3 >nul",
                    f'start "" "{installer_path}" /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
                ]
            ),
            encoding="utf-8",
        )
        subprocess.Popen(["cmd", "/c", str(launcher_path)], creationflags=0x08000000)
        self.exiting_to_system = True
        self.on_close()

    @staticmethod
    def compare_versions(left: str, right: str) -> int:
        def normalize(value: str) -> list[int]:
            clean = value.strip().lstrip("vV")
            parts = []
            for piece in clean.split("."):
                digits = "".join(ch for ch in piece if ch.isdigit())
                parts.append(int(digits) if digits else 0)
            return parts

        left_parts = normalize(left)
        right_parts = normalize(right)
        max_len = max(len(left_parts), len(right_parts))
        left_parts.extend([0] * (max_len - len(left_parts)))
        right_parts.extend([0] * (max_len - len(right_parts)))

        if left_parts > right_parts:
            return 1
        if left_parts < right_parts:
            return -1
        return 0

    @staticmethod
    def build_uncached_url(url: str) -> str:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}t={int(time.time())}"

    def update_key_status(self) -> None:
        color_map = {
            "Idle": THEME["field"],
            "Released": THEME["field"],
            "Holding": THEME["green_deep"],
            "Mapping saved": "#1d4ed8",
            "Waiting for key": "#4338ca",
            "Key captured": "#1d4ed8",
            "Invalid hotkey": "#7c2d12",
            "Invalid key": "#7c2d12",
            "Missing input": "#7c2d12",
        }
        color = color_map.get(self.key_status_var.get(), THEME["field"])
        self.key_status_badge.configure(fg_color=color)
        if self.key_status_var.get() != "Idle":
            self.pulse_status_badge(self.key_status_badge, color, self.key_status_pulse_after_ids)

    def update_macro_status(self) -> None:
        color_map = {
            "Ready": THEME["field"],
            "Running": THEME["green_deep"],
            "Macro saved": "#1d4ed8",
            "Profile added": "#1d4ed8",
            "Profile duplicated": "#1d4ed8",
            "Profile reset": "#1d4ed8",
            "Profiles imported": "#1d4ed8",
            "Profiles exported": "#1d4ed8",
            "Step added": "#1d4ed8",
            "Step reordered": "#1d4ed8",
            "Step removed": THEME["field"],
            "Steps cleared": THEME["field"],
            "Theme changed": "#1d4ed8",
            "Window capture": "#4338ca",
            "Window captured": "#1d4ed8",
            "Window capture failed": "#7c2d12",
            "Window mismatch": "#7c2d12",
            "Recording": "#4338ca",
            "Recorder saved": "#1d4ed8",
            "Recorder empty": THEME["field"],
            "Tray mode": "#1d4ed8",
            "Tray unavailable": "#7c2d12",
            "Driver needed": "#7c2d12",
            "Invalid hotkey": "#7c2d12",
            "Invalid macro": "#7c2d12",
            "Missing input": "#7c2d12",
            "No steps": "#7c2d12",
            "Duplicate hotkey": "#7c2d12",
            "Cannot delete": "#7c2d12",
            "Profile deleted": THEME["field"],
            "Import failed": "#7c2d12",
        }
        color = color_map.get(self.macro_status_var.get(), THEME["field"])
        self.macro_status_badge.configure(fg_color=color)
        if self.macro_status_var.get() != "Ready":
            self.pulse_status_badge(self.macro_status_badge, color, self.macro_status_pulse_after_ids)

    def on_close(self) -> None:
        if not self.exiting_to_system and self.close_to_tray:
            if self.hide_to_tray():
                return

        self.sync_config_from_ui()
        self.save_config()
        if self.recorder_active:
            self.stop_macro_recorder()
        self.stop_macro()
        self.force_release()

        if self.window_capture_after_id is not None:
            self.root.after_cancel(self.window_capture_after_id)
            self.window_capture_after_id = None

        self.disable_overlay_window()
        self.stop_tray_icon()

        if self.capture_target_hook is not None:
            keyboard.unhook(self.capture_target_hook)
            self.capture_target_hook = None
        if self.recorder_hook is not None:
            keyboard.unhook(self.recorder_hook)
            self.recorder_hook = None

        if self.key_hold_hotkey_handle is not None:
            keyboard.remove_hotkey(self.key_hold_hotkey_handle)
            self.key_hold_hotkey_handle = None

        for handle in self.macro_hotkey_handles.values():
            keyboard.remove_hotkey(handle)
        self.macro_hotkey_handles = {}

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()

    @staticmethod
    def safe_int(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def safe_float(value, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback


if __name__ == "__main__":
    app = KeyHoldApp()
    app.run()
