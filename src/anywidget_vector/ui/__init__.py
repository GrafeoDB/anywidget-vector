"""UI module for anywidget-vector: CSS, the vendored Three.js, and the esbuild bundle.

The front end is TypeScript (ui/*.ts, backends/**/*.ts, static/*.ts), bundled by
esbuild into ui/dist/widget.js (scripts/build-esm.mjs, `npm run build`; CI and
tests/test_ui_bundle.py fail when it is stale), plus the standalone export page's
renderer into ui/dist/export.js (inlined by widget.py's to_html). Three.js and OrbitControls
(vendor/three.min.js, built by scripts/vendor) are inlined in front of the bundle
as a classic script that sets the global ``anywidgetVectorVendor``; the bundle
reads it through ui/vendor-globals.ts.
"""

from pathlib import Path

_UI_DIR = Path(__file__).parent


def _read_file(path: Path) -> str:
    """Read file contents."""
    return path.read_text(encoding="utf-8")


def get_vendor_js() -> str:
    """Three.js and OrbitControls, bundled (a script that sets ``anywidgetVectorVendor``; built by scripts/vendor)."""
    return _read_file(_UI_DIR / "vendor" / "three.min.js")


def get_export_js() -> str:
    """The standalone export page's renderer: ``dist/export.js``, bundled from ``export.ts`` by
    ``scripts/build-esm.mjs`` the same way as ``dist/widget.js``. ``widget.py``'s ``to_html`` inlines it into
    ``export.html`` after the page's ``DATA``/``OPTIONS`` constants."""
    return _read_file(_UI_DIR / "dist" / "export.js")


def get_css() -> str:
    """Get the widget's CSS."""
    return _read_file(_UI_DIR / "styles.css")


def get_esm() -> str:
    """The widget's ES module: the vendored Three.js, then the esbuild bundle of the TypeScript front end."""
    return f"""\
// === Auto-generated ESM bundle for anywidget-vector ===
// Three.js and OrbitControls are bundled (vendor/three.min.js, licenses in vendor/three.LICENSES.txt): the widget
// loads no code from a CDN, except the Grafeo WASM engine in WASM mode
{get_vendor_js()}
// === esbuild bundle of ui/*.ts and backends (ui/dist/widget.js) ===
{_read_file(_UI_DIR / "dist" / "widget.js")}"""
