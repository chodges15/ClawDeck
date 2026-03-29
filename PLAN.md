# ClawDeck Row-Based Layout Redesign

## Context

ClawDeck currently maps Stream Deck buttons to screen positions, tiling up to 14 terminal windows across a 5x3 grid. The user only uses 3 Claude sessions at a time and wants each **row** on the Stream Deck to represent one session. This enables a new UX: when Claude stops for permission, the command scrolls across that row's buttons so the user can see and approve it without switching windows.

## New Button Layout

```
Row 0:  [T1]  [info] [info] [info] [info]    <- Session 1
Row 1:  [T2]  [info] [info] [info] [info]    <- Session 2
Row 2:  [T3]  [info] [info] [info] [info]    <- Session 3
```

- Left button (col 0): label + status color (idle/working/permission)
- Right 4 buttons (cols 1-4): CWD in normal states; scrolling command text during permission
- No dedicated ENTER key (T3 gets all 5 buttons; ENTER still exists in Nav Mode)

## Phase 1: Remove Tiling and Position-Based Code

### Delete these functions from `main.py`:
- `tile_windows()` (~line 992)
- `_match_windows_to_terminals()` (~line 1030)
- `_move_window_to_rect()` (~line 1058)
- `_is_snapped()` (~line 1081), `_check_snap_to_grid()` (~line 1099)
- `_find_nearest_empty_terminal()` (~line 1186)
- `_get_terminal_rect()` (~line 421), `_grid_rect()` (~line 931)
- `_get_screen_bounds()` (~line 524)
- `_get_terminal_windows()` (~line 497), `_find_controller_window()` (~line 964)
- `_refresh_controller_win_id()` (~line 983)
- `_start_overlay()` (~line 850), `_stop_overlay()` (~line 884), `_update_overlay()` (~line 903)

### Remove from `__init__`:
- `self.screen`, `self._prev_win_positions`, `self._snap_candidates`, `self._controller_win_id`, `self.overlay_proc`

### Remove constants:
- `LAYOUTS` dict, `LAYOUT_NAMES`, `GRID_SLOTS`, `DECK_TERMINAL_SLOTS`, `ENTER_KEY_INDEX`
- `SNAP_TOLERANCE`, `SNAP_SETTLE_POLLS`, `OVERLAY_FILE`

### Remove config keys:
- `snap_enabled`, `overlay_label` from `CONFIG_DEFAULTS`
- `layout` from `CONFIG_DEFAULTS` (replaced by fixed 3-row model)

### Remove REPL commands:
- `tile`, `snap`, `layout`

### Clean up `run()`:
- Remove `tile_windows()` call, `_start_overlay()`, `_stop_overlay()` from finally

### Clean up `_poll_active_loop()`:
- Remove `_check_snap_to_grid()`, `_update_overlay()` calls
- Replace `_get_frontmost_slot()` with new session-aware version (Phase 2)

### Remove unused Quartz imports:
- `CGWindowListCopyWindowInfo`, `kCGWindowListOptionOnScreenOnly`, `kCGWindowListExcludeDesktopElements`, `kCGNullWindowID`, `CGGetActiveDisplayList`, `CGDisplayBounds`, `CGMainDisplayID`

## Phase 2: New Row-Based Key Mapping

### New constants:
```python
NUM_SESSIONS = 3
SESSIONS = ["T1", "T2", "T3"]
KEYS_PER_ROW = COLS  # 5
```

### New helper functions replacing old layout functions:

- `_key_to_session(key)` -> returns session name ("T1"/"T2"/"T3"), replaces `_key_to_terminal()`
- `_session_label_key(session)` -> returns 0, 5, or 10; replaces `_terminal_to_active_slot()`
- `_key_is_label(key)` -> True if `key % KEYS_PER_ROW == 0`
- `_key_info_index(key)` -> 0-3 for info buttons, -1 for label buttons

### Remove:
- `_get_layout()`, `_get_terminal_names()`, `_get_terminal_slots()`, `_key_to_terminal()`, `_terminal_to_active_slot()`

## Phase 3: Session-Name-Based TTY Mapping

### New config:
```python
CONFIG_DEFAULTS["session_map"] = {"T1": "", "T2": "", "T3": ""}
```
Values are substring patterns matched case-insensitively against iTerm2 session names.

### New `_get_iterm_sessions()`:
AppleScript that iterates all iTerm2 windows/tabs/sessions and returns `[{name, tty}]`:
```applescript
tell application "iTerm2"
    repeat with w in windows
        repeat with t in tabs of w
            set s to current session of t
            -- output: name|||tty
        end repeat
    end repeat
end tell
```

### Rewrite `_build_tty_map()`:
- Call `_get_iterm_sessions()`
- For each session T1/T2/T3, find the first iTerm2 session whose name contains the configured pattern
- Store in `self.slot_tty` keyed by label key (0, 5, 10)
- Resolve CWD as before

### Remove `_get_app_window_ttys()`:
No longer needed (position-based matching is gone).

### New `_activate_session(session)`:
AppleScript to select the iTerm2 tab/window whose session name matches the pattern, replacing the position-based `_activate_slot()`. Used when entering Nav Mode.

### Update `_get_frontmost_slot()`:
Replace position-based detection. New approach: query iTerm2 for the frontmost session name, match it to T1/T2/T3 via session_map patterns, return the label key.

## Phase 4: Hook Update for Command Text

### `deck-hook.sh` changes:
When state is "pending", read stdin (Claude Code passes tool JSON via stdin to command hooks):
```bash
TOOL_INFO=""
if [ "$STATE" = "pending" ]; then
    TOOL_INFO=$(cat 2>/dev/null || true)
fi
```
Write `tool_input` field into the status JSON when present:
```bash
printf '{"state":"%s","tty":"%s","ts":%s,"tool_input":%s}' \
    "$STATE" "$TTY_NAME" "$(date +%s)" "$TOOL_INFO" > "$TMPFILE"
```

### `_read_status_files()` changes:
Parse `tool_input` from status JSON and store in new `self.slot_tool_info` dict (label_key -> dict with tool_name, tool_input).

### `install_hooks.py`:
No changes needed - the PreToolUse hook already fires for all tools and Claude Code already pipes hook input to stdin.

## Phase 5: Row-Based Rendering with Scroll Animation

### New state:
```python
self.slot_tool_info = {}    # label_key -> {tool_name, tool_input}
self.scroll_offsets = {}    # label_key -> pixel offset
self.scroll_images = {}     # label_key -> PIL Image (wide strip)
```

### New `_draw_row_mode()` (replaces `_draw_grid_mode()`):
For each session/row:

**Label button** (key 0/5/10):
- Shows "T1"/"T2"/"T3" with status color + amber border if active
- Same `_get_slot_style()` logic, keyed by label_key

**Info buttons** (keys 1-4, 6-9, 11-14):
- **Permission state**: show scrolling command text (marquee)
- **Other states**: button 1 shows CWD subtitle, rest dark
- **Unmapped session**: all dark

### `_format_tool_command(tool_info)`:
```
Bash: npm test
Edit: src/main.py
Read: config.json
ToolName: first_value
```

### Scroll animation:
- `_render_scroll_strip(text)`: render full command text as one wide PIL image on dark red background
- In `_poll_active_loop()`: for sessions in permission state, advance `scroll_offsets[key]` by `scroll_speed` pixels per tick
- `_render_scroll_button(strip, offset, button_idx)`: crop the strip at the right position for each of the 4 buttons
- Wrap offset when it exceeds strip width (seamless loop with padding)

### New config:
```python
CONFIG_DEFAULTS["scroll_speed"] = 2  # pixels per poll tick
```

## Phase 6: Permission Approval

### New `_approve_permission(session)`:
Write `y\n` directly to the TTY device:
```python
tty_path = f"/dev/{self.slot_tty[label_key]}"
fd = os.open(tty_path, os.O_WRONLY | os.O_NOCTTY)
os.write(fd, b"y\n")
os.close(fd)
```
This works without focusing the window. Requires same-user ownership of the TTY.

### Update `_handle_key()`:
In row mode (replaces grid mode):
- **Label key tap** (0/5/10):
  - If session in permission state -> `_approve_permission(session)`
  - Else if session is already active -> enter Nav Mode (same as before)
  - Else -> activate session (bring to foreground), mark as active
- **Label key hold**: activate + Whisprflow (same as before)
- **Info button tap** (1-4, 6-9, 11-14): no action (display only)

### Nav Mode:
Unchanged. Entering Nav Mode calls `_activate_session()` to focus the iTerm2 window, then keystrokes go via System Events as before.

## Phase 7: Config and Settings UI

### `CONFIG_DEFAULTS` final shape:
- Remove: `snap_enabled`, `overlay_label`, `layout`
- Add: `session_map`, `scroll_speed`

### `settings.html`:
- Remove: Layout grid picker (5 cards), Snap toggle, Overlay Label toggle
- Add: "Session Mapping" section with 3 text inputs for T1/T2/T3 patterns
- Add: "Scroll Speed" slider

### Settings API:
- Remove `tile_windows()` call on layout change
- The generic `config.update()` handles new fields automatically

## Phase 8: Tests

### Rewrite `tests/test_layouts.py`:
- Test `_key_to_session()`: keys 0-4 -> T1, 5-9 -> T2, 10-14 -> T3
- Test `_session_label_key()`: T1->0, T2->5, T3->10
- Test `_key_is_label()`, `_key_info_index()`

### New `tests/test_session_map.py`:
- Test `_build_tty_map()` with mocked `_get_iterm_sessions()` returning name/tty pairs
- Test case-insensitive substring matching
- Test unmatched patterns produce no mapping
- Test `_approve_permission()` with mocked `os.open`/`os.write`

### New `tests/test_scroll.py`:
- Test `_format_tool_command()` for Bash, Read, Edit, generic tools
- Test scroll offset wrapping logic

### Update `tests/test_config.py`:
- Update required keys: add `session_map`, `scroll_speed`; remove `snap_enabled`, `layout`, `overlay_label`

### Update `tests/conftest.py`:
- Remove screen bounds mocking, `LAYOUTS`/`LAYOUT_NAMES` imports
- Remove `_get_screen_bounds` patch

## Verification

1. Run existing test suite after Phase 1-2 to confirm deletions don't break remaining code
2. Mock-test session mapping with fake iTerm2 output
3. Manual test: set iTerm2 session names, configure `session_map`, verify TTY mapping
4. Manual test: trigger a permission prompt, verify scrolling animation on the 4 right buttons
5. Manual test: tap label button during permission, verify approval goes through
6. Run full `pytest` after all phases

## Files Modified

| File | Changes |
|------|---------|
| `main.py` | Major: remove tiling/overlay/snap, new row mapping, session-name TTY, scroll rendering, approval |
| `deck-hook.sh` | Capture tool_input from stdin on PreToolUse |
| `settings.html` | Remove layout/snap UI, add session map inputs |
| `tests/test_layouts.py` | Full rewrite for row-based mapping |
| `tests/test_config.py` | Update required config keys |
| `tests/conftest.py` | Remove screen/tiling mocks |
| `tests/test_session_map.py` | New: session name matching tests |
| `tests/test_scroll.py` | New: scroll rendering tests |
