# ClawDeck

Map an Elgato Stream Deck to three Claude Code sessions in iTerm2. Each session owns a full row on the 15-key deck: one label key plus four info keys that show the CWD or a scrolling permission preview.

Built for the **Stream Deck Original** (15-key, 5x3 grid) on **macOS**.

## What It Does

- Fixed 3-row layout: one row each for `T1`, `T2`, and `T3`
- Match rows to iTerm2 sessions by configurable session-name substrings
- Each row reflects Claude Code's live state via hooks
- Tap a label key to activate that session
- Tap a permission row label to approve with `y` without focusing the terminal
- Hold a button to trigger Whisprflow / dictation
- Nav Mode for arrow keys and number selection (Claude multi-choice prompts)
- Permission prompts scroll their command preview across the row's four info keys
- Browser-based settings UI for colors, session mapping, and behavior
- All colors fully customizable

### Button Colors

| Color | Meaning |
|-------|---------|
| Black | No Claude session |
| Blue | Idle — waiting for input |
| Green | Working — actively processing |
| Red (blinking) | Permission needed |
| Amber border | Active window |

All colors are customizable via the settings UI.

### Row Layout

```
┌─────┬─────┬─────┬─────┬─────┐
│ T1  │info │info │info │info │
├─────┼─────┼─────┼─────┼─────┤
│ T2  │info │info │info │info │
├─────┼─────┼─────┼─────┼─────┤
│ T3  │info │info │info │info │
└─────┴─────┴─────┴─────┴─────┘
```

- Left key: session label + status color
- Right four keys: CWD in normal states, scrolling command preview in permission state

### Modes

**Row Mode** (default):
- Tap label key → activate session
- Tap active label key → enter Nav Mode
- Tap a label in permission state → approve with `y`
- Hold any label key → activate + trigger MIC (Whisprflow)

**Nav Mode** (tap the active button):
```
  1    2    3    4    5     ← ROYGB number keys
            ↑        BACK
 MIC  ←    ↓    →    ⏎
```
- 1-5 → send number keystrokes
- Arrows → navigation
- MIC → Whisprflow (configurable)
- BACK → return to Grid Mode

## Requirements

- macOS (uses Quartz and AppleScript for session activation and keystroke sending)
- [Homebrew](https://brew.sh)
- Elgato Stream Deck Original (15-key)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed

## Install

```bash
git clone https://github.com/coryszatkowski/ClawDeck.git
cd ClawDeck
bash setup.sh
```

Setup will:
1. Install `hidapi` and Python 3.13 via Homebrew
2. Create a virtual environment and install dependencies
3. Offer to install Claude Code hooks into `~/.claude/settings.json`

On first run, you'll be prompted to grant **Accessibility** permissions to your terminal app (required for session activation and keystroke sending).

## Run

```bash
cd ClawDeck
.venv/bin/python main.py
```

This starts the controller with a terminal REPL and a browser-based settings UI.

## Utility Targets

For debugging iTerm discovery and manually painting the deck without starting the full controller:

```bash
make util-iterm
make util-iterm-frontmost
make util-deck-list
make util-deck-fill LABEL=TEST BG=ffb000 FG=000000
make util-deck-key KEY=0 LABEL=T1 BG=ffb000 FG=000000
make util-deck-clear
make util-deck-demo
```

Useful knobs:

- `WAIT=5` keeps the process alive for a few seconds after painting the deck
- `BRIGHTNESS=40` sets deck brightness for the utility command
- `BG` and `FG` are hex colors without the leading `#`

## Settings UI

A settings page is available at `http://127.0.0.1:19830` while the controller is running. Type `settings` in the REPL to open it. From here you can configure:

- **Session Mapping** — assign `T1`/`T2`/`T3` to iTerm2 session-name substrings
- **Brightness** — Stream Deck brightness slider
- **Colors** — pick custom colors for status states, nav keys, and active window
- **Behavior** — hold threshold, poll interval, scroll speed, idle timeout
- **MIC key** — Whisprflow (fn) or custom shell command
- **Hooks** — one-click Claude Code hook installation

## Runtime Commands

Type these while the controller is running:

| Command | Description |
|---------|-------------|
| `brightness <0-100>` | Set Stream Deck brightness |
| `hold <seconds>` | Set hold threshold for MIC (default 0.5s) |
| `poll <seconds>` | Set poll interval (default 0.2s) |
| `mic <fn\|command>` | Set MIC action (`fn` = Whisprflow, or any shell command) |
| `mic learn` | Press a key to capture it as the MIC action |
| `settings` | Open settings in browser |
| `quit` | Exit |

Settings persist to `config.json` automatically.

## Menu Bar App (Optional)

For a standalone menu bar experience:

```bash
.venv/bin/python menubar.py
```

Or build a `.app` bundle:

```bash
.venv/bin/python setup.py py2app
open dist/ClawDeck.app
```

## How It Works

```
main.py (DeckController)
  ├── Stream Deck ←→ Key callbacks (press/release/hold)
  ├── AppleScript ←→ iTerm2 session discovery + activation
  ├── Quartz API  ←→ Keystroke generation for MIC learning
  ├── HTTP server ←→ Settings UI (settings.html)
  ├── /tmp/deck-status/*  ← Hook status files (read)
  └── deck-hook.sh   ← Hook status writer (called by Claude Code hooks)
```

Claude Code hooks fire on state changes (tool use, permission prompts, idle) and write status files. The controller polls those files, maps them to configured iTerm2 sessions by TTY, and updates the matching row on the deck.

## Terminal Support

The row mapper is built around **iTerm2** session names and TTYs. The controller terminal can be any terminal app, but the three Claude sessions you want on the deck should be iTerm2 sessions with stable names that match your `session_map` settings.

## Contributing

### Branch Workflow

Feature branches off `main` with pull requests. Squash merge to keep history clean.

### Versioning

[Semver](https://semver.org/). Version lives in `main.py` as `__version__`.

### Testing

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m pytest --cov=main tests/ -v
```

Host and rendering boundary contracts now run in the default unit suite with mocked iTerm2, Quartz, and Stream Deck dependencies.

Opt-in macOS smoke tests are available for live iTerm2, TTY, and hardware checks:

```bash
CLAWDECK_MAC_SMOKE=1 .venv/bin/python -m pytest -m mac_integration tests/test_mac_smoke.py -v
CLAWDECK_DECK_SMOKE=1 .venv/bin/python -m pytest -m mac_integration tests/test_mac_smoke.py -k streamdeck -v
```

## License

MIT
