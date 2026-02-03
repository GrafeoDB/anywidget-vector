// Properties panel component for VectorSpace widget
import { ICONS } from "../static/icons.js";

export function createPropertiesPanel(model, callbacks) {
  const panel = document.createElement("div");
  panel.className = "avs-panel avs-panel-right";

  const inner = document.createElement("div");
  inner.className = "avs-panel-inner";
  panel.appendChild(inner);

  // Header
  const header = document.createElement("div");
  header.className = "avs-panel-header";
  header.innerHTML = `<span>Properties</span>`;
  const closeBtn = document.createElement("button");
  closeBtn.className = "avs-btn avs-btn-icon";
  closeBtn.innerHTML = ICONS.close;
  closeBtn.addEventListener("click", () => callbacks.onClose?.());
  header.appendChild(closeBtn);
  inner.appendChild(header);

  // Content container
  const content = document.createElement("div");
  content.className = "avs-properties-content";
  inner.appendChild(content);

  // Initial state
  showEmpty(content);

  // Update on selection change
  model.on("change:selected_points", () => {
    const selectedIds = model.get("selected_points") || [];
    const points = model.get("points") || [];
    if (selectedIds.length === 0) {
      showEmpty(content);
    } else if (selectedIds.length === 1) {
      const point = points.find(p => p.id === selectedIds[0]);
      if (point) {
        showPointProperties(content, point);
      } else {
        showEmpty(content);
      }
    } else {
      showMultipleSelection(content, selectedIds.length);
    }
  });

  // Update on hover
  model.on("change:hovered_point", () => {
    const hovered = model.get("hovered_point");
    const selectedIds = model.get("selected_points") || [];
    if (hovered && selectedIds.length === 0) {
      showPointProperties(content, hovered, true);
    } else if (selectedIds.length === 0) {
      showEmpty(content);
    }
  });

  return {
    element: panel,
    open: () => panel.classList.add("avs-open"),
    close: () => panel.classList.remove("avs-open"),
    toggle: () => panel.classList.toggle("avs-open"),
    isOpen: () => panel.classList.contains("avs-open"),
  };
}

function showEmpty(container) {
  container.innerHTML = `
    <div class="avs-properties-empty">
      <p>Select a point to view its properties</p>
    </div>
  `;
}

function showMultipleSelection(container, count) {
  container.innerHTML = `
    <div class="avs-properties-empty">
      <p>${count} points selected</p>
    </div>
  `;
}

function showPointProperties(container, point, isHover = false) {
  container.innerHTML = "";

  // Header with ID
  const header = document.createElement("div");
  header.className = "avs-section-header";
  header.textContent = isHover ? "Hovered" : "Selected";
  container.appendChild(header);

  // ID row
  addPropertyRow(container, "id", point.id);

  // Label if present
  if (point.label) {
    addPropertyRow(container, "label", point.label);
  }

  // Position section
  const posHeader = document.createElement("div");
  posHeader.className = "avs-section-header";
  posHeader.textContent = "Position";
  container.appendChild(posHeader);

  addPropertyRow(container, "x", formatNumber(point.x));
  addPropertyRow(container, "y", formatNumber(point.y));
  addPropertyRow(container, "z", formatNumber(point.z));

  // Score if present (from search results)
  if (point.score !== undefined) {
    const scoreHeader = document.createElement("div");
    scoreHeader.className = "avs-section-header";
    scoreHeader.textContent = "Similarity";
    container.appendChild(scoreHeader);
    addPropertyRow(container, "score", formatNumber(point.score));
  }

  // Other metadata
  const skipKeys = new Set(["id", "label", "x", "y", "z", "score", "vector", "color", "size", "shape"]);
  const metaKeys = Object.keys(point).filter(k => !skipKeys.has(k) && !k.startsWith("_"));

  if (metaKeys.length > 0) {
    const metaHeader = document.createElement("div");
    metaHeader.className = "avs-section-header";
    metaHeader.textContent = "Metadata";
    container.appendChild(metaHeader);

    metaKeys.forEach(key => {
      addPropertyRow(container, key, formatValue(point[key]));
    });
  }
}

function addPropertyRow(container, key, value) {
  const row = document.createElement("div");
  row.className = "avs-property-row";
  row.innerHTML = `
    <span class="avs-property-key">${key}</span>
    <span class="avs-property-value" title="${String(value)}">${value}</span>
  `;
  container.appendChild(row);
}

function formatNumber(val) {
  if (val === undefined || val === null) return "—";
  if (typeof val === "number") return val.toFixed(4);
  return String(val);
}

function formatValue(val) {
  if (val === undefined || val === null) return "—";
  if (typeof val === "number") return val.toFixed(4);
  if (typeof val === "object") return JSON.stringify(val).slice(0, 50);
  return String(val).slice(0, 50);
}
