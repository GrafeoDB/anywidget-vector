"""Demo module for anywidget-vector.

Shows the 64 nodes of grafeo's Silicon Valley demo dataset (people, companies, products, technologies, AI,
places, cities and events from the HBO series), placed in 3D by a PCA of their MiniLM description embeddings, so
nodes with similar descriptions sit near each other. The points render without any backend; the toolbar's query
runs in the browser on Grafeo WASM, which loads the same dataset from the jsDelivr CDN on the first Run.

Usage:
    uv add "anywidget-vector[demo]"

    from anywidget_vector.demo import demo_vector
    vs = demo_vector()
"""

from __future__ import annotations

import json
from typing import Any

from anywidget_vector.widget import VectorSpace, _pca

# The toolbar's starting query: the nodes whose descriptions are nearest to Pied Piper's compression algorithm
DEMO_QUERY = (
    "MATCH (m {key: 'middle-out'}), (n) "
    "RETURN n, cosine_distance(n.embedding, m.embedding) AS distance ORDER BY distance LIMIT 12"
)


def _silicon_valley() -> Any:
    try:
        from grafeo_datasets import silicon_valley
    except ImportError:
        raise ImportError('The demo needs the demo extra: uv add "anywidget-vector[demo]"') from None
    return silicon_valley


def demo_points() -> list[dict[str, Any]]:
    """The demo's points: one per node of the Silicon Valley dataset.

    Each point has the node's ``key`` as ``id``, its ``name`` as ``label``, its node label (``Person``,
    ``Company``, ...) as ``category``, its ``description``, the 384-dimensional embedding of that description
    as ``vector``, and ``x``, ``y`` and ``z`` from a PCA of all embeddings, scaled to lie within -1 and 1.
    """
    import numpy as np

    silicon_valley = _silicon_valley()
    nodes = silicon_valley.nodes()
    by_key = silicon_valley.vectors().by_key
    matrix = np.array([by_key[node["key"]] for node in nodes], dtype=np.float64)
    coords = _pca(matrix, n_components=3)
    # SVD leaves each axis's sign open; fix it so the picture is the same on every machine
    signs = np.sign(coords[np.abs(coords).argmax(axis=0), range(3)])
    coords = coords * np.where(signs == 0, 1.0, signs)
    # Fill the widget's grid, which spans -1 to 1 whatever the data (the PCA alone spans about -0.5 to 0.5)
    coords = coords / np.abs(coords).max()
    return [
        {
            "id": node["key"],
            "label": node["name"],
            "category": node["label"],
            "description": node["description"],
            "vector": by_key[node["key"]],
            "x": float(x),
            "y": float(y),
            "z": float(z),
        }
        for node, (x, y, z) in zip(nodes, coords, strict=True)
    ]


def _demo_statements(points: list[dict[str, Any]]) -> list[str]:
    """GQL that gives each node in the browser database the point's position and category.

    Run after the dataset's own statements, so query results land where the points are drawn and keep their
    colours. The exponent makes each number a float; without it GQL reads an exact decimal.
    """
    return [
        f"MATCH (n:{p['category']} {{key: '{p['id']}'}}) "
        f"SET n.x = {p['x']:.6e}, n.y = {p['y']:.6e}, n.z = {p['z']:.6e}, n.category = '{p['category']}'"
        for p in points
    ]


def demo_vector(**kwargs: Any) -> VectorSpace:
    """Create a demo VectorSpace widget on the Silicon Valley dataset.

    The 64 nodes are coloured by node label and placed by a PCA of their description embeddings
    (``Xenova/all-MiniLM-L6-v2``, 384 dimensions). The full embeddings are kept, so ``project("umap")``,
    ``project("tsne")`` and ``compute_distances(..., vector_field="vector")`` work on the real vectors.

    The toolbar starts with a GQL query for the nodes nearest to middle-out compression. Run sends it to
    Grafeo WASM in the browser, which loads ``@grafeo-db/wasm`` and ``@grafeo-db/datasets`` from the jsDelivr
    CDN on the first Run.

    Parameters
    ----------
    **kwargs
        Additional keyword arguments passed to VectorSpace constructor.
        Overrides demo defaults.

    Returns
    -------
    VectorSpace
        A ready-to-use VectorSpace widget with demo data rendered.

    Example
    -------
    >>> from anywidget_vector.demo import demo_vector
    >>> vs = demo_vector()
    >>> vs  # renders in notebook
    """
    import numpy as np

    points = demo_points()
    defaults: dict[str, Any] = {
        "points": points,
        "width": kwargs.pop("width", 900),
        "height": kwargs.pop("height", 600),
        "backend": "grafeo",
        "grafeo_connection_mode": "wasm",
        "query_input": DEMO_QUERY,
        "color_field": "category",
        "show_tooltip": True,
        "tooltip_fields": ["label", "category", "description"],
        "_demo_mode": True,
        "_demo_data": json.dumps(_demo_statements(points)),
    }
    own_points = "points" not in kwargs
    defaults.update(kwargs)

    widget = VectorSpace(**defaults)
    if own_points:
        widget.set_vectors(np.array([p["vector"] for p in points], dtype=np.float64))
    return widget
