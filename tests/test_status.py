import pytest
from main import (
    COLOR_BG_ACTIVE, COLOR_BG_IDLE, COLOR_BG_WORKING, COLOR_BG_PERMISSION,
    COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, MODE_GRID, MODE_NAV,
)


# --- Grid mode slot styling ---

def test_idle_style(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_IDLE
    assert border is None


def test_working_style(controller):
    controller.slot_status = {0: "working"}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_WORKING


def test_permission_blink_on(controller):
    controller.slot_status = {0: "permission"}
    controller.active_slot = None
    controller.blink_on = True
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_PERMISSION


def test_permission_blink_off(controller):
    controller.slot_status = {0: "permission"}
    controller.active_slot = None
    controller.blink_on = False
    bg, fg, border = controller._get_slot_style(0)
    # Dimmed — not full permission color
    assert bg != COLOR_BG_PERMISSION
    assert isinstance(bg, tuple)
    assert len(bg) == 3


def test_active_slot_gets_border(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = 0
    bg, fg, border = controller._get_slot_style(0)
    assert border is not None
    assert isinstance(border, tuple)
    assert len(border) == 3


def test_inactive_slot_no_border(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = 1
    bg, fg, border = controller._get_slot_style(0)
    assert border is None


def test_no_status_active(controller):
    controller.slot_status = {}
    controller.active_slot = 0
    bg, fg, border = controller._get_slot_style(0)
    # _color("active", ...) returns an RGB tuple from config
    assert isinstance(bg, tuple)
    assert len(bg) == 3
    assert border is None


def test_no_status_inactive(controller):
    controller.slot_status = {}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_DEFAULT
    assert fg == COLOR_FG_DEFAULT


# --- Nav mode key styling ---

def test_nav_style_number_keys(controller):
    for key, expected_label in enumerate(["1", "2", "3", "4", "5"]):
        result = controller._get_nav_style(key)
        assert result is not None
        assert expected_label in str(result["label"])


def test_nav_style_arrows(controller):
    arrow_keys = [7, 11, 12, 13]
    for key in arrow_keys:
        result = controller._get_nav_style(key)
        assert result is not None


def test_nav_style_invalid_key(controller):
    result = controller._get_nav_style(15)
    assert result is None
