// The cluster list explains the colours: each row has its swatch, the 8 largest clusters in the data colours and
// the rest in Other (registry.ts), the same colours the points are drawn with. jsdom from `npm ci --prefix tests/js`.
import assert from "node:assert/strict";
import { test } from "node:test";

import { LIGHT } from "../../src/anywidget_vector/ui/palette.ts";

let JSDOM: typeof import("jsdom").JSDOM | null = null;
try {
  ({ JSDOM } = await import("jsdom"));
} catch {
  // not installed
}
const skip: string | false = JSDOM ? false : "jsdom is not installed (npm ci --prefix tests/js)";

function model(values: Record<string, unknown>) {
  return { get: (key: string) => values[key], set: () => {}, save_changes: () => {}, on: () => {}, off: () => {} };
}

test("cluster rows carry their swatch, Other included", { skip }, async () => {
  const { window } = new JSDOM!("<!doctype html><body></body>");
  const g = globalThis as Record<string, unknown>;
  g.document = window.document;
  g.HTMLElement = window.HTMLElement;
  const { createSidebar } = await import("../../src/anywidget_vector/ui/sidebar.ts");

  // 40 clusters, c0 the largest (50 points) down to c39 (11 points)
  const points = Array.from({ length: 40 }, (_, i) => Array.from({ length: 50 - i }, (_, j) => ({ id: `c${i}-${j}`, c: `c${i}` }))).flat();
  const panel = createSidebar(model({ points, color_field: "c", dark_mode: false }) as never, {});
  const rows = [...panel.element.querySelectorAll(".avs-cluster-content .avs-property-row")];
  assert.equal(rows.length, 40);
  const colors = rows.map((row) => (row.querySelector(".avs-swatch") as HTMLElement | null)?.dataset.color);
  assert.deepEqual(colors.slice(0, 8), LIGHT.data);
  assert.ok(colors.slice(8).every((c) => c === LIGHT.other), "beyond the 8 largest: Other");
  assert.match(rows[0].textContent ?? "", /c0/);
  assert.match((rows[10].querySelector(".avs-swatch") as HTMLElement).title, /Other/);
});

test("cluster swatches follow a theme switch", { skip }, async () => {
  const { window } = new JSDOM!("<!doctype html><body></body>");
  const g = globalThis as Record<string, unknown>;
  g.document = window.document;
  g.HTMLElement = window.HTMLElement;
  const { createSidebar } = await import("../../src/anywidget_vector/ui/sidebar.ts");
  const { DARK } = await import("../../src/anywidget_vector/ui/palette.ts");
  const values: Record<string, unknown> = { points: [{ id: "a", c: "x" }, { id: "b", c: "x" }], color_field: "c", dark_mode: false };
  const handlers = new Map<string, (() => void)[]>();
  const live = {
    get: (k: string) => values[k],
    set: (k: string, v: unknown) => { values[k] = v; for (const h of handlers.get(`change:${k}`) ?? []) h(); },
    save_changes: () => {},
    on: (e: string, h: () => void) => handlers.set(e, [...(handlers.get(e) ?? []), h]),
    off: () => {},
  };
  const panel = createSidebar(live as never, {});
  const swatch = () => (panel.element.querySelector(".avs-cluster-content .avs-swatch") as HTMLElement).dataset.color;
  assert.equal(swatch(), LIGHT.data[0]);
  live.set("dark_mode", true);
  assert.equal(swatch(), DARK.data[0]);
});
