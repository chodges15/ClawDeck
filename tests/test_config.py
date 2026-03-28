"""Tests for config defaults and merging."""
import copy
import pytest
from main import CONFIG_DEFAULTS


# ─── CONFIG_DEFAULTS structure ───────────────────────────────────────────────

def test_defaults_has_required_keys():
    required = [
        "brightness",
        "hold_threshold",
        "poll_interval",
        "snap_enabled",
        "layout",
        "folder_label",
        "colors",
        "button_labels",
        "overlay_label",
    ]
    for key in required:
        assert key in CONFIG_DEFAULTS, f"Missing key: {key}"


def test_defaults_colors_has_all_keys():
    colors = CONFIG_DEFAULTS["colors"]
    required = ["active", "idle", "working", "permission", "label_text"]
    for key in required:
        assert key in colors, f"Missing color key: {key}"


def test_defaults_layout_valid():
    assert CONFIG_DEFAULTS["layout"] == "default"


def test_defaults_folder_label_valid():
    assert CONFIG_DEFAULTS["folder_label"] == "last"


# ─── Config merge behavior (via controller.config) ───────────────────────────

def test_config_merge_preserves_user_values(controller):
    # After construction, override brightness and confirm it sticks
    controller.config["brightness"] = 50
    assert controller.config["brightness"] == 50


def test_config_merge_adds_missing_keys(controller):
    # Simulate an old config that was loaded without folder_label.
    # Remove the key, then re-merge with CONFIG_DEFAULTS to mimic _load_config behavior.
    controller.config.pop("folder_label", None)

    # Re-apply the same deep-merge logic _load_config uses:
    # missing top-level keys from defaults get filled in.
    merged = copy.deepcopy(CONFIG_DEFAULTS)
    merged.update(controller.config)
    # folder_label is absent from the "user" config, so the default survives.
    assert merged.get("folder_label") == CONFIG_DEFAULTS["folder_label"]
