"""Tests for window matching and snap detection in DeckController."""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rect_center(rect):
    return rect["cx"], rect["cy"]


def _window_near(rect, dx=0, dy=0):
    """Return a window dict positioned at a zone's exact position + optional offset."""
    return {"x": rect["x"] + dx, "y": rect["y"] + dy, "w": rect["w"], "h": rect["h"]}


# ---------------------------------------------------------------------------
# _match_windows_to_terminals
# ---------------------------------------------------------------------------

class TestMatchWindowsToTerminals:

    def test_match_single_window(self, controller):
        names = controller._get_terminal_names()
        rects = {name: controller._get_terminal_rect(name) for name in names}

        target = names[0]
        win = _window_near(rects[target])

        result = controller._match_windows_to_terminals([win], names, rects)

        assert result.get(target) == win

    def test_match_multiple_windows(self, controller):
        names = controller._get_terminal_names()
        rects = {name: controller._get_terminal_rect(name) for name in names}

        # Pick first 3 zones and place a window at each
        targets = names[:3]
        windows = [_window_near(rects[t]) for t in targets]

        result = controller._match_windows_to_terminals(windows, names, rects)

        for t, win in zip(targets, windows):
            assert result.get(t) == win, f"Expected window at zone {t}"

    def test_match_no_duplicates(self, controller):
        names = controller._get_terminal_names()
        rects = {name: controller._get_terminal_rect(name) for name in names}

        targets = names[:3]
        windows = [_window_near(rects[t]) for t in targets]

        result = controller._match_windows_to_terminals(windows, names, rects)

        # Each zone that got a match should hold a distinct window object
        matched_wins = list(result.values())
        assert len(matched_wins) == len(set(id(w) for w in matched_wins)), \
            "Same window object assigned to multiple zones"

    def test_match_more_windows_than_zones(self, controller):
        names = controller._get_terminal_names()
        rects = {name: controller._get_terminal_rect(name) for name in names}

        # Create more windows than zones by stacking extras near zone 0
        first_rect = rects[names[0]]
        extra_windows = [_window_near(first_rect, dx=i * 5) for i in range(len(names) + 3)]

        result = controller._match_windows_to_terminals(extra_windows, names, rects)

        # Result should have at most one entry per zone
        assert len(result) <= len(names), "More matches returned than zones exist"
        # No zone should appear twice
        assert len(result) == len(set(result.keys()))


# ---------------------------------------------------------------------------
# _is_snapped
# ---------------------------------------------------------------------------

class TestIsSnapped:

    def test_snapped_exact_position(self, controller):
        names = controller._get_terminal_names()
        rect = controller._get_terminal_rect(names[0])

        win = _window_near(rect)
        assert controller._is_snapped(win) is True

    def test_snapped_within_tolerance(self, controller):
        names = controller._get_terminal_names()
        rect = controller._get_terminal_rect(names[0])

        win = _window_near(rect, dx=1, dy=1)
        assert controller._is_snapped(win) is True

    def test_snapped_outside_tolerance(self, controller):
        names = controller._get_terminal_names()
        rect = controller._get_terminal_rect(names[0])

        win = _window_near(rect, dx=5, dy=5)
        assert controller._is_snapped(win) is False


# ---------------------------------------------------------------------------
# _find_nearest_empty_terminal
# ---------------------------------------------------------------------------

class TestFindNearestEmptyTerminal:

    def test_nearest_empty_finds_closest(self, controller):
        names = controller._get_terminal_names()
        target = names[0]
        rect = controller._get_terminal_rect(target)

        # Window sitting right at zone 0
        win = _window_near(rect)
        win["id"] = 999

        # All other zones are occupied; target zone is empty
        occupied_windows = [
            {**_window_near(controller._get_terminal_rect(name)), "id": i}
            for i, name in enumerate(names)
            if name != target
        ]

        with patch.object(controller, "_get_terminal_windows", return_value=occupied_windows):
            result = controller._find_nearest_empty_terminal(win)

        assert result == target
