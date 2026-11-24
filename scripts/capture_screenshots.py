"""Capture up-to-date 3D Viewport and Solver screenshots for RocketCFD Studio."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from playwright.sync_api import sync_playwright

REPO_DIR = Path(__file__).resolve().parent.parent


def _launch_browser(pw: Any) -> Any:
    """Launch SwiftShader-enabled headless Chromium first, falling back to Edge channel."""
    launch_args = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
    try:
        return pw.chromium.launch(headless=True, args=launch_args)
    except Exception:  # noqa: 10
        return pw.chromium.launch(channel="msedge", headless=True, args=launch_args)


def capture_screenshots(out_dir: Path, python_exe: str | None = None) -> None:
    """Boot loopback WebView server and capture 3D Viewport and Solver envelope PNGs."""
    out_resolved = out_dir.expanduser().resolve()
    out_resolved.mkdir(parents=True, exist_ok=True)
    shot_main = out_resolved / "01_main.png"
    shot_solver = out_resolved / "02_solver.png"

    proc = subprocess.Popen(
        [python_exe or sys.executable, "-m", "rocketcfd.gui.web_app", "--headless-server", "0"],
        cwd=str(REPO_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        url = ""
        deadline = time.monotonic() + 25.0
        while time.monotonic() < deadline and proc.stdout is not None:
            line = proc.stdout.readline().strip()
            if line.startswith("READY "):
                url = line.split(" ", 1)[1].strip()
                break
        if not url:
            raise RuntimeError("RocketCFD headless server failed to start.")

        with sync_playwright() as pw:
            browser = _launch_browser(pw)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector('[id="kpi.panels"]:not(:has-text("--"))', timeout=20000)
            page.wait_for_timeout(900)
            page.screenshot(path=str(shot_main), full_page=False)

            page.fill('[data-testid="flow.altitude_input"]', "2000")
            page.fill('[data-testid="flow.velocity_input"]', "520")
            page.fill('[data-testid="flow.alpha_input"]', "3.0")
            page.click('[data-testid="flow.compute_btn"]')
            page.wait_for_timeout(800)
            page.click('[data-testid="tabs.solver_btn"]')
            page.wait_for_timeout(400)
            page.screenshot(path=str(shot_solver), full_page=False)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture RocketCFD Studio desktop screenshots.")
    parser.add_argument("--out-dir", type=Path, default=REPO_DIR / "assets" / "screenshots")
    parser.add_argument("--py", default=None, help="Optional Python interpreter to launch GUI backend")
    args = parser.parse_args()
    capture_screenshots(args.out_dir, python_exe=args.py)
    sys.stdout.write(f"Saved RocketCFD screenshots into {args.out_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
