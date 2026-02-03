// Toolbar component for VectorSpace widget
import { ICONS } from "../static/icons.js";
import { BACKENDS } from "./constants.js";

export function createToolbar(model, callbacks) {
  const toolbar = document.createElement("div");
  toolbar.className = "avs-toolbar";

  // Backend indicator (shows current backend name)
  const backendLabel = document.createElement("span");
  backendLabel.className = "avs-backend-label";
  backendLabel.textContent = BACKENDS[model.get("backend")]?.name || "Qdrant";
  toolbar.appendChild(backendLabel);

  // Query input (native format for selected backend)
  const queryInput = document.createElement("input");
  queryInput.type = "text";
  queryInput.className = "avs-query-input";
  queryInput.placeholder = getPlaceholder(model.get("backend"));
  queryInput.value = model.get("query_input") || "";
  queryInput.title = getHelp(model.get("backend"));
  queryInput.addEventListener("input", () => {
    model.set("query_input", queryInput.value);
    model.save_changes();
  });
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      callbacks.onRunQuery?.();
    }
  });
  toolbar.appendChild(queryInput);

  // Run button
  const runBtn = document.createElement("button");
  runBtn.className = "avs-btn avs-btn-primary";
  runBtn.innerHTML = ICONS.play;
  runBtn.title = "Run Query";
  runBtn.addEventListener("click", () => callbacks.onRunQuery?.());
  toolbar.appendChild(runBtn);

  // Settings button with status dot
  const settingsBtn = document.createElement("button");
  settingsBtn.className = "avs-btn avs-settings-btn";
  const statusDot = document.createElement("span");
  statusDot.className = "avs-status-dot";
  updateStatusDot(statusDot, model.get("connection_status") || "disconnected");
  settingsBtn.innerHTML = ICONS.settings;
  settingsBtn.appendChild(statusDot);
  settingsBtn.title = "Settings";
  settingsBtn.addEventListener("click", () => callbacks.onToggleSettings?.());
  toolbar.appendChild(settingsBtn);

  // Properties toggle button
  const propsBtn = document.createElement("button");
  propsBtn.className = "avs-btn";
  propsBtn.innerHTML = ICONS.cube;
  propsBtn.title = "Properties";
  propsBtn.addEventListener("click", () => callbacks.onToggleProperties?.());
  toolbar.appendChild(propsBtn);

  // Model change listeners
  model.on("change:connection_status", () => {
    updateStatusDot(statusDot, model.get("connection_status"));
  });

  model.on("change:backend", () => {
    const backend = model.get("backend");
    backendLabel.textContent = BACKENDS[backend]?.name || backend;
    queryInput.placeholder = getPlaceholder(backend);
    queryInput.title = getHelp(backend);
  });

  return {
    element: toolbar,
    runBtn,
    setLoading: (loading) => {
      if (loading) {
        runBtn.innerHTML = ICONS.loader;
        runBtn.classList.add("avs-loading");
        runBtn.disabled = true;
      } else {
        runBtn.innerHTML = ICONS.play;
        runBtn.classList.remove("avs-loading");
        runBtn.disabled = false;
      }
    },
  };
}

function updateStatusDot(dot, status) {
  dot.className = `avs-status-dot avs-status-${status}`;
}

function getPlaceholder(backend) {
  const placeholders = {
    qdrant: '{"vector": [...], "limit": 10}',
    pinecone: '{"vector": [...], "topK": 10}',
    weaviate: '{ Get { Class(limit: 10) { ... } } }',
    chroma: '{"query_embeddings": [...], "n_results": 10}',
    lancedb: 'category = "tech" AND year > 2020',
    grafeo: 'MATCH (n:Vector) RETURN n LIMIT 10',
  };
  return placeholders[backend] || "Enter query...";
}

function getHelp(backend) {
  const help = {
    qdrant: "JSON: vector, filter, limit, recommend, ids",
    pinecone: "JSON: vector, filter, topK, namespace",
    weaviate: "GraphQL: nearVector, nearText, where",
    chroma: "Dict: query_embeddings, where, n_results",
    lancedb: "SQL WHERE clause for filtering",
    grafeo: "Grafeo query language",
  };
  return help[backend] || "";
}
