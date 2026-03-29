import os
import pty
import select
import subprocess
import sys

import pytest


pytestmark = pytest.mark.mac_integration


def test_get_iterm_sessions_smoke(controller, require_mac_smoke):
    sessions = controller._get_iterm_sessions()

    assert isinstance(sessions, list)
    for session in sessions:
        assert isinstance(session["name"], str)
        assert isinstance(session["tty"], str)
        assert session["name"]
        assert session["tty"]


def test_activate_frontmost_session_smoke(controller, require_mac_smoke):
    sessions = controller._get_iterm_sessions()
    if not sessions:
        pytest.skip("No iTerm2 sessions found")

    target = sessions[0]
    controller.config["session_map"]["T1"] = target["name"]

    assert controller._activate_session("T1") is True
    assert controller._frontmost_session_name()


def test_approve_permission_smoke_with_real_tty(controller, require_mac_smoke):
    master_fd, slave_fd = pty.openpty()
    try:
        tty_path = os.ttyname(slave_fd)
        controller.slot_tty = {0: os.path.basename(tty_path)}

        assert controller._approve_permission("T1") is True

        ready, _, _ = select.select([master_fd], [], [], 1)
        assert ready, "Timed out waiting for data on smoke-test PTY"
        payload = os.read(master_fd, 16).replace(b"\r\n", b"\n")
        assert payload == b"y\n"
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def test_streamdeck_enumeration_smoke(require_deck_smoke):
    code = """
from StreamDeck.DeviceManager import DeviceManager
devices = DeviceManager().enumerate()
assert devices, "No Stream Deck devices found"
deck = devices[0]
deck.open()
deck.reset()
deck.close()
print(len(devices))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert int(result.stdout.strip()) >= 1
