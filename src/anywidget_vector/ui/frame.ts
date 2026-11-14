// Where the camera stands to frame the points (the same rule as anywidget-graph's 3D view, force3d.ts).

export interface Vec3 { x: number; y: number; z: number }

/**
 * How far from `center` a camera with a vertical field of view of `fovDeg` (and the canvas's `aspect`, width over
 * height) stands to see every point: the cloud's real radius over the sine of the tighter half-angle, plus a small
 * margin for the point spheres.
 */
export function fitDistance(points: Iterable<Vec3>, center: Vec3, fovDeg: number, aspect: number): number {
  let radius = 0;
  for (const p of points) radius = Math.max(radius, Math.hypot(p.x - center.x, p.y - center.y, p.z - center.z));
  const halfV = (fovDeg * Math.PI) / 360;
  const half = aspect < 1 ? Math.atan(Math.tan(halfV) * aspect) : halfV;
  return (radius / Math.sin(half)) * 1.08;
}

/** The centre of the points' bounding box. */
export function boxCenter(points: Vec3[]): Vec3 {
  const lo = { x: Infinity, y: Infinity, z: Infinity }, hi = { x: -Infinity, y: -Infinity, z: -Infinity };
  for (const p of points) {
    lo.x = Math.min(lo.x, p.x); lo.y = Math.min(lo.y, p.y); lo.z = Math.min(lo.z, p.z);
    hi.x = Math.max(hi.x, p.x); hi.y = Math.max(hi.y, p.y); hi.z = Math.max(hi.z, p.z);
  }
  return { x: (lo.x + hi.x) / 2, y: (lo.y + hi.y) / 2, z: (lo.z + hi.z) / 2 };
}

/**
 * How far the camera stands to frame a selection: like the whole cloud (fitDistance around the selection's centre),
 * but never closer than a quarter of the whole view, so a single point stays a point instead of filling the canvas.
 */
export function selectionDistance(selected: Vec3[], all: Vec3[], fovDeg: number, aspect: number): number {
  const own = fitDistance(selected, boxCenter(selected), fovDeg, aspect);
  const whole = fitDistance(all, boxCenter(all), fovDeg, aspect);
  return Math.max(own, whole * 0.25);
}
