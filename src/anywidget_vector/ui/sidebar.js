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

  // === Event Bindings ===
  model.on("change:points", () => {
    updateDimensions();
    updateClusters();
  });
  model.on("change:color_field", updateClusters);
  model.on("change:backend_config", updateCollections);
  model.on("change:backend", updateCollections);

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
