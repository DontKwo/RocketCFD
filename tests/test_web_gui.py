"""Loopback WebView Studio API, geometry preview, solver evaluation, and self-test suite."""
from __future__ import annotations

import json
from pathlib import Path
import threading
import urllib.error
import urllib.request

from rocketcfd import main as app_main
from rocketcfd.flow import FlowCondition
from rocketcfd.gui.openfoam_results import RESULT_HEADERS, format_case_table_rows
from rocketcfd.gui.web_app import start_server
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


def test_webview_http_endpoints_end_to_end() -> None:
    """Exercise GET /, GET /api/defaults, and POST geometry/condition/validation/export routes."""
    server, port = start_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/", timeout=5) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "RocketCFD Studio" in html

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
    finally:
        server.shutdown()
        server.server_close()
