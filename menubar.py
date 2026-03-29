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

import os
import subprocess
import sys
import threading
import webbrowser

import rumps

from clawdeck import DeckController
from clawdeck.constants import PROJECT_ROOT
from clawdeck.settings_server import SettingsServer

_app_instance = None


class ClawDeckApp(rumps.App):
    def __init__(self):
        super().__init__("ClawDeck", icon=None, title="\U0001f99e", quit_button=None)
        self.controller = None
        self._controller_thread = None
        self.settings_server = SettingsServer(lambda: self.controller)
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

        self._http_port = self.settings_server.start()

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
                self.controller.startup(start_settings_server=False)
                self.title = "\U0001f99e\u2713"
                self._update_menu_state(True)
            except RuntimeError as exc:
                rumps.notification("ClawDeck", "Error", str(exc))
                if self.controller:
                    self.controller.shutdown()
                self.controller = None
                self._update_menu_state(False)

        self._controller_thread = threading.Thread(target=run, daemon=True)
        self._controller_thread.start()

    def _stop_controller(self):
        if self.controller:
            self.controller.shutdown()
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
            self.controller.refresh_tty_map()
            self.controller.update_all_buttons()
        else:
            rumps.notification("ClawDeck", "", "Start the controller first.")

    def open_settings(self, _):
        if self._http_port:
            webbrowser.open(f"http://127.0.0.1:{self._http_port}/")

    def install_hooks(self, _):
        result = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "install_hooks.py")],
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
        self.settings_server.stop()
        rumps.quit_application()


if __name__ == "__main__":
    app = ClawDeckApp()
    _app_instance = app
    app.run()
