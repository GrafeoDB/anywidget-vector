// The standalone export page's renderer (ui/export.html, filled in by widget.py's to_html): a static 3D point
// cloud with orbit controls, optional axes and grid, and a hover tooltip -- no toolbar, panels, query or backend.
// scripts/build-esm.mjs bundles this into ui/dist/export.js, which to_html inlines after the page's DATA/OPTIONS.
import { THREE, OrbitControls } from "./vendor-globals.ts";
import { getPointColor, getPointSize } from "./canvas.ts";
import type { PointStyleOpts } from "./canvas.ts";
import { DARK, LIGHT } from "./palette.ts";
import { CategoryRegistry } from "./registry.ts";
import { categoricalCounts } from "./colors.ts";
import { fitDistance } from "./frame.ts";
import { applyInk } from "./ink.ts";
import { labChrome } from "./lab.ts";
import type { PointData } from "./types.ts";

// Written into the page by widget.py's to_html before this bundle runs
declare const DATA: PointData[];
declare const OPTIONS: {
  background?: string;
  dark_mode?: boolean;
  color_field?: string | null;
  color_scale?: string;
  color_domain?: [number, number] | null;
  size_field?: string | null;
  size_range?: number[];
  show_axes?: boolean;
  show_grid?: boolean;
  grid_divisions?: number;
  axis_labels?: { x?: string; y?: string; z?: string };
};

// ---------------------------------------------------------------------------
// Resolve options (the color/size helpers are the live widget's own, from canvas.ts)
// ---------------------------------------------------------------------------
// The data bounds: they fit the camera, and scale the point sizes the way the live canvas does (createPoints)
const box = new THREE.Box3();
DATA.forEach((p) => box.expandByPoint(new THREE.Vector3(p.x ?? 0, p.y ?? 0, p.z ?? 0)));
// One point, or points that share a position, give an empty box: 1 keeps the sizes and the camera distance nonzero
const dataSize = box.getSize(new THREE.Vector3()).length() || 1;
// Points sized for the framed view, as in the widget (canvas.ts)
const scaleFactor = dataSize / 6;
const rawRange = OPTIONS.size_range || [0.02, 0.06];

const opts: PointStyleOpts = {
  colorField: OPTIONS.color_field || null,
  colorScale: OPTIONS.color_scale || "viridis",
  colorDomain: OPTIONS.color_domain || null,
  sizeField: OPTIONS.size_field || null,
  sizeRange: [rawRange[0] * scaleFactor, rawRange[1] * scaleFactor],
  palette: OPTIONS.dark_mode ? DARK : LIGHT,
  // A fresh assignment from the page's data: the 8 largest categories get the data colours, as in the widget
  registry: null,
};
if (opts.colorField) {
  opts.registry = new CategoryRegistry();
  opts.registry.assign(categoricalCounts(DATA, opts.colorField));
}

// Compute the color and size domains from the data when not explicitly set
if (opts.colorField && !opts.colorDomain) {
  const values = DATA.map((p) => p[opts.colorField as string]).filter((v): v is number => typeof v === "number");
  if (values.length > 0) opts.colorDomain = [Math.min(...values), Math.max(...values)];
}
if (opts.sizeField) {
  const values = DATA.map((p) => p[opts.sizeField as string]).filter((v): v is number => typeof v === "number");
  if (values.length > 0) opts.sizeDomain = [Math.min(...values), Math.max(...values)];
}

// ---------------------------------------------------------------------------
// Scene setup
// ---------------------------------------------------------------------------
const container = document.getElementById("container")!;
const scene = new THREE.Scene();
// The background chosen in Python, else the theme's canvas colour (as the widget)
const background = OPTIONS.background || opts.palette.background;
scene.background = new THREE.Color(background);

const width = container.clientWidth;
const height = container.clientHeight;
const camera = new THREE.PerspectiveCamera(60, width / height, 0.01, 1000);
camera.position.set(5, 5, 5);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
container.appendChild(renderer.domElement);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const directional = new THREE.DirectionalLight(0xffffff, 0.8);
directional.position.set(5, 10, 7);
scene.add(directional);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// ---------------------------------------------------------------------------
// Axes and grid
// ---------------------------------------------------------------------------
// The widget's own (lab.ts): grey axes with mono letters and a hairline grid
scene.add(
  labChrome({
    showAxes: Boolean(OPTIONS.show_axes),
    showGrid: Boolean(OPTIONS.show_grid),
    labels: OPTIONS.axis_labels || {},
    divisions: OPTIONS.grid_divisions || 10,
    palette: opts.palette,
    background,
  }),
);

// ---------------------------------------------------------------------------
// Points
// ---------------------------------------------------------------------------
const pointsGroup = new THREE.Group();
scene.add(pointsGroup);

if (DATA.length > 0) {
  // One instanced mesh for every point: one geometry, one material and one draw call, whatever the point count
  const geometry = new THREE.SphereGeometry(1, 16, 16);
  const material = new THREE.MeshPhongMaterial({ color: 0xffffff });
  // Ink points, as in the widget (ink.ts): the body the colour over the background, the silhouette the full colour
  applyInk(material, { value: new THREE.Color(background) });
  const mesh = new THREE.InstancedMesh(geometry, material, DATA.length);
  const matrix = new THREE.Matrix4();
  DATA.forEach((point, idx) => {
    const size = getPointSize(point, opts);
    matrix.makeScale(size, size, size).setPosition(point.x ?? 0, point.y ?? 0, point.z ?? 0);
    mesh.setMatrixAt(idx, matrix);
    mesh.setColorAt(idx, getPointColor(point, opts));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.computeBoundingSphere();
  pointsGroup.add(mesh);

  // Auto-fit the camera to the data bounds
  // Framed as in the widget: the cloud's real radius, from the same angle (frame.ts)
  const center = box.getCenter(new THREE.Vector3());
  const distance = fitDistance(DATA.map((p) => ({ x: p.x ?? 0, y: p.y ?? 0, z: p.z ?? 0 })), center, camera.fov, camera.aspect) || 2;
  controls.target.copy(center);
  camera.position.copy(center.clone().add(new THREE.Vector3(0.6, 0.5, 0.8).normalize().multiplyScalar(distance)));
  // Clipping planes for the data's scale, as the widget's fitToView
  camera.near = Math.max(0.01, distance * 0.001);
  camera.far = Math.max(1000, distance * 10);
  camera.updateProjectionMatrix();
  controls.update();
}

// ---------------------------------------------------------------------------
// Tooltip via raycasting
// ---------------------------------------------------------------------------
const tooltipEl = document.getElementById("tooltip")!;
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

container.addEventListener("mousemove", (event) => {
  const rect = container.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(pointsGroup.children, true);

  if (intersects.length > 0) {
    // The instance under the pointer is the point's index in DATA
    const idx = intersects[0].instanceId;
    const point = idx === undefined ? undefined : DATA[idx];
    if (point) {
      // Point data can come from a database: build nodes with textContent, never markup
      const node = (tag: string, cls: string | null, text?: string) => {
        const el = document.createElement(tag);
        if (cls) el.className = cls;
        if (text !== undefined) el.textContent = text;
        return el;
      };
      const children: HTMLElement[] = [];
      if (point.label) children.push(node("div", "tooltip-label", String(point.label)));
      for (const [key, val] of Object.entries(point)) {
        if (key === "label" || key === "vector") continue;
        const row = node("div", "tooltip-row");
        const display = typeof val === "number" ? val.toFixed(3) : String(val);
        row.append(node("span", "tooltip-key", key + ":"), node("span", null, display));
        children.push(row);
      }
      tooltipEl.replaceChildren(...children);
      tooltipEl.style.display = "block";
      tooltipEl.style.left = event.clientX - rect.left + 15 + "px";
      tooltipEl.style.top = event.clientY - rect.top + 15 + "px";
    }
  } else {
    tooltipEl.style.display = "none";
  }
});
container.addEventListener("mouseleave", () => {
  tooltipEl.style.display = "none";
});

// ---------------------------------------------------------------------------
// Animation loop
// ---------------------------------------------------------------------------
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

// ---------------------------------------------------------------------------
// Resize handler
// ---------------------------------------------------------------------------
window.addEventListener("resize", () => {
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
});
