"""checkMesh output parsing and the mesh-quality pass/fail gate."""
from __future__ import annotations

from rocketcfd.openfoam.mesh_quality import (
    evaluate_mesh_quality,
    get_boundary_layer_targets,
    parse_check_mesh_output,
)
from rocketcfd.openfoam.settings import MeshSettings

PASSING_LOG = """
Checking geometry...
cells: 45200
Mesh non-orthogonality Max: 42.1 average: 10.2
Max skewness = 1.8 OK.
Max aspect ratio = 4.2 OK.
Mesh OK.
"""

FAILING_LOG = """
Checking geometry...
cells: 85000
***Max non-orthogonality = 72.4, this may impair the quality of the results
***Max skewness = 6.1, this may impair the quality of the results
***Max aspect ratio = 1250.0, this may impair the quality of the results
Failed 3 mesh checks.
"""


def test_parse_passing_log() -> None:
    report = parse_check_mesh_output(PASSING_LOG)
    assert report.max_non_orthogonality == 42.1
    assert report.average_non_orthogonality == 10.2
    assert report.max_skewness == 1.8
    assert report.max_aspect_ratio == 4.2
    assert report.cell_count == 45200
    assert report.checkmesh_reported_ok
    assert report.failed_check_count == 0


def test_parse_failing_log() -> None:
    report = parse_check_mesh_output(FAILING_LOG)
    assert report.max_non_orthogonality == 72.4
    assert report.max_skewness == 6.1
    assert report.max_aspect_ratio == 1250.0
    assert report.cell_count == 85000
    assert not report.checkmesh_reported_ok
    assert report.failed_check_count == 3


def test_evaluate_passes_within_thresholds() -> None:
    report = parse_check_mesh_output(PASSING_LOG)
    result = evaluate_mesh_quality(report, MeshSettings())
    assert result.passed


def test_evaluate_fails_outside_thresholds() -> None:
    report = parse_check_mesh_output(FAILING_LOG)
    result = evaluate_mesh_quality(report, MeshSettings())
    assert not result.passed
    assert result.reasons
    assert any("aspect ratio" in r for r in result.reasons)


def test_evaluate_gate_disabled_always_passes() -> None:
    report = parse_check_mesh_output(FAILING_LOG)
    settings = MeshSettings(require_mesh_quality_pass=False)
    result = evaluate_mesh_quality(report, settings)
    assert result.passed


def test_get_boundary_layer_targets() -> None:
    resolved = get_boundary_layer_targets("kOmegaSST", wall_resolved=True)
    assert resolved.target_y_plus == 1.0
    assert resolved.wall_resolved

    modeled = get_boundary_layer_targets("kOmegaSST", wall_resolved=False)
    assert modeled.target_y_plus == 30.0
    assert not modeled.wall_resolved
