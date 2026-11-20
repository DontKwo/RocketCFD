"""3D model loading (mesh and CAD formats), watertight repair, and panel-mesh extraction."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pymeshfix
import trimesh

MESH_EXTENSIONS = {".stl", ".obj", ".ply"}
BREP_EXTENSIONS = {".step", ".stp", ".iges", ".igs"}

CAD_INSTALL_HINT = "STEP/IGES support requires the optional CAD backend. Install it with: pip install -e .[cad]"
MANUAL_REPAIR_HINT = (
    "Automatic repair could not make this mesh watertight. Fix it manually in a mesh/CAD "
    "tool (fill holes, remove duplicate/degenerate faces, unify normals) and reload it."
)


class GeometryNotWatertightError(ValueError):
    """Raised when a loaded mesh is not watertight and automatic repair failed."""


@dataclass
class RepairReport:
    was_watertight: bool
    is_watertight: bool
    method: str
    repairs_applied: list[str] = field(default_factory=list)


@dataclass
class GeometryValidationReport:
    is_watertight: bool
    is_manifold: bool
    non_manifold_edge_count: int
    degenerate_face_count: int
    bounds: tuple[float, float, float, float, float, float]
    characteristic_length: float
    scale_warning: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class PanelMesh:
    vertices: np.ndarray
    faces: np.ndarray
    centroids: np.ndarray
    normals: np.ndarray
    areas: np.ndarray
    face_regions: np.ndarray | None = None

    @property
    def panel_count(self) -> int:
        return int(self.faces.shape[0])

    def centroid(self) -> np.ndarray:
        return np.average(self.centroids, axis=0, weights=self.areas)

    def bounds(self) -> tuple[float, float, float, float, float, float]:
        low = self.vertices.min(axis=0)
        high = self.vertices.max(axis=0)
        return (float(low[0]), float(high[0]), float(low[1]), float(high[1]), float(low[2]), float(high[2]))


def brep_backend_available() -> bool:
    """Cheap probe for the optional CAD backend; never raises."""
    try:
        return importlib.util.find_spec("OCP") is not None
    except (ImportError, ValueError):
        return False


def load_model(path: str | Path) -> trimesh.Trimesh:
    """Loads a triangulated mesh (STL/OBJ/PLY) directly, or tessellates a STEP/IGES
    BREP model into a mesh via the optional OCP backend."""
    ext = Path(path).suffix.lower()
    if ext in BREP_EXTENSIONS:
        if not brep_backend_available():
            raise RuntimeError(CAD_INSTALL_HINT)
        from rocketcfd.brep_backend import brep_load, brep_tessellate  # noqa: 13 (optional CAD backend, see brep_backend module docstring)
        shape = brep_load(str(path))
        vertices, faces = brep_tessellate(shape)
        if len(faces) == 0:
            raise ValueError(f"{path} tessellated to an empty mesh")
        return trimesh.Trimesh(vertices=vertices, faces=faces)
    if ext not in MESH_EXTENSIONS:
        raise ValueError(f"Unsupported 3D model format: {ext}")
    mesh = trimesh.load(str(path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path} did not load as a single triangular mesh")
    return mesh


def validate_geometry(mesh: trimesh.Trimesh) -> GeometryValidationReport:
    """Validates geometry watertightness, non-manifold edges, degenerate faces, and scale."""
    low = mesh.vertices.min(axis=0)
    high = mesh.vertices.max(axis=0)
    bounds = (
        float(low[0]), float(high[0]),
        float(low[1]), float(high[1]),
        float(low[2]), float(high[2]),
    )
    span = high - low
    char_length = float(np.max(span)) if len(span) > 0 else 1.0

    degenerate_faces = int(np.sum(mesh.area_faces <= 1e-12))
    edges = mesh.edges_sorted
    if len(edges) > 0:
        _, edge_counts = np.unique(edges, axis=0, return_counts=True)
        non_manifold = int(np.sum(edge_counts > 2))
    else:
        non_manifold = 0

    warnings: list[str] = []
    scale_warning: str | None = None
    if char_length > 100.0:
        scale_warning = f"Characteristic length {char_length:.1f} m is large; verify model is not in millimeters."
        warnings.append(scale_warning)
    elif char_length < 0.05:
        scale_warning = f"Characteristic length {char_length:.3f} m is small; verify model scale."
        warnings.append(scale_warning)

    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight.")
    if non_manifold > 0:
        warnings.append(f"Mesh has {non_manifold} non-manifold edges.")
    if degenerate_faces > 0:
        warnings.append(f"Mesh has {degenerate_faces} zero-area degenerate faces.")

    return GeometryValidationReport(
        is_watertight=bool(mesh.is_watertight),
        is_manifold=(non_manifold == 0),
        non_manifold_edge_count=non_manifold,
        degenerate_face_count=degenerate_faces,
        bounds=bounds,
        characteristic_length=char_length,
        scale_warning=scale_warning,
        warnings=warnings,
    )


def check_farfield_domain(
    mesh_bounds: tuple[float, float, float, float, float, float],
    domain_bounds: tuple[float, float, float, float, float, float],
) -> list[str]:
    """Checks whether the domain box provides adequate margins around the geometry."""
    warnings: list[str] = []
    m_xmin, m_xmax, m_ymin, m_ymax, m_zmin, m_zmax = mesh_bounds
    d_xmin, d_xmax, d_ymin, d_ymax, d_zmin, d_zmax = domain_bounds
    length = max(m_xmax - m_xmin, 1e-6)

    upstream = m_xmin - d_xmin
    downstream = d_xmax - m_xmax
    lateral_y = min(m_ymin - d_ymin, d_ymax - m_ymax)
    lateral_z = min(m_zmin - d_zmin, d_zmax - m_zmax)

    if upstream < 2.0 * length:
        warnings.append(f"Upstream margin ({upstream:.2f} m) is less than 2x body length ({length:.2f} m).")
    if downstream < 5.0 * length:
        warnings.append(f"Downstream margin ({downstream:.2f} m) is less than 5x body length ({length:.2f} m).")
    if min(lateral_y, lateral_z) < 2.0 * length:
        warnings.append(f"Lateral margin ({min(lateral_y, lateral_z):.2f} m) is less than 2x body length.")
    return warnings


def ensure_watertight(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, RepairReport]:
    """Attempts automatic repair and logs steps taken without mutating the input mesh."""
    was_watertight = bool(mesh.is_watertight)
    if was_watertight:
        return mesh.copy(), RepairReport(True, True, "none", ["none"])

    repairs: list[str] = []
    repaired = mesh.copy()
    trimesh.repair.fix_winding(repaired)
    repairs.append("fix_winding")
    trimesh.repair.fix_normals(repaired)
    repairs.append("fix_normals")
    trimesh.repair.fill_holes(repaired)
    repairs.append("fill_holes")
    if repaired.is_watertight:
        return repaired, RepairReport(False, True, "trimesh_fill_holes", repairs)

    fixed_vertices, fixed_faces = _pymeshfix_repair(mesh.vertices, mesh.faces)
    repaired = trimesh.Trimesh(vertices=fixed_vertices, faces=fixed_faces, process=True)
    repairs.append("pymeshfix")
    if not repaired.is_watertight:
        raise GeometryNotWatertightError(MANUAL_REPAIR_HINT)
    return repaired, RepairReport(False, True, "pymeshfix", repairs)


def _pymeshfix_repair(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    fixer = pymeshfix.MeshFix(vertices, faces)
    fixer.repair()
    return fixer.points, fixer.faces


def scale_mesh(mesh: trimesh.Trimesh, factor: float) -> trimesh.Trimesh:
    scaled = mesh.copy()
    scaled.apply_scale(factor)
    return scaled


def rotate_mesh(mesh: trimesh.Trimesh, angles_deg: tuple[float, float, float]) -> trimesh.Trimesh:
    """Rotates the mesh about the origin by the given X, then Y, then Z angles (degrees).
    This is the single point where a user-chosen orientation is baked into the geometry
    that both the 3D view and the CFD solve consume."""
    rotated = mesh.copy()
    rx, ry, rz = (np.radians(angle) for angle in angles_deg)
    matrix = trimesh.transformations.euler_matrix(rx, ry, rz, axes="sxyz")
    rotated.apply_transform(matrix)
    return rotated


def to_panel_mesh(mesh: trimesh.Trimesh, face_regions: np.ndarray | None = None) -> PanelMesh:
    return PanelMesh(
        vertices=np.asarray(mesh.vertices, dtype=np.float64),
        faces=np.asarray(mesh.faces, dtype=np.int64),
        centroids=np.asarray(mesh.triangles_center, dtype=np.float64),
        normals=np.asarray(mesh.face_normals, dtype=np.float64),
        areas=np.asarray(mesh.area_faces, dtype=np.float64),
        face_regions=face_regions,
    )


def frontal_area(panel_mesh: PanelMesh, direction_unit: np.ndarray) -> float:
    """Projected (silhouette) area of the mesh as seen looking along direction_unit,
    used as the default aerodynamic reference area."""
    cos_impact = panel_mesh.normals @ direction_unit
    projected = np.clip(-cos_impact, 0.0, 1.0) * panel_mesh.areas
    return float(projected.sum())
