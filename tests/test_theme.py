"""Tests for the theme contract shared with anywidget-graph and anywidget-archimate.

dark_mode reports the current theme and follows the host page until a theme is
chosen (constructor, Python after display, or the settings toggle), which sets
_theme_explicit. A chosen background sets _background_explicit. The JS side
(ui/theme.js) runs in Node against a small fake page and model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import traitlets

from anywidget_vector import VectorSpace
from anywidget_vector.ui import _strip_imports_exports
from tests.support import NODE, run_node_module

THEME_JS = Path(__file__).resolve().parent.parent / "src" / "anywidget_vector" / "ui" / "theme.js"
needs_node = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")

# A page (html and body with attributes and classes), MutationObserver, matchMedia and an anywidget-like model
# whose set() fires change events synchronously, like Backbone
FAKE_PAGE = """
const observers = [];
globalThis.MutationObserver = class {
  constructor(callback) { this.callback = callback; this.active = false; observers.push(this); }
  observe() { this.active = true; }
  disconnect() { this.active = false; }
};
// One attribute change wakes one observer of one view
const pageChanged = () => observers.find((o) => o.active)?.callback();

function node(attrs = {}, classes = [], parent = null) {
  return {
    attrs, classes, parent,
    getAttribute(name) { return this.attrs[name] ?? null; },
    get classList() { return this.classes; },
    closest() {
      for (let n = this; n; n = n.parent) {
        const theme = n.attrs["data-theme"];
        if (theme === "dark" || theme === "light") return n;
      }
      return null;
    },
  };
}
const html = node();
const body = node({}, [], html);
globalThis.document = { documentElement: html, body };

let prefersDark = false;
const mediaListeners = new Set();
globalThis.matchMedia = () => ({
  get matches() { return prefersDark; },
  addEventListener(_, f) { mediaListeners.add(f); },
  removeEventListener(_, f) { mediaListeners.delete(f); },
});
const osChanged = () => [...mediaListeners].forEach((f) => f());

function makeModel(state) {
  const handlers = {};
  return {
    state,
    get(name) { return this.state[name]; },
    set(name, value) {
      const old = this.state[name];
      this.state[name] = value;
      if (old !== value) (handlers["change:" + name] || []).slice().forEach((h) => h());
    },
    save_changes() {},
    on(name, h) { (handlers[name] ||= []).push(h); },
    off(name, h) { handlers[name] = (handlers[name] || []).filter((x) => x !== h); },
    listenerCount() { return Object.values(handlers).reduce((n, list) => n + list.length, 0); },
  };
}
const defaults = (extra = {}) => ({
  dark_mode: true, _theme_explicit: false, background: "#1a1a2e", _background_explicit: false, ...extra,
});
const widgetEl = node({}, [], body);
const results = {};
"""


def _run_theme(test_code: str, tmp_path: Path) -> dict:
    theme = _strip_imports_exports(THEME_JS.read_text(encoding="utf-8"))
    out = run_node_module(FAKE_PAGE + theme + test_code + "\nconsole.log(JSON.stringify(results));", tmp_path)
    return json.loads(out)


@needs_node
class TestThemeInNode:
    def test_a_dark_mode_given_from_python_wins_over_the_page_and_stays(self, tmp_path):
        result = _run_theme(
            """
html.attrs["data-theme"] = "dark";
prefersDark = true;
const model = makeModel(defaults({ dark_mode: false, _theme_explicit: true }));
const applied = [];
followHostTheme(model, widgetEl, (dark) => applied.push(dark));
results.first = { dark: model.get("dark_mode"), background: model.get("background") };
html.classes.push("dark");
pageChanged();
results.after = model.get("dark_mode");
results.applied = applied;
""",
            tmp_path,
        )
        assert result["first"] == {"dark": False, "background": "#ffffff"}
        assert result["after"] is False
        assert result["applied"] == [False, False]

    def test_following_the_page_continues_after_the_widgets_own_updates(self, tmp_path):
        result = _run_theme(
            """
const model = makeModel(defaults());
const applied = [];
followHostTheme(model, widgetEl, (dark) => applied.push(dark));
const seen = [model.get("dark_mode")];
html.classes.push("dark");
pageChanged();
seen.push(model.get("dark_mode"));
html.classes.pop();
pageChanged();
seen.push(model.get("dark_mode"));
prefersDark = true;
osChanged();
seen.push(model.get("dark_mode"));
results.seen = seen;
results.applied = applied;
results.explicit = model.get("_theme_explicit");
results.background = model.get("background");
""",
            tmp_path,
        )
        assert result["seen"] == [False, True, False, True]
        assert result["applied"] == [False, True, False, True]
        assert result["explicit"] is False
        assert result["background"] == "#181c1a"

    def test_a_dark_mode_set_after_render_stops_following_also_for_later_views(self, tmp_path):
        result = _run_theme(
            """
const model = makeModel(defaults());
followHostTheme(model, widgetEl, () => {});
model.set("dark_mode", true); // Python after display, or the settings toggle
results.explicit = model.get("_theme_explicit");
results.background = model.get("background");
html.attrs["data-theme"] = "light";
pageChanged();
results.afterPageChange = model.get("dark_mode");
const later = [];
followHostTheme(model, widgetEl, (dark) => later.push(dark));
results.laterView = later;
""",
            tmp_path,
        )
        assert result["explicit"] is True
        assert result["background"] == "#181c1a"
        assert result["afterPageChange"] is True
        assert result["laterView"] == [True]

    def test_a_second_view_does_not_take_the_first_views_updates_for_a_choice(self, tmp_path):
        # As in anywidget: each view gets its own proxy of the shared model, and the second view comes from a
        # second copy of the module (a cell run again)
        theme = _strip_imports_exports(THEME_JS.read_text(encoding="utf-8"))
        result = _run_theme(
            f"""
const secondCopy = (() => {{
{theme}
return {{ followHostTheme }};
}})();
const proxy = (m) => ({{
  get: m.get.bind(m), set: m.set.bind(m), save_changes: m.save_changes.bind(m), on: m.on.bind(m), off: m.off.bind(m),
}});
const model = makeModel(defaults());
followHostTheme(proxy(model), widgetEl, () => {{}});
secondCopy.followHostTheme(proxy(model), widgetEl, () => {{}});
html.classes.push("dark");
pageChanged();
results.dark = model.get("dark_mode");
results.explicit = model.get("_theme_explicit");
""",
            tmp_path,
        )
        assert result == {"dark": True, "explicit": False}

    def test_a_chosen_background_is_never_replaced(self, tmp_path):
        result = _run_theme(
            """
const given = makeModel(defaults({ background: "#000000", _background_explicit: true }));
followHostTheme(given, widgetEl, () => {});
const later = makeModel(defaults());
followHostTheme(later, widgetEl, () => {});
later.set("background", "#123456"); // Python after display
prefersDark = true;
osChanged(); // reaches both views
results.given = given.get("background");
results.later = [later.get("background"), later.get("_background_explicit")];
results.darkModes = [given.get("dark_mode"), later.get("dark_mode")];
""",
            tmp_path,
        )
        assert result["given"] == "#000000"
        assert result["later"] == ["#123456", True]
        assert result["darkModes"] == [True, True]

    def test_stopping_removes_observers_media_listener_and_model_listeners(self, tmp_path):
        result = _run_theme(
            """
const model = makeModel(defaults());
const stop = followHostTheme(model, widgetEl, () => {});
results.before = [observers.filter((o) => o.active).length, mediaListeners.size, model.listenerCount()];
stop();
results.after = [observers.filter((o) => o.active).length, mediaListeners.size, model.listenerCount()];
""",
            tmp_path,
        )
        assert result["before"] == [2, 1, 2]
        assert result["after"] == [0, 0, 0]

    def test_tracked_listeners_are_all_removed(self, tmp_path):
        result = _run_theme(
            """
const model = makeModel(defaults());
const view = trackModelListeners(model);
view.on("change:points", () => {});
view.on("change:background", () => {});
view.set("points", []);
results.before = model.listenerCount();
view.offAll();
results.after = model.listenerCount();
results.points = model.get("points");
""",
            tmp_path,
        )
        assert result == {"before": 2, "after": 0, "points": []}

    @pytest.mark.parametrize(
        ("setup", "expected"),
        [
            ("prefersDark = true;", True),
            ('html.attrs["data-theme"] = "light"; prefersDark = true;', False),
            ('body.attrs["data-theme"] = "dark"; html.classes.push("light");', True),
            ('widgetEl.parent = node({ "data-theme": "light" }, [], body); html.attrs["data-theme"] = "dark";', False),
            ('widgetEl.parent = node({ "data-theme": "cupcake" }, [], body); html.attrs["data-theme"] = "dark";', True),
            ('body.classes.push("light"); prefersDark = true;', False),
            ('html.classes.push("dark-theme"); body.classes.push("light");', True),
            ('html.attrs["data-theme"] = "cupcake"; prefersDark = true;', True),
        ],
        ids=[
            "os-dark",
            "data-theme-light-beats-os",
            "body-data-theme-beats-light-class",
            "closest-ancestor-wins",
            "other-data-theme-values-ignored",
            "light-class-beats-os",
            "dark-class-beats-light-class",
            "design-system-data-theme-on-html-ignored",
        ],
    )
    def test_host_theme_detection(self, tmp_path, setup, expected):
        result = _run_theme(setup + "\nresults.dark = detectHostDark(widgetEl);", tmp_path)
        assert result["dark"] is expected


class TestThemeTraits:
    def test_by_default_the_widget_follows_the_page(self):
        widget = VectorSpace()
        assert widget._theme_explicit is False
        assert widget._background_explicit is False

    @pytest.mark.parametrize("dark", [True, False])
    def test_a_dark_mode_given_to_the_widget_is_explicit(self, dark):
        widget = VectorSpace(dark_mode=dark)
        assert widget.dark_mode is dark
        assert widget._theme_explicit is True

    def test_none_means_follow_the_page(self):
        widget = VectorSpace(dark_mode=None, background=None)
        assert widget.dark_mode is True
        assert widget.background == "#1a1a2e"
        assert (widget._theme_explicit, widget._background_explicit) == (False, False)

    def test_a_background_given_to_the_widget_is_explicit(self):
        widget = VectorSpace(background="#000000")
        assert widget.background == "#000000"
        assert widget._background_explicit is True

    def test_setting_the_theme_before_display_is_a_choice(self):
        widget = VectorSpace()
        widget.dark_mode = False
        widget.background = "#202020"
        assert (widget._theme_explicit, widget._background_explicit) == (True, True)

    def test_setting_the_value_the_theme_already_has_is_a_choice(self):
        # On a dark page dark_mode already reads True; setting it keeps the widget dark when the page turns light
        widget = VectorSpace()
        widget.dark_mode = widget.dark_mode
        assert widget._theme_explicit is True
        assert widget._background_explicit is False

    def test_the_browser_following_the_page_is_not_a_choice(self):
        widget = VectorSpace()
        widget.set_state({"dark_mode": False, "background": "#ffffff"})
        assert (widget.dark_mode, widget.background) == (False, "#ffffff")
        assert (widget._theme_explicit, widget._background_explicit) == (False, False)
        # A Python assignment after browser updates still counts
        widget.dark_mode = True
        assert widget._theme_explicit is True

    def test_a_choice_made_in_the_browser_arrives_with_its_flag(self):
        widget = VectorSpace()
        widget.set_state({"dark_mode": True, "_theme_explicit": True})
        assert widget._theme_explicit is True

    def test_a_failed_browser_update_does_not_leave_python_assignments_ignored(self):
        widget = VectorSpace()
        with pytest.raises(traitlets.TraitError):
            widget.set_state({"dark_mode": "not a bool"})
        widget.dark_mode = False
        assert widget._theme_explicit is True

    def test_class_constructors_pass_the_theme_through(self):
        widget = VectorSpace.from_dict({"points": []}, dark_mode=False, background="#101010")
        assert (widget._theme_explicit, widget._background_explicit) == (True, True)
