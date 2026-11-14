// The shared anywidgets look: styles.css and palette.ts carry the design tokens
// (tests/js/fixtures/anywidgets-tokens.json is a copy of the generated tokens; `npm run sync-tokens -- <tokens.json>`
// rewrites both from a newer one). Run with: node --test tests/js/*.test.ts

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";

import { DARK, LIGHT } from "../../src/anywidget_vector/ui/palette.ts";
import { THEME_BACKGROUNDS } from "../../src/anywidget_vector/ui/theme.ts";

const UI = new URL("../../src/anywidget_vector/ui/", import.meta.url);
const tokens = JSON.parse(readFileSync(new URL("./fixtures/anywidgets-tokens.json", import.meta.url), "utf8"));
const css = readFileSync(new URL("styles.css", UI), "utf8");

function block(selector: string): string {
  const synced = css.match(/\/\* design-tokens:start[\s\S]*?\/\* design-tokens:end \*\//)?.[0] ?? "";
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return synced.match(new RegExp(`(^|\\n)${escaped} \\{([^}]*)\\}`))?.[2] ?? "";
}
const value = (body: string, name: string) => body.match(new RegExp(`--${name}: ([^;]+);`))?.[1];

test("the synced block holds the token values", () => {
  for (const [selector, mode] of [[".avs-wrapper", "light"], [".avs-wrapper.avs-dark", "dark"]] as const) {
    const body = block(selector);
    assert.ok(body, `${selector} in the synced block`);
    assert.equal(value(body, "avs-bg"), tokens[mode].background);
    assert.equal(value(body, "avs-text"), tokens[mode].foreground);
    assert.equal(value(body, "avs-border"), tokens[mode].border);
    assert.equal(value(body, "avs-primary"), tokens[mode].primary);
    assert.equal(value(body, "avs-error"), tokens[mode]["status-error"]);
    assert.equal(value(body, "avs-font-mono"), tokens[mode]["font-mono"]);
    assert.equal(value(body, "avs-radius-box"), tokens[mode]["radius-box"]);
  }
});

test("the synced block keeps the variable names and selectors", () => {
  const names = ["bg", "surface", "border", "text", "text-muted", "primary", "primary-hover", "success", "warning", "error", "radius"];
  for (const selector of [".avs-wrapper", ".avs-wrapper.avs-dark"]) {
    for (const name of names) assert.ok(value(block(selector), `avs-${name}`), `${selector} --avs-${name}`);
  }
});

test("palette.ts matches the tokens", () => {
  for (const [palette, mode] of [[LIGHT, "light"], [DARK, "dark"]] as const) {
    assert.deepEqual(palette.data, [1, 2, 3, 4, 5, 6, 7, 8].map((n) => tokens[mode][`data-${n}`]));
    assert.equal(palette.other, tokens[mode].input);
    assert.equal(palette.background, tokens[mode].background);
  }
});

test("the theme backgrounds are the palette backgrounds", () => {
  assert.deepEqual(THEME_BACKGROUNDS, { dark: DARK.background, light: LIGHT.background });
});

test("no hard-coded indigo, blue or slate is left", () => {
  const sources = [css, ...readdirSync(UI).filter((f) => f.endsWith(".ts")).map((f) => readFileSync(new URL(f, UI), "utf8"))];
  for (const banned of ["#6366f1", "0x6366f1", "#0880ea", "#e2e8f0", "#0f172a", "99, 102, 241"]) {
    for (const source of sources) assert.ok(!source.includes(banned), `${banned} still used`);
  }
});

test("a toggle that is on shows it: a ring of 3:1 or more against its surface, and aria-pressed", () => {
  const lum = (hex: string) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const contrast = (a: string, b: string) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  for (const mode of ["light", "dark"] as const) {
    assert.ok(contrast(tokens[mode]["muted-foreground"], tokens[mode].selected) >= 3, mode);
  }
  for (const rule of [".avs-mode-btn.avs-mode-active", ".avs-collection-item.avs-active"]) {
    const body = css.split(rule + " {")[1]?.split("}")[0] ?? css.split(rule + ",")[1]?.split("}")[0] ?? "";
    assert.match(body, /var\(--avs-text-muted\)/, `${rule} draws its ring in --avs-text-muted`);
  }
  for (const file of ["canvas.ts", "sidebar.ts"]) {
    assert.ok(readFileSync(new URL(file, UI), "utf8").includes('"aria-pressed"'), `${file} sets aria-pressed`);
  }
});
