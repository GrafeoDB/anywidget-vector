// Runs the to_html() page's renderer (ui/export.ts) in jsdom with the real vendored Three.js; only WebGLRenderer is
// stubbed (jsdom has no WebGL), and the camera and the points mesh are captured to check what the page draws.
// jsdom comes from `npm ci --prefix tests/js`.
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
const skip: string | false = JSDOM ? false : "jsdom is not installed (npm ci --prefix tests/js)";

const here = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.resolve(here, "..", "..", "src", "anywidget_vector", "ui");

let vendor: any = null;
let pageCount = 0;

// Loads the page once per call (a fresh module instance) and returns its DOM, camera and points mesh
async function exportPage(data: Record<string, unknown>[], options: Record<string, unknown> = {}) {
  assert.ok(JSDOM, "jsdom is not installed (npm ci --prefix tests/js)");
  const dom = new JSDOM('<!DOCTYPE html><div id="container"></div><div id="tooltip"></div>', { pretendToBeVisual: true });
  const { window } = dom;
  const g = globalThis as any;
  g.window = window;
  g.self = window;
  g.document = window.document;
  // The page's animation loop would keep the test process alive
  g.requestAnimationFrame = () => 0;
  g.DATA = data;
  g.OPTIONS = { size_range: [0.02, 0.06], show_axes: false, show_grid: false, ...options };

  if (!vendor) {
    // The vendored Three.js as a classic script: it sets globalThis.anywidgetVectorVendor
    (0, eval)(readFileSync(path.join(uiDir, "vendor", "three.min.js"), "utf8"));
    vendor = g.anywidgetVectorVendor;
    vendor.THREE.WebGLRenderer = class {
      domElement = g.document.createElement("canvas");
      setSize() {}
      setPixelRatio() {}
      render() {}
    };
  }
  const captured: { camera?: any; meshes: any[] } = { meshes: [] };
  const { PerspectiveCamera, InstancedMesh } = vendor.THREE;
  vendor.THREE.PerspectiveCamera = class extends PerspectiveCamera {
    constructor(...args: any[]) {
      super(...args);
      captured.camera = this;
    }
  };
  vendor.THREE.InstancedMesh = class extends InstancedMesh {
    constructor(...args: any[]) {
      super(...args);
      captured.meshes.push(this);
    }
  };
  try {
    pageCount += 1;
    await import(`../../src/anywidget_vector/ui/export.ts?page=${pageCount}`);
  } finally {
    vendor.THREE.PerspectiveCamera = PerspectiveCamera;
    vendor.THREE.InstancedMesh = InstancedMesh;
  }
  return { window, ...captured };
}

test("every point is one instance of a single mesh", { skip }, async () => {
  const data = [
    { id: "a", x: 0, y: 0, z: 0 },
    { id: "b", x: 1, y: 2, z: 3 },
    { id: "c", x: -1, y: 0, z: 1 },
  ];
  const { meshes } = await exportPage(data);
  assert.equal(meshes.length, 1, "one InstancedMesh");
  assert.equal(meshes[0].count, 3, "an instance per point");
});

test("point sizes scale with the data extent like the live canvas", { skip }, async () => {
  // Extent 100 on x: the live canvas multiplies size_range by 100 / 10; no size_field, so the middle of the range
  // (instance matrices are float32)
  const { meshes } = await exportPage([
    { id: "a", x: 0, y: 0, z: 0 },
    { id: "b", x: 100, y: 0, z: 0 },
  ]);
  const matrix = new vendor.THREE.Matrix4();
  meshes[0].getMatrixAt(0, matrix);
  const scale = new vendor.THREE.Vector3().setFromMatrixScale(matrix);
  assert.ok(Math.abs(scale.x - 0.04 * 10) < 1e-6, `sphere scale ${scale.x}, expected 0.4`);
});

test("a single point puts the camera away from its target", { skip }, async () => {
  const { camera } = await exportPage([{ id: "a", x: 2, y: 2, z: 2 }]);
  const distance = camera.position.distanceTo(new vendor.THREE.Vector3(2, 2, 2));
  assert.ok(distance > 0, `camera distance to the point is ${distance}`);
});

test("the tooltip hides when the pointer leaves the page", { skip }, async () => {
  const { window } = await exportPage([{ id: "a", x: 0, y: 0, z: 0 }]);
  const tooltip = window.document.getElementById("tooltip")!;
  tooltip.style.display = "block";
  window.document.getElementById("container")!.dispatchEvent(new window.Event("mouseleave"));
  assert.equal(tooltip.style.display, "none");
});
