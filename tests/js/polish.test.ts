// The vector polish pass: the widget's size, the camera's framing, what an empty canvas says, Other receding and
// when Properties opens. Run with: node --test tests/js/*.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { LIGHT, DARK } from "../../src/anywidget_vector/ui/palette.ts";
import { mixOver } from "../../src/anywidget_vector/ui/registry.ts";
import { wrapperSize, MIN_HEIGHT } from "../../src/anywidget_vector/ui/size.ts";
import { fitDistance } from "../../src/anywidget_vector/ui/frame.ts";
import { canvasNote, EMPTY_NOTE } from "../../src/anywidget_vector/ui/states.ts";
import { otherInk, OTHER_RECEDE } from "../../src/anywidget_vector/ui/colors.ts";
import { propertiesForSelection } from "../../src/anywidget_vector/ui/properties.ts";

const model = (values: Record<string, unknown>) => ({ get: (k: string) => values[k], set() {}, save_changes() {}, on() {}, off() {} });

test("no size given: fill the width, 16:10, at least what the chrome needs, at most 80% of the screen", () => {
  assert.deepEqual(wrapperSize(0, 0), { width: "100%", aspectRatio: "16 / 10", minHeight: `${MIN_HEIGHT}px`, maxHeight: "80vh" });
  assert.equal(MIN_HEIGHT, 360);
});

test("an explicit width or height wins", () => {
  assert.deepEqual(wrapperSize(700, 0), { width: "700px", aspectRatio: "16 / 10", minHeight: `${MIN_HEIGHT}px`, maxHeight: "80vh" });
  assert.deepEqual(wrapperSize(0, 500), { width: "100%", height: "500px" });
  assert.deepEqual(wrapperSize(700, 500), { width: "700px", height: "500px" });
});

test("the camera frames the cloud's real radius, every point in view, without slack", () => {
  const points = [];
  for (let i = 0; i < 200; i++) {
    const z = 1 - (2 * (i + 0.5)) / 200, r = Math.sqrt(1 - z * z), a = i * 2.39996;
    points.push({ x: r * Math.cos(a), y: r * Math.sin(a), z });
  }
  const half = (60 * Math.PI) / 360;
  const d = fitDistance(points, { x: 0, y: 0, z: 0 }, 60, 1.6);
  assert.ok(d >= 1 / Math.sin(half) && d <= 1.15 / Math.sin(half), String(d));
});

test("an empty widget says how to fill it; points or an error banner silence it", () => {
  assert.equal(canvasNote(model({ points: [] })), EMPTY_NOTE);
  assert.equal(EMPTY_NOTE, "Nothing to show yet. Pass points from Python, or run a query.");
  assert.equal(canvasNote(model({ points: [{ id: 1 }] })), "");
  assert.equal(canvasNote(model({ points: [], query_error: "bad" })), "");
});

test("Other points recede: their ink is Other faded towards the background", () => {
  assert.equal(otherInk(LIGHT), mixOver(LIGHT.other, LIGHT.background, OTHER_RECEDE));
  assert.equal(otherInk(DARK), mixOver(DARK.other, DARK.background, OTHER_RECEDE));
  assert.ok(OTHER_RECEDE < 1 && OTHER_RECEDE >= 0.4);
});

test("Properties opens when points are selected and closes when the selection clears", () => {
  assert.equal(propertiesForSelection(["a"], true), "open");
  assert.equal(propertiesForSelection([], true), "close");
  assert.equal(propertiesForSelection(["a"], false), null);
});

test("a selection is framed like the cloud, never closer than a quarter of the whole view (one point stays a point)", async () => {
  const { selectionDistance } = await import("../../src/anywidget_vector/ui/frame.ts");
  const all = [{ x: -1, y: 0, z: 0 }, { x: 1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 }, { x: 0, y: -1, z: 0 }];
  const whole = fitDistance(all, { x: 0, y: 0, z: 0 }, 60, 1.6);
  const one = selectionDistance([all[0]], all, 60, 1.6);
  assert.ok(one >= whole * 0.25 - 1e-9, `${one} vs ${whole}`);
  const two = selectionDistance([all[0], all[1]], all, 60, 1.6);
  assert.ok(Math.abs(two - fitDistance([all[0], all[1]], { x: 0, y: 0, z: 0 }, 60, 1.6)) < 1e-9);
});

test("a point without a value for the colour field is Other, not the largest cluster's colour", async () => {
  const { categoryColor } = await import("../../src/anywidget_vector/ui/colors.ts");
  const { CategoryRegistry } = await import("../../src/anywidget_vector/ui/registry.ts");
  const registry = new CategoryRegistry();
  registry.assign(new Map([["A", 1000], ["B", 10]]));
  assert.equal(categoryColor("A", registry, LIGHT), LIGHT.data[0]);
  assert.equal(categoryColor(undefined, registry, LIGHT), otherInk(LIGHT));
  assert.equal(categoryColor(null, registry, LIGHT), otherInk(LIGHT));
  assert.equal(categoryColor("never seen", registry, LIGHT), otherInk(LIGHT));
});
