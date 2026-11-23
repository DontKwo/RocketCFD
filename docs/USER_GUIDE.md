# RocketCFD User Guide

Welcome to the RocketCFD user guide. This document provides a step-by-step tutorial on how to use RocketCFD from start to finish.

## 1. Getting Started

### Installation
Ensure you have `uv` installed, as it is the primary environment and build manager for RocketCFD.

To install dependencies and prepare the environment, run:
```bash
uv build
```
*(Tests can be run with `uv run pytest`)*

### Launching the Application
Download the desktop executable from [RocketCFD Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest) (see the [Desktop Installation Guide](INSTALLATION.md)), or launch from source with `uv`:
```bash
uv run rocketcfd
```

## 2. Setting Up a Simulation

### Loading Geometry
1. Click the **Load Geometry** button.
2. Select an STL, OBJ, or PLY file. If you have the CAD backend installed, you can also load STEP or IGES files.
3. The geometry will automatically be checked and repaired for watertightness using `trimesh` and `pymeshfix`. If automatic repair fails, you will need to manually fix your mesh in a 3D modeling tool.

### Defining the Flight Profile
The solver and fluid properties are determined by the flight condition you set.
In the input pane, define:
* **Mach Number**: The speed of the vehicle relative to the speed of sound.
* **Altitude**: Automatically configures the ambient temperature and density using the 1976 Standard Atmosphere.
* **Angle of Attack ($\alpha$)**: The pitch of the vehicle relative to the freestream.
* **Sideslip ($\beta$)**: The yaw of the vehicle relative to the freestream.

*(Note: The solver is automatically selected based on the Mach number. For instance, subsonic flow might use `simpleFoam`, while supersonic flow will use `rhoCentralFoam`.)*

### Configuring the Mesh
Navigate to the Mesh Settings pane to configure `snappyHexMesh` defaults:
1. **Mesh Preset**: Choose from Coarse, Medium, or Fine presets to establish base cell sizing and refinement limits.
2. **Boundary Layer Configuration**: Enable the target $y^+$ feature to automatically compute the first-layer cell thickness necessary to capture viscous boundary layer effects based on flat-plate theory.

## 3. Running and Visualizing

### Executing the Solve
1. Click **Run Solve**.
2. The application will generate the OpenFOAM case structure (`0/`, `constant/`, `system/`), execute blockMesh, surfaceFeatures, and snappyHexMesh.
3. The selected solver (e.g., `rhoSimpleFoam`, `rhoPimpleFoam`) will begin executing.

### Live Monitoring
During local OpenFOAM solves, monitor `log.<solver>` residuals and force histories to verify convergence of continuity, momentum, and turbulence equations.

### Visualization
Inspect parametric geometry profiles, cross-sections, Mach flight envelopes, and reference benchmarks directly in the RocketCFD WebView Studio, or load sampled OpenFOAM VTK outputs via PyVista helpers.

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
- [FAQ](FAQ.md)
- [Theoretical Background](THEORY.md)
- [Developer Guide](DEVELOPMENT.md)
