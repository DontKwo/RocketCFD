"""Analytic/tabulated validation reference values."""
from __future__ import annotations

import pytest

from rocketcfd.validation.reference_data import (
    apollo_capsule_reference,
    cylinder_cd_reference,
    flat_plate_cf,
    naca0012_reference,
    slender_cone_wave_drag_cd,
    sphere_cd_reference,
)
from rocketcfd.validation.runner import full_canonical_validation_suite


def test_flat_plate_cf_laminar_matches_blasius() -> None:
    reynolds = 1e5
    assert flat_plate_cf(reynolds) == pytest.approx(1.328 / reynolds**0.5, rel=1e-9)


def test_flat_plate_cf_turbulent_matches_correlation() -> None:
    reynolds = 1e7
    assert flat_plate_cf(reynolds) == pytest.approx(0.074 / reynolds**0.2, rel=1e-9)


def test_flat_plate_cf_requires_positive_reynolds() -> None:
    with pytest.raises(ValueError):
        flat_plate_cf(0.0)


def test_sphere_cd_subcritical_plateau() -> None:
    cd = sphere_cd_reference(1e4)
    assert 0.3 < cd < 0.6


def test_sphere_cd_drag_crisis_drop() -> None:
    subcritical = sphere_cd_reference(1e5)
    supercritical = sphere_cd_reference(4e5)
    assert supercritical < subcritical


def test_cone_wave_drag_requires_supersonic() -> None:
    with pytest.raises(ValueError):
        slender_cone_wave_drag_cd(10.0, 0.8)


def test_cone_wave_drag_increases_with_half_angle() -> None:
    narrow = slender_cone_wave_drag_cd(5.0, 2.0)
    wide = slender_cone_wave_drag_cd(15.0, 2.0)
    assert wide > narrow


def test_cylinder_cd_subcritical_and_drag_crisis() -> None:
    subcritical = cylinder_cd_reference(1e4)
    crisis = cylinder_cd_reference(3e5)
    assert 1.0 <= subcritical <= 1.3
    assert crisis < subcritical


def test_naca0012_reference_lift_and_drag() -> None:
    cl_0, cd_0 = naca0012_reference(mach=0.2, reynolds_chord=1e6, alpha_deg=0.0)
    assert cl_0 == pytest.approx(0.0)
    assert 0.007 <= cd_0 <= 0.010

    cl_4, cd_4 = naca0012_reference(mach=0.2, reynolds_chord=1e6, alpha_deg=4.0)
    assert cl_4 > cl_0
    assert cd_4 > cd_0


def test_apollo_capsule_reference_supersonic() -> None:
    cd_0, cl_0, xcp_0 = apollo_capsule_reference(mach=2.0, alpha_deg=0.0)
    assert 1.2 <= cd_0 <= 1.35
    assert cl_0 == pytest.approx(0.0)
    assert 0.6 <= xcp_0 <= 0.7

    cd_20, cl_20, _ = apollo_capsule_reference(mach=2.0, alpha_deg=20.0)
    assert cl_20 > 0.0
    assert 0.25 <= (cl_20 / cd_20) <= 0.40


def test_full_canonical_validation_suite_cases() -> None:
    suite = full_canonical_validation_suite()
    case_names = [c.name for c in suite]
    assert "sphere" in case_names
    assert "cylinder" in case_names
    assert "flat_plate" in case_names
    assert "cone" in case_names
    assert "naca0012" in case_names
    assert "apollo_capsule" in case_names
