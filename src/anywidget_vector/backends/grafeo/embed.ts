/**
 * Grafeo WASM browser-side client for vector queries.
 * Lazy-loads @grafeo-db/wasm from the jsDelivr CDN on first use.
 */
import { grafeoRowToPoint } from "./points.ts";
import type { BackendConfig, PointData } from "../../ui/types.ts";

// The only place the browser engine version is set. Keep it exact and in
// lockstep with the `grafeo` Python extra in pyproject.toml.
export const GRAFEO_WASM_VERSION = "0.6.2";
export const GRAFEO_WASM_CDN = `https://cdn.jsdelivr.net/npm/@grafeo-db/wasm@${GRAFEO_WASM_VERSION}`;

interface WasmDatabase {
  free(): void;
  execute(query: string): unknown;
  executeWithLanguage(query: string, language: string): unknown;
}

let wasmDb: WasmDatabase | null = null;
let connecting: Promise<void> | null = null;

/**
 * Where the page keeps the loading promise for one glue module. A page can hold several copies of the widget
 * module (a cell run again, a marimo reconnect, anywidget-graph next to this widget), and they all get the same
 * cached glue module from the browser. A second instantiation would hand that glue new memory and break every
 * database the first one created, so the promise lives on globalThis, keyed by the glue URL alone.
 */
export function wasmBindingsKey(baseUrl: string): symbol {
  return Symbol.for(`grafeo-wasm:${baseUrl}/grafeo_wasm_bg.js`);
}

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
export function loadWasmBindings(baseUrl: string = GRAFEO_WASM_CDN): Promise<any> {
  const key = wasmBindingsKey(baseUrl);
  const wasmGlobals = globalThis as unknown as Record<symbol, Promise<any> | undefined>;
  if (!wasmGlobals[key]) {
    wasmGlobals[key] = (async () => {
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
      delete wasmGlobals[key]; // allow a retry after a network error
      throw err;
    });
  }
  return wasmGlobals[key] as Promise<any>;
}

/**
 * Initialize Grafeo WASM database.
 */
export async function connect() {
  if (wasmDb) return true;
  // Queries started while the bindings load share one Database instead of each creating one
  connecting ??= (async () => {
    try {
      const bindings = await loadWasmBindings();
      wasmDb ??= new bindings.Database();
    } finally {
      connecting = null;
    }
  })();
  await connecting;
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
export async function executeQuery(query: string, config?: BackendConfig): Promise<unknown> {
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
export function toPoints(result: unknown): PointData[] {
  if (!Array.isArray(result)) return [];
  return result.map((row, i) => grafeoRowToPoint(Object.entries(row ?? {}), i));
}
