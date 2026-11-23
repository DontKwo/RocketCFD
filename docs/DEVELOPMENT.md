# Developer Guide

This guide covers setting up the local Python development environment, running the test suite, and packaging standalone executables from source.

## Environment Setup

Install **Python 3.13+** via [uv](UV_INSTALLATION.md). Sync runtime and test/build tools inside the repository root:

```bash
uv sync --dev
```

### Windows

```powershell
uv run --no-project --python ".venv\Scripts\python.exe" -m pytest -q
uv run --no-project --python ".venv\Scripts\python.exe" -m rocketcfd --self-test
uv run --no-project --python ".venv\Scripts\python.exe" -m rocketcfd
```

### macOS

```bash
uv run --no-project --python ".venv/bin/python" -m pytest -q
uv run --no-project --python ".venv/bin/python" -m rocketcfd --self-test
uv run --no-project --python ".venv/bin/python" -m rocketcfd
```

### Linux

```bash
uv run --no-project --python ".venv/bin/python" -m pytest -q
uv run --no-project --python ".venv/bin/python" -m rocketcfd --self-test
uv run --no-project --python ".venv/bin/python" -m rocketcfd
```

## Optional OpenFOAM Solver Integration

To execute local `blockMesh`, `snappyHexMesh`, and OpenFOAM solver sweeps in development, follow the [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md) and confirm `openfoam2412` (or your version's `etc/bashrc`) is available natively on Linux or inside WSL2 on Windows.

## Building Standalone Binaries

Standalone executables bundle [web_app.py](../src/rocketcfd/gui/web_app.py), static frontend assets (`src/rocketcfd/gui/static/`), and application icons with PyInstaller (`--add-data`). Always run the packaged binary with `--self-test` before publishing.

## Related Documentation

- [Project Overview](../README.md)
- [uv Installation Guide](UV_INSTALLATION.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
- [AI Agent Reference](../AGENTS.md)
- [Validation Traceability](VALIDATION.md)
- [Theoretical Background](THEORY.md)
