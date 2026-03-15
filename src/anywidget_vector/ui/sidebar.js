/**
 * Left sidebar: Collections browser + Dimension/Cluster Explorer.
 */
import { ICONS } from "../static/icons.js";

export function createSidebar(model, callbacks) {
  const panel = document.createElement("div");
  panel.className = "avs-panel avs-panel-left";

  const inner = document.createElement("div");
  inner.className = "avs-panel-inner";
  panel.appendChild(inner);

  // Header
  const header = document.createElement("div");
  header.className = "avs-panel-header";
  header.innerHTML = "<span>Explorer</span>";
  const closeBtn = document.createElement("button");
  closeBtn.className = "avs-btn avs-btn-icon";
  closeBtn.innerHTML = ICONS.close;
  closeBtn.addEventListener("click", () => callbacks.onClose?.());
  header.appendChild(closeBtn);
  inner.appendChild(header);

  // === Collections Section ===
  const collectionsSection = document.createElement("div");
  collectionsSection.className = "avs-sidebar-section";

  const collectionsHeader = document.createElement("div");
  collectionsHeader.className = "avs-section-header";
  collectionsHeader.textContent = "Collections";
  collectionsSection.appendChild(collectionsHeader);

  const collectionsList = document.createElement("div");
  collectionsList.className = "avs-collections-list";
  collectionsSection.appendChild(collectionsList);
  inner.appendChild(collectionsSection);

  // === Dimensions Section ===
  const dimSection = document.createElement("div");
  dimSection.className = "avs-sidebar-section";

  const dimHeader = document.createElement("div");
  dimHeader.className = "avs-section-header";
  dimHeader.textContent = "Dimensions";
  dimSection.appendChild(dimHeader);

  const dimContent = document.createElement("div");
  dimContent.className = "avs-dimension-content";
  dimSection.appendChild(dimContent);
  inner.appendChild(dimSection);

  // === Clusters Section ===
  const clusterSection = document.createElement("div");
  clusterSection.className = "avs-sidebar-section";

  const clusterHeader = document.createElement("div");
  clusterHeader.className = "avs-section-header";
  clusterHeader.textContent = "Clusters";
  clusterSection.appendChild(clusterHeader);

  const clusterContent = document.createElement("div");
  clusterContent.className = "avs-cluster-content";
  clusterSection.appendChild(clusterContent);
  inner.appendChild(clusterSection);

  // === Update Functions ===

  function updateCollections() {
    collectionsList.innerHTML = "";
    const config = model.get("backend_config") || {};
    const backend = model.get("backend") || "grafeo";
    const name = config.collection || config.index || config.className || config.table || "";

    if (name) {
      const item = document.createElement("div");
      item.className = "avs-collection-item avs-active";
      item.textContent = name;
      collectionsList.appendChild(item);
    } else {
      const note = document.createElement("div");
      note.className = "avs-note";
      note.textContent = backend === "grafeo" ? "Grafeo embedded" : "Configure in settings";
      collectionsList.appendChild(note);
    }
  }

  function updateDimensions() {
    dimContent.innerHTML = "";
    const points = model.get("points") || [];

    if (points.length === 0) {
      dimContent.innerHTML = '<div class="avs-note">Load data to see dimensions</div>';
      return;
    }

    const sample = points[0];
    const vec = sample.vector || [];
    const dims = vec.length || 3;

    addStatRow(dimContent, "Points", points.length.toLocaleString());
    addStatRow(dimContent, "Dimensions", dims > 3 ? dims + "D → 3D" : "3D");

    // Axis mappings
    const axisLabels = model.get("axis_labels") || { x: "X", y: "Y", z: "Z" };
    addStatRow(dimContent, "X axis", axisLabels.x || "X");
    addStatRow(dimContent, "Y axis", axisLabels.y || "Y");
    addStatRow(dimContent, "Z axis", axisLabels.z || "Z");

    // Compute basic stats
    const xs = points.map((p) => p.x ?? 0);
    const ys = points.map((p) => p.y ?? 0);
    const zs = points.map((p) => p.z ?? 0);
    addStatRow(dimContent, "X range", rangeStr(xs));
    addStatRow(dimContent, "Y range", rangeStr(ys));
    addStatRow(dimContent, "Z range", rangeStr(zs));

    // Visual mapping dimensions
    const colorField = model.get("color_field");
    const sizeField = model.get("size_field");
    const shapeField = model.get("shape_field");
    if (colorField) addStatRow(dimContent, "Color", colorField);
    if (sizeField) {
      const sizeRange = model.get("size_range") || [0.02, 0.1];
      addStatRow(dimContent, "Size", sizeField + " [" + sizeRange[0] + "," + sizeRange[1] + "]");
    }
    if (shapeField) {
      const shapeMap = model.get("shape_map") || {};
      const shapes = Object.values(shapeMap);
      const unique = [...new Set(shapes)];
      addStatRow(dimContent, "Shape", shapeField + " (" + unique.length + " shapes)");
    }
  }

  function updateClusters() {
    clusterContent.innerHTML = "";
    const colorField = model.get("color_field");

    if (!colorField) {
      clusterContent.innerHTML = '<div class="avs-note">Set color_field to see clusters</div>';
      return;
    }

    const points = model.get("points") || [];
    const groups = {};
    points.forEach((p) => {
      const val = p[colorField] ?? "unknown";
      groups[val] = (groups[val] || 0) + 1;
    });

    const sorted = Object.entries(groups).sort((a, b) => b[1] - a[1]);
    if (sorted.length === 0) {
      clusterContent.innerHTML = '<div class="avs-note">No clusters found</div>';
      return;
    }

    sorted.forEach(([key, count]) => {
      const row = document.createElement("div");
      row.className = "avs-property-row avs-clickable";
      row.innerHTML =
        '<span class="avs-property-key">' + escapeHtml(String(key)) + "</span>" +
        '<span class="avs-property-value">' + count + "</span>";

      row.addEventListener("click", () => {
        // Filter/highlight cluster
        const ids = points
          .filter((p) => String(p[colorField] ?? "unknown") === String(key))
          .map((p) => p.id)
          .filter(Boolean);
        model.set("selected_points", ids);
        model.save_changes();
      });

      clusterContent.appendChild(row);
    });
  }

  // === Distance Section ===
  const distSection = document.createElement("div");
  distSection.className = "avs-sidebar-section";

  const distHeader = document.createElement("div");
  distHeader.className = "avs-section-header";
  distHeader.textContent = "Distance";
  distSection.appendChild(distHeader);

  const distContent = document.createElement("div");
  distContent.className = "avs-dimension-content";

  // Metric selector
  const metricGroup = document.createElement("div");
  metricGroup.className = "avs-form-group";
  const metricLabel = document.createElement("label");
  metricLabel.className = "avs-label";
  metricLabel.textContent = "Metric";
  metricGroup.appendChild(metricLabel);
  const metricSelect = document.createElement("select");
  metricSelect.className = "avs-select";
  metricSelect.style.width = "100%";
  ["euclidean", "cosine", "manhattan", "dot_product"].forEach(m => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    opt.selected = m === (model.get("distance_metric") || "euclidean");
    metricSelect.appendChild(opt);
  });
  metricSelect.addEventListener("change", () => {
    model.set("distance_metric", metricSelect.value);
    model.save_changes();
  });
  metricGroup.appendChild(metricSelect);
  distContent.appendChild(metricGroup);

  // K neighbors
  const kGroup = document.createElement("div");
  kGroup.className = "avs-form-group";
  const kLabel = document.createElement("label");
  kLabel.className = "avs-label";
  kLabel.textContent = "K neighbors";
  kGroup.appendChild(kLabel);
  const kInput = document.createElement("input");
  kInput.type = "number";
  kInput.className = "avs-input";
  kInput.min = "0";
  kInput.max = "50";
  kInput.value = model.get("k_neighbors") || 0;
  kInput.addEventListener("input", () => {
    const k = parseInt(kInput.value, 10) || 0;
    model.set("k_neighbors", k);
    model.set("show_connections", k > 0);
    model.save_changes();
  });
  kGroup.appendChild(kInput);
  distContent.appendChild(kGroup);

  // Distance info (updates when points are selected)
  const distInfo = document.createElement("div");
  distInfo.className = "avs-note";
  distInfo.textContent = "Select a point to see distances";
  distContent.appendChild(distInfo);

  distSection.appendChild(distContent);
  inner.appendChild(distSection);

  function updateDistanceInfo() {
    const selected = model.get("selected_points") || [];
    if (selected.length === 0) {
      distInfo.textContent = "Select a point to see distances";
      return;
    }
    const points = model.get("points") || [];
    const ref = points.find(p => p.id === selected[0]);
    if (!ref) return;

    const metric = metricSelect.value;
    const others = points.filter(p => p.id !== ref.id);

    function dist(a, b) {
      const dx = (a.x ?? 0) - (b.x ?? 0), dy = (a.y ?? 0) - (b.y ?? 0), dz = (a.z ?? 0) - (b.z ?? 0);
      if (metric === "manhattan") return Math.abs(dx) + Math.abs(dy) + Math.abs(dz);
      if (metric === "cosine") {
        const dot = (a.x??0)*(b.x??0) + (a.y??0)*(b.y??0) + (a.z??0)*(b.z??0);
        const ma = Math.sqrt((a.x??0)**2 + (a.y??0)**2 + (a.z??0)**2);
        const mb = Math.sqrt((b.x??0)**2 + (b.y??0)**2 + (b.z??0)**2);
        return (ma === 0 || mb === 0) ? 1 : 1 - dot / (ma * mb);
      }
      if (metric === "dot_product") return -((a.x??0)*(b.x??0) + (a.y??0)*(b.y??0) + (a.z??0)*(b.z??0));
      return Math.sqrt(dx*dx + dy*dy + dz*dz);
    }

    const sorted = others.map(p => ({ id: p.id, label: p.label || p.id, d: dist(ref, p) }))
      .sort((a, b) => a.d - b.d).slice(0, 5);

    distInfo.innerHTML = "<strong>" + escapeHtml(ref.label || ref.id) + "</strong><br>" +
      sorted.map(n => '<span class="avs-property-key">' + escapeHtml(n.label) +
        '</span> <span class="avs-property-value">' + n.d.toFixed(2) + "</span>").join("<br>");
  }

  // === Event Bindings ===
  model.on("change:points", () => {
    updateDimensions();
    updateClusters();
  });
  model.on("change:color_field", updateClusters);
  model.on("change:backend_config", updateCollections);
  model.on("change:backend", updateCollections);
  model.on("change:selected_points", updateDistanceInfo);
  model.on("change:distance_metric", () => {
    metricSelect.value = model.get("distance_metric") || "euclidean";
    updateDistanceInfo();
  });

  // Initial render
  updateCollections();
  updateDimensions();
  updateClusters();

  return {
    element: panel,
    open: () => panel.classList.add("avs-open"),
    close: () => panel.classList.remove("avs-open"),
    toggle: () => panel.classList.toggle("avs-open"),
    isOpen: () => panel.classList.contains("avs-open"),
  };
}

// === Helpers ===

function addStatRow(container, key, value) {
  const row = document.createElement("div");
  row.className = "avs-property-row";
  row.innerHTML =
    '<span class="avs-property-key">' + key + "</span>" +
    '<span class="avs-property-value">' + value + "</span>";
  container.appendChild(row);
}

function rangeStr(values) {
  if (values.length === 0) return "—";
  const min = Math.min(...values);
  const max = Math.max(...values);
  return min.toFixed(2) + " … " + max.toFixed(2);
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
