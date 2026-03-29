"""Tests for tab/session matching and permission approval writes."""

from unittest.mock import patch


def test_build_tty_map_matches_tab_titles_case_insensitively(controller):
    controller.config["session_map"] = {"T1": "Alpha", "T2": "BETA", "T3": ""}
    sessions = [
        {"name": "Claude worker", "tab_title": "alpha", "tty": "ttys001"},
        {"name": "claude worker", "tab_title": "beta", "tty": "ttys002"},
        {"name": "irrelevant", "tab_title": "other", "tty": "ttys003"},
    ]

    with patch.object(controller, "_get_iterm_sessions", return_value=sessions):
        with patch.object(controller, "_resolve_tty_cwd", side_effect=lambda tty: f"/tmp/{tty}"):
            controller._build_tty_map()

    assert controller.slot_tty == {0: "ttys001", 5: "ttys002"}
    assert controller.slot_cwd == {0: "/tmp/ttys001", 5: "/tmp/ttys002"}


def test_build_tty_map_ignores_unmatched_patterns(controller):
    controller.config["session_map"] = {"T1": "missing", "T2": "", "T3": "third"}
    sessions = [{"name": "Claude worker", "tab_title": "Third", "tty": "ttys004"}]

    with patch.object(controller, "_get_iterm_sessions", return_value=sessions):
        with patch.object(controller, "_resolve_tty_cwd", return_value="/tmp/ttys004"):
            controller._build_tty_map()

    assert controller.slot_tty == {10: "ttys004"}
    assert controller.slot_cwd == {10: "/tmp/ttys004"}


def test_build_tty_map_falls_back_to_literal_session_names_when_unconfigured(controller):
    controller.config["session_map"] = {"T1": "", "T2": "", "T3": ""}
    sessions = [
        {"name": "Claude worker", "tab_title": "T1", "tty": "ttys001"},
        {"name": "Worker shell", "tab_title": "Worker T3", "tty": "ttys003"},
    ]

    with patch.object(controller, "_get_iterm_sessions", return_value=sessions):
        with patch.object(controller, "_resolve_tty_cwd", side_effect=lambda tty: f"/tmp/{tty}"):
            controller._build_tty_map()

    assert controller.slot_tty == {0: "ttys001", 10: "ttys003"}
    assert controller.slot_cwd == {0: "/tmp/ttys001", 10: "/tmp/ttys003"}


def test_match_session_info_prefers_tab_title_and_falls_back_to_name(controller):
    controller.config["session_map"] = {"T1": "", "T2": "", "T3": ""}
    assert controller._match_session_info({"tab_title": "Claude T1", "name": "shell"}) == "T1"

    controller.config["session_map"] = {"T1": "alpha", "T2": "", "T3": ""}
    assert controller._match_session_info({"tab_title": "random", "name": "Claude alpha"}) == "T1"
    assert controller._match_session_info({"tab_title": "Claude T2", "name": "shell"}) is None


def test_approve_permission_writes_yes_to_tty(controller):
    controller.slot_tty = {0: "ttys009"}

    with patch("clawdeck.host.os.open", return_value=11) as open_mock:
        with patch("clawdeck.host.os.write") as write_mock:
            with patch("clawdeck.host.os.close") as close_mock:
                assert controller._approve_permission("T1") is True

    open_mock.assert_called_once()
    write_mock.assert_called_once_with(11, b"y\n")
    close_mock.assert_called_once_with(11)
