// What the canvas says when it has nothing to draw: an empty widget says how to fill it. While the query banner
// shows an error, it is quiet: the banner speaks.
import type { WidgetModel } from "./types.ts";

export const EMPTY_NOTE = "Nothing to show yet. Pass points from Python, or run a query.";

/** The canvas's note for the model's state, or "" for none. */
export function canvasNote(model: WidgetModel): string {
  if (model.get("query_error")) return "";
  return (model.get("points") ?? []).length > 0 ? "" : EMPTY_NOTE;
}

/** Show the note centred over `container`, following the model. */
export function mountCanvasNote(container: HTMLElement, model: WidgetModel): void {
  const note = document.createElement("div");
  note.className = "avs-canvas-note";
  note.setAttribute("role", "status");
  const update = () => {
    const text = canvasNote(model);
    note.textContent = text;
    note.style.display = text ? "" : "none";
  };
  model.on("change:points", update);
  model.on("change:query_error", update);
  update();
  container.appendChild(note);
}
