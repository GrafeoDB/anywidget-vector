/**
 * The side panels (explorer, settings, properties) open and close by their avs-open class. A closed panel is only
 * collapsed, so it is also made inert: Tab and screen readers skip its controls (as in anywidget-graph).
 */
import type { Panel } from "./types.ts";

/** Open or close a side panel. */
export function setPanelOpen(panel: HTMLElement, open: boolean): void {
  panel.classList.toggle("avs-open", open);
  panel.inert = !open;
}

/** The Panel controls of a side panel element; it starts closed. */
export function panelControls(panel: HTMLDivElement): Panel {
  setPanelOpen(panel, false);
  const isOpen = () => panel.classList.contains("avs-open");
  return {
    element: panel,
    open: () => setPanelOpen(panel, true),
    close: () => setPanelOpen(panel, false),
    toggle: () => setPanelOpen(panel, !isOpen()),
    isOpen,
  };
}

let fieldIds = 0;

/**
 * Tie each form group's label to its control (built label first, control after), so screen readers name the
 * control and a click on the label focuses it. A toggle inside its own text label (Dark mode) keeps that name.
 */
export function nameFields(root: HTMLElement): void {
  for (const group of root.querySelectorAll<HTMLElement>(".avs-form-group")) {
    const label = group.querySelector<HTMLLabelElement>(":scope > .avs-label");
    const field = group.querySelector<HTMLElement>("input, select, textarea");
    if (!label || !field || label.htmlFor || field.closest("label")) continue;
    if (!field.id) field.id = `avs-field-${++fieldIds}`;
    label.htmlFor = field.id;
  }
}

/** A panel's close button, named for screen readers and on hover. */
export function closeButton(icon: string, name: string, onClose: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.className = "avs-btn avs-btn-icon";
  button.innerHTML = icon;
  button.title = name;
  button.setAttribute("aria-label", name);
  button.addEventListener("click", onClose);
  return button;
}
