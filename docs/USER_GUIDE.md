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
RocketCFD comes with a built-in GUI built using PySide6 and PyVista. Launch the application from your terminal:
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
During the solve, switch the Plot Mode to **Residuals** to view real-time plots of continuity, momentum, and turbulence equation convergence.

### 3D Visualization
Once the solve is complete (or partially complete for transient solvers), you can view the results in the interactive PyVista viewport.
* Switch the view modes to inspect **Surface Pressure ($C_p$)**, **Wall Shear Stress**, or **Volumetric Velocity Slices**.
* Use your mouse to rotate, pan, and zoom around the computational domain.
