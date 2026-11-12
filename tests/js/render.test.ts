// Mounts the widget's front end in jsdom with a plain-object model (get, set, on, off, save_changes), the way a
// host without Jupyter does. The real vendored Three.js runs (loaded from ui/vendor/three.min.js); only
// WebGLRenderer is stubbed, because jsdom has no WebGL. jsdom comes from `npm ci --prefix tests/js`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

let JSDOM: typeof import("jsdom").JSDOM | null = null;
try {
  ({ JSDOM } = await import("jsdom"));
} catch {
  // not installed
}
const skip = JSDOM ? "" : "jsdom is not installed (npm ci --prefix tests/js)";

const here = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.resolve(here, "..", "..", "src", "anywidget_vector", "ui");

// A host model with the values kept for assertions; emit() fires a change event like anywidget does
function fakeModel(values: Record<string, any> = {}) {
  const handlers = new Map<string, Set<(...args: any[]) => void>>();
  return {
    values,
    get: (key: string) => values[key],
    set: (key: string, value: any) => {
      values[key] = value;
    },
    save_changes: () => {},
    on: (event: string, callback: (...args: any[]) => void) => {
      const set = handlers.get(event) ?? new Set();
      set.add(callback);
      handlers.set(event, set);
    },
    off: (event: string, callback: (...args: any[]) => void) => {
      handlers.get(event)?.delete(callback);
    },
    emit: (event: string, ...args: any[]) => {
      for (const callback of handlers.get(event) ?? []) callback(...args);
    },
    listenerCount: () => [...handlers.values()].reduce((n, set) => n + set.size, 0),
  };
}

// The widget's trait defaults (widget.py), so render() sees what a real host sends
const DEFAULTS: Record<string, any> = {
  points: [],
  width: 0,
  height: 0,
  background: "#1a1a2e",
  dark_mode: true,
  _theme_explicit: false,
  _background_explicit: false,
  show_axes: true,
  show_grid: true,
  axis_labels: { x: "X", y: "Y", z: "Z" },
  grid_divisions: 10,
  color_field: null,
  color_scale: "viridis",
  color_domain: null,
  size_field: null,
  size_range: [0.02, 0.06],
  shape_field: null,
  shape_map: {},
  camera_position: [2, 2, 2],
  camera_target: [0, 0, 0],
  selected_points: [],
  hovered_point: null,
  selection_mode: "click",
  show_tooltip: true,
  tooltip_fields: ["label", "x", "y", "z"],
  use_instancing: true,
  point_budget: 100000,
  distance_metric: "euclidean",
  show_connections: false,
  k_neighbors: 0,
  distance_threshold: null,
  connection_color: "#ffffff",
  connection_opacity: 0.3,
  show_toolbar: true,
  show_settings: true,
  show_properties: true,
  show_sidebar: true,
  backend: "grafeo",
  grafeo_connection_mode: "embedded",
  grafeo_server_url: "",
  backend_config: {},
  query_input: "",
  query_limit: 100,
  query_error: null,
  connection_status: "disconnected",
  embedding_config: {},
};

async function mount(values: Record<string, any> = {}) {
  assert.ok(JSDOM, skip);
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { pretendToBeVisual: true });
  const { window } = dom;
  // The widget modules read the DOM through globals; point them at the jsdom window
  const g = globalThis as any;
  g.window = window;
  g.self = window;
  g.document = window.document;
  g.HTMLElement = window.HTMLElement;
  g.MutationObserver = window.MutationObserver;
  g.CustomEvent = window.CustomEvent;
  g.requestAnimationFrame = window.requestAnimationFrame.bind(window);
  g.cancelAnimationFrame = window.cancelAnimationFrame.bind(window);
  g.getComputedStyle = window.getComputedStyle.bind(window);
  g.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  // The vendored Three.js (a classic script with a top-level var), evaluated in the global scope so it sees the
  // jsdom window/document above and sets globalThis.anywidgetVectorVendor
  (0, eval)(readFileSync(path.join(uiDir, "vendor", "three.min.js"), "utf8"));
  const vendor = g.anywidgetVectorVendor;
  // jsdom has no WebGL: the renderer stub owns a real canvas element, everything else is real Three.js
  vendor.THREE.WebGLRenderer = class {
    domElement = window.document.createElement("canvas");
    shadowMap: Record<string, unknown> = {};
    setSize() {}
    setPixelRatio() {}
    render() {}
    dispose() {}
  };

  const { default: widget } = await import("../../src/anywidget_vector/ui/index.ts");
  const model = fakeModel({ ...DEFAULTS, ...values });
  const el = window.document.createElement("div");
  window.document.body.appendChild(el);
  const cleanup = widget.render({ model: model as any, el });
  return { window, model, el, cleanup };
}

test("renders the toolbar, sidebar, properties and a canvas", async () => {
  const { el, cleanup } = await mount({
    points: [
      { id: "a", x: 1, y: 0, z: 0, label: "A" },
      { id: "b", x: 0, y: 2, z: 0, label: "B" },
      { id: "c", x: 0, y: 0, z: 3, label: "C" },
    ],
  });
  const wrapper = el.querySelector(".avs-wrapper");
  assert.ok(wrapper, "the wrapper is in the host element");
  assert.ok(el.querySelector(".avs-toolbar"), "the toolbar is rendered (show_toolbar)");
  assert.ok(el.querySelector(".avs-panel-left"), "the sidebar is rendered");
  assert.ok(el.querySelector(".avs-canvas-container canvas"), "the 3D canvas is in the container");
  // The sidebar's dimension stats count the points
  const dims = el.querySelector(".avs-dimension-content");
  assert.ok(dims?.textContent?.includes("3"), `sidebar counts 3 points, got: ${dims?.textContent}`);
  cleanup();
});

test("a theme change event flips the dark class on the wrapper", async () => {
  const { model, el, cleanup } = await mount({ dark_mode: true, _theme_explicit: true });
  const wrapper = el.querySelector(".avs-wrapper");
  assert.ok(wrapper?.classList.contains("avs-dark"), "dark mode on from the start");
  model.values.dark_mode = false;
  model.emit("change:dark_mode");
  assert.ok(!wrapper?.classList.contains("avs-dark"), "light after the change event");
  cleanup();
});

test("a points change event rebuilds the scene without error", async () => {
  const { model, cleanup } = await mount({ points: [{ id: "a", x: 0, y: 0, z: 0 }] });
  model.values.points = [
    { id: "a", x: 0, y: 0, z: 0 },
    { id: "b", x: 1, y: 1, z: 1 },
  ];
  model.emit("change:points");
  cleanup();
});

test("cleanup removes every model listener the view added", async () => {
  const { model, cleanup } = await mount();
  const before = model.listenerCount();
  assert.ok(before > 0, "the view listens to model changes");
  cleanup();
  assert.equal(model.listenerCount(), 0, "offAll removed the listeners");
});
