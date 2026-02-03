# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anywidget-vector==0.2.0",
#     "marimo",
# ]
# ///
import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import random

    from anywidget_vector import VectorSpace

    return VectorSpace, random


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # anywidget-vector Demo

    Interactive 3D vector visualization with distance metrics and query UI.
    """)
    return


@app.cell
def _(VectorSpace, random):
    # Generate sample clustered data
    random.seed(42)

    def generate_cluster(center, n=20, spread=0.15):
        points = []
        for i in range(n):
            points.append(
                {
                    "x": center[0] + random.gauss(0, spread),
                    "y": center[1] + random.gauss(0, spread),
                    "z": center[2] + random.gauss(0, spread),
                    "cluster": center[3],
                }
            )
        return points

    # Create 4 clusters
    clusters = [
        (0.3, 0.3, 0.3, "A"),
        (0.7, 0.3, 0.7, "B"),
        (0.3, 0.7, 0.7, "C"),
        (0.7, 0.7, 0.3, "D"),
    ]

    points = []
    for center in clusters:
        points.extend(generate_cluster(center))

    # Add IDs and labels
    for i, p in enumerate(points):
        p["id"] = f"point_{i}"
        p["label"] = f"Point {i} ({p['cluster']})"
        p["importance"] = random.random()

    # Create widget with color by cluster
    widget = VectorSpace(
        points=points,
        color_field="cluster",
        size_field="importance",
        size_range=[0.02, 0.06],
        width=800,
        height=500,
        background="#0f0f1a",
    )
    widget
    return points, widget


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Distance Features

    Click on a point above, then run the cells below to explore distance metrics.
    """)
    return


@app.cell
def _(widget):
    # Get the currently selected point
    selected = widget.selected_points
    selected_id = selected[0] if selected else "point_0"
    f"Selected point: {selected_id}"
    return (selected_id,)


@app.cell
def _(selected_id, widget):
    # Find 5 nearest neighbors using Euclidean distance
    neighbors_euclidean = widget.find_neighbors(selected_id, k=5, metric="euclidean")
    neighbors_euclidean
    return


@app.cell
def _(selected_id, widget):
    # Find 5 nearest neighbors using Cosine distance
    neighbors_cosine = widget.find_neighbors(selected_id, k=5, metric="cosine")
    neighbors_cosine
    return


@app.cell
def _(VectorSpace, points):
    # Create a second widget showing neighbor connections
    widget2 = VectorSpace(
        points=points,
        color_field="cluster",
        width=800,
        height=500,
        background="#0f0f1a",
        # Enable k-nearest neighbor connections
        show_connections=True,
        k_neighbors=3,
        distance_metric="euclidean",
        connection_color="#44ff88",
        connection_opacity=0.4,
    )
    widget2
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Color by Distance

    The widget below colors points by distance from a reference point.
    """)
    return


@app.cell
def _(VectorSpace, points):
    # Create widget and color by distance from first point
    widget3 = VectorSpace(
        points=[dict(p) for p in points],  # Copy points
        width=800,
        height=500,
        background="#0f0f1a",
        color_scale="plasma",
    )
    widget3.color_by_distance("point_0", metric="euclidean")
    widget3.show_neighbors("point_0", k=5)
    widget3
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Different Shapes

    Using shapes to encode an additional dimension.
    """)
    return


@app.cell
def _(VectorSpace, points):
    # Create widget with shape mapping
    widget4 = VectorSpace(
        points=points,
        color_field="cluster",
        shape_field="cluster",
        shape_map={
            "A": "sphere",
            "B": "cube",
            "C": "cone",
            "D": "octahedron",
        },
        size_range=[0.04, 0.04],  # Fixed size
        width=800,
        height=500,
        background="#0f0f1a",
    )
    widget4
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Query UI

    The widget below shows the query interface for vector database backends.
    Enable `show_query_input=True` to show the toolbar.

    **Supported backends:**
    - Browser-side (REST API): Qdrant, Pinecone, Weaviate
    - Python-side: Chroma, LanceDB, Grafeo

    **Query types:**
    - Text Search (requires embedding API)
    - Find Similar (by vector ID)
    - Raw Vector ([0.1, 0.2, ...])
    - Filter (JSON filter expressions)
    """)
    return


@app.cell
def _(VectorSpace, points):
    # Create widget with query UI enabled
    widget5 = VectorSpace(
        points=points,
        color_field="cluster",
        width=800,
        height=500,
        background="#0f0f1a",
        # Enable query UI
        show_query_input=True,
        show_settings=True,
        # Default to Qdrant backend
        backend="qdrant",
    )
    widget5
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Python-side Backend Example

    For Python-side backends like Chroma, configure the client directly:

    ```python
    import chromadb

    client = chromadb.Client()
    collection = client.get_or_create_collection("my_vectors")

    widget = VectorSpace(
        show_query_input=True,
        show_settings=True,
    )
    widget.set_backend("chroma", collection)

    # Optional: set custom embedding function for text search
    def my_embed(text):
        # Your embedding logic here
        return [0.1, 0.2, 0.3, ...]

    widget.set_embedding(my_embed)
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
