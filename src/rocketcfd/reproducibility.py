"""Reproducibility manifest creation, packaging, and validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from rocketcfd.flow import FlowCondition
from rocketcfd.openfoam.settings import MeshSettings, SolverSettings


@dataclass
class ReproducibilityManifest:
    version: str
    created_at_utc: str
    geometry_hash: str
    units: str
    reference_area: float
    reference_length: float
    coordinate_convention: str
    flow_condition: dict[str, Any]
    mesh_settings: dict[str, Any]
    mesh_quality_metrics: dict[str, Any]
    solver_settings: dict[str, Any]
    solver_application: str
    convergence_summary: dict[str, Any]
    aerodynamic_coefficients: dict[str, Any]
    center_of_pressure_x: float | None
    manifest_checksum: str = field(default="")


def _compute_checksum(payload: dict[str, Any]) -> str:
    cleaned = {k: v for k, v in payload.items() if k != "manifest_checksum"}
    encoded = json.dumps(cleaned, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_manifest(
    geometry_hash: str,
    units: str,
    reference_area: float,
    reference_length: float,
    condition: FlowCondition,
    mesh_settings: MeshSettings,
    solver_settings: SolverSettings,
    solver_application: str,
    mesh_quality_metrics: dict[str, Any],
    convergence_summary: dict[str, Any],
    coefficients: dict[str, Any],
    center_of_pressure_x: float | None = None,
    coordinate_convention: str = "x_aft_y_port_z_up",
) -> ReproducibilityManifest:
    """Assembles a full provenance and reproducibility record for a CFD case."""
    now_utc = datetime.now(timezone.utc).isoformat()
    raw_payload: dict[str, Any] = {
        "version": "0.1.0",
        "created_at_utc": now_utc,
        "geometry_hash": geometry_hash,
        "units": units,
        "reference_area": reference_area,
        "reference_length": reference_length,
        "coordinate_convention": coordinate_convention,
        "flow_condition": {
            "name": condition.name,
            "velocity": condition.velocity,
            "density": condition.density,
            "temperature": condition.temperature,
            "alpha_deg": condition.alpha_deg,
            "beta_deg": condition.beta_deg,
            "mach": condition.mach(),
        },
        "mesh_settings": asdict(mesh_settings),
        "mesh_quality_metrics": mesh_quality_metrics,
        "solver_settings": asdict(solver_settings),
        "solver_application": solver_application,
        "convergence_summary": convergence_summary,
        "aerodynamic_coefficients": coefficients,
        "center_of_pressure_x": center_of_pressure_x,
    }
    checksum = _compute_checksum(raw_payload)
    return ReproducibilityManifest(
        version=raw_payload["version"],
        created_at_utc=raw_payload["created_at_utc"],
        geometry_hash=raw_payload["geometry_hash"],
        units=raw_payload["units"],
        reference_area=raw_payload["reference_area"],
        reference_length=raw_payload["reference_length"],
        coordinate_convention=raw_payload["coordinate_convention"],
        flow_condition=raw_payload["flow_condition"],
        mesh_settings=raw_payload["mesh_settings"],
        mesh_quality_metrics=raw_payload["mesh_quality_metrics"],
        solver_settings=raw_payload["solver_settings"],
        solver_application=raw_payload["solver_application"],
        convergence_summary=raw_payload["convergence_summary"],
        aerodynamic_coefficients=raw_payload["aerodynamic_coefficients"],
        center_of_pressure_x=raw_payload["center_of_pressure_x"],
        manifest_checksum=checksum,
    )


def save_manifest(manifest: ReproducibilityManifest, target_file: Path) -> Path:
    """Writes the reproducibility manifest to target JSON file."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(asdict(manifest), indent=2))
    return target_file


def verify_manifest(manifest_path: Path) -> bool:
    """Verifies that an exported manifest's internal sha256 checksum matches its payload."""
    if not manifest_path.exists():
        return False
    data = json.loads(manifest_path.read_text())
    expected_checksum = data.get("manifest_checksum", "")
    calculated_checksum = _compute_checksum(data)
    return expected_checksum == calculated_checksum
