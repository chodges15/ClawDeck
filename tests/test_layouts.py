import pytest
from main import LAYOUTS, LAYOUT_NAMES, COLS, ROWS, ENTER_KEY_INDEX, GRID_SLOTS, TOTAL_KEYS


# --- Constants ---

def test_all_layouts_have_15_elements():
    for name, layout in LAYOUTS.items():
        assert len(layout) == 15, f"Layout '{name}' has {len(layout)} elements, expected 15"


def test_all_layouts_end_with_enter():
    for name, layout in LAYOUTS.items():
        assert layout[-1] == "ENTER", f"Layout '{name}' last element is '{layout[-1]}', expected 'ENTER'"


def test_layout_names_match_keys():
    assert set(LAYOUT_NAMES) == set(LAYOUTS.keys())


# --- Terminal name helpers ---

def test_get_terminal_names_excludes_enter(controller):
    names = controller._get_terminal_names()
    assert "ENTER" not in names


def test_get_terminal_names_unique(controller):
    names = controller._get_terminal_names()
    assert len(names) == len(set(names))


def test_get_terminal_names_default_has_14(controller):
    controller.config["layout"] = "default"
    names = controller._get_terminal_names()
    assert len(names) == 14


# --- Terminal slot helpers ---

def test_get_terminal_slots_covers_all_keys(controller):
    controller.config["layout"] = "default"
    slots = controller._get_terminal_slots()
    all_slot_keys = set()
    for key_list in slots.values():
        all_slot_keys.update(key_list)
    expected = set(range(TOTAL_KEYS)) - {ENTER_KEY_INDEX}
    assert all_slot_keys == expected


# --- Key ↔ terminal resolution ---

def test_key_to_terminal_enter_is_none(controller):
    controller.config["layout"] = "default"
    result = controller._key_to_terminal(ENTER_KEY_INDEX)
    assert result is None


def test_key_to_terminal_valid_keys(controller):
    controller.config["layout"] = "default"
    for key in range(TOTAL_KEYS - 1):  # 0–13
        result = controller._key_to_terminal(key)
        assert result is not None, f"Key {key} returned None, expected a terminal name"


def test_terminal_to_active_slot_returns_first_key(controller):
    controller.config["layout"] = "default"
    assert controller._terminal_to_active_slot("T1") == 0
    assert controller._terminal_to_active_slot("T2") == 1


# --- Grid geometry ---

def test_grid_rect_corners(controller):
    screen = controller.screen
    sx, sy, sw, sh = screen["x"], screen["y"], screen["w"], screen["h"]

    rect0 = controller._grid_rect(0)
    assert rect0["x"] == sx
    assert rect0["y"] == sy

    rect4 = controller._grid_rect(4)
    assert rect4["x"] + rect4["w"] == sx + sw

    rect14 = controller._grid_rect(ENTER_KEY_INDEX)
    assert rect14["x"] + rect14["w"] == sx + sw
    # Allow ±1 for int truncation rounding in grid calculations
    assert abs((rect14["y"] + rect14["h"]) - (sy + sh)) <= 1


def test_grid_rect_dimensions(controller):
    screen = controller.screen
    cell_w = screen["w"] / COLS
    cell_h = screen["h"] / ROWS

    for key in range(TOTAL_KEYS):
        rect = controller._grid_rect(key)
        assert abs(rect["w"] - cell_w) < 1, f"Key {key} width {rect['w']} != {cell_w}"
        assert abs(rect["h"] - cell_h) < 1, f"Key {key} height {rect['h']} != {cell_h}"


def test_get_terminal_rect_merged(controller):
    controller.config["layout"] = "quad"
    screen = controller.screen

    # In "quad" layout, first 4 keys (0,1,5,6) are "T1" — a 2x2 merged zone
    rect = controller._get_terminal_rect("T1")

    expected_w = (screen["w"] / COLS) * 2
    expected_h = (screen["h"] / ROWS) * 2

    assert abs(rect["w"] - expected_w) < 2, f"T1 width {rect['w']} != {expected_w}"
    assert abs(rect["h"] - expected_h) < 2, f"T1 height {rect['h']} != {expected_h}"


def test_layout_switch(controller):
    controller.config["layout"] = "default"
    default_layout = controller._get_layout()

    controller.config["layout"] = "quad"
    quad_layout = controller._get_layout()

    assert default_layout != quad_layout
    assert quad_layout == LAYOUTS["quad"]
