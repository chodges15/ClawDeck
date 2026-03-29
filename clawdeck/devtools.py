"""Developer utilities for inspecting host state and painting deck keys."""

import argparse
from contextlib import contextmanager
import sys
import time

from StreamDeck.DeviceManager import DeviceManager

from .config import ConfigStore, hex_to_rgb
from .constants import BRIGHTNESS, COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, TOTAL_KEYS
from .host import HostIntegration, match_session_name, session_pattern
from .render import DeckRenderer


def parse_color(value, fallback):
    """Parse a config-style hex color, or return the provided fallback."""
    if value in (None, ""):
        return fallback
    return hex_to_rgb(value)


def collect_iterm_snapshot(host=None, config_store=None):
    """Collect mapped row info plus raw iTerm session details."""
    host = host or HostIntegration()
    config_store = config_store or ConfigStore()
    config = config_store.load()
    sessions = host.get_iterm_sessions()
    frontmost = host.frontmost_session_name()

    rows = []
    for session_name in config["session_map"]:
        pattern = session_pattern(config, session_name)
        matched = None
        for info in sessions:
            if pattern and pattern.lower() in info["name"].lower():
                matched = dict(info)
                break
        if matched:
            matched["cwd"] = host.resolve_tty_cwd(matched["tty"])
        rows.append(
            {
                "session": session_name,
                "pattern": pattern,
                "match": matched,
            }
        )

    detailed_sessions = []
    for info in sessions:
        detailed = dict(info)
        detailed["cwd"] = host.resolve_tty_cwd(info["tty"])
        detailed["mapped_session"] = match_session_name(config, info["name"])
        detailed_sessions.append(detailed)

    return {
        "frontmost": frontmost,
        "rows": rows,
        "sessions": detailed_sessions,
    }


def print_iterm_snapshot(snapshot, out=None):
    """Print a human-readable snapshot gathered from iTerm and config."""
    out = out or sys.stdout
    print("Frontmost:", snapshot["frontmost"] or "-", file=out)
    print("", file=out)
    print("Configured rows:", file=out)
    for row in snapshot["rows"]:
        match = row["match"]
        if match:
            print(
                f"- {row['session']}: pattern={row['pattern']!r} tty={match['tty']} cwd={match['cwd'] or '-'} name={match['name']!r}",
                file=out,
            )
        else:
            print(
                f"- {row['session']}: pattern={row['pattern']!r} match=-",
                file=out,
            )

    print("", file=out)
    print("iTerm sessions:", file=out)
    if not snapshot["sessions"]:
        print("- none", file=out)
        return
    for info in snapshot["sessions"]:
        mapped = info["mapped_session"] or "-"
        print(
            f"- tty={info['tty']} mapped={mapped} cwd={info['cwd'] or '-'} name={info['name']!r}",
            file=out,
        )


@contextmanager
def open_first_deck():
    """Yield the first Stream Deck device that can be opened."""
    devices = DeviceManager().enumerate()
    if not devices:
        raise RuntimeError("No Stream Deck devices found.")

    last_error = None
    for device in devices:
        try:
            device.open()
            try:
                yield device
            finally:
                try:
                    device.close()
                except Exception:
                    pass
            return
        except Exception as exc:
            last_error = exc
            continue

    if last_error is None:
        raise RuntimeError("Could not open any Stream Deck interface.")
    raise RuntimeError(f"Could not open any Stream Deck interface: {last_error}")


def list_decks(out=None):
    """Print connected Stream Deck devices and basic capabilities."""
    out = out or sys.stdout
    devices = DeviceManager().enumerate()
    if not devices:
        print("No Stream Deck devices found.", file=out)
        return 1

    for index, device in enumerate(devices):
        deck_type = "unknown"
        try:
            deck_type = device.deck_type()
        except Exception:
            pass
        key_count = "unknown"
        try:
            key_count = device.key_count()
        except Exception:
            pass
        print(f"{index}: type={deck_type} keys={key_count}", file=out)
    return 0


def wait_after_update(wait_seconds=0, hold=False):
    """Delay exit long enough to inspect a rendered deck state."""
    if hold:
        input("Press Enter to release the deck...")
        return
    if wait_seconds and wait_seconds > 0:
        time.sleep(wait_seconds)


def paint_all_keys(deck, renderer, label, bg, fg):
    """Fill every key on the deck with the same rendered image."""
    image = renderer.render_button(deck, label, bg=bg, fg=fg)
    for key in range(deck.key_count()):
        deck.set_key_image(key, image)


def paint_key(deck, renderer, key, label, bg, fg):
    """Render one deck key with the supplied label and colors."""
    if key < 0 or key >= deck.key_count():
        raise ValueError(f"Key must be between 0 and {deck.key_count() - 1}")
    image = renderer.render_button(deck, label, bg=bg, fg=fg)
    deck.set_key_image(key, image)


def paint_demo(deck, renderer):
    """Paint the deck with a simple per-key color and index demo."""
    colors = [
        (180, 40, 40),
        (200, 120, 20),
        (190, 175, 20),
        (40, 150, 60),
        (40, 80, 200),
    ]
    for key in range(deck.key_count()):
        bg = colors[key % len(colors)]
        deck.set_key_image(deck_key := key, renderer.render_button(deck, str(deck_key), bg=bg))


def set_brightness(deck, brightness):
    """Set deck brightness without additional validation."""
    deck.set_brightness(brightness)


def cmd_iterm_info(_args):
    """Show the current configured and discovered iTerm snapshot."""
    print_iterm_snapshot(collect_iterm_snapshot())
    return 0


def cmd_iterm_frontmost(_args):
    """Print the current frontmost iTerm session name."""
    host = HostIntegration()
    print(host.frontmost_session_name() or "-")
    return 0


def cmd_deck_list(_args):
    """List connected Stream Deck devices."""
    return list_decks()


def cmd_deck_clear(args):
    """Blank every key on the first available deck."""
    renderer = DeckRenderer()
    with open_first_deck() as deck:
        set_brightness(deck, args.brightness)
        paint_all_keys(deck, renderer, "", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT)
        wait_after_update(args.wait, args.hold)
    return 0


def cmd_deck_fill(args):
    """Paint every key on the first available deck with one style."""
    renderer = DeckRenderer()
    bg = parse_color(args.bg, COLOR_BG_DEFAULT)
    fg = parse_color(args.fg, COLOR_FG_DEFAULT)
    with open_first_deck() as deck:
        set_brightness(deck, args.brightness)
        paint_all_keys(deck, renderer, args.label, bg, fg)
        wait_after_update(args.wait, args.hold)
    return 0


def cmd_deck_key(args):
    """Paint a single key on the first available deck."""
    renderer = DeckRenderer()
    bg = parse_color(args.bg, COLOR_BG_DEFAULT)
    fg = parse_color(args.fg, COLOR_FG_DEFAULT)
    with open_first_deck() as deck:
        set_brightness(deck, args.brightness)
        paint_key(deck, renderer, args.key, args.label, bg, fg)
        wait_after_update(args.wait, args.hold)
    return 0


def cmd_deck_demo(args):
    """Render the indexed demo pattern on the first available deck."""
    renderer = DeckRenderer()
    with open_first_deck() as deck:
        set_brightness(deck, args.brightness)
        paint_demo(deck, renderer)
        wait_after_update(args.wait, args.hold)
    return 0


def build_parser():
    """Build the CLI parser for `python -m clawdeck.devtools`."""
    parser = argparse.ArgumentParser(prog="python -m clawdeck.devtools")
    subparsers = parser.add_subparsers(dest="group", required=True)

    iterm_parser = subparsers.add_parser("iterm", help="Inspect iTerm-derived data")
    iterm_subparsers = iterm_parser.add_subparsers(dest="iterm_cmd", required=True)

    iterm_info = iterm_subparsers.add_parser("info", help="Show mapped and raw iTerm sessions")
    iterm_info.set_defaults(func=cmd_iterm_info)

    iterm_frontmost = iterm_subparsers.add_parser(
        "frontmost", help="Print the current frontmost iTerm session name"
    )
    iterm_frontmost.set_defaults(func=cmd_iterm_frontmost)

    deck_parser = subparsers.add_parser("deck", help="Directly manipulate the Stream Deck")
    deck_subparsers = deck_parser.add_subparsers(dest="deck_cmd", required=True)

    deck_list = deck_subparsers.add_parser("list", help="List detected Stream Deck devices")
    deck_list.set_defaults(func=cmd_deck_list)

    for name, help_text, func in [
        ("clear", "Blank every key", cmd_deck_clear),
        ("fill", "Paint every key with the same label/color", cmd_deck_fill),
        ("key", "Paint one key", cmd_deck_key),
        ("demo", "Paint all keys with index labels", cmd_deck_demo),
    ]:
        subparser = deck_subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--brightness", type=int, default=BRIGHTNESS)
        subparser.add_argument("--wait", type=float, default=0)
        subparser.add_argument("--hold", action="store_true")
        if name in {"fill", "key"}:
            subparser.add_argument("--label", default="TEST")
            subparser.add_argument("--bg", default="ffb000")
            subparser.add_argument("--fg", default="000000")
        if name == "key":
            subparser.add_argument("--key", type=int, required=True)
        subparser.set_defaults(func=func)

    return parser


def main(argv=None):
    """Parse arguments and dispatch the selected devtools command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
