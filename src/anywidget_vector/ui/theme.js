// === Theme: follow the host page, unless the user chose ===
// The contract is shared with anywidget-graph and anywidget-archimate: dark_mode reports the current theme.
// It follows the page until someone chooses (dark_mode passed from Python, set from Python after display, or
// the settings toggle), which sets _theme_explicit. A background chosen the same way sets _background_explicit
// and is never replaced by the theme's canvas color.

export const THEME_BACKGROUNDS = { dark: "#181c1a", light: "#ffffff" };

// How many theme writes by a widget are running right now. Writes are synchronous, so a change event fired while
// this is above 0 is the widget's own, not a user's choice. It lives on globalThis, not on the model: anywidget
// hands each view its own model proxy, and a page can hold several copies of this module (a cell run again), while
// every view of one widget shares the underlying model and sees the others' writes.
const THEME_WRITES = Symbol.for("anywidget.theme-writes");

function writingTheme() {
  return (globalThis[THEME_WRITES] ?? 0) > 0;
}

/**
 * Decide dark or light from the page's signals, strongest first: data-theme "dark" or "light" on the widget's
 * closest ancestor, then on html and body (other data-theme values, such as design-system names, are ignored),
 * then a dark or light class on html or body, then the operating system.
 */
export function resolveDark({ ancestorTheme, htmlTheme, bodyTheme, classes = [], prefersDark = false }) {
  for (const theme of [ancestorTheme, htmlTheme, bodyTheme]) {
    if (theme === "dark") return true;
    if (theme === "light") return false;
  }
  if (classes.some((c) => c === "dark" || c === "dark-theme")) return true;
  if (classes.some((c) => c === "light" || c === "light-theme")) return false;
  return Boolean(prefersDark);
}

export function detectHostDark(el) {
  const html = document.documentElement;
  const body = document.body;
  const ancestor = el?.closest?.('[data-theme="dark"], [data-theme="light"]');
  return resolveDark({
    ancestorTheme: ancestor?.getAttribute("data-theme"),
    htmlTheme: html?.getAttribute("data-theme"),
    bodyTheme: body?.getAttribute("data-theme"),
    classes: [...(html?.classList ?? []), ...(body?.classList ?? [])],
    prefersDark: Boolean(globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches),
  });
}

/**
 * Keep dark_mode and background in step with the page and call apply(dark) on every theme change.
 * Returns a function that stops following (observers, media listener and model listeners).
 */
export function followHostTheme(model, el, apply) {
  function write(dark) {
    globalThis[THEME_WRITES] = (globalThis[THEME_WRITES] ?? 0) + 1;
    try {
      if (!model.get("_theme_explicit") && model.get("dark_mode") !== dark) model.set("dark_mode", dark);
      const background = dark ? THEME_BACKGROUNDS.dark : THEME_BACKGROUNDS.light;
      if (!model.get("_background_explicit") && model.get("background") !== background) {
        model.set("background", background);
      }
      model.save_changes();
    } finally {
      globalThis[THEME_WRITES] -= 1;
    }
    apply(dark);
  }

  function sync() {
    write(model.get("_theme_explicit") ? model.get("dark_mode") : detectHostDark(el));
  }

  function onDarkModeChange() {
    if (writingTheme()) return;
    // Python after display, or the settings toggle: a choice, also for later views
    model.set("_theme_explicit", true);
    write(model.get("dark_mode"));
  }

  function onBackgroundChange() {
    if (writingTheme() || model.get("_background_explicit")) return;
    model.set("_background_explicit", true);
    model.save_changes();
  }

  model.on("change:dark_mode", onDarkModeChange);
  model.on("change:background", onBackgroundChange);
  sync();

  // data-theme on any ancestor, classes and inline styles on html and body, and the operating system
  const themeObserver = new MutationObserver(sync);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"], subtree: true });
  const classObserver = new MutationObserver(sync);
  for (const node of [document.documentElement, document.body]) {
    if (node) classObserver.observe(node, { attributes: true, attributeFilter: ["class", "style"] });
  }
  const media = globalThis.matchMedia?.("(prefers-color-scheme: dark)");
  media?.addEventListener?.("change", sync);

  return () => {
    themeObserver.disconnect();
    classObserver.disconnect();
    media?.removeEventListener?.("change", sync);
    model.off("change:dark_mode", onDarkModeChange);
    model.off("change:background", onBackgroundChange);
  };
}

/**
 * The model as the widget's components see it: listeners they add are recorded, and offAll() removes them,
 * so a removed view stops reacting to the model.
 */
export function trackModelListeners(model) {
  const listeners = [];
  return {
    get: (name) => model.get(name),
    set: (name, value) => model.set(name, value),
    save_changes: () => model.save_changes(),
    on(name, callback) {
      model.on(name, callback);
      listeners.push([name, callback]);
    },
    off: (name, callback) => model.off(name, callback),
    offAll() {
      for (const [name, callback] of listeners.splice(0)) model.off(name, callback);
    },
  };
}
