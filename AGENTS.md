# AGENTS.md

## Test Overview

ClawDeck's test suite is built to cover the controller logic in `main.py` without requiring live macOS UI automation or attached Stream Deck hardware during normal runs.

Current local baseline:

- `.venv/bin/python -m pytest -q`
  - `145 passed, 4 skipped`
- `.venv/bin/python -m pytest --cov=main --cov-report=term-missing -q`
  - `88%` coverage on `main.py`

## How The Suite Works

The default test run uses targeted stubs from [tests/conftest.py](/Users/chodges/src/ClawDeck/tests/conftest.py):

- Quartz and CoreFoundation are replaced with deterministic in-memory stubs.
- Stream Deck imports are stubbed before `main.py` is imported.
- Pillow is real, so rendering tests exercise actual image creation and cropping.
- `FakeDeck` captures button images, brightness changes, callbacks, and open/reset/close state.
- `controller`, `fake_deck`, `subprocess_result`, and `status_dir` are the main reusable fixtures.

This keeps the normal suite fast and sandbox-safe while still testing most controller behavior as contracts.

## Running Tests

Default suite:

```bash
.venv/bin/python -m pytest -q
```

Coverage:

```bash
.venv/bin/python -m pytest --cov=main --cov-report=term-missing -q
```

Opt-in smoke tests:

```bash
CLAWDECK_MAC_SMOKE=1 .venv/bin/python -m pytest -m mac_integration tests/test_mac_smoke.py -v
CLAWDECK_DECK_SMOKE=1 .venv/bin/python -m pytest -m mac_integration tests/test_mac_smoke.py -k streamdeck -v
```

`tests/test_mac_smoke.py` is skipped by default. Use it only on a real macOS machine with iTerm2 and, for the deck test, attached hardware.

## Test Map

| File | Purpose |
| --- | --- |
| [tests/test_config.py](/Users/chodges/src/ClawDeck/tests/test_config.py) | Config defaults and merge behavior. |
| [tests/test_colors.py](/Users/chodges/src/ClawDeck/tests/test_colors.py) | RGB/hex helpers and configured color lookup. |
| [tests/test_keys.py](/Users/chodges/src/ClawDeck/tests/test_keys.py) | Keystroke label formatting and font selection. |
| [tests/test_cwd.py](/Users/chodges/src/ClawDeck/tests/test_cwd.py) | Folder label formatting for `last`, `two`, `full`, and `off`. |
| [tests/test_layouts.py](/Users/chodges/src/ClawDeck/tests/test_layouts.py) | Row-model key mapping: session rows, label keys, info keys. |
| [tests/test_status.py](/Users/chodges/src/ClawDeck/tests/test_status.py) | Slot styling and nav button style resolution. |
| [tests/test_scroll.py](/Users/chodges/src/ClawDeck/tests/test_scroll.py) | Tool command summaries, scroll offset math, scroll-strip caching, mode-based redraw dispatch. |
| [tests/test_session_map.py](/Users/chodges/src/ClawDeck/tests/test_session_map.py) | Session-name-to-TTY mapping and direct permission approval writes. |
| [tests/test_status_ingestion.py](/Users/chodges/src/ClawDeck/tests/test_status_ingestion.py) | Hook status-file parsing, pending-to-permission inference, stale cleanup, and marquee cache invalidation. |
| [tests/test_controller_actions.py](/Users/chodges/src/ClawDeck/tests/test_controller_actions.py) | Key press flow, row/nav actions, REPL commands, and one-pass poll-loop behavior. |
| [tests/test_host_contracts.py](/Users/chodges/src/ClawDeck/tests/test_host_contracts.py) | External boundary contracts: AppleScript, `ps`/`lsof`, `/dev/<tty>` writes, Quartz MIC events, startup/shutdown flow. |
| [tests/test_render_contracts.py](/Users/chodges/src/ClawDeck/tests/test_render_contracts.py) | Button rendering, marquee cropping/wraparound, row rendering, and nav rendering. |
| [tests/test_settings_server.py](/Users/chodges/src/ClawDeck/tests/test_settings_server.py) | Embedded HTTP settings server endpoints, config updates, hook installer launch, and port fallback. |
| [tests/test_mac_smoke.py](/Users/chodges/src/ClawDeck/tests/test_mac_smoke.py) | Live macOS smoke checks for iTerm2 discovery/activation, real TTY approval, and optional Stream Deck enumeration. |

## Maintenance Notes

- Prefer adding unit tests first, using the existing fixtures, before reaching for smoke coverage.
- If you change an OS boundary in `main.py`, update [tests/test_host_contracts.py](/Users/chodges/src/ClawDeck/tests/test_host_contracts.py) so the exact subprocess or device contract stays explicit.
- If you change row rendering or marquee behavior, update [tests/test_render_contracts.py](/Users/chodges/src/ClawDeck/tests/test_render_contracts.py), [tests/test_scroll.py](/Users/chodges/src/ClawDeck/tests/test_scroll.py), and [tests/test_status_ingestion.py](/Users/chodges/src/ClawDeck/tests/test_status_ingestion.py) together.
- If you change settings API behavior, update [tests/test_settings_server.py](/Users/chodges/src/ClawDeck/tests/test_settings_server.py) rather than relying on manual browser checks.
- Keep smoke tests lightweight. They should only answer "does the real boundary basically work?" and should not duplicate the detailed contract assertions already covered by the default suite.
