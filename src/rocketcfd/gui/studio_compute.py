"""Pure-Python geometry, solver-regime, CAD import, 3D mesh serialization, and TACC helpers."""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from rocketcfd.atmosphere import us_standard_atmosphere
from rocketcfd.flow import FlowCondition
from rocketcfd.gas import speed_of_sound, sutherland_viscosity
from rocketcfd.geometry import (
    PanelMesh,
    brep_backend_available,
    frontal_area,
    load_model,
    rotate_mesh,
    scale_mesh,
    to_panel_mesh,
    validate_geometry,
)
from rocketcfd.openfoam.boundary_layer import first_layer_thickness
from rocketcfd.openfoam.case_builder import write_mesh_case
from rocketcfd.openfoam.runner import find_openfoam_bashrc_native, list_wsl_distros
from rocketcfd.openfoam.settings import (
    MESH_PRESET_NAMES,
    MESH_PRESETS,
    TURBULENCE_MODELS,
    mesh_settings_for_preset,
)
from rocketcfd.solver_selection import (
    DEFAULT_MACH_CEILING,
    HARD_MACH_LIMIT,
    MachOutOfRangeError,
    select_solver,
)
from rocketcfd.tacc import TaccSettings, generate_slurm_script
from rocketcfd.templates_geometry import (
    NOSECONE_SHAPES,
    assemble_rocket,
    boattail,
    body_tube,
    nosecone,
    trapezoidal_fin,
)
from rocketcfd.validation.reference_data import (
    apollo_capsule_reference,
    cylinder_cd_reference,
    flat_plate_cf,
    naca0012_reference,
    slender_cone_wave_drag_cd,
    sphere_cd_reference,
)

UNIT_TO_METERS = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "in": 0.0254,
    "ft": 0.3048,
}


def _encode_figure_data_url(figure: Figure) -> str:
    """Render a matplotlib figure to a base64 PNG data URI and close it."""
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=135, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _positive_float(payload: dict[str, Any], key: str, default: float) -> float:
    """Parse a positive float parameter or raise ValueError."""
    raw = payload.get(key, default)
    parsed_value = float(raw)
    if parsed_value <= 0.0:
        raise ValueError(f"{key} must be positive (got {parsed_value:g}).")
    return parsed_value


def serialize_panel_mesh_3d(panel: PanelMesh, max_faces: int = 12000) -> dict[str, Any]:
    """Serialize PanelMesh geometry and aerodynamic pressure preview scalars for Three.js."""
    verts = panel.vertices
    faces = panel.faces
    normals = panel.normals
    n_verts = int(verts.shape[0])

    # Compute modified-Newtonian surface Cp preview (-n_x freestream windward component)
    face_cp = 2.0 * (np.clip(-normals[:, 0], 0.0, 1.0) ** 2)
    vertex_cp_sum = np.zeros(n_verts, dtype=np.float64)
    vertex_counts = np.zeros(n_verts, dtype=np.int32)
    for corner_idx in range(3):
        vertex_ids = faces[:, corner_idx]
        np.add.at(vertex_cp_sum, vertex_ids, face_cp)
        np.add.at(vertex_counts, vertex_ids, 1)
    vertex_cp = np.divide(vertex_cp_sum, np.maximum(vertex_counts, 1))

    x_min, x_max = float(verts[:, 0].min()), float(verts[:, 0].max())
    axial_span = max(x_max - x_min, 1e-6)
    axial_norm = (verts[:, 0] - x_min) / axial_span

    stride = max(1, len(faces) // max_faces)
    sampled_faces = faces[::stride]
    return {
        "positions": np.round(verts.reshape(-1), 5).tolist(),
        "indices": sampled_faces.reshape(-1).astype(int).tolist(),
        "cpScalars": np.round(vertex_cp, 4).tolist(),
        "axialScalars": np.round(axial_norm, 4).tolist(),
        "bounds": [round(bound_coord, 5) for bound_coord in panel.bounds()],
        "vertexCount": n_verts,
        "faceCount": int(sampled_faces.shape[0]),
    }


def build_default_panel_mesh() -> PanelMesh:
    """Construct default parametric rocket PanelMesh for initial Studio session."""
    panel, _report, _params = _assemble_panel_mesh({})
    return panel


def _assemble_panel_mesh(payload: dict[str, Any]) -> tuple[PanelMesh, Any, dict[str, float]]:
    """Construct parametric rocket geometry from UI inputs and convert to PanelMesh."""
    nose_shape = str(payload.get("nosecone_shape", "ogive")).strip()
    if nose_shape not in NOSECONE_SHAPES:
        raise ValueError(f"Unsupported nosecone shape '{nose_shape}'.")

    nose_len = _positive_float(payload, "nosecone_length", 0.45)
    body_len = _positive_float(payload, "body_length", 1.55)
    diameter = _positive_float(payload, "diameter", 0.15)
    fin_count = max(3, min(8, int(payload.get("fin_count", 4))))
    fin_span = _positive_float(payload, "fin_span", 0.14)
    fin_root = _positive_float(payload, "fin_root_chord", 0.24)
    fin_tip = _positive_float(payload, "fin_tip_chord", 0.11)
    fin_sweep = max(0.0, float(payload.get("fin_sweep", 0.09)))
    fin_thickness = 0.008
    use_boattail = bool(payload.get("boattail_enabled", True))
    tail_len = _positive_float(payload, "boattail_length", 0.14) if use_boattail else 0.0
    tail_dia = min(diameter * 0.95, _positive_float(payload, "boattail_aft_diameter", diameter * 0.72)) if use_boattail else diameter

    nose_mesh = nosecone(length=nose_len, base_diameter=diameter, shape=nose_shape)
    tube_mesh = body_tube(length=body_len, diameter=diameter)
    fins = [
        trapezoidal_fin(fin_root, fin_tip, fin_span, fin_sweep, fin_thickness)
        for _idx in range(fin_count)
    ]
    tail_mesh = boattail(tail_len, diameter, tail_dia) if use_boattail else None
    combined = assemble_rocket(nose_mesh, tube_mesh, fins=fins, boattail_mesh=tail_mesh)
    report = validate_geometry(combined)
    panel = to_panel_mesh(combined)
    params = {
        "noseconeLength": nose_len,
        "bodyLength": body_len,
        "diameter": diameter,
        "finCount": float(fin_count),
        "finSpan": fin_span,
        "boattailLength": tail_len,
    }
    return panel, report, params


def _render_geometry_preview(panel: PanelMesh, total_len: float, diameter: float) -> str:
    """Plot dark-slate engineering views (side wireframe & cross-section) to PNG."""
    fig, (axis_side, axis_front) = plt.subplots(
        1, 2, figsize=(10.2, 4.2), gridspec_kw={"width_ratios": [2.2, 1.0]}, facecolor="#0f172a"
    )
    verts = panel.vertices
    faces = panel.faces
    stride = max(1, len(faces) // 1600)
    sampled_faces = faces[::stride]

    for axis_obj in (axis_side, axis_front):
        axis_obj.set_facecolor("#0f172a")
        axis_obj.tick_params(colors="#cbd5e1", labelsize=9)
        for spine in axis_obj.spines.values():
            spine.set_color("#334155")

    tri_x = verts[sampled_faces, 0]
    tri_y = verts[sampled_faces, 1]
    tri_z = verts[sampled_faces, 2]
    axis_side.triplot(verts[:, 0], verts[:, 2], sampled_faces, color="#38bdf8", linewidth=0.35, alpha=0.65)
    axis_side.plot(tri_x.mean(axis=1), tri_z.mean(axis=1), ".", color="#7dd3fc", markersize=0.6, alpha=0.35)
    axis_side.set_title(f"Side Profile X-Z (Length {total_len:.2f} m)", color="#f8fafc", fontsize=11, pad=8)
    axis_side.set_xlabel("Axial X (m)", color="#94a3b8", fontsize=9)
    axis_side.set_ylabel("Vertical Z (m)", color="#94a3b8", fontsize=9)
    axis_side.set_aspect("equal", adjustable="datalim")
    axis_side.grid(True, color="#1e293b", linestyle="--", linewidth=0.7)

    axis_front.triplot(verts[:, 1], verts[:, 2], sampled_faces, color="#22c55e", linewidth=0.35, alpha=0.6)
    axis_front.plot(tri_y.mean(axis=1), tri_z.mean(axis=1), ".", color="#86efac", markersize=0.5, alpha=0.3)
    axis_front.set_title(f"Front Y-Z (Fin Span {diameter:.3f} m)", color="#f8fafc", fontsize=11, pad=8)
    axis_front.set_xlabel("Lateral Y (m)", color="#94a3b8", fontsize=9)
    axis_front.set_aspect("equal", adjustable="datalim")
    axis_front.grid(True, color="#1e293b", linestyle="--", linewidth=0.7)

    fig.tight_layout(pad=1.3)
    return _encode_figure_data_url(fig)


def build_defaults_payload() -> dict[str, Any]:
    """Return studio defaults, presets, OpenFOAM detection status, and benchmarks."""
    presets_info: list[dict[str, Any]] = []
    for name in MESH_PRESET_NAMES:
        cfg = MESH_PRESETS[name]
        presets_info.append({
            "name": name,
            "backgroundCellCount": cfg.background_cell_count,
            "refinementMax": cfg.surface_refinement_max,
            "boundaryLayers": cfg.n_boundary_layers,
            "targetYPlus": cfg.target_y_plus,
        })

    wsl_distros = list_wsl_distros() if os.name == "nt" else []
    native_bashrc = find_openfoam_bashrc_native() if os.name != "nt" else None
    return {
        "ok": True,
        "noseconeShapes": [
            {"id": shape, "label": shape.replace("_", " ").title()}
            for shape in NOSECONE_SHAPES
        ],
        "meshPresets": presets_info,
        "turbulenceModels": list(TURBULENCE_MODELS),
        "machLimits": {"defaultCeiling": DEFAULT_MACH_CEILING, "hardLimit": HARD_MACH_LIMIT},
        "environment": {
            "platform": os.name,
            "wslDistros": wsl_distros,
            "nativeOpenFoamBashrc": native_bashrc or "Not detected locally (optional for preview/export)",
            "dockerAvailable": shutil.which("docker") is not None,
            "brepAvailable": brep_backend_available(),
        },
        "validation": build_validation_payload({}),
    }


def _geometry_response_from_panel(panel: PanelMesh, warnings: list[str], is_manifold: bool, label: str) -> dict[str, Any]:
    """Format uniform geometry metrics, 2D schematic, and 3D WebGL buffer payload."""
    bounds = panel.bounds()
    total_len = bounds[1] - bounds[0]
    diameter = max(bounds[3] - bounds[2], bounds[5] - bounds[4])
    ref_area = frontal_area(panel, np.array([1.0, 0.0, 0.0]))
    preview_url = _render_geometry_preview(panel, total_len, diameter)
    return {
        "ok": True,
        "message": f"Built {label} ({panel.panel_count} triangular panels).",
        "metrics": {
            "panelCount": panel.panel_count,
            "vertexCount": int(panel.vertices.shape[0]),
            "lengthMeters": round(total_len, 4),
            "spanMeters": round(diameter, 4),
            "wettedAreaM2": round(float(panel.areas.sum()), 4),
            "frontalAreaM2": round(ref_area, 5),
            "isManifold": bool(is_manifold),
            "warnings": list(warnings),
        },
        "previewImage": preview_url,
        "mesh3d": serialize_panel_mesh_3d(panel),
    }


def build_geometry_with_panel(payload: dict[str, Any]) -> tuple[dict[str, Any], PanelMesh | None]:
    """Build parametric rocket PanelMesh and return both UI response and active PanelMesh."""
    try:
        panel, report, _params = _assemble_panel_mesh(payload)
    except (ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}, None
    resp = _geometry_response_from_panel(panel, list(report.warnings), bool(report.is_manifold), "parametric rocket assembly")
    return resp, panel


def build_geometry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build parametric rocket PanelMesh, metrics, 2D schematic, and 3D WebGL buffers."""
    resp, _panel = build_geometry_with_panel(payload)
    return resp


def import_cad_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], PanelMesh | None]:
    """Load uploaded STL/OBJ/STEP model, apply unit scaling and Euler rotation, and serialize 3D view."""
    try:
        unit_key = str(payload.get("unit", "m")).strip().lower()
        if unit_key not in UNIT_TO_METERS:
            raise ValueError(f"Unsupported unit '{unit_key}'. Choose one of {tuple(UNIT_TO_METERS)}.")
        scale_factor = _positive_float(payload, "scale", 1.0) * UNIT_TO_METERS[unit_key]
        rot_x = float(payload.get("rot_x", 0.0))
        rot_y = float(payload.get("rot_y", 0.0))
        rot_z = float(payload.get("rot_z", 0.0))

        file_b64 = payload.get("fileBase64")
        file_name = Path(str(payload.get("fileName", "model.stl"))).name
        if isinstance(file_b64, str) and file_b64.strip():
            raw_bytes = base64.b64decode(file_b64.split(",")[-1])
            ext = Path(file_name).suffix.lower() or ".stl"
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_model = Path(tmp_dir) / f"upload{ext}"
                tmp_model.write_bytes(raw_bytes)
                loaded = load_model(tmp_model)
        else:
            raw_path = str(payload.get("filePath", "")).strip()
            if not raw_path:
                raise ValueError("Provide an STL/OBJ/STEP file upload or local file path.")
            model_path = Path(raw_path).expanduser()
            if not model_path.is_file():
                raise ValueError(f"Model file not found: {model_path}")
            loaded = load_model(model_path)
            file_name = model_path.name

        transformed = scale_mesh(loaded, scale_factor)
        if rot_x != 0.0 or rot_y != 0.0 or rot_z != 0.0:
            transformed = rotate_mesh(transformed, (rot_x, rot_y, rot_z))
        report = validate_geometry(transformed)
        panel = to_panel_mesh(transformed)
        resp = _geometry_response_from_panel(
            panel,
            list(report.warnings),
            bool(report.is_manifold),
            f"imported CAD model ({file_name})",
        )
        return resp, panel
    except (ValueError, RuntimeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}, None


def build_condition_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate atmosphere, Mach solver regime, y+ cell sizing, and regime plot."""
    try:
        altitude_m = max(0.0, float(payload.get("altitude_m", 1500.0)))
        velocity_mps = _positive_float(payload, "velocity_mps", 420.0)
        alpha_deg = float(payload.get("alpha_deg", 2.5))
        beta_deg = float(payload.get("beta_deg", 0.0))
        ref_len = _positive_float(payload, "nosecone_length", 0.45) + _positive_float(payload, "body_length", 1.55)
        preset_name = str(payload.get("mesh_preset", "Medium"))
        mesh_cfg = mesh_settings_for_preset(preset_name)
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    atmo = us_standard_atmosphere(altitude_m)
    cond = FlowCondition(
        name=f"M_eval_{int(altitude_m)}m",
        velocity=velocity_mps,
        alpha_deg=alpha_deg,
        beta_deg=beta_deg,
        density=atmo.density,
        temperature=atmo.temperature,
    )
    mach = cond.mach()
    dyn_pressure = cond.dynamic_pressure()
    viscosity = sutherland_viscosity(atmo.temperature)
    reynolds = velocity_mps * ref_len * atmo.density / max(viscosity, 1e-12)
    y_plus_first_m = first_layer_thickness(mesh_cfg.target_y_plus, velocity_mps, atmo.density, viscosity, ref_len)

    try:
        selection = select_solver(mach)
    except MachOutOfRangeError as exc:
        return {"ok": False, "error": str(exc)}

    alts = np.linspace(0.0, 50000.0, 120)
    mach_curve = [velocity_mps / speed_of_sound(us_standard_atmosphere(float(alt)).temperature) for alt in alts]

    fig, axis_env = plt.subplots(figsize=(9.5, 4.0), facecolor="#0f172a")
    axis_env.set_facecolor("#0f172a")
    axis_env.tick_params(colors="#cbd5e1", labelsize=9)
    for spine in axis_env.spines.values():
        spine.set_color("#334155")

    axis_env.axhspan(0.0, 0.3, color="#14532d", alpha=0.25, label="Incompressible (simpleFoam)")
    axis_env.axhspan(0.3, 0.8, color="#1e3a8a", alpha=0.25, label="Subsonic Compressible (rhoSimpleFoam)")
    axis_env.axhspan(0.8, 1.2, color="#78350f", alpha=0.25, label="Transonic (rhoPimpleFoam)")
    axis_env.axhspan(1.2, 3.0, color="#7f1d1d", alpha=0.20, label="Supersonic (rhoCentralFoam)")
    axis_env.plot(alts / 1000.0, mach_curve, color="#38bdf8", linewidth=2.2)
    axis_env.scatter([altitude_m / 1000.0], [mach], color="#22c55e", s=70, zorder=5)
    axis_env.annotate(
        f"Current: {selection.application} (M={mach:.2f})",
        xy=(altitude_m / 1000.0, mach),
        xytext=(6, 8),
        textcoords="offset points",
        color="#f8fafc",
        fontsize=9,
    )
    axis_env.set_title("OpenFOAM Solver Regime vs. Altitude", color="#f8fafc", fontsize=11, pad=8)
    axis_env.set_xlabel("Altitude (km)", color="#94a3b8", fontsize=9)
    axis_env.set_ylabel("Mach Number", color="#94a3b8", fontsize=9)
    axis_env.set_ylim(0.0, max(2.2, max(mach_curve) * 1.15))
    axis_env.grid(True, color="#1e293b", linestyle="--", linewidth=0.7)
    axis_env.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#f8fafc")
    fig.tight_layout(pad=1.2)

    return {
        "ok": True,
        "message": f"Selected {selection.application} ({selection.regime}, Mach {mach:.3f}).",
        "condition": {
            "mach": round(mach, 4),
            "solver": selection.application,
            "regime": selection.regime,
            "compressible": selection.compressible,
            "steady": selection.steady,
            "temperatureK": round(atmo.temperature, 2),
            "pressurePa": round(atmo.pressure, 1),
            "densityKgM3": round(atmo.density, 5),
            "dynamicPressurePa": round(dyn_pressure, 1),
            "reynolds": round(reynolds, 0),
            "firstLayerMeters": float(f"{y_plus_first_m:.3e}"),
            "warnings": list(selection.warnings),
        },
        "solverPlotImage": _encode_figure_data_url(fig),
    }


def export_openfoam_case_payload(payload: dict[str, Any], active_panel: PanelMesh | None = None) -> dict[str, Any]:
    """Generate a complete OpenFOAM mesh/system/triSurface directory on disk."""
    try:
        if active_panel is not None and str(payload.get("geometry_source", "parametric")) == "cad":
            panel = active_panel
        else:
            panel, _report, _params = _assemble_panel_mesh(payload)
        altitude_m = max(0.0, float(payload.get("altitude_m", 1500.0)))
        velocity_mps = _positive_float(payload, "velocity_mps", 420.0)
        preset_name = str(payload.get("mesh_preset", "Medium"))
        mesh_cfg = mesh_settings_for_preset(preset_name)
        atmo = us_standard_atmosphere(altitude_m)
        ref_cond = FlowCondition("export_ref", velocity=velocity_mps, density=atmo.density, temperature=atmo.temperature)
        out_dir = Path(tempfile.mkdtemp(prefix="rocketcfd_case_"))
        write_mesh_case(out_dir, panel, mesh_cfg, mach=ref_cond.mach(), reference_condition=ref_cond)
        generated_files = sorted(str(item.relative_to(out_dir)).replace("\\", "/") for item in out_dir.rglob("*") if item.is_file())
        return {
            "ok": True,
            "message": f"Exported OpenFOAM mesh case ({len(generated_files)} files).",
            "caseDirName": out_dir.name,
            "files": generated_files,
        }
    except (OSError, ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}


def build_validation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute canonical CFD validation reference table and benchmark curve."""
    mach_eval = max(0.2, min(4.0, float(payload.get("mach", 1.8))))
    re_eval = max(1e4, float(payload.get("reynolds", 1.5e6)))
    naca_cl, naca_cd = naca0012_reference(min(mach_eval, 0.7), re_eval, 4.0)
    apollo_cd, apollo_cl, apollo_xcp = apollo_capsule_reference(max(mach_eval, 1.5), 10.0)
    rows = [
        {"benchmark": "Sphere Drag (Schlichting)", "metric": "Cd", "referenceValue": round(sphere_cd_reference(re_eval), 4)},
        {"benchmark": "Circular Cylinder Cross-Flow", "metric": "Cd", "referenceValue": round(cylinder_cd_reference(re_eval), 4)},
        {"benchmark": "Turbulent Flat Plate Skin Friction", "metric": "Cf", "referenceValue": round(flat_plate_cf(re_eval), 5)},
        {"benchmark": "NACA 0012 Airfoil (alpha=4 deg)", "metric": "Cl / Cd", "referenceValue": f"{naca_cl:.3f} / {naca_cd:.4f}"},
        {"benchmark": "10 deg Slender Cone Wave Drag", "metric": "Cd_wave", "referenceValue": round(slender_cone_wave_drag_cd(10.0, max(mach_eval, 1.4)), 4)},
        {"benchmark": "Apollo CM Supersonic (alpha=10 deg)", "metric": "Cd / Cl / Xcp/D", "referenceValue": f"{apollo_cd:.3f} / {apollo_cl:.3f} / {apollo_xcp:.2f}"},
    ]

    mach_sweep = np.linspace(1.15, 4.0, 60)
    cone_cd = [slender_cone_wave_drag_cd(10.0, float(item)) for item in mach_sweep]
    fig, axis_val = plt.subplots(figsize=(9.5, 3.8), facecolor="#0f172a")
    axis_val.set_facecolor("#0f172a")
    axis_val.tick_params(colors="#cbd5e1", labelsize=9)
    for spine in axis_val.spines.values():
        spine.set_color("#334155")
    axis_val.plot(mach_sweep, cone_cd, color="#38bdf8", linewidth=2.2, label="10 deg Slender Cone Linearized Wave Drag")
    axis_val.set_title("Supersonic Reference Benchmark Curve (Slender Cone Wave Drag)", color="#f8fafc", fontsize=11, pad=8)
    axis_val.set_xlabel("Mach Number", color="#94a3b8", fontsize=9)
    axis_val.set_ylabel("Wave Drag Coefficient Cd", color="#94a3b8", fontsize=9)
    axis_val.grid(True, color="#1e293b", linestyle="--", linewidth=0.7)
    axis_val.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#f8fafc")
    fig.tight_layout(pad=1.2)

    return {"ok": True, "rows": rows, "validationImage": _encode_figure_data_url(fig)}


def build_tacc_script_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a ready-to-submit TACC Lonestar6/Stampede SLURM OpenFOAM script."""
    host = str(payload.get("host", "ls6.tacc.utexas.edu")).strip() or "ls6.tacc.utexas.edu"
    username = str(payload.get("username", "researcher")).strip() or "researcher"
    allocation = str(payload.get("allocation", "TG-AER00001")).strip() or "TG-AER00001"
    remote_root = str(payload.get("remote_case_root", "$WORK/rocketcfd")).strip() or "$WORK/rocketcfd"
    job_name = str(payload.get("job_name", "rocketcfd_run")).strip() or "rocketcfd_run"
    application = str(payload.get("application", "rhoCentralFoam")).strip() or "rhoCentralFoam"
    nodes = max(1, int(payload.get("nodes", 1)))
    tasks_per_node = max(1, int(payload.get("tasks_per_node", 56)))
    walltime = str(payload.get("walltime", "02:00:00")).strip() or "02:00:00"
    settings = TaccSettings(
        host=host,
        username=username,
        allocation=allocation,
        remote_case_root=remote_root,
        nodes=nodes,
        tasks_per_node=tasks_per_node,
        walltime=walltime,
    )
    script = generate_slurm_script(job_name, f"{remote_root}/{job_name}", application, settings)
    return {"ok": True, "message": "Generated TACC SLURM batch script.", "script": script}
