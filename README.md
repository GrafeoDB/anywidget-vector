# anywidget-vector

Interactive 3D vector visualization for Python notebooks.

Works with Marimo, Jupyter, VS Code, Colab, anywhere [anywidget](https://anywidget.dev/) runs.

## Features

- **Universal**: One widget, every notebook environment
- **6D Visualization**: X, Y, Z position + Color, Shape, Size encoding
- **Backend-agnostic**: NumPy, pandas, Qdrant, Chroma, or raw dicts
- **Interactive**: Orbit, pan, zoom, click, hover, select
- **Customizable**: Color scales, shapes, sizes, themes
- **Performant**: Instanced rendering for large point clouds

## Installation

```bash
uv add anywidget-vector
```

## Quick Start

```python
from anywidget_vector import VectorSpace

widget = VectorSpace(points=[
    {"id": "a", "x": 0.5, "y": 0.3, "z": 0.8, "label": "Point A", "cluster": 0},
    {"id": "b", "x": -0.2, "y": 0.7, "z": 0.1, "label": "Point B", "cluster": 1},
    {"id": "c", "x": 0.1, "y": -0.4, "z": 0.6, "label": "Point C", "cluster": 0},
])

widget
```

## Data Sources

### Dictionary

```python
from anywidget_vector import VectorSpace

widget = VectorSpace.from_dict({
    "points": [
        {"id": "a", "x": 0, "y": 0, "z": 0},
        {"id": "b", "x": 1, "y": 1, "z": 1},
    ]
})
```

### NumPy Arrays

```python
import numpy as np
from anywidget_vector import VectorSpace

positions = np.random.randn(100, 3)
widget = VectorSpace.from_numpy(positions)
```

### pandas DataFrame

```python
import pandas as pd
from anywidget_vector import VectorSpace

df = pd.DataFrame({
    "x": [0.1, 0.5, 0.9],
    "y": [0.2, 0.6, 0.3],
    "z": [0.3, 0.1, 0.7],
    "cluster": ["A", "B", "A"],
    "size": [0.5, 1.0, 0.8],
})

widget = VectorSpace.from_dataframe(
    df,
    color_col="cluster",
    size_col="size",
)
```

### UMAP / t-SNE / PCA

```python
import umap
from anywidget_vector import VectorSpace

# Reduce high-dimensional data to 3D
embedding = umap.UMAP(n_components=3).fit_transform(high_dim_data)
widget = VectorSpace.from_umap(embedding, labels=labels)
```

### Qdrant

```python
from qdrant_client import QdrantClient
from anywidget_vector import VectorSpace

client = QdrantClient("localhost", port=6333)
widget = VectorSpace.from_qdrant(client, "my_collection", limit=5000)
```

### ChromaDB

```python
import chromadb
from anywidget_vector import VectorSpace

client = chromadb.Client()
collection = client.get_collection("embeddings")
widget = VectorSpace.from_chroma(collection)
```

## Visual Encoding

### 6 Dimensions

| Dimension | Visual Channel | Example |
|-----------|---------------|---------|
| X | Horizontal position | `x` coordinate |
| Y | Vertical position | `y` coordinate |
| Z | Depth position | `z` coordinate |
| Color | Hue/gradient | Cluster, score |
| Shape | Geometry | Category, type |
| Size | Scale | Importance, count |

### Color Scales

```python
widget = VectorSpace(
    points=data,
    color_field="score",           # Field to map
    color_scale="viridis",         # Scale: viridis, plasma, inferno, magma, cividis, turbo
    color_domain=[0, 100],         # Optional: explicit range
)
```

### Shapes

```python
widget = VectorSpace(
    points=data,
    shape_field="category",
    shape_map={
        "type_a": "sphere",        # Available: sphere, cube, cone,
        "type_b": "cube",          #            tetrahedron, octahedron, cylinder
        "type_c": "cone",
    }
)
```

### Size

```python
widget = VectorSpace(
    points=data,
    size_field="importance",
    size_range=[0.02, 0.15],       # Min/max point size
)
```

## Interactivity

### Events

```python
widget = VectorSpace(points=data)

@widget.on_click
def handle_click(point_id, point_data):
    print(f"Clicked: {point_id}")
    print(f"Data: {point_data}")

@widget.on_hover
def handle_hover(point_id, point_data):
    if point_id:
        print(f"Hovering: {point_id}")

@widget.on_selection
def handle_selection(point_ids, points_data):
    print(f"Selected {len(point_ids)} points")
```

### Selection

```python
widget.selected_points          # Get current selection
widget.select(["a", "b"])       # Select points
widget.clear_selection()        # Clear
```

### Camera

```python
widget.camera_position          # Get position [x, y, z]
widget.camera_target            # Get target [x, y, z]
widget.reset_camera()           # Reset to default
widget.focus_on(["a", "b"])     # Focus on specific points
```

## Options

```python
widget = VectorSpace(
    points=data,
    width=1000,
    height=700,
    background="#1a1a2e",         # Dark theme default
    show_axes=True,
    show_grid=True,
    axis_labels={"x": "PC1", "y": "PC2", "z": "PC3"},
    show_tooltip=True,
    tooltip_fields=["label", "x", "y", "z", "cluster"],
    selection_mode="click",       # "click" or "multi"
    use_instancing=True,          # Performance: instanced rendering
)
```

## Distance Metrics

Compute distances and visualize similarity relationships between points.

### Supported Metrics

| Metric | Description |
|--------|-------------|
| `euclidean` | Straight-line distance (L2 norm) |
| `cosine` | Angle-based distance (1 - cosine similarity) |
| `manhattan` | Sum of absolute differences (L1 norm) |
| `dot_product` | Negative dot product (higher = closer) |

### Color by Distance

```python
# Color points by distance from a reference
widget.color_by_distance("point_a")
widget.color_by_distance("point_a", metric="cosine")
```

### Find Neighbors

```python
# Find k nearest neighbors
neighbors = widget.find_neighbors("point_a", k=5)
# Returns: [("point_b", 0.1), ("point_c", 0.2), ...]

# Find neighbors within distance threshold
neighbors = widget.find_neighbors("point_a", threshold=0.5)
```

### Show Connections

```python
# Draw lines to k-nearest neighbors
widget.show_neighbors("point_a", k=5)

# Draw lines to all points within threshold
widget.show_neighbors("point_a", threshold=0.3)

# Manual connection settings
widget = VectorSpace(
    points=data,
    show_connections=True,
    k_neighbors=3,
    distance_metric="cosine",
    connection_color="#00ff00",
    connection_opacity=0.5,
)
```

### Compute Distances

```python
# Get distances from reference to all points
distances = widget.compute_distances("point_a")
# Returns: {"point_b": 0.1, "point_c": 0.5, ...}

# Use high-dimensional vectors (not just x,y,z)
distances = widget.compute_distances(
    "point_a",
    metric="cosine",
    vector_field="embedding"  # Use full embedding vector
)
```

## Export

```python
widget.to_json()                # Export points as JSON string
```

## Environment Support

| Environment | Supported |
|-------------|-----------|
| Marimo | ✅ |
| JupyterLab | ✅ |
| Jupyter Notebook | ✅ |
| VS Code | ✅ |
| Google Colab | ✅ |
| Databricks | ✅ |

## Related

- [anywidget](https://anywidget.dev/), custom Jupyter widgets made easy
- [anywidget-graph](https://github.com/GrafeoDB/anywidget-graph), graph visualization widget
- [Three.js](https://threejs.org/), 3D JavaScript library

## License

Apache-2.0
