// 3D Canvas component using Three.js
import * as THREE from "https://esm.sh/three@0.160.0";
import { OrbitControls } from "https://esm.sh/three@0.160.0/addons/controls/OrbitControls.js";
import { COLOR_SCALES, CATEGORICAL_COLORS } from "./constants.js";

// Shape geometries factory
const SHAPE_GEOMETRIES = {
  sphere: () => new THREE.SphereGeometry(1, 16, 16),
  cube: () => new THREE.BoxGeometry(1, 1, 1),
  cone: () => new THREE.ConeGeometry(0.7, 1.4, 16),
  tetrahedron: () => new THREE.TetrahedronGeometry(1),
  octahedron: () => new THREE.OctahedronGeometry(1),
  cylinder: () => new THREE.CylinderGeometry(0.5, 0.5, 1, 16),
};

// Distance metrics
const DISTANCE_METRICS = {
  euclidean: (a, b) => {
    const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return Math.sqrt(dx*dx + dy*dy + dz*dz);
  },
  cosine: (a, b) => {
    const dot = a.x*b.x + a.y*b.y + a.z*b.z;
    const magA = Math.sqrt(a.x*a.x + a.y*a.y + a.z*a.z);
    const magB = Math.sqrt(b.x*b.x + b.y*b.y + b.z*b.z);
    if (magA === 0 || magB === 0) return 1;
    return 1 - (dot / (magA * magB));
  },
  manhattan: (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y) + Math.abs(a.z - b.z),
  dot_product: (a, b) => -(a.x*b.x + a.y*b.y + a.z*b.z),
};

export function createCanvas(model, container, callbacks) {
  let scene, camera, renderer, controls;
  let pointsGroup, connectionsGroup;
  let raycaster, mouse;
  let hoveredObject = null;
  let tooltip;
  let axesGroup, gridHelper;
  let animationId;
  let resizeObserver;
  let selectionRect, boxOverlay;
  let currentMode = model.get("selection_mode") || "click";

  init();
  animate();

  function init() {
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

    // ResizeObserver for responsive sizing
    resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
      }
    });
    resizeObserver.observe(container);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    const target = model.get("camera_target") || [0, 0, 0];
    controls.target.set(target[0], target[1], target[2]);
    controls.addEventListener("change", onCameraChange);

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(5, 10, 7);
    scene.add(directional);

    // Groups
    pointsGroup = new THREE.Group();
    scene.add(pointsGroup);
    connectionsGroup = new THREE.Group();
    scene.add(connectionsGroup);
    axesGroup = new THREE.Group();
    scene.add(axesGroup);

    // Setup
    setupAxesAndGrid();
    setupRaycaster();
    setupTooltip();
    setupZoomControls();
    setupModeControls();
    setupBoxSelection();
    createPoints();
    createConnections();
    bindModelEvents();
  }

  function setupAxesAndGrid() {
    while (axesGroup.children.length > 0) axesGroup.remove(axesGroup.children[0]);
    if (gridHelper) { scene.remove(gridHelper); gridHelper = null; }

    if (model.get("show_axes")) {
      const axes = new THREE.AxesHelper(1.2);
      axesGroup.add(axes);
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
    canvas.width = 64; canvas.height = 32;
    ctx.font = "bold 24px Arial";
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.textAlign = "center";
    ctx.fillText(text, 32, 24);
    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture }));
    sprite.position.set(position[0], position[1], position[2]);
    sprite.scale.set(0.25, 0.125, 1);
    axesGroup.add(sprite);
  }

  function createPoints() {
    while (pointsGroup.children.length > 0) {
      const obj = pointsGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
      pointsGroup.remove(obj);
    }

    const points = model.get("points") || [];
    if (points.length === 0) return;

    const opts = {
      colorField: model.get("color_field"),
      colorScale: model.get("color_scale") || "viridis",
      colorDomain: model.get("color_domain"),
      sizeField: model.get("size_field"),
      sizeRange: model.get("size_range") || [0.02, 0.1],
      shapeField: model.get("shape_field"),
      shapeMap: model.get("shape_map") || {},
    };

    // Compute domains
    if (opts.colorField && !opts.colorDomain) {
      const values = points.map(p => p[opts.colorField]).filter(v => typeof v === "number");
      if (values.length > 0) opts.colorDomain = [Math.min(...values), Math.max(...values)];
    }
    if (opts.sizeField) {
      const values = points.map(p => p[opts.sizeField]).filter(v => typeof v === "number");
      if (values.length > 0) opts.sizeDomain = [Math.min(...values), Math.max(...values)];
    }

    const useInstancing = model.get("use_instancing") && points.length > 100;
    if (useInstancing) {
      createInstancedPoints(points, opts);
    } else {
      createIndividualPoints(points, opts);
    }
  }

  function getPointColor(point, opts) {
    if (point.color) return new THREE.Color(point.color);
    if (opts.colorField && point[opts.colorField] !== undefined) {
      const value = point[opts.colorField];
      if (typeof value === "number") {
        return getColorFromScale(value, opts.colorScale, opts.colorDomain);
      }
      return getCategoricalColor(value);
    }
    return new THREE.Color(0x6366f1);
  }

  function getPointSize(point, opts) {
    if (point.size !== undefined) return point.size;
    if (opts.sizeField && point[opts.sizeField] !== undefined && opts.sizeDomain) {
      const [min, max] = opts.sizeDomain;
      const t = max > min ? (point[opts.sizeField] - min) / (max - min) : 0.5;
      return opts.sizeRange[0] + t * (opts.sizeRange[1] - opts.sizeRange[0]);
    }
    return (opts.sizeRange[0] + opts.sizeRange[1]) * 0.5;
  }

  function getPointShape(point, opts) {
    if (point.shape && SHAPE_GEOMETRIES[point.shape]) return point.shape;
    if (opts.shapeField && point[opts.shapeField] !== undefined) {
      const value = String(point[opts.shapeField]);
      if (opts.shapeMap[value] && SHAPE_GEOMETRIES[opts.shapeMap[value]]) return opts.shapeMap[value];
      const shapes = Object.keys(SHAPE_GEOMETRIES);
      return shapes[hashString(value) % shapes.length];
    }
    return "sphere";
  }

  function createIndividualPoints(points, opts) {
    points.forEach((point, idx) => {
      const shape = getPointShape(point, opts);
      const geometry = SHAPE_GEOMETRIES[shape]();
      const color = getPointColor(point, opts);
      const material = new THREE.MeshPhongMaterial({ color });
      const mesh = new THREE.Mesh(geometry, material);
      const size = getPointSize(point, opts);
      mesh.scale.set(size, size, size);
      mesh.position.set(point.x ?? 0, point.y ?? 0, point.z ?? 0);
      mesh.userData = { pointIndex: idx, pointId: point.id || `point_${idx}` };
      pointsGroup.add(mesh);
    });
  }

  function createInstancedPoints(points, opts) {
    const groups = {};
    points.forEach((point, idx) => {
      const shape = getPointShape(point, opts);
      if (!groups[shape]) groups[shape] = [];
      groups[shape].push({ point, idx });
    });

    for (const [shape, items] of Object.entries(groups)) {
      const geometry = SHAPE_GEOMETRIES[shape]();
      const material = new THREE.MeshPhongMaterial({ vertexColors: false });
      const instancedMesh = new THREE.InstancedMesh(geometry, material, items.length);
      const matrix = new THREE.Matrix4();
      const colors = new Float32Array(items.length * 3);

      items.forEach(({ point, idx }, i) => {
        const size = getPointSize(point, opts);
        const pointColor = getPointColor(point, opts);
        matrix.identity();
        matrix.makeScale(size, size, size);
        matrix.setPosition(point.x ?? 0, point.y ?? 0, point.z ?? 0);
        instancedMesh.setMatrixAt(i, matrix);
        colors[i * 3] = pointColor.r;
        colors[i * 3 + 1] = pointColor.g;
        colors[i * 3 + 2] = pointColor.b;
      });

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

  function createConnections() {
    while (connectionsGroup.children.length > 0) {
      const obj = connectionsGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
      connectionsGroup.remove(obj);
    }

    const points = model.get("points") || [];
    const showConnections = model.get("show_connections");
    if (!showConnections || points.length < 2) return;

    const kNeighbors = model.get("k_neighbors") || 0;
    const distanceThreshold = model.get("distance_threshold");
    const referencePoint = model.get("reference_point");
    const distanceMetric = model.get("distance_metric") || "euclidean";
    const connectionColor = model.get("connection_color") || "#ffffff";
    const connectionOpacity = model.get("connection_opacity") || 0.3;

    const material = new THREE.LineBasicMaterial({
      color: new THREE.Color(connectionColor),
      transparent: true,
      opacity: connectionOpacity,
    });

    const computeDist = (p1, p2) => {
      const fn = DISTANCE_METRICS[distanceMetric] || DISTANCE_METRICS.euclidean;
      return fn(p1, p2);
    };

    if (referencePoint) {
      const refIdx = points.findIndex(p => p.id === referencePoint);
      if (refIdx === -1) return;
      const ref = points[refIdx];
      const distances = points.map((p, i) => ({
        idx: i, point: p,
        dist: i === refIdx ? Infinity : computeDist(ref, p)
      })).filter(d => d.dist !== Infinity).sort((a, b) => a.dist - b.dist);

      let neighbors;
      if (distanceThreshold != null) neighbors = distances.filter(d => d.dist <= distanceThreshold);
      else if (kNeighbors > 0) neighbors = distances.slice(0, kNeighbors);
      else return;

      neighbors.forEach(n => {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array([
          ref.x ?? 0, ref.y ?? 0, ref.z ?? 0,
          n.point.x ?? 0, n.point.y ?? 0, n.point.z ?? 0
        ]), 3));
        connectionsGroup.add(new THREE.Line(geometry, material));
      });
    } else if (kNeighbors > 0) {
      points.forEach((p, i) => {
        const distances = points.map((other, j) => ({
          idx: j, point: other,
          dist: i === j ? Infinity : computeDist(p, other)
        })).filter(d => d.dist !== Infinity).sort((a, b) => a.dist - b.dist).slice(0, kNeighbors);

        distances.forEach(n => {
          if (i < n.idx) {
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array([
              p.x ?? 0, p.y ?? 0, p.z ?? 0,
              n.point.x ?? 0, n.point.y ?? 0, n.point.z ?? 0
            ]), 3));
            connectionsGroup.add(new THREE.Line(geometry, material));
          }
        });
      });
    }
  }

  function setupRaycaster() {
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("click", onClick);
  }

  function onMouseMove(event) {
    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pointsGroup.children, true);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const points = model.get("points") || [];
      let pointIndex, pointId;

      if (hit.object.userData.isInstanced) {
        pointIndex = hit.object.userData.pointIndices[hit.instanceId];
        pointId = hit.object.userData.pointIds[hit.instanceId];
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
    // Box mode handles selection via the overlay, not raycaster clicks
    if (currentMode === "box") return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pointsGroup.children, true);

    if (intersects.length > 0) {
      const hit = intersects[0];
      let pointId;
      if (hit.object.userData.isInstanced) {
        pointId = hit.object.userData.pointIds[hit.instanceId];
      } else {
        pointId = hit.object.userData.pointId;
      }

      const selectionMode = model.get("selection_mode") || "click";
      const currentSelection = model.get("selected_points") || [];

      if (selectionMode === "click") {
        model.set("selected_points", [pointId]);
      } else if (selectionMode === "multi") {
        if (currentSelection.includes(pointId)) {
          model.set("selected_points", currentSelection.filter(id => id !== pointId));
        } else {
          model.set("selected_points", [...currentSelection, pointId]);
        }
      }
      model.save_changes();
    } else {
      model.set("selected_points", []);
      model.save_changes();
    }
  }

  function setupTooltip() {
    tooltip = document.createElement("div");
    tooltip.className = "avs-tooltip";
    container.appendChild(tooltip);
  }

  function setupZoomControls() {
    const zoomControls = document.createElement("div");
    zoomControls.className = "avs-zoom-controls";

    const zoomInBtn = document.createElement("button");
    zoomInBtn.className = "avs-zoom-btn";
    zoomInBtn.innerHTML = ICONS.zoomIn;
    zoomInBtn.title = "Zoom in";
    zoomInBtn.addEventListener("click", () => {
      camera.position.lerp(controls.target, 0.3);
      controls.update();
    });

    const zoomOutBtn = document.createElement("button");
    zoomOutBtn.className = "avs-zoom-btn";
    zoomOutBtn.innerHTML = ICONS.zoomOut;
    zoomOutBtn.title = "Zoom out";
    zoomOutBtn.addEventListener("click", () => {
      const dir = camera.position.clone().sub(controls.target).normalize();
      camera.position.add(dir.multiplyScalar(0.5));
      controls.update();
    });

    const zoomFitBtn = document.createElement("button");
    zoomFitBtn.className = "avs-zoom-btn";
    zoomFitBtn.innerHTML = ICONS.zoomFit;
    zoomFitBtn.title = "Fit to view";
    zoomFitBtn.addEventListener("click", () => {
      const points = model.get("points") || [];
      if (points.length === 0) return;
      const box = new THREE.Box3();
      points.forEach(p => box.expandByPoint(new THREE.Vector3(p.x ?? 0, p.y ?? 0, p.z ?? 0)));
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3()).length();
      const distance = size / (2 * Math.tan(Math.PI * camera.fov / 360));
      controls.target.copy(center);
      camera.position.copy(center.clone().add(new THREE.Vector3(0, 0, distance * 1.2)));
      controls.update();
    });

    zoomControls.appendChild(zoomInBtn);
    zoomControls.appendChild(zoomOutBtn);
    zoomControls.appendChild(zoomFitBtn);
    container.appendChild(zoomControls);
  }

  function setupModeControls() {
    const modeGroup = document.createElement("div");
    modeGroup.className = "avs-mode-group";

    const clickBtn = document.createElement("button");
    clickBtn.className = "avs-mode-btn avs-mode-active";
    clickBtn.innerHTML = ICONS.cursor;
    clickBtn.title = "Click / multi-select mode";
    clickBtn.dataset.mode = "click";

    const boxBtn = document.createElement("button");
    boxBtn.className = "avs-mode-btn";
    boxBtn.innerHTML = ICONS.boxSelect;
    boxBtn.title = "Box select mode";
    boxBtn.dataset.mode = "box";

    function setActiveMode(mode) {
      currentMode = mode;
      model.set("selection_mode", mode === "box" ? "box" : "click");
      model.save_changes();

      clickBtn.classList.toggle("avs-mode-active", mode !== "box");
      boxBtn.classList.toggle("avs-mode-active", mode === "box");

      // Toggle orbit controls: disabled in box mode so drag draws the rectangle
      controls.enabled = (mode !== "box");

      // Show/hide box overlay
      if (boxOverlay) {
        boxOverlay.style.display = (mode === "box") ? "block" : "none";
      }
    }

    clickBtn.addEventListener("click", () => setActiveMode("click"));
    boxBtn.addEventListener("click", () => setActiveMode("box"));

    modeGroup.appendChild(clickBtn);
    modeGroup.appendChild(boxBtn);
    container.appendChild(modeGroup);

    // Sync with model changes from Python side
    model.on("change:selection_mode", () => {
      const mode = model.get("selection_mode") || "click";
      if (mode !== currentMode) setActiveMode(mode);
    });
  }

  function setupBoxSelection() {
    // Transparent overlay that captures mouse events in box mode
    boxOverlay = document.createElement("div");
    boxOverlay.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;z-index:15;display:none;cursor:crosshair;";
    container.appendChild(boxOverlay);

    // Visual selection rectangle
    selectionRect = document.createElement("div");
    selectionRect.className = "avs-selection-rect";
    container.appendChild(selectionRect);

    let dragging = false;
    let startX = 0, startY = 0;

    boxOverlay.addEventListener("mousedown", (e) => {
      if (currentMode !== "box") return;
      e.preventDefault();
      dragging = true;
      const rect = container.getBoundingClientRect();
      startX = e.clientX - rect.left;
      startY = e.clientY - rect.top;
      selectionRect.style.left = startX + "px";
      selectionRect.style.top = startY + "px";
      selectionRect.style.width = "0px";
      selectionRect.style.height = "0px";
      selectionRect.style.display = "block";
    });

    boxOverlay.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const rect = container.getBoundingClientRect();
      const curX = e.clientX - rect.left;
      const curY = e.clientY - rect.top;
      const x = Math.min(startX, curX);
      const y = Math.min(startY, curY);
      const w = Math.abs(curX - startX);
      const h = Math.abs(curY - startY);
      selectionRect.style.left = x + "px";
      selectionRect.style.top = y + "px";
      selectionRect.style.width = w + "px";
      selectionRect.style.height = h + "px";
    });

    boxOverlay.addEventListener("mouseup", (e) => {
      if (!dragging) return;
      dragging = false;
      selectionRect.style.display = "none";

      const rect = container.getBoundingClientRect();
      const endX = e.clientX - rect.left;
      const endY = e.clientY - rect.top;

      const x1 = Math.min(startX, endX);
      const y1 = Math.min(startY, endY);
      const x2 = Math.max(startX, endX);
      const y2 = Math.max(startY, endY);

      // Ignore tiny drags (likely accidental clicks)
      if (x2 - x1 < 4 && y2 - y1 < 4) return;

      const selectedIds = getPointsInScreenRect(
        camera, model.get("points") || [],
        { x1, y1, x2, y2 },
        rect.width, rect.height
      );
      model.set("selected_points", selectedIds);
      model.save_changes();
    });
  }

  function getPointsInScreenRect(cam, points, rect, canvasWidth, canvasHeight) {
    const { x1, y1, x2, y2 } = rect;
    const selected = [];
    points.forEach(p => {
      const pos = new THREE.Vector3(p.x ?? 0, p.y ?? 0, p.z ?? 0).project(cam);
      const sx = (pos.x * 0.5 + 0.5) * canvasWidth;
      const sy = (-pos.y * 0.5 + 0.5) * canvasHeight;
      if (sx >= x1 && sx <= x2 && sy >= y1 && sy <= y2) {
        selected.push(p.id || `point_${points.indexOf(p)}`);
      }
    });
    return selected;
  }

  function showTooltip(event, point) {
    if (!model.get("show_tooltip")) return;
    const fields = model.get("tooltip_fields") || ["label", "x", "y", "z"];
    let html = "";
    if (point.label) html += `<div class="avs-tooltip-label">${point.label}</div>`;
    fields.filter(f => f !== "label" && point[f] !== undefined).forEach(f => {
      let value = point[f];
      if (typeof value === "number") value = value.toFixed(3);
      html += `<div class="avs-tooltip-row"><span class="avs-tooltip-key">${f}:</span><span>${value}</span></div>`;
    });
    tooltip.innerHTML = html;
    tooltip.style.display = "block";
    const rect = container.getBoundingClientRect();
    tooltip.style.left = (event.clientX - rect.left + 15) + "px";
    tooltip.style.top = (event.clientY - rect.top + 15) + "px";
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
    model.on("change:points", () => { createPoints(); createConnections(); });
    model.on("change:background", () => { scene.background = new THREE.Color(model.get("background")); });
    model.on("change:show_axes", setupAxesAndGrid);
    model.on("change:show_grid", setupAxesAndGrid);
    model.on("change:color_field", createPoints);
    model.on("change:color_scale", createPoints);
    model.on("change:color_domain", createPoints);
    model.on("change:size_field", createPoints);
    model.on("change:size_range", createPoints);
    model.on("change:shape_field", createPoints);
    model.on("change:shape_map", createPoints);
    model.on("change:show_connections", createConnections);
    model.on("change:k_neighbors", createConnections);
    model.on("change:distance_threshold", createConnections);
    model.on("change:reference_point", createConnections);
    model.on("change:distance_metric", createConnections);
    model.on("change:connection_color", createConnections);
    model.on("change:connection_opacity", createConnections);
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
    resizeObserver.disconnect();
    controls.dispose();
    renderer.dispose();
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }
    });
  }

  function applyFilter(filterText) {
    const points = model.get("points") || [];
    const filter = (filterText || "").toLowerCase().trim();
    const total = points.length;

    if (!filter) {
      // Reset all to full opacity
      pointsGroup.children.forEach(obj => {
        if (obj.userData.isInstanced) {
          // Restore original colors from stored data
          if (obj.userData._originalColors) {
            const attr = obj.geometry.getAttribute("color");
            attr.array.set(obj.userData._originalColors);
            attr.needsUpdate = true;
          }
        } else if (obj.material) {
          obj.material.opacity = 1;
          obj.material.transparent = false;
          obj.material.needsUpdate = true;
        }
      });
      return { matched: total, total };
    }

    let matched = 0;
    // Build match set from points data
    const matchSet = new Set();
    points.forEach((point, idx) => {
      if (pointMatchesFilter(point, filter)) {
        matchSet.add(idx);
        matched++;
      }
    });

    pointsGroup.children.forEach(obj => {
      if (obj.userData.isInstanced) {
        // Dim non-matching instances by darkening their color
        const indices = obj.userData.pointIndices;
        const attr = obj.geometry.getAttribute("color");
        if (!obj.userData._originalColors) {
          obj.userData._originalColors = new Float32Array(attr.array);
        }
        for (let i = 0; i < indices.length; i++) {
          const matches = matchSet.has(indices[i]);
          const dim = matches ? 1.0 : 0.12;
          attr.array[i * 3] = obj.userData._originalColors[i * 3] * dim;
          attr.array[i * 3 + 1] = obj.userData._originalColors[i * 3 + 1] * dim;
          attr.array[i * 3 + 2] = obj.userData._originalColors[i * 3 + 2] * dim;
        }
        attr.needsUpdate = true;
      } else if (obj.material) {
        const idx = obj.userData.pointIndex;
        const matches = matchSet.has(idx);
        obj.material.transparent = !matches;
        obj.material.opacity = matches ? 1.0 : 0.12;
        obj.material.needsUpdate = true;
      }
    });

    return { matched, total };
  }

  return { cleanup, applyFilter };
}

function pointMatchesFilter(point, filter) {
  for (const [key, val] of Object.entries(point)) {
    if (key === "x" || key === "y" || key === "z" || key === "vector") continue;
    if (val != null && String(val).toLowerCase().includes(filter)) return true;
  }
  return false;
}

// Helper functions
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
