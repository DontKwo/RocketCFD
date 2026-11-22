"""Unit tests for the supported physics envelope, limitations, and regime descriptions."""
from __future__ import annotations

import pytest

from rocketcfd.flow import FlowCondition
from rocketcfd.physics_envelope import (
    CERTIFICATION_DISCLAIMER,
    PHYSICS_ENVELOPE,
    explain_physics_regime,
    validate_flow_condition_envelope,
)


def test_envelope_has_disclaimer_and_geometry_classes() -> None:
    assert CERTIFICATION_DISCLAIMER in PHYSICS_ENVELOPE.disclaimer
    assert "axisymmetric_rockets" in PHYSICS_ENVELOPE.geometry_classes
    assert "capsules" in PHYSICS_ENVELOPE.geometry_classes
    assert len(PHYSICS_ENVELOPE.limitations) > 0


def test_validate_condition_inside_envelope_clean() -> None:
    condition = FlowCondition(
        name="nominal_subsonic",
        velocity=150.0,
        density=1.225,
        temperature=288.15,
        alpha_deg=2.0,
        beta_deg=0.0,
    )
    warnings = validate_flow_condition_envelope(condition)
    assert warnings == []


def test_validate_condition_flags_excessive_mach() -> None:
    # Freestream speed corresponding to Mach ~ 10 at standard sea level temperature.
    condition = FlowCondition(name="hypersonic", velocity=3400.0, alpha_deg=0.0, beta_deg=0.0, density=1.225, temperature=288.15)
    warnings = validate_flow_condition_envelope(condition)
    assert any("exceeds hard limit" in w for w in warnings)


def test_validate_condition_flags_extreme_temperatures() -> None:
    cryo = FlowCondition(name="cold", velocity=100.0, alpha_deg=0.0, beta_deg=0.0, density=1.225, temperature=100.0)
    hot = FlowCondition(name="hot", velocity=100.0, alpha_deg=0.0, beta_deg=0.0, density=1.225, temperature=800.0)
    assert any("below standard atmospheric" in w for w in validate_flow_condition_envelope(cryo))
    assert any("calorically perfect air" in w for w in validate_flow_condition_envelope(hot))


def test_explain_physics_regime_covers_all_regimes() -> None:
    incomp = explain_physics_regime(0.1)
    assert incomp["regime"] == "incompressible"
    assert incomp["application"] == "simpleFoam"
    assert "omitted_physics" in incomp

    subsonic = explain_physics_regime(0.5)
    assert subsonic["regime"] == "subsonic_compressible"
    assert subsonic["application"] == "rhoSimpleFoam"

    transonic = explain_physics_regime(0.95)
    assert transonic["regime"] == "transonic"
    assert transonic["application"] == "rhoPimpleFoam"

    supersonic = explain_physics_regime(2.0)
    assert supersonic["regime"] == "supersonic"
    assert supersonic["application"] == "rhoCentralFoam"
