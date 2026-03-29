#!/usr/bin/env python3
"""
ClawDeck Menu Bar App — wraps DeckController in a macOS menu bar interface.

Provides:
  - Start/Stop Stream Deck controller
  - Status indicator in menu bar
  - Settings window (local HTTP server + browser)
  - Session-map rescan
  - Install/update hooks
"""

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import rumps

from main import BRIGHTNESS, CONFIG_DEFAULTS, CONFIG_FILE, DeckController

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_HTML = os.path.join(SCRIPT_DIR, "settings.html")

_app_instance = None


def _normalize_saved_config(raw):
    config = dict(CONFIG_DEFAULTS)
    config["colors"] = dict(CONFIG_DEFAULTS["colors"])
    config["session_map"] = dict(CONFIG_DEFAULTS["session_map"])

    if not isinstance(raw, dict):
        return config

    colors = raw.get("colors", {})
    session_map = raw.get("session_map", {})
    for key, value in raw.items():
        if key in ("colors", "session_map"):
            continue
        config[key] = value
    if isinstance(colors, dict):
        config["colors"].update(colors)
    if isinstance(session_map, dict):
        config["session_map"].update(session_map)
    return config


class SettingsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/settings"):
            with open(SETTINGS_HTML, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/settings":
            config = _normalize_saved_config({})
            try:
                with open(CONFIG_FILE) as f:
                    config = _normalize_saved_config(json.load(f))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            self._json_response(config)
            return

        if path == "/api/status":
            app = _app_instance
            ctrl = app.controller if app else None
            if ctrl and ctrl.running:
                self._json_response(
                    {
                        "running": True,
                        "deck": ctrl.deck.deck_type() if ctrl.deck else "unknown",
                        "sessions": len(ctrl.slot_tty),
                    }
                )
            else:
                self._json_response({"running": False})
            return

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len else b""

        if path == "/api/settings":
            try:
                new_config = json.loads(body)
            except json.JSONDecodeError:
                self._json_response({"ok": False, "error": "Invalid JSON"}, 400)
                return

            app = _app_instance
            ctrl = app.controller if app else None
            if ctrl:
                old_session_map = dict(ctrl.config.get("session_map", {}))
                ctrl._apply_config_update(new_config)
                if ctrl.running:
                    if ctrl.deck:
                        try:
                            ctrl.deck.set_brightness(ctrl.config.get("brightness", BRIGHTNESS))
                        except Exception:
                            pass
                    if ctrl.config.get("session_map", {}) != old_session_map:
                        ctrl._build_tty_map()
                    ctrl._update_all_buttons()
            else:
                config = _normalize_saved_config({})
                try:
                    with open(CONFIG_FILE) as f:
                        config = _normalize_saved_config(json.load(f))
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
                config = _normalize_saved_config({**config, **new_config})
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
                    f.write("\n")

            self._json_response({"ok": True})
            return

        if path == "/api/hooks":
            result = subprocess.run(
                [sys.executable, os.path.join(SCRIPT_DIR, "install_hooks.py")],
                input="y\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (result.stdout + result.stderr).strip()
            self._json_response({"ok": result.returncode == 0, "output": output})
            return

        self.send_error(404)

    def _json_response(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ClawDeckApp(rumps.App):
    def __init__(self):
        super().__init__("ClawDeck", icon=None, title="\U0001f99e", quit_button=None)
        self.controller = None
        self._controller_thread = None
        self._http_server = None
        self._http_port = None

        self.menu = [
            rumps.MenuItem("Start", callback=self.toggle_controller),
            rumps.MenuItem("Rescan Sessions", callback=self.rescan_sessions),
            None,
            rumps.MenuItem("Settings...", callback=self.open_settings),
            rumps.MenuItem("Install Hooks", callback=self.install_hooks),
            None,
            rumps.MenuItem("Quit ClawDeck", callback=self.quit_app),
        ]

        self._start_http_server()

    def _start_http_server(self):
        for port in range(19830, 19850):
            try:
                server = HTTPServer(("127.0.0.1", port), SettingsHandler)
                self._http_server = server
                self._http_port = port
                threading.Thread(target=server.serve_forever, daemon=True).start()
                return
            except OSError:
                continue

    def toggle_controller(self, sender):
        if self.controller and self.controller.running:
            self._stop_controller()
            sender.title = "Start"
            self.title = "\U0001f99e"
        else:
            self._start_controller()
            sender.title = "Stop"

    def _start_controller(self):
        def run():
            try:
                self.controller = DeckController()
                self.controller._check_accessibility()

                from StreamDeck.DeviceManager import DeviceManager

                devices = DeviceManager().enumerate()
                if not devices:
                    rumps.notification(
                        "ClawDeck",
                        "No Stream Deck Found",
                        "Make sure your Stream Deck is plugged in.",
                    )
                    self.controller = None
                    self._update_menu_state(False)
                    return

                for dev in devices:
                    try:
                        dev.open()
                        self.controller.deck = dev
                        break
                    except Exception:
                        continue
                else:
                    rumps.notification(
                        "ClawDeck",
                        "Connection Failed",
                        "Could not open Stream Deck. Try unplugging and reconnecting.",
                    )
                    self.controller = None
                    self._update_menu_state(False)
                    return

                ctrl = self.controller
                ctrl.deck.reset()
                ctrl.deck.set_brightness(ctrl.config["brightness"])
                ctrl._build_tty_map()
                ctrl._clear_status_dir()
                ctrl._update_all_buttons()
                ctrl.deck.set_key_callback(ctrl._on_key_change)
                ctrl.running = True

                self.title = "\U0001f99e\u2713"
                self._update_menu_state(True)
                ctrl._poll_active_loop()
            except Exception as exc:
                rumps.notification("ClawDeck", "Error", str(exc))
                self.controller = None
                self._update_menu_state(False)

        self._controller_thread = threading.Thread(target=run, daemon=True)
        self._controller_thread.start()

    def _stop_controller(self):
        if self.controller:
            self.controller.running = False
            if self.controller.deck:
                try:
                    self.controller.deck.reset()
                    self.controller.deck.close()
                except Exception:
                    pass
            self.controller = None
        self._update_menu_state(False)

    def _update_menu_state(self, running):
        try:
            item = self.menu["Start"]
        except KeyError:
            try:
                item = self.menu["Stop"]
            except KeyError:
                return
        item.title = "Stop" if running else "Start"
        self.title = "\U0001f99e\u2713" if running else "\U0001f99e"

    def rescan_sessions(self, _):
        if self.controller and self.controller.running:
            self.controller._build_tty_map()
            self.controller._update_all_buttons()
        else:
            rumps.notification("ClawDeck", "", "Start the controller first.")

    def open_settings(self, _):
        if self._http_port:
            webbrowser.open(f"http://127.0.0.1:{self._http_port}/")

    def install_hooks(self, _):
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "install_hooks.py")],
            input="y\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            rumps.notification(
                "ClawDeck",
                "Hooks Installed",
                "Restart Claude Code sessions to pick up new hooks.",
            )
        else:
            rumps.notification(
                "ClawDeck",
                "Hook Install Failed",
                result.stderr[:200] if result.stderr else "Unknown error",
            )

    def quit_app(self, _):
        self._stop_controller()
        if self._http_server:
            self._http_server.shutdown()
        rumps.quit_application()


if __name__ == "__main__":
    app = ClawDeckApp()
    _app_instance = app
    app.run()
