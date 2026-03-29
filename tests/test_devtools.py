"""Tests for the `clawdeck.devtools` helper commands."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from clawdeck.devtools import (
    collect_iterm_snapshot,
    list_decks,
    paint_all_keys,
    paint_key,
)


def test_collect_iterm_snapshot_includes_row_matches_and_raw_sessions(default_config):
    class FakeHost:
        """Host double that returns predictable iTerm session data."""

        def get_iterm_sessions(self):
            return [
                {"name": "Claude shell", "tab_title": "T1", "tty": "ttys001"},
                {"name": "Worker shell", "tab_title": "T2", "tty": "ttys002"},
            ]

        def frontmost_session_name(self):
            return "Worker T2"

        def resolve_tty_cwd(self, tty):
            return f"/tmp/{tty}"

    config = dict(default_config)
    config["session_map"] = {"T1": "", "T2": "", "T3": ""}
    snapshot = collect_iterm_snapshot(
        host=FakeHost(),
        config_store=SimpleNamespace(load=lambda: config),
    )

    assert snapshot["frontmost"] == "Worker T2"
    assert snapshot["rows"][0]["match"]["tty"] == "ttys001"
    assert snapshot["rows"][1]["match"]["cwd"] == "/tmp/ttys002"
    assert snapshot["rows"][2]["match"] is None
    assert snapshot["sessions"][1]["mapped_session"] == "T2"


def test_list_decks_prints_detected_devices(capsys):
    deck = SimpleNamespace(deck_type=lambda: "Fake Deck", key_count=lambda: 15)
    with patch("clawdeck.devtools.DeviceManager") as manager_cls:
        manager_cls.return_value.enumerate.return_value = [deck]
        rc = list_decks()

    assert rc == 0
    assert "type=Fake Deck keys=15" in capsys.readouterr().out


def test_paint_all_keys_sets_every_key(fake_deck):
    renderer = SimpleNamespace(render_button=lambda deck, label, bg, fg: {"label": label, "bg": bg})

    paint_all_keys(fake_deck, renderer, "TEST", (1, 2, 3), (255, 255, 255))

    assert len(fake_deck.images) == fake_deck.key_count()
    assert fake_deck.images[0]["label"] == "TEST"
    assert fake_deck.images[14]["bg"] == (1, 2, 3)


def test_paint_key_rejects_invalid_index(fake_deck):
    renderer = SimpleNamespace(render_button=lambda deck, label, bg, fg: None)

    with pytest.raises(ValueError):
        paint_key(fake_deck, renderer, 99, "TEST", (1, 2, 3), (255, 255, 255))
