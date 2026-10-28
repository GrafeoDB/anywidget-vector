/**
 * Grafeo WASM browser-side client for vector queries.
 * Lazy-loads @grafeo-db/wasm from the jsDelivr CDN on first use.
 */
import { grafeoRowToPoint } from "./points.js";

// The only place the browser engine version is set. Keep it exact and in
// lockstep with the `grafeo` Python extra in pyproject.toml.
export const GRAFEO_WASM_VERSION = "0.6.0";
export const GRAFEO_WASM_CDN = `https://cdn.jsdelivr.net/npm/@grafeo-db/wasm@${GRAFEO_WASM_VERSION}`;

let wasmDb = null;
let wasmBindingsPromise = null;

/**
 * Load the wasm-bindgen bindings once per page.
 *
 * @grafeo-db/wasm is built with wasm-bindgen's bundler target: it has no init
 * function and its entry point imports the .wasm file as an ES module, which
 * browsers cannot do (esm.sh inlines it as raw bytes, so `new Database()`
 * fails). The JS glue is imported directly and the binary is instantiated
 * here with the glue as its import object.
 *
 * `baseUrl` exists for tests/js/wasm_smoke.mjs, which loads a local package.
 */
export function loadWasmBindings(baseUrl = GRAFEO_WASM_CDN) {
  if (!wasmBindingsPromise) {
    wasmBindingsPromise = (async () => {
      const bindings = await import(`${baseUrl}/grafeo_wasm_bg.js`);
      const imports = { "./grafeo_wasm_bg.js": bindings };
      const wasmUrl = `${baseUrl}/grafeo_wasm_bg.wasm`;
      let instance;
      try {
        ({ instance } = await WebAssembly.instantiateStreaming(fetch(wasmUrl), imports));
      } catch (_) {
        // Fallback for servers or proxies that do not send application/wasm
        const resp = await fetch(wasmUrl);
        if (!resp.ok) throw new Error("Failed to download " + wasmUrl + ": " + resp.status);
        ({ instance } = await WebAssembly.instantiate(await resp.arrayBuffer(), imports));
      }
      bindings.__wbg_set_wasm(instance.exports);
      return bindings;
    })().catch((err) => {
      wasmBindingsPromise = null; // allow a retry after a network error
      throw err;
    });
  }
  return wasmBindingsPromise;
}

/**
 * Initialize Grafeo WASM database.
 */
export async function connect() {
  if (!wasmDb) {
    const bindings = await loadWasmBindings();
    wasmDb = new bindings.Database();
  }
  return true;
}

/**
 * Close the WASM database.
 */
export async function disconnect() {
  if (wasmDb) {
    try {
      wasmDb.free();
    } catch (_) {
      // ignore
    }
    wasmDb = null;
  }
}

/**
 * Check if connected.
 */
export function isConnected() {
  return wasmDb !== null;
}

/**
 * Execute a query against the WASM database.
 * The engine rejects several `;`-separated statements in one call.
 */
export async function executeQuery(query, config) {
  if (!wasmDb) throw new Error("WASM database not initialized");

  const language = config?.language;
  if (language && language !== "gql") {
    return wasmDb.executeWithLanguage(query, language);
  }
  return wasmDb.execute(query);
}

/**
 * Convert WASM execute() result to points array.
 * execute() returns Array<Record<string, unknown>>.
 */
export function toPoints(result) {
  if (!Array.isArray(result)) return [];
  return result.map((row, i) => grafeoRowToPoint(Object.entries(row ?? {}), i));
}
