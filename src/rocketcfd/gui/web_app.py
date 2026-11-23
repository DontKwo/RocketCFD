"""Loopback HTTP and WebView Studio server for RocketCFD."""
from __future__ import annotations

import argparse
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
import threading
from typing import Any
from urllib.parse import urlparse
import urllib.request
import webbrowser

from rocketcfd.gui.studio_compute import (
    build_condition_payload,
    build_defaults_payload,
    build_geometry_payload,
    build_validation_payload,
    export_openfoam_case_payload,
)


def resolve_repo_root() -> Path:
    """Resolve PyInstaller bundle root or repository root directory."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[3]


def resolve_static_dir() -> Path:
    """Locate static HTML/CSS/JS WebView assets in source or bundled layout."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "rocketcfd" / "gui" / "static"
    return Path(__file__).resolve().parent / "static"


class StudioHandler(BaseHTTPRequestHandler):
    """Serve static WebView Studio files and CFD calculation endpoints."""

    def __init__(self, *args: Any, static_dir: Path, assets_dir: Path, **kwargs: Any) -> None:
        self.static_dir = static_dir
        self.assets_dir = assets_dir
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress HTTP access logs on stdout during CLI and self-test runs."""
        del format, args

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, target: Path) -> None:
        if not target.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Asset not found"})
            return
        mime, _ = mimetypes.guess_type(str(target))
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict[str, Any]:
        raw_len = int(self.headers.get("Content-Length", "0") or "0")
        if raw_len <= 0:
            return {}
        return json.loads(self.rfile.read(raw_len).decode("utf-8"))

    def do_GET(self) -> None:
        """Handle static asset downloads and studio defaults query."""
        route = urlparse(self.path).path
        static_routes = {
            "/": self.static_dir / "index.html",
            "/index.html": self.static_dir / "index.html",
            "/styles.css": self.static_dir / "styles.css",
            "/app.js": self.static_dir / "app.js",
            "/icon.png": self.assets_dir / "icon.png",
        }
        if route in static_routes:
            self._send_file(static_routes[route])
            return
        if route == "/api/defaults":
            self._send_json(HTTPStatus.OK, build_defaults_payload())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"Unknown route: {route}"})

    def do_POST(self) -> None:
        """Handle geometry assembly, solver evaluation, validation, and case export."""
        route = urlparse(self.path).path
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Malformed JSON request body."})
            return

        handlers = {
            "/api/geometry": build_geometry_payload,
            "/api/condition": build_condition_payload,
            "/api/validation": build_validation_payload,
            "/api/export_case": export_openfoam_case_payload,
        }
        handler = handlers.get(route)
        if handler is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"Unknown route: {route}"})
            return
        result = handler(payload)
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        self._send_json(status, result)


def start_server(port: int = 0) -> tuple[ThreadingHTTPServer, int]:
    """Start the loopback HTTP server on an ephemeral or requested port."""
    root = resolve_repo_root()
    handler_cls = partial(StudioHandler, static_dir=resolve_static_dir(), assets_dir=root / "assets")
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    return server, int(server.server_port)


def run_self_test() -> int:
    """Verify static index, defaults, geometry, and condition endpoints on loopback."""
    server, port = start_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(base_url, timeout=5) as resp:
            if resp.status != 200 or b"RocketCFD" not in resp.read():
                return 1
        with urllib.request.urlopen(f"{base_url}api/defaults", timeout=5) as resp:
            defaults = json.loads(resp.read().decode("utf-8"))
            if not defaults.get("ok"):
                return 1
        geom_req = urllib.request.Request(
            f"{base_url}api/geometry",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(geom_req, timeout=15) as resp:
            geom_res = json.loads(resp.read().decode("utf-8"))
            if not geom_res.get("ok"):
                return 1
        sys.stdout.write(f"SELF_TEST_OK {base_url}\n")
        sys.stdout.flush()
        return 0
    finally:
        server.shutdown()
        server.server_close()


def launch_cli(argv: list[str] | None = None) -> int:
    """CLI entrypoint for GUI, --self-test, and --headless-server modes."""
    parser = argparse.ArgumentParser(description="RocketCFD WebView Studio")
    parser.add_argument("--self-test", action="store_true", help="Verify server startup and exit cleanly.")
    parser.add_argument("--headless-server", type=int, default=None, help="Bind port for browser automation without opening a window.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    port = args.headless_server if args.headless_server is not None else 0
    server, bound_port = start_server(port)
    url = f"http://127.0.0.1:{bound_port}/"
    sys.stdout.write(f"READY {url}\n")
    sys.stdout.flush()

    if args.headless_server is None:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch_cli())
