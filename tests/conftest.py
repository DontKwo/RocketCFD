"""Pytest fixtures and test helpers for RocketCFD."""  # noqa: 29
from __future__ import annotations

import subprocess
from collections.abc import Callable


def fake_subprocess_run(returncode: int = 0, stdout: str = "", stderr: str = "") -> Callable[..., subprocess.CompletedProcess]:
    """Return a subprocess.run monkeypatch target returning a fixed CompletedProcess."""

    def _fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)

    return _fake_run


class FakeOpenFOAMReaderTimeMixin:
    """Shared no-op time-selection method for fake pyvista reader test doubles."""

    def set_active_time_value(self, value: float) -> None:  # noqa: 21
        """Ignore active time selection in mocked reader tests."""
        del value
        return None
