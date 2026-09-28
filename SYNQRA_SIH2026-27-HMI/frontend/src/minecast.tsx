/**
 * Mine-Cast entry point — mine-cast.html.
 *
 * The fourth client view of the one canonical Twin, alongside the control room
 * (index.html) and the two vehicle consoles (truck01.html, truck02.html).
 *
 * Deliberately minimal, matching `src/truck01.tsx` and `src/truck02.tsx`: find the root,
 * mount the app. Mine-Cast takes no vehicle prop - it is a fleet-wide view, and the
 * vehicle it inspects is an operator selection, not a build-time identity.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MineCastApp } from "./minecast/MineCastApp";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root is missing from mine-cast.html");
}

createRoot(container).render(
  <StrictMode>
    <MineCastApp />
  </StrictMode>,
);
