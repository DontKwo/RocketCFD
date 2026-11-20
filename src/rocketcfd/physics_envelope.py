"""Defines the supported physics envelope, limitations, and engineering review disclaimer."""
from __future__ import annotations

from dataclasses import dataclass, field

from rocketcfd.flow import FlowCondition
from rocketcfd.solver_selection import (
    DEFAULT_MACH_CEILING,
    HARD_MACH_LIMIT,
    INCOMPRESSIBLE,
    SUBSONIC_COMPRESSIBLE,
    SUPERSONIC,
    TRANSONIC,
    select_solver,
)

CERTIFICATION_DISCLAIMER: str = (
    "RocketCFD is for rapid aerodynamic design, parameter sweeps, and research. "
    "It is not certification CFD and does not replace qualified engineering review."
)


@dataclass(frozen=True)
class PhysicsEnvelope:
    geometry_classes: tuple[str, ...] = (
        "axisymmetric_rockets",
        "bluff_bodies",
        "capsules",
        "slender_cones",
        "airfoils",
        "fins",
    )
    mach_regimes: tuple[str, ...] = (
        INCOMPRESSIBLE,
        SUBSONIC_COMPRESSIBLE,
        TRANSONIC,
        SUPERSONIC,
    )
    min_mach: float = 0.0
    default_mach_ceiling: float = DEFAULT_MACH_CEILING
    hard_mach_limit: float = HARD_MACH_LIMIT
    min_reynolds: float = 1.0e3
    max_reynolds: float = 1.0e8
    compressibility_models: tuple[str, ...] = (
        "incompressible_constant_density",
        "compressible_perfect_gas",
        "kurganov_tadmor_central_upwind",
    )
    turbulence_models: tuple[str, ...] = ("kOmegaSST", "SpalartAllmaras")
    heat_transfer_scope: str = "calorically_perfect_air_adiabatic_wall"
    limitations: tuple[str, ...] = (
        "No high-temperature chemical dissociation or real-gas ionization (M > 8).",
        "No radiative surface heat transfer.",
        "No active base-bleed or rocket exhaust plume chemical reaction.",
        "Assumes clean, rigid exterior geometry without structural aeroelastic deflection.",
    )
    disclaimer: str = CERTIFICATION_DISCLAIMER


PHYSICS_ENVELOPE = PhysicsEnvelope()


def validate_flow_condition_envelope(
    condition: FlowCondition,
    mach_ceiling: float = DEFAULT_MACH_CEILING,
) -> list[str]:
    """Evaluates whether condition falls within the supported physics envelope."""
    warnings: list[str] = []
    mach = condition.mach()
    if mach < 0.0:
        warnings.append(f"Mach {mach:.2f} is negative.")
    elif mach > HARD_MACH_LIMIT:
        warnings.append(
            f"Mach {mach:.2f} exceeds hard limit {HARD_MACH_LIMIT:.1f}; real-gas effects dominate."
        )
    elif mach > mach_ceiling:
        warnings.append(
            f"Mach {mach:.2f} exceeds configured ceiling {mach_ceiling:.1f}."
        )

    # Estimate body Reynolds number assuming standard 1 meter characteristic length.
    reynolds = condition.density * condition.velocity / 1.8e-5
    if reynolds < PHYSICS_ENVELOPE.min_reynolds and condition.velocity > 0.0:
        warnings.append(
            f"Estimated Reynolds number {reynolds:.1e} is below recommended {PHYSICS_ENVELOPE.min_reynolds:.1e}."
        )
    elif reynolds > PHYSICS_ENVELOPE.max_reynolds:
        warnings.append(
            f"Estimated Reynolds number {reynolds:.1e} exceeds recommended {PHYSICS_ENVELOPE.max_reynolds:.1e}."
        )

    if condition.temperature < 150.0:
        warnings.append(f"Temperature {condition.temperature:.1f} K is below standard atmospheric range.")
    elif condition.temperature > 500.0:
        warnings.append(f"Temperature {condition.temperature:.1f} K exceeds calorically perfect air limits.")

    return warnings


def explain_physics_regime(mach: float) -> dict[str, str]:
    """Returns regime classification, solver application, and omitted physics notes."""
    selection = select_solver(mach)
    omitted = "Real-gas chemistry, surface ablation, and radiative transfer are omitted."
    if selection.regime == INCOMPRESSIBLE:
        physics = "Constant density; acoustic and compressibility waves neglected."
    elif selection.regime == SUBSONIC_COMPRESSIBLE:
        physics = "Compressible Navier-Stokes; perfect gas equation of state."
    elif selection.regime == TRANSONIC:
        physics = "Transient compressible flow with unsteady shock and boundary-layer interaction."
    else:
        physics = "Compressible flow with shock capturing via central-upwind schemes."
    return {
        "regime": selection.regime,
        "application": selection.application,
        "physics_description": physics,
        "omitted_physics": omitted,
        "disclaimer": CERTIFICATION_DISCLAIMER,
    }
