// The vendored Three.js bundle (ui/vendor/three.min.js, built by scripts/vendor) is inlined in front of the
// widget module by the Python side, as a classic script that sets the global `anywidgetVectorVendor`.
// The types come from @types/three (the vendored build is three@0.186.1).
import type * as THREE_TYPES from "three";
import type { OrbitControls as OrbitControlsType } from "three/addons/controls/OrbitControls.js";

declare global {
  // eslint-disable-next-line no-var
  var anywidgetVectorVendor: { THREE: typeof THREE_TYPES; OrbitControls: typeof OrbitControlsType };
}

export const THREE: typeof THREE_TYPES = globalThis.anywidgetVectorVendor.THREE;
export const OrbitControls: typeof OrbitControlsType = globalThis.anywidgetVectorVendor.OrbitControls;
