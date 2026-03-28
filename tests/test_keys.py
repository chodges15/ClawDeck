"""Tests for keystroke formatting and font picking."""
import pytest
from main import _format_keystroke

# Modifier flag masks (from main.py)
MOD_COMMAND = 1 << 20   # 0x100000
MOD_SHIFT   = 1 << 17   # 0x20000
MOD_CONTROL = 1 << 18   # 0x40000
MOD_OPTION  = 1 << 19   # 0x80000


# ─── _format_keystroke ───────────────────────────────────────────────────────

def test_format_keystroke_letter():
    # key_code 0 = "A", no modifiers
    result = _format_keystroke(0, 0)
    assert result == "A"


def test_format_keystroke_with_command():
    # Command flag should inject "⌘" before the key name
    result = _format_keystroke(0, MOD_COMMAND)
    assert "⌘" in result
    assert "A" in result


def test_format_keystroke_with_shift():
    # Shift flag should inject "⇧" before the key name
    result = _format_keystroke(0, MOD_SHIFT)
    assert "⇧" in result
    assert "A" in result


def test_format_keystroke_fn_key():
    # key_code 63 maps to the string "fn"
    result = _format_keystroke(63, 0)
    assert result == "fn"


# ─── _pick_font ──────────────────────────────────────────────────────────────

def test_pick_font_short_label(controller):
    controller.font_sm = "sm"
    controller.font_md = "md"
    controller.font_lg = "lg"

    assert controller._pick_font("A") == "lg"     # len 1
    assert controller._pick_font("AB") == "lg"    # len 2


def test_pick_font_medium_label(controller):
    controller.font_sm = "sm"
    controller.font_md = "md"
    controller.font_lg = "lg"

    assert controller._pick_font("ABC") == "md"   # len 3
    assert controller._pick_font("ABCD") == "md"  # len 4


def test_pick_font_long_label(controller):
    controller.font_sm = "sm"
    controller.font_md = "md"
    controller.font_lg = "lg"

    assert controller._pick_font("ABCDE") == "sm"      # len 5
    assert controller._pick_font("ABCDEFGH") == "sm"   # len 8
