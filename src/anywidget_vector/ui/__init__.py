"""UI module aggregation - loads CSS and JS components."""

from pathlib import Path

_UI_DIR = Path(__file__).parent
_STATIC_DIR = _UI_DIR.parent / "static"
_BACKENDS_DIR = _UI_DIR.parent / "backends"


def _read_file(path: Path) -> str:
    """Read file contents."""
    return path.read_text(encoding="utf-8")


def get_css() -> str:
    """Get aggregated CSS."""
    return _read_file(_UI_DIR / "styles.css")


def get_esm() -> str:
    """Get aggregated ESM JavaScript.

    Combines all UI components into a single module.
    """
    # Read component files
    icons_js = _read_file(_STATIC_DIR / "icons.js")
    constants_js = _read_file(_UI_DIR / "constants.js")
    toolbar_js = _read_file(_UI_DIR / "toolbar.js")
    settings_js = _read_file(_UI_DIR / "settings.js")
    properties_js = _read_file(_UI_DIR / "properties.js")
    canvas_js = _read_file(_UI_DIR / "canvas.js")

    # Read browser-side backend clients
    qdrant_client = _read_file(_BACKENDS_DIR / "qdrant" / "client.js")
    pinecone_client = _read_file(_BACKENDS_DIR / "pinecone" / "client.js")
    weaviate_client = _read_file(_BACKENDS_DIR / "weaviate" / "client.js")

    # Build combined ESM
    esm = f"""
// === Auto-generated ESM bundle for anywidget-vector ===
import * as THREE from "https://esm.sh/three@0.160.0";
import {{ OrbitControls }} from "https://esm.sh/three@0.160.0/addons/controls/OrbitControls.js";

// === Icons ===
{_strip_imports_exports(icons_js)}

// === Constants ===
{_strip_imports_exports(constants_js)}

// === Backend Clients ===
// Qdrant
{_strip_imports_exports(qdrant_client).replace("function executeQuery", "async function qdrantExecute").replace("function toPoints", "function qdrantToPoints")}

// Pinecone
{_strip_imports_exports(pinecone_client).replace("function executeQuery", "async function pineconeExecute").replace("function toPoints", "function pineconeToPoints")}

// Weaviate
{_strip_imports_exports(weaviate_client).replace("function executeQuery", "async function weaviateExecute").replace("function toPoints", "function weaviateToPoints")}

// Unified query executor
async function executeBackendQuery(model) {{
  const backend = model.get("backend");
  const query = model.get("query_input");
  const config = model.get("backend_config") || {{}};

  let response, points;

  if (backend === "qdrant") {{
    response = await qdrantExecute(query, config);
    points = qdrantToPoints(response);
  }} else if (backend === "pinecone") {{
    response = await pineconeExecute(query, config);
    points = pineconeToPoints(response);
  }} else if (backend === "weaviate") {{
    const className = config.className || config.class || "Vector";
    response = await weaviateExecute(query, config);
    points = weaviateToPoints(response, className);
  }} else {{
    throw new Error(`Browser backend not supported: ${{backend}}`);
  }}

  return points;
}}

// === Toolbar ===
{_strip_imports_exports(toolbar_js)}

// === Settings Panel ===
{_strip_imports_exports(settings_js)}

// === Properties Panel ===
{_strip_imports_exports(properties_js)}

// === Canvas (Three.js) ===
{_strip_imports_exports(canvas_js)}

// === Main Render Function ===
function render({{ model, el }}) {{
  const wrapper = document.createElement("div");
  wrapper.className = "avs-wrapper";
  wrapper.style.width = model.get("width") + "px";
  el.appendChild(wrapper);

  let settingsPanel = null;
  let propertiesPanel = null;
  let toolbarUI = null;

  if (model.get("show_toolbar")) {{
    toolbarUI = createToolbar(model, {{
      onRunQuery: () => runQuery(),
      onToggleSettings: () => settingsPanel?.toggle(),
      onToggleProperties: () => propertiesPanel?.toggle(),
    }});
    wrapper.appendChild(toolbarUI.element);
  }}

  const main = document.createElement("div");
  main.className = "avs-main";
  main.style.height = model.get("height") + "px";
  wrapper.appendChild(main);

  const canvasContainer = document.createElement("div");
  canvasContainer.className = "avs-canvas-container";
  canvasContainer.style.width = "100%";
  canvasContainer.style.height = "100%";
  main.appendChild(canvasContainer);

  if (model.get("show_settings")) {{
    settingsPanel = createSettingsPanel(model, {{
      onClose: () => settingsPanel?.close(),
    }});
    main.appendChild(settingsPanel.element);
  }}

  if (model.get("show_properties")) {{
    propertiesPanel = createPropertiesPanel(model, {{
      onClose: () => propertiesPanel?.close(),
    }});
    main.appendChild(propertiesPanel.element);
  }}

  const canvas = createCanvas(model, canvasContainer, {{}});

  async function runQuery() {{
    if (toolbarUI) toolbarUI.setLoading(true);

    try {{
      model.set("query_error", null);
      model.set("connection_status", "connecting");
      model.save_changes();

      const backend = model.get("backend");
      const backendInfo = BACKENDS[backend];

      if (backendInfo && backendInfo.side === "browser") {{
        const points = await executeBackendQuery(model);
        model.set("points", points);
        model.set("connection_status", "connected");
        model.save_changes();
      }} else {{
        model.set("_execute_query", Date.now());
        model.save_changes();
      }}
    }} catch (err) {{
      model.set("query_error", err.message);
      model.set("connection_status", "error");
      model.save_changes();
      console.error("Query error:", err);
    }} finally {{
      if (toolbarUI) toolbarUI.setLoading(false);
    }}
  }}

  return () => {{ canvas.cleanup(); }};
}}

export default {{ render }};
"""
    return esm


def _strip_imports_exports(code: str) -> str:
    """Remove import and export statements from JS code."""
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import "):
            continue
        if stripped.startswith("export function "):
            line = line.replace("export function ", "function ")
        elif stripped.startswith("export async function "):
            line = line.replace("export async function ", "async function ")
        elif stripped.startswith("export const "):
            line = line.replace("export const ", "const ")
        elif stripped.startswith("export default"):
            continue
        lines.append(line)
    return "\n".join(lines)
