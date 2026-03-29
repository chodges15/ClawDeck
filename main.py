#!/usr/bin/env python3
"""
ClawDeck — Stream Deck controller for Claude Code terminal sessions

Maps a 5x3 (15-key) Elgato Stream Deck into three horizontal session rows:

ROW MODE (default):
  ┌─────┬─────┬─────┬─────┬─────┐
  │ T1  │info │info │info │info │
  ├─────┼─────┼─────┼─────┼─────┤
  │ T2  │info │info │info │info │
  ├─────┼─────┼─────┼─────┼─────┤
  │ T3  │info │info │info │info │
  └─────┴─────┴─────┴─────┴─────┘
  - Label key shows session status and focuses the mapped iTerm2 session
  - Tap the active label key again to enter Nav Mode
  - If Claude is waiting for permission, tap the label key to approve with `y`
  - Hold a label key to focus that session and trigger Whisprflow
  - The four info keys show the CWD, or a scrolling command preview in permission state

NAV MODE:
  ┌─────┬─────┬─────┬─────┬─────┐
  │  1  │  2  │  3  │  4  │  5  │
  ├─────┼─────┼─────┼─────┼─────┤
  │     │     │  ↑  │     │BACK │
  ├─────┼─────┼─────┼─────┼─────┤
  │ MIC │  ←  │  ↓  │  →  │  ⏎  │
  └─────┴─────┴─────┴─────┴─────┘
"""

__version__ = "0.3.0"

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def _setup_logging():
    """Configure clawdeck logger with console and file handlers."""
    log_dir = Path.home() / ".clawdeck"
    try:
        log_dir.mkdir(exist_ok=True)
    except OSError:
        log_dir = Path("/tmp/.clawdeck")
        log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("clawdeck")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_dir / "clawdeck.log", maxBytes=1_000_000, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("File logging unavailable; continuing with console logging only")

    return logger


logger = _setup_logging()

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    CGEventPost,
    CGEventSetFlags,
    CGEventTapCreate,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
    kCGSessionEventTap,
)
import CoreFoundation


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

ITERM_APP_NAME = "iTerm2"
COLS = 5
ROWS = 3
NUM_SESSIONS = 3
SESSIONS = ["T1", "T2", "T3"]
KEYS_PER_ROW = COLS
TOTAL_KEYS = COLS * ROWS
HOLD_THRESHOLD_SEC = 0.5
FN_KEY_CODE = 63
POLL_INTERVAL = 0.2
STATUS_DIR = "/tmp/deck-status"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_STALE_SEC = 3600
PENDING_INFER_SEC = 2.0
BLINK_INTERVAL = 0.5
TTY_MAP_REFRESH_SEC = 30
ACTIVE_CWD_REFRESH_SEC = 1
BRIGHTNESS = 80
DEFAULT_SCROLL_SPEED = 2

# Colors (R, G, B)
COLOR_BG_DEFAULT = (0, 0, 0)
COLOR_FG_DEFAULT = (255, 255, 255)
COLOR_BG_ACTIVE = (255, 176, 0)
COLOR_FG_ACTIVE = (0, 0, 0)
COLOR_BG_IDLE = (30, 100, 220)
COLOR_FG_IDLE = (255, 255, 255)
COLOR_BG_WORKING = (30, 160, 70)
COLOR_FG_WORKING = (255, 255, 255)
COLOR_BG_PERMISSION = (200, 50, 50)
COLOR_FG_PERMISSION = (255, 255, 255)
COLOR_BG_NAV_BACK = (160, 30, 30)
COLOR_BG_NAV_ARROW = (30, 35, 55)
COLOR_FG_NAV_ARROW = (180, 200, 255)
COLOR_BG_NAV_ACTION = (230, 230, 230)
COLOR_FG_NAV_ACTION = (0, 0, 0)
COLOR_BG_NAV_EMPTY = (15, 15, 15)
COLOR_BG_NUM_1 = (180, 40, 40)
COLOR_BG_NUM_2 = (200, 120, 20)
COLOR_BG_NUM_3 = (190, 175, 20)
COLOR_BG_NUM_4 = (40, 150, 60)
COLOR_BG_NUM_5 = (40, 80, 200)

MODE_ROW = "row"
MODE_GRID = MODE_ROW  # Backward-compatible alias for older callers/tests.
MODE_NAV = "nav"

NAV_KEYMAP = {
    0: ("num", "1"),
    1: ("num", "2"),
    2: ("num", "3"),
    3: ("num", "4"),
    4: ("num", "5"),
    7: ("arrow", "Up"),
    9: ("back", None),
    10: ("whisprflow", None),
    11: ("arrow", "Left"),
    12: ("arrow", "Down"),
    13: ("arrow", "Right"),
    14: ("enter", None),
}

NAV_BUTTON_STYLES = {
    0: {"label": "1", "bg": COLOR_BG_NUM_1, "fg": COLOR_FG_DEFAULT},
    1: {"label": "2", "bg": COLOR_BG_NUM_2, "fg": COLOR_FG_DEFAULT},
    2: {"label": "3", "bg": COLOR_BG_NUM_3, "fg": COLOR_FG_DEFAULT},
    3: {"label": "4", "bg": COLOR_BG_NUM_4, "fg": COLOR_FG_DEFAULT},
    4: {"label": "5", "bg": COLOR_BG_NUM_5, "fg": COLOR_FG_DEFAULT},
    7: {"label": "↑", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    9: {"label": "BACK", "bg": COLOR_BG_NAV_BACK, "fg": COLOR_FG_DEFAULT},
    10: {"label": "MIC", "bg": COLOR_BG_NAV_ACTION, "fg": COLOR_FG_NAV_ACTION},
    11: {"label": "←", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    12: {"label": "↓", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    13: {"label": "→", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    14: {"label": "⏎", "bg": COLOR_BG_NAV_ACTION, "fg": COLOR_FG_NAV_ACTION},
}

ARROW_KEY_CODES = {"Up": 126, "Down": 125, "Left": 123, "Right": 124}

kCGKeyboardEventKeycode = 9
MOD_SHIFT = 0x20000
MOD_CONTROL = 0x40000
MOD_OPTION = 0x80000
MOD_COMMAND = 0x100000
MOD_FN = 0x800000

KEY_NAMES = {
    0: "A",
    1: "S",
    2: "D",
    3: "F",
    4: "H",
    5: "G",
    6: "Z",
    7: "X",
    8: "C",
    9: "V",
    11: "B",
    12: "Q",
    13: "W",
    14: "E",
    15: "R",
    16: "Y",
    17: "T",
    18: "1",
    19: "2",
    20: "3",
    21: "4",
    22: "6",
    23: "5",
    24: "=",
    25: "9",
    26: "7",
    27: "-",
    28: "8",
    29: "0",
    31: "O",
    32: "U",
    34: "I",
    35: "P",
    37: "L",
    38: "J",
    40: "K",
    45: "N",
    46: "M",
    36: "Return",
    48: "Tab",
    49: "Space",
    51: "Delete",
    53: "Escape",
    63: "fn",
    122: "F1",
    120: "F2",
    99: "F3",
    118: "F4",
    96: "F5",
    97: "F6",
    98: "F7",
    100: "F8",
    101: "F9",
    109: "F10",
    103: "F11",
    111: "F12",
    123: "Left",
    124: "Right",
    125: "Down",
    126: "Up",
}


def _format_keystroke(key_code, flags):
    """Build a human-readable label like '⌘⇧A' from key code + modifier flags."""
    parts = []
    if flags & MOD_CONTROL:
        parts.append("⌃")
    if flags & MOD_OPTION:
        parts.append("⌥")
    if flags & MOD_SHIFT:
        parts.append("⇧")
    if flags & MOD_COMMAND:
        parts.append("⌘")
    if flags & MOD_FN:
        parts.append("fn+")
    parts.append(KEY_NAMES.get(key_code, f"key{key_code}"))
    return "".join(parts)


CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


CONFIG_DEFAULTS = {
    "brightness": BRIGHTNESS,
    "hold_threshold": HOLD_THRESHOLD_SEC,
    "poll_interval": POLL_INTERVAL,
    "mic_command": "fn",
    "idle_timeout": STATUS_STALE_SEC,
    "folder_label": "last",
    "button_labels": True,
    "scroll_speed": DEFAULT_SCROLL_SPEED,
    "session_map": {session: "" for session in SESSIONS},
    "colors": {
        "active": _rgb_to_hex(COLOR_BG_ACTIVE),
        "idle": _rgb_to_hex(COLOR_BG_IDLE),
        "working": _rgb_to_hex(COLOR_BG_WORKING),
        "permission": _rgb_to_hex(COLOR_BG_PERMISSION),
        "num_1": _rgb_to_hex(COLOR_BG_NUM_1),
        "num_2": _rgb_to_hex(COLOR_BG_NUM_2),
        "num_3": _rgb_to_hex(COLOR_BG_NUM_3),
        "num_4": _rgb_to_hex(COLOR_BG_NUM_4),
        "num_5": _rgb_to_hex(COLOR_BG_NUM_5),
        "arrows": _rgb_to_hex(COLOR_BG_NAV_ARROW),
        "mic_enter": _rgb_to_hex(COLOR_BG_NAV_ACTION),
        "label_text": "#000000",
    },
}


class DeckController:
    def __init__(self):
        self.config = self._load_config()
        self.mode = MODE_ROW
        self.active_slot = None  # label key (0, 5, 10)
        self._key_press_time = {}
        self.deck = None
        self.running = False
        self._settings_port = None
        self._init_fonts()
        self.slot_tty = {}
        self.slot_cwd = {}
        self.slot_status = {}
        self.slot_tool_info = {}
        self.scroll_offsets = {}
        self.scroll_images = {}
        self.scroll_text = {}
        self.blink_on = True
        self._last_blink_toggle = time.time()
        self._last_tty_refresh = 0
        self._last_active_cwd_check = 0
        self._lock = threading.Lock()

    # ─── Config ───────────────────────────────────────────────────────

    def _normalize_config(self, raw):
        config = dict(CONFIG_DEFAULTS)
        config["colors"] = dict(CONFIG_DEFAULTS["colors"])
        config["session_map"] = dict(CONFIG_DEFAULTS["session_map"])

        if not isinstance(raw, dict):
            return config

        saved = dict(raw)
        colors = saved.pop("colors", None)
        session_map = saved.pop("session_map", None)
        config.update(saved)

        if isinstance(colors, dict):
            config["colors"].update(colors)

        if isinstance(session_map, dict):
            for session in SESSIONS:
                value = session_map.get(session)
                if isinstance(value, str):
                    config["session_map"][session] = value

        return config

    def _load_config(self):
        """Load config from config.json, filling in defaults for missing keys."""
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.debug("Config load skipped: %s", e)
            saved = {}
        return self._normalize_config(saved)

    def _save_config(self):
        """Persist current config to config.json."""
        try:
            tmp = CONFIG_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.config, f, indent=2)
                f.write("\n")
            os.rename(tmp, CONFIG_FILE)
        except Exception as e:
            logger.error("Config save failed: %s", e)

    def _apply_config_update(self, updates, save=True):
        merged = dict(self.config)
        merged["colors"] = dict(self.config.get("colors", {}))
        merged["session_map"] = dict(self.config.get("session_map", {}))

        if isinstance(updates, dict):
            colors = updates.get("colors")
            session_map = updates.get("session_map")
            for key, value in updates.items():
                if key in ("colors", "session_map"):
                    continue
                merged[key] = value
            if isinstance(colors, dict):
                merged["colors"].update(colors)
            if isinstance(session_map, dict):
                for session in SESSIONS:
                    if session in session_map:
                        merged["session_map"][session] = session_map[session]

        self.config = self._normalize_config(merged)
        if save:
            self._save_config()

    def _color(self, key, fallback):
        colors = self.config.get("colors", {})
        h = colors.get(key)
        if h:
            try:
                return _hex_to_rgb(h)
            except (ValueError, IndexError) as e:
                logger.debug("Invalid color hex for '%s': %s", key, e)
        return fallback

    # ─── Session Mapping ─────────────────────────────────────────────

    def _key_to_session(self, key):
        if 0 <= key < TOTAL_KEYS:
            return SESSIONS[key // KEYS_PER_ROW]
        return None

    def _session_label_key(self, session):
        if session not in SESSIONS:
            return None
        return SESSIONS.index(session) * KEYS_PER_ROW

    def _key_is_label(self, key):
        return 0 <= key < TOTAL_KEYS and key % KEYS_PER_ROW == 0

    def _key_info_index(self, key):
        if not 0 <= key < TOTAL_KEYS:
            return -1
        col = key % KEYS_PER_ROW
        return col - 1 if col else -1

    def _session_pattern(self, session):
        return str(self.config.get("session_map", {}).get(session, "")).strip()

    def _match_session_name(self, session_name):
        if not session_name:
            return None
        lowered = session_name.lower()
        for session in SESSIONS:
            pattern = self._session_pattern(session)
            if pattern and pattern.lower() in lowered:
                return session
        return None

    def _check_accessibility(self):
        """Check if Accessibility permissions are granted for this terminal app."""
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first process',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True

        print()
        print("━━━ Accessibility Permission Required ━━━")
        print("  Your terminal app needs Accessibility access for")
        print("  session activation and keystroke sending.")
        print()
        print("  Opening System Settings now...")
        print("  → Toggle ON your terminal app, then press Enter here.")
        print()

        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            capture_output=True,
        )

        while True:
            try:
                input("  Press Enter after granting permission...")
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first process',
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print("  Accessibility permission granted!")
                return True
            print("  Not yet — make sure your terminal app is toggled ON, then try again.")

    def _get_iterm_sessions(self):
        """Return iTerm2 sessions as [{'name': str, 'tty': str}, ...]."""
        script = r'''
tell application "iTerm2"
    if not running then return ""
    set output to ""
    repeat with w in windows
        repeat with t in tabs of w
            try
                set s to current session of t
                set sessionName to name of s
                set sessionTTY to tty of s
                set output to output & sessionName & "|||" & sessionTTY & linefeed
            end try
        end repeat
    end repeat
    return output
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
        except Exception:
            logger.warning("Failed to read iTerm2 sessions", exc_info=True)
            return []

        sessions = []
        for line in result.stdout.splitlines():
            if "|||" not in line:
                continue
            name, tty = line.split("|||", 1)
            tty = tty.strip()
            if tty.startswith("/dev/"):
                tty = tty[5:]
            if name.strip() and tty:
                sessions.append({"name": name.strip(), "tty": tty})
        return sessions

    def _build_tty_map(self):
        tty_map = {}
        cwd_map = {}
        sessions = self._get_iterm_sessions()

        for session in SESSIONS:
            pattern = self._session_pattern(session)
            if not pattern:
                continue
            for info in sessions:
                if pattern.lower() in info["name"].lower():
                    label_key = self._session_label_key(session)
                    tty_map[label_key] = info["tty"]
                    cwd = self._resolve_tty_cwd(info["tty"])
                    if cwd:
                        cwd_map[label_key] = cwd
                    break

        logger.debug("TTY map: %s", tty_map)
        logger.debug(
            "CWD map: %s",
            {slot: Path(cwd).name for slot, cwd in cwd_map.items()},
        )

        self.slot_tty = tty_map
        self.slot_cwd = cwd_map

    def _resolve_tty_cwd(self, tty_name):
        """Get the working directory of the most recent shell on a TTY."""
        try:
            result = subprocess.run(
                ["ps", "-t", tty_name, "-o", "pid=,comm="],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            shell_pid = None
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    comm = parts[1].strip().lstrip("-")
                    if comm in ("zsh", "bash", "fish"):
                        shell_pid = parts[0].strip()
            if not shell_pid:
                return None

            result = subprocess.run(
                ["lsof", "-a", "-p", shell_pid, "-d", "cwd", "-Fn"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.strip().split("\n"):
                if line.startswith("n"):
                    return line[1:]
            return None
        except Exception:
            logger.debug("Failed to resolve CWD for %s", tty_name, exc_info=True)
            return None

    def _format_cwd(self, path):
        if not path:
            return None

        mode = self.config.get("folder_label", "last")
        if mode == "off":
            return None

        home = str(Path.home())
        tilde_path = "~" + path[len(home):] if path.startswith(home) else path

        if mode == "full":
            return tilde_path
        if mode == "two":
            parts = Path(path).parts
            return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
        return Path(path).name

    def _frontmost_session_name(self):
        script = r'''
tell application "iTerm2"
    if not running then return ""
    try
        return name of current session of current tab of current window
    on error
        return ""
    end try
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            name = result.stdout.strip()
            return name or None
        except Exception:
            logger.debug("Failed to detect frontmost iTerm2 session", exc_info=True)
            return None

    def _activate_session(self, session):
        pattern = self._session_pattern(session)
        if not pattern:
            return False

        pattern_json = json.dumps(pattern)
        script = f'''
set matchPattern to {pattern_json}
tell application "{ITERM_APP_NAME}"
    if not running then return "not-running"
    repeat with w in windows
        repeat with t in tabs of w
            try
                set s to current session of t
                set sessionName to name of s
                ignoring case
                    if sessionName contains matchPattern then
                        set current tab of w to t
                        set index of w to 1
                        activate
                        return "ok"
                    end if
                end ignoring
            end try
        end repeat
    end repeat
    return "no-match"
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            logger.warning("Failed to activate session %s", session, exc_info=True)
            return False

        ok = result.returncode == 0 and result.stdout.strip() == "ok"
        if ok:
            self.active_slot = self._session_label_key(session)
        return ok

    def _get_frontmost_slot(self):
        session_name = self._frontmost_session_name()
        session = self._match_session_name(session_name)
        return self._session_label_key(session) if session else None

    # ─── Claude Status (Hook Integration) ────────────────────────────

    def _normalize_tool_info(self, raw):
        if raw in (None, "", {}):
            return None

        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped:
                return None
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                return {"tool_name": "Tool", "tool_input": stripped}

        if not isinstance(raw, dict):
            return {"tool_name": "Tool", "tool_input": raw}

        tool_name = raw.get("tool_name") or raw.get("tool") or raw.get("name")
        tool_input = raw.get("tool_input")

        if tool_input is None:
            if "input" in raw:
                tool_input = raw["input"]
            elif "toolInput" in raw:
                tool_input = raw["toolInput"]

        if tool_name is None and isinstance(raw.get("tool"), dict):
            tool_name = raw["tool"].get("name")

        if tool_name is None and len(raw) == 1:
            only_key, only_value = next(iter(raw.items()))
            tool_name = str(only_key)
            tool_input = only_value

        if tool_name is None:
            tool_name = "Tool"

        if tool_input is None:
            tool_input = {
                key: value
                for key, value in raw.items()
                if key not in {"tool_name", "tool", "name", "input", "tool_input", "toolInput"}
            } or None

        return {"tool_name": str(tool_name), "tool_input": tool_input}

    def _read_status_files(self):
        status_dir = Path(STATUS_DIR)
        if not status_dir.exists():
            return

        now = time.time()
        idle_timeout = self.config.get("idle_timeout", STATUS_STALE_SEC)
        tty_to_slot = {tty: slot for slot, tty in self.slot_tty.items()}
        new_status = {}
        new_tool_info = {}

        for f in status_dir.iterdir():
            if f.name.startswith("."):
                continue
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Skipping status file: %s", e)
                continue

            tty = data.get("tty", f.name)
            slot = tty_to_slot.get(tty)
            if slot is None:
                continue

            ts = data.get("ts", 0)
            state = data.get("state", "unknown")
            age = now - ts

            if idle_timeout and state not in ("permission", "pending") and age > idle_timeout:
                continue

            if state == "pending":
                state = "permission" if age >= PENDING_INFER_SEC else "working"

            new_status[slot] = state

            tool_info = self._normalize_tool_info(data.get("tool_input"))
            if tool_info is not None:
                new_tool_info[slot] = tool_info

        permission_slots = {slot for slot, state in new_status.items() if state == "permission"}
        stale_slots = set(self.scroll_offsets) | set(self.scroll_images) | set(self.scroll_text)
        stale_slots -= permission_slots
        for slot in stale_slots:
            self.scroll_offsets.pop(slot, None)
            self.scroll_images.pop(slot, None)
            self.scroll_text.pop(slot, None)

        for slot in permission_slots:
            text = self._format_tool_command(new_tool_info.get(slot))
            if self.scroll_text.get(slot) != text:
                self.scroll_offsets[slot] = 0
                self.scroll_images.pop(slot, None)
                self.scroll_text.pop(slot, None)

        self.slot_status = new_status
        self.slot_tool_info = new_tool_info

    def _approve_permission(self, session):
        label_key = self._session_label_key(session)
        tty_name = self.slot_tty.get(label_key)
        if not tty_name:
            return False

        tty_path = f"/dev/{tty_name}"
        fd = None
        try:
            fd = os.open(tty_path, os.O_WRONLY | os.O_NOCTTY)
            os.write(fd, b"y\n")
            return True
        except OSError:
            logger.warning("Failed to approve permission for %s via %s", session, tty_path, exc_info=True)
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    logger.debug("Failed to close TTY %s", tty_path, exc_info=True)

    # ─── Keystroke Sending ───────────────────────────────────────────

    def _trigger_mic(self):
        mic_cmd = self.config.get("mic_command", "fn")

        if mic_cmd == "fn":
            for _ in range(2):
                event_down = CGEventCreateKeyboardEvent(None, FN_KEY_CODE, True)
                CGEventPost(kCGHIDEventTap, event_down)
                event_up = CGEventCreateKeyboardEvent(None, FN_KEY_CODE, False)
                CGEventPost(kCGHIDEventTap, event_up)
                time.sleep(0.05)
            return

        if isinstance(mic_cmd, dict) and mic_cmd.get("type") == "keystroke":
            key_code = mic_cmd["key_code"]
            flags = mic_cmd.get("flags", 0)
            event_down = CGEventCreateKeyboardEvent(None, key_code, True)
            if flags:
                CGEventSetFlags(event_down, flags)
            CGEventPost(kCGHIDEventTap, event_down)
            event_up = CGEventCreateKeyboardEvent(None, key_code, False)
            if flags:
                CGEventSetFlags(event_up, flags)
            CGEventPost(kCGHIDEventTap, event_up)
            return

        if isinstance(mic_cmd, str):
            try:
                subprocess.Popen(
                    mic_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                logger.warning("MIC command failed", exc_info=True)

    def _learn_keystroke(self):
        captured = {}

        def callback(proxy, event_type, event, refcon):
            if event_type == kCGEventKeyDown:
                captured["key_code"] = CGEventGetIntegerValueField(
                    event, kCGKeyboardEventKeycode
                )
                captured["flags"] = CGEventGetFlags(event)
                CoreFoundation.CFRunLoopStop(CoreFoundation.CFRunLoopGetCurrent())
                return None
            if event_type == kCGEventFlagsChanged:
                flags = CGEventGetFlags(event)
                key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                if flags & (MOD_SHIFT | MOD_CONTROL | MOD_OPTION | MOD_COMMAND | MOD_FN):
                    captured["key_code"] = key_code
                    captured["flags"] = flags
                    CoreFoundation.CFRunLoopStop(CoreFoundation.CFRunLoopGetCurrent())
                    return None
            return event

        event_mask = (1 << kCGEventKeyDown) | (1 << kCGEventFlagsChanged)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            0,
            event_mask,
            callback,
            None,
        )

        if tap is None:
            logger.error("Failed to create event tap — check Accessibility permissions")
            print("  Failed to create event tap — check Accessibility permissions")
            return

        source = CoreFoundation.CFMachPortCreateRunLoopSource(None, tap, 0)
        loop = CoreFoundation.CFRunLoopGetCurrent()
        CoreFoundation.CFRunLoopAddSource(loop, source, CoreFoundation.kCFRunLoopCommonModes)

        print("  Press the key (or combo) you want for MIC...")
        CoreFoundation.CFRunLoopRun()
        CoreFoundation.CFRunLoopRemoveSource(
            loop, source, CoreFoundation.kCFRunLoopCommonModes
        )

        if not captured:
            print("  No keystroke captured")
            return

        key_code = captured["key_code"]
        flags = captured["flags"]
        clean_flags = flags & (MOD_SHIFT | MOD_CONTROL | MOD_OPTION | MOD_COMMAND | MOD_FN)
        label = _format_keystroke(key_code, clean_flags)

        self.config["mic_command"] = {
            "type": "keystroke",
            "key_code": key_code,
            "flags": clean_flags,
            "label": label,
        }
        self._save_config()
        print(f"  mic → {label}")

    def _send_key(self, key_name):
        if key_name == "Return":
            script = 'tell application "System Events" to key code 36'
        elif key_name in ARROW_KEY_CODES:
            script = f'tell application "System Events" to key code {ARROW_KEY_CODES[key_name]}'
        else:
            script = f'tell application "System Events" to keystroke "{key_name}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)

    # ─── Button Rendering ────────────────────────────────────────────

    def _init_fonts(self):
        candidates = [
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Geneva.ttf",
            "/Library/Fonts/Arial.ttf",
        ]

        def load(size):
            for path in candidates:
                try:
                    return ImageFont.truetype(path, size)
                except (IOError, OSError):
                    logger.debug("Font not found: %s", path)
                    continue
            return ImageFont.load_default()

        self.font_sm = load(12)
        self.font_md = load(18)
        self.font_lg = load(26)
        self.font_xs = load(9)

    def _pick_font(self, label):
        if len(label) <= 2:
            return self.font_lg
        if len(label) <= 4:
            return self.font_md
        return self.font_sm

    def _button_dimensions(self):
        if self.deck:
            try:
                image = PILHelper.create_image(self.deck, background=COLOR_BG_DEFAULT)
                return image.size
            except Exception:
                logger.debug("Failed to query button dimensions", exc_info=True)
        return (72, 72)

    def _render_button(
        self,
        label,
        bg=COLOR_BG_DEFAULT,
        fg=COLOR_FG_DEFAULT,
        border_color=None,
        border_width=8,
        subtitle=None,
    ):
        image = PILHelper.create_image(self.deck, background=bg)
        draw = ImageDraw.Draw(image)
        width, height = image.size

        if border_color:
            for i in range(border_width):
                draw.rectangle(
                    [i, i, width - 1 - i, height - 1 - i],
                    outline=border_color,
                )

        bar_h = 0
        if subtitle:
            bar_h = 16
            draw.rectangle([0, 0, width, bar_h], fill=(0, 0, 0, 153))
            display_subtitle = subtitle
            sub_bbox = draw.textbbox((0, 0), display_subtitle, font=self.font_xs)
            sub_tw = sub_bbox[2] - sub_bbox[0]
            while sub_tw > width - 10 and len(display_subtitle) > 3:
                display_subtitle = display_subtitle[:-1]
                sub_bbox = draw.textbbox((0, 0), f"{display_subtitle}…", font=self.font_xs)
                sub_tw = sub_bbox[2] - sub_bbox[0]
            if display_subtitle != subtitle:
                display_subtitle = f"{display_subtitle}…"
            sub_x = (width - sub_tw) / 2
            sub_y = (bar_h - (sub_bbox[3] - sub_bbox[1])) / 2 - 1
            draw.text(
                (sub_x, sub_y),
                display_subtitle,
                font=self.font_xs,
                fill=(255, 255, 255),
            )

        if label:
            font = self._pick_font(label)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (width - tw) / 2
            y = (height - th) / 2 - 2 + (bar_h / 2 if bar_h else 0)
            draw.text((x, y), label, font=font, fill=fg)

        return PILHelper.to_native_format(self.deck, image)

    def _first_display_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            for item in value:
                found = self._first_display_value(item)
                if found:
                    return found
            return None
        if isinstance(value, dict):
            for item in value.values():
                found = self._first_display_value(item)
                if found:
                    return found
            return None
        return str(value)

    def _format_tool_command(self, tool_info):
        if not tool_info:
            return "Permission required"

        tool_name = str(tool_info.get("tool_name") or "Tool")
        tool_input = tool_info.get("tool_input")
        lower_name = tool_name.lower()

        summary = None
        if isinstance(tool_input, dict):
            if lower_name == "bash":
                summary = tool_input.get("command") or tool_input.get("cmd")
            elif lower_name in {"read", "edit", "write", "multiedit"}:
                summary = (
                    tool_input.get("file_path")
                    or tool_input.get("path")
                    or self._first_display_value(tool_input.get("paths"))
                )

        if summary is None:
            summary = self._first_display_value(tool_input)

        if summary:
            return f"{tool_name}: {summary}"
        return tool_name

    def _render_scroll_strip(self, text):
        button_w, button_h = self._button_dimensions()
        viewport_w = button_w * (KEYS_PER_ROW - 1)
        gap = max(button_w // 2, 24)
        background = tuple(max(c // 3, 20) for c in self._color("permission", COLOR_BG_PERMISSION))

        probe = Image.new("RGB", (1, 1), background)
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), text, font=self.font_sm)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        strip_w = max(text_w + gap * 2, viewport_w + gap)
        strip = Image.new("RGB", (strip_w, button_h), background)
        draw = ImageDraw.Draw(strip)
        text_x = gap
        text_y = (button_h - text_h) / 2 - bbox[1]
        draw.text((text_x, text_y), text, font=self.font_sm, fill=COLOR_FG_PERMISSION)
        return strip

    def _ensure_scroll_strip(self, label_key):
        text = self._format_tool_command(self.slot_tool_info.get(label_key))
        if label_key not in self.scroll_images or self.scroll_text.get(label_key) != text:
            self.scroll_images[label_key] = self._render_scroll_strip(text)
            self.scroll_text[label_key] = text
            self.scroll_offsets[label_key] = 0
        return self.scroll_images[label_key]

    def _render_scroll_button(self, strip, offset, button_idx):
        button_w, button_h = self._button_dimensions()
        start = (offset + button_idx * button_w) % strip.width

        if start + button_w <= strip.width:
            crop = strip.crop((start, 0, start + button_w, button_h))
        else:
            right = strip.crop((start, 0, strip.width, button_h))
            left = strip.crop((0, 0, button_w - right.width, button_h))
            crop = Image.new("RGB", (button_w, button_h))
            crop.paste(right, (0, 0))
            crop.paste(left, (right.width, 0))

        return PILHelper.to_native_format(self.deck, crop)

    def _advance_scroll_offset(self, label_key, strip_width):
        speed = max(int(self.config.get("scroll_speed", DEFAULT_SCROLL_SPEED)), 0)
        if strip_width <= 0:
            self.scroll_offsets[label_key] = 0
            return 0
        next_offset = (self.scroll_offsets.get(label_key, 0) + speed) % strip_width
        self.scroll_offsets[label_key] = next_offset
        return next_offset

    def _advance_scroll_offsets(self):
        changed = False
        for label_key, state in self.slot_status.items():
            if state != "permission":
                continue
            strip = self._ensure_scroll_strip(label_key)
            old_offset = self.scroll_offsets.get(label_key, 0)
            new_offset = self._advance_scroll_offset(label_key, strip.width)
            if new_offset != old_offset:
                changed = True
        return changed

    # ─── Display Updates ─────────────────────────────────────────────

    def _update_all_buttons(self):
        if self.mode == MODE_NAV:
            self._draw_nav_mode()
        else:
            self._draw_row_mode()

    def _get_slot_style(self, slot):
        if isinstance(slot, str):
            label_key = self._session_label_key(slot)
        else:
            session = self._key_to_session(slot)
            label_key = self._session_label_key(session) if session else slot

        is_active = label_key == self.active_slot
        status = self.slot_status.get(label_key)
        active_color = self._color("active", COLOR_BG_ACTIVE)
        border = active_color if is_active else None

        if status == "idle":
            return self._color("idle", COLOR_BG_IDLE), COLOR_FG_IDLE, border
        if status == "working":
            return self._color("working", COLOR_BG_WORKING), COLOR_FG_WORKING, border
        if status == "permission":
            perm_color = self._color("permission", COLOR_BG_PERMISSION)
            if self.blink_on:
                return perm_color, COLOR_FG_PERMISSION, border
            dim = tuple(max(c // 4, 10) for c in perm_color)
            return dim, (100, 100, 100), border

        if is_active:
            return active_color, self._color("label_text", COLOR_FG_ACTIVE), None
        return COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, None

    def _draw_row_mode(self):
        for session in SESSIONS:
            label_key = self._session_label_key(session)
            bg, fg, border = self._get_slot_style(label_key)
            self.deck.set_key_image(
                label_key,
                self._render_button(session, bg, fg, border_color=border),
            )

            info_keys = range(label_key + 1, label_key + KEYS_PER_ROW)
            status = self.slot_status.get(label_key)
            is_mapped = label_key in self.slot_tty

            if not is_mapped:
                for key in info_keys:
                    self.deck.set_key_image(
                        key, self._render_button("", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT)
                    )
                continue

            if status == "permission":
                strip = self._ensure_scroll_strip(label_key)
                offset = self.scroll_offsets.get(label_key, 0)
                for button_idx, key in enumerate(info_keys):
                    self.deck.set_key_image(
                        key, self._render_scroll_button(strip, offset, button_idx)
                    )
                continue

            subtitle = None
            raw_cwd = self.slot_cwd.get(label_key)
            if raw_cwd and self.config.get("button_labels", True):
                subtitle = self._format_cwd(raw_cwd)

            first_key = label_key + 1
            self.deck.set_key_image(
                first_key,
                self._render_button("", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, subtitle=subtitle),
            )
            for key in range(first_key + 1, label_key + KEYS_PER_ROW):
                self.deck.set_key_image(
                    key, self._render_button("", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT)
                )

    def _get_nav_style(self, key):
        style = NAV_BUTTON_STYLES.get(key)
        if style is None:
            return None

        bg = style["bg"]
        if key in (0, 1, 2, 3, 4):
            bg = self._color(f"num_{key + 1}", bg)
        elif key in (7, 11, 12, 13):
            bg = self._color("arrows", bg)
        elif key in (10, 14):
            bg = self._color("mic_enter", bg)

        return {"label": style["label"], "bg": bg, "fg": style["fg"]}

    def _draw_nav_mode(self):
        for key in range(TOTAL_KEYS):
            border = self._color("active", COLOR_BG_ACTIVE) if key == self.active_slot else None
            style = self._get_nav_style(key)
            if style:
                self.deck.set_key_image(
                    key,
                    self._render_button(
                        style["label"],
                        style["bg"],
                        style["fg"],
                        border_color=border,
                    ),
                )
            else:
                self.deck.set_key_image(
                    key,
                    self._render_button("", COLOR_BG_NAV_EMPTY, border_color=border),
                )

    # ─── Key Press Handling ──────────────────────────────────────────

    def _on_key_change(self, deck, key, pressed):
        with self._lock:
            self._handle_key(key, pressed)

    def _handle_key(self, key, pressed):
        if self.mode == MODE_NAV:
            if pressed:
                self._handle_nav_key(key)
            return

        if not self._key_is_label(key):
            return

        session = self._key_to_session(key)
        if session is None:
            return

        if pressed:
            self._key_press_time[key] = time.time()
            return

        press_time = self._key_press_time.pop(key, None)
        if press_time is None:
            return

        held = time.time() - press_time
        if held >= self.config.get("hold_threshold", HOLD_THRESHOLD_SEC):
            self._activate_session(session)
            self._update_all_buttons()
            self._trigger_mic()
            return

        self._handle_row_key(session)

    def _handle_row_key(self, session):
        label_key = self._session_label_key(session)

        if self.slot_status.get(label_key) == "permission":
            self._approve_permission(session)
            return

        if label_key == self.active_slot:
            self._activate_session(session)
            self.mode = MODE_NAV
            self._update_all_buttons()
            return

        if self._activate_session(session):
            self._update_all_buttons()

    def _handle_nav_key(self, key):
        action = NAV_KEYMAP.get(key)
        if action is None:
            return

        kind, value = action

        if kind == "back":
            self.mode = MODE_ROW
            self._update_all_buttons()
        elif kind == "num":
            self._send_key(value)
        elif kind == "arrow":
            self._send_key(value)
        elif kind == "whisprflow":
            self._trigger_mic()
        elif kind == "enter":
            self._send_key("Return")

    # ─── Active Window Polling ───────────────────────────────────────

    def _poll_active_loop(self):
        consecutive_errors = 0
        while self.running:
            try:
                with self._lock:
                    if self.mode == MODE_ROW:
                        needs_redraw = False
                        now = time.time()

                        if now - self._last_tty_refresh >= TTY_MAP_REFRESH_SEC:
                            old_ttys = dict(self.slot_tty)
                            old_cwds = dict(self.slot_cwd)
                            self._build_tty_map()
                            self._last_tty_refresh = now
                            if self.slot_tty != old_ttys or self.slot_cwd != old_cwds:
                                needs_redraw = True

                        slot = self._get_frontmost_slot()
                        if slot != self.active_slot:
                            self.active_slot = slot
                            needs_redraw = True

                        if (
                            self.active_slot is not None
                            and now - self._last_active_cwd_check >= ACTIVE_CWD_REFRESH_SEC
                        ):
                            tty = self.slot_tty.get(self.active_slot)
                            if tty:
                                cwd = self._resolve_tty_cwd(tty)
                                old_cwd = self.slot_cwd.get(self.active_slot)
                                if cwd and cwd != old_cwd:
                                    self.slot_cwd[self.active_slot] = cwd
                                    needs_redraw = True
                            self._last_active_cwd_check = now

                        old_status = dict(self.slot_status)
                        old_tool_info = dict(self.slot_tool_info)
                        self._read_status_files()
                        if self.slot_status != old_status or self.slot_tool_info != old_tool_info:
                            needs_redraw = True

                        if now - self._last_blink_toggle >= BLINK_INTERVAL:
                            self.blink_on = not self.blink_on
                            self._last_blink_toggle = now
                            if "permission" in self.slot_status.values():
                                needs_redraw = True

                        if self._advance_scroll_offsets():
                            needs_redraw = True

                        if needs_redraw:
                            self._update_all_buttons()

                consecutive_errors = 0
            except Exception:
                consecutive_errors += 1
                if consecutive_errors <= 10 or consecutive_errors % 100 == 0:
                    level = logging.ERROR if consecutive_errors >= 10 else logging.WARNING
                    logger.log(
                        level,
                        "Poll loop error (consecutive: %d)",
                        consecutive_errors,
                        exc_info=True,
                    )

            time.sleep(self.config.get("poll_interval", POLL_INTERVAL))

    # ─── REPL Commands ────────────────────────────────────────────────

    def _handle_command(self, raw):
        parts = raw.split(None, 1)
        if not parts:
            return
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if cmd == "help":
            print("━━━ Commands ━━━")
            print("  brightness <0-100>    Set Stream Deck brightness")
            print("  hold <seconds>        Set hold threshold for Whisprflow")
            print("  poll <seconds>        Set poll interval")
            print("  mic <fn|command>      Set MIC action")
            print("  mic learn             Capture the next keystroke as MIC")
            print("  settings              Open settings in browser")
            print("  quit                  Exit")
            return

        if cmd == "brightness":
            if arg is None:
                print(f"  brightness = {self.config['brightness']}")
                return
            try:
                val = int(arg)
                if not 0 <= val <= 100:
                    raise ValueError
            except ValueError:
                print("  Usage: brightness <0-100>")
                return
            self.config["brightness"] = val
            if self.deck:
                self.deck.set_brightness(val)
            self._save_config()
            print(f"  brightness → {val}")
            return

        if cmd == "hold":
            if arg is None:
                print(f"  hold = {self.config['hold_threshold']}s")
                return
            try:
                val = float(arg)
                if val <= 0:
                    raise ValueError
            except ValueError:
                print("  Usage: hold <seconds>")
                return
            self.config["hold_threshold"] = val
            self._save_config()
            print(f"  hold → {val}s")
            return

        if cmd == "poll":
            if arg is None:
                print(f"  poll = {self.config['poll_interval']}s")
                return
            try:
                val = float(arg)
                if val <= 0:
                    raise ValueError
            except ValueError:
                print("  Usage: poll <seconds>")
                return
            self.config["poll_interval"] = val
            self._save_config()
            print(f"  poll → {val}s")
            return

        if cmd == "mic":
            if arg is None:
                mic_cmd = self.config["mic_command"]
                if isinstance(mic_cmd, dict):
                    print(f"  mic = {mic_cmd.get('label', mic_cmd)}")
                else:
                    print(f"  mic = {mic_cmd}")
                return
            if arg.lower() == "learn":
                self._learn_keystroke()
                return
            self.config["mic_command"] = arg
            self._save_config()
            print(f"  mic → {arg}")
            return

        if cmd == "settings":
            if self._settings_port:
                import webbrowser

                webbrowser.open(f"http://127.0.0.1:{self._settings_port}/")
                print("  Opened settings in browser")
            else:
                print("━━━ Settings ━━━")
                for key, value in self.config.items():
                    print(f"  {key} = {value}")
            return

        if cmd in ("quit", "exit", "q"):
            raise SystemExit

        print(f"  Unknown command: {cmd} (type 'help' for commands)")

    # ─── Main Entry Point ────────────────────────────────────────────

    def _clear_status_dir(self):
        os.makedirs(STATUS_DIR, exist_ok=True)
        for f in Path(STATUS_DIR).iterdir():
            try:
                f.unlink()
            except PermissionError:
                logger.debug("Could not unlink %s, falling back to rm", f)
                subprocess.run(["rm", "-f", str(f)], capture_output=True)

    def run(self):
        self._check_accessibility()

        devices = DeviceManager().enumerate()
        if not devices:
            logger.error("No Stream Deck found")
            print("No Stream Deck found. Make sure it's plugged in.")
            print("Also verify: brew install hidapi && pip install streamdeck")
            sys.exit(1)

        logger.info("Found %d HID interface(s), attempting to open...", len(devices))
        for i, dev in enumerate(devices):
            try:
                dev.open()
                self.deck = dev
                logger.info("Opened interface %d: %s", i, dev.deck_type())
                break
            except Exception as e:
                logger.warning("Interface %d failed: %s", i, e)
        else:
            logger.error("Could not open any Stream Deck interface")
            print("ERROR: Could not open any Stream Deck interface.")
            print("If this is a permissions issue, try: sudo python main.py")
            sys.exit(1)

        self.deck.reset()
        self.deck.set_brightness(self.config["brightness"])

        key_count = self.deck.key_count()
        logger.info("Connected: %s (%d keys)", self.deck.deck_type(), key_count)
        if key_count != TOTAL_KEYS:
            logger.warning(
                "Expected %d keys but deck has %d — row layout may not work correctly",
                TOTAL_KEYS,
                key_count,
            )
            print(f"Warning: this script expects {TOTAL_KEYS} keys but your deck has {key_count}.")

        self._build_tty_map()
        self._clear_status_dir()
        self._update_all_buttons()
        self.deck.set_key_callback(self._on_key_change)

        settings_port = self._start_settings_server()

        self.running = True
        poller = threading.Thread(target=self._poll_active_loop, daemon=True)
        poller.start()

        amber = "\033[38;5;214m"
        dim = "\033[2m"
        reset = "\033[0m"
        print(
            f"""
{amber}  ██████╗██╗      █████╗ ██╗    ██╗{reset}
{amber} ██╔════╝██║     ██╔══██╗██║    ██║{reset}
{amber} ██║     ██║     ███████║██║ █╗ ██║{reset}
{amber} ██║     ██║     ██╔══██║██║███╗██║{reset}
{amber} ╚██████╗███████╗██║  ██║╚███╔███╔╝{reset}
{amber}  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝{reset}  {dim}v{__version__}{reset}
"""
        )
        print("  Type 'help' for commands")
        if settings_port:
            print(f"  Settings UI: http://127.0.0.1:{settings_port}")
        print()

        try:
            while True:
                cmd = input().strip()
                self._handle_command(cmd)
        except (KeyboardInterrupt, EOFError, SystemExit):
            pass
        finally:
            print("\nShutting down...")
            self.running = False
            if self.deck:
                self.deck.reset()
                self.deck.close()
            print("Done.")

    # ─── Settings HTTP Server ────────────────────────────────────────

    def _start_settings_server(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import urlparse

        controller_ref = self
        settings_html_path = os.path.join(SCRIPT_DIR, "settings.html")

        class SettingsHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                path = urlparse(self.path).path
                if path in ("/", "/settings"):
                    with open(settings_html_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content)
                elif path == "/api/settings":
                    self._json_response(controller_ref.config)
                elif path == "/api/status":
                    if controller_ref.running and controller_ref.deck:
                        self._json_response(
                            {
                                "running": True,
                                "deck": controller_ref.deck.deck_type(),
                                "sessions": len(controller_ref.slot_tty),
                            }
                        )
                    else:
                        self._json_response({"running": False})
                else:
                    self.send_error(404)

            def do_POST(self):
                path = urlparse(self.path).path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len) if content_len else b""

                if path == "/api/settings":
                    try:
                        new_config = json.loads(body)
                    except json.JSONDecodeError:
                        self._json_response({"ok": False, "error": "Invalid JSON"}, 400)
                        return

                    old_session_map = dict(controller_ref.config.get("session_map", {}))
                    controller_ref._apply_config_update(new_config)

                    if controller_ref.deck and controller_ref.running:
                        try:
                            controller_ref.deck.set_brightness(
                                controller_ref.config.get("brightness", BRIGHTNESS)
                            )
                        except Exception:
                            logger.warning("Failed to set brightness via settings API", exc_info=True)

                        if controller_ref.config.get("session_map", {}) != old_session_map:
                            controller_ref._build_tty_map()

                        controller_ref._update_all_buttons()

                    self._json_response({"ok": True})
                    return

                if path == "/api/hooks":
                    result = subprocess.run(
                        [sys.executable, os.path.join(SCRIPT_DIR, "install_hooks.py")],
                        input="y\n",
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    output = (result.stdout + result.stderr).strip()
                    self._json_response({"ok": result.returncode == 0, "output": output})
                    return

                self.send_error(404)

            def _json_response(self, data, code=200):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        for port in range(19830, 19850):
            try:
                server = HTTPServer(("127.0.0.1", port), SettingsHandler)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self._settings_port = port
                return port
            except OSError:
                logger.debug("Port %d in use, trying next", port)
                continue
        return None


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("Usage: python main.py")
        print()
    else:
        DeckController().run()
