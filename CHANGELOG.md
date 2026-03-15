# Changelog

## 0.3.0 (unreleased)

### New Features

- **Distance metrics sidebar**: Distance section with metric selector (euclidean, cosine, manhattan, dot product), configurable k-neighbors (0-50), and live nearest-neighbor display for the selected point
- **Dimension mapping display**: Sidebar now shows active visual mapping fields: color field, size range, shape field and unique shape count

### Improvements

- Improved sidebar styling and layout

## 0.2.8 (2026-03-15)

### New Features

- **6D parallel coordinates example**: Fashion-MNIST demo with PCA across 6+ dimensions, interactive axis mapping, and shape mapping to categorical labels

## 0.2.7 (2026-03-15)

### New Features

- **Dark/light mode toggle**: `dark_mode` trait with real-time CSS color scheme switching and theme-aware styling across all panels

## 0.2.6 (2026-03-15)

### New Features

- **NumPy array support**: `add_numpy()` method for adding points from arrays with automatic PCA projection for high-dimensional data (D > 3)
- **Dimensionality reduction**: `project()` method with PCA, t-SNE and UMAP support; `set_vectors()` for storing high-dimensional vectors separately
- **Example scripts**: Projection demo and numpy integration examples

### Improvements

- High-dimensional vector storage without syncing to JavaScript
- Coordinate normalization after projection
- Added demo screenshot to README

## 0.2.5 (2026-03-04)

### Bug Fixes

- Fixed lasso selection stability issues
- Removed problematic custom traitlets implementation

### Improvements

- Added keyboard shortcuts: F to fit view, Escape to clear selection
- Better visual feedback for selection modes
- Cleaner toolbar layout with integrated mode controls

## 0.2.4 (2026-03-02)

### New Features

- **Zoom and pan controls**: Zoom in, zoom out and fit-to-view buttons in the toolbar
- **Box selection mode**: New selection mode alongside click and multi-select, with visual feedback during selection
- **HTML export**: `to_html()` and `save_html()` methods for self-contained HTML output with embedded data and Three.js

### Improvements

- Improved camera fitting algorithm for better initial view framing
- Updated README with comprehensive usage examples
- Updated dependencies

## 0.2.3 (2026-02-12)

### New Features

- **Sidebar explorer**: Three collapsible sections: collections browser, dimensions explorer (point count, dimensionality, axis ranges) and clusters explorer (grouped by color field with sizes)
- **Browser-side Grafeo backend**: JavaScript client for Grafeo server and WASM-embedded queries
- **Demo module**: Reference implementation showing various widget features

### Improvements

- Consistency pass across all backend modules
- Ruff configuration tuned for marimo compatibility

## 0.2.2 (2026-02-07)

### New Features

- **Streaming factory methods**: `from_numpy()`, `from_umap()` and `from_arrays()` constructors for various data formats

### Improvements

- Added Apache 2.0 license
- Expanded test suite with 194 additional test cases
- ESM bundle aggregation for widget JavaScript

## 0.2.1 (2026-02-03)

### New Features

- **Multi-backend architecture**: Six backends: Qdrant, Pinecone, Weaviate (browser-side REST), Chroma, LanceDB, Grafeo (Python-side)
- **Modular UI**: Separated rendering into canvas, settings, properties and toolbar components
- **Backend factory methods**: `from_qdrant()`, `from_pinecone()`, `from_weaviate()`, `from_chroma()`, `from_lancedb()`, `from_grafeo()`
- **Event system**: `on_click()`, `on_hover()` and `on_selection()` decorators with callback signatures
- **CI/CD**: GitHub Actions pipelines for testing and PyPI publishing

### Improvements

- Refactored monolithic widget into modular component architecture
- Added README with usage examples

## 0.1.0 (2026-02-03)

- Initial release: Three.js-based interactive 3D vector visualization with instanced rendering, six shape types, continuous and categorical color mapping, orbit controls, hover tooltips, axes/grid display and raycast-based selection
