(function () {
  "use strict";

  const state = {
    images: {},
    activeTab: "geometry"
  };

  function setStatus(message) {
    const banner = document.getElementById("status.banner");
    if (banner) banner.textContent = message;
  }

  window.addEventListener("error", function (event) {
    setStatus("Unexpected interface error: " + (event.message || "Unknown failure"));
  });

  window.addEventListener("unhandledrejection", function (event) {
    setStatus("Request did not finish cleanly: " + (event.reason ? String(event.reason) : "Unknown error"));
  });

  async function apiGet(url) {
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return resp.json();
  }

  async function apiPost(url, payload) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
    });
    const data = await resp.json();
    if (!resp.ok && data && data.error) {
      throw new Error(data.error);
    }
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return data;
  }

  function currentPayload() {
    return {
      nosecone_shape: document.getElementById("rocket.nosecone_shape").value,
      nosecone_length: Number(document.getElementById("rocket.nosecone_length").value || 0.45),
      body_length: Number(document.getElementById("rocket.body_length").value || 1.55),
      diameter: Number(document.getElementById("rocket.diameter").value || 0.15),
      fin_count: Number(document.getElementById("rocket.fin_count").value || 4),
      fin_span: Number(document.getElementById("rocket.fin_span").value || 0.14),
      altitude_m: Number(document.getElementById("flow.altitude_input").value || 0),
      velocity_mps: Number(document.getElementById("flow.velocity_input").value || 420),
      alpha_deg: Number(document.getElementById("flow.alpha_input").value || 0),
      mesh_preset: document.getElementById("flow.mesh_preset").value || "Medium"
    };
  }

  function showTab(tabKey) {
    state.activeTab = tabKey;
    const map = {
      "geometry": "tabs.geometry_btn",
      "solver": "tabs.solver_btn",
      "validation": "tabs.validation_btn"
    };
    Object.keys(map).forEach(function (key) {
      const btn = document.querySelector('[data-testid="' + map[key] + '"]');
      if (btn) btn.classList.toggle("active", key === tabKey);
    });

    const img = document.getElementById("preview.image");
    const empty = document.getElementById("preview.empty");
    const src = state.images[tabKey];
    if (img && empty) {
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
      [item.benchmark, item.metric, item.referenceValue].forEach(function (val) {
        const td = document.createElement("td");
        td.textContent = String(val);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    host.appendChild(table);
  }

  async function buildGeometry() {
    setStatus("Assembling parametric rocket panel mesh...");
    const res = await apiPost("/api/geometry", currentPayload());
    if (!res.ok) {
      setStatus(res.error || "Geometry build failed.");
      return;
    }
    state.images.geometry = res.previewImage;
    document.getElementById("kpi.panels").textContent = String(res.metrics.panelCount);
    showTab("geometry");
    setStatus(res.message);
  }

  async function evaluateCondition() {
    setStatus("Evaluating US Standard Atmosphere and OpenFOAM solver regime...");
    const res = await apiPost("/api/condition", currentPayload());
    if (!res.ok) {
      setStatus(res.error || "Condition evaluation failed.");
      return;
    }
    const cond = res.condition;
    document.getElementById("kpi.mach").textContent = String(cond.mach);
    document.getElementById("kpi.solver").textContent = String(cond.solver);
    document.getElementById("kpi.pressure").textContent = cond.dynamicPressurePa.toLocaleString() + " Pa";
    state.images.solver = res.solverPlotImage;
    showTab("solver");
    setStatus(res.message);
  }

  async function exportCase() {
    setStatus("Generating OpenFOAM blockMeshDict, snappyHexMeshDict, and STL files...");
    const res = await apiPost("/api/export_case", currentPayload());
    if (!res.ok) {
      setStatus(res.error || "OpenFOAM case export failed.");
      return;
    }
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
      const wslList = defaults.environment.wslDistros || [];
      envEl.textContent = wslList.length > 0
        ? "WSL distributions detected: " + wslList.join(", ")
        : "OpenFOAM runtime status: " + defaults.environment.nativeOpenFoamBashrc;
    }

    if (defaults.validation) {
      state.images.validation = defaults.validation.validationImage;
      renderValidationTable(defaults.validation.rows);
    }

    await evaluateCondition();
    await buildGeometry();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelector('[data-testid="tabs.geometry_btn"]').addEventListener("click", function () { showTab("geometry"); });
    document.querySelector('[data-testid="tabs.solver_btn"]').addEventListener("click", function () { showTab("solver"); });
    document.querySelector('[data-testid="tabs.validation_btn"]').addEventListener("click", function () { showTab("validation"); });

    document.querySelector('[data-testid="rocket.build_btn"]').addEventListener("click", function () {
      buildGeometry().catch(function (err) { setStatus(String(err)); });
    });
    document.querySelector('[data-testid="flow.compute_btn"]').addEventListener("click", function () {
      evaluateCondition().catch(function (err) { setStatus(String(err)); });
    });
    document.querySelector('[data-testid="flow.export_btn"]').addEventListener("click", function () {
      exportCase().catch(function (err) { setStatus(String(err)); });
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
})();
