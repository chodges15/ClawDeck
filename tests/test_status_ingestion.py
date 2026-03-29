import json

import main


def test_normalize_tool_info_handles_string_json(controller):
    raw = '{"tool_name":"Bash","tool_input":{"command":"npm test"}}'

    assert controller._normalize_tool_info(raw) == {
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"},
    }


def test_normalize_tool_info_handles_single_key_dict(controller):
    assert controller._normalize_tool_info({"Read": "README.md"}) == {
        "tool_name": "Read",
        "tool_input": "README.md",
    }


def test_read_status_files_infers_states_and_tool_info(controller, status_dir, monkeypatch):
    controller.slot_tty = {0: "ttys001", 5: "ttys002"}
    now = 1_000.0
    monkeypatch.setattr(main.time, "time", lambda: now)

    (status_dir / "recent.json").write_text(
        json.dumps(
            {
                "tty": "ttys001",
                "state": "pending",
                "ts": now - 0.5,
                "tool_input": {"tool_name": "Bash", "tool_input": {"command": "pytest"}},
            }
        )
    )
    (status_dir / "permission.json").write_text(
        json.dumps(
            {
                "tty": "ttys002",
                "state": "pending",
                "ts": now - main.PENDING_INFER_SEC - 0.1,
                "tool_input": {"tool_name": "Read", "tool_input": {"file_path": "main.py"}},
            }
        )
    )

    controller._read_status_files()

    assert controller.slot_status == {0: "working", 5: "permission"}
    assert controller.slot_tool_info[0]["tool_name"] == "Bash"
    assert controller.slot_tool_info[5]["tool_input"] == {"file_path": "main.py"}
    assert controller.scroll_offsets[5] == 0
    assert 0 not in controller.scroll_offsets


def test_read_status_files_drops_stale_idle_and_ignores_invalid_files(controller, status_dir, monkeypatch):
    controller.slot_tty = {0: "ttys001"}
    controller.scroll_offsets = {0: 7}
    controller.scroll_images = {0: "strip"}
    controller.scroll_text = {0: "old"}
    now = 2_000.0
    monkeypatch.setattr(main.time, "time", lambda: now)

    (status_dir / ".hidden").write_text("{}")
    (status_dir / "broken.json").write_text("{not json")
    (status_dir / "stale.json").write_text(
        json.dumps({"tty": "ttys001", "state": "idle", "ts": now - main.STATUS_STALE_SEC - 1})
    )

    controller._read_status_files()

    assert controller.slot_status == {}
    assert controller.slot_tool_info == {}
    assert controller.scroll_offsets == {}
    assert controller.scroll_images == {}
    assert controller.scroll_text == {}


def test_read_status_files_resets_scroll_cache_when_permission_text_changes(controller, status_dir, monkeypatch):
    controller.slot_tty = {0: "ttys001"}
    controller.scroll_offsets = {0: 13}
    controller.scroll_images = {0: "old-strip"}
    controller.scroll_text = {0: "Bash: old command"}
    now = 3_000.0
    monkeypatch.setattr(main.time, "time", lambda: now)

    (status_dir / "permission.json").write_text(
        json.dumps(
            {
                "tty": "ttys001",
                "state": "permission",
                "ts": now,
                "tool_input": {"tool_name": "Bash", "tool_input": {"command": "new command"}},
            }
        )
    )

    controller._read_status_files()

    assert controller.slot_status == {0: "permission"}
    assert controller.scroll_offsets[0] == 0
    assert 0 not in controller.scroll_images
    assert 0 not in controller.scroll_text


def test_read_status_files_normalizes_dev_tty_paths(controller, status_dir, monkeypatch):
    controller.slot_tty = {0: "ttys001"}
    now = 3_500.0
    monkeypatch.setattr(main.time, "time", lambda: now)

    (status_dir / "permission.json").write_text(
        json.dumps({"tty": "/dev/ttys001", "state": "working", "ts": now})
    )

    controller._read_status_files()

    assert controller.slot_status == {0: "working"}


def test_read_status_files_keeps_existing_scroll_cache_when_permission_text_unchanged(controller, status_dir, monkeypatch):
    controller.slot_tty = {0: "ttys001"}
    controller.scroll_offsets = {0: 9}
    controller.scroll_images = {0: "strip"}
    controller.scroll_text = {0: "Bash: same command"}
    now = 4_000.0
    monkeypatch.setattr(main.time, "time", lambda: now)

    (status_dir / "permission.json").write_text(
        json.dumps(
            {
                "tty": "ttys001",
                "state": "permission",
                "ts": now,
                "tool_input": {"tool_name": "Bash", "tool_input": {"command": "same command"}},
            }
        )
    )

    controller._read_status_files()

    assert controller.scroll_offsets[0] == 9
    assert controller.scroll_images[0] == "strip"
    assert controller.scroll_text[0] == "Bash: same command"
