"""Force/moment -> aerodynamic coefficients."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rocketcfd.flow import FlowCondition


@dataclass
class Coefficients:
    cd: float
    cl: float
    cs: float
    cm: np.ndarray
    normal_force_coeff: float = 0.0
    center_of_pressure_x: float | None = None


def calculate_center_of_pressure(
    cm_pitch: float,
    normal_force_coeff: float,
    reference_length: float,
    moment_ref_x: float = 0.0,
) -> float | None:
    """Calculates longitudinal center of pressure location Xcp from pitching moment and normal force."""
    if abs(normal_force_coeff) < 1e-5 or reference_length <= 0.0:
        return None
    return float(moment_ref_x - (cm_pitch / normal_force_coeff) * reference_length)


def validate_reference_dimensions(
    reference_area: float,
    reference_length: float,
    model_bounds: tuple[float, float, float, float, float, float],
) -> list[str]:
    """Validates aerodynamic reference dimensions against geometry bounding box extents."""
    warnings: list[str] = []
    if reference_area <= 0.0:
        warnings.append(f"Reference area must be positive, got {reference_area:.4e} m^2.")
    if reference_length <= 0.0:
        warnings.append(f"Reference length must be positive, got {reference_length:.4e} m.")

    xmin, xmax, ymin, ymax, zmin, zmax = model_bounds
    length_span = max(xmax - xmin, 1e-6)
    area_span = max(ymax - ymin, 1e-6) * max(zmax - zmin, 1e-6)

    if reference_length > 10.0 * length_span:
        warnings.append(f"Reference length {reference_length:.2f} m is over 10x model length ({length_span:.2f} m).")
    elif reference_length < 0.05 * length_span:
        warnings.append(f"Reference length {reference_length:.2f} m is under 0.05x model length ({length_span:.2f} m).")

    if reference_area > 10.0 * area_span:
        warnings.append(f"Reference area {reference_area:.4f} m^2 is over 10x projected cross section.")
    elif reference_area < 0.01 * area_span:
        warnings.append(f"Reference area {reference_area:.4f} m^2 is under 0.01x projected cross section.")

    return warnings


def from_force_moment(
    condition: FlowCondition,
    force: np.ndarray,
    moment: np.ndarray,
    reference_area: float,
    reference_length: float,
) -> Coefficients:
    direction = condition.direction_unit()
    up = condition.up_unit()
    side_dir = np.cross(direction, up)
    side_dir = side_dir / np.linalg.norm(side_dir)
    lift_dir = np.cross(side_dir, direction)

    q = condition.dynamic_pressure()
    denom = q * reference_area if reference_area > 0.0 else 1.0

    cd = force @ direction / denom
    cl = force @ lift_dir / denom
    cs = force @ side_dir / denom
    cm = moment / (denom * reference_length)
    normal_coeff = force @ up / denom

    xcp: float | None = None
    if isinstance(normal_coeff, (int, float, np.floating)):
        cm_pitch = float(cm @ side_dir) if hasattr(cm, "__matmul__") and cm.ndim == 1 else 0.0
        xcp = calculate_center_of_pressure(cm_pitch, float(normal_coeff), reference_length)

    return Coefficients(
        cd=cd,
        cl=cl,
        cs=cs,
        cm=cm,
        normal_force_coeff=normal_coeff,
        center_of_pressure_x=xcp,
    )
