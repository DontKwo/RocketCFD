"""Grid Convergence Index (GCI) and spatial discretization uncertainty estimation."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class GCIResult:
    coarse_value: float
    medium_value: float
    fine_value: float
    r21: float
    r32: float
    apparent_order: float
    extrapolated_value: float
    approx_relative_error: float
    extrapolated_relative_error: float
    gci_fine_pct: float
    gci_medium_pct: float
    asymptotic_ratio: float
    convergence_type: str


def calculate_gci(
    coarse_cells: int,
    medium_cells: int,
    fine_cells: int,
    coarse_val: float,
    medium_val: float,
    fine_val: float,
    dimension: int = 3,
    safety_factor: float = 1.25,
) -> GCIResult:
    """Computes Roache GCI uncertainty across three systematically refined mesh levels."""
    if not (coarse_cells < medium_cells < fine_cells):
        raise ValueError("Cell counts must satisfy coarse < medium < fine.")
    if dimension <= 0:
        raise ValueError("Spatial dimension must be positive.")

    r21 = (fine_cells / medium_cells) ** (1.0 / dimension)
    r32 = (medium_cells / coarse_cells) ** (1.0 / dimension)

    delta21 = fine_val - medium_val
    delta32 = medium_val - coarse_val

    if abs(delta21) < 1e-14:
        return GCIResult(
            coarse_value=coarse_val,
            medium_value=medium_val,
            fine_value=fine_val,
            r21=r21,
            r32=r32,
            apparent_order=2.0,
            extrapolated_value=fine_val,
            approx_relative_error=0.0,
            extrapolated_relative_error=0.0,
            gci_fine_pct=0.0,
            gci_medium_pct=0.0,
            asymptotic_ratio=1.0,
            convergence_type="exact_match",
        )

    ratio = delta32 / delta21
    if ratio > 1.0:
        convergence_type = "diverging"
    elif ratio < 0.0:
        convergence_type = "oscillatory"
    else:
        convergence_type = "monotonic"

    # Solve for apparent order p using fixed-point iteration.
    p = 2.0
    for _ in range(50):
        s = 1.0 if ratio > 0.0 else -1.0
        term = abs(ratio)
        q_p = np.log((r21**p - s) / (r32**p - s)) if abs(r32**p - s) > 1e-12 else 0.0
        p_next = float(abs(np.log(term) + q_p) / np.log(r21))
        if abs(p_next - p) < 1e-6:
            p = p_next
            break
        p = 0.5 * (p + p_next)

    p = max(0.5, min(p, 6.0))
    rp_minus_1 = r21**p - 1.0
    if abs(rp_minus_1) < 1e-12:
        rp_minus_1 = 1e-12

    extrapolated = fine_val + delta21 / rp_minus_1
    fine_scale = abs(fine_val) if abs(fine_val) > 1e-12 else 1.0
    ext_scale = abs(extrapolated) if abs(extrapolated) > 1e-12 else 1.0

    ea21 = abs(delta21 / fine_scale)
    e_ext = abs((extrapolated - fine_val) / ext_scale)

    gci_fine = safety_factor * ea21 / rp_minus_1 * 100.0

    rp32_minus_1 = r32**p - 1.0
    if abs(rp32_minus_1) < 1e-12:
        rp32_minus_1 = 1e-12
    med_scale = abs(medium_val) if abs(medium_val) > 1e-12 else 1.0
    ea32 = abs(delta32 / med_scale)
    gci_medium = safety_factor * ea32 / rp32_minus_1 * 100.0

    asymp_denom = (r21**p) * gci_fine if gci_fine > 1e-12 else 1.0
    asymptotic_ratio = gci_medium / asymp_denom

    return GCIResult(
        coarse_value=coarse_val,
        medium_value=medium_val,
        fine_value=fine_val,
        r21=r21,
        r32=r32,
        apparent_order=p,
        extrapolated_value=extrapolated,
        approx_relative_error=ea21,
        extrapolated_relative_error=e_ext,
        gci_fine_pct=gci_fine,
        gci_medium_pct=gci_medium,
        asymptotic_ratio=asymptotic_ratio,
        convergence_type=convergence_type,
    )
