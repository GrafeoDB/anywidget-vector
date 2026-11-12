// The vendored Three.js bundle (ui/vendor/three.min.js, built by scripts/vendor) is inlined in front of this bundle
// by the Python side, in the same ES module: it is one top-level `var anywidgetVectorVendor`, which in a module is a
// module-scoped binding, not a property of globalThis. So it is read by its bare name, which resolves to that binding
// (and to the global when a test evaluates the vendored file as a classic script).
// The types come from @types/three (the vendored build is three@0.186.1).
import type * as THREE_TYPES from "three";
import type { OrbitControls as OrbitControlsType } from "three/addons/controls/OrbitControls.js";

declare global {
  // eslint-disable-next-line no-var
  var anywidgetVectorVendor: { THREE: typeof THREE_TYPES; OrbitControls: typeof OrbitControlsType };
}

export const THREE: typeof THREE_TYPES = anywidgetVectorVendor.THREE;
export const OrbitControls: typeof OrbitControlsType = anywidgetVectorVendor.OrbitControls;
