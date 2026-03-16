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
    # width=0 means "auto" (fill container). height=0 means "match width" (1:1 ratio).
    width = traitlets.Int(default_value=0).tag(sync=True)
    height = traitlets.Int(default_value=0).tag(sync=True)
    background = traitlets.Unicode(default_value="#1a1a2e").tag(sync=True)

    # === Theme ===
    dark_mode = traitlets.Bool(default_value=True).tag(sync=True)

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
    size_range = traitlets.List(default_value=[0.02, 0.06]).tag(sync=True)

    # === Shape Mapping ===
    shape_field = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    shape_map = traitlets.Dict(default_value={}).tag(sync=True)

    # === Camera ===
    camera_position = traitlets.List(default_value=[2, 2, 2]).tag(sync=True)
    camera_target = traitlets.List(default_value=[0, 0, 0]).tag(sync=True)

    # === Interaction ===
    selected_points = traitlets.List(default_value=[]).tag(sync=True)
    _selection_version = traitlets.Int(default_value=0).tag(sync=True)
    hovered_point = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)
    selection_mode = traitlets.CaselessStrEnum(values=["click", "multi", "box", "lasso"], default_value="click").tag(
        sync=True
    )

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
    show_toolbar = traitlets.Bool(default_value=True).tag(sync=True)
    show_settings = traitlets.Bool(default_value=True).tag(sync=True)
    show_properties = traitlets.Bool(default_value=True).tag(sync=True)

    # === Backend ===
    backend = traitlets.Unicode(default_value="grafeo").tag(sync=True)

    # === Grafeo Connection Mode ===
    grafeo_connection_mode = traitlets.Unicode(default_value="embedded").tag(sync=True)
    grafeo_server_url = traitlets.Unicode(default_value="http://localhost:7474").tag(sync=True)
    backend_config = traitlets.Dict(default_value={}).tag(sync=True)
    connection_status = traitlets.Unicode(default_value="disconnected").tag(sync=True)

    # === Query (native format per backend) ===
    query_input = traitlets.Unicode(default_value="").tag(sync=True)
    query_error = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    _execute_query = traitlets.Int(default_value=0).tag(sync=True)

    # === Demo Mode (auto-populate WASM and run query) ===
    _demo_mode = traitlets.Bool(default_value=False).tag(sync=True)
    _demo_data = traitlets.Unicode(default_value="").tag(sync=True)

    def __init__(self, points: list[dict[str, Any]] | None = None, **kwargs: Any) -> None:
        super().__init__(points=points or [], **kwargs)
        self._backend_client: Any = None
        self._vectors: Any = None  # High-dim vectors for projection (numpy array, not synced to JS)
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

    # === Add Points ===

    def add_points(self, data: list[dict[str, Any]]) -> VectorSpace:
        """Append point dicts to the existing points.

        Args:
            data: List of point dicts with at least x, y keys.

        Returns:
            Self for chaining.
        """
        self.points = [*self.points, *_normalize_points(data)]
        return self

    def add_numpy(
        self,
        positions: Any,
        *,
        ids: list[str] | None = None,
        labels: list[str] | None = None,
        metadata: dict[str, list[Any]] | None = None,
    ) -> VectorSpace:
        """Append points from a NumPy array.

        For arrays with D > 3 columns, the full vectors are stored internally
        and PCA is used for the initial 3D coordinates. Call ``project()`` to
        switch projection methods interactively.

        Args:
            positions: Array of shape (N, 2), (N, 3), or (N, D) for high-dim data.
            ids: Optional list of point IDs.
            labels: Optional list of labels.
            metadata: Optional dict mapping field names to per-point value lists.

        Returns:
            Self for chaining.
        """
        import numpy as np

        arr = np.asarray(positions, dtype=np.float64)
        n_samples, n_dims = arr.shape

        # High-dimensional: store vectors and project to 3D
        if n_dims > 3:
            if self._vectors is not None:
                self._vectors = np.vstack([self._vectors, arr])
            else:
                self._vectors = arr
            coords = _pca(arr, n_components=3)
        else:
            coords = arr

        offset = len(self.points)
        new_points = []
        for i in range(n_samples):
            point: dict[str, Any] = {
                "id": ids[i] if ids else f"point_{offset + i}",
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "z": float(coords[i, 2]) if coords.shape[1] > 2 else 0.0,
            }
            if labels:
                point["label"] = labels[i]
            if metadata:
                for key, values in metadata.items():
                    point[key] = values[i]
            new_points.append(point)
        self.points = [*self.points, *new_points]
        return self

    # === Projection ===

    def set_vectors(self, vectors: Any) -> VectorSpace:
        """Store high-dimensional vectors for use with ``project()``.

        Must have the same number of rows as ``self.points``.

        Args:
            vectors: Array-like of shape (N, D).

        Returns:
            Self for chaining.
        """
        import numpy as np

        self._vectors = np.asarray(vectors, dtype=np.float64)
        return self

    def project(self, method: str = "pca", *, n_components: int = 3, **kwargs: Any) -> VectorSpace:
        """Reproject point coordinates using dimensionality reduction.

        Reads vectors from ``set_vectors()`` / ``add_numpy()`` (for D > 3), or
        falls back to extracting the ``vector`` field from each point dict.

        Supported methods: ``pca``, ``tsne``, ``umap``.

        Args:
            method: Projection algorithm name.
            n_components: Target dimensions (2 or 3).
            **kwargs: Passed to the underlying algorithm.

        Returns:
            Self for chaining.
        """
        vectors = self._resolve_vectors()
        n_components = min(n_components, vectors.shape[1])

        if method == "pca":
            coords = _pca(vectors, n_components=n_components)
        elif method == "tsne":
            coords = _tsne(vectors, n_components=n_components, **kwargs)
        elif method == "umap":
            coords = _umap(vectors, n_components=n_components, **kwargs)
        else:
            raise ValueError(f"Unknown projection method: {method!r}. Use 'pca', 'tsne', or 'umap'.")

        # Normalize to roughly [-1, 1] so the scene stays well-framed
        for col in range(coords.shape[1]):
            c = coords[:, col]
            lo, hi = c.min(), c.max()
            if hi - lo > 0:
                coords[:, col] = 2 * (c - lo) / (hi - lo) - 1

        points = [dict(p) for p in self.points]
        for i, p in enumerate(points):
            p["x"] = float(coords[i, 0])
            p["y"] = float(coords[i, 1])
            p["z"] = float(coords[i, 2]) if n_components >= 3 else 0.0
        self.points = points
        return self

    def _resolve_vectors(self) -> Any:
        """Get the vector matrix for projection."""
        import numpy as np

        if self._vectors is not None:
            if len(self._vectors) != len(self.points):
                raise ValueError(
                    f"Stored vectors ({len(self._vectors)}) don't match point count ({len(self.points)}). "
                    "Call set_vectors() again after modifying points."
                )
            return self._vectors

        # Fall back to point["vector"] fields
        vecs = [p.get("vector") for p in self.points]
        if all(v is not None for v in vecs):
            return np.array(vecs, dtype=np.float64)

        raise ValueError(
            "No vectors available. Use set_vectors(), add_numpy() with D > 3, or ensure points have a 'vector' field."
        )

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

    @classmethod
    def from_pinecone(
        cls,
        index: Any,
        *,
        namespace: str = "",
        limit: int = 5000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from a Pinecone index.

        Uses list() to fetch vectors, then converts via the Pinecone converter.

        Args:
            index: pinecone.Index instance.
            namespace: Namespace to query (default: "").
            limit: Maximum number of vectors to fetch.
            **kwargs: Additional widget options.
        """
        from anywidget_vector.backends.pinecone.converter import to_points

        response = index.query(
            vector=[0.0] * index.describe_index_stats()["dimension"],
            top_k=limit,
            include_values=True,
            include_metadata=True,
            namespace=namespace,
        )
        return cls(points=to_points(response), **kwargs)

    @classmethod
    def from_weaviate(
        cls,
        client: Any,
        class_name: str,
        *,
        limit: int = 5000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from a Weaviate collection.

        Fetches objects with vectors using a GraphQL Get query.

        Args:
            client: weaviate.Client instance.
            class_name: Weaviate class name to query.
            limit: Maximum number of objects to fetch.
            **kwargs: Additional widget options.
        """
        from anywidget_vector.backends.weaviate.converter import to_points

        response = client.query.get(class_name).with_additional(["id", "vector"]).with_limit(limit).do()
        return cls(points=to_points(response, class_name), **kwargs)

    @classmethod
    def from_lancedb(
        cls,
        table: Any,
        *,
        limit: int = 5000,
        **kwargs: Any,
    ) -> VectorSpace:
        """Create from a LanceDB table.

        Reads rows from the table and converts them to visualization points.

        Args:
            table: lancedb.table.Table instance.
            limit: Maximum number of rows to fetch.
            **kwargs: Additional widget options.
        """
        from anywidget_vector.backends.lancedb.converter import to_points

        results = table.to_pandas().head(limit).to_dict("records")
        return cls(points=to_points(results), **kwargs)

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

    def to_html(
        self,
        width: str = "100%",
        height: str = "600px",
        title: str = "Vector Visualization",
    ) -> str:
        """Generate a self-contained HTML string that renders the 3D visualization.

        The output loads Three.js and OrbitControls from esm.sh CDN and embeds
        the current points data plus visual settings. It renders a static 3D
        point cloud with color/size mapping, orbit controls, optional axes and
        grid, and a hover tooltip. No toolbar, panels, query, or backend code
        is included.

        Args:
            width: CSS width for the container element.
            height: CSS height for the container element.
            title: HTML page title.

        Returns:
            A complete HTML document as a string.
        """
        options = {
            "background": self.background,
            "color_field": self.color_field,
            "color_scale": self.color_scale,
            "color_domain": self.color_domain,
            "size_field": self.size_field,
            "size_range": list(self.size_range),
            "show_axes": self.show_axes,
            "show_grid": self.show_grid,
            "axis_labels": dict(self.axis_labels),
        }
        return _HTML_TEMPLATE.format(
            title=title,
            width=width,
            height=height,
            json_data=json.dumps(self.points),
            json_options=json.dumps(options),
        )

    def save_html(self, path: str, **kwargs: Any) -> None:
        """Save the visualization as a self-contained HTML file.

        Args:
            path: File path to write the HTML to.
            **kwargs: Forwarded to ``to_html()`` (width, height, title).
        """
        from pathlib import Path

        Path(path).write_text(self.to_html(**kwargs), encoding="utf-8")


# === HTML Export Template ===

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ margin: 0; overflow: hidden; font-family: sans-serif; }}
#container {{ width: {width}; height: {height}; position: relative; }}
.tooltip {{
  display: none;
  position: absolute;
  background: rgba(15, 15, 35, 0.92);
  color: #e2e8f0;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  pointer-events: none;
  z-index: 100;
  max-width: 260px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}}
.tooltip-label {{ font-weight: 600; margin-bottom: 4px; color: #a5b4fc; }}
.tooltip-row {{ display: flex; justify-content: space-between; gap: 12px; }}
.tooltip-key {{ color: #94a3b8; }}
</style>
</head>
<body>
<div id="container"></div>
<div id="tooltip" class="tooltip"></div>
<script type="module">
import * as THREE from "https://esm.sh/three@0.160.0";
import {{ OrbitControls }} from "https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js";

const DATA = {json_data};
const OPTIONS = {json_options};

// ---------------------------------------------------------------------------
// Color scales (same LUT data used by the live widget)
// ---------------------------------------------------------------------------
const COLOR_SCALES = {{
  viridis: [[0.267,0.004,0.329],[0.282,0.140,0.458],[0.253,0.265,0.530],[0.206,0.371,0.553],[0.163,0.471,0.558],[0.127,0.566,0.551],[0.134,0.658,0.518],[0.267,0.749,0.441],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144]],
  plasma: [[0.050,0.030,0.528],[0.254,0.014,0.615],[0.417,0.001,0.658],[0.578,0.015,0.643],[0.716,0.135,0.538],[0.826,0.268,0.407],[0.906,0.411,0.271],[0.959,0.567,0.137],[0.981,0.733,0.106],[0.964,0.903,0.259],[0.940,0.975,0.131]],
  inferno: [[0.001,0.000,0.014],[0.046,0.031,0.186],[0.140,0.046,0.357],[0.258,0.039,0.406],[0.366,0.071,0.432],[0.478,0.107,0.429],[0.591,0.148,0.404],[0.706,0.206,0.347],[0.815,0.290,0.259],[0.905,0.411,0.145],[0.969,0.565,0.026]],
  magma: [[0.001,0.000,0.014],[0.035,0.028,0.144],[0.114,0.049,0.315],[0.206,0.053,0.431],[0.306,0.064,0.505],[0.413,0.086,0.531],[0.529,0.113,0.527],[0.654,0.158,0.501],[0.776,0.232,0.459],[0.878,0.338,0.418],[0.953,0.468,0.392]],
  cividis: [[0.000,0.135,0.304],[0.000,0.179,0.345],[0.117,0.222,0.360],[0.214,0.263,0.365],[0.293,0.304,0.370],[0.366,0.345,0.375],[0.437,0.387,0.382],[0.509,0.429,0.393],[0.582,0.473,0.409],[0.659,0.520,0.431],[0.739,0.570,0.461]],
  turbo: [[0.190,0.072,0.232],[0.254,0.265,0.530],[0.163,0.471,0.558],[0.134,0.658,0.518],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144],[0.988,0.652,0.198],[0.925,0.394,0.235],[0.796,0.177,0.214],[0.480,0.016,0.110]],
}};

const CATEGORICAL_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#14b8a6"
];

// ---------------------------------------------------------------------------
// Color / size helpers
// ---------------------------------------------------------------------------
function hashString(str) {{
  let hash = 0;
  for (let i = 0; i < str.length; i++) {{
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }}
  return Math.abs(hash);
}}

function getColorFromScale(value, scaleName, domain) {{
  const scale = COLOR_SCALES[scaleName] || COLOR_SCALES.viridis;
  const [min, max] = domain || [0, 1];
  const range = max - min;
  const t = range > 0 ? Math.max(0, Math.min(1, (value - min) / range)) : 0.5;
  const idx = t * (scale.length - 1);
  const i = Math.floor(idx);
  const f = idx - i;
  if (i >= scale.length - 1) {{
    const c = scale[scale.length - 1];
    return new THREE.Color(c[0], c[1], c[2]);
  }}
  const c1 = scale[i], c2 = scale[i + 1];
  return new THREE.Color(
    c1[0] + f * (c2[0] - c1[0]),
    c1[1] + f * (c2[1] - c1[1]),
    c1[2] + f * (c2[2] - c1[2])
  );
}}

function getCategoricalColor(value) {{
  const idx = hashString(String(value)) % CATEGORICAL_COLORS.length;
  return new THREE.Color(CATEGORICAL_COLORS[idx]);
}}

function getPointColor(point, opts) {{
  if (point.color) return new THREE.Color(point.color);
  if (opts.colorField && point[opts.colorField] !== undefined) {{
    const value = point[opts.colorField];
    if (typeof value === "number") {{
      return getColorFromScale(value, opts.colorScale, opts.colorDomain);
    }}
    return getCategoricalColor(value);
  }}
  return new THREE.Color(0x6366f1);
}}

function getPointSize(point, opts) {{
  if (point.size !== undefined) return point.size;
  if (opts.sizeField && point[opts.sizeField] !== undefined && opts.sizeDomain) {{
    const [min, max] = opts.sizeDomain;
    const t = max > min ? (point[opts.sizeField] - min) / (max - min) : 0.5;
    return opts.sizeRange[0] + t * (opts.sizeRange[1] - opts.sizeRange[0]);
  }}
  return (opts.sizeRange[0] + opts.sizeRange[1]) * 0.5;
}}

// ---------------------------------------------------------------------------
// Prepare options
// ---------------------------------------------------------------------------
const opts = {{
  colorField: OPTIONS.color_field || null,
  colorScale: OPTIONS.color_scale || "viridis",
  colorDomain: OPTIONS.color_domain || null,
  sizeField: OPTIONS.size_field || null,
  sizeRange: OPTIONS.size_range || [0.02, 0.1],
  sizeDomain: null,
}};

// Compute color domain from data when not explicitly set
if (opts.colorField && !opts.colorDomain) {{
  const values = DATA.map(p => p[opts.colorField]).filter(v => typeof v === "number");
  if (values.length > 0) opts.colorDomain = [Math.min(...values), Math.max(...values)];
}}

// Compute size domain from data
if (opts.sizeField) {{
  const values = DATA.map(p => p[opts.sizeField]).filter(v => typeof v === "number");
  if (values.length > 0) opts.sizeDomain = [Math.min(...values), Math.max(...values)];
}}

// ---------------------------------------------------------------------------
// Scene setup
// ---------------------------------------------------------------------------
const container = document.getElementById("container");
const scene = new THREE.Scene();
scene.background = new THREE.Color(OPTIONS.background || "#1a1a2e");

const width = container.clientWidth;
const height = container.clientHeight;
const camera = new THREE.PerspectiveCamera(60, width / height, 0.01, 1000);
camera.position.set(5, 5, 5);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
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
if (OPTIONS.show_axes) {{
  const axes = new THREE.AxesHelper(1.2);
  scene.add(axes);
  const labels = OPTIONS.axis_labels || {{ x: "X", y: "Y", z: "Z" }};
  function addAxisLabel(text, position, color) {{
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = 64; canvas.height = 32;
    ctx.font = "bold 24px Arial";
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.textAlign = "center";
    ctx.fillText(text, 32, 24);
    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({{ map: texture }}));
    sprite.position.set(position[0], position[1], position[2]);
    sprite.scale.set(0.25, 0.125, 1);
    scene.add(sprite);
  }}
  addAxisLabel(labels.x || "X", [1.3, 0, 0], 0xff4444);
  addAxisLabel(labels.y || "Y", [0, 1.3, 0], 0x44ff44);
  addAxisLabel(labels.z || "Z", [0, 0, 1.3], 0x4444ff);
}}

if (OPTIONS.show_grid) {{
  const gridHelper = new THREE.GridHelper(2, 10, 0x444444, 0x333333);
  scene.add(gridHelper);
}}

// ---------------------------------------------------------------------------
// Points
// ---------------------------------------------------------------------------
const pointsGroup = new THREE.Group();
scene.add(pointsGroup);

if (DATA.length > 0) {{
  DATA.forEach((point, idx) => {{
    const geometry = new THREE.SphereGeometry(1, 16, 16);
    const color = getPointColor(point, opts);
    const material = new THREE.MeshPhongMaterial({{ color }});
    const mesh = new THREE.Mesh(geometry, material);
    const size = getPointSize(point, opts);
    mesh.scale.set(size, size, size);
    mesh.position.set(point.x ?? 0, point.y ?? 0, point.z ?? 0);
    mesh.userData = {{ pointIndex: idx, pointId: point.id || "point_" + idx }};
    pointsGroup.add(mesh);
  }});

  // Auto-fit camera to data bounds
  const box = new THREE.Box3();
  DATA.forEach(p => box.expandByPoint(new THREE.Vector3(p.x ?? 0, p.y ?? 0, p.z ?? 0)));
  const center = box.getCenter(new THREE.Vector3());
  const bsize = box.getSize(new THREE.Vector3()).length();
  const distance = bsize / (2 * Math.tan(Math.PI * camera.fov / 360));
  controls.target.copy(center);
  camera.position.copy(center.clone().add(new THREE.Vector3(distance * 0.6, distance * 0.6, distance * 0.6)));
  controls.update();
}}

// ---------------------------------------------------------------------------
// Tooltip via raycasting
// ---------------------------------------------------------------------------
const tooltipEl = document.getElementById("tooltip");
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

container.addEventListener("mousemove", (event) => {{
  const rect = container.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(pointsGroup.children, true);

  if (intersects.length > 0) {{
    const hit = intersects[0];
    const idx = hit.object.userData.pointIndex;
    const point = DATA[idx];
    if (point) {{
      let html = "";
      if (point.label) html += '<div class="tooltip-label">' + point.label + "</div>";
      for (const [key, val] of Object.entries(point)) {{
        if (key === "label" || key === "vector") continue;
        let display = val;
        if (typeof val === "number") display = val.toFixed(3);
        html += '<div class="tooltip-row"><span class="tooltip-key">' + key + ':</span><span>' + display + "</span></div>";
      }}
      tooltipEl.innerHTML = html;
      tooltipEl.style.display = "block";
      tooltipEl.style.left = (event.clientX - rect.left + 15) + "px";
      tooltipEl.style.top = (event.clientY - rect.top + 15) + "px";
    }}
  }} else {{
    tooltipEl.style.display = "none";
  }}
}});

// ---------------------------------------------------------------------------
// Animation loop
// ---------------------------------------------------------------------------
function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}}
animate();

// ---------------------------------------------------------------------------
// Resize handler
// ---------------------------------------------------------------------------
window.addEventListener("resize", () => {{
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {{
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }}
}});
</script>
</body>
</html>
"""


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


# === Projection Helpers ===


def _pca(vectors: Any, n_components: int = 3) -> Any:
    """PCA via SVD (numpy only, no sklearn needed)."""
    import numpy as np

    x = np.asarray(vectors, dtype=np.float64)
    x_centered = x - x.mean(axis=0)
    _u, _s, vt = np.linalg.svd(x_centered, full_matrices=False)
    return x_centered @ vt[:n_components].T


def _tsne(vectors: Any, n_components: int = 3, **kwargs: Any) -> Any:
    """t-SNE projection (requires scikit-learn)."""
    try:
        from sklearn.manifold import TSNE
    except ImportError:
        raise ImportError("t-SNE requires scikit-learn: uv add scikit-learn") from None
    kwargs.setdefault("perplexity", min(30.0, len(vectors) - 1))
    return TSNE(n_components=n_components, **kwargs).fit_transform(vectors)


def _umap(vectors: Any, n_components: int = 3, **kwargs: Any) -> Any:
    """UMAP projection (requires umap-learn)."""
    try:
        from umap import UMAP
    except ImportError:
        raise ImportError("UMAP requires umap-learn: uv add umap-learn") from None
    kwargs.setdefault("n_neighbors", min(15, len(vectors) - 1))
    return UMAP(n_components=n_components, **kwargs).fit_transform(vectors)
