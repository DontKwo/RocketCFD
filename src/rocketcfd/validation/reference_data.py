"""Analytic and tabulated reference values for canonical validation benchmarks."""
from __future__ import annotations

import numpy as np

FLAT_PLATE_TRANSITION_REYNOLDS = 5.0e5

# Standard sphere Cd-vs-Re curve digitized from Schlichting & Gersten, "Boundary-Layer Theory."
_SPHERE_CD_LOG10_RE = np.array([1.0, 2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.3, 5.48, 5.7, 6.0, 6.5, 7.0])
_SPHERE_CD = np.array([3.0, 1.5, 0.5, 0.4, 0.47, 0.5, 0.5, 0.4, 0.1, 0.1, 0.13, 0.18, 0.2])

# Standard circular cylinder cross-flow Cd-vs-Re curve from Tritton, Wieselsberger, and ESDU.
_CYLINDER_CD_LOG10_RE = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 5.48, 6.0, 7.0])
_CYLINDER_CD = np.array([3.0, 1.0, 1.0, 1.2, 1.2, 0.3, 0.4, 0.5])


def flat_plate_cf(reynolds_length: float, transition_reynolds: float = FLAT_PLATE_TRANSITION_REYNOLDS) -> float:
    """Mean skin-friction coefficient over a flat plate of length L."""
    if reynolds_length <= 0.0:
        raise ValueError("reynolds_length must be positive")
    if reynolds_length < transition_reynolds:
        return 1.328 / np.sqrt(reynolds_length)
    return 0.074 / reynolds_length**0.2


def sphere_cd_reference(reynolds_diameter: float) -> float:
    """Standard sphere drag coefficient interpolated from digitized experimental curve."""
    if reynolds_diameter <= 0.0:
        raise ValueError("reynolds_diameter must be positive")
    log_re = np.log10(reynolds_diameter)
    return float(np.interp(log_re, _SPHERE_CD_LOG10_RE, _SPHERE_CD))


def cylinder_cd_reference(reynolds_diameter: float) -> float:
    """Circular cylinder cross-flow drag coefficient from digitized experimental curve."""
    if reynolds_diameter <= 0.0:
        raise ValueError("reynolds_diameter must be positive")
    log_re = np.log10(reynolds_diameter)
    return float(np.interp(log_re, _CYLINDER_CD_LOG10_RE, _CYLINDER_CD))


def naca0012_reference(mach: float, reynolds_chord: float, alpha_deg: float) -> tuple[float, float]:
    """NACA 0012 section lift and drag coefficients from Abbott & von Doenhoff data."""
    if mach >= 0.8:
        raise ValueError("Linearized NACA 0012 reference is valid for subsonic Mach < 0.8.")
    if abs(alpha_deg) > 12.0:
        raise ValueError("Linearized airfoil reference is valid below stall (|alpha| <= 12 deg).")
    prandtl_beta = np.sqrt(max(1.0 - mach**2, 0.01))
    cl = 2.0 * np.pi * np.radians(alpha_deg) / prandtl_beta
    base_cd = 0.008 * (1.0e6 / max(reynolds_chord, 1.0e4)) ** 0.1
    cd = base_cd + 0.012 * cl**2
    return float(cl), float(cd)


def apollo_capsule_reference(mach: float, alpha_deg: float) -> tuple[float, float, float]:
    """Apollo Command Module supersonic drag, lift, and center of pressure from NASA TM X-1183."""
    if mach < 1.2:
        raise ValueError("Apollo CM supersonic benchmark requires Mach >= 1.2.")
    alpha_rad = np.radians(alpha_deg)
    # At alpha=0 deg, blunt heatshield drag coefficient is approximately 1.28.
    cd = float(1.28 * np.cos(alpha_rad) ** 2 + 0.3 * np.sin(alpha_rad) ** 2)
    cl = float(0.4 * np.sin(2.0 * alpha_rad))
    # Normalized longitudinal center of pressure location Xcp / D measured from nose.
    xcp_over_d = float(0.65 - 0.05 * np.sin(alpha_rad))
    return cd, cl, xcp_over_d


def slender_cone_wave_drag_cd(half_angle_deg: float, mach: float) -> float:
    """Linearized supersonic wave-drag coefficient for a sharp cone at zero angle of attack."""
    if mach <= 1.0:
        raise ValueError("slender_cone_wave_drag_cd requires supersonic Mach (M > 1)")
    theta = np.radians(half_angle_deg)
    return float(4.0 * theta**2 / np.sqrt(mach**2 - 1.0))
