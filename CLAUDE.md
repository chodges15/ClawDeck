# ClawDeck — Developer Reference

This file is for Claude Code (and human contributors) working on the codebase.
For install/usage instructions, see README.md.

## Project Structure

```
clawdeck/
├── main.py              # Core controller — DeckController class
├── overlay.py           # Amber screen border overlay (separate process)
├── deck-hook.sh         # Claude Code hook script (writes status files)
├── install_hooks.py     # Merges hooks into ~/.claude/settings.json
├── setup.sh             # One-time setup (deps + venv + hooks)
├── claude-hooks.json    # Reference hook config (for manual install)
├── requirements.txt     # Python dependencies
├── config.json          # User settings (created at runtime, gitignored)
├── .deck-overlay.json   # Overlay IPC file (created at runtime, gitignored)
├── LICENSE              # MIT
└── CLAUDE.md            # This file
```

## Architecture

- **main.py** — Single class `DeckController`. Opens Stream Deck via `hidapi`, tiles terminal windows into a 5x3 grid, polls for state changes every 200ms in a background thread, renders button images via Pillow.
- **overlay.py** — Separate NSApplication process. Draws a transparent `NSWindow` with a `CALayer` amber border. Reads position from `.deck-overlay.json` every 100ms. Must be standalone functions (not NSObject methods) to avoid PyObjC selector conflicts.
- **deck-hook.sh** — Called by Claude Code hooks. Writes JSON status files to `/tmp/deck-status/{TTY_NAME}` atomically (temp + mv). Detects its own TTY via `tty` command or process tree fallback.
- **install_hooks.py** — Merges hook entries into `~/.claude/settings.json` using `_source: "clawdeck"` tag. Safe to re-run (replaces old entries, preserves hooks from other sources).

## Grid Layout

```
Key indices (0-indexed, row-major):
 0  1  2  3  4       ← Row 0
 5  6  7  8  9       ← Row 1
10 11 12 13 14       ← Row 2
```

- Keys 0-13: Terminal window buttons (T1-T14)
- Key 14: Always Enter key (screen slot 14 used for the controller's own terminal)
- Controller terminal is auto-detected by TTY and placed in slot 14 during tiling

## Key Behaviors

**Grid Mode:** Terminal keys use press/release timing. Tap (<0.5s) fires on release for normal action. Hold (>=0.5s) triggers MIC action. Enter key fires on press (no hold).

**Nav Mode:** All keys fire on press. Layout has ROYGB number row (0-4), BACK at key 9, arrows at 7/11/12/13, MIC at 10, Enter at 14.

## Status State Machine

```
User sends prompt → UserPromptSubmit → "working" (green)
Claude uses tool  → PreToolUse → "pending"
  Tool completes  → PostToolUse → "working" (green)
  No PostToolUse for >2s → inferred "permission" (red blink)
  Notification/permission_prompt → "permission" (confirmed)
Claude done       → Stop/idle_prompt → "idle" (blue)
```

## IPC Files

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `/tmp/deck-status/{TTY}` | deck-hook.sh | main.py | Claude state per terminal |
| `.deck-overlay.json` | main.py | overlay.py | Active window position |
| `config.json` | main.py | main.py | Persistent user settings |

All writes are atomic (temp file + rename).

## Development Notes

- **Quartz** coordinates are top-left origin. AppKit is bottom-left. overlay.py converts: `ns_y = primary_h - quartz_y - height`.
- **PyObjC** works with Python <=3.13. Python 3.14+ may break.
- **AppleScript** is needed for window management — Quartz can read positions but can't move/resize windows.
- **TTY mapping** only works for Terminal.app and iTerm2 (AppleScript TTY resolution). Other terminal apps tile and activate but won't show per-session status colors.
- **CGEvent tap** is used for `mic learn` keystroke capture. Requires Accessibility permissions. Handles both keyDown and flagsChanged (modifier-only keys like fn).
- **MIC config** can be: `"fn"` (double fn press), a dict with `type: "keystroke"` (learned key), or a shell command string.
