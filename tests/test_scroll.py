"""Tests for permission marquee formatting and scroll advancement."""

def test_format_tool_command_for_bash(controller):
    tool_info = {"tool_name": "Bash", "tool_input": {"command": "npm test"}}
    assert controller._format_tool_command(tool_info) == "Bash: npm test"


def test_format_tool_command_for_read(controller):
    tool_info = {"tool_name": "Read", "tool_input": {"file_path": "config.json"}}
    assert controller._format_tool_command(tool_info) == "Read: config.json"


def test_format_tool_command_for_edit(controller):
    tool_info = {"tool_name": "Edit", "tool_input": {"file_path": "src/main.py"}}
    assert controller._format_tool_command(tool_info) == "Edit: src/main.py"


def test_format_tool_command_generic_uses_first_value(controller):
    tool_info = {"tool_name": "Search", "tool_input": {"query": "needle", "limit": 5}}
    assert controller._format_tool_command(tool_info) == "Search: needle"


def test_advance_scroll_offset_wraps(controller):
    controller.config["scroll_speed"] = 2
    controller.scroll_offsets[0] = 7
    assert controller._advance_scroll_offset(0, 8) == 1
    assert controller.scroll_offsets[0] == 1


def test_advance_scroll_offset_handles_zero_width(controller):
    controller.config["scroll_speed"] = 2
    controller.scroll_offsets[0] = 7
    assert controller._advance_scroll_offset(0, 0) == 0
    assert controller.scroll_offsets[0] == 0


def test_ensure_scroll_strip_caches_by_formatted_text(controller):
    controller.slot_tool_info = {0: {"tool_name": "Bash", "tool_input": {"command": "pytest"}}}

    rendered = []

    def fake_render(text):
        rendered.append(text)
        return f"strip:{text}"

    controller._render_scroll_strip = fake_render

    assert controller._ensure_scroll_strip(0) == "strip:Bash: pytest"
    assert controller._ensure_scroll_strip(0) == "strip:Bash: pytest"
    assert rendered == ["Bash: pytest"]


def test_advance_scroll_offsets_only_moves_permission_rows(controller):
    controller.slot_status = {0: "permission", 5: "idle"}
    controller.scroll_offsets = {0: 1}
    controller._ensure_scroll_strip = lambda key: type("Strip", (), {"width": 8})()

    changed = controller._advance_scroll_offsets()

    assert changed is True
    assert controller.scroll_offsets[0] == 3


def test_update_all_buttons_dispatches_by_mode(controller):
    calls = []
    controller._draw_row_mode = lambda: calls.append("row")
    controller._draw_nav_mode = lambda: calls.append("nav")

    controller.mode = "row"
    controller._update_all_buttons()
    controller.mode = "nav"
    controller._update_all_buttons()

    assert calls == ["row", "nav"]
