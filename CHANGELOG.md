# Changelog

## 0.4.0 (unreleased)

Requires Python 3.12 or later; the Grafeo backend requires grafeo 0.6. See "Upgrading to 0.4" in the README.

### Breaking

- **Grafeo 0.6**: The `grafeo` extra requires `grafeo>=0.6.0,<0.7`; grafeo 0.5.x is no longer supported. Grafeo 0.6 changes query results and files, and these reach the widget's Grafeo backend:
  - Every database is a single file. The first read-write open of a 0.5.x database migrates it and keeps the old file as `<file>.pre-0.6`, which 0.5.x needs to go back; opening a directory that is not a 0.5.x database fails
  - A GQL number with a point is an exact decimal, so `0.0/0.0` and `1/0` fail the query (division by zero) where they gave NaN or null, and so does integer overflow. Use exponent literals (`0.0e0/0.0e0`) for IEEE floats
  - A `WHERE` right after `INSERT`, `CREATE`, `MERGE` or `DELETE` is an error, and an `INSERT` alone returns no rows, so running one from the toolbar clears the scene
  - GQL `ORDER BY` puts nulls last in both directions
- **WASM engine 0.6**: The browser-side Grafeo backend loads `@grafeo-db/wasm` 0.6.0 (was 0.5.0 in 0.3.2) from jsDelivr. The version is set once, `GRAFEO_WASM_VERSION` in `backends/grafeo/embed.js`, and a test keeps it in lockstep with the Python pin (npm and PyPI spellings of a pre-release, such as `0.6.1-rc.2` and `0.6.1rc2`, compare as the same version)

### Improvements

- **Decimals become numbers**: Grafeo 0.6 returns decimals (`decimal.Decimal` in Python, `{"$decimal": "1.50"}` in WASM). The widget turns them into floats in every Grafeo mode, also inside lists, maps and node properties, so `RETURN 0.5 AS score` maps to color and size, `1.5 AS x` places a point, and a plain list `[1.0, 0.0, 0.0]` still gives a vector. Without this, Python points could not be sent to the browser as JSON and WASM points landed at the origin
- **Vector search errors**: A query vector of the wrong size or with NaN is a regular `grafeo.GrafeoError` in Grafeo 0.6 (0.5.44 panicked, and its WASM build trapped), shown in the widget with the sizes it names. The panic guard stays for any other engine bug
- **Three.js 0.186.1**: The widget and `to_html()` load Three.js 0.186.1 (was 0.160.0) from esm.sh; Three.js dropped WebGL 1 in 0.163, so a browser needs WebGL 2
- **Dependencies**: All locked dependencies refreshed (`uv lock --upgrade`); the `dev` extra includes grafeo, numpy and packaging so the full test suite runs everywhere. CI and the release workflow use uv (`uv lock --check`, `uv sync --locked`, `uv build`) and current GitHub Actions (checkout v7, setup-uv v10, setup-node v7, upload-artifact v7, download-artifact v8). The `tool.uv.dev-dependencies` table moved to `[dependency-groups]`, and ruff leaves Markdown files alone
- **Engine contract tests**: The tests that pin Grafeo behavior now cover 0.6: error classes and messages for unknown metrics, zero dimensions, wrong-size and NaN query vectors and NaN in an indexed vector, filter operators (`$in`, `$ne`), tied distances, decimal literals and an `INSERT` without rows. `tests/js/wasm_smoke.mjs` checks decimals and the wrong-size error in WASM
- **Same points in every Grafeo mode**: Embedded, server and WASM results go through the same rules: node values (`RETURN n`) contribute their properties, labels and id, unaliased columns such as `n.embedding` or `id(n)` are recognized, and explicit `x`/`y`/`z` win over the first vector components
- **Server errors**: grafeo-server error responses show their `detail` text instead of raw JSON
- **Scheduled engine check**: A weekly workflow runs the suite against the newest grafeo on PyPI (pre-releases included) and a smoke test against the pinned and the newest `@grafeo-db/wasm`
- **Python 3.15**: Tested on Python 3.15; CI runs the suite on 3.12 to 3.15 and the classifiers list 3.12 to 3.15

### Bug Fixes

- **Embedded Grafeo queries**: Queries failed with "'QueryBuilder' object is not iterable" because the client called `GrafeoDB.query()`, which returns a query builder. It now calls `execute()`
- **WASM mode**: `@grafeo-db/wasm` is published for bundlers since 0.5.x, so importing it from esm.sh no longer yields a working `Database`. The loader now imports the JS glue and instantiates the binary itself. WASM vectors (`Float32Array`) are converted to arrays, so they place points and sync to Python
- **Engine panics**: A Grafeo panic (for example a vector search with the wrong number of dimensions) escaped the query callback because pyo3 raises it as a `BaseException`. It is now reported as a query error
- **Query status**: A Python-side query with an empty result left the status at "connecting" and kept the old points. The result now replaces the points and the status becomes "connected"; a new query clears the previous error
- **NaN and infinity in points**: These values are not valid JSON and one NaN coordinate broke camera framing for the whole scene. Top-level non-finite values are now replaced with `None` (with a `RuntimeWarning`), and distance and focus methods treat `None` coordinates as 0
- **HTML injection**: Point labels and values from a database were inserted as HTML in the tooltip, the properties panel and the exported HTML page. They are now set as text. `to_html()` also escapes the title and keeps a `</script>` inside the data from ending the script
- **Vector edge cases**: `add_numpy()` with a single high-dimensional row, a 1-D or one-column array, or ids/labels/metadata of the wrong length raised an unrelated `IndexError`; it now works (single row) or raises a clear `ValueError`. `project()` handles a single point and reports ragged or non-finite vectors clearly. `compute_distances(vector_field=...)` leaves out points without that vector instead of returning infinity, and raises on vectors of different lengths instead of truncating them
- **Version**: `anywidget_vector.__version__` reported 0.2.5; it now reads the installed package version

## 0.3.2 (2026-03-16)

### Improvements

- **Marimo reactivity fix**: Removed camera and hover JS-to-Python sync to prevent continuous cell re-execution. Only user-initiated actions (selection, mode change) now trigger marimo reactive updates
- **Custom scroll zoom**: Replaced OrbitControls zoom with a custom wheel handler for much finer granularity
- **Selection hides completely**: Lasso/box selection now fully hides non-selected points (scale-to-zero for instanced meshes) instead of dimming
- **Auto zoom-to-fit on selection**: Camera automatically frames the selected points after lasso/box selection
- **Search filter modes**: Typing in the search bar dims non-matching points as a preview, pressing Run/Enter hides them completely
- **Hover via callback**: Properties panel hover now uses a direct JS callback instead of model sync, eliminating unnecessary Python round-trips

### Bug Fixes

- **setSelection scoping**: Moved `setSelection` helper to `createCanvas` scope so lasso/box/click handlers can access it
- **Camera debounce variable**: Fixed `_cameraDebounce` lexical declaration error by moving it to the correct scope

## 0.3.1 (2026-03-16)

### New Features

- **Lasso selection**: New lasso mode for freehand point selection in the 3D canvas, with point-in-polygon hit testing
- **Selection highlighting**: Selected points show wireframe highlight rings and non-selected points are dimmed to 15% brightness
- **Auto-sizing**: Width defaults to 100% (fill container), height defaults to 1:1 aspect ratio. Both can still be set to fixed pixel values

### Bug Fixes

- **Properties panel**: Panel is now always created (previously skipped when `show_properties=False`), so the toolbar button always works. Starts closed unless `show_properties=True`
- **Distance metric feedback**: Changing the metric now auto-enables k=5 connections when a point is selected, giving immediate visual feedback

### Improvements

- Reduced scroll zoom sensitivity (`zoomSpeed` halved to 0.5)
- Search filter dimming increased from 12% to 6% opacity for clearer visual contrast
- Camera no longer resets on every point update (only on initial load)
- Cross-widget filtering: example updated so VectorSpace lasso selection feeds back into ParallelCoordinates dimming via marimo reactivity

## 0.3.0 (2026-03-16)

### New Features

- **Distance metrics sidebar**: Distance section with metric selector (euclidean, cosine, manhattan, dot product), configurable k-neighbors (0-50) and live nearest-neighbor display for the selected point
- **Dimension mapping display**: Sidebar now shows active visual mapping fields: color field, size range, shape field and unique shape count

### Improvements

- Improved sidebar styling and layout

## 0.2.8 (2026-03-15)

### New Features

- **6D parallel coordinates example**: Fashion-MNIST demo with PCA across 6+ dimensions, interactive axis mapping and shape mapping to categorical labels

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
