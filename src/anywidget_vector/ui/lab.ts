// The lab chrome of the 3D view, shared by the widget (canvas.ts) and the to_html() page (export.ts): the axes in the
// theme's edge colour with muted mono letters and a faint hairline grid, as the graph's 3D view (no red, green and
// blue).
import { THREE } from "./vendor-globals.ts";
import type * as THREE_NS from "three";
import { mixOver } from "./registry.ts";
import type { Palette } from "./registry.ts";

export interface LabOptions {
  showAxes: boolean;
  showGrid: boolean;
  labels: { x?: string; y?: string; z?: string };
  divisions: number;
  palette: Palette;
  /** The canvas background (any CSS colour); the grid's hairlines are the edge colour faded towards it */
  background: string;
}

/** The axes, their letters and the grid, in one group (empty when both are off). */
export function labChrome(options: LabOptions): THREE_NS.Group {
  const group = new THREE.Group();
  const { palette } = options;
  if (options.showAxes) {
    // One line per axis (the vendored three.js has Line, not LineSegments)
    const axisMaterial = new THREE.LineBasicMaterial({ color: palette.edge });
    for (const end of [[1.2, 0, 0], [0, 1.2, 0], [0, 0, 1.2]]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(end[0], end[1], end[2])]);
      group.add(new THREE.Line(geometry, axisMaterial));
    }
    const label = (text: string, position: [number, number, number]) => {
      const sprite = axisLabel(text, palette.other);
      if (sprite) {
        sprite.position.set(...position);
        group.add(sprite);
      }
    };
    label(options.labels.x || "X", [1.32, 0, 0]);
    label(options.labels.y || "Y", [0, 1.32, 0]);
    label(options.labels.z || "Z", [0, 0, 1.32]);
  }
  if (options.showGrid) {
    const base = options.background || palette.background;
    group.add(new THREE.GridHelper(2, options.divisions || 10, mixOver(palette.edge, base, 0.7), mixOver(palette.edge, base, 0.4)));
  }
  return group;
}

function axisLabel(text: string, color: string): THREE_NS.Sprite | null {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  canvas.width = 128;
  canvas.height = 32;
  ctx.font = '500 22px "JetBrains Mono", ui-monospace, monospace';
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 64, 16);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
  sprite.scale.set(0.26, 0.065, 1);
  return sprite;
}

/** Free the GPU side of an object and everything under it: geometries, materials and their textures. */
export function disposeTree(root: THREE_NS.Object3D): void {
  root.traverse((obj) => {
    const { geometry, material } = obj as THREE_NS.Mesh;
    geometry?.dispose();
    for (const m of Array.isArray(material) ? material : material ? [material] : []) {
      (m as THREE_NS.SpriteMaterial).map?.dispose();
      m.dispose();
    }
  });
}
