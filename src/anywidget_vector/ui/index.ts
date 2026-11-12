// The widget's ES module entry: assembles the panels and canvas and defines render(). Bundled by
// scripts/build-esm.mjs into ui/dist/widget.js, which the Python side inlines after the vendored Three.js.

import { backendInfo as lookupBackend } from "./constants.ts";
import { followHostTheme, trackModelListeners } from "./theme.ts";
import { createSidebar } from "./sidebar.ts";
import { createToolbar } from "./toolbar.ts";
import { createSettingsPanel } from "./settings.ts";
import { createPropertiesPanel } from "./properties.ts";
import { createCanvas } from "./canvas.ts";
import { executeBackendQuery, isLatestQuery, startQuery } from "./query.ts";
import type { Panel, PropertiesPanel, WidgetModel } from "./types.ts";



function render({ model: widgetModel, el }: { model: WidgetModel; el: HTMLElement }): () => void {
  // Components see a model whose listeners are removed with the view
  const model = trackModelListeners(widgetModel);
  const wrapper = document.createElement("div");
  wrapper.className = "avs-wrapper";

  const _w = model.get("width");
  const _h = model.get("height");
  wrapper.style.width = _w > 0 ? _w + "px" : "100%";
  if (_h > 0) {
    wrapper.style.height = _h + "px";
  } else {
    wrapper.style.aspectRatio = "1 / 1";
  }

  el.appendChild(wrapper);

  // Follows the page theme until the user chooses (theme.js)
  const stopFollowingTheme = followHostTheme(model, el, (dark: boolean) => wrapper.classList.toggle("avs-dark", dark));

  let sidebar: Panel;
  let settingsPanel: Panel | null = null;
  let propertiesPanel: PropertiesPanel;
  let toolbarUI: ReturnType<typeof createToolbar> | null = null;

  if (model.get("show_toolbar")) {
    toolbarUI = createToolbar(model, {
      onRunQuery: () => runQuery(),
      onFilterInput: (text: string) => {
        if (canvas) {
          const result = canvas.applyFilter(text, false);
          if (toolbarUI) toolbarUI.setFilterCount(result.matched, result.total);
        }
      },
      onToggleSidebar: () => sidebar?.toggle(),
      onToggleSettings: () => {
        if (propertiesPanel?.isOpen()) propertiesPanel.close();
        settingsPanel?.toggle();
      },
      onToggleProperties: () => {
        if (settingsPanel?.isOpen()) settingsPanel.close();
        propertiesPanel?.toggle();
      },
    });
    wrapper.appendChild(toolbarUI.element);
  }

  const main = document.createElement("div");
  main.className = "avs-main";
  wrapper.appendChild(main);

  // Sidebar (left, explorer panel)
  sidebar = createSidebar(model, {
    onClose: () => sidebar?.close(),
  });
  main.appendChild(sidebar.element);

  const canvasContainer = document.createElement("div");
  canvasContainer.className = "avs-canvas-container";
  canvasContainer.style.width = "100%";
  canvasContainer.style.height = "100%";
  main.appendChild(canvasContainer);

  if (model.get("show_settings")) {
    settingsPanel = createSettingsPanel(model, {
      onClose: () => settingsPanel?.close(),
    });
    main.appendChild(settingsPanel.element);
  }

  propertiesPanel = createPropertiesPanel(model, {
    onClose: () => propertiesPanel?.close(),
  });
  main.appendChild(propertiesPanel.element);
  if (model.get("show_properties")) propertiesPanel.open();

  let canvas: ReturnType<typeof createCanvas>;
  try {
    canvas = createCanvas(model, canvasContainer, {
      onHover: (point) => propertiesPanel?.setHoveredPoint(point),
    });
  } catch (err) {
    // No WebGL, for one: the view never returns its cleanup, so remove the listeners it already added
    stopFollowingTheme();
    model.offAll();
    throw err;
  }

  async function runQuery() {
    const query = model.get("query_input") || "";

    // Apply hard client-side filter (completely hide non-matching)
    if (canvas) {
      const result = canvas.applyFilter(query, true);
      if (toolbarUI) toolbarUI.setFilterCount(result.matched, result.total);
    }

    // Additionally run a backend query if connected
    const backend = model.get("backend");
    const backendInfo = lookupBackend(backend);
    const mode = model.get("grafeo_connection_mode") || "embedded";
    const status = model.get("connection_status");

    const isBrowserSide = (backendInfo && backendInfo.side === "browser") ||
      (backend === "grafeo" && (mode === "server" || mode === "wasm"));
    const hasBackend = isBrowserSide || status === "connected";

    if (!hasBackend) return;

    // A slower, older query must not overwrite the result of a newer one
    const ticket = startQuery(widgetModel);
    if (toolbarUI) toolbarUI.setLoading(true);
    // A Python-side query answers later: the Run button keeps loading until Python sets the final status
    let pythonPending = false;

    try {
      model.set("query_error", null);
      model.set("connection_status", "connecting");
      model.save_changes();

      if (isBrowserSide) {
        const points = await executeBackendQuery(model);
        if (!isLatestQuery(widgetModel, ticket)) return;
        model.set("points", points);
        model.set("connection_status", "connected");
        model.save_changes();
      } else {
        const onStatus = () => {
          if (model.get("connection_status") === "connecting") return;
          model.off("change:connection_status", onStatus);
          if (toolbarUI && isLatestQuery(widgetModel, ticket)) toolbarUI.setLoading(false);
        };
        model.on("change:connection_status", onStatus);
        pythonPending = true;
        model.set("_execute_query", Date.now());
        model.save_changes();
      }
    } catch (err) {
      if (!isLatestQuery(widgetModel, ticket)) return;
      model.set("query_error", err instanceof Error ? err.message : String(err));
      model.set("connection_status", "error");
      model.save_changes();
      console.error("Query error:", err);
    } finally {
      if (!pythonPending && toolbarUI && isLatestQuery(widgetModel, ticket)) toolbarUI.setLoading(false);
    }
  }

  return () => {
    stopFollowingTheme();
    model.offAll();
    canvas.cleanup();
  };
}

export default { render };
