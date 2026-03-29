"""Tests for macOS host-boundary subprocess and device contracts."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

import clawdeck.controller as controller_module
import clawdeck.host as host_module
import clawdeck.input as input_module
from tests.conftest import FakeDeck


def test_check_accessibility_success(controller, subprocess_result):
    with patch("clawdeck.host.subprocess.run", return_value=subprocess_result()) as run_mock:
        assert controller._check_accessibility() is True

    run_mock.assert_called_once_with(
        [
            "osascript",
            "-e",
            'tell application "System Events" to get name of first process',
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )


def test_check_accessibility_opens_settings_and_retries(controller, subprocess_result):
    with patch(
        "clawdeck.host.subprocess.run",
        side_effect=[
            subprocess_result(returncode=1),
            subprocess_result(),
            subprocess_result(returncode=0),
        ],
    ) as run_mock:
        with patch("builtins.input", return_value="") as input_mock:
            assert controller._check_accessibility() is True

    assert run_mock.call_args_list == [
        call(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first process',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        ),
        call(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            capture_output=True,
        ),
        call(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first process',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        ),
    ]
    input_mock.assert_called_once()


def test_get_iterm_sessions_parses_session_tab_and_window_metadata(controller, subprocess_result):
    stdout = "\n".join(
        [
            "\x1f".join(
                [
                    "Claude T1",
                    "/dev/ttys001",
                    "T1",
                    "1",
                    "session-1",
                    "Default",
                    "true",
                    "false",
                    "120",
                    "40",
                    "101",
                    "1",
                    "Claude Workspace",
                    "true",
                ]
            ),
            "\x1f".join(
                [
                    "Claude T2",
                    "ttys002",
                    "T2",
                    "2",
                    "session-2",
                    "Hotkey",
                    "false",
                    "true",
                    "80",
                    "24",
                    "102",
                    "2",
                    "Scratch",
                    "false",
                ]
            ),
            "bad-line",
            "\x1f".join(["", "/dev/ttys003", "T3", "3", "session-3", "", "false", "false", "80", "24", "103", "3", "Unused", "false"]),
        ]
    )
    with patch("clawdeck.host.subprocess.run", return_value=subprocess_result(stdout=stdout)) as run_mock:
        sessions = controller._get_iterm_sessions()

    assert sessions == [
        {
            "name": "Claude T1",
            "tty": "ttys001",
            "tab_title": "T1",
            "tab_index": 1,
            "session_id": "session-1",
            "profile_name": "Default",
            "is_processing": True,
            "is_at_shell_prompt": False,
            "columns": 120,
            "rows": 40,
            "window_id": 101,
            "window_index": 1,
            "window_name": "Claude Workspace",
            "window_frontmost": True,
        },
        {
            "name": "Claude T2",
            "tty": "ttys002",
            "tab_title": "T2",
            "tab_index": 2,
            "session_id": "session-2",
            "profile_name": "Hotkey",
            "is_processing": False,
            "is_at_shell_prompt": True,
            "columns": 80,
            "rows": 24,
            "window_id": 102,
            "window_index": 2,
            "window_name": "Scratch",
            "window_frontmost": False,
        },
    ]
    args, kwargs = run_mock.call_args
    assert args[0][:2] == ["osascript", "-e"]
    assert "repeat with s in sessions of t" in args[0][2]
    assert 'tell application "iTerm2"' in args[0][2]
    assert 'set sessionName to ""' in args[0][2]
    assert "set tabTitle to title of t" in args[0][2]
    assert "set profileName to profile name of s" in args[0][2]
    assert 'if sessionName is not "" and sessionTTY is not "" then' in args[0][2]
    assert "set fieldSep to ASCII character 31" in args[0][2]
    assert kwargs == {"capture_output": True, "text": True, "timeout": 10}


def test_resolve_tty_cwd_uses_last_shell_pid(controller, subprocess_result):
    with patch(
        "clawdeck.host.subprocess.run",
        side_effect=[
            subprocess_result(stdout="101 python\n202 -zsh\n303 bash\n"),
            subprocess_result(stdout="p303\nn/Users/chodges/src/ClawDeck\n"),
        ],
    ) as run_mock:
        cwd = controller._resolve_tty_cwd("ttys001")

    assert cwd == "/Users/chodges/src/ClawDeck"
    assert run_mock.call_args_list == [
        call(
            ["ps", "-t", "ttys001", "-o", "pid=,comm="],
            capture_output=True,
            text=True,
            timeout=5,
        ),
        call(
            ["lsof", "-a", "-p", "303", "-d", "cwd", "-Fn"],
            capture_output=True,
            text=True,
            timeout=5,
        ),
    ]


def test_frontmost_session_name_strips_output(controller, subprocess_result):
    with patch(
        "clawdeck.host.subprocess.run",
        return_value=subprocess_result(stdout=" Claude T2 \n"),
    ) as run_mock:
        assert controller._frontmost_session_name() == "Claude T2"

    args, kwargs = run_mock.call_args
    assert args[0][:2] == ["osascript", "-e"]
    assert 'current session of current tab of current window' in args[0][2]
    assert kwargs == {"capture_output": True, "text": True, "timeout": 5}


def test_get_frontmost_slot_matches_tab_title(controller, subprocess_result):
    controller.config["session_map"] = {"T1": "T1", "T2": "T2", "T3": "T3"}

    with patch(
        "clawdeck.host.subprocess.run",
        return_value=subprocess_result(stdout="T1\x1f~/src/ClawDeck (-zsh)\n"),
    ) as run_mock:
        assert controller._get_frontmost_slot() == controller._session_label_key("T1")

    args, kwargs = run_mock.call_args
    assert args[0][:2] == ["osascript", "-e"]
    assert 'title of current tab of current window' in args[0][2]
    assert 'name of current session of current tab of current window' in args[0][2]
    assert kwargs == {"capture_output": True, "text": True, "timeout": 5}


def test_activate_session_matches_pattern_and_updates_active_slot(controller, subprocess_result):
    controller.config["session_map"]["T2"] = "Alpha Worker"

    with patch(
        "clawdeck.host.subprocess.run",
        return_value=subprocess_result(stdout="ok\n"),
    ) as run_mock:
        assert controller._activate_session("T2") is True

    assert controller.active_slot == controller._session_label_key("T2")
    args, kwargs = run_mock.call_args
    assert args[0][:2] == ["osascript", "-e"]
    assert 'tell application "iTerm2"' in args[0][2]
    assert 'set matchPattern to "Alpha Worker"' in args[0][2]
    assert "set tabTitle to title of t" in args[0][2]
    assert "tabTitle contains matchPattern or sessionName contains matchPattern" in args[0][2]
    assert "tell t to select" in args[0][2]
    assert "reveal hotkey window" in args[0][2]
    assert kwargs == {"capture_output": True, "text": True, "timeout": 10}


def test_activate_session_returns_false_when_blank_entry_is_intentionally_unmapped(controller):
    controller.config["session_map"] = {"T1": "", "T2": "alpha", "T3": ""}

    with patch("clawdeck.host.subprocess.run") as run_mock:
        assert controller._activate_session("T1") is False

    run_mock.assert_not_called()


def test_approve_permission_uses_tty_path_and_closes_fd_on_error(controller):
    controller.slot_tty = {0: "ttys009"}

    with patch("clawdeck.host.os.open", return_value=11) as open_mock:
        with patch("clawdeck.host.os.write", side_effect=OSError("blocked")) as write_mock:
            with patch("clawdeck.host.os.close") as close_mock:
                assert controller._approve_permission("T1") is False

    open_mock.assert_called_once_with("/dev/ttys009", host_module.os.O_WRONLY | host_module.os.O_NOCTTY)
    write_mock.assert_called_once_with(11, b"y\n")
    close_mock.assert_called_once_with(11)


def test_trigger_mic_fn_posts_fn_key_twice(controller):
    controller.config["mic_command"] = "fn"

    with patch("clawdeck.input.CGEventCreateKeyboardEvent", side_effect=lambda _, code, down: (code, down)):
        with patch("clawdeck.input.CGEventPost") as post_mock:
            with patch("clawdeck.input.time.sleep") as sleep_mock:
                controller._trigger_mic()

    assert post_mock.call_args_list == [
        call(input_module.kCGHIDEventTap, (input_module.FN_KEY_CODE, True)),
        call(input_module.kCGHIDEventTap, (input_module.FN_KEY_CODE, False)),
        call(input_module.kCGHIDEventTap, (input_module.FN_KEY_CODE, True)),
        call(input_module.kCGHIDEventTap, (input_module.FN_KEY_CODE, False)),
    ]
    assert sleep_mock.call_args_list == [call(0.05), call(0.05)]


def test_trigger_mic_keystroke_applies_flags(controller):
    controller.config["mic_command"] = {
        "type": "keystroke",
        "key_code": 7,
        "flags": input_module.MOD_COMMAND | input_module.MOD_SHIFT,
    }

    with patch("clawdeck.input.CGEventCreateKeyboardEvent", side_effect=lambda _, code, down: {"code": code, "down": down}) as create_mock:
        with patch("clawdeck.input.CGEventSetFlags") as set_flags_mock:
            with patch("clawdeck.input.CGEventPost") as post_mock:
                controller._trigger_mic()

    assert create_mock.call_args_list == [call(None, 7, True), call(None, 7, False)]
    assert set_flags_mock.call_count == 2
    assert post_mock.call_count == 2


def test_trigger_mic_shell_command_uses_popen(controller):
    controller.config["mic_command"] = "shortcuts run Whisprflow"

    with patch("clawdeck.input.subprocess.Popen") as popen_mock:
        controller._trigger_mic()

    popen_mock.assert_called_once_with(
        "shortcuts run Whisprflow",
        shell=True,
        stdout=input_module.subprocess.DEVNULL,
        stderr=input_module.subprocess.DEVNULL,
    )


def test_learn_keystroke_returns_when_event_tap_cannot_be_created(controller):
    with patch("clawdeck.input.CGEventTapCreate", return_value=None):
        with patch.object(controller.config_store, "save") as save_mock:
            controller._learn_keystroke()

    save_mock.assert_not_called()


def test_learn_keystroke_captures_key_and_saves_config(controller):
    captured = {}

    def fake_create(_tap, _place, _options, _mask, callback, _refcon):
        captured["callback"] = callback
        return object()

    def fake_runloop():
        event = {"key_code": 0, "flags": input_module.MOD_COMMAND | input_module.MOD_SHIFT}
        captured["callback"](None, input_module.kCGEventKeyDown, event, None)

    with patch("clawdeck.input.CGEventTapCreate", side_effect=fake_create):
        with patch.object(input_module.CoreFoundation, "CFRunLoopRun", side_effect=fake_runloop):
            with patch.object(controller.config_store, "save") as save_mock:
                controller._learn_keystroke()

    assert controller.config["mic_command"] == {
        "type": "keystroke",
        "key_code": 0,
        "flags": input_module.MOD_COMMAND | input_module.MOD_SHIFT,
        "label": "⇧⌘A",
    }
    save_mock.assert_called_once_with(controller.config)


@pytest.mark.parametrize(
    ("key_name", "expected_script"),
    [
        ("Return", 'tell application "System Events" to key code 36'),
        ("Up", 'tell application "System Events" to key code 126'),
        ("1", 'tell application "System Events" to keystroke "1"'),
    ],
)
def test_send_key_uses_expected_system_events_script(controller, key_name, expected_script):
    with patch("clawdeck.input.subprocess.run") as run_mock:
        controller._send_key(key_name)

    run_mock.assert_called_once_with(["osascript", "-e", expected_script], capture_output=True)


def test_clear_status_dir_unlinks_files_and_falls_back_to_rm(controller, status_dir, monkeypatch):
    removable = status_dir / "ok.json"
    locked = status_dir / "locked.json"
    removable.write_text("{}")
    locked.write_text("{}")
    real_unlink = Path.unlink

    def selective_unlink(path_obj):
        if path_obj.name == "locked.json":
            raise PermissionError("locked")
        return real_unlink(path_obj)

    monkeypatch.setattr(controller_module.Path, "unlink", selective_unlink, raising=False)

    with patch("clawdeck.controller.subprocess.run") as run_mock:
        controller._clear_status_dir()

    assert not removable.exists()
    run_mock.assert_called_once_with(["rm", "-f", str(locked)], capture_output=True)


def test_run_exits_when_no_stream_deck_available(controller):
    manager = SimpleNamespace(enumerate=lambda: [])

    with patch.object(controller, "_check_accessibility") as access_mock:
        with patch("clawdeck.controller.DeviceManager", return_value=manager):
            with pytest.raises(SystemExit):
                controller.run()

    access_mock.assert_called_once_with()


def test_run_initializes_first_working_device_and_shuts_down_cleanly(controller):
    bad_dev = MagicMock()
    bad_dev.open.side_effect = RuntimeError("busy")
    good_dev = FakeDeck()
    manager = SimpleNamespace(enumerate=lambda: [bad_dev, good_dev])
    threads = []

    class FakeThread:
        """Thread double that records startup without spawning work."""

        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon
            self.started = False
            threads.append(self)

        def start(self):
            self.started = True

    with patch.object(controller, "_check_accessibility"):
        with patch.object(controller, "_build_tty_map") as build_mock:
            with patch.object(controller, "_clear_status_dir") as clear_mock:
                with patch.object(controller, "_update_all_buttons") as update_mock:
                    with patch.object(controller, "_start_settings_server", return_value=19830):
                        with patch("clawdeck.controller.DeviceManager", return_value=manager):
                            with patch("clawdeck.controller.threading.Thread", side_effect=FakeThread):
                                with patch("builtins.input", side_effect=EOFError):
                                    controller.run()

    bad_dev.open.assert_called_once_with()
    assert good_dev.opened is True
    assert good_dev.brightness == controller.config["brightness"]
    assert good_dev.callback == controller._on_key_change
    assert good_dev.reset_calls == 2
    assert good_dev.closed is True
    build_mock.assert_called_once_with()
    clear_mock.assert_called_once_with()
    update_mock.assert_called_once_with()
    assert len(threads) == 1
    assert threads[0].daemon is True
    assert threads[0].started is True
