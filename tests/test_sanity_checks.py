"""Negative-drag, discontinuity, and convergence sanity flags."""
from __future__ import annotations

import numpy as np

from rocketcfd.sanity_checks import (
    assess_comprehensive_convergence,
    build_sanity_report,
    check_convergence,
    check_discontinuities,
    check_force_moment_convergence,
    check_negative_drag,
)


def test_negative_drag_flagged() -> None:
    flags = check_negative_drag([0.5, -0.1, 0.3])
    assert len(flags) == 1
    assert flags[0].case_index == 1


def test_no_negative_drag_no_flags() -> None:
    assert check_negative_drag([0.5, 0.6, 0.3]) == []


def test_discontinuity_detected() -> None:
    flags = check_discontinuities([0.0, 1.0, 2.0], [0.5, 0.51, 2.0], threshold_pct=25.0)
    assert len(flags) == 1


def test_smooth_sweep_no_discontinuity() -> None:
    flags = check_discontinuities([0.0, 1.0, 2.0], [0.5, 0.52, 0.54], threshold_pct=25.0)
    assert flags == []


def test_convergence_pass() -> None:
    assert check_convergence([1e-2, 1e-3, 1e-5], threshold=1e-4) is None


def test_convergence_fail() -> None:
    flag = check_convergence([1e-2, 1e-3, 1e-3], threshold=1e-4)
    assert flag is not None


def test_convergence_empty_history_flags() -> None:
    flag = check_convergence([])
    assert flag is not None


def test_build_sanity_report_combines_checks() -> None:
    report = build_sanity_report(cd_values=[-0.1, 0.5, 5.0], x_values=[0.0, 1.0, 2.0])
    assert not report.clean
    assert len(report.flags) >= 1


def test_force_moment_convergence_stable() -> None:
    forces = np.array([[10.0, 0.0, 0.0]] * 20)
    moments = np.array([[0.0, 5.0, 0.0]] * 20)
    eval_res = check_force_moment_convergence(forces, moments)
    assert eval_res.converged
    assert eval_res.force_variation_pct == 0.0


def test_force_moment_convergence_unstable() -> None:
    # Fluctuating forces (oscillations).
    forces = np.array([[10.0 + (i % 2) * 5.0, 0.0, 0.0] for i in range(20)])
    moments = np.array([[0.0, 5.0, 0.0]] * 20)
    eval_res = check_force_moment_convergence(forces, moments, max_variation_pct=1.0)
    assert not eval_res.converged
    assert eval_res.force_variation_pct > 1.0


def test_assess_comprehensive_convergence_converged() -> None:
    residuals = {
        "p": (np.array([1.0, 2.0]), np.array([1e-2, 1e-5])),
        "Ux": (np.array([1.0, 2.0]), np.array([1e-2, 1e-6])),
    }
    forces = np.array([[10.0, 0.0, 0.0]] * 10)
    moments = np.array([[0.0, 5.0, 0.0]] * 10)
    assessment = assess_comprehensive_convergence(residuals, forces, moments, residual_threshold=1e-4)
    assert assessment.status == "CONVERGED"
    assert assessment.residuals_converged
    assert assessment.forces_converged


def test_assess_comprehensive_convergence_oscillatory() -> None:
    residuals = {"p": (np.array([1.0, 2.0]), np.array([1e-2, 1e-5]))}
    forces = np.array([[10.0 + (i % 2) * 2.0, 0.0, 0.0] for i in range(10)])
    moments = np.array([[0.0, 5.0, 0.0]] * 10)
    assessment = assess_comprehensive_convergence(residuals, forces, moments)
    assert assessment.status == "OSCILLATORY_FORCES"
    assert not assessment.forces_converged
