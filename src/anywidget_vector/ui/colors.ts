// The categorical colours of one widget: a registry per colour field (registry.ts), shared by the canvas and the
// sidebar's cluster list, so a cluster's swatch is its points' data colour (Other's swatch is the full Other grey,
// its points recede), and a cluster keeps its colour while the view shows data that has it.
import { DARK, LIGHT } from "./palette.ts";
import { CategoryRegistry, countBy, mixOver } from "./registry.ts";
import type { Palette } from "./registry.ts";
import type { PointData, WidgetModel } from "./types.ts";

const REGISTRIES = new WeakMap<object, Map<string, CategoryRegistry>>();

/** The registry of one colour field in one widget view (keyed by the view's model), created on first use. */
export function categoryRegistry(model: object, field: string): CategoryRegistry {
  let byField = REGISTRIES.get(model);
  if (!byField) REGISTRIES.set(model, (byField = new Map()));
  let registry = byField.get(field);
  if (!registry) byField.set(field, (registry = new CategoryRegistry()));
  return registry;
}

/**
 * The field's registry with the points' categories assigned. Categories that carry over keep their colour; points
 * that share no coloured category with the registry are a new dataset (another query), so the field starts fresh
 * and its largest categories get the 8 colours instead of all falling to Other.
 */
export function assignedRegistry(model: object, field: string, points: PointData[]): CategoryRegistry {
  const counts = categoricalCounts(points, field);
  let registry = categoryRegistry(model, field);
  if (counts.size > 0 && ![...counts.keys()].some((category) => registry.slot(category) !== null)) {
    registry = new CategoryRegistry();
    REGISTRIES.get(model)!.set(field, registry);
  }
  registry.assign(counts);
  return registry;
}

/** The current theme's palette. */
export function paletteFor(model: WidgetModel): Palette {
  return model.get("dark_mode") ? DARK : LIGHT;
}

/** How many points have each categorical (non-number) value of a field; missing values are left out. */
export function categoricalCounts(points: PointData[], field: string): Map<string, number> {
  return countBy(points, (p) => {
    const v = p[field];
    return v === undefined || v === null || typeof v === "number" ? undefined : String(v);
  });
}

/** How much of Other's grey its points keep over the background: they recede, so the eight data colours lead */
export const OTHER_RECEDE = 0.7;

/** The colour Other points are drawn with in a theme (the cluster list's swatch keeps the full Other grey). */
export function otherInk(palette: Palette): string {
  return mixOver(palette.other, palette.background, OTHER_RECEDE);
}

/**
 * A categorical value's colour: its slot's data colour, else Other (receding). A point without a value (undefined,
 * null) is Other too, so it never borrows the largest category's colour.
 */
export function categoryColor(value: unknown, registry: CategoryRegistry | null | undefined, palette: Palette): string {
  const slot = value === undefined || value === null || !registry ? null : registry.slot(String(value));
  return slot === null ? otherInk(palette) : palette.data[slot];
}
