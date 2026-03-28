# Test Suite — Design Spec

Comprehensive unit tests for ClawDeck's pure logic and state logic functions. Uses pytest with minimal mocking — test what we can without macOS/hardware dependencies.

---

## Framework

pytest. No additional test dependencies beyond what's in the venv. Tests live in `tests/` at the project root.

---

## Test Modules

### `tests/test_colors.py` — Color helpers
- `_rgb_to_hex`: standard colors, edge cases (0,0,0), (255,255,255)
- `_hex_to_rgb`: with/without `#` prefix, lowercase/uppercase
- `_color` method: returns config color, falls back to default on missing/invalid hex
- Roundtrip: rgb → hex → rgb

### `tests/test_layouts.py` — Layout resolution and grid geometry
- `_get_layout`: each named layout returns 15 elements, last is always ENTER
- `_get_terminal_names`: unique names in order, excludes ENTER, correct count per layout
- `_get_terminal_slots`: maps names to correct key indices, merged slots share a name
- `_key_to_terminal`: returns correct name for each key, None for ENTER
- `_terminal_to_active_slot`: returns first key index for a terminal
- `_grid_rect`: correct x/y/w/h for corner slots (0, 4, 10, 14), center slot
- `_get_terminal_rect`: merged slots produce correct bounding rect

### `tests/test_cwd.py` — CWD formatting
- `_format_cwd` with mode "last": returns last folder name
- `_format_cwd` with mode "two": returns last two path segments
- `_format_cwd` with mode "full": replaces home dir with ~
- `_format_cwd` with mode "off": returns None
- Edge cases: root path, home dir itself, path with spaces, None input

### `tests/test_window_matching.py` — Window-to-terminal matching
- `_match_windows_to_terminals`: windows match nearest zone by center distance
- Multiple windows: each assigned to different zone (no duplicates)
- More windows than zones: extras unmatched
- More zones than windows: zones left empty
- `_is_snapped`: window within 2px tolerance → True, outside → False
- `_find_nearest_empty_terminal`: finds closest unoccupied zone, skips occupied

### `tests/test_status.py` — Slot styling and status state machine
- `_get_slot_style`: idle → blue, working → green, permission → red (blink on/off)
- Active slot gets amber border, inactive gets None
- No status + active → amber fill, no status + inactive → black
- `_get_nav_style`: correct labels and colors for each nav key
- Config color overrides apply

### `tests/test_keys.py` — Key handling and keystroke formatting
- `_format_keystroke`: modifier combinations (cmd, shift, ctrl, option), letter keys, special keys
- `_pick_font`: 1-2 chars → large, 3-4 → medium, 5+ → small
- `_handle_grid_key`: tap activates slot, tap active slot enters nav mode
- `_handle_nav_key`: number keys send keystrokes, BACK returns to grid mode, arrows send arrows

### `tests/test_config.py` — Config loading and merging
- Default config has all required keys
- Config merge preserves user values, adds new defaults
- Nested dict merge (colors) adds new keys without overwriting existing
- Invalid/missing config file → falls back to defaults

---

## Test Controller

Many methods are on `DeckController` which needs macOS APIs in `__init__`. Create a lightweight test fixture that patches the OS-dependent init calls:

```python
@pytest.fixture
def controller():
    """DeckController with OS/hardware deps patched out."""
    with patch.object(DeckController, '_get_screen_bounds', return_value={'x': 0, 'y': 25, 'w': 2560, 'h': 1415}):
        with patch.object(DeckController, '_init_fonts'):
            with patch.object(DeckController, '_load_config', return_value=dict(CONFIG_DEFAULTS)):
                c = DeckController()
                c.screen = {'x': 0, 'y': 25, 'w': 2560, 'h': 1415}
                c.font_xs = c.font_sm = c.font_md = c.font_lg = None
                return c
```

This lets us test all the layout, style, matching, and state methods without Quartz/fonts/config file.

---

## Scope & Non-Goals

- No testing of Quartz, AppKit, AppleScript, or Stream Deck hardware
- No testing of overlay.py (pure PyObjC, needs running NSApplication)
- No testing of settings.html
- No integration tests (would need a running Stream Deck)
- No mocking subprocess calls for TTY/CWD resolution (OS-specific, tested manually)
