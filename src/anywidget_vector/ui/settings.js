// Settings panel component for VectorSpace widget
import { ICONS } from "../static/icons.js";
import { BACKENDS } from "./constants.js";

export function createSettingsPanel(model, callbacks) {
  const panel = document.createElement("div");
  panel.className = "avs-panel avs-panel-right";

  const inner = document.createElement("div");
  inner.className = "avs-panel-inner";
  panel.appendChild(inner);

  // Header
  const header = document.createElement("div");
  header.className = "avs-panel-header";
  header.innerHTML = `<span>Settings</span>`;
  const closeBtn = document.createElement("button");
  closeBtn.className = "avs-btn avs-btn-icon";
  closeBtn.innerHTML = ICONS.close;
  closeBtn.addEventListener("click", () => callbacks.onClose?.());
  header.appendChild(closeBtn);
  inner.appendChild(header);

  // Backend selector
  const backendGroup = createFormGroup("Backend");
  const backendSelect = document.createElement("select");
  backendSelect.className = "avs-select";
  Object.entries(BACKENDS).forEach(([key, config]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = `${config.name} (${config.side})`;
    backendSelect.appendChild(opt);
  });
  backendSelect.value = model.get("backend") || "qdrant";
  backendSelect.addEventListener("change", () => {
    model.set("backend", backendSelect.value);
    model.save_changes();
    updateConnectionFields(connFields, model);
  });
  backendGroup.appendChild(backendSelect);
  inner.appendChild(backendGroup);

  // Connection fields container
  const connFields = document.createElement("div");
  connFields.className = "avs-connection-fields";
  inner.appendChild(connFields);

  // Embedding config section
  const embHeader = document.createElement("div");
  embHeader.className = "avs-section-header";
  embHeader.textContent = "Embedding (for text search)";
  inner.appendChild(embHeader);

  const embProviderGroup = createFormGroup("Provider");
  const embProviderSelect = document.createElement("select");
  embProviderSelect.className = "avs-select";
  [{ v: "openai", l: "OpenAI" }, { v: "cohere", l: "Cohere" }].forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.v;
    opt.textContent = p.l;
    embProviderSelect.appendChild(opt);
  });
  const embConfig = model.get("embedding_config") || {};
  embProviderSelect.value = embConfig.provider || "openai";
  embProviderGroup.appendChild(embProviderSelect);
  inner.appendChild(embProviderGroup);

  const embKeyGroup = createFormGroup("API Key");
  const embKeyInput = document.createElement("input");
  embKeyInput.type = "password";
  embKeyInput.className = "avs-input";
  embKeyInput.placeholder = "sk-...";
  embKeyInput.value = embConfig.apiKey || "";
  embKeyGroup.appendChild(embKeyInput);
  inner.appendChild(embKeyGroup);

  const embModelGroup = createFormGroup("Model");
  const embModelInput = document.createElement("input");
  embModelInput.type = "text";
  embModelInput.className = "avs-input";
  embModelInput.placeholder = "text-embedding-3-small";
  embModelInput.value = embConfig.model || "";
  embModelGroup.appendChild(embModelInput);
  inner.appendChild(embModelGroup);

  // Update embedding config on change
  const updateEmbedding = () => {
    model.set("embedding_config", {
      provider: embProviderSelect.value,
      apiKey: embKeyInput.value,
      model: embModelInput.value,
    });
    model.save_changes();
  };
  embProviderSelect.addEventListener("change", updateEmbedding);
  embKeyInput.addEventListener("input", updateEmbedding);
  embModelInput.addEventListener("input", updateEmbedding);

  // Query limit
  const limitGroup = createFormGroup("Result Limit");
  const limitInput = document.createElement("input");
  limitInput.type = "number";
  limitInput.className = "avs-input";
  limitInput.min = "1";
  limitInput.max = "10000";
  limitInput.value = model.get("query_limit") || 100;
  limitInput.addEventListener("input", () => {
    model.set("query_limit", parseInt(limitInput.value, 10) || 100);
    model.save_changes();
  });
  limitGroup.appendChild(limitInput);
  inner.appendChild(limitGroup);

  // Error display
  const errorDiv = document.createElement("div");
  errorDiv.className = "avs-error";
  errorDiv.style.display = "none";
  inner.appendChild(errorDiv);

  model.on("change:query_error", () => {
    const err = model.get("query_error");
    if (err) {
      errorDiv.textContent = err;
      errorDiv.style.display = "block";
    } else {
      errorDiv.style.display = "none";
    }
  });

  // Initialize connection fields
  updateConnectionFields(connFields, model);

  return {
    element: panel,
    open: () => panel.classList.add("avs-open"),
    close: () => panel.classList.remove("avs-open"),
    toggle: () => panel.classList.toggle("avs-open"),
    isOpen: () => panel.classList.contains("avs-open"),
  };
}

function createFormGroup(label) {
  const group = document.createElement("div");
  group.className = "avs-form-group";
  const lbl = document.createElement("label");
  lbl.className = "avs-label";
  lbl.textContent = label;
  group.appendChild(lbl);
  return group;
}

function updateConnectionFields(container, model) {
  container.innerHTML = "";

  const backend = model.get("backend") || "qdrant";
  const config = model.get("backend_config") || {};
  const backendInfo = BACKENDS[backend];

  // URL field (for browser-side backends)
  if (backendInfo.side === "browser") {
    const urlGroup = createFormGroup("URL");
    const urlInput = document.createElement("input");
    urlInput.type = "text";
    urlInput.className = "avs-input";
    urlInput.placeholder = backend === "qdrant" ? "http://localhost:6333" :
                           backend === "pinecone" ? "https://xxx.pinecone.io" :
                           "http://localhost:8080";
    urlInput.value = config.url || "";
    urlInput.addEventListener("input", () => updateBackendConfig(model, container));
    urlGroup.appendChild(urlInput);
    container.appendChild(urlGroup);
  }

  // API Key (for backends with auth)
  if (backendInfo.hasAuth) {
    const keyGroup = createFormGroup("API Key");
    const keyInput = document.createElement("input");
    keyInput.type = "password";
    keyInput.className = "avs-input";
    keyInput.placeholder = "API Key (optional for local)";
    keyInput.value = config.apiKey || "";
    keyInput.addEventListener("input", () => updateBackendConfig(model, container));
    keyGroup.appendChild(keyInput);
    container.appendChild(keyGroup);
  }

  // Collection/Index/Class/Table name
  let nameLabel, namePlaceholder;
  if (backendInfo.hasCollection) {
    nameLabel = "Collection";
    namePlaceholder = "my_collection";
  } else if (backendInfo.hasIndex) {
    nameLabel = "Index";
    namePlaceholder = "my-index";
  } else if (backendInfo.hasClass) {
    nameLabel = "Class";
    namePlaceholder = "MyClass";
  } else if (backendInfo.hasTable) {
    nameLabel = "Table";
    namePlaceholder = "my_table";
  }

  if (nameLabel) {
    const nameGroup = createFormGroup(nameLabel);
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.className = "avs-input";
    nameInput.placeholder = namePlaceholder;
    nameInput.value = config.collection || config.index || config.className || config.table || "";
    nameInput.dataset.field = nameLabel.toLowerCase();
    nameInput.addEventListener("input", () => updateBackendConfig(model, container));
    nameGroup.appendChild(nameInput);
    container.appendChild(nameGroup);
  }

  // Namespace (Pinecone specific)
  if (backend === "pinecone") {
    const nsGroup = createFormGroup("Namespace");
    const nsInput = document.createElement("input");
    nsInput.type = "text";
    nsInput.className = "avs-input";
    nsInput.placeholder = "(optional)";
    nsInput.value = config.namespace || "";
    nsInput.addEventListener("input", () => updateBackendConfig(model, container));
    nsGroup.appendChild(nsInput);
    container.appendChild(nsGroup);
  }

  // Python-side backends note
  if (backendInfo.side === "python") {
    const note = document.createElement("div");
    note.className = "avs-note";
    note.textContent = "Configure this backend in Python using set_backend()";
    container.appendChild(note);
  }
}

function updateBackendConfig(model, container) {
  const backend = model.get("backend") || "qdrant";
  const inputs = container.querySelectorAll(".avs-input");
  const config = {};

  inputs.forEach((input, idx) => {
    if (!input.value) return;
    const placeholder = input.placeholder.toLowerCase();
    if (placeholder.includes("http") || placeholder.includes("localhost")) {
      config.url = input.value;
    } else if (placeholder.includes("api key")) {
      config.apiKey = input.value;
    } else if (placeholder.includes("collection")) {
      config.collection = input.value;
    } else if (placeholder.includes("index")) {
      config.index = input.value;
    } else if (placeholder.includes("class")) {
      config.className = input.value;
    } else if (placeholder.includes("table")) {
      config.table = input.value;
    } else if (placeholder.includes("optional")) {
      config.namespace = input.value;
    }
  });

  model.set("backend_config", config);
  model.save_changes();
}
