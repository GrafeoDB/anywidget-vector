/**
 * Grafeo WASM browser-side client for vector queries.
 * Lazy-loads @grafeo-db/wasm from esm.sh on first use.
 */

let wasmDb = null;
let wasmInitialized = false;

/**
 * Initialize Grafeo WASM database.
 */
export async function connect() {
  if (!wasmInitialized) {
    const mod = await import("https://esm.sh/@grafeo-db/wasm@0.5.0");
    await mod.default();
    wasmInitialized = true;
    wasmDb = new mod.Database();
  } else if (!wasmDb) {
    const mod = await import("https://esm.sh/@grafeo-db/wasm@0.5.0");
    wasmDb = new mod.Database();
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

  return result.map((row, i) => {
    const point = { id: `point_${i}` };

    for (const [key, val] of Object.entries(row)) {
      if (key === "id" || key === "ID") {
        point.id = String(val);
      } else if (key === "vector" || key === "embedding" || key === "embeddings") {
        const vec = Array.isArray(val) ? val : [];
        point.x = vec[0] ?? 0;
        point.y = vec[1] ?? 0;
        point.z = vec[2] ?? 0;
        point.vector = vec;
      } else if (key === "x" || key === "y" || key === "z") {
        point[key] = typeof val === "number" ? val : parseFloat(val) || 0;
      } else if (val !== null && val !== undefined) {
        if (typeof val === "object" && val.properties) {
          Object.assign(point, val.properties);
          if (val.id !== undefined) point.id = String(val.id);
        } else {
          point[key] = val;
        }
      }
    }

    point.x = point.x ?? 0;
    point.y = point.y ?? 0;
    point.z = point.z ?? 0;
    return point;
  });
}
