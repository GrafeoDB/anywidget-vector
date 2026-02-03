"""Traitlet definitions for VectorSpace widget."""

from __future__ import annotations

import traitlets


class VectorSpaceTraits(traitlets.HasTraits):
    """All traitlets for the VectorSpace widget, grouped logically."""

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

    # === Distance Metrics and Connections ===
    distance_metric = traitlets.Unicode(default_value="euclidean").tag(sync=True)
    show_connections = traitlets.Bool(default_value=False).tag(sync=True)
    k_neighbors = traitlets.Int(default_value=0).tag(sync=True)
    distance_threshold = traitlets.Float(default_value=None, allow_none=True).tag(sync=True)
    reference_point = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    connection_color = traitlets.Unicode(default_value="#ffffff").tag(sync=True)
    connection_opacity = traitlets.Float(default_value=0.3).tag(sync=True)

    # === UI Visibility ===
    show_toolbar = traitlets.Bool(default_value=False).tag(sync=True)
    show_settings = traitlets.Bool(default_value=False).tag(sync=True)
    show_properties = traitlets.Bool(default_value=False).tag(sync=True)

    # === Backend Configuration ===
    backend = traitlets.Unicode(default_value="qdrant").tag(sync=True)
    backend_config = traitlets.Dict(default_value={}).tag(sync=True)
    connection_status = traitlets.Unicode(default_value="disconnected").tag(sync=True)

    # === Query Parameters ===
    query_type = traitlets.Unicode(default_value="text").tag(sync=True)
    query_input = traitlets.Unicode(default_value="").tag(sync=True)
    query_limit = traitlets.Int(default_value=100).tag(sync=True)
    query_error = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)

    # === Embedding Configuration ===
    embedding_config = traitlets.Dict(default_value={}).tag(sync=True)

    # === Internal Triggers ===
    _execute_query = traitlets.Int(default_value=0).tag(sync=True)
