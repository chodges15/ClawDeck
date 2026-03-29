"""Shared fixtures for ClawDeck tests.

main.py imports macOS-only modules (Quartz, StreamDeck) at module level.
Provide targeted stubs before importing the module so tests can run inside
the sandbox while still exercising rendering and integration contracts.
"""

import copy
import json
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from unittest.mock import MagicMock, patch

import pytest

try:
    import PIL
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - repo env should have Pillow
    PIL = MagicMock()
    Image = MagicMock()
    ImageDraw = MagicMock()
    ImageFont = MagicMock()


class StubPILHelper:
    """Minimal PILHelper stand-in used by tests."""

    @staticmethod
    def create_image(deck, background=(0, 0, 0)):
        size = getattr(deck, "button_size", (72, 72)) if deck else (72, 72)
        return Image.new("RGB", size, background)

    @staticmethod
    def to_native_format(deck, image):
        return image


def _make_quartz_module():
    """Build a deterministic Quartz stub module for tests."""
    module = ModuleType("Quartz")
    module.kCGEventFlagsChanged = 12
    module.kCGEventKeyDown = 10
    module.kCGHIDEventTap = 0
    module.kCGHeadInsertEventTap = 0
    module.kCGSessionEventTap = 1

    def create_keyboard_event(_, key_code, key_down):
        return {"key_code": key_code, "key_down": key_down, "flags": 0}

    def get_flags(event):
        if isinstance(event, dict):
            return event.get("flags", 0)
        return getattr(event, "flags", 0)

    def get_integer_value(event, _field):
        if isinstance(event, dict):
            return event.get("key_code", 0)
        return getattr(event, "key_code", 0)

    def set_flags(event, flags):
        if isinstance(event, dict):
            event["flags"] = flags
        else:
            event.flags = flags

    module.CGEventCreateKeyboardEvent = MagicMock(side_effect=create_keyboard_event)
    module.CGEventGetFlags = MagicMock(side_effect=get_flags)
    module.CGEventGetIntegerValueField = MagicMock(side_effect=get_integer_value)
    module.CGEventPost = MagicMock()
    module.CGEventSetFlags = MagicMock(side_effect=set_flags)
    module.CGEventTapCreate = MagicMock(return_value=object())
    return module


def _make_corefoundation_module():
    """Build a deterministic CoreFoundation stub module for tests."""
    module = ModuleType("CoreFoundation")
    module.kCFRunLoopCommonModes = "kCFRunLoopCommonModes"
    module.CFMachPortCreateRunLoopSource = MagicMock(return_value="source")
    module.CFRunLoopAddSource = MagicMock()
    module.CFRunLoopGetCurrent = MagicMock(return_value="loop")
    module.CFRunLoopRemoveSource = MagicMock()
    module.CFRunLoopRun = MagicMock()
    module.CFRunLoopStop = MagicMock()
    return module


def _install_stub_modules():
    """Install test doubles before importing modules that expect macOS deps."""
    quartz = _make_quartz_module()
    core_foundation = _make_corefoundation_module()
    streamdeck = ModuleType("StreamDeck")
    device_manager = ModuleType("StreamDeck.DeviceManager")
    image_helpers = ModuleType("StreamDeck.ImageHelpers")
    rumps = ModuleType("rumps")

    device_manager.DeviceManager = MagicMock(name="DeviceManager")
    image_helpers.PILHelper = StubPILHelper
    rumps.App = MagicMock(name="App")

    sys.modules["Quartz"] = quartz
    sys.modules["CoreFoundation"] = core_foundation
    sys.modules["StreamDeck"] = streamdeck
    sys.modules["StreamDeck.DeviceManager"] = device_manager
    sys.modules["StreamDeck.ImageHelpers"] = image_helpers
    sys.modules["rumps"] = rumps
    sys.modules.setdefault("PIL", PIL)
    sys.modules.setdefault("PIL.Image", Image)
    sys.modules.setdefault("PIL.ImageDraw", ImageDraw)
    sys.modules.setdefault("PIL.ImageFont", ImageFont)


_install_stub_modules()

from clawdeck.config import CONFIG_DEFAULTS, hex_to_rgb, rgb_to_hex  # noqa: E402
from clawdeck.constants import (  # noqa: E402
    COLS,
    ROWS,
    KEYS_PER_ROW,
    NUM_SESSIONS,
    SESSIONS,
    TOTAL_KEYS,
    MODE_ROW,
    MODE_NAV,
    COLOR_BG_ACTIVE,
    COLOR_BG_IDLE,
    COLOR_BG_WORKING,
    COLOR_BG_PERMISSION,
    COLOR_BG_DEFAULT,
    COLOR_FG_DEFAULT,
    NAV_BUTTON_STYLES,
)
from clawdeck.controller import DeckController  # noqa: E402
from clawdeck.input import format_keystroke  # noqa: E402
import clawdeck.controller as controller_module  # noqa: E402
import clawdeck.status as status_module  # noqa: E402


class FakeDeck:
    """In-memory Stream Deck test double that captures rendered output."""

    def __init__(self, key_count=TOTAL_KEYS, button_size=(72, 72), deck_name="Fake Deck"):
        """Initialize a fake deck with configurable geometry and metadata."""
        self._key_count = key_count
        self.button_size = button_size
        self._deck_name = deck_name
        self.images = {}
        self.callback = None
        self.brightness = None
        self.opened = False
        self.closed = False
        self.reset_calls = 0

    def open(self):
        self.opened = True

    def reset(self):
        self.reset_calls += 1

    def close(self):
        self.closed = True

    def deck_type(self):
        return self._deck_name

    def key_count(self):
        return self._key_count

    def set_brightness(self, value):
        self.brightness = value

    def set_key_callback(self, callback):
        self.callback = callback

    def set_key_image(self, key, image):
        self.images[key] = image


def pytest_configure(config):
    """Register custom markers used by the test suite."""
    config.addinivalue_line(
        "markers",
        "mac_integration: opt-in smoke tests for live macOS integrations and hardware",
    )


def pytest_collection_modifyitems(config, items):
    """Skip macOS smoke tests on non-Darwin platforms."""
    if sys.platform == "darwin":
        return

    skip = pytest.mark.skip(reason="macOS smoke tests require Darwin")
    for item in items:
        if item.get_closest_marker("mac_integration"):
            item.add_marker(skip)


@pytest.fixture
def controller():
    """Provide a controller with config and font loading stubbed for tests."""
    default_font = ImageFont.load_default() if hasattr(ImageFont, "load_default") else None
    with patch("clawdeck.controller.ConfigStore.load", return_value=copy.deepcopy(CONFIG_DEFAULTS)):
        with patch("clawdeck.render.DeckRenderer._init_fonts"):
            ctrl = DeckController()
    ctrl.config = copy.deepcopy(CONFIG_DEFAULTS)
    ctrl.renderer.font_xs = default_font
    ctrl.renderer.font_sm = default_font
    ctrl.renderer.font_md = default_font
    ctrl.renderer.font_lg = default_font
    return ctrl


@pytest.fixture
def default_config():
    """Return a deep-copied default config for test mutation."""
    return copy.deepcopy(CONFIG_DEFAULTS)


@pytest.fixture
def fake_deck():
    """Return a fresh fake Stream Deck device."""
    return FakeDeck()


@pytest.fixture
def subprocess_result():
    """Build simple subprocess result objects for boundary tests."""
    def make(stdout="", stderr="", returncode=0):
        return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)

    return make


@pytest.fixture
def status_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(status_module, "STATUS_DIR", str(tmp_path))
    monkeypatch.setattr(controller_module, "STATUS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def require_mac_smoke():
    if os.environ.get("CLAWDECK_MAC_SMOKE") != "1":
        pytest.skip("Set CLAWDECK_MAC_SMOKE=1 to run macOS smoke tests")


@pytest.fixture
def require_deck_smoke():
    if os.environ.get("CLAWDECK_DECK_SMOKE") != "1":
        pytest.skip("Set CLAWDECK_DECK_SMOKE=1 to run Stream Deck smoke tests")


@pytest.fixture
def claude_hook_common_fields():
    """Return stable fake common fields used by Claude hook payload fixtures."""
    return {
        "session_id": "session-test-001",
        "transcript_path": "/Users/tester/.claude/projects/demo-project/transcript.jsonl",
        "cwd": "/Users/tester/src/demo-project",
        "permission_mode": "default",
    }


@pytest.fixture
def claude_hook_payloads(claude_hook_common_fields):
    """Return docs-inspired Claude hook payloads with stable fake values."""
    common = copy.deepcopy(claude_hook_common_fields)

    payloads = {
        "pre_tool_use": {
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git status --short"},
            "tool_use_id": "toolu_test_pre_001",
        },
        "permission_request": {
            **common,
            "hook_event_name": "PermissionRequest",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/Users/tester/src/demo-project/app.py",
                "content": "print('hello')\n",
            },
            "tool_use_id": "toolu_test_perm_001",
            "permission_suggestions": [
                {
                    "label": "Allow once",
                    "value": "allow_once",
                },
                {
                    "label": "Deny",
                    "value": "deny",
                },
            ],
        },
        "post_tool_use": {
            **common,
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/Users/tester/src/demo-project/README.md"},
            "tool_response": {
                "content": "Demo project README",
            },
            "tool_use_id": "toolu_test_post_001",
        },
        "notification": {
            **common,
            "hook_event_name": "Notification",
            "message": "Claude needs permission to write app.py",
            "title": "Permission required",
            "notification_type": "permission_prompt",
        },
        "cwd_changed": {
            **common,
            "hook_event_name": "CwdChanged",
            "cwd": "/Users/tester/src/demo-project/packages/api",
            "old_cwd": "/Users/tester/src/demo-project",
            "new_cwd": "/Users/tester/src/demo-project/packages/api",
        },
    }

    # Keep fixture values valid JSON so hook tests can pipe them directly to stdin.
    json.dumps(payloads)
    return payloads
