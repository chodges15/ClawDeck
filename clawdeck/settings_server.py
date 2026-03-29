from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import sys
import threading
from urllib.parse import urlparse

from .app_logging import logger
from .config import ConfigStore
from .constants import BRIGHTNESS, PROJECT_ROOT, SETTINGS_PORT_END, SETTINGS_PORT_START


class SettingsServer:
    def __init__(self, controller_provider, config_store=None):
        self._controller_provider = controller_provider
        self.config_store = config_store or ConfigStore()
        self._server = None
        self.port = None

    def _controller(self):
        return self._controller_provider()

    def _make_handler(self):
        server_ref = self
        settings_html_path = PROJECT_ROOT / "settings.html"

        class SettingsHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                path = urlparse(self.path).path
                controller = server_ref._controller()
                if path in ("/", "/settings"):
                    with open(settings_html_path, "rb") as handle:
                        content = handle.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content)
                elif path == "/api/settings":
                    config = controller.config if controller else server_ref.config_store.load()
                    self._json_response(config)
                elif path == "/api/status":
                    if controller and controller.running and controller.deck:
                        self._json_response(
                            {
                                "running": True,
                                "deck": controller.deck.deck_type(),
                                "sessions": len(controller.state.slot_tty),
                            }
                        )
                    else:
                        self._json_response({"running": False})
                else:
                    self.send_error(404)

            def do_POST(self):
                path = urlparse(self.path).path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len) if content_len else b""
                controller = server_ref._controller()

                if path == "/api/settings":
                    try:
                        new_config = json.loads(body)
                    except json.JSONDecodeError:
                        self._json_response({"ok": False, "error": "Invalid JSON"}, 400)
                        return

                    if controller:
                        old_session_map = dict(controller.config.get("session_map", {}))
                        controller._apply_config_update(new_config)

                        if controller.deck and controller.running:
                            try:
                                controller.deck.set_brightness(
                                    controller.config.get("brightness", BRIGHTNESS)
                                )
                            except Exception:
                                logger.warning(
                                    "Failed to set brightness via settings API",
                                    exc_info=True,
                                )

                            if controller.config.get("session_map", {}) != old_session_map:
                                controller._build_tty_map()

                            controller._update_all_buttons()
                    else:
                        config = server_ref.config_store.load()
                        config = server_ref.config_store.apply_update(
                            config, new_config, save=False
                        )
                        server_ref.config_store.save(config)

                    self._json_response({"ok": True})
                    return

                if path == "/api/hooks":
                    result = subprocess.run(
                        [sys.executable, str(PROJECT_ROOT / "install_hooks.py")],
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

        return SettingsHandler

    def start(self):
        handler_cls = self._make_handler()
        for port in range(SETTINGS_PORT_START, SETTINGS_PORT_END):
            try:
                self._server = HTTPServer(("127.0.0.1", port), handler_cls)
                threading.Thread(target=self._server.serve_forever, daemon=True).start()
                self.port = port
                return port
            except OSError:
                logger.debug("Port %d in use, trying next", port)
                continue
        return None

    def stop(self):
        if not self._server:
            return
        self._server.shutdown()
        if hasattr(self._server, "server_close"):
            self._server.server_close()
        self._server = None
        self.port = None
