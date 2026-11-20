"""Unit tests for Roache Grid Convergence Index (GCI) calculations."""
from __future__ import annotations

import pytest

from rocketcfd.uncertainty import calculate_gci


def test_gci_monotonic_convergence() -> None:
    # 3 systematically refined meshes with known 2nd-order convergence.
    coarse_n = 100_000
    med_n = 800_000
    fine_n = 6_400_000

    f3 = 0.500
    f2 = 0.450
    f1 = 0.435

    result = calculate_gci(coarse_n, med_n, fine_n, f3, f2, f1, dimension=3)
    assert result.convergence_type == "monotonic"
    assert result.r21 == pytest.approx(2.0, rel=1e-3)
    assert result.r32 == pytest.approx(2.0, rel=1e-3)
    assert 1.0 <= result.apparent_order <= 3.0
    assert result.gci_fine_pct < result.gci_medium_pct
    assert result.asymptotic_ratio > 0.0


def test_gci_exact_match_zero_uncertainty() -> None:
    result = calculate_gci(100, 200, 400, 1.0, 1.0, 1.0)
    assert result.convergence_type == "exact_match"
    assert result.gci_fine_pct == 0.0
    assert result.extrapolated_value == 1.0


def test_gci_oscillatory_behavior() -> None:
    result = calculate_gci(100, 200, 400, 1.0, 1.1, 1.05)
    assert result.convergence_type == "oscillatory"


def test_gci_diverging_behavior() -> None:
    result = calculate_gci(100, 200, 400, 1.0, 1.1, 1.3)
    assert result.convergence_type == "diverging"


def test_gci_requires_monotonic_cell_counts() -> None:
    with pytest.raises(ValueError, match="Cell counts"):
        calculate_gci(500, 200, 800, 1.0, 1.1, 1.2)


def test_gci_requires_positive_dimension() -> None:
    with pytest.raises(ValueError, match="Spatial dimension"):
        calculate_gci(100, 200, 400, 1.0, 1.1, 1.2, dimension=0)
