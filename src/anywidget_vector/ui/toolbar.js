// Toolbar component for VectorSpace widget
import { ICONS } from "../static/icons.js";

export function createToolbar(model, callbacks) {
  const toolbar = document.createElement("div");
  toolbar.className = "avs-toolbar";

  // Sidebar toggle (left, explorer panel)
  const sidebarBtn = document.createElement("button");
  sidebarBtn.className = "avs-btn";
  sidebarBtn.innerHTML = ICONS.sidebar || ICONS.menu || '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>';
  sidebarBtn.title = "Toggle explorer";
  sidebarBtn.addEventListener("click", () => callbacks.onToggleSidebar?.());
  toolbar.appendChild(sidebarBtn);

  // Search / filter input
  const queryInput = document.createElement("input");
  queryInput.type = "text";
  queryInput.className = "avs-query-input";
  queryInput.placeholder = "Filter points...";
  queryInput.value = model.get("query_input") || "";
  queryInput.title = "Type to filter points by label or metadata";
  queryInput.addEventListener("input", () => {
    model.set("query_input", queryInput.value);
    model.save_changes();
    callbacks.onFilterInput?.(queryInput.value);
  });
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      callbacks.onRunQuery?.();
    }
  });
  toolbar.appendChild(queryInput);

  // Filter count badge
  const filterCount = document.createElement("span");
  filterCount.className = "avs-filter-count";
  filterCount.style.display = "none";
  toolbar.appendChild(filterCount);

  // Run button
  const runBtn = document.createElement("button");
  runBtn.className = "avs-btn avs-btn-primary";
  runBtn.innerHTML = ICONS.play;
  runBtn.title = "Run Query";
  runBtn.addEventListener("click", () => callbacks.onRunQuery?.());
  toolbar.appendChild(runBtn);

  // Settings button with status dot (mutual exclusion with properties)
  const settingsBtn = document.createElement("button");
  settingsBtn.className = "avs-btn avs-settings-btn";
  const statusDot = document.createElement("span");
  statusDot.className = "avs-status-dot";
  updateStatusDot(statusDot, model.get("connection_status") || "disconnected");
  settingsBtn.innerHTML = ICONS.settings;
  settingsBtn.appendChild(statusDot);
  settingsBtn.title = "Settings";
  settingsBtn.addEventListener("click", () => callbacks.onToggleSettings?.());
  toolbar.appendChild(settingsBtn);

  // Properties toggle button (mutual exclusion with settings)
  const propsBtn = document.createElement("button");
  propsBtn.className = "avs-btn";
  propsBtn.innerHTML = ICONS.cube;
  propsBtn.title = "Properties";
  propsBtn.addEventListener("click", () => callbacks.onToggleProperties?.());
  toolbar.appendChild(propsBtn);

  // Model change listeners
  model.on("change:connection_status", () => {
    updateStatusDot(statusDot, model.get("connection_status"));
  });

  return {
    element: toolbar,
    runBtn,
    setLoading: (loading) => {
      if (loading) {
        runBtn.innerHTML = ICONS.loader;
        runBtn.classList.add("avs-loading");
        runBtn.disabled = true;
      } else {
        runBtn.innerHTML = ICONS.play;
        runBtn.classList.remove("avs-loading");
        runBtn.disabled = false;
      }
    },
    setFilterCount: (matched, total) => {
      if (matched < total) {
        filterCount.textContent = `${matched}/${total}`;
        filterCount.style.display = "";
      } else {
        filterCount.style.display = "none";
      }
    },
  };
}

function updateStatusDot(dot, status) {
  dot.className = `avs-status-dot avs-status-${status}`;
}

