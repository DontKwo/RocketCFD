"""Loopback WebView Studio API, 3D mesh, CAD import, OpenFOAM runner, and self-test suite."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

import trimesh
import pytest

from rocketcfd import main as app_main
from rocketcfd.flow import FlowCondition
from rocketcfd.gui.openfoam_results import RESULT_HEADERS, format_case_table_rows
from rocketcfd.gui.web_app import capture_screenshot, find_chromium_browser, start_server
from rocketcfd.openfoam.case_result import OpenFoamCaseResult
from rocketcfd.openfoam.coefficients import Coefficients


def test_self_test_entrypoint_succeeds(capsys: object) -> None:
    """Ensure the public --self-test entrypoint boots and probes cleanly."""
    exit_code = app_main(["--self-test"])
    assert exit_code == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "SELF_TEST_OK" in captured.out


def test_format_case_table_rows_aligns_with_headers(tmp_path: Path) -> None:
    """Verify table formatting produces one cell per declared header column."""
    sample = OpenFoamCaseResult(
        condition=FlowCondition(name="mach_1_5", velocity=510.0),
        application="rhoCentralFoam",
        coefficients=Coefficients(cd=0.42, cl=0.11, cs=0.0, cm=(0.0, 0.02, 0.0)),
        force=(120.0, 0.0, 31.0),
        moment=(0.0, 5.5, 0.0),
        case_dir=tmp_path,
        reference_area=0.0177,
        reference_length=2.0,
    )
    rows = format_case_table_rows([sample])
    assert len(rows) == 1
    assert len(rows[0]) == len(RESULT_HEADERS)
    assert rows[0][0] == "mach_1_5"
    assert rows[0][1] == "rhoCentralFoam"


def test_webview_http_endpoints_end_to_end(tmp_path: Path) -> None:
    """Exercise defaults, 3D mesh, CAD import, solver, sweep job lifecycle, TACC, and screenshot."""
    server, port = start_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/", timeout=5) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "RocketCFD Studio" in html

        with urllib.request.urlopen(f"{base}/vendor/three.module.min.js", timeout=5) as resp:
            assert resp.status == 200
            assert len(resp.read()) > 10000

        with urllib.request.urlopen(f"{base}/api/defaults", timeout=5) as resp:
            defaults = json.loads(resp.read().decode("utf-8"))
            assert defaults["ok"] is True
            assert len(defaults["noseconeShapes"]) >= 3
            assert len(defaults["meshPresets"]) == 3

        def _post(path: str, payload: dict[str, object]) -> dict[str, object]:
            req = urllib.request.Request(
                f"{base}{path}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))

        geom = _post("/api/geometry", {"nosecone_shape": "von_karman", "fin_count": 4})
        assert geom["ok"] is True
        assert str(geom["previewImage"]).startswith("data:image/png;base64,")
        mesh3d = geom["mesh3d"]
        assert isinstance(mesh3d, dict)
        assert len(mesh3d["positions"]) > 0
        assert len(mesh3d["cpScalars"]) == mesh3d["vertexCount"]

        # Exercise STL upload + unit scaling + Euler rotation
        cone = trimesh.creation.cone(radius=0.08, height=0.9)
        stl_bytes = cone.export(file_type="stl")
        assert isinstance(stl_bytes, (bytes, bytearray))
        cad_res = _post(
            "/api/import_cad",
            {
                "fileName": "test_rocket.stl",
                "fileBase64": base64.b64encode(stl_bytes).decode("ascii"),
                "unit": "m",
                "scale": 1.2,
                "rot_x": 0.0,
                "rot_y": 90.0,
                "rot_z": 0.0,
            },
        )
        assert cad_res["ok"] is True
        assert cad_res["mesh3d"]["faceCount"] > 0

        cond = _post("/api/condition", {"altitude_m": 2500.0, "velocity_mps": 450.0, "mesh_preset": "Medium"})
        assert cond["ok"] is True
        assert cond["condition"]["solver"] == "rhoCentralFoam"

        validation_res = _post("/api/validation", {"mach": 2.0, "reynolds": 2.0e6})
        assert validation_res["ok"] is True
        assert len(validation_res["rows"]) == 6

        exported = _post("/api/export_case", {"altitude_m": 1000.0, "velocity_mps": 380.0})
        assert exported["ok"] is True
        assert "system/snappyHexMeshDict" in exported["files"]
        assert "constant/triSurface/body.stl" in exported["files"]

        tacc_res = _post("/api/tacc/script", {"host": "ls6.tacc.utexas.edu", "allocation": "TG-TEST"})
        assert tacc_res["ok"] is True
        assert "#SBATCH -A TG-TEST" in str(tacc_res["script"])

        # Start async sweep job and poll status cleanly even without local OpenFOAM installed
        sweep_res = _post(
            "/api/sweep/start",
            {"backend": "wsl", "sweep_velocities": "420", "sweep_alphas": "0", "case_root": str(tmp_path / "cases")},
        )
        assert sweep_res["ok"] is True
        job_id = str(sweep_res["jobId"])
        time.sleep(0.2)
        with urllib.request.urlopen(f"{base}/api/jobs/{job_id}", timeout=5) as poll_resp:
            job_data = json.loads(poll_resp.read().decode("utf-8"))
            assert job_data["ok"] is True
            assert job_data["job"]["id"] == job_id

        bad_req = urllib.request.Request(
            f"{base}/api/geometry",
            data=json.dumps({"nosecone_shape": "invalid_shape"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(bad_req, timeout=5)
            raise AssertionError("Expected HTTP 400 on invalid nosecone_shape")
        except urllib.error.HTTPError as err:
            assert err.code == 400

        shot_out = tmp_path / "shot.png"
        if find_chromium_browser():
            capture_screenshot(f"{base}/", shot_out)
            assert shot_out.is_file() and shot_out.stat().st_size > 1000
        else:
            with pytest.raises(RuntimeError, match="No Chromium"):
                capture_screenshot(f"{base}/", shot_out)
    finally:
        server.shutdown()
        server.server_close()
