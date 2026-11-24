<p align="center">
  <img src="assets/logo.png" alt="RocketCFD Logo" width="240" />
</p>

# RocketCFD

**Interactive 3D rocket aerodynamics, OpenFOAM case generation, and live solver automation.**

RocketCFD Studio lets engineers assemble parametric rockets or import STL/OBJ/STEP geometry, inspect Modified-Newtonian $C_p$ pressure shading in a 3D WebGL viewport, map flight conditions across OpenFOAM regimes, and run local or HPC sweeps.

---

## Download

| Platform | Download | Setup Guide |
| :--- | :--- | :--- |
| Windows (64-bit) | [RocketCFD-Windows.exe](https://github.com/DontKwo/RocketCFD/releases/latest/download/RocketCFD-Windows.exe) | [Windows Guide](docs/INSTALLATION.md#windows) &bull; [OpenFOAM WSL2](docs/OPENFOAM_INSTALLATION.md#windows) |
| macOS (Apple Silicon) | [RocketCFD-macOS.zip](https://github.com/DontKwo/RocketCFD/releases/latest/download/RocketCFD-macOS.zip) | [macOS Guide](docs/INSTALLATION.md#macos) &bull; [OpenFOAM macOS](docs/OPENFOAM_INSTALLATION.md#macos) |
| Linux (x86_64) | [RocketCFD-Linux.tar.gz](https://github.com/DontKwo/RocketCFD/releases/latest/download/RocketCFD-Linux.tar.gz) | [Linux Guide](docs/INSTALLATION.md#linux) &bull; [OpenFOAM Linux](docs/OPENFOAM_INSTALLATION.md#linux) |

---

## Screenshots

<p align="center">
  <img src="assets/screenshots/01_main.png" alt="RocketCFD Studio Interactive 3D Cp Mesh Viewport" width="760" />
</p>

<p align="center">
  <img src="assets/screenshots/02_solver.png" alt="RocketCFD Solver Regime Envelope" width="760" />
</p>

---

## How to Use

1. Download the executable for your operating system from the [Download](#download) table above and follow the [Desktop Installation Guide](docs/INSTALLATION.md).
2. *(Optional)* Follow the [OpenFOAM Installation Guide](docs/OPENFOAM_INSTALLATION.md) if you plan to run full live 3D CFD solves locally, in WSL2, or in Docker.
3. Build a parametric rocket or import an STL, OBJ, or STEP model with unit conversion, scaling, and rotation transforms in the **3D Viewport**.
4. Evaluate Mach regimes and $y^+$ mesh presets, export complete OpenFOAM cases, launch async sweeps under **Run Sweep**, inspect CSV residuals, or generate **TACC SLURM** scripts.

---

## Key Features

- **3D WebGL Viewport & CAD Import**: Assemble parametric rockets or import STL/OBJ/STEP files with unit scaling, axis rotation, and live Modified-Newtonian $C_p$ shading.
- **Automated Mach Regime Classification**: Maps altitude, airspeed, and 1976 US Standard Atmosphere properties to `simpleFoam`, `rhoSimpleFoam`, `rhoPimpleFoam`, or `rhoCentralFoam`.
- **Boundary Layer & Mesh Presets**: Sizes `snappyHexMesh` background grids, refinement levels, and target $y^+$ first-layer thickness from flat-plate theory and Sutherland's law.
- **Live OpenFOAM Sweeps & TACC SLURM**: Runs asynchronous sweeps across WSL2, Native Linux, or Docker with live residual curves, CSV exports, validation benchmarks, and cluster scripts.

---

## Documentation

### User Documentation
- [User Guide](docs/USER_GUIDE.md)
- [Desktop Installation Guide](docs/INSTALLATION.md)
- [OpenFOAM Installation Guide](docs/OPENFOAM_INSTALLATION.md)
- [Frequently Asked Questions](docs/FAQ.md)

### Developer Documentation
- [Developer Guide](docs/DEVELOPMENT.md)
- [uv Installation Guide](docs/UV_INSTALLATION.md)

### Theory, Validation & AI Documentation
- [Theoretical Background](docs/THEORY.md)
- [Validation Traceability](docs/VALIDATION.md)
- [AI Agent Reference](AGENTS.md)

### Legal & Security Policies
- [Security Policy](SECURITY.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)
- [MIT License](LICENSE)

---

## Safety & Disclaimers

- **Official `main` Releases Only**: Download executables strictly from `DontKwo/RocketCFD` (`main` / official [Releases](https://github.com/DontKwo/RocketCFD/releases/latest)). Do **not** download forked releases unless you have verified the source code yourself; only official `main` releases are maintained by the author.
- **OS Security Prompt Discretion**: Independent builds may trigger Windows SmartScreen or macOS Gatekeeper warnings. Review the [Desktop Installation Guide](docs/INSTALLATION.md) and bypass security prompts strictly at your own discretion.
- **AS-IS & Engineering Notice**: Provided "AS IS" under the [MIT License](LICENSE), without warranty of any kind. CFD outputs and OpenFOAM configurations are engineering estimates, not certified flight-safety approvals.
