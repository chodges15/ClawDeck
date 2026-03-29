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
