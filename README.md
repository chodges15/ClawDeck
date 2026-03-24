# ClawDeck

Map an Elgato Stream Deck to a grid of terminal windows running Claude Code sessions. Each button shows the session's state — idle (blue), working (green), needs permission (red blink). Tap to switch windows, hold to dictate.

Built for the **Stream Deck Original** (15-key, 5x3 grid) on **macOS**.

## What It Does

- Tiles up to 14 terminal windows into a 5x3 screen grid
- Each Stream Deck button reflects Claude Code's live state via hooks
- Tap a button to activate that terminal window
- Hold a button to trigger Whisprflow / dictation
- Nav Mode for arrow keys and number selection (Claude multi-choice prompts)
- Amber screen border highlights the active window
- Snap-to-grid: drag a terminal and it auto-snaps to the nearest slot

### Button Colors

| Color | Meaning |
|-------|---------|
| Black | No Claude session |
| Blue | Idle — waiting for input |
| Green | Working — actively processing |
| Red (blinking) | Permission needed |
| Amber border | Active window |

### Modes

**Grid Mode** (default):
```
 T1   T2   T3   T4   T5
 T6   T7   T8   T9   T10
 T11  T12  T13  T14   ⏎
```
- Tap → activate window
- Tap active window → enter Nav Mode
- Hold any button → activate + trigger MIC (Whisprflow)
- Bottom-right → Enter key

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

- macOS (uses Quartz, AppKit, AppleScript for window management)
- [Homebrew](https://brew.sh)
- Elgato Stream Deck Original (15-key)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed

## Install

```bash
git clone https://github.com/YOUR_USERNAME/clawdeck.git
cd clawdeck
bash setup.sh
```

Setup will:
1. Install `hidapi` and Python 3.13 via Homebrew
2. Create a virtual environment and install dependencies
3. Offer to install Claude Code hooks into `~/.claude/settings.json`

On first run, you'll be prompted to grant **Accessibility** permissions to your terminal app (required for window management). If you use multiple terminal apps (e.g. Terminal.app for the controller and iTerm2 for Claude sessions), grant Accessibility to **all of them** in System Settings > Privacy & Security > Accessibility.

## Run

```bash
cd clawdeck
.venv/bin/python main.py
```

## Runtime Commands

Type these while the controller is running:

| Command | Description |
|---------|-------------|
| `tile` | Re-arrange windows into grid |
| `brightness <0-100>` | Set Stream Deck brightness |
| `hold <seconds>` | Set hold threshold for MIC (default 0.5s) |
| `poll <seconds>` | Set poll interval (default 0.2s) |
| `snap <on\|off>` | Toggle snap-to-grid |
| `mic <fn\|command>` | Set MIC action (`fn` = Whisprflow, or any shell command) |
| `mic learn` | Press a key to capture it as the MIC action |
| `settings` | Show current settings |
| `quit` | Exit |

Settings persist to `config.json` automatically.

## How It Works

```
main.py (DeckController)
  ├── Stream Deck ←→ Key callbacks (press/release/hold)
  ├── Quartz API  ←→ Window discovery, frontmost detection
  ├── AppleScript ←→ Window tiling, activation, keystroke sending
  ├── /tmp/deck-status/*  ← Hook status files (read)
  └── .deck-overlay.json  → Overlay position (write)
          │                              ▲
          ▼                              │
    overlay.py                    deck-hook.sh
    (amber border)                (called by Claude Code hooks)
```

Claude Code hooks fire on state changes (tool use, permission prompts, idle) and write status files. The controller polls these every 200ms and updates button colors accordingly.

## Terminal Apps Supported

Terminal.app and iTerm2 have full TTY mapping (status colors per window). Other apps (Warp, Alacritty, kitty, Hyper) will tile and activate but won't show per-session status colors.

## License

MIT
