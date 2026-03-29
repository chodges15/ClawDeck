"""Tests for config defaults and merging."""

from clawdeck.config import CONFIG_DEFAULTS


def test_defaults_has_required_keys():
    required = [
        "brightness",
        "hold_threshold",
        "poll_interval",
        "idle_timeout",
        "folder_label",
        "button_labels",
        "scroll_speed",
        "session_map",
        "colors",
    ]
    for key in required:
        assert key in CONFIG_DEFAULTS, f"Missing key: {key}"


def test_defaults_colors_has_all_keys():
    colors = CONFIG_DEFAULTS["colors"]
    required = ["active", "idle", "working", "permission", "label_text"]
    for key in required:
        assert key in colors, f"Missing color key: {key}"


def test_defaults_session_map_has_all_sessions():
    assert CONFIG_DEFAULTS["session_map"] == {"T1": "", "T2": "", "T3": ""}


def test_defaults_scroll_speed_valid():
    assert CONFIG_DEFAULTS["scroll_speed"] == 2


def test_defaults_folder_label_valid():
    assert CONFIG_DEFAULTS["folder_label"] == "last"


def test_config_update_preserves_existing_values(controller):
    controller.config["brightness"] = 50
    controller._apply_config_update({"scroll_speed": 4}, save=False)
    assert controller.config["brightness"] == 50
    assert controller.config["scroll_speed"] == 4


def test_config_update_merges_session_map(controller):
    controller._apply_config_update({"session_map": {"T1": "alpha"}}, save=False)
    assert controller.config["session_map"] == {"T1": "alpha", "T2": "", "T3": ""}


def test_normalize_config_adds_missing_nested_keys(controller):
    raw = {"session_map": {"T2": "beta"}}
    normalized = controller._normalize_config(raw)
    assert normalized["session_map"] == {"T1": "", "T2": "beta", "T3": ""}
    assert normalized["scroll_speed"] == CONFIG_DEFAULTS["scroll_speed"]
