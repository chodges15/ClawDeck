import io
import json
from types import MethodType, SimpleNamespace
from unittest.mock import patch


class FakeHTTPServer:
    instances = []

    def __init__(self, address, handler_cls):
        self.address = address
        self.handler_cls = handler_cls
        self.started = False
        FakeHTTPServer.instances.append(self)

    def serve_forever(self):
        self.started = True


class FakeThread:
    instances = []

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self.started = False
        FakeThread.instances.append(self)

    def start(self):
        self.started = True


def make_handler(handler_cls, path, body=b"", headers=None):
    handler = handler_cls.__new__(handler_cls)
    handler.path = path
    handler.headers = headers or {}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.status = None
    handler.sent_headers = []
    handler.error_code = None

    def send_response(self, code):
        self.status = code

    def send_header(self, key, value):
        self.sent_headers.append((key, value))

    def end_headers(self):
        return None

    def send_error(self, code):
        self.error_code = code

    handler.send_response = MethodType(send_response, handler)
    handler.send_header = MethodType(send_header, handler)
    handler.end_headers = MethodType(end_headers, handler)
    handler.send_error = MethodType(send_error, handler)
    return handler


def start_fake_server(controller, monkeypatch, tmp_path):
    import http.server

    FakeHTTPServer.instances.clear()
    FakeThread.instances.clear()
    monkeypatch.setattr(http.server, "HTTPServer", FakeHTTPServer)
    monkeypatch.setattr("threading.Thread", FakeThread)
    monkeypatch.setattr("main.SCRIPT_DIR", str(tmp_path))
    (tmp_path / "settings.html").write_text("<html>ok</html>")
    port = controller._start_settings_server()
    server = FakeHTTPServer.instances[0]
    return port, server.handler_cls


def test_start_settings_server_starts_first_available_port(controller, monkeypatch, tmp_path):
    port, _handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    assert port == 19830
    assert controller._settings_port == 19830
    assert len(FakeThread.instances) == 1
    assert FakeThread.instances[0].daemon is True
    assert FakeThread.instances[0].started is True


def test_settings_handler_get_endpoints(controller, monkeypatch, tmp_path, fake_deck):
    controller.running = True
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001", 5: "ttys002"}
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    root = make_handler(handler_cls, "/")
    root.do_GET()
    assert root.status == 200
    assert root.wfile.getvalue() == b"<html>ok</html>"

    settings = make_handler(handler_cls, "/api/settings")
    settings.do_GET()
    payload = json.loads(settings.wfile.getvalue())
    assert payload["brightness"] == controller.config["brightness"]

    status = make_handler(handler_cls, "/api/status")
    status.do_GET()
    payload = json.loads(status.wfile.getvalue())
    assert payload == {"running": True, "deck": fake_deck.deck_type(), "sessions": 2}

    missing = make_handler(handler_cls, "/missing")
    missing.do_GET()
    assert missing.error_code == 404


def test_settings_handler_settings_alias_and_status_false(controller, monkeypatch, tmp_path):
    controller.running = False
    controller.deck = None
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    alias = make_handler(handler_cls, "/settings")
    alias.do_GET()
    assert alias.status == 200

    status = make_handler(handler_cls, "/api/status")
    status.do_GET()
    assert json.loads(status.wfile.getvalue()) == {"running": False}

    alias.log_message("%s", "ignored")


def test_settings_handler_updates_config_and_refreshes_running_deck(controller, monkeypatch, tmp_path, fake_deck):
    controller.running = True
    controller.deck = fake_deck
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    with patch.object(controller, "_apply_config_update") as apply_mock:
        with patch.object(controller, "_build_tty_map") as build_mock:
            with patch.object(controller, "_update_all_buttons") as update_mock:
                apply_mock.side_effect = lambda updates: controller.config.update(
                    {"brightness": 25, "session_map": {"T1": "alpha", "T2": "", "T3": ""}}
                )
                body = json.dumps({"brightness": 25, "session_map": {"T1": "alpha"}}).encode()
                headers = {"Content-Length": str(len(body))}
                handler = make_handler(handler_cls, "/api/settings", body=body, headers=headers)
                handler.do_POST()

    assert handler.status == 200
    assert json.loads(handler.wfile.getvalue()) == {"ok": True}
    assert fake_deck.brightness == 25
    apply_mock.assert_called_once()
    build_mock.assert_called_once_with()
    update_mock.assert_called_once_with()


def test_settings_handler_swallow_brightness_errors(controller, monkeypatch, tmp_path):
    broken_deck = SimpleNamespace(
        set_brightness=lambda value: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    controller.running = True
    controller.deck = broken_deck
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    with patch("main.logger.warning") as warn_mock:
        with patch.object(controller, "_apply_config_update") as apply_mock:
            with patch.object(controller, "_update_all_buttons") as update_mock:
                apply_mock.side_effect = lambda updates: controller.config.update({"brightness": 33})
                body = json.dumps({"brightness": 33}).encode()
                headers = {"Content-Length": str(len(body))}
                handler = make_handler(handler_cls, "/api/settings", body=body, headers=headers)
                handler.do_POST()

    assert handler.status == 200
    warn_mock.assert_called_once()
    update_mock.assert_called_once_with()


def test_settings_handler_rejects_invalid_json(controller, monkeypatch, tmp_path):
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    handler = make_handler(
        handler_cls,
        "/api/settings",
        body=b"{bad json",
        headers={"Content-Length": "9"},
    )
    handler.do_POST()

    assert handler.status == 400
    assert json.loads(handler.wfile.getvalue()) == {"ok": False, "error": "Invalid JSON"}


def test_settings_handler_runs_hook_installer(controller, monkeypatch, tmp_path, subprocess_result):
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    with patch("main.subprocess.run", return_value=subprocess_result(stdout="installed\n")) as run_mock:
        handler = make_handler(handler_cls, "/api/hooks")
        handler.do_POST()

    assert handler.status == 200
    assert json.loads(handler.wfile.getvalue()) == {"ok": True, "output": "installed"}
    run_mock.assert_called_once()


def test_settings_handler_unknown_post_returns_404(controller, monkeypatch, tmp_path):
    _port, handler_cls = start_fake_server(controller, monkeypatch, tmp_path)

    handler = make_handler(handler_cls, "/api/nope")
    handler.do_POST()

    assert handler.error_code == 404


def test_start_settings_server_skips_busy_ports(controller, monkeypatch, tmp_path):
    import http.server

    calls = {"count": 0}

    class BusyThenOK(FakeHTTPServer):
        def __init__(self, address, handler_cls):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("busy")
            super().__init__(address, handler_cls)

    FakeHTTPServer.instances.clear()
    FakeThread.instances.clear()
    monkeypatch.setattr(http.server, "HTTPServer", BusyThenOK)
    monkeypatch.setattr("threading.Thread", FakeThread)
    monkeypatch.setattr("main.SCRIPT_DIR", str(tmp_path))
    (tmp_path / "settings.html").write_text("<html>ok</html>")

    port = controller._start_settings_server()

    assert port == 19831
