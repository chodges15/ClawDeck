"""Tests for mapping deck key indexes onto the row layout model."""

from clawdeck.constants import KEYS_PER_ROW, SESSIONS, TOTAL_KEYS


def test_key_to_session_maps_each_row(controller):
    expected = {
        0: "T1",
        1: "T1",
        4: "T1",
        5: "T2",
        9: "T2",
        10: "T3",
        14: "T3",
    }
    for key, session in expected.items():
        assert controller._key_to_session(key) == session


def test_session_label_key_maps_to_first_column(controller):
    assert controller._session_label_key("T1") == 0
    assert controller._session_label_key("T2") == KEYS_PER_ROW
    assert controller._session_label_key("T3") == KEYS_PER_ROW * 2


def test_key_is_label_only_first_column(controller):
    assert controller._key_is_label(0) is True
    assert controller._key_is_label(5) is True
    assert controller._key_is_label(10) is True
    assert controller._key_is_label(1) is False
    assert controller._key_is_label(14) is False


def test_key_info_index_maps_info_buttons(controller):
    assert controller._key_info_index(0) == -1
    assert controller._key_info_index(1) == 0
    assert controller._key_info_index(2) == 1
    assert controller._key_info_index(3) == 2
    assert controller._key_info_index(4) == 3
    assert controller._key_info_index(5) == -1
    assert controller._key_info_index(TOTAL_KEYS) == -1


def test_sessions_constant_matches_model():
    assert SESSIONS == ["T1", "T2", "T3"]
