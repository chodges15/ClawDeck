from unittest.mock import patch


def test_build_tty_map_matches_session_names_case_insensitively(controller):
    controller.config["session_map"] = {"T1": "Alpha", "T2": "BETA", "T3": ""}
    sessions = [
        {"name": "Claude alpha worker", "tty": "ttys001"},
        {"name": "claude beta worker", "tty": "ttys002"},
        {"name": "irrelevant", "tty": "ttys003"},
    ]

    with patch.object(controller, "_get_iterm_sessions", return_value=sessions):
        with patch.object(controller, "_resolve_tty_cwd", side_effect=lambda tty: f"/tmp/{tty}"):
            controller._build_tty_map()

    assert controller.slot_tty == {0: "ttys001", 5: "ttys002"}
    assert controller.slot_cwd == {0: "/tmp/ttys001", 5: "/tmp/ttys002"}


def test_build_tty_map_ignores_unmatched_patterns(controller):
    controller.config["session_map"] = {"T1": "missing", "T2": "", "T3": "third"}
    sessions = [{"name": "Claude Third", "tty": "ttys004"}]

    with patch.object(controller, "_get_iterm_sessions", return_value=sessions):
        with patch.object(controller, "_resolve_tty_cwd", return_value="/tmp/ttys004"):
            controller._build_tty_map()

    assert controller.slot_tty == {10: "ttys004"}
    assert controller.slot_cwd == {10: "/tmp/ttys004"}


def test_approve_permission_writes_yes_to_tty(controller):
    controller.slot_tty = {0: "ttys009"}

    with patch("main.os.open", return_value=11) as open_mock:
        with patch("main.os.write") as write_mock:
            with patch("main.os.close") as close_mock:
                assert controller._approve_permission("T1") is True

    open_mock.assert_called_once()
    write_mock.assert_called_once_with(11, b"y\n")
    close_mock.assert_called_once_with(11)
