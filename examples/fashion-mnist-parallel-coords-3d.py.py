# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars==1.38.1",
#     "numpy==2.4.2",
#     "scikit-learn==1.8.0",
#     "wigglystuff",
#     "matplotlib==3.10.8",
#     "pandas==3.0.1",
#     "anywidget-vector",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import polars as pl
    from sklearn.datasets import fetch_openml
    from sklearn.decomposition import PCA
    from wigglystuff import ParallelCoordinates

    from anywidget_vector import VectorSpace

    return PCA, ParallelCoordinates, VectorSpace, fetch_openml, mo, np, pl, plt


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Fashion MNIST: Parallel Coordinates + 3D Vector View

    Brush the parallel coordinates axes to filter. The 3D scatter updates in real time.
    Use the dropdowns to map PCA dimensions to visual channels.
    """)
    return


@app.cell
def _(fetch_openml, np):
    mnist = fetch_openml("Fashion-MNIST", version=1, as_frame=False, parser="auto")
    images = mnist.data.astype(np.float32)
    labels = mnist.target.astype(int)

    label_names = {
        0: "T-shirt/top",
        1: "Trouser",
        2: "Pullover",
        3: "Dress",
        4: "Coat",
        5: "Sandal",
        6: "Shirt",
        7: "Sneaker",
        8: "Bag",
        9: "Ankle boot",
    }
    LABEL_COLORS = {
        "T-shirt/top": "#6366f1",
        "Trouser": "#f59e0b",
        "Pullover": "#10b981",
        "Dress": "#ef4444",
        "Coat": "#8b5cf6",
        "Sandal": "#06b6d4",
        "Shirt": "#f97316",
        "Sneaker": "#84cc16",
        "Bag": "#ec4899",
        "Ankle boot": "#14b8a6",
    }
    SHAPE_NAMES = ["sphere", "cube", "cone", "octahedron", "cylinder", "tetrahedron"]
    return LABEL_COLORS, SHAPE_NAMES, images, label_names, labels


@app.cell
def _(mo):
    n_samples_slider = mo.ui.slider(start=500, stop=5000, step=500, value=2000, label="Samples")
    n_components_slider = mo.ui.slider(start=3, stop=15, step=1, value=8, label="PCA dims")
    mo.hstack([n_samples_slider, n_components_slider])
    return n_components_slider, n_samples_slider


@app.cell
def _(
    PCA,
    images,
    label_names,
    labels,
    n_components_slider,
    n_samples_slider,
    np,
    pl,
):
    rng = np.random.default_rng(42)
    idx = rng.choice(len(images), size=n_samples_slider.value, replace=False)

    pca = PCA(n_components=n_components_slider.value)
    components = pca.fit_transform(images[idx])

    df = pl.DataFrame({f"PC{i + 1}": components[:, i] for i in range(n_components_slider.value)}).with_columns(
        pl.Series("label", [label_names[labels[i]] for i in idx])
    )
    return components, df, idx


@app.cell
def _(ParallelCoordinates, df, mo):
    widget = mo.ui.anywidget(ParallelCoordinates(df, color_by="label"))
    widget
    return (widget,)


@app.cell
def _(mo, n_components_slider):
    pcs = [f"PC{i + 1}" for i in range(n_components_slider.value)]
    x_dim = mo.ui.dropdown(options=pcs, value="PC1", label="X")
    y_dim = mo.ui.dropdown(options=pcs, value="PC2", label="Y")
    z_dim = mo.ui.dropdown(options=pcs, value="PC3", label="Z")
    size_dim = mo.ui.dropdown(options=["none", *pcs], value="none", label="Size")
    color_dim = mo.ui.dropdown(options=["label", *pcs], value="label", label="Color")
    shape_dim = mo.ui.dropdown(options=["label", "none"], value="none", label="Shape")
    mo.hstack([x_dim, y_dim, z_dim, size_dim, color_dim, shape_dim], gap=0.5)
    return color_dim, shape_dim, size_dim, x_dim, y_dim, z_dim


@app.cell
def _(
    LABEL_COLORS,
    SHAPE_NAMES,
    VectorSpace,
    color_dim,
    components,
    idx,
    label_names,
    labels,
    shape_dim,
    size_dim,
    x_dim,
    y_dim,
    z_dim,
):
    def _pc(name):
        return int(name[2:]) - 1

    xi, yi, zi = _pc(x_dim.value), _pc(y_dim.value), _pc(z_dim.value)

    vs_points = []
    for i in range(len(components)):
        name = label_names[labels[idx[i]]]
        p = {
            "id": f"p_{i}",
            "x": float(components[i, xi]),
            "y": float(components[i, yi]),
            "z": float(components[i, zi]),
            "label": name,
        }
        if color_dim.value == "label":
            p["color"] = LABEL_COLORS[name]
        else:
            p["color_val"] = float(components[i, _pc(color_dim.value)])
        if size_dim.value != "none":
            p["size_val"] = float(components[i, _pc(size_dim.value)])
        if shape_dim.value == "label":
            unique = sorted(set(label_names.values()))
            p["shape_cat"] = name
            shape_map = {n: SHAPE_NAMES[j % len(SHAPE_NAMES)] for j, n in enumerate(unique)}
        vs_points.append(p)

    vs_kwargs = {
        "axis_labels": {"x": x_dim.value, "y": y_dim.value, "z": z_dim.value},
    }
    if color_dim.value != "label":
        vs_kwargs["color_field"] = "color_val"
        vs_kwargs["color_scale"] = "viridis"
    if size_dim.value != "none":
        vs_kwargs["size_field"] = "size_val"
        vs_kwargs["size_range"] = [0.01, 0.06]
    if shape_dim.value == "label":
        vs_kwargs["shape_field"] = "shape_cat"
        vs_kwargs["shape_map"] = shape_map

    vs = VectorSpace(
        points=vs_points,
        width=1200,
        height=500,
        dark_mode=False,
        background="#fafafa",
        show_toolbar=True,
        show_settings=True,
        show_properties=False,
        **vs_kwargs,
    )
    vs
    return vs, vs_points


@app.cell
def _(LABEL_COLORS, color_dim, mo, vs, vs_points, widget):
    _filtered = set(widget.widget.filtered_indices)
    _dim_color = "#d1d5db"
    _updated = []
    for i, p in enumerate(vs_points):
        new_p = dict(p)
        if i in _filtered:
            if color_dim.value == "label":
                new_p["color"] = LABEL_COLORS[p["label"]]
            else:
                new_p.pop("color", None)
        else:
            new_p["color"] = _dim_color
        _updated.append(new_p)
    vs.points = _updated
    mo.md(f"**{len(_filtered)}** / {len(vs_points)} points selected")
    return


@app.cell
def _(idx, images, label_names, labels, np, plt, widget):
    filtered = widget.widget.filtered_indices
    sample_idx = np.array(filtered[:10]) if len(filtered) >= 10 else np.array(filtered)

    fig, axes = plt.subplots(1, len(sample_idx), figsize=(2 * len(sample_idx), 2))
    if len(sample_idx) == 1:
        axes = [axes]
    for _ax, _si in zip(axes, sample_idx, strict=False):
        _ax.imshow(images[idx[_si]].reshape(28, 28), cmap="gray")
        _ax.set_title(label_names[labels[idx[_si]]], fontsize=9)
        _ax.axis("off")
    plt.tight_layout()
    fig
    return


if __name__ == "__main__":
    app.run()
