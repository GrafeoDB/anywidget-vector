# Based on the Fashion MNIST Parallel Coordinates notebook by the marimo team:
# https://github.com/marimo-team/gallery-examples/blob/main/notebooks/wigglystuff/fashion-mnist-parallel-coords.py
#
# Extended with anywidget-vector 3D scatter view and 6D dimension mapping.
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars==1.38.1",
#     "numpy==2.4.2",
#     "scikit-learn==1.8.0",
#     "wigglystuff==0.2.37",
#     "matplotlib==3.10.8",
#     "pandas==3.0.1",
#     "anywidget-vector==0.3.1",
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
    # Fashion MNIST: Parallel Coordinates + 6D Vector View

    Brush the parallel coordinates axes to filter. The 3D (xyz)+3D(color/size/shape) scatter updates in real time.
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
    # d3 schemeCategory10, assigned alphabetically to match wigglystuff
    _d3 = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    LABEL_COLORS = {_name: _d3[_i] for _i, _name in enumerate(sorted(label_names.values()))}
    SHAPE_NAMES = ["sphere", "cube", "cone", "octahedron", "cylinder", "tetrahedron"]
    return LABEL_COLORS, SHAPE_NAMES, images, label_names, labels


@app.cell
def _(mo):
    n_samples_slider = mo.ui.slider(start=500, stop=5000, step=500, value=2000, label="Samples")
    n_components_slider = mo.ui.slider(start=3, stop=15, step=1, value=5, label="PCA dims")
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
    _rng = np.random.default_rng(42)
    idx = _rng.choice(len(images), size=n_samples_slider.value, replace=False)

    _pca = PCA(n_components=n_components_slider.value)
    components = _pca.fit_transform(images[idx])

    df = pl.DataFrame({f"PC{i + 1}": components[:, i] for i in range(n_components_slider.value)}).with_columns(
        pl.Series("label", [label_names[labels[i]] for i in idx])
    )
    return components, df, idx


@app.cell
def _(LABEL_COLORS, ParallelCoordinates, df, mo):
    widget = mo.ui.anywidget(ParallelCoordinates(df, color_by="label", color_map=LABEL_COLORS))
    widget
    return (widget,)


@app.cell
def _(mo, n_components_slider):
    pcs = [f"PC{i + 1}" for i in range(n_components_slider.value)]
    x_dim = mo.ui.dropdown(options=pcs, value="PC1", label="X")
    y_dim = mo.ui.dropdown(options=pcs, value="PC2", label="Y")
    z_dim = mo.ui.dropdown(options=pcs, value="PC3", label="Z")
    size_dim = mo.ui.dropdown(options=["none", *pcs], value="PC4", label="Size")
    color_dim = mo.ui.dropdown(options=["label", *pcs], value="label", label="Color")
    shape_dim = mo.ui.dropdown(options=["label", "none", *pcs], value="PC5", label="Shape")
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
    mo,
    np,
    shape_dim,
    size_dim,
    x_dim,
    y_dim,
    z_dim,
):
    def _pc(name):
        return int(name[2:]) - 1

    _xi, _yi, _zi = _pc(x_dim.value), _pc(y_dim.value), _pc(z_dim.value)
    _color_pc = None if color_dim.value == "label" else _pc(color_dim.value)
    _size_pc = None if size_dim.value == "none" else _pc(size_dim.value)
    _shape_mode = shape_dim.value  # "label", "none", or a PC name

    # Shape mapping: label-based or PC-based (binned into 6 shape buckets)
    _unique_labels = sorted(set(label_names.values()))
    _shape_map = {_n: SHAPE_NAMES[_j % len(SHAPE_NAMES)] for _j, _n in enumerate(_unique_labels)}
    _shape_bins = None
    if _shape_mode not in ("label", "none"):
        _shape_col = components[:, _pc(_shape_mode)]
        _quantiles = np.percentile(_shape_col, np.linspace(0, 100, len(SHAPE_NAMES) + 1))
        _shape_bins = list(zip(_quantiles[:-1], _quantiles[1:], SHAPE_NAMES, strict=False))
        _shape_map = {_s: _s for _s in SHAPE_NAMES}

    def _get_shape_bin(_val):
        for _lo, _hi, _s in _shape_bins:
            if _val <= _hi:
                return _s
        return SHAPE_NAMES[-1]

    vs_points = []
    for _i in range(len(components)):
        _name = label_names[labels[idx[_i]]]
        _p = {
            "id": f"p_{_i}",
            "x": float(components[_i, _xi]),
            "y": float(components[_i, _yi]),
            "z": float(components[_i, _zi]),
            "label": _name,
        }
        if _color_pc is None:
            _p["color"] = LABEL_COLORS[_name]
        else:
            _p["color_val"] = float(components[_i, _color_pc])
        if _size_pc is not None:
            _p["size_val"] = float(components[_i, _size_pc])
        if _shape_mode == "label":
            _p["shape_cat"] = _name
        elif _shape_bins is not None:
            _p["shape_cat"] = _get_shape_bin(components[_i, _pc(_shape_mode)])
        vs_points.append(_p)

    _vs_kwargs = {
        "axis_labels": {"x": x_dim.value, "y": y_dim.value, "z": z_dim.value},
    }
    if _color_pc is not None:
        _vs_kwargs["color_field"] = "color_val"
        _vs_kwargs["color_scale"] = "viridis"
    if _size_pc is not None:
        _vs_kwargs["size_field"] = "size_val"
        _vs_kwargs["size_range"] = [0.01, 0.03]
    if _shape_mode != "none":
        _vs_kwargs["shape_field"] = "shape_cat"
        _vs_kwargs["shape_map"] = _shape_map

    vs_widget = VectorSpace(
        points=vs_points,
        height=900,
        show_toolbar=True,
        show_settings=True,
        show_properties=False,
        **_vs_kwargs,
    )
    vs = mo.ui.anywidget(vs_widget)
    vs
    return vs, vs_points, vs_widget


@app.cell
def _(LABEL_COLORS, color_dim, mo, vs_points, vs_widget, widget):
    # ParallelCoordinates -> VectorSpace (one-way)
    # Uses vs_widget (raw) to avoid triggering vs-dependent cells
    _par_selected = list(widget.widget.selected_indices or [])
    _par_filtered = set(widget.widget.filtered_indices)
    _active_set = set(_par_selected) if _par_selected else _par_filtered
    _updated = []
    for _i, _p in enumerate(vs_points):
        if _i not in _active_set:
            continue
        _new_p = dict(_p)
        if color_dim.value == "label":
            _new_p["color"] = LABEL_COLORS[_p["label"]]
        else:
            _new_p.pop("color", None)
        _updated.append(_new_p)
    vs_widget.points = _updated
    mo.md(f"**{len(_updated)}** / {len(vs_points)} points selected")
    return


@app.cell
def _(LABEL_COLORS, ParallelCoordinates, df, mo, vs):
    # VectorSpace -> filtered ParallelCoordinates (reactive via vs.value)
    _selected = list(vs.widget.selected_points or [])
    if _selected:
        _indices = sorted(int(sid.split("_")[1]) for sid in _selected)
        _filtered_df = df[_indices]
        _par = ParallelCoordinates(_filtered_df, color_by="label", color_map=LABEL_COLORS)
        mo.vstack(
            [
                mo.md(f"**{len(_indices)}** points selected in 3D view"),
                mo.ui.anywidget(_par),
            ]
        )
    else:
        mo.md("*Lasso or box-select points in the 3D view to filter*")
    return


@app.cell
def _(LABEL_COLORS, idx, images, label_names, labels, np, plt, vs, widget):
    _selected_ids = set(vs.widget.selected_points or [])
    _filtered = widget.widget.filtered_indices

    _show = [_i for _i in range(len(idx)) if f"p_{_i}" in _selected_ids][:10] if _selected_ids else list(_filtered[:10])

    _sample_idx = np.array(_show) if len(_show) > 0 else np.array([0])

    _fig, _axes = plt.subplots(1, len(_sample_idx), figsize=(2 * len(_sample_idx), 2.4))
    if len(_sample_idx) == 1:
        _axes = [_axes]
    for _ax, _si in zip(_axes, _sample_idx, strict=False):
        _name = label_names[labels[idx[_si]]]
        _ax.imshow(images[idx[_si]].reshape(28, 28), cmap="gray")
        _ax.set_title(_name, fontsize=9)
        _ax.axis("off")
        if f"p_{_si}" in _selected_ids:
            _color = LABEL_COLORS.get(_name, "#0880ea")
            for _spine in _ax.spines.values():
                _spine.set_visible(True)
                _spine.set_color(_color)
                _spine.set_linewidth(3)
            _ax.set_title(_name, fontsize=9, fontweight="bold", color=_color)
    plt.tight_layout()
    _fig
    return


if __name__ == "__main__":
    app.run()
