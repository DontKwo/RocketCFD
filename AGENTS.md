# AI Agent Operational Reference (RocketCFD)

This document provides a dense technical summary for AI agents inspecting or modifying the RocketCFD codebase.

## Architecture
- **GUI**: PySide6 & PyVista (3D viewing). See `src/rocketcfd/gui/`.
- **CFD Backend**: OpenFOAM automated via Python wrappers (`src/rocketcfd/openfoam/`).
- **Geometry**: Loads STL/OBJ/PLY using `trimesh` and `pymeshfix`. Optional STEP/IGES support via `cadquery-ocp` (`src/rocketcfd/brep_backend.py`).
- **Simulation Flow**: Geometry setup $\rightarrow$ Mesh generation (`snappyHexMesh`) $\rightarrow$ Solver selection (based on Mach) $\rightarrow$ Solve $\rightarrow$ Results parsing & visualization.

## Mathematical Formulation
- **Incompressible Flow ($M < 0.3$)**:
  - Solved with `simpleFoam`.
  - Constant density.
- **Subsonic Compressible ($0.3 \leq M < 0.8$)**:
  - Solved with `rhoSimpleFoam`.
  - Compressible, steady-state formulation.
- **Transonic ($0.8 \leq M < 1.2$)**:
  - Solved with `rhoPimpleFoam`.
  - Compressible, transient formulation to capture unsteady shock/boundary-layer interactions.
- **Supersonic ($M \geq 1.2$)**:
  - Solved with `rhoCentralFoam`.
  - Uses fixed upwind-biased schemes for robustness. Transient solver.
- **Turbulence**: k-Omega SST (default) or Spalart-Allmaras.
- **Atmosphere**: 1976 Standard Atmosphere (`src/rocketcfd/atmosphere.py`).

## Mesh Format
- Base block mesh (`blockMesh`) extended by `snappyHexMesh` for feature snapping and boundary layer refinement.
- Configurable $y^+$ targets for first-layer thickness (calculated using flat-plate theory & Sutherland's law for viscosity).
- Panels and regions tracked for forces and momentum calculations.

## Test Harness
- `pytest` for all functional tests.
- Contains validation checks (e.g., Apollo CM benchmarks) in `tests/`.
- Run tests via: `uv run pytest`.
- Must exit with code 0. No skipping allowed.

## Execution Rules
- **Run GUI**: `uv run rocketcfd`
- **Run Tests**: `uv run pytest`
- **Build**: `uv build`
- Use `uv` for all environment management.
- DO NOT edit build artifacts. Trace changes to source files.
- Ensure strict adherence to GPL-3.0 licensing and assign all copyrights to `DontKwo`.
- No personal info, emails, or credentials in the repo. Email is exclusively `323857007+DontKwo@users.noreply.github.com` ("the outlook address").

## File Map
- `src/rocketcfd/solver_selection.py`: Defines Mach regimes and solvers.
- `src/rocketcfd/flow.py`: Defines `FlowCondition` (Mach, altitude, alpha, beta, etc.).
- `src/rocketcfd/geometry.py`: Watertight repair and STL loading.
- `src/rocketcfd/sweep.py`: Batch condition permutations.
- `src/rocketcfd/openfoam/runner.py`: Wrapper for OpenFOAM CLI execution (local/WSL).
- `src/rocketcfd/openfoam/case_builder.py`: Writes all `0/`, `constant/`, and `system/` OpenFOAM dictionaries.
