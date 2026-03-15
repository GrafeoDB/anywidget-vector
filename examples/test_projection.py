# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anywidget-vector",
#     "marimo",
#     "numpy",
#     "scikit-learn",
# ]
# ///

import marimo

__generated_with = "0.20.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import numpy as np

    from anywidget_vector import VectorSpace

    return VectorSpace, np


@app.cell(hide_code=True)
def _(mo):
    mo.md("""# Interactive Projection Demo

    High-dimensional data projected to 3D. Switch projections live with the dropdown.
    """)
    return


@app.cell
def _(np):
    # Generate 50-dimensional clustered data
    rng = np.random.default_rng(42)

    def make_cluster(center, n=80, noise=0.3):
        return rng.normal(loc=center, scale=noise, size=(n, len(center)))

    n_dims = 50
    centers = [rng.uniform(-2, 2, size=n_dims) for _ in range(5)]
    cluster_names = ["alpha", "beta", "gamma", "delta", "epsilon"]

    vectors = np.vstack([make_cluster(c) for c in centers])
    groups = [name for name, c in zip(cluster_names, centers) for _ in range(80)]
    labels = [f"{g}-{i}" for i, g in enumerate(groups)]

    f"Generated {len(vectors)} points in {n_dims}D across 5 clusters"
    return vectors, groups, labels


@app.cell
def _(mo):
    method = mo.ui.dropdown(
        options=["pca", "tsne"],
        value="pca",
        label="Projection method",
    )
    method
    return (method,)


@app.cell
def _(VectorSpace, groups, labels, method, vectors):
    w = VectorSpace(
        width=900,
        height=500,
        background="#0f0f1a",
        color_field="group",
    )
    w.add_numpy(
        vectors,
        labels=labels,
        metadata={"group": groups},
    )
    w.project(method.value)
    w
    return (w,)


@app.cell
def _(method, w):
    f"Showing **{method.value.upper()}** projection of {len(w.points)} points"
    return


if __name__ == "__main__":
    app.run()
