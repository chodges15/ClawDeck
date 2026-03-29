"""Contracts for docs-inspired Claude hook payload fixtures."""

import json


def test_claude_hook_payloads_include_stable_common_fields(claude_hook_common_fields, claude_hook_payloads):
    for payload in claude_hook_payloads.values():
        assert payload["session_id"] == claude_hook_common_fields["session_id"]
        assert payload["transcript_path"] == claude_hook_common_fields["transcript_path"]
        assert payload["permission_mode"] == claude_hook_common_fields["permission_mode"]
        assert payload["cwd"].startswith("/Users/tester/")


def test_claude_hook_payloads_cover_current_row_ui_events(claude_hook_payloads):
    pre_tool_use = claude_hook_payloads["pre_tool_use"]
    permission_request = claude_hook_payloads["permission_request"]
    post_tool_use = claude_hook_payloads["post_tool_use"]
    notification = claude_hook_payloads["notification"]
    cwd_changed = claude_hook_payloads["cwd_changed"]

    assert pre_tool_use["hook_event_name"] == "PreToolUse"
    assert pre_tool_use["tool_name"] == "Bash"
    assert pre_tool_use["tool_input"]["command"] == "git status --short"
    assert pre_tool_use["tool_use_id"] == "toolu_test_pre_001"

    assert permission_request["hook_event_name"] == "PermissionRequest"
    assert permission_request["tool_name"] == "Write"
    assert permission_request["tool_input"]["file_path"].endswith("/app.py")
    assert permission_request["permission_suggestions"][0]["value"] == "allow_once"

    assert post_tool_use["hook_event_name"] == "PostToolUse"
    assert post_tool_use["tool_name"] == "Read"
    assert post_tool_use["tool_response"]["content"] == "Demo project README"

    assert notification["hook_event_name"] == "Notification"
    assert notification["notification_type"] == "permission_prompt"
    assert notification["title"] == "Permission required"

    assert cwd_changed["hook_event_name"] == "CwdChanged"
    assert cwd_changed["cwd"] == cwd_changed["new_cwd"]
    assert cwd_changed["old_cwd"].endswith("/demo-project")


def test_claude_hook_payloads_are_json_serializable(claude_hook_payloads):
    encoded = json.dumps(claude_hook_payloads, sort_keys=True)

    assert "session-test-001" in encoded
    assert "toolu_test_perm_001" in encoded
    assert "permission_prompt" in encoded
