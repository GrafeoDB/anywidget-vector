// The standalone export page's renderer (ui/export.html, filled in by widget.py's to_html): a static 3D point
// cloud with orbit controls, optional axes and grid, and a hover tooltip -- no toolbar, panels, query or backend.
// scripts/build-esm.mjs bundles this into ui/dist/export.js, which to_html inlines after the page's DATA/OPTIONS.
import { THREE, OrbitControls } from "./vendor-globals.ts";
import { getPointColor, getPointSize } from "./canvas.ts";
import type { PointStyleOpts } from "./canvas.ts";
import type { PointData } from "./types.ts";

// Written into the page by widget.py's to_html before this bundle runs
declare const DATA: PointData[];
declare const OPTIONS: {
  background?: string;
  color_field?: string | null;
  color_scale?: string;
  color_domain?: [number, number] | null;
  size_field?: string | null;
  size_range?: number[];
  show_axes?: boolean;
  show_grid?: boolean;
  axis_labels?: { x?: string; y?: string; z?: string };
};

// ---------------------------------------------------------------------------
// Resolve options (the color/size helpers are the live widget's own, from canvas.ts)
// ---------------------------------------------------------------------------
const opts: PointStyleOpts = {
  colorField: OPTIONS.color_field || null,
  colorScale: OPTIONS.color_scale || "viridis",
  colorDomain: OPTIONS.color_domain || null,
  sizeField: OPTIONS.size_field || null,
  sizeRange: OPTIONS.size_range || [0.02, 0.1],
};

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
scene.background = new THREE.Color(OPTIONS.background || "#1a1a2e");

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
if (OPTIONS.show_axes) {
  const axes = new THREE.AxesHelper(1.2);
  scene.add(axes);
  const labels = OPTIONS.axis_labels || { x: "X", y: "Y", z: "Z" };
  function addAxisLabel(text: string, position: [number, number, number], color: number) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;
    canvas.width = 64;
    canvas.height = 32;
    ctx.font = "bold 24px Arial";
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.textAlign = "center";
    ctx.fillText(text, 32, 24);
    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture }));
    sprite.position.set(position[0], position[1], position[2]);
    sprite.scale.set(0.25, 0.125, 1);
    scene.add(sprite);
  }
  addAxisLabel(labels.x || "X", [1.3, 0, 0], 0xff4444);
  addAxisLabel(labels.y || "Y", [0, 1.3, 0], 0x44ff44);
  addAxisLabel(labels.z || "Z", [0, 0, 1.3], 0x4444ff);
}

if (OPTIONS.show_grid) {
  const gridHelper = new THREE.GridHelper(2, 10, 0x444444, 0x333333);
  scene.add(gridHelper);
}

// ---------------------------------------------------------------------------
// Points
// ---------------------------------------------------------------------------
const pointsGroup = new THREE.Group();
scene.add(pointsGroup);

if (DATA.length > 0) {
  DATA.forEach((point, idx) => {
    const geometry = new THREE.SphereGeometry(1, 16, 16);
    const color = getPointColor(point, opts);
    const material = new THREE.MeshPhongMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    const size = getPointSize(point, opts);
    mesh.scale.set(size, size, size);
    mesh.position.set(point.x ?? 0, point.y ?? 0, point.z ?? 0);
    mesh.userData = { pointIndex: idx, pointId: point.id || "point_" + idx };
    pointsGroup.add(mesh);
  });

  // Auto-fit the camera to the data bounds
  const box = new THREE.Box3();
  DATA.forEach((p) => box.expandByPoint(new THREE.Vector3(p.x ?? 0, p.y ?? 0, p.z ?? 0)));
  const center = box.getCenter(new THREE.Vector3());
  const bsize = box.getSize(new THREE.Vector3()).length();
  const distance = bsize / (2 * Math.tan((Math.PI * camera.fov) / 360));
  controls.target.copy(center);
  camera.position.copy(center.clone().add(new THREE.Vector3(distance * 0.6, distance * 0.6, distance * 0.6)));
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
    const hit = intersects[0];
    const idx = hit.object.userData.pointIndex as number;
    const point = DATA[idx];
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
