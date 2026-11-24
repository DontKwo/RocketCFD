import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const state = {
  images: {},
  mesh3d: null,
  activeTab: "viewport3d",
  resultsCsv: "",
  currentJobId: null,
  pollTimer: null,
  geometrySource: "parametric",
  viewer: {
    renderer: null,
    scene: null,
    camera: null,
    controls: null,
    meshObj: null,
    wireObj: null,
    resizeBound: false
  }
};

function setStatus(message) {
  const banner = document.getElementById("status.banner");
  if (banner) banner.textContent = message;
}

function setRunnerLog(text) {
  const box = document.getElementById("runner.log_box");
  if (box) box.textContent = text || "Ready.";
}

window.addEventListener("error", function (event) {
  setStatus("Unexpected interface error: " + (event.message || "Unknown failure"));
});

window.addEventListener("unhandledrejection", function (event) {
  setStatus("Request did not finish cleanly: " + (event.reason ? String(event.reason) : "Unknown error"));
});

async function apiGet(url) {
  const resp = await fetch(url, { cache: "no-store" });
  const data = await resp.json();
  if (!resp.ok && data && data.error) throw new Error(data.error);
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return data;
}

async function apiPost(url, payload) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {})
  });
  const data = await resp.json();
  if (!resp.ok && data && data.error) throw new Error(data.error);
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return data;
}

function scalarColor(normVal) {
  const clamped = Math.max(0, Math.min(1, normVal));
  const color = new THREE.Color();
  if (clamped < 0.5) {
    color.setRGB(0.15 + clamped * 0.7, 0.45 + clamped * 0.9, 0.96 - clamped * 0.4);
  } else {
    const upper = (clamped - 0.5) * 2;
    color.setRGB(0.5 + upper * 0.48, 0.9 - upper * 0.65, 0.76 - upper * 0.68);
  }
  return color;
}

function ensureThreeViewport(host) {
  if (state.viewer.renderer) return true;
  const width = Math.max(host.clientWidth || 900, 320);
  const height = Math.max(host.clientHeight || 410, 260);
  try {
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    host.textContent = "";
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1222);

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.01, 200);
    camera.position.set(2.4, 1.35, 1.1);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    const hemiLight = new THREE.HemisphereLight(0xe2e8f0, 0x1e293b, 1.15);
    scene.add(hemiLight);
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.3);
    keyLight.position.set(4, 6, 5);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.55);
    fillLight.position.set(-4, -3, -2);
    scene.add(fillLight);

    const axes = new THREE.AxesHelper(0.45);
    axes.position.set(-0.25, -0.35, -0.35);
    scene.add(axes);

    const grid = new THREE.GridHelper(4.0, 20, 0x334155, 0x1e293b);
    grid.position.y = -0.35;
    scene.add(grid);

    state.viewer.renderer = renderer;
    state.viewer.scene = scene;
    state.viewer.camera = camera;
    state.viewer.controls = controls;

    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    if (!state.viewer.resizeBound) {
      state.viewer.resizeBound = true;
      window.addEventListener("resize", function () {
        if (!state.viewer.renderer || !host.clientWidth) return;
        const nextW = Math.max(host.clientWidth, 320);
        const nextH = Math.max(host.clientHeight, 260);
        state.viewer.camera.aspect = nextW / nextH;
        state.viewer.camera.updateProjectionMatrix();
        state.viewer.renderer.setSize(nextW, nextH);
      });
    }
    return true;
  } catch (err) {
    return false;
  }
}

function renderCanvas2DFallback(host, meshData) {
  host.textContent = "";
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(host.clientWidth || 900, 640);
  canvas.height = 410;
  host.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx || !meshData) return;
  ctx.fillStyle = "#0b1222";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const pos = meshData.positions || [];
  const idx = meshData.indices || [];
  const bounds = meshData.bounds || [0, 2, -0.2, 0.2, -0.2, 0.2];
  const spanX = Math.max(bounds[1] - bounds[0], 0.1);
  const spanZ = Math.max(bounds[5] - bounds[4], 0.1);
  const scale = Math.min((canvas.width * 0.76) / spanX, (canvas.height * 0.65) / spanZ);
  const offsetX = canvas.width * 0.12 - bounds[0] * scale;
  const offsetY = canvas.height * 0.52;

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  for (let triIdx = 0; triIdx + 2 < idx.length; triIdx += 3) {
    const a = idx[triIdx] * 3;
    const b = idx[triIdx + 1] * 3;
    const c = idx[triIdx + 2] * 3;
    const ax = offsetX + pos[a] * scale - pos[a + 1] * scale * 0.22;
    const ay = offsetY - pos[a + 2] * scale + pos[a + 1] * scale * 0.18;
    const bx = offsetX + pos[b] * scale - pos[b + 1] * scale * 0.22;
    const by = offsetY - pos[b + 2] * scale + pos[b + 1] * scale * 0.18;
    const cx = offsetX + pos[c] * scale - pos[c + 1] * scale * 0.22;
    const cy = offsetY - pos[c + 2] * scale + pos[c + 1] * scale * 0.18;
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.lineTo(ax, ay);
  }
  ctx.stroke();
}

function resetCameraToMesh(meshData) {
  if (!meshData || !state.viewer.camera || !state.viewer.controls) return;
  const bounds = meshData.bounds || [0, 2, -0.2, 0.2, -0.2, 0.2];
  const centerX = (bounds[0] + bounds[1]) * 0.5;
  const centerY = (bounds[2] + bounds[3]) * 0.5;
  const centerZ = (bounds[4] + bounds[5]) * 0.5;
  const diag = Math.max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 0.5);
  state.viewer.controls.target.set(centerX, centerY, centerZ);
  state.viewer.camera.position.set(centerX + diag * 0.55, centerY + diag * 0.42, centerZ + diag * 0.78);
  state.viewer.camera.updateProjectionMatrix();
  state.viewer.controls.update();
}

function update3DViewport() {
  const host = document.getElementById("viewport3d.host");
  const meshData = state.mesh3d;
  if (!host || !meshData) return;

  if (!ensureThreeViewport(host)) {
    renderCanvas2DFallback(host, meshData);
    return;
  }
  const rectW = Math.max(host.clientWidth || 720, 320);
  const rectH = Math.max(host.clientHeight || 465, 260);
  if (state.viewer.renderer && state.viewer.camera) {
    state.viewer.camera.aspect = rectW / rectH;
    state.viewer.camera.updateProjectionMatrix();
    state.viewer.renderer.setSize(rectW, rectH);
  }

  const scene = state.viewer.scene;
  if (state.viewer.meshObj) {
    scene.remove(state.viewer.meshObj);
    state.viewer.meshObj.geometry.dispose();
    state.viewer.meshObj.material.dispose();
  }
  if (state.viewer.wireObj) {
    scene.remove(state.viewer.wireObj);
    state.viewer.wireObj.geometry.dispose();
    state.viewer.wireObj.material.dispose();
  }

  const mode = document.getElementById("viewport.mode_select").value || "cp";
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(meshData.positions);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(meshData.indices);
  geometry.computeVertexNormals();

  if (mode === "cp" || mode === "axial") {
    const rawScalars = mode === "cp" ? meshData.cpScalars : meshData.axialScalars;
    const minVal = mode === "cp" ? 0.0 : 0.0;
    const maxVal = mode === "cp" ? 1.4 : 1.0;
    const colors = new Float32Array(positions.length);
    for (let idx = 0; idx < rawScalars.length; idx++) {
      const col = scalarColor((rawScalars[idx] - minVal) / Math.max(maxVal - minVal, 1e-6));
      colors[idx * 3] = col.r;
      colors[idx * 3 + 1] = col.g;
      colors[idx * 3 + 2] = col.b;
    }
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  }

  const material = new THREE.MeshStandardMaterial({
    color: (mode === "cp" || mode === "axial") ? 0xffffff : 0x38bdf8,
    vertexColors: mode === "cp" || mode === "axial",
    roughness: 0.38,
    metalness: 0.18,
    wireframe: mode === "wireframe",
    side: THREE.DoubleSide
  });

  const mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);
  state.viewer.meshObj = mesh;

  const wireMat = new THREE.MeshBasicMaterial({
    color: 0x0f172a,
    wireframe: true,
    transparent: true,
    opacity: mode === "wireframe" ? 0.0 : 0.22
  });
  const wireMesh = new THREE.Mesh(geometry, wireMat);
  scene.add(wireMesh);
  state.viewer.wireObj = wireMesh;

  resetCameraToMesh(meshData);
  state.viewer.renderer.render(scene, state.viewer.camera);
}

function currentPayload() {
  return {
    geometry_source: state.geometrySource,
    nosecone_shape: document.getElementById("rocket.nosecone_shape").value,
    nosecone_length: Number(document.getElementById("rocket.nosecone_length").value || 0.45),
    body_length: Number(document.getElementById("rocket.body_length").value || 1.55),
    diameter: Number(document.getElementById("rocket.diameter").value || 0.15),
    fin_count: Number(document.getElementById("rocket.fin_count").value || 4),
    fin_span: Number(document.getElementById("rocket.fin_span").value || 0.14),
    altitude_m: Number(document.getElementById("flow.altitude_input").value || 0),
    velocity_mps: Number(document.getElementById("flow.velocity_input").value || 420),
    alpha_deg: Number(document.getElementById("flow.alpha_input").value || 0),
    mesh_preset: document.getElementById("flow.mesh_preset").value || "Medium",
    backend: document.getElementById("runner.backend_select").value || "wsl",
    cores: Number(document.getElementById("runner.cores_input").value || 4),
    sweep_velocities: document.getElementById("runner.sweep_velocities").value || "420",
    sweep_alphas: document.getElementById("runner.sweep_alphas").value || "2.5"
  };
}

function showTab(tabKey) {
  state.activeTab = tabKey;
  const tabMap = {
    viewport3d: "tabs.viewport3d_btn",
    geometry: "tabs.geometry_btn",
    solver: "tabs.solver_btn",
    results: "tabs.results_btn",
    validation: "tabs.validation_btn"
  };
  Object.keys(tabMap).forEach(function (key) {
    const btn = document.querySelector('[data-testid="' + tabMap[key] + '"]');
    if (btn) btn.classList.toggle("active", key === tabKey);
  });

  document.getElementById("panel.viewport3d").hidden = tabKey !== "viewport3d";
  document.getElementById("panel.imageView").hidden = !(tabKey === "geometry" || tabKey === "solver");
  document.getElementById("panel.resultsView").hidden = tabKey !== "results";
  document.getElementById("panel.validationView").hidden = tabKey !== "validation";

  if (tabKey === "viewport3d") {
    update3DViewport();
  } else if (tabKey === "geometry" || tabKey === "solver") {
    const img = document.getElementById("preview.image");
    const empty = document.getElementById("preview.empty");
    const src = state.images[tabKey];
    if (src) {
      img.src = src;
      img.hidden = false;
      empty.hidden = true;
    } else {
      img.hidden = true;
      empty.hidden = false;
    }
  }
}

function renderValidationTable(rows) {
  const host = document.getElementById("table.validation_host");
  if (!host) return;
  host.textContent = "";
  const table = document.createElement("table");
  table.innerHTML = "<thead><tr><th>Benchmark</th><th>Metric</th><th>Reference Value</th></tr></thead><tbody></tbody>";
  const tbody = table.querySelector("tbody");
  (rows || []).forEach(function (item) {
    const tr = document.createElement("tr");
    [item.benchmark, item.metric, item.referenceValue].forEach(function (cellVal) {
      const td = document.createElement("td");
      td.textContent = String(cellVal);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  host.appendChild(table);
}

function renderSweepResults(rows, csvText, residualsPlot) {
  if (csvText) state.resultsCsv = csvText;
  const resImg = document.getElementById("residuals.image");
  const resEmpty = document.getElementById("residuals.empty");
  if (residualsPlot) {
    resImg.src = residualsPlot;
    resImg.hidden = false;
    resEmpty.hidden = true;
  } else {
    resImg.hidden = true;
    resEmpty.hidden = false;
  }

  const host = document.getElementById("results.table_host");
  host.textContent = "";
  if (!rows || rows.length === 0) {
    host.innerHTML = "<p class='muted'>No solved aerodynamic coefficient rows yet.</p>";
    return;
  }
  const cols = Object.keys(rows[0]);
  const table = document.createElement("table");
  const headHtml = cols.map(function (col) { return "<th>" + col + "</th>"; }).join("");
  table.innerHTML = "<thead><tr>" + headHtml + "</tr></thead><tbody></tbody>";
  const tbody = table.querySelector("tbody");
  rows.forEach(function (row) {
    const tr = document.createElement("tr");
    cols.forEach(function (col) {
      const td = document.createElement("td");
      td.textContent = String(row[col]);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  host.appendChild(table);
}

function renderLiveValidationRows(rows) {
  const host = document.getElementById("validation.live_host");
  host.textContent = "";
  if (!rows || rows.length === 0) return;
  const table = document.createElement("table");
  table.innerHTML = "<thead><tr><th>Benchmark Case</th><th>Computed</th><th>Reference</th><th>Delta %</th><th>Status</th></tr></thead><tbody></tbody>";
  const tbody = table.querySelector("tbody");
  rows.forEach(function (item) {
    const tr = document.createElement("tr");
    [item.caseName, item.computedValue, item.referenceValue, item.deltaPct + "%", item.passed ? "PASS" : "CHECK"].forEach(function (val) {
      const td = document.createElement("td");
      td.textContent = String(val);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  host.appendChild(table);
}

async function buildGeometry() {
  state.geometrySource = "parametric";
  setStatus("Assembling parametric rocket panel mesh...");
  const res = await apiPost("/api/geometry", currentPayload());
  if (!res.ok) {
    setStatus(res.error || "Geometry build failed.");
    return;
  }
  state.images.geometry = res.previewImage;
  state.mesh3d = res.mesh3d;
  document.getElementById("kpi.panels").textContent = String(res.metrics.panelCount);
  if (state.activeTab === "viewport3d") {
    update3DViewport();
  } else {
    showTab(state.activeTab);
  }
  setStatus(res.message);
}

async function applyCadImport() {
  const fileEl = document.getElementById("cad.file_input");
  const file = fileEl && fileEl.files ? fileEl.files[0] : null;
  if (!file) {
    setStatus("Select an STL, OBJ, or STEP file to import.");
    return;
  }
  setStatus("Importing and transforming " + file.name + "...");
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binaryStr = "";
  for (let idx = 0; idx < bytes.length; idx++) {
    binaryStr += String.fromCharCode(bytes[idx]);
  }
  const b64 = btoa(binaryStr);
  const res = await apiPost("/api/import_cad", {
    fileName: file.name,
    fileBase64: b64,
    unit: document.getElementById("cad.unit_select").value,
    scale: Number(document.getElementById("cad.scale_input").value || 1.0),
    rot_x: Number(document.getElementById("cad.rot_x_input").value || 0),
    rot_y: Number(document.getElementById("cad.rot_y_input").value || 0),
    rot_z: Number(document.getElementById("cad.rot_z_input").value || 0)
  });
  state.geometrySource = "cad";
  state.images.geometry = res.previewImage;
  state.mesh3d = res.mesh3d;
  document.getElementById("kpi.panels").textContent = String(res.metrics.panelCount);
  showTab("viewport3d");
  setStatus(res.message);
}

async function evaluateCondition() {
  setStatus("Evaluating US Standard Atmosphere and OpenFOAM solver regime...");
  const res = await apiPost("/api/condition", currentPayload());
  const cond = res.condition;
  document.getElementById("kpi.mach").textContent = String(cond.mach);
  document.getElementById("kpi.solver").textContent = String(cond.solver);
  document.getElementById("kpi.pressure").textContent = cond.dynamicPressurePa.toLocaleString() + " Pa";
  state.images.solver = res.solverPlotImage;
  if (state.activeTab === "solver") showTab("solver");
  setStatus(res.message);
}

async function exportCase() {
  setStatus("Generating OpenFOAM blockMeshDict, snappyHexMeshDict, and STL files...");
  const res = await apiPost("/api/export_case", currentPayload());
  const host = document.getElementById("files.case_host");
  if (host) {
    host.textContent = "";
    const table = document.createElement("table");
    table.innerHTML = "<thead><tr><th>Generated Case File</th></tr></thead><tbody></tbody>";
    const tbody = table.querySelector("tbody");
    (res.files || []).forEach(function (rel) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.textContent = res.caseDirName + "/" + rel;
      tr.appendChild(td);
      tbody.appendChild(tr);
    });
    host.appendChild(table);
  }
  setStatus(res.message);
}

async function pollActiveJob() {
  if (!state.currentJobId) return;
  const res = await apiGet("/api/jobs/" + encodeURIComponent(state.currentJobId));
  const job = res.job;
  if (!job) return;
  setStatus(job.message);
  if (job.logs && job.logs.length > 0) setRunnerLog(job.logs.join("\n"));
  if (job.kind === "sweep") {
    renderSweepResults(job.rows, job.csv, job.residualsPlot);
  } else if (job.kind === "validation" && job.validationRows.length > 0) {
    renderLiveValidationRows(job.validationRows);
  }
  if (job.status === "running") {
    state.pollTimer = setTimeout(pollActiveJob, 800);
  } else {
    state.pollTimer = null;
  }
}

async function startSweepJob() {
  if (state.pollTimer) clearTimeout(state.pollTimer);
  setStatus("Starting OpenFOAM aerodynamic sweep...");
  const res = await apiPost("/api/sweep/start", currentPayload());
  state.currentJobId = res.jobId;
  setStatus(res.message);
  showTab("results");
  state.pollTimer = setTimeout(pollActiveJob, 600);
}

async function cancelActiveJob() {
  if (!state.currentJobId) {
    setStatus("No active OpenFOAM job running.");
    return;
  }
  const res = await apiPost("/api/jobs/" + encodeURIComponent(state.currentJobId) + "/cancel", {});
  setStatus(res.message || "Cancellation sent.");
}

async function importResultsFolder() {
  const dirStr = document.getElementById("results.import_path_input").value.trim();
  const res = await apiPost("/api/results/import", { directory: dirStr });
  renderSweepResults(res.rows || [], res.csv || "", res.residualsPlot || "");
  setStatus(res.message);
}

async function runLiveValidation() {
  if (state.pollTimer) clearTimeout(state.pollTimer);
  setStatus("Starting live OpenFOAM canonical validation suite...");
  const res = await apiPost("/api/validation/run", currentPayload());
  state.currentJobId = res.jobId;
  setStatus(res.message);
  state.pollTimer = setTimeout(pollActiveJob, 600);
}

async function generateTaccScript() {
  const res = await apiPost("/api/tacc/script", {
    host: document.getElementById("tacc.host_input").value,
    allocation: document.getElementById("tacc.allocation_input").value,
    application: document.getElementById("kpi.solver").textContent || "rhoCentralFoam"
  });
  const box = document.getElementById("tacc.script_box");
  box.textContent = res.script || "";
  box.hidden = false;
  setStatus(res.message);
}

async function initializeStudio() {
  const defaults = await apiGet("/api/defaults");
  const shapeSel = document.getElementById("rocket.nosecone_shape");
  shapeSel.textContent = "";
  (defaults.noseconeShapes || []).forEach(function (shape) {
    const opt = document.createElement("option");
    opt.value = shape.id;
    opt.textContent = shape.label;
    shapeSel.appendChild(opt);
  });
  shapeSel.value = "ogive";

  const presetSel = document.getElementById("flow.mesh_preset");
  presetSel.textContent = "";
  (defaults.meshPresets || []).forEach(function (preset) {
    const opt = document.createElement("option");
    opt.value = preset.name;
    opt.textContent = preset.name + " (y+ " + preset.targetYPlus + ")";
    presetSel.appendChild(opt);
  });
  presetSel.value = "Medium";

  const envEl = document.getElementById("env.status");
  if (envEl && defaults.environment) {
    const env = defaults.environment;
    const wslList = env.wslDistros || [];
    const dockerStr = env.dockerAvailable ? "Docker CLI detected" : "Docker not found";
    const ofStatus = wslList.length > 0 ? ("WSL: " + wslList.join(", ")) : env.nativeOpenFoamBashrc;
    envEl.textContent = ofStatus + " | " + dockerStr + " | STEP/IGES CAD: " + (env.brepAvailable ? "Enabled" : "STL/OBJ/PLY");
  }

  if (defaults.validation) {
    renderValidationTable(defaults.validation.rows);
    const valImg = document.getElementById("validation.image");
    if (valImg && defaults.validation.validationImage) {
      valImg.src = defaults.validation.validationImage;
      valImg.hidden = false;
    }
  }

  await evaluateCondition();
  await buildGeometry();
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelector('[data-testid="rocket.source_select"]').addEventListener("change", function (ev) {
    const isCad = ev.target.value === "cad";
    document.getElementById("cadControlsBar").hidden = !isCad;
  });

  document.querySelector('[data-testid="tabs.viewport3d_btn"]').addEventListener("click", function () { showTab("viewport3d"); });
  document.querySelector('[data-testid="tabs.geometry_btn"]').addEventListener("click", function () { showTab("geometry"); });
  document.querySelector('[data-testid="tabs.solver_btn"]').addEventListener("click", function () { showTab("solver"); });
  document.querySelector('[data-testid="tabs.results_btn"]').addEventListener("click", function () { showTab("results"); });
  document.querySelector('[data-testid="tabs.validation_btn"]').addEventListener("click", function () { showTab("validation"); });

  document.querySelector('[data-testid="viewport.mode_select"]').addEventListener("change", update3DViewport);
  document.querySelector('[data-testid="viewport.reset_btn"]').addEventListener("click", function () {
    resetCameraToMesh(state.mesh3d);
  });

  document.querySelector('[data-testid="rocket.build_btn"]').addEventListener("click", function () {
    buildGeometry().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="cad.apply_btn"]').addEventListener("click", function () {
    applyCadImport().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="flow.compute_btn"]').addEventListener("click", function () {
    evaluateCondition().then(function () { showTab("solver"); }).catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="flow.export_btn"]').addEventListener("click", function () {
    exportCase().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="runner.start_sweep_btn"]').addEventListener("click", function () {
    startSweepJob().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="runner.cancel_btn"]').addEventListener("click", function () {
    cancelActiveJob().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="results.import_btn"]').addEventListener("click", function () {
    importResultsFolder().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="results.export_csv_btn"]').addEventListener("click", function () {
    if (!state.resultsCsv) {
      setStatus("Run a sweep or import solved OpenFOAM results before exporting CSV.");
      return;
    }
    const blob = new Blob([state.resultsCsv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "rocketcfd_results.csv";
    link.click();
    URL.revokeObjectURL(url);
    setStatus("Downloaded rocketcfd_results.csv");
  });
  document.querySelector('[data-testid="validation.run_live_btn"]').addEventListener("click", function () {
    runLiveValidation().catch(function (err) { setStatus(String(err)); });
  });
  document.querySelector('[data-testid="tacc.generate_btn"]').addEventListener("click", function () {
    generateTaccScript().catch(function (err) { setStatus(String(err)); });
  });

  document.querySelector('[data-testid="header.theme_toggle"]').addEventListener("click", function (ev) {
    const root = document.documentElement;
    const isLight = root.getAttribute("data-theme") === "light";
    if (isLight) {
      root.removeAttribute("data-theme");
      ev.currentTarget.textContent = "Light Theme";
    } else {
      root.setAttribute("data-theme", "light");
      ev.currentTarget.textContent = "Dark Theme";
    }
  });

  initializeStudio().catch(function (err) {
    setStatus("Failed to initialize RocketCFD Studio: " + String(err));
  });
});
