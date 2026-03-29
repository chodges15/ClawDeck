"""Helpers for mapping Stream Deck key indexes onto row-model concepts."""

from .constants import KEYS_PER_ROW, SESSIONS, TOTAL_KEYS


def key_to_session(key):
    """Return the logical session for a key index, if any."""
    if 0 <= key < TOTAL_KEYS:
        return SESSIONS[key // KEYS_PER_ROW]
    return None


def session_label_key(session):
    """Return the label-key index for a logical session row."""
    if session not in SESSIONS:
        return None
    return SESSIONS.index(session) * KEYS_PER_ROW


def key_is_label(key):
    """Return whether a key index is the first key in its row."""
    return 0 <= key < TOTAL_KEYS and key % KEYS_PER_ROW == 0


def key_info_index(key):
    """Return the zero-based info-column index for a non-label key."""
    if not 0 <= key < TOTAL_KEYS:
        return -1
    col = key % KEYS_PER_ROW
    return col - 1 if col else -1
