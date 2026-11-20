"""Unit tests for reproducibility manifest generation, storage, and checksum validation."""
from __future__ import annotations

import json
from pathlib import Path

from rocketcfd.flow import FlowCondition
from rocketcfd.openfoam.settings import MeshSettings, SolverSettings
from rocketcfd.reproducibility import build_manifest, save_manifest, verify_manifest


def test_build_and_verify_manifest(tmp_path: Path) -> None:
    condition = FlowCondition(name="test_cond", velocity=100.0, alpha_deg=1.0, beta_deg=0.0)
    manifest = build_manifest(
        geometry_hash="abc123hash",
        units="m",
        reference_area=0.25,
        reference_length=1.5,
        condition=condition,
        mesh_settings=MeshSettings(),
        solver_settings=SolverSettings(),
        solver_application="simpleFoam",
        mesh_quality_metrics={"max_skewness": 1.5, "cell_count": 50000},
        convergence_summary={"status": "CONVERGED"},
        coefficients={"cd": 0.42, "cl": 0.15},
        center_of_pressure_x=0.75,
    )
    assert manifest.version == "0.1.0"
    assert manifest.manifest_checksum != ""

    target_file = tmp_path / "case_manifest.json"
    save_manifest(manifest, target_file)
    assert target_file.exists()
    assert verify_manifest(target_file)


def test_verify_manifest_detects_tampering(tmp_path: Path) -> None:
    condition = FlowCondition(name="test_cond", velocity=100.0)
    manifest = build_manifest(
        geometry_hash="original_hash",
        units="m",
        reference_area=0.1,
        reference_length=1.0,
        condition=condition,
        mesh_settings=MeshSettings(),
        solver_settings=SolverSettings(),
        solver_application="rhoSimpleFoam",
        mesh_quality_metrics={},
        convergence_summary={},
        coefficients={},
    )
    target_file = tmp_path / "tampered_manifest.json"
    save_manifest(manifest, target_file)

    # Tamper with the file contents without updating the checksum.
    data = json.loads(target_file.read_text())
    data["geometry_hash"] = "tampered_hash"
    target_file.write_text(json.dumps(data))

    assert not verify_manifest(target_file)


def test_verify_manifest_non_existent_file(tmp_path: Path) -> None:
    assert not verify_manifest(tmp_path / "does_not_exist.json")
