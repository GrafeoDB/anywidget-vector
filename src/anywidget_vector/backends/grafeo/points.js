/**
 * Conversion of Grafeo query rows into widget points.
 *
 * Shared by the Grafeo server (HTTP) and WASM backends. The embedded (Python)
 * backend applies the same rules in backends/grafeo/converter.py.
 *
 * Engine value encoding (grafeo 0.5.44):
 *   node:   {_id, _labels, ...properties}
 *   vector: Array (server, Python) or Float32Array (WASM)
 *   unaliased columns are named after their expression: `n.embedding`, `id(n)`
 *
 * Coordinates come from explicit x/y/z fields when present, otherwise from the
 * first three components of the vector. Non-finite coordinates become 0, so
 * one bad value cannot break camera framing for the whole scene.
 */

const GRAFEO_VECTOR_KEYS = new Set(["vector", "embedding", "embeddings"]);
const GRAFEO_AXES = ["x", "y", "z"];

export function isGrafeoNode(val) {
  return val !== null && typeof val === "object" && "_id" in val && Array.isArray(val._labels);
}

/** Map a result column to a point key: `n.embedding` -> `embedding`, `id(n)` -> `id`. */
export function grafeoColumnKey(column) {
  const property = /^[A-Za-z_]\w*\.([A-Za-z_]\w*)$/.exec(column);
  if (property) return property[1];
  if (/^id\(\s*[A-Za-z_]\w*\s*\)$/i.test(column)) return "id";
  return column;
}

/** Make a value safe to sync to Python as JSON (typed arrays and BigInt are not). */
function grafeoPlainValue(val) {
  if (ArrayBuffer.isView(val) && !(val instanceof DataView)) return Array.from(val);
  if (typeof val === "bigint") {
    const num = Number(val);
    return Number.isSafeInteger(num) ? num : String(val);
  }
  return val;
}

function grafeoFiniteNumber(val) {
  const num = typeof val === "number" ? val : parseFloat(val);
  return Number.isFinite(num) ? num : 0;
}

/** Flatten a row into [key, value] fields, expanding node values into their properties. */
function grafeoRowFields(entries) {
  const fields = [];
  const columnKeys = new Set();
  for (const [column, raw] of entries) {
    const val = grafeoPlainValue(raw);
    if (isGrafeoNode(val)) {
      for (const [key, prop] of Object.entries(val)) {
        if (!key.startsWith("_")) fields.push([key, grafeoPlainValue(prop)]);
      }
      // The engine identity wins over a user property named `id`
      fields.push(["id", val._id], ["labels", [...val._labels]]);
      continue;
    }
    // `RETURN a.name, b.name`: keep the second one under its full column name
    const key = grafeoColumnKey(String(column));
    fields.push([columnKeys.has(key) ? String(column) : key, val]);
    columnKeys.add(key);
  }
  return fields;
}

/**
 * Convert one result row, given as [column, value] pairs, into a point.
 */
export function grafeoRowToPoint(entries, index) {
  const point = { id: `point_${index}` };
  let vector = null;

  for (const [key, val] of grafeoRowFields(entries)) {
    if (val === null || val === undefined) continue;
    if (key === "id" || key === "ID") {
      point.id = String(val);
    } else if (GRAFEO_VECTOR_KEYS.has(key) && Array.isArray(val)) {
      if (vector === null) vector = val;
    } else if (GRAFEO_AXES.includes(key)) {
      point[key] = grafeoFiniteNumber(val);
    } else {
      point[key] = val;
    }
  }

  if (vector !== null) point.vector = vector;
  GRAFEO_AXES.forEach((axis, i) => {
    if (point[axis] === undefined) point[axis] = vector ? grafeoFiniteNumber(vector[i] ?? 0) : 0;
  });
  return point;
}
