# RocketCFD User Guide

Welcome to RocketCFD Studio, an offline 3D rocket aerodynamics, OpenFOAM case generation, and sweep automation desktop application.

## 1. Launching the Application

Download the standalone desktop executable from [RocketCFD Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest) and follow the [Desktop Installation Guide](INSTALLATION.md) for Windows, macOS, or Linux.

*(Optional)* For running full live 3D OpenFOAM solves locally or via WSL2/Docker, follow the [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md). Developers running from source can follow the [Developer Guide](DEVELOPMENT.md).

## 2. Geometry & CAD Import

Use the **Rocket Geometry** card in the left panel:
- **Parametric Rocket**: Configure nosecone shape (`conical`, `ogive`, `von_karman`), nose length, body length, diameter, fin count, and fin span, then click **Build Geometry**.
- **Import STL / OBJ / STEP**: Switch **Geometry Source** to **Import STL / OBJ / STEP**, select your mesh file, choose source **Units** (`m`, `mm`, `cm`, `in`, `ft`), set **Scale** and **Rot X / Y / Z (deg)**, and click **Import & Transform**.
- Inspect the assembled triangle panel mesh interactively inside the **3D Viewport** tab using orbit, pan, zoom, and surface shading modes (**Modified-Newtonian Cp**, **Solid Lit Aerospace**, **Triangular Mesh Wireframe**, and **Axial Station Gradient**).

## 3. Flight Setup & OpenFOAM Export

Use the **Flight & Solver Setup** card:
1. Enter **Altitude (m)**, **Velocity (m/s)**, **Alpha (deg)**, and **Mesh Preset** (`Coarse`, `Medium`, `Fine`).
2. Click **Evaluate Solver** to compute 1976 US Standard Atmosphere properties, Flight Mach, selected OpenFOAM solver (`simpleFoam` through `rhoCentralFoam`), dynamic pressure, and target $y^+$ boundary layer sizing.
3. Click **Export Case** to generate `0/`, `constant/triSurface/`, and `system/` dictionaries on disk and preview generated file paths.
4. Switch between **2D Engineering Views** and **Solver Regime Envelope** to inspect dimensioned drawings and altitude regime curves.

## 4. Live Sweeps, Residuals & TACC HPC

1. In **OpenFOAM Runner**, select your backend (**Windows WSL2**, **Native Linux**, or **Docker (OpenFOAM 2412)**), CPU core count, velocity list, and alpha list.
2. Click **Run Sweep** to execute asynchronous OpenFOAM jobs, monitor live log output and residual convergence curves, and inspect aerodynamic force tables under **Residuals & Results** (or import existing OpenFOAM folders and export CSV results).
3. Under **Validation & HPC**, run benchmark validation comparisons or enter your TACC host and SLURM allocation to generate ready-to-submit cluster batch scripts.

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
- [Frequently Asked Questions](FAQ.md)
- [Theoretical Background](THEORY.md)
- [Validation Traceability](VALIDATION.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
