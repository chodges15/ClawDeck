import pytest
from clawdeck.config import hex_to_rgb as _hex_to_rgb, rgb_to_hex as _rgb_to_hex


def test_rgb_to_hex_standard():
    assert _rgb_to_hex((255, 176, 0)) == "#ffb000"
    assert _rgb_to_hex((0, 0, 0)) == "#000000"
    assert _rgb_to_hex((255, 255, 255)) == "#ffffff"


def test_rgb_to_hex_primary_colors():
    assert _rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert _rgb_to_hex((0, 255, 0)) == "#00ff00"
    assert _rgb_to_hex((0, 0, 255)) == "#0000ff"


def test_hex_to_rgb_with_hash():
    assert _hex_to_rgb("#ffb000") == (255, 176, 0)


def test_hex_to_rgb_without_hash():
    assert _hex_to_rgb("ffb000") == (255, 176, 0)


def test_hex_to_rgb_uppercase():
    assert _hex_to_rgb("#FFB000") == (255, 176, 0)


def test_roundtrip():
    original = (123, 45, 67)
    assert _hex_to_rgb(_rgb_to_hex(original)) == original


def test_color_method_returns_config_value(controller):
    controller.config["colors"]["active"] = "#ff0000"
    result = controller._color("active", (0, 0, 0))
    assert result == (255, 0, 0)


def test_color_method_fallback(controller):
    fallback = (1, 2, 3)
    result = controller._color("nonexistent_key_xyz", fallback)
    assert result == fallback
