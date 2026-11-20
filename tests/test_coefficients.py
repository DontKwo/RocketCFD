"""Unit tests for aerodynamic coefficient, center of pressure, and dimension validation."""
from __future__ import annotations

import numpy as np
import pytest

from rocketcfd.flow import FlowCondition
from rocketcfd.openfoam.coefficients import (
    calculate_center_of_pressure,
    from_force_moment,
    validate_reference_dimensions,
)


def test_calculate_center_of_pressure_symmetric() -> None:
    # Pitching moment zero at aerodynamic center/center of pressure.
    xcp = calculate_center_of_pressure(cm_pitch=0.0, normal_force_coeff=0.5, reference_length=2.0, moment_ref_x=1.0)
    assert xcp == pytest.approx(1.0)


def test_calculate_center_of_pressure_offset() -> None:
    # Pitching moment positive (nose-up) means center of pressure is forward of reference.
    xcp = calculate_center_of_pressure(cm_pitch=0.1, normal_force_coeff=0.5, reference_length=2.0, moment_ref_x=1.0)
    assert xcp == pytest.approx(1.0 - (0.1 / 0.5) * 2.0)


def test_calculate_center_of_pressure_zero_normal_force() -> None:
    assert calculate_center_of_pressure(cm_pitch=0.1, normal_force_coeff=0.0, reference_length=2.0) is None


def test_validate_reference_dimensions() -> None:
    bounds = (0.0, 5.0, -0.5, 0.5, -0.5, 0.5)
    # Reasonable dimensions.
    assert validate_reference_dimensions(0.8, 5.0, bounds) == []

    # Non-positive or out of scale.
    assert len(validate_reference_dimensions(-1.0, 5.0, bounds)) > 0
    assert len(validate_reference_dimensions(0.8, 100.0, bounds)) > 0


def test_from_force_moment_populates_center_of_pressure() -> None:
    condition = FlowCondition(name="test", velocity=100.0, density=1.225)
    force = np.array([100.0, 0.0, 50.0])
    moment = np.array([0.0, 25.0, 0.0])
    coeffs = from_force_moment(condition, force, moment, reference_area=1.0, reference_length=1.0)
    assert coeffs.normal_force_coeff > 0.0
    assert coeffs.center_of_pressure_x is not None
