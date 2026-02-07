"""Main VectorSpace widget using anywidget and Three.js."""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Any

import anywidget
import traitlets

from anywidget_vector.backends import is_python_backend
from anywidget_vector.backends.chroma.client import execute_query as chroma_query
from anywidget_vector.backends.grafeo.client import execute_query as grafeo_query
from anywidget_vector.backends.lancedb.client import execute_query as lancedb_query
from anywidget_vector.ui import get_css, get_esm

if TYPE_CHECKING:
    pass


class VectorSpace(anywidget.AnyWidget):
    """Interactive 3D vector visualization widget using Three.js.

    Supports multiple vector database backends with native query formats:
    - Qdrant, Pinecone, Weaviate (browser-side REST)
    - Chroma, LanceDB, Grafeo (Python-side)
    """

    _esm = get_esm()
    _css = get_css()

    # === Data ===
    points = traitlets.List(trait=traitlets.Dict()).tag(sync=True)

    # === Display ===
    width = traitlets.Int(default_value=800).tag(sync=True)
    height = traitlets.Int(default_value=600).tag(sync=True)
    background = traitlets.Unicode(default_value="#1a1a2e").tag(sync=True)

    # === Axes and Grid ===
    show_axes = traitlets.Bool(default_value=True).tag(sync=True)
    show_grid = traitlets.Bool(default_value=True).tag(sync=True)
    axis_labels = traitlets.Dict(default_value={"x": "X", "y": "Y", "z": "Z"}).tag(sync=True)
    grid_divisions = traitlets.Int(default_value=10).tag(sync=True)

    # === Color Mapping ===
    color_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    color_scale = traitlets.Unicode(default_value="viridis").tag(sync=True)
    color_domain = traitlets.List(default_value=None, allow_none=True).tag(sync=True)

    # === Size Mapping ===
    size_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    size_range = traitlets.List(default_value=[0.02, 0.1]).tag(sync=True)

    # === Shape Mapping ===
    shape_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    shape_map = traitlets.Dict(default_value={}).tag(sync=True)

    # === Camera ===
    camera_position = traitlets.List(default_value=[2, 2, 2]).tag(sync=True)
    camera_target = traitlets.List(default_value=[0, 0, 0]).tag(sync=True)

    # === Interaction ===
    selected_points = traitlets.List(default_value=[]).tag(sync=True)
    hovered_point = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)
    selection_mode = traitlets.Unicode(default_value="click").tag(sync=True)

    # === Tooltip ===
    show_tooltip = traitlets.Bool(default_value=True).tag(sync=True)
    tooltip_fields = traitlets.List(default_value=["label", "x", "y", "z"]).tag(sync=True)

    # === Performance ===
    use_instancing = traitlets.Bool(default_value=True).tag(sync=True)
    point_budget = traitlets.Int(default_value=100000).tag(sync=True)

    # === Distance and Connections ===
    distance_metric = traitlets.Unicode(default_value="euclidean").tag(sync=True)
    show_connections = traitlets.Bool(default_value=False).tag(sync=True)
    k_neighbors = traitlets.Int(default_value=0).tag(sync=True)
    distance_threshold = traitlets.Float(default_value=None, allow_none=True).tag(sync=True)
    reference_point = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    connection_color = traitlets.Unicode(default_value="#ffffff").tag(sync=True)
    connection_opacity = traitlets.Float(default_value=0.3).tag(sync=True)

    # === UI ===
    show_toolbar = traitlets.Bool(default_value=False).tag(sync=True)
    show_settings = traitlets.Bool(default_value=False).tag(sync=True)
    show_properties = traitlets.Bool(default_value=False).tag(sync=True)

    # === Backend ===
    backend = traitlets.Unicode(default_value="qdrant").tag(sync=True)
    backend_config = traitlets.Dict(default_value={}).tag(sync=True)
    connection_status = traitlets.Unicode(default_value="disconnected").tag(sync=True)

    # === Query (native format per backend) ===
    query_input = traitlets.Unicode(default_value="").tag(sync=True)
    query_error = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    _execute_query = traitlets.Int(default_value=0).tag(sync=True)

    def __init__(self, points: list[dict[str, Any]] | None = None, **kwargs: Any) -> None:
        super().__init__(points=points or [], **kwargs)
        self._backend_client: Any = None
        self.observe(self._on_execute_query, names=["_execute_query"])

    # === Backend Configuration ===

    def set_backend(self, backend: str, client: Any = None, **config: Any) -> VectorSpace:
        """Configure backend for querying.

        Args:
            backend: Backend name (qdrant, pinecone, weaviate, chroma, lancedb, grafeo)
            client: Client object for Python-side backends
            **config: Connection config (url, apiKey, collection, etc.)

        Returns:
            Self for chaining
        """
        self.backend = backend
        self._backend_client = client
        self.backend_config = config
        self.show_toolbar = True
        self.show_settings = True
        return self

    def _on_execute_query(self, change: dict[str, Any]) -> None:
        """Handle query execution for Python-side backends."""
        if change["new"] == 0 or not is_python_backend(self.backend):
            return
        try:
            self.connection_status = "connecting"
            results = self._execute_python_query()
            if results:
                self.points = results
                self.connection_status = "connected"
        except Exception as e:
            self.query_error = str(e)
            self.connection_status = "error"

    def _execute_python_query(self) -> list[dict[str, Any]]:
        """Execute query using Python-side backend."""
        if not self._backend_client:
            raise ValueError("Backend not configured. Call set_backend() first.")

        query = self.query_input

        if self.backend == "chroma":
            return chroma_query(self._backend_client, query)
        elif self.backend == "lancedb":
            return lancedb_query(self._backend_client, query)
        elif self.backend == "grafeo":
            return grafeo_query(self._backend_client, query)

        raise ValueError(f"Unknown Python backend: {self.backend}")

    # === Event Decorators ===

    def on_click(self, callback: Any) -> Any:
        """Register a click handler.

        The callback receives (point_id, point_data) when a point is clicked.
        """

        def _handler(change: dict[str, Any]) -> None:
            points = change["new"]
            if points and len(points) == 1:
                pid = points[0]
                pdata = next((p for p in self.points if p.get("id") == pid), {})
                callback(pid, pdata)

        self.observe(_handler, names=["selected_points"])
        return callback

    def on_hover(self, callback: Any) -> Any:
        """Register a hover handler.

        The callback receives (point_id, point_data) on hover, or (None, None) on leave.
        """

        def _handler(change: dict[str, Any]) -> None:
            point = change["new"]
            if point:
                callback(point.get("id"), point)
            else:
                callback(None, None)

        self.observe(_handler, names=["hovered_point"])
        return callback

    def on_selection(self, callback: Any) -> Any:
        """Register a selection handler.

        The callback receives (point_ids, points_data) when selection changes.
        """

        def _handler(change: dict[str, Any]) -> None:
            pids = change["new"]
            pdata = [p for p in self.points if p.get("id") in set(pids)]
            callback(pids, pdata)

        self.observe(_handler, names=["selected_points"])
        return callback

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
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from arrays of positions."""
        pos_list = _to_list(positions)
        points = []
        for i, p in enumerate(pos_list):
            point = {
                "id": ids[i] if ids else f"point_{i}",
                "x": float(p[0]),
                "y": float(p[1]),
                "z": float(p[2]) if len(p) > 2 else 0.0,
            }
            if labels:
                point["label"] = labels[i]
            points.append(point)
        return cls(points=points, **kwargs)

    @classmethod
    def from_numpy(
        cls,
        positions: Any,
        *,
        ids: list[str] | None = None,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from NumPy array of shape (N, 2) or (N, 3)."""
        return cls.from_arrays(positions, ids=ids, labels=labels, **kwargs)

    @classmethod
    def from_umap(
        cls,
        embedding: Any,
        *,
        ids: list[str] | None = None,
        labels: list[str] | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from UMAP, t-SNE, or PCA embedding array of shape (N, 2) or (N, 3)."""
        return cls.from_arrays(embedding, ids=ids, labels=labels, **kwargs)

    @classmethod
    def from_dataframe(
        cls,
        df: Any,
        *,
        x: str = "x",
        y: str = "y",
        z: str = "z",
        color_col: str | None = None,
        size_col: str | None = None,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from pandas DataFrame.

        Args:
            df: pandas DataFrame with coordinate columns.
            x: Column name for x coordinate.
            y: Column name for y coordinate.
            z: Column name for z coordinate.
            color_col: Column to use for color mapping.
            size_col: Column to use for size mapping.
            **kwargs: Additional widget options.
        """
        if color_col:
            kwargs.setdefault("color_field", color_col)
        if size_col:
            kwargs.setdefault("size_field", size_col)
        points = [
            {"id": f"point_{i}", "x": float(row[x]), "y": float(row[y]), "z": float(row.get(z, 0)), **row}
            for i, row in enumerate(df.to_dict("records"))
        ]
        return cls(points=points, **kwargs)

    @classmethod
    def from_qdrant(
        cls,
        client: Any,
        collection: str,
        *,
        limit: int = 5000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from a Qdrant collection.

        Args:
            client: qdrant_client.QdrantClient instance.
            collection: Collection name.
            limit: Maximum number of points to fetch.
            **kwargs: Additional widget options.
        """
        records, _ = client.scroll(collection, limit=limit, with_vectors=True)
        points = []
        for r in records:
            point: dict[str, Any] = {"id": str(r.id)}
            vec = r.vector
            if vec:
                point["x"] = float(vec[0]) if len(vec) > 0 else 0.0
                point["y"] = float(vec[1]) if len(vec) > 1 else 0.0
                point["z"] = float(vec[2]) if len(vec) > 2 else 0.0
                point["vector"] = list(vec)
            if r.payload:
                point.update(r.payload)
            points.append(point)
        return cls(points=points, **kwargs)

    @classmethod
    def from_chroma(
        cls,
        collection: Any,
        *,
        limit: int = 5000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from a ChromaDB collection.

        Args:
            collection: chromadb Collection object.
            limit: Maximum number of points to fetch.
            **kwargs: Additional widget options.
        """
        from anywidget_vector.backends.chroma.converter import to_points

        response = collection.get(
            limit=limit,
            include=["embeddings", "metadatas", "documents"],
        )
        return cls(points=to_points(response), **kwargs)

    # === Distance Methods ===

    def compute_distances(
        self,
        reference_id: str,
        metric: str | None = None,
        vector_field: str | None = None,
    ) -> dict[str, float]:
        """Compute distances from reference point to all others.

        Args:
            reference_id: ID of the reference point.
            metric: Distance metric (euclidean, cosine, manhattan, dot_product).
            vector_field: Use a high-dimensional vector field instead of x/y/z.
        """
        metric = metric or self.distance_metric
        ref = next((p for p in self.points if p.get("id") == reference_id), None)
        if not ref:
            return {}
        return {
            p.get("id"): self._distance(ref, p, metric, vector_field)
            for p in self.points
            if p.get("id") != reference_id
        }

    def find_neighbors(
        self, reference_id: str, k: int | None = None, threshold: float | None = None
    ) -> list[tuple[str, float]]:
        """Find nearest neighbors of a reference point."""
        distances = sorted(self.compute_distances(reference_id).items(), key=lambda x: x[1])
        if threshold is not None:
            return [(pid, d) for pid, d in distances if d <= threshold]
        return distances[:k] if k else distances

    def color_by_distance(self, reference_id: str, metric: str | None = None) -> None:
        """Color points by distance from reference."""
        distances = self.compute_distances(reference_id, metric=metric)
        self.points = [{**p, "_distance": distances.get(p.get("id"), 0)} for p in self.points]
        self.color_field = "_distance"
        self.reference_point = reference_id

    def show_neighbors(self, reference_id: str, k: int | None = None, threshold: float | None = None) -> None:
        """Show connections to nearest neighbors."""
        self.reference_point = reference_id
        self.show_connections = True
        if k:
            self.k_neighbors = k
        if threshold:
            self.distance_threshold = threshold

    def _distance(self, p1: dict, p2: dict, metric: str, vector_field: str | None = None) -> float:
        """Compute distance between two points."""
        if vector_field:
            v1 = p1.get(vector_field, [])
            v2 = p2.get(vector_field, [])
            n = min(len(v1), len(v2))
            if n == 0:
                return float("inf")
        else:
            v1 = [p1.get("x", 0), p1.get("y", 0), p1.get("z", 0)]
            v2 = [p2.get("x", 0), p2.get("y", 0), p2.get("z", 0)]
            n = 3

        if metric == "euclidean":
            return math.sqrt(sum((v1[i] - v2[i]) ** 2 for i in range(n)))
        elif metric == "cosine":
            dot = sum(v1[i] * v2[i] for i in range(n))
            m1 = math.sqrt(sum(v1[i] ** 2 for i in range(n)))
            m2 = math.sqrt(sum(v2[i] ** 2 for i in range(n)))
            return 1 - (dot / (m1 * m2)) if m1 and m2 else 1.0
        elif metric == "manhattan":
            return sum(abs(v1[i] - v2[i]) for i in range(n))
        elif metric == "dot_product":
            return -sum(v1[i] * v2[i] for i in range(n))
        return math.sqrt(sum((v1[i] - v2[i]) ** 2 for i in range(n)))

    # === Camera ===

    # === Selection ===

    def select(self, point_ids: list[str]) -> None:
        """Programmatically select points by ID."""
        self.selected_points = point_ids

    def clear_selection(self) -> None:
        """Clear all selected points."""
        self.selected_points = []

    # === Camera ===

    def reset_camera(self) -> None:
        """Reset camera to default."""
        self.camera_position = [2, 2, 2]
        self.camera_target = [0, 0, 0]

    def focus_on(self, point_ids: list[str]) -> None:
        """Focus camera on specific points."""
        pts = [p for p in self.points if p.get("id") in point_ids]
        if pts:
            cx = sum(p.get("x", 0) for p in pts) / len(pts)
            cy = sum(p.get("y", 0) for p in pts) / len(pts)
            cz = sum(p.get("z", 0) for p in pts) / len(pts)
            self.camera_target = [cx, cy, cz]
            self.camera_position = [cx + 1.5, cy + 1.5, cz + 1.5]

    # === Export ===

    def to_json(self) -> str:
        """Export points as JSON."""
        return json.dumps(self.points)


# === Helper Functions ===


def _normalize_points(data: list[Any]) -> list[dict[str, Any]]:
    """Normalize various point formats to standard dict format."""
    return [_normalize_point(p, i) for i, p in enumerate(data)]


def _normalize_point(point: Any, index: int) -> dict[str, Any]:
    """Convert a single point to standard format."""
    if isinstance(point, dict):
        if "id" not in point:
            point = {**point, "id": f"point_{index}"}
        return point
    if hasattr(point, "__iter__") and hasattr(point, "__len__") and len(point) >= 2:
        return {
            "id": f"point_{index}",
            "x": float(point[0]),
            "y": float(point[1]),
            "z": float(point[2]) if len(point) > 2 else 0.0,
        }
    raise ValueError(f"Cannot normalize point: {point}")


def _to_list(obj: Any) -> list[Any]:
    """Convert numpy arrays or other iterables to lists."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return list(obj)
