# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anywidget-vector==0.2.5",
#     "marimo",
#     "numpy==2.4.3",
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
    import numpy as np

    from anywidget_vector import VectorSpace

    return VectorSpace, np


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Test: `add_numpy`
    """)
    return


@app.cell
def _(VectorSpace):
    # Start with an empty widget
    w = VectorSpace(
        width=900,
        height=500,
        background="#0f0f1a",
        color_field="group",
    )
    w
    return (w,)


@app.cell
def _(mo, np, w):
    # Add two numpy clusters
    rng = np.random.default_rng(42)

    cluster_a = rng.normal(loc=[0.3, 0.3, 0.3], scale=0.1, size=(50, 3))
    cluster_b = rng.normal(loc=[0.7, 0.7, 0.7], scale=0.1, size=(50, 3))

    w.add_numpy(
        cluster_a,
        labels=[f"A-{i}" for i in range(len(cluster_a))],
        metadata={"group": ["alpha"] * len(cluster_a)},
    ).add_numpy(
        cluster_b,
        labels=[f"B-{i}" for i in range(len(cluster_b))],
        metadata={"group": ["beta"] * len(cluster_b)},
    )

    mo.md(f"Added **{len(w.points)}** points total")
    return


@app.cell
def _(mo, np, w):
    # Add a third cluster with 2D data (z defaults to 0)
    rng2 = np.random.default_rng(99)
    flat = rng2.normal(loc=[0.5, 0.5], scale=0.08, size=(30, 2))

    w.add_numpy(flat, metadata={"group": ["flat"] * len(flat)})

    mo.md(f"Now **{len(w.points)}** points (added 30 flat 2D points)")
    return


@app.cell
def _(mo, w):
    # Verify point IDs are unique
    ids = [p["id"] for p in w.points]
    unique = len(set(ids))
    status = "All IDs unique" if unique == len(ids) else f"DUPLICATE IDS: {len(ids) - unique} collisions"
    mo.md(f"Points: {len(ids)}, Unique IDs: {unique}: **{status}**")
    return


if __name__ == "__main__":
    app.run()
