"""Top-level controller that coordinates host, input, status, and rendering."""

import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from StreamDeck.DeviceManager import DeviceManager

from .app_logging import logger
from .config import CONFIG_DEFAULTS, ConfigStore
from .constants import (
    ACTIVE_CWD_REFRESH_SEC,
    BLINK_INTERVAL,
    BRIGHTNESS,
    HOLD_THRESHOLD_SEC,
    MODE_NAV,
    MODE_ROW,
    NAV_KEYMAP,
    POLL_INTERVAL,
    STATUS_DIR,
    TOTAL_KEYS,
    TTY_MAP_REFRESH_SEC,
)
from .host import (
    HostIntegration,
    match_session_info,
    match_session_name,
    normalize_tty_name,
    session_matches_pattern,
    session_pattern,
)
from .input import InputController
from .layout import key_info_index, key_is_label, key_to_session, session_label_key
from .render import DeckRenderer
from .settings_server import SettingsServer
from .state import ControllerState
from .status import StatusReader
from .version import __version__


class DeckController:
    """Drive the Stream Deck UI and keep it in sync with iTerm and Claude state."""

    def __init__(self):
        """Initialize collaborators, state, and lazy runtime resources."""
        self.config_store = ConfigStore()
        self.config = self.config_store.load()
        self.state = ControllerState()
        self.deck = None
        self.running = False
        self._settings_port = None
        self._lock = threading.Lock()
        self._poller = None

        self.host = HostIntegration()
        self.input = InputController()
        self.renderer = DeckRenderer(self.config_store)
        self.status_reader = StatusReader()
        self.settings_server = SettingsServer(lambda: self, self.config_store)

    @property
    def mode(self):
        return self.state.mode

    @mode.setter
    def mode(self, value):
        self.state.mode = value

    @property
    def active_slot(self):
        return self.state.active_slot

    @active_slot.setter
    def active_slot(self, value):
        self.state.active_slot = value

    @property
    def slot_tty(self):
        return self.state.slot_tty

    @slot_tty.setter
    def slot_tty(self, value):
        self.state.slot_tty = value

    @property
    def slot_cwd(self):
        return self.state.slot_cwd

    @slot_cwd.setter
    def slot_cwd(self, value):
        self.state.slot_cwd = value

    @property
    def slot_status(self):
        return self.state.slot_status

    @slot_status.setter
    def slot_status(self, value):
        self.state.slot_status = value

    @property
    def slot_tool_info(self):
        return self.state.slot_tool_info

    @slot_tool_info.setter
    def slot_tool_info(self, value):
        self.state.slot_tool_info = value

    @property
    def scroll_offsets(self):
        return self.state.scroll_offsets

    @scroll_offsets.setter
    def scroll_offsets(self, value):
        self.state.scroll_offsets = value

    @property
    def scroll_images(self):
        return self.state.scroll_images

    @scroll_images.setter
    def scroll_images(self, value):
        self.state.scroll_images = value

    @property
    def scroll_text(self):
        return self.state.scroll_text

    @scroll_text.setter
    def scroll_text(self, value):
        self.state.scroll_text = value

    @property
    def blink_on(self):
        return self.state.blink_on

    @blink_on.setter
    def blink_on(self, value):
        self.state.blink_on = value

    @property
    def font_xs(self):
        return self.renderer.font_xs

    @font_xs.setter
    def font_xs(self, value):
        self.renderer.font_xs = value

    @property
    def font_sm(self):
        return self.renderer.font_sm

    @font_sm.setter
    def font_sm(self, value):
        self.renderer.font_sm = value

    @property
    def font_md(self):
        return self.renderer.font_md

    @font_md.setter
    def font_md(self, value):
        self.renderer.font_md = value

    @property
    def font_lg(self):
        return self.renderer.font_lg

    @font_lg.setter
    def font_lg(self, value):
        self.renderer.font_lg = value

    @property
    def _last_tty_refresh(self):
        return self.state.last_tty_refresh

    @_last_tty_refresh.setter
    def _last_tty_refresh(self, value):
        self.state.last_tty_refresh = value

    @property
    def _last_active_cwd_check(self):
        return self.state.last_active_cwd_check

    @_last_active_cwd_check.setter
    def _last_active_cwd_check(self, value):
        self.state.last_active_cwd_check = value

    @property
    def _last_blink_toggle(self):
        return self.state.last_blink_toggle

    @_last_blink_toggle.setter
    def _last_blink_toggle(self, value):
        self.state.last_blink_toggle = value

    def apply_config_update(self, updates, save=True):
        """Apply a config update through the shared config store."""
        self.config = self.config_store.apply_update(self.config, updates, save=save)

    def refresh_tty_map(self):
        """Rebuild cached session-to-TTY and TTY-to-CWD mappings."""
        self._build_tty_map()
        return self.state.slot_tty, self.state.slot_cwd

    def update_all_buttons(self):
        """Redraw the deck if a hardware device is currently open."""
        if self.deck:
            self._update_all_buttons()

    # Backward-compatible delegate surface for existing callers/tests.

    def _normalize_config(self, raw):
        return self.config_store.normalize(raw)

    def _load_config(self):
        return self.config_store.load()

    def _save_config(self):
        self.config_store.save(self.config)

    def _apply_config_update(self, updates, save=True):
        self.apply_config_update(updates, save=save)

    def _color(self, key, fallback):
        return self.config_store.color(self.config, key, fallback)

    def _key_to_session(self, key):
        return key_to_session(key)

    def _session_label_key(self, session):
        return session_label_key(session)

    def _key_is_label(self, key):
        return key_is_label(key)

    def _key_info_index(self, key):
        return key_info_index(key)

    def _session_pattern(self, session):
        return session_pattern(self.config, session)

    def _match_session_name(self, session_name):
        return match_session_name(self.config, session_name)

    def _match_session_info(self, info):
        return match_session_info(self.config, info)

    def _normalize_tty_name(self, tty_name):
        return normalize_tty_name(tty_name)

    def _check_accessibility(self):
        return self.host.check_accessibility()

    def _get_iterm_sessions(self):
        return self.host.get_iterm_sessions()

    def _build_tty_map(self):
        tty_map = {}
        cwd_map = {}
        sessions = self._get_iterm_sessions()

        for session in CONFIG_DEFAULTS["session_map"]:
            pattern = self._session_pattern(session)
            if not pattern:
                continue
            for info in sessions:
                if session_matches_pattern(pattern, info):
                    label_key = self._session_label_key(session)
                    tty_map[label_key] = info["tty"]
                    cwd = self._resolve_tty_cwd(info["tty"])
                    if cwd:
                        cwd_map[label_key] = cwd
                    break

        self.state.slot_tty = tty_map
        self.state.slot_cwd = cwd_map

    def _resolve_tty_cwd(self, tty_name):
        return self.host.resolve_tty_cwd(tty_name)

    def _format_cwd(self, path):
        return self.renderer.format_cwd(self.config, path)

    def _frontmost_session_name(self):
        return self.host.frontmost_session_name()

    def _get_frontmost_slot(self):
        return self.host.get_frontmost_slot(self.config)

    def _normalize_tool_info(self, raw):
        return self.status_reader.normalize_tool_info(raw)

    def _read_status_files(self):
        snapshot = self.status_reader.read(
            self.state.slot_tty,
            self.config,
            self.renderer.format_tool_command,
            self.state.scroll_text,
        )
        self._apply_status_snapshot(snapshot)

    def _trigger_mic(self):
        self.input.trigger_mic(self.config)

    def _learn_keystroke(self):
        self.input.learn_keystroke(self.config, self.config_store)

    def _send_key(self, key_name):
        self.input.send_key(key_name)

    def _pick_font(self, label):
        return self.renderer.pick_font(label)

    def _button_dimensions(self):
        return self.renderer.button_dimensions(self.deck)

    def _render_button(self, label, **kwargs):
        return self.renderer.render_button(self.deck, label, **kwargs)

    def _first_display_value(self, value):
        return self.renderer.first_display_value(value)

    def _format_tool_command(self, tool_info):
        return self.renderer.format_tool_command(tool_info)

    def _render_scroll_strip(self, text):
        return self.renderer.render_scroll_strip(self.deck, self.config, text)

    def _ensure_scroll_strip(self, label_key):
        text = self._format_tool_command(self.state.slot_tool_info.get(label_key))
        if label_key not in self.state.scroll_images or self.state.scroll_text.get(label_key) != text:
            self.state.scroll_images[label_key] = self._render_scroll_strip(text)
            self.state.scroll_text[label_key] = text
            self.state.scroll_offsets[label_key] = 0
        return self.state.scroll_images[label_key]

    def _render_scroll_button(self, strip, offset, button_idx):
        return self.renderer.render_scroll_button(self.deck, strip, offset, button_idx)

    def _advance_scroll_offset(self, label_key, strip_width):
        return self.renderer.advance_scroll_offset(
            self.state, self.config, label_key, strip_width
        )

    def _advance_scroll_offsets(self):
        changed = False
        for label_key, status in self.state.slot_status.items():
            if status != "permission":
                continue
            strip = self._ensure_scroll_strip(label_key)
            old_offset = self.state.scroll_offsets.get(label_key, 0)
            new_offset = self._advance_scroll_offset(label_key, strip.width)
            if new_offset != old_offset:
                changed = True
        return changed

    def _update_all_buttons(self):
        if self.state.mode == MODE_NAV:
            self._draw_nav_mode()
        else:
            self._draw_row_mode()

    def _get_slot_style(self, slot):
        return self.renderer.get_slot_style(self.config, self.state, slot)

    def _draw_row_mode(self):
        if not self.deck:
            return
        for session in CONFIG_DEFAULTS["session_map"]:
            label_key = self._session_label_key(session)
            bg, fg, border = self._get_slot_style(label_key)
            self.deck.set_key_image(
                label_key,
                self._render_button(session, bg=bg, fg=fg, border_color=border),
            )

            info_keys = range(label_key + 1, label_key + 5)
            status = self.state.slot_status.get(label_key)
            is_mapped = label_key in self.state.slot_tty

            if not is_mapped:
                for key in info_keys:
                    self.deck.set_key_image(
                        key, self._render_button("", bg=(0, 0, 0), fg=(255, 255, 255))
                    )
                continue

            if status == "permission":
                strip = self._ensure_scroll_strip(label_key)
                offset = self.state.scroll_offsets.get(label_key, 0)
                for button_idx, key in enumerate(info_keys):
                    self.deck.set_key_image(
                        key, self._render_scroll_button(strip, offset, button_idx)
                    )
                continue

            subtitle = None
            raw_cwd = self.state.slot_cwd.get(label_key)
            if raw_cwd and self.config.get("button_labels", True):
                subtitle = self._format_cwd(raw_cwd)

            first_key = label_key + 1
            self.deck.set_key_image(
                first_key,
                self._render_button("", bg=(0, 0, 0), fg=(255, 255, 255), subtitle=subtitle),
            )
            for key in range(first_key + 1, label_key + 5):
                self.deck.set_key_image(
                    key, self._render_button("", bg=(0, 0, 0), fg=(255, 255, 255))
                )

    def _get_nav_style(self, key):
        return self.renderer.get_nav_style(self.config, key)

    def _draw_nav_mode(self):
        if not self.deck:
            return
        for key in range(TOTAL_KEYS):
            border = self._color("active", (255, 176, 0)) if key == self.state.active_slot else None
            style = self._get_nav_style(key)
            if style:
                self.deck.set_key_image(
                    key,
                    self._render_button(
                        style["label"],
                        bg=style["bg"],
                        fg=style["fg"],
                        border_color=border,
                    ),
                )
            else:
                self.deck.set_key_image(
                    key,
                    self._render_button("", bg=(15, 15, 15), border_color=border),
                )

    def _start_settings_server(self):
        return self.start_settings_server()

    def _activate_session(self, session):
        ok = self.host.activate_session(self.config, session)
        if ok:
            self.state.active_slot = session_label_key(session)
        return ok

    def _approve_permission(self, session):
        label_key = session_label_key(session)
        tty_name = self.state.slot_tty.get(label_key)
        if not tty_name:
            return False
        return self.host.approve_permission(tty_name)

    def _apply_status_snapshot(self, snapshot):
        for slot in snapshot.clear_scroll_slots:
            self.state.scroll_offsets.pop(slot, None)
            self.state.scroll_images.pop(slot, None)
            self.state.scroll_text.pop(slot, None)

        for slot in snapshot.reset_scroll_slots:
            self.state.scroll_offsets[slot] = 0
            self.state.scroll_images.pop(slot, None)
            self.state.scroll_text.pop(slot, None)

        self.state.slot_status = snapshot.slot_status
        self.state.slot_tool_info = snapshot.slot_tool_info

    def _on_key_change(self, deck, key, pressed):
        with self._lock:
            self._handle_key(key, pressed)

    def _handle_key(self, key, pressed):
        if self.state.mode == MODE_NAV:
            if pressed:
                self._handle_nav_key(key)
            return

        if not self._key_is_label(key):
            return

        session = self._key_to_session(key)
        if session is None:
            return

        if pressed:
            self.state.key_press_time[key] = time.time()
            return

        press_time = self.state.key_press_time.pop(key, None)
        if press_time is None:
            return

        held = time.time() - press_time
        if held >= self.config.get("hold_threshold", HOLD_THRESHOLD_SEC):
            self._activate_session(session)
            self._update_all_buttons()
            self._trigger_mic()
            return

        self._handle_row_key(session)

    def _handle_row_key(self, session):
        label_key = session_label_key(session)

        if self.state.slot_status.get(label_key) == "permission":
            self._approve_permission(session)
            return

        if label_key == self.state.active_slot:
            self._activate_session(session)
            self.state.mode = MODE_NAV
            self._update_all_buttons()
            return

        if self._activate_session(session):
            self._update_all_buttons()

    def _handle_nav_key(self, key):
        action = NAV_KEYMAP.get(key)
        if action is None:
            return

        kind, value = action

        if kind == "back":
            self.state.mode = MODE_ROW
            self._update_all_buttons()
        elif kind == "num":
            self._send_key(value)
        elif kind == "arrow":
            self._send_key(value)
        elif kind == "whisprflow":
            self._trigger_mic()
        elif kind == "enter":
            self._send_key("Return")

    def _poll_active_loop(self):
        consecutive_errors = 0
        while self.running:
            try:
                with self._lock:
                    if self.state.mode == MODE_ROW:
                        needs_redraw = False
                        now = time.time()

                        if now - self.state.last_tty_refresh >= TTY_MAP_REFRESH_SEC:
                            old_ttys = dict(self.state.slot_tty)
                            old_cwds = dict(self.state.slot_cwd)
                            self._build_tty_map()
                            self.state.last_tty_refresh = now
                            if self.state.slot_tty != old_ttys or self.state.slot_cwd != old_cwds:
                                needs_redraw = True

                        slot = self._get_frontmost_slot()
                        if slot != self.state.active_slot:
                            self.state.active_slot = slot
                            needs_redraw = True

                        if (
                            self.state.active_slot is not None
                            and now - self.state.last_active_cwd_check >= ACTIVE_CWD_REFRESH_SEC
                        ):
                            tty = self.state.slot_tty.get(self.state.active_slot)
                            if tty:
                                cwd = self._resolve_tty_cwd(tty)
                                old_cwd = self.state.slot_cwd.get(self.state.active_slot)
                                if cwd and cwd != old_cwd:
                                    self.state.slot_cwd[self.state.active_slot] = cwd
                                    needs_redraw = True
                            self.state.last_active_cwd_check = now

                        old_status = dict(self.state.slot_status)
                        old_tool_info = dict(self.state.slot_tool_info)
                        self._read_status_files()
                        if (
                            self.state.slot_status != old_status
                            or self.state.slot_tool_info != old_tool_info
                        ):
                            needs_redraw = True

                        if now - self.state.last_blink_toggle >= BLINK_INTERVAL:
                            self.state.blink_on = not self.state.blink_on
                            self.state.last_blink_toggle = now
                            if "permission" in self.state.slot_status.values():
                                needs_redraw = True

                        if self._advance_scroll_offsets():
                            needs_redraw = True

                        if needs_redraw:
                            self._update_all_buttons()

                consecutive_errors = 0
            except Exception:
                consecutive_errors += 1
                if consecutive_errors <= 10 or consecutive_errors % 100 == 0:
                    level = logging.ERROR if consecutive_errors >= 10 else logging.WARNING
                    logger.log(
                        level,
                        "Poll loop error (consecutive: %d)",
                        consecutive_errors,
                        exc_info=True,
                    )

            time.sleep(self.config.get("poll_interval", POLL_INTERVAL))

    def _handle_command(self, raw):
        """Handle a single interactive command entered on stdin."""
        parts = raw.split(None, 1)
        if not parts:
            return
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if cmd == "help":
            print("━━━ Commands ━━━")
            print("  brightness <0-100>    Set Stream Deck brightness")
            print("  hold <seconds>        Set hold threshold for Whisprflow")
            print("  poll <seconds>        Set poll interval")
            print("  mic <fn|command>      Set MIC action")
            print("  mic learn             Capture the next keystroke as MIC")
            print("  settings              Open settings in browser")
            print("  quit                  Exit")
            return

        if cmd == "brightness":
            if arg is None:
                print(f"  brightness = {self.config['brightness']}")
                return
            try:
                val = int(arg)
                if not 0 <= val <= 100:
                    raise ValueError
            except ValueError:
                print("  Usage: brightness <0-100>")
                return
            self.config["brightness"] = val
            if self.deck:
                self.deck.set_brightness(val)
            self._save_config()
            print(f"  brightness → {val}")
            return

        if cmd == "hold":
            if arg is None:
                print(f"  hold = {self.config['hold_threshold']}s")
                return
            try:
                val = float(arg)
                if val <= 0:
                    raise ValueError
            except ValueError:
                print("  Usage: hold <seconds>")
                return
            self.config["hold_threshold"] = val
            self._save_config()
            print(f"  hold → {val}s")
            return

        if cmd == "poll":
            if arg is None:
                print(f"  poll = {self.config['poll_interval']}s")
                return
            try:
                val = float(arg)
                if val <= 0:
                    raise ValueError
            except ValueError:
                print("  Usage: poll <seconds>")
                return
            self.config["poll_interval"] = val
            self._save_config()
            print(f"  poll → {val}s")
            return

        if cmd == "mic":
            if arg is None:
                mic_cmd = self.config["mic_command"]
                if isinstance(mic_cmd, dict):
                    print(f"  mic = {mic_cmd.get('label', mic_cmd)}")
                else:
                    print(f"  mic = {mic_cmd}")
                return
            if arg.lower() == "learn":
                self._learn_keystroke()
                return
            self.config["mic_command"] = arg
            self._save_config()
            print(f"  mic → {arg}")
            return

        if cmd == "settings":
            if self._settings_port:
                import webbrowser

                webbrowser.open(f"http://127.0.0.1:{self._settings_port}/")
                print("  Opened settings in browser")
            else:
                print("━━━ Settings ━━━")
                for key, value in self.config.items():
                    print(f"  {key} = {value}")
            return

        if cmd in ("quit", "exit", "q"):
            raise SystemExit

        print(f"  Unknown command: {cmd} (type 'help' for commands)")

    def _clear_status_dir(self):
        """Remove stale status files left behind by earlier runs."""
        os.makedirs(STATUS_DIR, exist_ok=True)
        for file_path in Path(STATUS_DIR).iterdir():
            try:
                file_path.unlink()
            except PermissionError:
                logger.debug("Could not unlink %s, falling back to rm", file_path)
                subprocess.run(["rm", "-f", str(file_path)], capture_output=True)

    def _open_deck(self):
        """Open the first accessible Stream Deck interface."""
        devices = DeviceManager().enumerate()
        if not devices:
            raise RuntimeError(
                "No Stream Deck found. Make sure it's plugged in.\n"
                "Also verify: brew install hidapi && pip install streamdeck"
            )

        logger.info("Found %d HID interface(s), attempting to open...", len(devices))
        for index, device in enumerate(devices):
            try:
                device.open()
                self.deck = device
                logger.info("Opened interface %d: %s", index, device.deck_type())
                return
            except Exception as exc:
                logger.warning("Interface %d failed: %s", index, exc)

        raise RuntimeError(
            "ERROR: Could not open any Stream Deck interface.\n"
            "If this is a permissions issue, try: sudo python main.py"
        )

    def start_settings_server(self):
        """Start the embedded settings server and return its bound port."""
        self._settings_port = self.settings_server.start()
        return self._settings_port

    def startup(self, start_settings_server=True):
        """Initialize hardware, render the initial UI, and launch the poll loop."""
        self._check_accessibility()
        self._open_deck()

        self.deck.reset()
        self.deck.set_brightness(self.config["brightness"])

        key_count = self.deck.key_count()
        logger.info("Connected: %s (%d keys)", self.deck.deck_type(), key_count)
        if key_count != TOTAL_KEYS:
            logger.warning(
                "Expected %d keys but deck has %d — row layout may not work correctly",
                TOTAL_KEYS,
                key_count,
            )
            print(f"Warning: this script expects {TOTAL_KEYS} keys but your deck has {key_count}.")

        self._build_tty_map()
        self._clear_status_dir()
        self._update_all_buttons()
        self.deck.set_key_callback(self._on_key_change)

        if start_settings_server:
            self._start_settings_server()

        self.running = True
        self._poller = threading.Thread(target=self._poll_active_loop, daemon=True)
        self._poller.start()
        return self._settings_port

    def shutdown(self):
        """Stop background work and release hardware and server resources."""
        self.running = False
        if self.deck:
            self.deck.reset()
            self.deck.close()
            self.deck = None
        self.settings_server.stop()
        self._settings_port = None

    def run(self):
        """Run the interactive controller until the user exits."""
        try:
            settings_port = self.startup(start_settings_server=True)
        except RuntimeError as exc:
            print(str(exc))
            sys.exit(1)

        amber = "\033[38;5;214m"
        dim = "\033[2m"
        reset = "\033[0m"
        print(
            f"""
{amber}  ██████╗██╗      █████╗ ██╗    ██╗{reset}
{amber} ██╔════╝██║     ██╔══██╗██║    ██║{reset}
{amber} ██║     ██║     ███████║██║ █╗ ██║{reset}
{amber} ██║     ██║     ██╔══██║██║███╗██║{reset}
{amber} ╚██████╗███████╗██║  ██║╚███╔███╔╝{reset}
{amber}  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝{reset}  {dim}v{__version__}{reset}
"""
        )
        print("  Type 'help' for commands")
        if settings_port:
            print(f"  Settings UI: http://127.0.0.1:{settings_port}")
        print()

        try:
            while True:
                cmd = input().strip()
                self._handle_command(cmd)
        except (KeyboardInterrupt, EOFError, SystemExit):
            pass
        finally:
            print("\nShutting down...")
            self.shutdown()
            print("Done.")
