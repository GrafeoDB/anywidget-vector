"""Tests for the ESM bundle built by ``anywidget_vector.ui``.

The bundler concatenates every JS file into one module, strips imports and
exports, and renames each backend's ``executeQuery``/``toPoints``. These tests
check that the result is still a valid module, that every renamed function
exists, that the browser engine version is pinned exactly once, and they run
the shipped backend code in Node against engine-shaped results.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from anywidget_vector.ui import _backend_clients, _strip_imports_exports, get_esm
from tests.support import NODE, run_node_module

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "anywidget_vector"
needs_node = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")

TOP_LEVEL_FUNCTION = re.compile(r"^(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE)
TOP_LEVEL_BINDING = re.compile(r"^(?:const|let|var)\s+(\w+)", re.MULTILINE)


@pytest.fixture(scope="module")
def esm() -> str:
    return get_esm()


def _wasm_version(esm: str) -> str:
    match = re.search(r'^const GRAFEO_WASM_VERSION = "([^"]+)";$', esm, re.MULTILINE)
    assert match, "GRAFEO_WASM_VERSION is not defined in the bundle"
    return match.group(1)


class TestBundleStructure:
    def test_get_esm_only_three_imports_and_default_export(self, esm):
        imports = [line for line in esm.splitlines() if line.lstrip().startswith("import ")]
        exports = [line for line in esm.splitlines() if line.lstrip().startswith("export ")]
        assert all("https://esm.sh/three@0.186.1" in line for line in imports), imports
        assert len(imports) == 2
        assert exports == ["export default { render };"]

    def test_get_esm_top_level_names_unique(self, esm):
        names = TOP_LEVEL_FUNCTION.findall(esm) + TOP_LEVEL_BINDING.findall(esm)
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        assert duplicates == []

    @pytest.mark.parametrize(
        "name",
        [
            "qdrantExecute",
            "qdrantToPoints",
            "pineconeExecute",
            "pineconeToPoints",
            "weaviateExecute",
            "weaviateToPoints",
            "grafeoServerExecute",
            "grafeoServerToPoints",
            "grafeoEmbedConnect",
            "grafeoEmbedDisconnect",
            "grafeoEmbedIsConnected",
            "grafeoEmbedExecuteQuery",
            "grafeoEmbedToPoints",
            "grafeoRowToPoint",
            "executeBackendQuery",
            "createCanvas",
            "createToolbar",
            "createSidebar",
            "createSettingsPanel",
            "createPropertiesPanel",
            "render",
        ],
    )
    def test_get_esm_defines_function(self, esm, name):
        assert name in TOP_LEVEL_FUNCTION.findall(esm)

    def test_get_esm_no_unrenamed_backend_functions(self, esm):
        names = set(TOP_LEVEL_FUNCTION.findall(esm))
        assert not names & {"executeQuery", "toPoints", "connect", "disconnect", "isConnected"}

    def test_strip_imports_exports(self):
        code = 'import { A } from "./a.js";\nexport const B = 1;\nexport async function c() {}\nexport default {};\n'
        assert _strip_imports_exports(code) == "const B = 1;\nasync function c() {}\n"

    @needs_node
    def test_get_esm_parses_as_module(self, esm, tmp_path):
        bundle = tmp_path / "bundle.mjs"
        bundle.write_text(esm, encoding="utf-8")
        assert NODE is not None
        proc = subprocess.run([NODE, "--check", str(bundle)], capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr

    @needs_node
    @pytest.mark.parametrize(
        "path",
        sorted(str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob("*.js")),
    )
    def test_each_js_file_parses_after_strip(self, path, tmp_path):
        module = tmp_path / "module.mjs"
        module.write_text(_strip_imports_exports((PACKAGE / path).read_text(encoding="utf-8")), encoding="utf-8")
        assert NODE is not None
        proc = subprocess.run([NODE, "--check", str(module)], capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr


class TestWasmPin:
    def test_wasm_package_referenced_once(self, esm):
        assert esm.count("@grafeo-db/wasm@") == 1
        assert "esm.sh/@grafeo-db" not in esm
        assert "const GRAFEO_WASM_CDN = `https://cdn.jsdelivr.net/npm/@grafeo-db/wasm@${GRAFEO_WASM_VERSION}`;" in esm

    def test_wasm_version_is_exact(self, esm):
        # An exact npm version (a pre-release such as 0.6.0-beta.1 included), never a range
        assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?", _wasm_version(esm))
        assert esm.count("GRAFEO_WASM_VERSION = ") == 1

    def test_wasm_version_in_lockstep_with_python_pin(self, esm):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        extras = project["optional-dependencies"]
        (grafeo_pin,) = extras["grafeo"]
        assert grafeo_pin in extras["dev"], "the dev extra should test the same grafeo range"
        specifier = Requirement(grafeo_pin).specifier
        lower = [spec.version for spec in specifier if spec.operator in (">=", "~=", "==")]
        assert len(lower) == 1, grafeo_pin
        # npm writes 0.6.0-beta.1 where PyPI writes 0.6.0b1: compare them as versions
        wasm = Version(_wasm_version(esm))
        assert Version(lower[0]) == wasm, (
            "bump GRAFEO_WASM_VERSION in backends/grafeo/embed.js together with the grafeo extra"
        )
        assert specifier.contains(wasm, prereleases=True), (grafeo_pin, str(wasm))

    @pytest.mark.parametrize(
        ("npm", "pypi"), [("0.6.0-beta.1", "0.6.0b1"), ("0.6.0", "0.6.0"), ("0.6.1-rc.2", "0.6.1rc2")]
    )
    def test_npm_and_pypi_spellings_compare_equal(self, npm, pypi):
        assert Version(npm) == Version(pypi)


def _backend_harness(test_code: str) -> str:
    """Shipped backend code (after strip and rename) followed by test code in the same scope."""
    return _backend_clients() + "\n// === test ===\n" + test_code


@needs_node
class TestBackendCodeInNode:
    def test_wasm_to_points_engine_shapes(self, tmp_path):
        out = run_node_module(
            _backend_harness(
                """
const rows = [
  { n: { _id: 7, _labels: ["Doc"], name: "a", embedding: new Float32Array([0.5, 0.25, 2]) }, distance: 0.1 },
  { "n.name": "b", "n.embedding": new Float32Array([1, 2, 3]), "id(n)": 8 },
  { id: 9n, vector: [Number.NaN, 4, 5], label: "c" },
  { name: "d", x: 1, y: "2", z: Infinity, embedding: [9, 9, 9] },
];
console.log(JSON.stringify(grafeoEmbedToPoints(rows)));
console.log(JSON.stringify(grafeoEmbedToPoints(null)));
"""
            ),
            tmp_path,
        )
        points_line, empty_line = out.strip().splitlines()
        points = json.loads(points_line)
        assert points[0] == {
            "id": "7",
            "name": "a",
            "labels": ["Doc"],
            "distance": 0.1,
            "vector": [0.5, 0.25, 2],
            "x": 0.5,
            "y": 0.25,
            "z": 2,
        }
        assert points[1] == {"id": "8", "name": "b", "vector": [1, 2, 3], "x": 1, "y": 2, "z": 3}
        assert points[2]["id"] == "9"
        assert (points[2]["x"], points[2]["y"], points[2]["z"]) == (0, 4, 5)
        assert (points[3]["x"], points[3]["y"], points[3]["z"]) == (1, 2, 0)
        assert json.loads(empty_line) == []

    def test_wasm_decimals_become_numbers(self, tmp_path):
        # grafeo 0.6: a GQL number with a point is an exact decimal, {$decimal: "..."} in WASM
        out = run_node_module(
            _backend_harness(
                """
const dec = (text) => ({ $decimal: text });
const rows = [
  { n: { _id: 1, _labels: ["Doc"], weight: dec("1.50"), tags: [dec("0.1"), "a"] }, score: dec("0.25") },
  { x: dec("1.5"), y: dec("-2"), z: dec("0.125"), embedding: [dec("9.0"), dec("8.0"), dec("7.0")] },
  { meta: { a: dec("3.0"), b: { $decimal: "1", other: 2 } }, embedding: [dec("0.5"), dec("0.25")] },
];
console.log(JSON.stringify(grafeoEmbedToPoints(rows)));
"""
            ),
            tmp_path,
        )
        points = json.loads(out)
        assert points[0] == {
            "id": "1",
            "labels": ["Doc"],
            "weight": 1.5,
            "tags": [0.1, "a"],
            "score": 0.25,
            "x": 0,
            "y": 0,
            "z": 0,
        }
        assert (points[1]["x"], points[1]["y"], points[1]["z"]) == (1.5, -2, 0.125)
        assert points[1]["vector"] == [9, 8, 7]
        # Only a map whose one key is $decimal is a decimal
        assert points[2]["meta"] == {"a": 3, "b": {"$decimal": "1", "other": 2}}
        assert (points[2]["x"], points[2]["y"], points[2]["z"]) == (0.5, 0.25, 0)

    def test_server_to_points_rows_as_arrays(self, tmp_path):
        response = {
            "columns": ["n", "distance", "n.name"],
            "rows": [[{"_id": 1, "_labels": ["Doc"], "embedding": [1, 0, 0]}, 0.5, "x"]],
            "execution_time_ms": 0.2,
        }
        out = run_node_module(
            _backend_harness(f"console.log(JSON.stringify(grafeoServerToPoints({json.dumps(response)})));"),
            tmp_path,
        )
        assert json.loads(out) == [
            {"id": "1", "labels": ["Doc"], "vector": [1, 0, 0], "distance": 0.5, "name": "x", "x": 1, "y": 0, "z": 0}
        ]

    def test_server_execute_request_and_error_detail(self, tmp_path):
        out = run_node_module(
            _backend_harness(
                """
const calls = [];
globalThis.fetch = async (url, init) => {
  calls.push({ url, body: JSON.parse(init.body), auth: init.headers.Authorization });
  if (calls.length === 1) return new Response(JSON.stringify({ columns: ["x"], rows: [[1]] }), { status: 200 });
  return new Response(JSON.stringify({ error: "bad_request", detail: "syntax error near MATCH" }), { status: 400 });
};
const config = { url: "http://srv:7474", authToken: "t", database: "docs" };
const ok = await grafeoServerExecute("MATCH (n) RETURN n", config);
let message = "";
try { await grafeoServerExecute("MATCH", { url: "http://srv:7474" }); } catch (err) { message = err.message; }
console.log(JSON.stringify({ calls, ok, message }));
"""
            ),
            tmp_path,
        )
        result = json.loads(out)
        assert result["calls"][0] == {
            "url": "http://srv:7474/query",
            "body": {"query": "MATCH (n) RETURN n", "language": "gql", "database": "docs"},
            "auth": "Bearer t",
        }
        assert result["ok"] == {"columns": ["x"], "rows": [[1]]}
        assert result["message"] == "Grafeo error: syntax error near MATCH"

    def test_wasm_connect_and_language_dispatch(self, tmp_path):
        out = run_node_module(
            _backend_harness(
                """
const log = [];
class FakeDatabase {
  execute(q) { log.push(["execute", q]); return [{ x: 1 }]; }
  executeWithLanguage(q, lang) { log.push(["executeWithLanguage", q, lang]); return []; }
  free() { log.push(["free"]); }
}
wasmBindingsPromise = Promise.resolve({ Database: FakeDatabase });
const before = grafeoEmbedIsConnected();
await grafeoEmbedConnect();
await grafeoEmbedExecuteQuery("MATCH (n) RETURN n", {});
await grafeoEmbedExecuteQuery("MATCH (n) RETURN n", { language: "cypher" });
await grafeoEmbedDisconnect();
console.log(JSON.stringify({ before, after: grafeoEmbedIsConnected(), log }));
"""
            ),
            tmp_path,
        )
        result = json.loads(out)
        assert result["before"] is False
        assert result["after"] is False
        assert result["log"] == [
            ["execute", "MATCH (n) RETURN n"],
            ["executeWithLanguage", "MATCH (n) RETURN n", "cypher"],
            ["free"],
        ]

    @pytest.mark.parametrize("content_type", ["application/wasm", "application/octet-stream"])
    def test_wasm_loader_wires_glue_and_binary(self, tmp_path, content_type):
        """The bundler-target wiring: import the glue, instantiate the binary, hand exports to the glue."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "package.json").write_text('{"type": "module"}', encoding="utf-8")
        (pkg / "grafeo_wasm_bg.js").write_text(
            "export let wasmExports = null;\n"
            "export function __wbg_set_wasm(exports) { wasmExports = exports; }\n"
            "export class Database { constructor() { this.ready = wasmExports !== null; } }\n",
            encoding="utf-8",
        )
        out = run_node_module(
            _backend_harness(
                f"""
import {{ pathToFileURL }} from "node:url";
const EMPTY_WASM = new Uint8Array([0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00]);
const fetched = [];
globalThis.fetch = async (url) => {{
  fetched.push(String(url));
  return new Response(EMPTY_WASM, {{ headers: {{ "content-type": {json.dumps(content_type)} }} }});
}};
const base = pathToFileURL({json.dumps(str(pkg))}).href;
const bindings = await loadWasmBindings(base);
const again = await loadWasmBindings(base);
console.log(JSON.stringify({{ ready: new bindings.Database().ready, same: bindings === again, fetched, base }}));
"""
            ),
            tmp_path,
        )
        result = json.loads(out)
        assert result["ready"] is True
        assert result["same"] is True
        assert set(result["fetched"]) == {result["base"] + "/grafeo_wasm_bg.wasm"}

    def test_properties_row_renders_data_as_text(self, tmp_path):
        icons = _strip_imports_exports((PACKAGE / "static" / "icons.js").read_text(encoding="utf-8"))
        properties = _strip_imports_exports((PACKAGE / "ui" / "properties.js").read_text(encoding="utf-8"))
        fake_dom = """
const document = {
  createElement(tag) {
    return {
      tag, children: [], className: "", title: "", text: "", html: null,
      appendChild(child) { this.children.push(child); return child; },
      append(...kids) { this.children.push(...kids); },
      set textContent(v) { this.text = v; },
      get textContent() { return this.text + this.children.map((c) => c.textContent).join(""); },
      set innerHTML(v) { this.html = v; },
    };
  },
};
"""
        test_code = """
const container = document.createElement("div");
addPropertyRow(container, "<b>key</b>", '<img src=x onerror="alert(1)">');
const row = container.children[0];
console.log(JSON.stringify({
  html: [row.html, ...row.children.map((c) => c.html)],
  text: row.children.map((c) => c.textContent),
  title: row.children[1].title,
}));
"""
        out = run_node_module(fake_dom + icons + properties + test_code, tmp_path)
        result = json.loads(out)
        assert result["html"] == [None, None, None]
        assert result["text"] == ["<b>key</b>", '<img src=x onerror="alert(1)">']
        assert result["title"] == '<img src=x onerror="alert(1)">'


class TestNoMarkupFromPointData:
    def test_canvas_tooltip_uses_text_content(self):
        canvas = (PACKAGE / "ui" / "canvas.js").read_text(encoding="utf-8")
        body = canvas[canvas.index("function showTooltip(") : canvas.index("function hideTooltip(")]
        assert "innerHTML" not in body
        assert "textContent" in body

    def test_sidebar_stat_row_uses_text_content(self):
        sidebar = (PACKAGE / "ui" / "sidebar.js").read_text(encoding="utf-8")
        body = sidebar[sidebar.index("function addStatRow(") : sidebar.index("function rangeStr(")]
        assert "innerHTML" not in body
