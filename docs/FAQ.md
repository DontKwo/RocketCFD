# RocketCFD FAQ

## Geometry and Meshing

### How do I ensure my geometry is watertight?
RocketCFD automatically attempts to repair loaded STL/OBJ files using `trimesh` and `pymeshfix` (see `src/rocketcfd/geometry.py`). If the automated repair fails, you will receive a manual repair hint. You must open your geometry in a CAD or mesh editing tool to manually fill holes, remove duplicate faces, and unify normals.

### How is the boundary layer thickness calculated?
If the target $y^+$ setting is enabled, the first-layer cell thickness is automatically computed based on flat-plate boundary layer theory and Sutherland's law for viscosity. This ensures you adequately capture viscous sublayer effects without manual trial and error.

## Solvers and Execution

### Why am I getting convergence errors or high residuals?
CFD runs, particularly compressible ones, can diverge if the mesh is poor or boundary conditions undergo sudden shocks.
- **Check your Mesh**: Ensure feature refinement and snappyHexMesh layer addition succeeded without heavily distorted cells.
- **Monitor Residuals**: Use the live GUI plotting to watch continuity (`p`), momentum (`U`), and turbulence (`k`/`omega`) residuals. If they spike instead of decaying smoothly, the simulation is diverging.
- **Regime specific**: Ensure you are not operating at a Mach number that invokes unsupported physics (e.g., $M > 8$ dissociation).

### How does RocketCFD choose the solver?
Solver selection is fully automated based on the configured Mach number (see `src/rocketcfd/solver_selection.py`):
- **Incompressible ($M < 0.3$)**: Uses `simpleFoam`.
- **Subsonic Compressible ($0.3 \leq M < 0.8$)**: Uses `rhoSimpleFoam`.
- **Transonic ($0.8 \leq M < 1.2$)**: Uses transient `rhoPimpleFoam`.
- **Supersonic ($M \geq 1.2$)**: Uses `rhoCentralFoam` with fixed upwind-biased schemes.

### How do boundary conditions work in RocketCFD?
When you define a flight condition (Velocity, Alpha, Beta, Altitude), RocketCFD automatically writes the correct OpenFOAM dictionaries in the `0/` directory. It uses the 1976 Standard Atmosphere to calculate freestream pressure and temperature, and maps your vehicle's orientation into the velocity field boundary equations.
