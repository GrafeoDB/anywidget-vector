"""Main VectorSpace widget using anywidget and Three.js."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import anywidget
import traitlets

if TYPE_CHECKING:
    from collections.abc import Callable

_ESM = """
import * as THREE from "https://esm.sh/three@0.160.0";
import { OrbitControls } from "https://esm.sh/three@0.160.0/addons/controls/OrbitControls.js";

// Color scales
const COLOR_SCALES = {
  viridis: [[0.267,0.004,0.329],[0.282,0.140,0.458],[0.253,0.265,0.530],[0.206,0.371,0.553],[0.163,0.471,0.558],[0.127,0.566,0.551],[0.134,0.658,0.518],[0.267,0.749,0.441],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144]],
  plasma: [[0.050,0.030,0.528],[0.254,0.014,0.615],[0.417,0.001,0.658],[0.578,0.015,0.643],[0.716,0.135,0.538],[0.826,0.268,0.407],[0.906,0.411,0.271],[0.959,0.567,0.137],[0.981,0.733,0.106],[0.964,0.903,0.259],[0.940,0.975,0.131]],
  inferno: [[0.001,0.000,0.014],[0.046,0.031,0.186],[0.140,0.046,0.357],[0.258,0.039,0.406],[0.366,0.071,0.432],[0.478,0.107,0.429],[0.591,0.148,0.404],[0.706,0.206,0.347],[0.815,0.290,0.259],[0.905,0.411,0.145],[0.969,0.565,0.026]],
  magma: [[0.001,0.000,0.014],[0.035,0.028,0.144],[0.114,0.049,0.315],[0.206,0.053,0.431],[0.306,0.064,0.505],[0.413,0.086,0.531],[0.529,0.113,0.527],[0.654,0.158,0.501],[0.776,0.232,0.459],[0.878,0.338,0.418],[0.953,0.468,0.392]],
  cividis: [[0.000,0.135,0.304],[0.000,0.179,0.345],[0.117,0.222,0.360],[0.214,0.263,0.365],[0.293,0.304,0.370],[0.366,0.345,0.375],[0.437,0.387,0.382],[0.509,0.429,0.393],[0.582,0.473,0.409],[0.659,0.520,0.431],[0.739,0.570,0.461]],
  turbo: [[0.190,0.072,0.232],[0.254,0.265,0.530],[0.163,0.471,0.558],[0.134,0.658,0.518],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144],[0.988,0.652,0.198],[0.925,0.394,0.235],[0.796,0.177,0.214],[0.480,0.016,0.110]],
};

const CATEGORICAL_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#14b8a6"
];

// Shape geometries factory
const SHAPES = {
  sphere: () => new THREE.SphereGeometry(1, 16, 16),
  cube: () => new THREE.BoxGeometry(1, 1, 1),
  cone: () => new THREE.ConeGeometry(0.7, 1.4, 16),
  tetrahedron: () => new THREE.TetrahedronGeometry(1),
  octahedron: () => new THREE.OctahedronGeometry(1),
  cylinder: () => new THREE.CylinderGeometry(0.5, 0.5, 1, 16),
};

function getColorFromScale(value, scaleName, domain) {
  const scale = COLOR_SCALES[scaleName] || COLOR_SCALES.viridis;
  const [min, max] = domain || [0, 1];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const idx = t * (scale.length - 1);
  const i = Math.floor(idx);
  const f = idx - i;
  if (i >= scale.length - 1) {
    const c = scale[scale.length - 1];
    return new THREE.Color(c[0], c[1], c[2]);
  }
  const c1 = scale[i], c2 = scale[i + 1];
  return new THREE.Color(
    c1[0] + f * (c2[0] - c1[0]),
    c1[1] + f * (c2[1] - c1[1]),
    c1[2] + f * (c2[2] - c1[2])
  );
}

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function getCategoricalColor(value) {
  const idx = hashString(String(value)) % CATEGORICAL_COLORS.length;
  return new THREE.Color(CATEGORICAL_COLORS[idx]);
}

function render({ model, el }) {
  let scene, camera, renderer, controls;
  let pointsGroup;
  let raycaster, mouse;
  let hoveredObject = null;
  let tooltip;
  let axesGroup, gridHelper;
  let animationId;

  init();
  animate();

  function init() {
    // Container
    const container = document.createElement("div");
    container.className = "anywidget-vector";
    container.style.width = model.get("width") + "px";
    container.style.height = model.get("height") + "px";
    container.style.position = "relative";
    el.appendChild(container);

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(model.get("background"));

    // Camera
    const aspect = model.get("width") / model.get("height");
    camera = new THREE.PerspectiveCamera(60, aspect, 0.01, 1000);
    const camPos = model.get("camera_position") || [2, 2, 2];
    camera.position.set(camPos[0], camPos[1], camPos[2]);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(model.get("width"), model.get("height"));
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    const target = model.get("camera_target") || [0, 0, 0];
    controls.target.set(target[0], target[1], target[2]);
    controls.addEventListener("change", onCameraChange);

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(5, 10, 7);
    scene.add(directional);

    // Groups
    pointsGroup = new THREE.Group();
    scene.add(pointsGroup);
    axesGroup = new THREE.Group();
    scene.add(axesGroup);

    // Setup
    setupAxesAndGrid();
    setupRaycaster(container);
    setupTooltip(container);
    createPoints();
    bindModelEvents();
  }

  function setupAxesAndGrid() {
    // Clear existing
    while (axesGroup.children.length > 0) {
      axesGroup.remove(axesGroup.children[0]);
    }
    if (gridHelper) {
      scene.remove(gridHelper);
      gridHelper = null;
    }

    if (model.get("show_axes")) {
      const axes = new THREE.AxesHelper(1.2);
      axesGroup.add(axes);

      // Axis labels
      const labels = model.get("axis_labels") || { x: "X", y: "Y", z: "Z" };
      addAxisLabel(labels.x, [1.3, 0, 0], 0xff4444);
      addAxisLabel(labels.y, [0, 1.3, 0], 0x44ff44);
      addAxisLabel(labels.z, [0, 0, 1.3], 0x4444ff);
    }

    if (model.get("show_grid")) {
      gridHelper = new THREE.GridHelper(2, model.get("grid_divisions") || 10, 0x444444, 0x333333);
      scene.add(gridHelper);
    }
  }

  function addAxisLabel(text, position, color) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = 64;
    canvas.height = 32;
    ctx.font = "bold 24px Arial";
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.textAlign = "center";
    ctx.fillText(text, 32, 24);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(material);
    sprite.position.set(position[0], position[1], position[2]);
    sprite.scale.set(0.25, 0.125, 1);
    axesGroup.add(sprite);
  }

  function createPoints() {
    // Clear existing
    while (pointsGroup.children.length > 0) {
      const obj = pointsGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
      pointsGroup.remove(obj);
    }

    const points = model.get("points") || [];
    if (points.length === 0) return;

    const colorField = model.get("color_field");
    const colorScale = model.get("color_scale") || "viridis";
    const colorDomain = model.get("color_domain");
    const sizeField = model.get("size_field");
    const sizeRange = model.get("size_range") || [0.02, 0.1];
    const shapeField = model.get("shape_field");
    const shapeMap = model.get("shape_map") || {};

    // Compute color domain if needed
    let computedColorDomain = colorDomain;
    if (colorField && !colorDomain) {
      const values = points.map(p => p[colorField]).filter(v => typeof v === "number");
      if (values.length > 0) {
        computedColorDomain = [Math.min(...values), Math.max(...values)];
      }
    }

    // Compute size domain if needed
    let sizeDomain = null;
    if (sizeField) {
      const values = points.map(p => p[sizeField]).filter(v => typeof v === "number");
      if (values.length > 0) {
        sizeDomain = [Math.min(...values), Math.max(...values)];
      }
    }

    // Group points by shape for instanced rendering
    const useInstancing = model.get("use_instancing") && points.length > 100;

    if (useInstancing) {
      createInstancedPoints(points, {
        colorField, colorScale, computedColorDomain,
        sizeField, sizeRange, sizeDomain,
        shapeField, shapeMap
      });
    } else {
      createIndividualPoints(points, {
        colorField, colorScale, computedColorDomain,
        sizeField, sizeRange, sizeDomain,
        shapeField, shapeMap
      });
    }
  }

  function getPointColor(point, colorField, colorScale, colorDomain) {
    if (point.color) {
      return new THREE.Color(point.color);
    }
    if (colorField && point[colorField] !== undefined) {
      const value = point[colorField];
      if (typeof value === "number") {
        return getColorFromScale(value, colorScale, colorDomain);
      }
      return getCategoricalColor(value);
    }
    return new THREE.Color(0x6366f1);
  }

  function getPointSize(point, sizeField, sizeRange, sizeDomain) {
    if (point.size !== undefined) {
      return point.size;
    }
    if (sizeField && point[sizeField] !== undefined && sizeDomain) {
      const value = point[sizeField];
      const [min, max] = sizeDomain;
      const t = max > min ? (value - min) / (max - min) : 0.5;
      return sizeRange[0] + t * (sizeRange[1] - sizeRange[0]);
    }
    return sizeRange[0] + (sizeRange[1] - sizeRange[0]) * 0.5;
  }

  function getPointShape(point, shapeField, shapeMap) {
    if (point.shape && SHAPES[point.shape]) {
      return point.shape;
    }
    if (shapeField && point[shapeField] !== undefined) {
      const value = String(point[shapeField]);
      if (shapeMap[value] && SHAPES[shapeMap[value]]) {
        return shapeMap[value];
      }
      // Default shape rotation for unmapped categories
      const shapes = Object.keys(SHAPES);
      return shapes[hashString(value) % shapes.length];
    }
    return "sphere";
  }

  function createIndividualPoints(points, opts) {
    points.forEach((point, idx) => {
      const shape = getPointShape(point, opts.shapeField, opts.shapeMap);
      const geometry = SHAPES[shape]();
      const color = getPointColor(point, opts.colorField, opts.colorScale, opts.computedColorDomain);
      const material = new THREE.MeshPhongMaterial({ color });
      const mesh = new THREE.Mesh(geometry, material);

      const size = getPointSize(point, opts.sizeField, opts.sizeRange, opts.sizeDomain);
      mesh.scale.set(size, size, size);
      mesh.position.set(
        point.x ?? 0,
        point.y ?? 0,
        point.z ?? 0
      );

      mesh.userData = { pointIndex: idx, pointId: point.id || `point_${idx}` };
      pointsGroup.add(mesh);
    });
  }

  function createInstancedPoints(points, opts) {
    // Group by shape
    const groups = {};
    points.forEach((point, idx) => {
      const shape = getPointShape(point, opts.shapeField, opts.shapeMap);
      if (!groups[shape]) groups[shape] = [];
      groups[shape].push({ point, idx });
    });

    for (const [shape, items] of Object.entries(groups)) {
      const geometry = SHAPES[shape]();
      const material = new THREE.MeshPhongMaterial({ vertexColors: false });
      const instancedMesh = new THREE.InstancedMesh(geometry, material, items.length);

      const matrix = new THREE.Matrix4();
      const color = new THREE.Color();
      const colors = new Float32Array(items.length * 3);

      items.forEach(({ point, idx }, i) => {
        const size = getPointSize(point, opts.sizeField, opts.sizeRange, opts.sizeDomain);
        const pointColor = getPointColor(point, opts.colorField, opts.colorScale, opts.computedColorDomain);

        matrix.identity();
        matrix.makeScale(size, size, size);
        matrix.setPosition(point.x ?? 0, point.y ?? 0, point.z ?? 0);
        instancedMesh.setMatrixAt(i, matrix);

        colors[i * 3] = pointColor.r;
        colors[i * 3 + 1] = pointColor.g;
        colors[i * 3 + 2] = pointColor.b;
      });

      // Store color per instance using custom attribute
      geometry.setAttribute("color", new THREE.InstancedBufferAttribute(colors, 3));
      material.vertexColors = true;

      instancedMesh.instanceMatrix.needsUpdate = true;
      instancedMesh.userData = {
        isInstanced: true,
        pointIndices: items.map(({ idx }) => idx),
        pointIds: items.map(({ point, idx }) => point.id || `point_${idx}`)
      };
      pointsGroup.add(instancedMesh);
    }
  }

  function setupRaycaster(container) {
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("click", onClick);
  }

  function onMouseMove(event) {
    const rect = event.target.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pointsGroup.children, true);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const points = model.get("points") || [];
      let pointIndex, pointId;

      if (hit.object.userData.isInstanced) {
        const instanceId = hit.instanceId;
        pointIndex = hit.object.userData.pointIndices[instanceId];
        pointId = hit.object.userData.pointIds[instanceId];
      } else {
        pointIndex = hit.object.userData.pointIndex;
        pointId = hit.object.userData.pointId;
      }

      const point = points[pointIndex];
      if (point && (!hoveredObject || hoveredObject.pointId !== pointId)) {
        hoveredObject = { pointIndex, pointId };
        model.set("hovered_point", point);
        model.save_changes();
        showTooltip(event, point);
      }
    } else if (hoveredObject) {
      hoveredObject = null;
      model.set("hovered_point", null);
      model.save_changes();
      hideTooltip();
    }
  }

  function onClick(event) {
    const rect = event.target.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pointsGroup.children, true);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const points = model.get("points") || [];
      let pointIndex, pointId;

      if (hit.object.userData.isInstanced) {
        const instanceId = hit.instanceId;
        pointIndex = hit.object.userData.pointIndices[instanceId];
        pointId = hit.object.userData.pointIds[instanceId];
      } else {
        pointIndex = hit.object.userData.pointIndex;
        pointId = hit.object.userData.pointId;
      }

      const point = points[pointIndex];
      const selectionMode = model.get("selection_mode") || "click";
      const currentSelection = model.get("selected_points") || [];

      if (selectionMode === "click") {
        model.set("selected_points", [pointId]);
      } else {
        // Toggle in multi-select mode
        if (currentSelection.includes(pointId)) {
          model.set("selected_points", currentSelection.filter(id => id !== pointId));
        } else {
          model.set("selected_points", [...currentSelection, pointId]);
        }
      }
      model.save_changes();
    } else {
      // Click on empty space - clear selection
      model.set("selected_points", []);
      model.save_changes();
    }
  }

  function setupTooltip(container) {
    tooltip = document.createElement("div");
    tooltip.className = "anywidget-vector-tooltip";
    tooltip.style.cssText = `
      position: absolute;
      display: none;
      background: rgba(0, 0, 0, 0.85);
      color: white;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;
      pointer-events: none;
      z-index: 1000;
      max-width: 250px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    `;
    container.appendChild(tooltip);
  }

  function showTooltip(event, point) {
    if (!model.get("show_tooltip")) return;

    const fields = model.get("tooltip_fields") || ["label", "x", "y", "z"];
    let html = "";

    if (point.label) {
      html += `<div style="font-weight: 600; margin-bottom: 4px;">${point.label}</div>`;
    }

    const rows = fields
      .filter(f => f !== "label" && point[f] !== undefined)
      .map(f => {
        let value = point[f];
        if (typeof value === "number") {
          value = value.toFixed(3);
        }
        return `<div style="display: flex; justify-content: space-between; gap: 12px;"><span style="color: #999;">${f}:</span><span>${value}</span></div>`;
      });

    html += rows.join("");
    tooltip.innerHTML = html;
    tooltip.style.display = "block";

    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left + 15;
    const y = event.clientY - rect.top + 15;
    tooltip.style.left = x + "px";
    tooltip.style.top = y + "px";
  }

  function hideTooltip() {
    tooltip.style.display = "none";
  }

  function onCameraChange() {
    model.set("camera_position", [camera.position.x, camera.position.y, camera.position.z]);
    model.set("camera_target", [controls.target.x, controls.target.y, controls.target.z]);
    model.save_changes();
  }

  function bindModelEvents() {
    model.on("change:points", createPoints);
    model.on("change:background", () => {
      scene.background = new THREE.Color(model.get("background"));
    });
    model.on("change:show_axes", setupAxesAndGrid);
    model.on("change:show_grid", setupAxesAndGrid);
    model.on("change:color_field", createPoints);
    model.on("change:color_scale", createPoints);
    model.on("change:color_domain", createPoints);
    model.on("change:size_field", createPoints);
    model.on("change:size_range", createPoints);
    model.on("change:shape_field", createPoints);
    model.on("change:shape_map", createPoints);

    model.on("change:camera_position", () => {
      const pos = model.get("camera_position");
      if (pos) camera.position.set(pos[0], pos[1], pos[2]);
    });
    model.on("change:camera_target", () => {
      const target = model.get("camera_target");
      if (target) controls.target.set(target[0], target[1], target[2]);
    });
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }

  function cleanup() {
    cancelAnimationFrame(animationId);
    controls.dispose();
    renderer.dispose();
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach(m => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });
  }

  return cleanup;
}

export default { render };
"""

_CSS = """
.anywidget-vector {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border-radius: 8px;
  overflow: hidden;
}
.anywidget-vector canvas {
  display: block;
}
"""


class VectorSpace(anywidget.AnyWidget):
    """Interactive 3D vector visualization widget using Three.js."""

    _esm = _ESM
    _css = _CSS

    # Data
    points = traitlets.List(trait=traitlets.Dict()).tag(sync=True)

    # Display
    width = traitlets.Int(default_value=800).tag(sync=True)
    height = traitlets.Int(default_value=600).tag(sync=True)
    background = traitlets.Unicode(default_value="#1a1a2e").tag(sync=True)

    # Axes and grid
    show_axes = traitlets.Bool(default_value=True).tag(sync=True)
    show_grid = traitlets.Bool(default_value=True).tag(sync=True)
    axis_labels = traitlets.Dict(default_value={"x": "X", "y": "Y", "z": "Z"}).tag(sync=True)
    grid_divisions = traitlets.Int(default_value=10).tag(sync=True)

    # Color
    color_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    color_scale = traitlets.Unicode(default_value="viridis").tag(sync=True)
    color_domain = traitlets.List(default_value=None, allow_none=True).tag(sync=True)

    # Size
    size_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    size_range = traitlets.List(default_value=[0.02, 0.1]).tag(sync=True)

    # Shape
    shape_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    shape_map = traitlets.Dict(default_value={}).tag(sync=True)

    # Camera
    camera_position = traitlets.List(default_value=[2, 2, 2]).tag(sync=True)
    camera_target = traitlets.List(default_value=[0, 0, 0]).tag(sync=True)

    # Interaction
    selected_points = traitlets.List(default_value=[]).tag(sync=True)
    hovered_point = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)
    selection_mode = traitlets.Unicode(default_value="click").tag(sync=True)

    # Tooltip
    show_tooltip = traitlets.Bool(default_value=True).tag(sync=True)
    tooltip_fields = traitlets.List(default_value=["label", "x", "y", "z"]).tag(sync=True)

    # Performance
    use_instancing = traitlets.Bool(default_value=True).tag(sync=True)
    point_budget = traitlets.Int(default_value=100000).tag(sync=True)

    def __init__(
        self,
        points: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(points=points or [], **kwargs)
        self._click_callbacks: list[Callable] = []
        self._hover_callbacks: list[Callable] = []
        self._selection_callbacks: list[Callable] = []

    # === Factory Methods ===

    @classmethod
    def from_dict(cls, data: dict[str, Any] | list[dict[str, Any]], **kwargs: Any) -> VectorSpace:
        """Create from dict with 'points' key or list of point dicts."""
        if isinstance(data, dict) and "points" in data:
            points = data["points"]
        elif isinstance(data, list):
            points = data
        else:
            points = [data]
        return cls(points=_normalize_points(points), **kwargs)

    @classmethod
    def from_arrays(
        cls,
        positions: Any,
        *,
        ids: list[str] | None = None,
        colors: Any = None,
        sizes: Any = None,
        labels: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from arrays of positions and optional attributes."""
        pos_list = _to_list(positions)
        n = len(pos_list)

        points = []
        for i in range(n):
            point: dict[str, Any] = {
                "id": ids[i] if ids else f"point_{i}",
                "x": float(pos_list[i][0]),
                "y": float(pos_list[i][1]),
                "z": float(pos_list[i][2]) if len(pos_list[i]) > 2 else 0.0,
            }
            if colors is not None:
                color_list = _to_list(colors)
                point["color"] = color_list[i] if i < len(color_list) else None
            if sizes is not None:
                size_list = _to_list(sizes)
                point["size"] = float(size_list[i]) if i < len(size_list) else None
            if labels is not None and i < len(labels):
                point["label"] = labels[i]
            if metadata is not None and i < len(metadata):
                point.update(metadata[i])
            points.append(point)

        return cls(points=points, **kwargs)

    @classmethod
    def from_numpy(
        cls,
        arr: Any,
        *,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from numpy array (N, 3) or (N, D)."""
        arr_list = _to_list(arr)
        return cls.from_arrays(arr_list, labels=labels, **kwargs)

    @classmethod
    def from_dataframe(
        cls,
        df: Any,
        *,
        x: str = "x",
        y: str = "y",
        z: str = "z",
        id_col: str | None = None,
        color_col: str | None = None,
        size_col: str | None = None,
        shape_col: str | None = None,
        label_col: str | None = None,
        include_cols: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from pandas DataFrame with column mapping."""
        points = []
        for i, row in enumerate(df.to_dict("records")):
            point: dict[str, Any] = {
                "id": str(row[id_col]) if id_col and id_col in row else f"point_{i}",
                "x": float(row[x]) if x in row else 0.0,
                "y": float(row[y]) if y in row else 0.0,
                "z": float(row[z]) if z in row else 0.0,
            }
            if label_col and label_col in row:
                point["label"] = str(row[label_col])
            if color_col and color_col in row:
                point[color_col] = row[color_col]
            if size_col and size_col in row:
                point[size_col] = row[size_col]
            if shape_col and shape_col in row:
                point[shape_col] = row[shape_col]
            if include_cols:
                for col in include_cols:
                    if col in row:
                        point[col] = row[col]
            points.append(point)

        # Auto-set field mappings
        if color_col and "color_field" not in kwargs:
            kwargs["color_field"] = color_col
        if size_col and "size_field" not in kwargs:
            kwargs["size_field"] = size_col
        if shape_col and "shape_field" not in kwargs:
            kwargs["shape_field"] = shape_col

        return cls(points=points, **kwargs)

    # === Vector DB Adapters ===

    @classmethod
    def from_qdrant(
        cls,
        client: Any,
        collection: str,
        *,
        limit: int = 1000,
        with_vectors: bool = True,
        scroll_filter: Any = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from Qdrant collection."""
        records, _ = client.scroll(
            collection_name=collection,
            limit=limit,
            with_vectors=with_vectors,
            scroll_filter=scroll_filter,
        )
        points = []
        for record in records:
            vec = record.vector if hasattr(record, "vector") else None
            point: dict[str, Any] = {"id": str(record.id)}
            if vec and len(vec) >= 3:
                point["x"], point["y"], point["z"] = float(vec[0]), float(vec[1]), float(vec[2])
            if hasattr(record, "payload") and record.payload:
                point.update(record.payload)
            points.append(point)
        return cls(points=points, **kwargs)

    @classmethod
    def from_chroma(
        cls,
        collection: Any,
        *,
        n_results: int = 1000,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from ChromaDB collection."""
        include = include or ["embeddings", "metadatas"]
        result = collection.get(limit=n_results, where=where, include=include)
        points = []
        ids = result.get("ids", [])
        embeddings = result.get("embeddings", [])
        metadatas = result.get("metadatas", [])

        for i, id_ in enumerate(ids):
            point: dict[str, Any] = {"id": str(id_)}
            if embeddings and i < len(embeddings) and embeddings[i]:
                vec = embeddings[i]
                if len(vec) >= 3:
                    point["x"], point["y"], point["z"] = float(vec[0]), float(vec[1]), float(vec[2])
            if metadatas and i < len(metadatas) and metadatas[i]:
                point.update(metadatas[i])
            points.append(point)
        return cls(points=points, **kwargs)

    @classmethod
    def from_lancedb(
        cls,
        table: Any,
        *,
        limit: int = 1000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from LanceDB table."""
        df = table.to_pandas()
        if len(df) > limit:
            df = df.head(limit)
        return cls.from_dataframe(df, **kwargs)

    # === Dimensionality Reduction Adapters ===

    @classmethod
    def from_umap(
        cls,
        embedding: Any,
        *,
        labels: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from UMAP embedding (N, 3)."""
        return cls.from_arrays(embedding, labels=labels, metadata=metadata, **kwargs)

    @classmethod
    def from_tsne(
        cls,
        embedding: Any,
        *,
        labels: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from t-SNE embedding (N, 3)."""
        return cls.from_arrays(embedding, labels=labels, metadata=metadata, **kwargs)

    @classmethod
    def from_pca(
        cls,
        embedding: Any,
        *,
        labels: list[str] | None = None,
        explained_variance: list[float] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from PCA embedding (N, 3) with optional variance info."""
        if explained_variance and len(explained_variance) >= 3:
            kwargs.setdefault(
                "axis_labels",
                {
                    "x": f"PC1 ({explained_variance[0]:.1%})",
                    "y": f"PC2 ({explained_variance[1]:.1%})",
                    "z": f"PC3 ({explained_variance[2]:.1%})",
                },
            )
        return cls.from_arrays(embedding, labels=labels, **kwargs)

    # === Event Callbacks ===

    def on_click(self, callback: Callable[[str, dict[str, Any]], None]) -> Callable:
        """Register callback for point click: callback(point_id, point_data)."""
        self._click_callbacks.append(callback)

        def observer(change: dict[str, Any]) -> None:
            selected = change["new"]
            if selected and len(selected) > 0:
                point_id = selected[-1] if isinstance(selected, list) else selected
                point_data = next((p for p in self.points if p.get("id") == point_id), {})
                for cb in self._click_callbacks:
                    cb(point_id, point_data)

        self.observe(observer, names=["selected_points"])
        return callback

    def on_hover(self, callback: Callable[[str | None, dict[str, Any] | None], None]) -> Callable:
        """Register callback for hover: callback(point_id, point_data)."""
        self._hover_callbacks.append(callback)

        def observer(change: dict[str, Any]) -> None:
            point = change["new"]
            if point:
                for cb in self._hover_callbacks:
                    cb(point.get("id"), point)
            else:
                for cb in self._hover_callbacks:
                    cb(None, None)

        self.observe(observer, names=["hovered_point"])
        return callback

    def on_selection(self, callback: Callable[[list[str], list[dict[str, Any]]], None]) -> Callable:
        """Register callback for selection changes: callback(point_ids, points_data)."""
        self._selection_callbacks.append(callback)

        def observer(change: dict[str, Any]) -> None:
            point_ids = change["new"] or []
            point_data = [p for p in self.points if p.get("id") in point_ids]
            for cb in self._selection_callbacks:
                cb(point_ids, point_data)

        self.observe(observer, names=["selected_points"])
        return callback

    # === Camera Control ===

    def reset_camera(self) -> None:
        """Reset camera to default position."""
        self.camera_position = [2, 2, 2]
        self.camera_target = [0, 0, 0]

    def focus_on(self, point_ids: list[str]) -> None:
        """Focus camera on specific points."""
        if not point_ids:
            return
        matching = [p for p in self.points if p.get("id") in point_ids]
        if not matching:
            return
        cx = sum(p.get("x", 0) for p in matching) / len(matching)
        cy = sum(p.get("y", 0) for p in matching) / len(matching)
        cz = sum(p.get("z", 0) for p in matching) / len(matching)
        self.camera_target = [cx, cy, cz]
        self.camera_position = [cx + 1.5, cy + 1.5, cz + 1.5]

    # === Selection ===

    def select(self, point_ids: list[str]) -> None:
        """Programmatically select points."""
        self.selected_points = point_ids

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_points = []

    # === Export ===

    def to_json(self) -> str:
        """Export points data as JSON."""
        import json

        return json.dumps(self.points)


# === Helper Functions ===


def _normalize_points(data: list[Any]) -> list[dict[str, Any]]:
    """Normalize various point formats to standard dict format."""
    return [_normalize_point(p, i) for i, p in enumerate(data)]


def _normalize_point(point: Any, index: int) -> dict[str, Any]:
    """Convert a single point to standard format."""
    if isinstance(point, dict):
        return _ensure_point_id(point, index)
    if hasattr(point, "__iter__") and hasattr(point, "__len__") and len(point) >= 2:
        return {
            "id": f"point_{index}",
            "x": float(point[0]),
            "y": float(point[1]),
            "z": float(point[2]) if len(point) > 2 else 0.0,
        }
    raise ValueError(f"Cannot normalize point: {point}")


def _ensure_point_id(point: dict[str, Any], index: int) -> dict[str, Any]:
    """Ensure point has an ID."""
    if "id" not in point:
        point = {**point, "id": f"point_{index}"}
    return point


def _to_list(obj: Any) -> list[Any]:
    """Convert numpy arrays or other iterables to lists."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return list(obj)
