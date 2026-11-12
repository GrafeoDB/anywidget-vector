"""Main VectorSpace widget using anywidget and Three.js."""

from __future__ import annotations

import html
import json
import math
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anywidget
import traitlets

from anywidget_vector.backends import is_python_backend
from anywidget_vector.backends.chroma.client import execute_query as chroma_query
from anywidget_vector.backends.grafeo.client import execute_query as grafeo_query
from anywidget_vector.backends.lancedb.client import execute_query as lancedb_query
from anywidget_vector.ui import get_css, get_esm, get_export_js, get_vendor_js

if TYPE_CHECKING:
    pass


class _ChosenOnSet(traitlets.TraitType):
    """A theme trait that records a choice in its `flag` trait whenever Python assigns it.

    Assigning the value the trait already has counts too: `widget.dark_mode = True` on a dark page keeps the widget
    dark after the page turns light. Values the widget writes from the browser arrive through `set_state` and are
    not a choice.
    """

    def __init__(self, *args: Any, flag: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.flag = flag

    def set(self, obj: Any, value: Any) -> None:
        super().set(obj, value)
        if not obj._applying_frontend_state:
            obj.set_trait(self.flag, True)


class _ChosenBool(_ChosenOnSet, traitlets.Bool):
    pass


class _ChosenUnicode(_ChosenOnSet, traitlets.Unicode):
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
    background = _ChosenUnicode(default_value="#1a1a2e", flag="_background_explicit").tag(sync=True)

    # === Theme ===
    # dark_mode reports the current theme. The widget follows the host page until a theme is chosen: dark_mode
    # set from Python (in the constructor, before or after display) or the settings toggle (shared with
    # anywidget-graph and anywidget-archimate). Until a background is chosen the same way, the widget sets it
    # to the theme's canvas color.
    dark_mode = _ChosenBool(default_value=True, flag="_theme_explicit").tag(sync=True)
    _theme_explicit = traitlets.Bool(default_value=False).tag(sync=True)
    _background_explicit = traitlets.Bool(default_value=False).tag(sync=True)
    # True while state from the browser is applied (see set_state)
    _applying_frontend_state = False

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
        # None means "follow the page" (dark_mode) or "the theme's canvas color" (background), like leaving it out
        for name in ("dark_mode", "background"):
            if kwargs.get(name, ...) is None:
                del kwargs[name]
        super().__init__(points=points or [], **kwargs)
        self._backend_client: Any = None
        self._vectors: Any = None  # High-dim vectors for projection (numpy array, not synced to JS)
        self.observe(self._on_execute_query, names=["_execute_query"])

    def set_state(self, sync_data: dict[str, Any]) -> None:
        """Apply state from the browser (Jupyter and marimo both call this): theme values it carries are the
        widget following the page or a choice the browser already recorded, not a choice made in Python."""
        self._applying_frontend_state = True
        try:
            super().set_state(sync_data)
        finally:
            self._applying_frontend_state = False

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

    @traitlets.validate("points")
    def _validate_points(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        """Replace NaN and infinity in top-level point values with None.

        JSON cannot carry them (Jupyter sends the string "nan" instead) and a
        single NaN coordinate breaks camera framing for the whole scene. The
        frontend treats None like a missing value (coordinates default to 0).
        Nested values such as ``vector`` lists are left as they are.
        """
        points, replaced = _replace_non_finite(proposal["value"])
        if replaced:
            warnings.warn(
                f"{replaced} non-finite value(s) (NaN or infinity) in points were replaced with None",
                RuntimeWarning,
                stacklevel=2,
            )
        return points

    def _on_execute_query(self, change: dict[str, Any]) -> None:
        """Handle query execution for Python-side backends."""
        if change["new"] == 0 or not is_python_backend(self.backend):
            return
        try:
            self.query_error = None
            self.connection_status = "connecting"
            # An empty result clears the scene, like the browser-side backends do
            self.points = self._execute_python_query()
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

        Raises:
            ValueError: if ``positions`` is not a 2-D array with at least 2 columns,
                if a D > 3 array holds NaN or infinity (PCA cannot use them), or if
                ``ids``, ``labels`` or a ``metadata`` list does not have one entry per row.
        """
        import numpy as np

        arr = _as_matrix(positions, "positions")
        n_samples, n_dims = arr.shape
        if n_dims < 2:
            raise ValueError(f"positions needs at least 2 columns (x, y), got shape {arr.shape}")
        _check_lengths(
            n_samples,
            {"ids": ids, "labels": labels, **{f"metadata[{k!r}]": v for k, v in (metadata or {}).items()}},
        )

        # High-dimensional: store vectors and project to 3D
        if n_dims > 3:
            coords = _pca(arr, n_components=3)  # validates before any state changes
            if self._vectors is not None:
                self._vectors = np.vstack([self._vectors, arr])
            else:
                self._vectors = arr
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
        self._vectors = _as_matrix(vectors, "vectors")
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
        vectors = _require_finite(self._resolve_vectors(), "vectors")
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
        vecs = [v for p in self.points if (v := p.get("vector")) is not None]
        if vecs and len(vecs) == len(self.points):
            if len(lengths := {len(v) for v in vecs}) > 1:
                raise ValueError(
                    f"Point 'vector' fields have different lengths ({sorted(lengths)}); "
                    "projection needs one dimension for all points."
                )
            return _as_matrix(np.array(vecs, dtype=np.float64), "point vectors")

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
                Same names and values as a Grafeo vector index with that metric.
            vector_field: Use a high-dimensional vector field instead of x/y/z.
                Points without that field (or with an empty one) are left out.

        Raises:
            ValueError: if a point's ``vector_field`` has a different length than
                the reference point's.
        """
        metric = metric or self.distance_metric
        ref = next((p for p in self.points if p.get("id") == reference_id), None)
        if not ref:
            return {}
        others = [p for p in self.points if p.get("id") != reference_id]
        if vector_field:
            # Points without the vector have no distance (previously infinity, which is not valid JSON)
            if not _has_vector(ref.get(vector_field)):
                return {}
            others = [p for p in others if _has_vector(p.get(vector_field))]
            dims = len(ref[vector_field])
            if mismatched := [p.get("id") for p in others if len(p[vector_field]) != dims]:
                raise ValueError(
                    f"'{vector_field}' of {reference_id!r} has {dims} dimensions, "
                    f"but these points differ: {mismatched[:5]}"
                )
        return {p.get("id"): self._distance(ref, p, metric, vector_field) for p in others}

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
            v1 = p1[vector_field]
            v2 = p2[vector_field]
            n = len(v1)
        else:
            v1 = [_coord(p1, "x"), _coord(p1, "y"), _coord(p1, "z")]
            v2 = [_coord(p2, "x"), _coord(p2, "y"), _coord(p2, "z")]
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
            cx = sum(_coord(p, "x") for p in pts) / len(pts)
            cy = sum(_coord(p, "y") for p in pts) / len(pts)
            cz = sum(_coord(p, "z") for p in pts) / len(pts)
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

        The output embeds Three.js and OrbitControls (bundled with the package, so
        the file works offline) plus the current points data and visual settings. It renders a static 3D
        point cloud with color/size mapping, orbit controls, optional axes and
        grid, and a hover tooltip. No toolbar, panels, query, or backend code
        is included.

        Args:
            width: CSS width for the container element.
            height: CSS height for the container element.
            title: HTML page title.

        Returns:
            A complete HTML document as a string.

        Raises:
            ValueError: If width or height is not a plain CSS value (such as ``600px``, ``100%`` or ``calc(...)``).
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
            title=html.escape(title),
            width=_css_value("width", width),
            height=_css_value("height", height),
            vendor_js=get_vendor_js(),
            json_data=_json_for_script(self.points),
            json_options=_json_for_script(options),
            export_js=get_export_js(),
        )

    def save_html(self, path: str, **kwargs: Any) -> None:
        """Save the visualization as a self-contained HTML file.

        Args:
            path: File path to write the HTML to.
            **kwargs: Forwarded to ``to_html()`` (width, height, title).
        """
        Path(path).write_text(self.to_html(**kwargs), encoding="utf-8")


# === HTML Export Template ===

# The page to_html() fills in (a str.format template: literal braces are doubled)
_HTML_TEMPLATE = (Path(__file__).parent / "ui" / "export.html").read_text(encoding="utf-8")


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


def _replace_non_finite(points: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return points with top-level NaN/infinity floats set to None, and how many were replaced."""
    replaced = 0
    cleaned = points
    for i, point in enumerate(points):
        bad = [k for k, v in point.items() if isinstance(v, float) and not math.isfinite(v)]
        if not bad:
            continue
        if cleaned is points:
            cleaned = list(points)
        cleaned[i] = {**point, **dict.fromkeys(bad)}
        replaced += len(bad)
    return cleaned, replaced


_CSS_VALUE = re.compile(r"[#\w(),.%\s+*/-]+")


def _css_value(name: str, value: str) -> str:
    """A CSS value that cannot leave its declaration: no `;`, braces, quotes or `<`."""
    if not _CSS_VALUE.fullmatch(value):
        raise ValueError(f"{name} must be a plain CSS value such as '600px' or '100%', got {value!r}")
    return value


def _json_for_script(value: Any) -> str:
    """JSON that is safe inside an inline <script>: a "</script>" in the data cannot end the element."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _has_vector(value: Any) -> bool:
    return value is not None and len(value) > 0


def _coord(point: dict[str, Any], axis: str) -> Any:
    """A coordinate, with missing or None (for example a replaced NaN) as 0, like the frontend."""
    value = point.get(axis)
    return 0 if value is None else value


def _check_lengths(n_rows: int, columns: dict[str, Any]) -> None:
    for name, values in columns.items():
        if values is not None and len(values) != n_rows:
            raise ValueError(f"{name} has {len(values)} entries, expected one per row ({n_rows})")


def _as_matrix(values: Any, name: str) -> Any:
    """Coerce to a 2-D float64 array with a clear error for ragged or 1-D input."""
    import numpy as np

    try:
        arr = np.asarray(values, dtype=np.float64)
    except ValueError as exc:
        raise ValueError(f"{name} must be a 2-D array of numbers with equal-length rows: {exc}") from None
    if arr.ndim != 2:
        raise ValueError(f"{name} must be a 2-D array of shape (N, D), got shape {arr.shape}")
    return arr


def _require_finite(arr: Any, name: str) -> Any:
    import numpy as np

    if not np.isfinite(arr).all():
        raise ValueError(f"{name} contain NaN or infinite values; projection needs finite numbers")
    return arr


# === Projection Helpers ===


def _pca(vectors: Any, n_components: int = 3) -> Any:
    """PCA via SVD (numpy only, no sklearn needed).

    Always returns ``n_components`` columns: with fewer samples than components
    (for example a single vector) the missing components are zero.
    """
    import numpy as np

    x = _require_finite(np.asarray(vectors, dtype=np.float64), "vectors")
    if len(x) == 0:
        return np.zeros((0, n_components))
    x_centered = x - x.mean(axis=0)
    _u, _s, vt = np.linalg.svd(x_centered, full_matrices=False)
    coords = x_centered @ vt[:n_components].T
    if coords.shape[1] < n_components:
        coords = np.pad(coords, ((0, 0), (0, n_components - coords.shape[1])))
    return coords


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
