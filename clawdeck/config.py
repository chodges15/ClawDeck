"""Configuration loading, defaults, and update helpers for ClawDeck."""

import json
import os

from .app_logging import logger
from .constants import (
    BRIGHTNESS,
    COLOR_BG_ACTIVE,
    COLOR_BG_IDLE,
    COLOR_BG_NAV_ACTION,
    COLOR_BG_NAV_ARROW,
    COLOR_BG_NUM_1,
    COLOR_BG_NUM_2,
    COLOR_BG_NUM_3,
    COLOR_BG_NUM_4,
    COLOR_BG_NUM_5,
    COLOR_BG_PERMISSION,
    COLOR_BG_WORKING,
    DEFAULT_SCROLL_SPEED,
    HOLD_THRESHOLD_SEC,
    POLL_INTERVAL,
    PROJECT_ROOT,
    SESSIONS,
    STATUS_STALE_SEC,
)


CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")


def rgb_to_hex(rgb):
    """Convert an RGB tuple into a CSS-style hex string."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hex_to_rgb(value):
    """Convert a hex color string into an RGB tuple."""
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


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
        "active": rgb_to_hex(COLOR_BG_ACTIVE),
        "idle": rgb_to_hex(COLOR_BG_IDLE),
        "working": rgb_to_hex(COLOR_BG_WORKING),
        "permission": rgb_to_hex(COLOR_BG_PERMISSION),
        "num_1": rgb_to_hex(COLOR_BG_NUM_1),
        "num_2": rgb_to_hex(COLOR_BG_NUM_2),
        "num_3": rgb_to_hex(COLOR_BG_NUM_3),
        "num_4": rgb_to_hex(COLOR_BG_NUM_4),
        "num_5": rgb_to_hex(COLOR_BG_NUM_5),
        "arrows": rgb_to_hex(COLOR_BG_NAV_ARROW),
        "mic_enter": rgb_to_hex(COLOR_BG_NAV_ACTION),
        "label_text": "#000000",
    },
}


class ConfigStore:
    """Persist and normalize user configuration stored in `config.json`."""

    def __init__(self, path=CONFIG_FILE):
        """Initialize the store with an optional config path override."""
        self.path = path

    def normalize(self, raw):
        """Merge raw config data onto the default config structure."""
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

    def load(self):
        """Load config from disk and fall back to defaults on parse errors."""
        try:
            with open(self.path) as handle:
                saved = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug("Config load skipped: %s", exc)
            saved = {}
        return self.normalize(saved)

    def save(self, config):
        """Write config to disk atomically when possible."""
        try:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w") as handle:
                json.dump(config, handle, indent=2)
                handle.write("\n")
            os.rename(tmp_path, self.path)
        except Exception as exc:
            logger.error("Config save failed: %s", exc)

    def apply_update(self, config, updates, save=True):
        """Merge an update payload into config and optionally persist it."""
        merged = dict(config)
        merged["colors"] = dict(config.get("colors", {}))
        merged["session_map"] = dict(config.get("session_map", {}))

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

        normalized = self.normalize(merged)
        if save:
            self.save(normalized)
        return normalized

    def color(self, config, key, fallback):
        """Return a configured RGB color or a fallback tuple."""
        colors = config.get("colors", {})
        value = colors.get(key)
        if value:
            try:
                return hex_to_rgb(value)
            except (ValueError, IndexError) as exc:
                logger.debug("Invalid color hex for '%s': %s", key, exc)
        return fallback
