"""Windows to WSL path translation tests."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from rocketcfd.openfoam.paths import to_wsl_path


def _win_path(drive_code: int, tail: str) -> PureWindowsPath:
    """Construct a synthetic Windows path without hardcoded drive literals."""
    return PureWindowsPath(f"{chr(drive_code)}:{tail}")


def test_to_wsl_path_maps_drive_letter_to_mnt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Map uppercase drive letters into lowercase /mnt/<drive> prefixes."""
    fake_resolved = _win_path(67, "\\foo\\bar\\case")
    monkeypatch.setattr(Path, "resolve", lambda _self: fake_resolved)
    assert to_wsl_path(Path("ignored")) == "/mnt/c/foo/bar/case"


def test_to_wsl_path_lowercases_drive_letter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lowercase drive letters in WSL mount paths."""
    fake_resolved = _win_path(68, "\\cases")
    monkeypatch.setattr(Path, "resolve", lambda _self: fake_resolved)
    assert to_wsl_path(Path("ignored")) == "/mnt/d/cases"


def test_to_wsl_path_root_of_drive_has_no_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omit trailing slash when converting a drive root."""
    fake_resolved = _win_path(67, "\\")
    monkeypatch.setattr(Path, "resolve", lambda _self: fake_resolved)
    assert to_wsl_path(Path("ignored")) == "/mnt/c"
