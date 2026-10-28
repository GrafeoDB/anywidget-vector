// Smoke test of the browser-side Grafeo backend (backends/grafeo/embed.js)
// against a real, unpacked @grafeo-db/wasm package.
//
//   npm pack @grafeo-db/wasm@0.6.0 && tar -xzf grafeo-db-wasm-0.6.0.tgz
//   node tests/js/wasm_smoke.mjs package
//
// It runs the same loader the widget uses in the browser (glue import plus
// manual instantiation of the bundler-target binary), then the vector search
// flow from the README, and checks the points the widget would display.
// Run it before bumping GRAFEO_WASM_VERSION. Needs Node 22 or later.

import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const pkgDir = path.resolve(process.argv[2] ?? "");
const pkg = JSON.parse(await readFile(path.join(pkgDir, "package.json"), "utf8"));

// Node's fetch() cannot read file: URLs, which is where the loader gets the binary from here
const networkFetch = globalThis.fetch;
globalThis.fetch = async (url, init) => {
  const href = String(url);
  if (!href.startsWith("file:")) return networkFetch(url, init);
  return new Response(await readFile(new URL(href)), { headers: { "content-type": "application/wasm" } });
};

const embed = await import(new URL("../../src/anywidget_vector/backends/grafeo/embed.js", import.meta.url));
console.log(`@grafeo-db/wasm ${pkg.version} (widget pins ${embed.GRAFEO_WASM_VERSION})`);

let failures = 0;
function check(condition, message) {
  console.log(`${condition ? "ok  " : "FAIL"} ${message}`);
  if (!condition) failures += 1;
}

// Primes the bindings cache that connect() uses, from the local package
await embed.loadWasmBindings(pathToFileURL(pkgDir).href);
await embed.connect();
check(embed.isConnected(), "connect() creates a database");

const run = (query, config = {}) => embed.executeQuery(query, config);
const docs = [
  ["alpha", [1.0, 0.0, 0.0]],
  ["beta", [0.9, 0.2, 0.1]],
  ["gamma", [0.1, 1.0, 0.2]],
  ["delta", [0.0, 0.8, 0.9]],
];
for (const [name, vec] of docs) {
  await run(`INSERT (:Doc {name: '${name}', embedding: vector([${vec.map((v) => v.toFixed(1)).join(", ")}])})`);
}
await run("CREATE VECTOR INDEX doc_embedding ON :Doc(embedding) DIMENSION 3 METRIC 'cosine'");

const search =
  "CALL grafeo.search.vector('Doc', 'embedding', [1.0, 0.1, 0.0], 3) YIELD node_id, distance " +
  "NEXT MATCH (n:Doc) WHERE id(n) = node_id RETURN n, distance ORDER BY distance";
const points = embed.toPoints(await run(search));
check(points.length === 3, `vector search returns k=3 points (got ${points.length})`);
check(points[0]?.name === "alpha" && points[1]?.name === "beta", "nearest neighbors come first");
check(
  points.every((p, i) => i === 0 || p.distance >= points[i - 1].distance),
  "points are ordered by distance",
);
check(
  points.every((p) => Array.isArray(p.vector) && p.vector.length === 3),
  "vectors arrive as plain arrays",
);
check(points[0]?.x === 1 && points[0]?.y === 0 && points[0]?.z === 0, "coordinates come from the embedding");
check(JSON.stringify(points[0]?.labels) === '["Doc"]', "node labels are kept");
check(/^\d+$/.test(points[0]?.id ?? ""), "point id is the engine node id");

const unaliased = embed.toPoints(await run("MATCH (n:Doc) WHERE n.name = 'gamma' RETURN n.name, n.embedding"));
check(unaliased[0]?.name === "gamma" && unaliased[0]?.y === 1, "unaliased columns map to name and vector");

const cypher = embed.toPoints(await run("MATCH (n:Doc) RETURN n.name AS name", { language: "cypher" }));
check(cypher.length === docs.length, "Cypher goes through executeWithLanguage");

// grafeo 0.6.0: a GQL number with a point is an exact decimal, {$decimal: "..."} in WASM
const numbers = embed.toPoints(
  await run("MATCH (n:Doc) WHERE n.name = 'alpha' RETURN n.name AS name, 0.25 AS score, 1.5 AS x, [0.5, 2.0] AS pair"),
);
check(
  numbers[0]?.score === 0.25 && numbers[0]?.x === 1.5 && JSON.stringify(numbers[0]?.pair) === "[0.5,2]",
  "number literals with a point arrive as numbers",
);

let rejected = false;
try {
  await run("MATCH (n) RETURN n; MATCH (m) RETURN m");
} catch (_) {
  rejected = true;
}
check(rejected, "several statements in one call raise an error");

// 0.5.44 trapped (`unreachable`) on a query vector of the wrong size, which broke the module
let sizeError = "";
try {
  await run(search.replace("[1.0, 0.1, 0.0]", "[1.0, 0.1]"));
} catch (err) {
  sizeError = String(err?.message ?? err);
}
check(/expects 3/.test(sizeError), `a query vector of the wrong size is an error (${sizeError})`);
check(embed.toPoints(await run(search)).length === 3, "the database keeps answering after that error");

await embed.disconnect();
check(!embed.isConnected(), "disconnect() frees the database");

if (failures > 0) {
  console.error(`${failures} check(s) failed`);
  process.exit(1);
}
console.log("all checks passed");
