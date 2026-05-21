import json
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import customtkinter as ctk
import keyboard
from PIL import Image

try:
    import vgamepad as vg
except ImportError:
    vg = None


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
APP_VERSION = "1.0.5"
DEFAULT_UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/revb3d/InputLab/main/update.json"
LOGO_PNG_PATH = APP_DIR / "InputLabLogo.png"
LOGO_ICO_PATH = APP_DIR / "InputLabLogo.ico"
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
DEFAULT_CONFIG = {
    "toggle_hotkey": "f2",
    "target_key": "m",
    "macro_hotkey": "f3",
    "macro_interval_seconds": 75,
    "macro_steps": [
        {"button": "A", "hold_ms": 90, "delay_ms": 120},
        {"button": "", "hold_ms": 90, "delay_ms": 120},
        {"button": "", "hold_ms": 90, "delay_ms": 120},
        {"button": "", "hold_ms": 90, "delay_ms": 120},
    ],
}


class KeyHoldApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("InputLab")
        self.root.geometry("720x560")
        self.root.minsize(720, 560)
        self.root.configure(fg_color="#0b0f14")
        self.logo_image = None
        self.logo_photo = None
        self.apply_window_icon()

        self.config = self.load_config()
        self.toggle_hotkey = self.config["toggle_hotkey"]
        self.target_key = self.config["target_key"]
        self.macro_hotkey = self.config["macro_hotkey"]
        self.macro_interval_seconds = self.config["macro_interval_seconds"]
        self.update_manifest_url = DEFAULT_UPDATE_MANIFEST_URL
        self.macro_steps = self.config["macro_steps"]

        self.is_holding = False
        self.capture_target_hook = None
        self.key_hold_hotkey_handle = None
        self.macro_hotkey_handle = None

        self.virtual_gamepad = None
        self.macro_thread = None
        self.macro_running = threading.Event()

        self.key_status_var = ctk.StringVar(value="Idle")
        self.key_detail_var = ctk.StringVar(
            value=f"Press {self.toggle_hotkey.upper()} to toggle {self.target_key.upper()}."
        )
        self.macro_status_var = ctk.StringVar(value="Ready")
        self.macro_detail_var = ctk.StringVar(
            value=f"Press {self.macro_hotkey.upper()} to start or stop the controller macro."
        )
        self.macro_current_step_var = ctk.StringVar(value="Current step: None")
        self.macro_last_action_var = ctk.StringVar(value="Last action: None")
        self.macro_next_action_var = ctk.StringVar(value="Next action in: --")
        self.macro_loop_var = ctk.StringVar(value="Loop count: 0")
        self.current_view = "keyboard"
        self.update_status_var = ctk.StringVar(value=f"Version {APP_VERSION}")
        self.update_detail_var = ctk.StringVar(value="Update checks are manual.")
        self.latest_download_url = ""
        self.update_check_in_progress = False

        self.build_ui()
        self.register_key_hold_hotkey(self.toggle_hotkey)
        self.register_macro_hotkey(self.macro_hotkey)
        self.root.after(1200, self.auto_check_for_updates)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self) -> dict:
        config = DEFAULT_CONFIG.copy()
        config["macro_steps"] = [step.copy() for step in DEFAULT_CONFIG["macro_steps"]]

        if not CONFIG_PATH.exists():
            return config

        try:
            raw_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return config

        config["toggle_hotkey"] = str(raw_data.get("toggle_hotkey", config["toggle_hotkey"])).lower()
        config["target_key"] = str(raw_data.get("target_key", config["target_key"])).lower()
        config["macro_hotkey"] = str(raw_data.get("macro_hotkey", config["macro_hotkey"])).lower()
        config["macro_interval_seconds"] = self.safe_float(
            raw_data.get("macro_interval_seconds"),
            config["macro_interval_seconds"],
        )
        loaded_steps = raw_data.get("macro_steps", [])
        normalized_steps = []
        for index in range(4):
            base_step = DEFAULT_CONFIG["macro_steps"][index].copy()
            if index < len(loaded_steps) and isinstance(loaded_steps[index], dict):
                loaded_step = loaded_steps[index]
                base_step["button"] = str(loaded_step.get("button", base_step["button"])).upper()
                base_step["hold_ms"] = self.safe_int(loaded_step.get("hold_ms"), base_step["hold_ms"])
                base_step["delay_ms"] = self.safe_int(loaded_step.get("delay_ms"), base_step["delay_ms"])
            normalized_steps.append(base_step)

        config["macro_steps"] = normalized_steps
        return config

    def save_config(self) -> None:
        self.sync_config_from_ui()
        payload = {
            "toggle_hotkey": self.toggle_hotkey,
            "target_key": self.target_key,
            "macro_hotkey": self.macro_hotkey,
            "macro_interval_seconds": self.macro_interval_seconds,
            "macro_steps": self.macro_steps,
        }
        CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def sync_config_from_ui(self) -> None:
        if hasattr(self, "hotkey_entry"):
            typed_hotkey = self.hotkey_entry.get().strip().lower()
            if typed_hotkey:
                self.toggle_hotkey = typed_hotkey

        if hasattr(self, "key_entry"):
            typed_target = self.key_entry.get().strip().lower()
            if typed_target:
                self.target_key = typed_target

        if hasattr(self, "macro_hotkey_entry"):
            typed_macro_hotkey = self.macro_hotkey_entry.get().strip().lower()
            if typed_macro_hotkey:
                self.macro_hotkey = typed_macro_hotkey

        if hasattr(self, "macro_interval_entry"):
            typed_interval = self.macro_interval_entry.get().strip()
            if typed_interval:
                self.macro_interval_seconds = self.safe_float(
                    typed_interval,
                    self.macro_interval_seconds,
                )

        if hasattr(self, "macro_step_widgets"):
            self.macro_steps = self.collect_macro_steps(include_blank_steps=True)

    def build_ui(self) -> None:
        outer = ctk.CTkFrame(
            self.root,
            fg_color="#10161f",
            corner_radius=22,
            border_color="#202938",
            border_width=1,
        )
        outer.pack(fill="both", expand=True, padx=22, pady=22)

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(22, 14))

        header_top = ctk.CTkFrame(header, fg_color="transparent")
        header_top.pack(fill="x")

        if LOGO_PNG_PATH.exists():
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(LOGO_PNG_PATH),
                dark_image=Image.open(LOGO_PNG_PATH),
                size=(52, 52),
            )
            logo_label = ctk.CTkLabel(header_top, text="", image=self.logo_image)
            logo_label.pack(side="left", padx=(0, 14))

        title_block = ctk.CTkFrame(header_top, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True)

        title = ctk.CTkLabel(
            title_block,
            text="InputLab",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=28, weight="bold"),
            text_color="#f5f7fb",
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_block,
            text="Keep your keyboard hold running while you switch over to a separate Xbox controller macro tab.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#93a0b8",
        )
        subtitle.pack(anchor="w", pady=(6, 0))

        self.body_scroll = ctk.CTkScrollableFrame(
            outer,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#182131",
            scrollbar_button_hover_color="#273347",
        )
        self.body_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        body = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(
            body,
            width=190,
            fg_color="#0d131b",
            corner_radius=18,
            border_color="#1b2433",
            border_width=1,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 16))
        sidebar.pack_propagate(False)

        nav_title = ctk.CTkLabel(
            sidebar,
            text="Sections",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color="#e7edf7",
        )
        nav_title.pack(anchor="w", padx=16, pady=(18, 12))

        self.keyboard_nav_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.keyboard_nav_row.pack(fill="x", padx=14, pady=(0, 10))

        self.keyboard_activity_indicator = ctk.CTkLabel(
            self.keyboard_nav_row,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#253247",
        )
        self.keyboard_activity_indicator.pack(side="left", padx=(2, 10))

        self.keyboard_nav_button = ctk.CTkButton(
            self.keyboard_nav_row,
            text="Keyboard Hold",
            height=44,
            corner_radius=14,
            anchor="w",
            fg_color="#14532d",
            hover_color="#1a6a39",
            text_color="#f8fbff",
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
            fg_color="#253247",
        )
        self.macro_activity_indicator.pack(side="left", padx=(2, 10))

        self.macro_nav_button = ctk.CTkButton(
            self.macro_nav_row,
            text="Controller Macro",
            height=44,
            corner_radius=14,
            anchor="w",
            fg_color="#182131",
            hover_color="#273347",
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=lambda: self.show_view("macro"),
        )
        self.macro_nav_button.pack(side="left", fill="x", expand=True)

        update_card = ctk.CTkFrame(
            sidebar,
            fg_color="#101722",
            corner_radius=16,
            border_color="#1b2433",
            border_width=1,
        )
        update_card.pack(side="bottom", fill="x", padx=14, pady=14)

        ctk.CTkLabel(
            update_card,
            text="Updates",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color="#e7edf7",
        ).pack(anchor="w", padx=14, pady=(14, 6))

        ctk.CTkLabel(
            update_card,
            textvariable=self.update_status_var,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
            wraplength=140,
            justify="left",
        ).pack(anchor="w", padx=14)

        ctk.CTkLabel(
            update_card,
            textvariable=self.update_detail_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#91a0b8",
            wraplength=140,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(6, 12))

        self.check_updates_button = ctk.CTkButton(
            update_card,
            text="Check for updates",
            height=38,
            corner_radius=12,
            fg_color="#182131",
            hover_color="#273347",
            text_color="#f8fbff",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.check_for_updates,
        )
        self.check_updates_button.pack(fill="x", padx=14, pady=(0, 8))

        self.open_update_button = ctk.CTkButton(
            update_card,
            text="Open latest download",
            height=38,
            corner_radius=12,
            fg_color="#182131",
            hover_color="#273347",
            text_color="#f8fbff",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            command=self.open_latest_download,
            state="disabled",
        )
        self.open_update_button.pack(fill="x", padx=14, pady=(0, 14))

        self.content_area = ctk.CTkFrame(
            body,
            fg_color="#0d131b",
            corner_radius=18,
            border_color="#1b2433",
            border_width=1,
        )
        self.content_area.pack(side="left", fill="both", expand=True)

        self.keyboard_view = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.macro_view = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self.build_keyboard_tab(self.keyboard_view)
        self.build_macro_tab(self.macro_view)
        self.show_view("keyboard")
        self.update_activity_indicators()

    def show_view(self, view_name: str) -> None:
        self.current_view = view_name

        self.keyboard_view.pack_forget()
        self.macro_view.pack_forget()

        if view_name == "keyboard":
            self.keyboard_view.pack(fill="both", expand=True)
            self.keyboard_nav_button.configure(
                fg_color="#14532d",
                hover_color="#1a6a39",
                text_color="#f8fbff",
            )
            self.macro_nav_button.configure(
                fg_color="#182131",
                hover_color="#273347",
                text_color="#dce7f8",
            )
        else:
            self.macro_view.pack(fill="both", expand=True)
            self.macro_nav_button.configure(
                fg_color="#14532d",
                hover_color="#1a6a39",
                text_color="#f8fbff",
            )
            self.keyboard_nav_button.configure(
                fg_color="#182131",
                hover_color="#273347",
                text_color="#dce7f8",
            )
        self.update_activity_indicators()

    def build_keyboard_tab(self, tab) -> None:
        status_card = self.build_status_card(
            tab,
            self.key_status_var,
            self.key_detail_var,
        )
        status_card.pack(fill="x", padx=20, pady=(20, 16))

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
            fg_color="#182131",
            hover_color="#273347",
            border_color="#253247",
            border_width=1,
            text_color="#dce7f8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            command=self.capture_target_key,
        )
        capture_target_button.pack(anchor="e")

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 8))

        apply_button = ctk.CTkButton(
            actions,
            text="Apply Keyboard Mapping",
            height=46,
            corner_radius=16,
            fg_color="#3b82f6",
            hover_color="#5b9dff",
            text_color="#f8fbff",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            command=self.apply_keyboard_mapping,
        )
        apply_button.pack(side="left")

        release_button = ctk.CTkButton(
            actions,
            text="Release Held Key",
            height=46,
            corner_radius=16,
            fg_color="#182131",
            hover_color="#273347",
            border_color="#253247",
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
            text_color="#718198",
        )
        footer.pack(anchor="w", padx=24, pady=(6, 0))

        update_section = self.build_section_frame(tab)
        update_section.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            update_section,
            text="Automatic updates",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color="#e7edf7",
        ).pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            update_section,
            text="This build is locked to the official InputLab update feed and checks automatically after launch.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#7f8ca3",
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
        status_card = self.build_status_card(
            tab,
            self.macro_status_var,
            self.macro_detail_var,
        )
        status_card.pack(fill="x", padx=20, pady=(20, 16))

        macro_body = ctk.CTkFrame(tab, fg_color="transparent")
        macro_body.pack(fill="x", padx=20, pady=(0, 16), anchor="w")

        macro_config_column = ctk.CTkFrame(macro_body, fg_color="transparent")
        macro_config_column.pack(side="left", fill="y", padx=(0, 12), anchor="n")

        progress_column = ctk.CTkFrame(macro_body, fg_color="transparent", width=300)
        progress_column.pack(side="left", fill="y", anchor="n")
        progress_column.pack_propagate(False)

        setup = self.build_section_frame(macro_config_column)
        setup.pack(fill="x", pady=(0, 16))

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

        macro_hint = ctk.CTkLabel(
            setup,
            text="Each step presses one virtual Xbox button, waits, releases it, then waits again before the next step. After the full sequence finishes, the macro waits for the loop interval before starting over.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#7f8ca3",
        )
        macro_hint.pack(anchor="w", padx=18, pady=(0, 10))

        steps_frame = self.build_section_frame(macro_config_column)
        steps_frame.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(steps_frame, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            header,
            text="Step",
            width=56,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Button",
            width=120,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="Hold (ms)",
            width=100,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="Delay after (ms)",
            width=130,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13, weight="bold"),
            text_color="#dce7f8",
        ).pack(side="left")

        self.macro_step_widgets = []
        for index, step in enumerate(self.macro_steps, start=1):
            row = ctk.CTkFrame(steps_frame, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=8)

            ctk.CTkLabel(
                row,
                text=str(index),
                width=56,
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color="#9aa8c1",
            ).pack(side="left")

            button_box = ctk.CTkComboBox(
                row,
                values=[""] + BUTTON_OPTIONS,
                width=120,
                height=38,
                corner_radius=12,
                border_color="#253247",
                fg_color="#121926",
                button_color="#182131",
                button_hover_color="#273347",
                dropdown_fg_color="#121926",
                dropdown_hover_color="#1d293b",
                dropdown_text_color="#f8fbff",
            )
            button_box.pack(side="left", padx=(0, 10))
            button_box.set(step["button"])

            hold_entry = ctk.CTkEntry(
                row,
                width=100,
                height=38,
                corner_radius=12,
                border_color="#253247",
                fg_color="#121926",
                text_color="#f8fbff",
                font=ctk.CTkFont(family="Segoe UI", size=13),
            )
            hold_entry.pack(side="left", padx=(0, 10))
            hold_entry.insert(0, str(step["hold_ms"]))

            delay_entry = ctk.CTkEntry(
                row,
                width=130,
                height=38,
                corner_radius=12,
                border_color="#253247",
                fg_color="#121926",
                text_color="#f8fbff",
                font=ctk.CTkFont(family="Segoe UI", size=13),
            )
            delay_entry.pack(side="left")
            delay_entry.insert(0, str(step["delay_ms"]))

            self.macro_step_widgets.append(
                {
                    "button": button_box,
                    "hold_ms": hold_entry,
                    "delay_ms": delay_entry,
                }
            )

        progress_frame = self.build_section_frame(progress_column)
        progress_frame.pack(fill="both", expand=True)

        progress_header = ctk.CTkLabel(
            progress_frame,
            text="Live progress",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            text_color="#e7edf7",
        )
        progress_header.pack(anchor="w", padx=18, pady=(16, 10))

        for variable in (
            self.macro_current_step_var,
            self.macro_last_action_var,
            self.macro_next_action_var,
            self.macro_loop_var,
        ):
            ctk.CTkLabel(
                progress_frame,
                textvariable=variable,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color="#b4c0d3",
                anchor="w",
                justify="left",
                wraplength=220,
            ).pack(fill="x", padx=18, pady=4)

        actions = ctk.CTkFrame(macro_config_column, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 8))

        apply_button = ctk.CTkButton(
            actions,
            text="Apply Macro",
            height=46,
            corner_radius=16,
            fg_color="#3b82f6",
            hover_color="#5b9dff",
            text_color="#f8fbff",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            command=self.apply_macro_mapping,
        )
        apply_button.pack(side="left")

        start_button = ctk.CTkButton(
            actions,
            text="Start Macro",
            height=46,
            corner_radius=16,
            fg_color="#14532d",
            hover_color="#1a6a39",
            text_color="#f8fbff",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15, weight="bold"),
            command=self.start_macro,
        )
        start_button.pack(side="left", padx=(12, 0))

        stop_button = ctk.CTkButton(
            actions,
            text="Stop Macro",
            height=46,
            corner_radius=16,
            fg_color="#182131",
            hover_color="#273347",
            border_color="#253247",
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
            text_color="#718198",
            wraplength=620,
            justify="left",
        )
        driver_note.pack(anchor="w", padx=24, pady=(6, 0))

        self.macro_status_badge = status_card.badge
        self.update_macro_status()

    def build_status_card(self, parent, status_var, detail_var):
        card = ctk.CTkFrame(
            parent,
            fg_color="#0d131b",
            corner_radius=18,
            border_color="#1b2433",
            border_width=1,
        )

        badge = ctk.CTkLabel(
            card,
            textvariable=status_var,
            width=126,
            height=34,
            corner_radius=17,
            fg_color="#1f2937",
            text_color="#dbe3f2",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
        )
        badge.pack(anchor="w", padx=18, pady=(18, 10))

        detail = ctk.CTkLabel(
            card,
            textvariable=detail_var,
            wraplength=620,
            justify="left",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#b4c0d3",
        )
        detail.pack(anchor="w", padx=18, pady=(0, 18))

        card.badge = badge
        return card

    def build_section_frame(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color="#0d131b",
            corner_radius=18,
            border_color="#1b2433",
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
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)

        label = ctk.CTkLabel(
            row,
            text=label_text,
            width=120,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14, weight="bold"),
            text_color="#e7edf7",
        )
        label.pack(side="left", padx=(0, 14))

        entry_kwargs = {
            "height": 42,
            "corner_radius": 14,
            "border_color": "#253247",
            "fg_color": "#121926",
            "text_color": "#f8fbff",
            "placeholder_text": hint_text,
            "font": ctk.CTkFont(family="Segoe UI", size=14),
        }
        if entry_width is not None:
            entry_kwargs["width"] = entry_width

        entry = ctk.CTkEntry(row, **entry_kwargs)
        entry.pack(side="left", fill="x" if expand_entry else "none", expand=expand_entry)
        entry.insert(0, value)
        return entry

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

    def register_macro_hotkey(self, hotkey: str) -> None:
        if self.macro_hotkey_handle is not None:
            keyboard.remove_hotkey(self.macro_hotkey_handle)
            self.macro_hotkey_handle = None

        self.macro_hotkey_handle = keyboard.add_hotkey(
            hotkey,
            self.toggle_macro,
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
            if event.name in {self.toggle_hotkey, self.macro_hotkey}:
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
        new_hotkey = self.macro_hotkey_entry.get().strip().lower()
        if not new_hotkey:
            self.set_macro_status("Missing input", "Add a macro hotkey before applying the controller macro.")
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

        self.stop_macro()
        self.macro_hotkey = new_hotkey
        self.macro_interval_seconds = interval_seconds
        self.macro_steps = self.collect_macro_steps(include_blank_steps=True)
        self.register_macro_hotkey(self.macro_hotkey)
        self.save_config()
        self.reset_macro_progress()

        self.set_macro_status(
            "Macro saved",
            f"Press {self.macro_hotkey.upper()} to start or stop the controller macro. It will wait {self.macro_interval_seconds:g} seconds between loops.",
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

    def toggle_macro(self) -> None:
        if self.macro_running.is_set():
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self) -> None:
        try:
            active_steps = self.collect_macro_steps()
        except ValueError as exc:
            self.set_macro_status("Invalid macro", str(exc))
            return

        if not active_steps:
            self.set_macro_status("No steps", "Add at least one controller button step before starting the macro.")
            return

        if not self.ensure_gamepad():
            return

        if self.macro_running.is_set():
            self.set_macro_status(
                "Running",
                f"Macro is already running. Press {self.macro_hotkey.upper()} or Stop Macro to end it.",
            )
            return

        self.macro_running.set()
        self.reset_macro_progress()
        self.update_activity_indicators()
        self.macro_thread = threading.Thread(
            target=self.run_macro_loop,
            args=(active_steps,),
            daemon=True,
        )
        self.macro_thread.start()
        self.set_macro_status(
            "Running",
            f"The virtual Xbox macro is looping now with a {self.macro_interval_seconds:g} second interval. Press {self.macro_hotkey.upper()} again to stop it.",
        )

    def stop_macro(self) -> None:
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
                f"Press {self.macro_hotkey.upper()} to start or stop the controller macro.",
            )

    def run_macro_loop(self, steps) -> None:
        loop_count = 0
        while self.macro_running.is_set():
            loop_count += 1
            self.root.after(0, lambda lc=loop_count: self.macro_loop_var.set(f"Loop count: {lc}"))
            for index, step in enumerate(steps, start=1):
                if not self.macro_running.is_set():
                    break
                self.press_virtual_button(index, len(steps), step["button"], step["hold_ms"], step["delay_ms"])
            if self.macro_running.is_set() and self.macro_interval_seconds > 0:
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
                self.sleep_with_cancel(self.macro_interval_seconds)

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
        self.reset_macro_progress()
        self.update_activity_indicators()
        self.set_macro_status(
            "Ready",
            f"Press {self.macro_hotkey.upper()} to start or stop the controller macro.",
        )

    def reset_macro_progress(self) -> None:
        self.macro_current_step_var.set("Current step: None")
        self.macro_last_action_var.set("Last action: None")
        self.macro_next_action_var.set("Next action in: --")
        self.macro_loop_var.set("Loop count: 0")

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
        keyboard_color = "#ef4444" if self.is_holding else "#253247"
        macro_color = "#ef4444" if self.macro_running.is_set() else "#253247"
        self.keyboard_activity_indicator.configure(fg_color=keyboard_color)
        self.macro_activity_indicator.configure(fg_color=macro_color)

    def set_key_status(self, status: str, detail: str) -> None:
        self.key_status_var.set(status)
        self.key_detail_var.set(detail)
        self.update_key_status()

    def set_macro_status(self, status: str, detail: str) -> None:
        self.macro_status_var.set(status)
        self.macro_detail_var.set(detail)
        self.update_macro_status()

    def set_update_status(self, title: str, detail: str, has_download: bool = False) -> None:
        self.update_status_var.set(title)
        self.update_detail_var.set(detail)
        self.open_update_button.configure(state="normal" if has_download else "disabled")

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
            with urllib.request.urlopen(self.update_manifest_url, timeout=8) as response:
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

        latest_version = str(payload.get("version", "")).strip()
        download_url = str(payload.get("download_url", "")).strip()
        notes = str(payload.get("notes", "")).strip()

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

    def open_latest_download(self) -> None:
        if self.latest_download_url:
            webbrowser.open(self.latest_download_url)

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

    def update_key_status(self) -> None:
        color_map = {
            "Idle": "#1f2937",
            "Released": "#1f2937",
            "Holding": "#14532d",
            "Mapping saved": "#1d4ed8",
            "Waiting for key": "#4338ca",
            "Key captured": "#1d4ed8",
            "Invalid hotkey": "#7c2d12",
            "Invalid key": "#7c2d12",
            "Missing input": "#7c2d12",
        }
        self.key_status_badge.configure(
            fg_color=color_map.get(self.key_status_var.get(), "#1f2937")
        )

    def update_macro_status(self) -> None:
        color_map = {
            "Ready": "#1f2937",
            "Running": "#14532d",
            "Macro saved": "#1d4ed8",
            "Driver needed": "#7c2d12",
            "Invalid hotkey": "#7c2d12",
            "Invalid macro": "#7c2d12",
            "Missing input": "#7c2d12",
            "No steps": "#7c2d12",
        }
        self.macro_status_badge.configure(
            fg_color=color_map.get(self.macro_status_var.get(), "#1f2937")
        )

    def on_close(self) -> None:
        self.sync_config_from_ui()
        self.save_config()
        self.stop_macro()
        self.force_release()

        if self.capture_target_hook is not None:
            keyboard.unhook(self.capture_target_hook)
            self.capture_target_hook = None

        if self.key_hold_hotkey_handle is not None:
            keyboard.remove_hotkey(self.key_hold_hotkey_handle)
            self.key_hold_hotkey_handle = None

        if self.macro_hotkey_handle is not None:
            keyboard.remove_hotkey(self.macro_hotkey_handle)
            self.macro_hotkey_handle = None

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
