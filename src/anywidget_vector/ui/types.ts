// Shared types for the widget's front end: the anywidget model contract and the synced trait shapes.

/** The anywidget model contract (a host may provide exactly this). */
export interface WidgetModel {
  get(key: string): any;
  set(key: string, value: any): void;
  save_changes(): void;
  on(event: string, callback: (...args: any[]) => void): void;
  off(event: string, callback: (...args: any[]) => void): void;
}

/** One point of the `points` trait. A coordinate can be missing, or null (the Python side sends NaN and infinity
 * as null): read it with `?? 0`. */
export interface PointData {
  id?: string;
  x?: number | null;
  y?: number | null;
  z?: number | null;
  vector?: number[];
  color?: string;
  size?: number;
  [key: string]: unknown;
}

/** The `backend_config` trait: free-form per backend. */
export type BackendConfig = Record<string, any>;

/** One entry of the BACKENDS table in constants.ts. */
export interface BackendInfo {
  name: string;
  side: string;
  modes?: string[];
  queryLanguage?: string;
  placeholder?: string;
  hasAuth?: boolean;
  hasCollection?: boolean;
  hasIndex?: boolean;
  hasClass?: boolean;
  hasTable?: boolean;
}

/** Callbacks the panels and canvas get from render(). */
export interface CanvasCallbacks {
  onHover?: (point: PointData | null) => void;
  onSelect?: (point: PointData | null) => void;
  onSelection?: (points: PointData[]) => void;
}

/** Callbacks render() hands to the toolbar. */
export interface ToolbarCallbacks {
  onRunQuery?: () => void;
  onFilterInput?: (text: string) => void;
  onToggleSidebar?: () => void;
  onToggleSettings?: () => void;
  onToggleProperties?: () => void;
}

/** Callbacks render() hands to the side panels. */
export interface PanelCallbacks {
  onClose?: () => void;
}

/** What the sidebar and settings/properties panels return. */
export interface Panel {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
  toggle: () => void;
  isOpen: () => boolean;
}

/** The properties panel also reports the hovered point. */
export interface PropertiesPanel extends Panel {
  setHoveredPoint: (point: PointData | null) => void;
}
