# AI Agent Operational Reference (RocketCFD)

This document summarizes repository architecture, tooling rules, and entrypoints for AI agents working in RocketCFD.

## Architecture

- **WebView Studio GUI (`src/rocketcfd/gui/`)**:
  - `web_app.py`: Standard-library loopback HTTP server (`ThreadingHTTPServer`) and CLI dispatcher (`--self-test`, `--headless-server`).
  - `studio_compute.py`: Pure-Python parametric rocket mesh assembly, 1976 US Standard Atmosphere evaluation, solver regime selection, validation benchmarks, and OpenFOAM case export.
  - `static/`: Vanilla HTML/CSS/JS frontend with dark/light theme tokens and dot-separated control IDs enforced by [UI Linter Config](.uilint.toml).
- **Aerodynamics & OpenFOAM Automation (`src/rocketcfd/`)**:
  - [Solver Selection](src/rocketcfd/solver_selection.py): Automatic Mach classification (`simpleFoam`, `rhoSimpleFoam`, `rhoPimpleFoam`, `rhoCentralFoam`) with `DEFAULT_MACH_CEILING = 3.0` and `HARD_MACH_LIMIT = 8.0`.
  - `flow.py` & `atmosphere.py`: `FlowCondition`, wind vector composition, and 1976 US Standard Atmosphere tables.
  - `geometry.py` & `templates_geometry.py`: Watertight mesh repair (`trimesh`, `pymeshfix`) and parametric nosecone/fin/boattail builders.
  - `openfoam/`: Case dictionary templates (`templates.py`), `write_mesh_case` / `write_run_case` (`case_builder.py`), and native Linux / WSL runner wrappers (`runner.py`).

## Execution & Test Harness

- Environment manager: `uv` (`uv sync --dev`), Python `>= 3.13`.
- Test suite: `uv run --no-project --python ".venv/Scripts/python.exe" -m pytest -q` (must exit 0).
- Self-test probe: `uv run --no-project --python ".venv/Scripts/python.exe" -m rocketcfd --self-test` (prints `SELF_TEST_OK`).
- License: [MIT License](LICENSE) (`Copyright (c) 2026 DontKwo`). Keep all docs/code MIT-aligned.
- Linter rules: Follow `.aitools.toml`, `.uilint.toml`, and `README.md <= 120` lines. Link docs directly and preserve `## Related Documentation` footers on every file under `docs/`.

## Related Documentation

- [Project Overview](README.md)
- [User Guide](docs/USER_GUIDE.md)
- [Desktop Installation Guide](docs/INSTALLATION.md)
- [OpenFOAM Installation Guide](docs/OPENFOAM_INSTALLATION.md)
- [Developer Guide](docs/DEVELOPMENT.md)
- [Theoretical Background](docs/THEORY.md)
- [Security Policy](SECURITY.md)
