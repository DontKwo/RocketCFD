"""Loopback HTTP and WebView Studio server for RocketCFD."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Any
from urllib.parse import urlparse
import urllib.request
import webbrowser

from rocketcfd.geometry import PanelMesh
from rocketcfd.gui.job_runner import JobManager, import_existing_results_payload
from rocketcfd.gui.studio_compute import (
    build_condition_payload,
    build_default_panel_mesh,
    build_defaults_payload,
    build_geometry_with_panel,
    build_tacc_script_payload,
    build_validation_payload,
    export_openfoam_case_payload,
    import_cad_payload,
)


def _install_exception_hook() -> None:
    """Install top-level exception hook for desktop GUI error reporting."""

    def _log_unhandled(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        del exc_tb
        sys.stderr.write(f"Unhandled RocketCFD Studio error ({exc_type.__name__}): {exc_value}\n")

    sys.excepthook = _log_unhandled


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


def find_chromium_browser() -> str | None:
    """Locate Edge or Chrome executable for standalone WebView window and screenshots."""
    if os.name == "nt":
        win_candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
        for candidate in win_candidates:
            if candidate and Path(candidate).is_file():
                return candidate

    posix_candidates = [
        "google-chrome",
        "chromium",
        "chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "msedge",
        "microsoft-edge",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for candidate in posix_candidates:
        if os.path.sep in candidate:
            if Path(candidate).is_file():
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


@dataclass
class StudioSession:
    """Thread-safe active geometry and background OpenFOAM job session."""

    panel_mesh: PanelMesh = field(default_factory=build_default_panel_mesh)
    jobs: JobManager = field(default_factory=JobManager)
    lock: threading.Lock = field(default_factory=threading.Lock)


class StudioHandler(BaseHTTPRequestHandler):
    """Serve static WebView Studio files and CFD calculation endpoints."""

    def __init__(self, *args: Any, static_dir: Path, assets_dir: Path, session: StudioSession, **kwargs: Any) -> None:
        self.static_dir = static_dir
        self.assets_dir = assets_dir
        self.session = session
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress HTTP access logs on stdout during CLI and self-test runs."""
        del format, args

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, target: Path) -> None:
        if not target.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Asset not found"})
            return
        mime, _ = mimetypes.guess_type(str(target))
        if target.suffix.lower() == ".js":
            mime = "application/javascript"
        content_type = mime or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type = f"{content_type}; charset=utf-8"
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict[str, Any]:
        raw_len = int(self.headers.get("Content-Length", "0") or "0")
        if raw_len <= 0:
            return {}
        return json.loads(self.rfile.read(raw_len).decode("utf-8"))

    def do_GET(self) -> None:
        """Handle static asset downloads, Three.js vendor modules, defaults, and job polling."""
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
        if route.startswith("/vendor/"):
            rel_name = route[len("/vendor/"):]
            candidate = (self.static_dir / "vendor" / rel_name).resolve()
            vendor_root = (self.static_dir / "vendor").resolve()
            if str(candidate).startswith(str(vendor_root)) and candidate.is_file():
                self._send_file(candidate)
                return
        if route == "/api/defaults":
            self._send_json(HTTPStatus.OK, build_defaults_payload())
            return
        if route.startswith("/api/jobs/"):
            job_id = route[len("/api/jobs/"):].strip("/")
            res = self.session.jobs.poll_job(job_id)
            self._send_json(HTTPStatus.OK if res.get("ok") else HTTPStatus.NOT_FOUND, res)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"Unknown route: {route}"})

    def do_POST(self) -> None:
        """Handle geometry, CAD import, solver, OpenFOAM jobs, validation, and case export."""
        route = urlparse(self.path).path
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Malformed JSON request body."})
            return

        if route == "/api/geometry":
            result, new_panel = build_geometry_with_panel(payload)
            if new_panel is not None:
                with self.session.lock:
                    self.session.panel_mesh = new_panel
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        if route == "/api/import_cad":
            result, cad_panel = import_cad_payload(payload)
            if cad_panel is not None:
                with self.session.lock:
                    self.session.panel_mesh = cad_panel
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        if route == "/api/export_case":
            with self.session.lock:
                current_panel = self.session.panel_mesh
            result = export_openfoam_case_payload(payload, active_panel=current_panel)
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        if route == "/api/sweep/start":
            with self.session.lock:
                current_panel = self.session.panel_mesh
            result = self.session.jobs.start_sweep(payload, current_panel)
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        if route == "/api/validation/run":
            result = self.session.jobs.start_validation(payload)
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        if route.startswith("/api/jobs/") and route.endswith("/cancel"):
            job_id = route[len("/api/jobs/"):-len("/cancel")].strip("/")
            result = self.session.jobs.cancel_job(job_id)
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.NOT_FOUND, result)
            return

        if route == "/api/results/import":
            result = import_existing_results_payload(str(payload.get("directory", "")))
            self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)
            return

        sync_handlers = {
            "/api/condition": build_condition_payload,
            "/api/validation": build_validation_payload,
            "/api/tacc/script": build_tacc_script_payload,
        }
        handler = sync_handlers.get(route)
        if handler is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"Unknown route: {route}"})
            return
        result = handler(payload)
        self._send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST, result)


def start_server(port: int = 0) -> tuple[ThreadingHTTPServer, int]:
    """Start the loopback HTTP server on an ephemeral or requested port."""
    root = resolve_repo_root()
    session = StudioSession()
    handler_cls = partial(StudioHandler, static_dir=resolve_static_dir(), assets_dir=root / "assets", session=session)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    return server, int(server.server_port)


def capture_screenshot(base_url: str, output_target: Path) -> None:
    """Capture headless WebView Studio screenshot with WebGL SwiftShader enabled."""
    resolved = output_target.expanduser().resolve()
    target_png = resolved if resolved.suffix.lower() == ".png" else resolved / "01_main.png"
    target_png.parent.mkdir(parents=True, exist_ok=True)
    browser = find_chromium_browser()
    if not browser:
        raise RuntimeError("No Chromium or Edge executable available for --screenshot.")
    gl_flags = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] if os.name != "nt" else []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile_dir:
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                *gl_flags,
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--no-first-run",
                "--no-default-browser-check",
                "--hide-scrollbars",
                "--virtual-time-budget=2800",
                f"--user-data-dir={profile_dir}",
                "--window-size=1440,900",
                f"--screenshot={target_png}",
                base_url,
            ],
            check=True,
            timeout=45,
        )
    if not target_png.is_file() or target_png.stat().st_size < 1000:
        raise RuntimeError(f"Screenshot missing or empty: {target_png}")
    sys.stdout.write(f"SCREENSHOT_OK {target_png}\n")
    sys.stdout.flush()


def run_self_test() -> int:
    """Verify static index, Three.js vendor module, defaults, and geometry APIs on loopback."""
    server, port = start_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(base_url, timeout=5) as resp:
            if resp.status != 200 or b"RocketCFD" not in resp.read():
                return 1
        with urllib.request.urlopen(f"{base_url}vendor/three.module.min.js", timeout=5) as resp:
            if resp.status != 200 or len(resp.read()) < 10000:
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
            if not geom_res.get("ok") or not geom_res.get("mesh3d", {}).get("positions"):
                return 1
        sys.stdout.write(f"SELF_TEST_OK {base_url}\n")
        sys.stdout.flush()
        return 0
    finally:
        server.shutdown()
        server.server_close()


def _launch_app_window(url: str, server: ThreadingHTTPServer) -> None:
    """Open standalone WebView Studio window and block until user closes it."""
    browser = find_chromium_browser()
    if browser:
        profile_root = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "RocketCFD" / "WindowProfile"
        profile_root.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            [
                browser,
                f"--app={url}",
                f"--user-data-dir={profile_root}",
                "--new-window",
                "--window-size=1440,900",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        proc.wait()
        server.shutdown()
        return
    webbrowser.open(url)
    server.serve_forever()


def launch_cli(argv: list[str] | None = None) -> int:
    """CLI entrypoint for GUI, --self-test, --screenshot, and --headless-server modes."""
    _install_exception_hook()
    parser = argparse.ArgumentParser(description="RocketCFD WebView Studio")
    parser.add_argument("--self-test", action="store_true", help="Verify server startup and exit cleanly.")
    parser.add_argument("--headless-server", type=int, default=None, help="Bind port for browser automation without opening a window.")
    parser.add_argument("--screenshot", type=Path, default=None, help="Capture GUI PNG screenshot and exit.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    port = args.headless_server if args.headless_server is not None else 0
    server, bound_port = start_server(port)
    url = f"http://127.0.0.1:{bound_port}/"

    if args.screenshot is not None:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            capture_screenshot(url, args.screenshot)
            return 0
        finally:
            server.shutdown()
            server.server_close()

    sys.stdout.write(f"READY {url}\n")
    sys.stdout.flush()
    try:
        if args.headless_server is not None:
            server.serve_forever()
        else:
            _launch_app_window(url, server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch_cli())
