# RocketCFD Theoretical Background

This document outlines the core physics and mathematical formulations governing the automated OpenFOAM setups within RocketCFD.

## Flow Regimes and Solvers

The governing Navier-Stokes equations are adapted based on the vehicle's flight Mach number ($M$) to optimize stability and accuracy.

1. **Incompressible Flow ($M < 0.3$)**
   - At low speeds, density variations are negligible. The continuity equation simplifies to $\nabla \cdot \mathbf{U} = 0$.
   - **Solver**: `simpleFoam`
   - **Characteristics**: Steady-state solver for incompressible, turbulent flow using the SIMPLE (Semi-Implicit Method for Pressure Linked Equations) algorithm.

2. **Subsonic Compressible ($0.3 \leq M < 0.8$)**
   - Density changes become significant, requiring the solution of the energy equation alongside mass and momentum.
   - **Solver**: `rhoSimpleFoam`
   - **Characteristics**: Steady-state compressible solver.

3. **Transonic ($0.8 \leq M < 1.2$)**
   - Transonic flow features a mixture of subsonic and supersonic regions, often containing unsteady shock waves and complex shock/boundary-layer interactions.
   - **Solver**: `rhoPimpleFoam`
   - **Characteristics**: Transient solver for compressible flow using the PIMPLE (merged PISO-SIMPLE) algorithm to capture unsteady phenomena that a steady solver cannot reliably resolve.

4. **Supersonic ($M \geq 1.2$)**
   - Characterized by dominant shock waves and expansion fans. Information propagates only downstream.
   - **Solver**: `rhoCentralFoam`
   - **Characteristics**: Density-based compressible solver employing central-upwind schemes (Kurganov and Tadmor) to robustly capture sharp discontinuities like shocks without excessive oscillation.

## Fluid Properties and Atmosphere

- **Viscosity**: Dynamic viscosity ($\mu$) is modeled using **Sutherland's Law**, which accounts for the temperature dependence of gas viscosity:
  $$ \mu = \mu_{ref} \left( \frac{T}{T_{ref}} \right)^{3/2} \frac{T_{ref} + S}{T + S} $$
- **Atmosphere**: The ambient freestream pressure, temperature, and density are determined from the user's input altitude using the **1976 US Standard Atmosphere** model.

## Turbulence Modeling

RocketCFD defaults to solving the Reynolds-Averaged Navier-Stokes (RANS) equations to model turbulence.
- The standard **k-$\omega$ SST (Shear Stress Transport)** model is used by default. It combines the advantages of the k-$\omega$ model near the wall (for adverse pressure gradients and separation) and the k-$\epsilon$ model in the free stream.
- The **Spalart-Allmaras** one-equation model is also supported.
