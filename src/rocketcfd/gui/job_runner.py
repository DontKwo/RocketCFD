"""Background OpenFOAM sweep, validation runner, and solved-case importer for WebView Studio."""
from __future__ import annotations

import base64
from collections.abc import Callable
import csv
from dataclasses import dataclass, field
import io
import os
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Any
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rocketcfd.atmosphere import us_standard_atmosphere
from rocketcfd.flow import FlowCondition
from rocketcfd.geometry import PanelMesh
from rocketcfd.gui.openfoam_results import RESULT_HEADERS, format_case_table_rows
from rocketcfd.openfoam.case_result import OpenFoamCaseResult, find_case_roots, import_case_results, run_openfoam_sweep
from rocketcfd.openfoam.execution import ExecutionBackend, NativeLinuxExecutionBackend, NativeLinuxSettings, WslExecutionBackend, WslSettings
from rocketcfd.openfoam.results_parser import parse_residual_history
from rocketcfd.openfoam.runner import solve_log_filename, stream_process
from rocketcfd.openfoam.settings import SolverSettings, mesh_settings_for_preset
from rocketcfd.sweep import SweepAxis, build_conditions, parse_values
from rocketcfd.validation.runner import default_validation_suite, full_canonical_validation_suite, run_validation_suite


@dataclass
class DockerSettings:
    """Configuration for executing OpenFOAM commands inside a Docker container."""

    image: str = "microfluidica/openfoam:2412"
    openfoam_bashrc: str = "/usr/lib/openfoam/openfoam2412/etc/bashrc"
    case_root: Path = field(default_factory=lambda: Path.home() / "rocketcfd-openfoam-cases")


@dataclass
class DockerExecutionBackend:
    """Execution backend wrapping OpenFOAM container commands via Docker CLI."""

    settings: DockerSettings

    @property
    def case_root(self) -> Path:
        return self.settings.case_root

    def ensure_ready(self, on_log: Callable[[str], None]) -> None:
        if not shutil.which("docker"):
            raise RuntimeError("Docker CLI not found in PATH. Install Docker Desktop (see OpenFOAM Installation Guide).")
        probe = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10, check=False)
        if probe.returncode != 0:
            raise RuntimeError("Docker daemon is not running. Start Docker Desktop before running solves.")
        on_log(f"Using Docker OpenFOAM runtime ({self.settings.image}).")

    def available_processors(self) -> int:
        return max(1, os.cpu_count() or 1)

    def run(self, commands: list[str], case_dir: Path, on_log: Callable[[str], None]) -> None:
        mount_dir = str(case_dir.resolve())
        for command in commands:
            inner = (
                f"set -o pipefail; "
                f"if [ -f '{self.settings.openfoam_bashrc}' ]; then source '{self.settings.openfoam_bashrc}'; fi; "
                f"cd /case && {command}"
            )
            docker_cmd = ["docker", "run", "--rm", "-v", f"{mount_dir}:/case", self.settings.image, "bash", "-lc", inner]
            stream_process(docker_cmd, on_log, command)


def select_execution_backend(backend_name: str, payload: dict[str, Any]) -> ExecutionBackend:
    """Build WSL2, Native Linux, or Docker OpenFOAM execution backend from UI settings."""
    mode = backend_name.strip().lower()
    raw_root = str(payload.get("case_root", "")).strip()
    case_root = Path(raw_root).expanduser() if raw_root else Path.home() / "rocketcfd-openfoam-cases"
    bashrc = str(payload.get("openfoam_bashrc", "")).strip()
    if mode == "wsl":
        if os.name != "nt":
            raise RuntimeError("WSL2 backend is only available on Windows hosts.")
        distro = str(payload.get("wsl_distro", "")).strip()
        return WslExecutionBackend(WslSettings(distro=distro, openfoam_bashrc=bashrc, case_root=case_root))
    if mode == "native_linux":
        if os.name == "nt":
            raise RuntimeError("Native Linux backend requires a Linux host; use WSL2 or Docker on Windows.")
        return NativeLinuxExecutionBackend(NativeLinuxSettings(openfoam_bashrc=bashrc, case_root=case_root))
    if mode == "docker":
        image = str(payload.get("docker_image", "microfluidica/openfoam:2412")).strip() or "microfluidica/openfoam:2412"
        return DockerExecutionBackend(DockerSettings(image=image, case_root=case_root))
    raise ValueError(f"Unsupported execution backend '{backend_name}'.")


def _encode_results_csv(cases: list[OpenFoamCaseResult]) -> str:
    """Serialize solved OpenFOAM cases to CSV text."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(RESULT_HEADERS)
    for row in format_case_table_rows(cases):
        writer.writerow(row)
    return buf.getvalue()


def _render_residuals_plot(residuals: dict[str, tuple[np.ndarray, np.ndarray]]) -> str:
    """Render semilog residual convergence chart as a PNG base64 data URI."""
    if not residuals:
        return ""
    fig, axis_res = plt.subplots(figsize=(9.5, 3.8), facecolor="#0f172a")
    axis_res.set_facecolor("#0f172a")
    axis_res.tick_params(colors="#cbd5e1", labelsize=9)
    for spine in axis_res.spines.values():
        spine.set_color("#334155")
    for field_name, (times, vals) in sorted(residuals.items()):
        positive = vals[vals > 0.0]
        if len(positive) == 0:
            continue
        valid_mask = vals > 0.0
        axis_res.semilogy(times[valid_mask], vals[valid_mask], linewidth=1.6, label=field_name)
    axis_res.set_title("OpenFOAM Residual Convergence History", color="#f8fafc", fontsize=11, pad=8)
    axis_res.set_xlabel("Iteration / Time", color="#94a3b8", fontsize=9)
    axis_res.set_ylabel("Initial Residual (log scale)", color="#94a3b8", fontsize=9)
    axis_res.grid(True, which="both", color="#1e293b", linestyle="--", linewidth=0.7)
    axis_res.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#f8fafc")
    fig.tight_layout(pad=1.2)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def _latest_residuals_from_dirs(run_dirs: list[Path]) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], str]:
    """Read solver log residual curves from the most recent solved directory."""
    for run_dir in reversed(run_dirs):
        for log_file in sorted(run_dir.glob("log.*")):
            if log_file.name == "log.checkMesh":
                continue
            hist = parse_residual_history(log_file)
            if hist:
                return hist, _render_residuals_plot(hist)
    return {}, ""


def _serialize_table_dicts(cases: list[OpenFoamCaseResult]) -> list[dict[str, Any]]:
    """Build JSON-friendly dicts matching RESULT_HEADERS."""
    rows = []
    for raw_row in format_case_table_rows(cases):
        rows.append(dict(zip(RESULT_HEADERS, raw_row, strict=True)))
    return rows


class JobManager:
    """Manages asynchronous OpenFOAM parameter sweeps and validation suite jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def start_sweep(self, payload: dict[str, Any], panel_mesh: PanelMesh) -> dict[str, Any]:
        """Start an asynchronous OpenFOAM aerodynamic sweep over velocity and angle of attack."""
        try:
            backend_name = str(payload.get("backend", "wsl" if os.name == "nt" else "native_linux"))
            execution = select_execution_backend(backend_name, payload)
            altitude_m = max(0.0, float(payload.get("altitude_m", 1500.0)))
            atmo = us_standard_atmosphere(altitude_m)
            base_cond = FlowCondition(
                name="sweep_base",
                velocity=float(payload.get("velocity_mps", 420.0)),
                alpha_deg=float(payload.get("alpha_deg", 2.5)),
                beta_deg=0.0,
                density=atmo.density,
                temperature=atmo.temperature,
            )
            vel_vals = parse_values(str(payload.get("sweep_velocities", str(payload.get("velocity_mps", 420.0)))))
            alpha_vals = parse_values(str(payload.get("sweep_alphas", str(payload.get("alpha_deg", 2.5)))))
            conditions = build_conditions(base_cond, [SweepAxis("velocity", vel_vals), SweepAxis("alpha_deg", alpha_vals)])
            mesh_cfg = mesh_settings_for_preset(str(payload.get("mesh_preset", "Medium")))
            turb_model = str(payload.get("turbulence_model", "kOmegaSST"))
            n_procs = max(1, int(payload.get("cores", 4)))
            max_iters = max(50, int(payload.get("max_iterations", 500)))
            solver_cfg = SolverSettings(turbulence_model=turb_model, n_processors=n_procs, max_iterations=max_iters)
        except (ValueError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}

        job_id = uuid.uuid4().hex[:10]
        cancel_ev = threading.Event()
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "kind": "sweep",
                "status": "running",
                "progress": 0,
                "total": len(conditions),
                "message": f"Starting {len(conditions)}-case OpenFOAM sweep...",
                "logs": [],
                "runDirs": [],
                "results": [],
                "rows": [],
                "csv": "",
                "residualsPlot": "",
                "validationRows": [],
                "cancelEvent": cancel_ev,
            }

        def _worker() -> None:
            def _on_log(line: str) -> None:
                if cancel_ev.is_set():
                    raise RuntimeError("OpenFOAM sweep cancelled by user.")
                with self._lock:
                    logs = self._jobs[job_id]["logs"]
                    logs.append(line)
                    if len(logs) > 250:
                        del logs[:50]

            def _on_progress(done: int, total: int) -> None:
                with self._lock:
                    self._jobs[job_id]["progress"] = done
                    self._jobs[job_id]["total"] = total

            def _on_started(label: str, run_dir: Path, app_name: str) -> None:
                with self._lock:
                    self._jobs[job_id]["runDirs"].append(run_dir)
                    self._jobs[job_id]["message"] = f"Solving {label} ({app_name})..."

            def _on_result(case_res: OpenFoamCaseResult) -> None:
                with self._lock:
                    res_list = self._jobs[job_id]["results"]
                    res_list.append(case_res)
                    self._jobs[job_id]["rows"] = _serialize_table_dicts(res_list)
                    self._jobs[job_id]["csv"] = _encode_results_csv(res_list)
                    _hist, plot_uri = _latest_residuals_from_dirs(self._jobs[job_id]["runDirs"])
                    if plot_uri:
                        self._jobs[job_id]["residualsPlot"] = plot_uri

            try:
                cases = run_openfoam_sweep(
                    panel_mesh=panel_mesh,
                    conditions=conditions,
                    moment_ref=np.zeros(3),
                    ground_plane=None,
                    mesh_settings=mesh_cfg,
                    solver_settings=solver_cfg,
                    execution=execution,
                    reference_area=None,
                    reference_length=None,
                    on_log=_on_log,
                    on_progress=_on_progress,
                    model_name=str(payload.get("model_name", "rocket")),
                    on_case_result=_on_result,
                    on_case_started=_on_started,
                )
                with self._lock:
                    self._jobs[job_id]["status"] = "completed"
                    self._jobs[job_id]["rows"] = _serialize_table_dicts(cases)
                    self._jobs[job_id]["csv"] = _encode_results_csv(cases)
                    _hist, plot_uri = _latest_residuals_from_dirs(self._jobs[job_id]["runDirs"])
                    if plot_uri:
                        self._jobs[job_id]["residualsPlot"] = plot_uri
                    self._jobs[job_id]["message"] = f"Completed {len(cases)} OpenFOAM case(s)."
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id]["status"] = "cancelled" if cancel_ev.is_set() else "failed"
                    self._jobs[job_id]["message"] = str(exc)

        threading.Thread(target=_worker, daemon=True).start()
        return {"ok": True, "jobId": job_id, "message": f"Queued OpenFOAM sweep ({len(conditions)} case(s))."}

    def start_validation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute benchmark validation cases against OpenFOAM in background thread."""
        try:
            backend_name = str(payload.get("backend", "wsl" if os.name == "nt" else "native_linux"))
            execution = select_execution_backend(backend_name, payload)
            suite_mode = str(payload.get("suite", "default")).strip().lower()
            cases = full_canonical_validation_suite() if suite_mode == "full" else default_validation_suite()
            mesh_cfg = mesh_settings_for_preset(str(payload.get("mesh_preset", "Coarse")))
            solver_cfg = SolverSettings(
                turbulence_model=str(payload.get("turbulence_model", "kOmegaSST")),
                n_processors=max(1, int(payload.get("cores", 4))),
                max_iterations=max(100, int(payload.get("max_iterations", 400))),
            )
        except (ValueError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}

        job_id = uuid.uuid4().hex[:10]
        cancel_ev = threading.Event()
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "kind": "validation",
                "status": "running",
                "progress": 0,
                "total": len(cases),
                "message": f"Running {len(cases)} canonical OpenFOAM validation cases...",
                "logs": [],
                "runDirs": [],
                "results": [],
                "rows": [],
                "csv": "",
                "residualsPlot": "",
                "validationRows": [],
                "cancelEvent": cancel_ev,
            }

        def _worker() -> None:
            def _on_log(line: str) -> None:
                if cancel_ev.is_set():
                    raise RuntimeError("Validation run cancelled by user.")
                with self._lock:
                    logs = self._jobs[job_id]["logs"]
                    logs.append(line)
                    if len(logs) > 250:
                        del logs[:50]

            try:
                val_results = run_validation_suite(cases, execution, mesh_cfg, solver_cfg, _on_log)
                val_rows = [
                    {
                        "caseName": res_item.case_name,
                        "computedValue": round(res_item.computed_value, 5),
                        "referenceValue": round(res_item.reference_value, 5),
                        "deltaPct": round(res_item.delta_pct, 2),
                        "passed": bool(res_item.passed),
                    }
                    for res_item in val_results
                ]
                passed_cnt = sum(1 for row in val_rows if row["passed"])
                with self._lock:
                    self._jobs[job_id]["status"] = "completed"
                    self._jobs[job_id]["progress"] = len(val_rows)
                    self._jobs[job_id]["validationRows"] = val_rows
                    self._jobs[job_id]["message"] = f"Validation finished: {passed_cnt}/{len(val_rows)} benchmarks passed."
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id]["status"] = "cancelled" if cancel_ev.is_set() else "failed"
                    self._jobs[job_id]["message"] = str(exc)

        threading.Thread(target=_worker, daemon=True).start()
        return {"ok": True, "jobId": job_id, "message": "Queued OpenFOAM validation suite."}

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Request cancellation of a running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {"ok": False, "error": f"Unknown job id '{job_id}'."}
            job["cancelEvent"].set()
            job["message"] = "Cancellation requested..."
        return {"ok": True, "message": "Cancellation requested."}

    def poll_job(self, job_id: str) -> dict[str, Any]:
        """Return current job progress, latest residuals plot, logs, and results."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {"ok": False, "error": f"Unknown job id '{job_id}'."}
            snapshot = {
                "id": job["id"],
                "kind": job["kind"],
                "status": job["status"],
                "progress": job["progress"],
                "total": job["total"],
                "message": job["message"],
                "logs": list(job["logs"][-80:]),
                "rows": list(job["rows"]),
                "csv": job["csv"],
                "residualsPlot": job["residualsPlot"],
                "validationRows": list(job["validationRows"]),
            }
            if job["status"] == "running" and job["runDirs"] and not snapshot["residualsPlot"]:
                _hist, plot_uri = _latest_residuals_from_dirs(job["runDirs"])
                snapshot["residualsPlot"] = plot_uri
        return {"ok": True, "job": snapshot}


def import_existing_results_payload(directory_str: str) -> dict[str, Any]:
    """Import completed OpenFOAM case results, residuals, and CSV from a folder."""
    raw_dir = directory_str.strip()
    if not raw_dir:
        return {"ok": False, "error": "Enter a directory path containing solved OpenFOAM cases."}
    target_path = Path(raw_dir).expanduser()
    if not target_path.exists():
        return {"ok": False, "error": f"Case directory not found: {target_path}"}

    roots = find_case_roots(target_path)
    if not roots:
        return {"ok": False, "error": f"No solved OpenFOAM postProcessing/forces1 directories found under {target_path}"}

    all_cases: list[OpenFoamCaseResult] = []
    run_dirs: list[Path] = []
    for root_dir in roots:
        cases = import_case_results(root_dir)
        all_cases.extend(cases)
        run_dirs.extend(case.case_dir for case in cases)

    _hist, plot_uri = _latest_residuals_from_dirs(run_dirs)
    return {
        "ok": True,
        "message": f"Imported {len(all_cases)} solved OpenFOAM case(s) from {target_path}.",
        "rows": _serialize_table_dicts(all_cases),
        "csv": _encode_results_csv(all_cases),
        "residualsPlot": plot_uri,
    }
