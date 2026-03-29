"""Tests for controller key handling, commands, and poll-loop behavior."""

from unittest.mock import MagicMock, patch

import pytest

import clawdeck.controller as controller_module
from clawdeck.constants import MODE_NAV, MODE_ROW


def test_handle_key_hold_activates_session_updates_buttons_and_triggers_mic(controller, monkeypatch):
    controller.mode = MODE_ROW
    controller.config["hold_threshold"] = 0.5
    monkeypatch.setattr(controller_module.time, "time", lambda: 10.0)
    controller._handle_key(0, True)

    with patch.object(controller, "_activate_session") as activate_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            with patch.object(controller, "_trigger_mic") as mic_mock:
                monkeypatch.setattr(controller_module.time, "time", lambda: 10.8)
                controller._handle_key(0, False)

    activate_mock.assert_called_once_with("T1")
    update_mock.assert_called_once_with()
    mic_mock.assert_called_once_with()


def test_handle_key_press_ignores_non_label_keys_in_row_mode(controller):
    controller.mode = MODE_ROW

    with patch.object(controller, "_handle_info_key") as info_mock:
        controller._handle_key(1, True)

    info_mock.assert_not_called()


def test_handle_key_release_routes_dir_button_to_info_handler(controller):
    controller.mode = MODE_ROW

    with patch.object(controller, "_handle_info_key") as info_mock:
        controller._handle_key(1, False)

    info_mock.assert_called_once_with("T1", 0)


def test_handle_key_release_routes_other_info_buttons_to_info_handler(controller):
    controller.mode = MODE_ROW

    with patch.object(controller, "_handle_info_key") as info_mock:
        controller._handle_key(2, False)

    info_mock.assert_called_once_with("T1", 1)


def test_handle_key_in_nav_mode_routes_only_pressed_events(controller):
    controller.mode = MODE_NAV

    with patch.object(controller, "_handle_nav_key") as nav_mock:
        controller._handle_key(7, True)
        controller._handle_key(7, False)

    nav_mock.assert_called_once_with(7)


def test_handle_key_returns_when_session_resolution_fails(controller):
    controller.mode = MODE_ROW

    with patch.object(controller, "_key_is_label", return_value=True):
        with patch.object(controller, "_key_to_session", return_value=None):
            with patch.object(controller, "_handle_row_key") as row_mock:
                controller._handle_key(0, True)

    row_mock.assert_not_called()


def test_handle_key_release_without_press_is_ignored(controller):
    controller.mode = MODE_ROW

    with patch.object(controller, "_handle_row_key") as row_mock:
        controller._handle_key(0, False)

    row_mock.assert_not_called()


def test_handle_key_short_press_routes_to_row_handler(controller, monkeypatch):
    controller.mode = MODE_ROW
    controller.config["hold_threshold"] = 0.5
    monkeypatch.setattr(controller_module.time, "time", lambda: 10.0)
    controller._handle_key(0, True)

    with patch.object(controller, "_handle_row_key") as row_mock:
        monkeypatch.setattr(controller_module.time, "time", lambda: 10.1)
        controller._handle_key(0, False)

    row_mock.assert_called_once_with("T1")


def test_handle_row_key_permission_approves_without_navigation(controller):
    controller.slot_status = {0: "permission"}

    with patch.object(controller, "_approve_permission") as approve_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_row_key("T1")

    approve_mock.assert_called_once_with("T1")
    update_mock.assert_not_called()


def test_handle_row_key_active_slot_enters_nav_mode(controller):
    controller.active_slot = 0

    with patch.object(controller, "_activate_session", return_value=True) as activate_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_row_key("T1")

    assert controller.mode == MODE_NAV
    activate_mock.assert_called_once_with("T1")
    update_mock.assert_called_once_with()


def test_handle_row_key_inactive_slot_updates_only_when_activation_succeeds(controller):
    controller.active_slot = None

    with patch.object(controller, "_activate_session", return_value=False) as activate_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_row_key("T2")

    activate_mock.assert_called_once_with("T2")
    update_mock.assert_not_called()


def test_handle_row_key_inactive_slot_updates_when_activation_succeeds(controller):
    controller.active_slot = None

    with patch.object(controller, "_activate_session", return_value=True) as activate_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_row_key("T3")

    activate_mock.assert_called_once_with("T3")
    update_mock.assert_called_once_with()


def test_handle_info_key_dir_button_opens_vscode_for_hook_cwd(controller):
    controller.slot_hook_cwd = {0: "/Users/tester/src/demo-project"}
    controller.slot_cwd = {0: "/"}

    with patch.object(controller, "_open_vscode") as open_mock:
        controller._handle_info_key("T1", 0)

    open_mock.assert_called_once_with("/Users/tester/src/demo-project")


def test_handle_info_key_dir_button_does_not_fallback_to_tty_cwd(controller):
    controller.slot_hook_cwd = {}
    controller.slot_cwd = {0: "/Users/tester/src/shell-root"}

    with patch.object(controller, "_open_vscode") as open_mock:
        controller._handle_info_key("T1", 0)

    open_mock.assert_not_called()


def test_handle_info_key_diff_button_opens_kaleidoscope_review(controller):
    controller.slot_hook_cwd = {0: "/Users/tester/src/demo-project"}

    with patch.object(controller, "_open_kaleidoscope_review") as review_mock:
        review_mock.return_value = "opened"
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_info_key("T1", 2)

    review_mock.assert_called_once_with("/Users/tester/src/demo-project")
    assert controller.info_feedback[(0, 2)]["subtitle"] == "opening"
    update_mock.assert_called_once_with()


def test_handle_info_key_diff_button_shows_no_path_feedback(controller):
    controller.slot_hook_cwd = {}

    with patch.object(controller, "_update_all_buttons") as update_mock:
        controller._handle_info_key("T1", 2)

    assert controller.info_feedback[(0, 2)]["subtitle"] == "no path"
    update_mock.assert_called_once_with()


def test_handle_info_key_diff_button_does_not_fallback_to_tty_cwd(controller):
    controller.slot_hook_cwd = {}
    controller.slot_cwd = {0: "/Users/tester/src/shell-root"}

    with patch.object(controller, "_open_kaleidoscope_review") as review_mock:
        with patch.object(controller, "_update_all_buttons") as update_mock:
            controller._handle_info_key("T1", 2)

    review_mock.assert_not_called()
    assert controller.info_feedback[(0, 2)]["subtitle"] == "no path"
    update_mock.assert_called_once_with()


def test_handle_info_key_branch_button_does_nothing(controller):
    controller.slot_hook_cwd = {0: "/Users/tester/src/demo-project"}

    with patch.object(controller, "_open_vscode") as open_mock:
        with patch.object(controller, "_open_kaleidoscope_review") as review_mock:
            with patch.object(controller, "_write_session_text") as write_mock:
                controller._handle_info_key("T1", 1)

    open_mock.assert_not_called()
    review_mock.assert_not_called()
    write_mock.assert_not_called()


def test_handle_info_key_play_button_writes_continue_to_tty(controller):
    with patch.object(controller, "_write_session_text") as write_mock:
        controller._handle_info_key("T1", 3)

    write_mock.assert_called_once_with("T1", "continue\n")


def test_clear_expired_info_feedback_removes_expired_entries(controller):
    controller.info_feedback = {
        (0, 2): {"label": "DIFF", "subtitle": "clean", "expires_at": 10.0},
        (5, 2): {"label": "DIFF", "subtitle": "opening", "expires_at": 30.0},
    }

    assert controller._clear_expired_info_feedback(now=15.0) is True
    assert controller.info_feedback == {
        (5, 2): {"label": "DIFF", "subtitle": "opening", "expires_at": 30.0}
    }


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (0, ("_send_key", "1")),
        (7, ("_send_key", "Up")),
        (10, ("_trigger_mic", None)),
        (14, ("_send_key", "Return")),
    ],
)
def test_handle_nav_key_dispatches_expected_action(controller, key, expected):
    controller.mode = MODE_NAV
    method_name, arg = expected

    with patch.object(controller, "_send_key") as send_mock:
        with patch.object(controller, "_trigger_mic") as mic_mock:
            controller._handle_nav_key(key)

    if method_name == "_send_key":
        send_mock.assert_called_once_with(arg)
        mic_mock.assert_not_called()
    else:
        mic_mock.assert_called_once_with()
        send_mock.assert_not_called()


def test_handle_nav_key_back_returns_to_row_mode(controller):
    controller.mode = MODE_NAV

    with patch.object(controller, "_update_all_buttons") as update_mock:
        controller._handle_nav_key(9)

    assert controller.mode == MODE_ROW
    update_mock.assert_called_once_with()


def test_on_key_change_locks_and_forwards_event(controller):
    with patch.object(controller, "_handle_key") as handle_mock:
        controller._on_key_change(None, 0, True)

    handle_mock.assert_called_once_with(0, True)


def test_handle_command_brightness_updates_config_and_deck(controller, fake_deck):
    controller.deck = fake_deck

    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("brightness 42")

    assert controller.config["brightness"] == 42
    assert fake_deck.brightness == 42
    save_mock.assert_called_once_with()


def test_handle_command_mic_learn_calls_capture(controller):
    with patch.object(controller, "_learn_keystroke") as learn_mock:
        controller._handle_command("mic learn")

    learn_mock.assert_called_once_with()


def test_handle_command_help_prints_usage(controller, capsys):
    controller._handle_command("help")

    out = capsys.readouterr().out
    assert "brightness <0-100>" in out
    assert "quit" in out


def test_handle_command_blank_input_is_ignored(controller, capsys):
    controller._handle_command("")

    assert capsys.readouterr().out == ""


def test_handle_command_brightness_without_arg_prints_current_value(controller, capsys):
    controller.config["brightness"] = 88

    controller._handle_command("brightness")

    assert "brightness = 88" in capsys.readouterr().out


def test_handle_command_brightness_rejects_invalid_value(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("brightness 500")

    assert "Usage: brightness <0-100>" in capsys.readouterr().out
    save_mock.assert_not_called()


def test_handle_command_hold_updates_config(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("hold 1.25")

    assert controller.config["hold_threshold"] == 1.25
    assert "hold → 1.25s" in capsys.readouterr().out
    save_mock.assert_called_once_with()


def test_handle_command_hold_without_arg_prints_current_value(controller, capsys):
    controller.config["hold_threshold"] = 0.75

    controller._handle_command("hold")

    assert "hold = 0.75s" in capsys.readouterr().out


def test_handle_command_hold_rejects_invalid_value(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("hold nope")

    assert "Usage: hold <seconds>" in capsys.readouterr().out
    save_mock.assert_not_called()


def test_handle_command_hold_rejects_non_positive_value(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("hold 0")

    assert "Usage: hold <seconds>" in capsys.readouterr().out
    save_mock.assert_not_called()


def test_handle_command_poll_updates_config(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("poll 0.8")

    assert controller.config["poll_interval"] == 0.8
    assert "poll → 0.8s" in capsys.readouterr().out
    save_mock.assert_called_once_with()


def test_handle_command_poll_without_arg_prints_current_value(controller, capsys):
    controller.config["poll_interval"] = 0.4

    controller._handle_command("poll")

    assert "poll = 0.4s" in capsys.readouterr().out


def test_handle_command_poll_rejects_invalid_value(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("poll 0")

    assert "Usage: poll <seconds>" in capsys.readouterr().out
    save_mock.assert_not_called()


def test_handle_command_mic_without_arg_prints_keystroke_label(controller, capsys):
    controller.config["mic_command"] = {"label": "⌘M", "key_code": 46, "flags": 0}

    controller._handle_command("mic")

    assert "mic = ⌘M" in capsys.readouterr().out


def test_handle_command_mic_without_arg_prints_string_command(controller, capsys):
    controller.config["mic_command"] = "fn"

    controller._handle_command("mic")

    assert "mic = fn" in capsys.readouterr().out


def test_handle_command_mic_updates_string_command(controller, capsys):
    with patch.object(controller, "_save_config") as save_mock:
        controller._handle_command("mic shortcuts run Whisprflow")

    assert controller.config["mic_command"] == "shortcuts run Whisprflow"
    assert "mic → shortcuts run Whisprflow" in capsys.readouterr().out
    save_mock.assert_called_once_with()


def test_handle_command_settings_opens_browser_when_server_running(controller):
    controller._settings_port = 19830

    with patch("webbrowser.open") as open_mock:
        controller._handle_command("settings")

    open_mock.assert_called_once_with("http://127.0.0.1:19830/")


def test_handle_command_settings_prints_config_when_server_not_running(controller, capsys):
    controller._settings_port = None

    controller._handle_command("settings")

    out = capsys.readouterr().out
    assert "━━━ Settings ━━━" in out
    assert "brightness =" in out


def test_handle_command_quit_raises_system_exit(controller):
    with pytest.raises(SystemExit):
        controller._handle_command("quit")


def test_handle_command_unknown_prints_message(controller, capsys):
    controller._handle_command("nope")

    out = capsys.readouterr().out
    assert "Unknown command: nope" in out


def test_poll_active_loop_updates_buttons_when_row_state_changes(controller, monkeypatch):
    controller.running = True
    controller.mode = MODE_ROW
    controller.active_slot = None
    controller.slot_tty = {0: "ttys001"}
    controller.slot_cwd = {0: "/tmp/old"}
    controller.slot_hook_cwd = {0: "/Users/tester/src/project"}
    controller.slot_branch = {0: "main"}
    controller.slot_status = {}
    controller.slot_tool_info = {}
    controller._last_tty_refresh = 0
    controller._last_active_cwd_check = 0
    controller._last_blink_toggle = 0
    controller.blink_on = True

    monkeypatch.setattr(controller_module.time, "time", lambda: 100.0)

    def fake_build():
        controller.slot_cwd = {0: "/tmp/from-map"}

    def fake_read():
        controller.slot_status = {0: "permission"}
        controller.slot_hook_cwd = {0: "/Users/tester/src/project"}
        controller.slot_tool_info = {0: {"tool_name": "Bash", "tool_input": {"command": "pytest"}}}

    def fake_sleep(_interval):
        controller.running = False

    with patch.object(controller, "_build_tty_map", side_effect=fake_build) as build_mock:
        with patch.object(controller, "_get_frontmost_slot", return_value=0) as front_mock:
            with patch.object(controller, "_resolve_tty_cwd", return_value="/tmp/new") as cwd_mock:
                with patch.object(controller, "_resolve_git_branch", return_value="feature/new") as branch_mock:
                    with patch.object(controller, "_read_status_files", side_effect=fake_read) as read_mock:
                        with patch.object(controller, "_update_all_buttons") as update_mock:
                            monkeypatch.setattr(controller_module.time, "sleep", fake_sleep)
                            controller._poll_active_loop()

    build_mock.assert_called_once_with()
    front_mock.assert_called_once_with()
    cwd_mock.assert_called_once_with("ttys001")
    branch_mock.assert_called_once_with("/Users/tester/src/project")
    read_mock.assert_called_once_with()
    update_mock.assert_called_once_with()
    assert controller.active_slot == 0
    assert controller.slot_cwd[0] == "/tmp/new"
    assert controller.slot_branch[0] == "feature/new"
    assert controller.blink_on is False


def test_poll_active_loop_logs_errors_and_keeps_going(controller, monkeypatch):
    controller.running = True
    controller.mode = MODE_ROW

    def fake_sleep(_interval):
        controller.running = False

    with patch.object(controller, "_build_tty_map", side_effect=RuntimeError("boom")):
        with patch("clawdeck.controller.logger.log") as log_mock:
            monkeypatch.setattr(controller_module.time, "sleep", fake_sleep)
            monkeypatch.setattr(controller_module.time, "time", lambda: 100.0)
            controller._poll_active_loop()

    log_mock.assert_called_once()
