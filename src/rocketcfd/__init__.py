"""RocketCFD public application entrypoint."""
from __future__ import annotations

from rocketcfd.gui.web_app import launch_cli


def main(argv: list[str] | None = None) -> int:  # noqa: 21
    """Launch the RocketCFD WebView Studio or self-test probe."""
    return launch_cli(argv)
