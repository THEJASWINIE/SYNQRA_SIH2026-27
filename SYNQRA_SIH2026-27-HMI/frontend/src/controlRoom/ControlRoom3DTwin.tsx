/**
 * S1-native 3D Digital Twin Viewport for Control Room Operations Overview.
 *
 * ==========================================================================
 *  ONE DIGITAL TWIN, S1-NATIVE 3D WORKSPACE
 *
 *  Provides an interactive 3D spatial view of the Bailadila Deposit-5 Digital Twin
 *  directly inside the Control Room S1 center column.
 *
 *  ARCHITECTURAL SEPARATION:
 *  - Consumes canonical Twin vehicle state from ProviderHost / AppStateStore.
 *  - S1 owns its own 3D camera state, camera controls, and vehicle selection.
 *  - Zero dependency on Mine-Cast application state (minecastStore, MineCastApp).
 *  - Reuses the low-level rendering primitive MineCanvas via React.lazy. The only
 *    Mine-Cast modules reached are pure projections/primitives (asserted in
 *    controlRoomWorkspace.test.tsx).
 *  - WebGL is detected synchronously at first render: without a context (SSR, Node
 *    tests, a browser without WebGL) an honest notice is drawn and Three.js is never
 *    loaded. S1 keeps working either way.
 * ==========================================================================
 */

import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";

import { type LayerId, projectMineCast } from "../minecast/minecastProjection";
import { spatialPositions } from "../minecast/spatialPosition";
import { VERTICAL_EXAGGERATION } from "../minecast/terrainField";
import { CORRIDOR_DISCLOSURE } from "../state/sceneCorridors";
import { useAppState } from "../state/useAppState";
import { SCENE_FRAME, TWIN_SCENE_LABEL } from "../state/vehiclePosition";

/** Disclosures every 3D frame carries. Exported so the tests assert the exact wording. */
export const TWIN_3D_DISCLOSURES = {
  provenance: "3D DIGITAL TWIN · SIMULATION",
  frame: SCENE_FRAME,
  geometry: "SYNTHETIC DEMONSTRATION GEOMETRY",
  vehicles: `VEHICLES: DIGITAL TWIN SIMULATION (${SCENE_FRAME}) · NOT GNSS`,
  terrain: `SYNTHETIC TERRAIN · NOT SURVEYED · VERTICAL SCALE ${VERTICAL_EXAGGERATION}x`,
  extent: "PUBLISHED COORDINATE EXTENT — NOT A LEASE BOUNDARY",
} as const;

/**
 * Lazy-loaded WebGL canvas keeps Three.js out of SSR and Node test environments.
 */
const MineCanvas = lazy(() => import("../minecast/MineCanvas"));

export type CameraCommand = "FIT" | "ZOOM_IN" | "ZOOM_OUT" | "PLAN_VIEW" | "OBLIQUE_VIEW";

export interface CameraRequest {
  readonly command: CameraCommand;
  readonly seq: number;
}

export interface ControlRoom3DTwinProps {
  /** Canonical vehicleId owned by S1; drawn as the selection ring. */
  readonly selectedVehicleId: string | null;
  readonly onSelectVehicle?: (vehicleId: string) => void;
  /** S1 HAUL ROUTES emphasis: route labels and brighter corridors in the scene. */
  readonly routeEmphasis?: boolean;
}

/** Check if WebGL is available in the current browser environment. */
function detectWebgl(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl2") ??
        canvas.getContext("webgl") ??
        canvas.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}

/** Default operational layer visibility for S1 3D workspace. */
const DEFAULT_3D_LAYERS: Record<LayerId, boolean> = {
  TERRAIN: true,
  ORTHOPHOTO: false,
  PUBLISHED_EXTENT: true,
  PIT: true,
  BENCHES: true,
  HAUL_ROADS: true,
  RAMPS: true,
  MINE_ZONES: true,
  VEHICLES: true,
  ROUTES: false,
  SAFETY: true,
  V2V: true,
  V2I_RSU: false,
};

export function ControlRoom3DTwin({
  selectedVehicleId,
  onSelectVehicle,
  routeEmphasis = false,
}: ControlRoom3DTwinProps) {
  const state = useAppState();
  const host = useRef<HTMLDivElement | null>(null);
  const [webgl] = useState(detectWebgl);
  const [aspect, setAspect] = useState(16 / 9);

  // S1 owns its own camera state entirely (independent of minecastStore)
  const [cameraRequest, setCameraRequest] = useState<CameraRequest | null>(null);

  const sendCamera = (command: CameraCommand) => {
    setCameraRequest((prev) => ({ command, seq: (prev?.seq ?? 0) + 1 }));
  };

  useEffect(() => {
    const el = host.current;
    if (!el) return;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setAspect(rect.width / rect.height);
      }
    };
    measure();

    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /*
    ONE source: the same AppStateStore the 2D map reads. `projectMineCast` is a pure
    projection of canonical Twin state; `spatialPositions` passes `position_scene`
    through in SCENE_METRES. Nothing here is a second position source.
  */
  const minecast = useMemo(() => projectMineCast(state), [state]);
  const vehiclePositions = useMemo(
    () => spatialPositions(minecast.vehicles, minecast.site),
    [minecast.vehicles, minecast.site],
  );
  // The route id the Twin stamped on the selected pose - read, never inferred here.
  const highlightRouteId =
    minecast.vehicles.find((v) => v.canonicalVehicleId === selectedVehicleId)?.scenePose
      ?.routeId ?? null;

  return (
    <div className="cr-3d-workspace" ref={host} data-testid="cr-3d-twin">
      {/* Provenance strip: what this view is, and what its geometry is not. */}
      <div className="cr-corridor-strip" role="note">
        <span className="cr-corridor-tag cr-3d-provenance">
          {`${TWIN_3D_DISCLOSURES.provenance} · ${TWIN_3D_DISCLOSURES.frame}`}
        </span>
        <span className="cr-corridor-tag faint">
          {`${TWIN_3D_DISCLOSURES.geometry} · ${CORRIDOR_DISCLOSURE}`}
        </span>
      </div>

      <div className="cr-3d-canvas-wrap">
        {!webgl ? (
          <div className="mc-canvas-notice" role="note">
            <h2 className="mc-placeholder-title">WEBGL UNAVAILABLE</h2>
            <p>
              This browser reports no WebGL context, so no 3D scene is drawn. Switch to 2D
              MAP: the same Digital Twin state is shown there.
            </p>
          </div>
        ) : (
          <Suspense
            fallback={
              <div className="mc-canvas-notice" role="status">
                <h2 className="mc-placeholder-title">LOADING 3D SPATIAL VIEW</h2>
              </div>
            }
          >
            <MineCanvas
              site={minecast.site}
              layerVisibility={DEFAULT_3D_LAYERS}
              aspect={aspect}
              vehiclePositions={vehiclePositions}
              vehicles={minecast.vehicles}
              cameraRequest={cameraRequest}
              selectedVehicleId={selectedVehicleId}
              onSelectVehicle={onSelectVehicle}
              routeEmphasis={routeEmphasis}
              highlightRouteId={highlightRouteId}
            />
          </Suspense>
        )}

        {/* S1-native Camera Controls Rail */}
        <nav className="cr-3d-controls" aria-label="3D Camera Controls">
          <button
            type="button"
            className="cr-cam-btn"
            title="Fit scene to overview"
            onClick={() => sendCamera("FIT")}
          >
            FIT
          </button>
          <button
            type="button"
            className="cr-cam-btn"
            title="Zoom in"
            onClick={() => sendCamera("ZOOM_IN")}
          >
            +
          </button>
          <button
            type="button"
            className="cr-cam-btn"
            title="Zoom out"
            onClick={() => sendCamera("ZOOM_OUT")}
          >
            −
          </button>
          <button
            type="button"
            className="cr-cam-btn"
            title="Orthographic top-down plan view"
            onClick={() => sendCamera("PLAN_VIEW")}
          >
            PLAN
          </button>
          <button
            type="button"
            className="cr-cam-btn"
            title="Oblique 3D perspective view"
            onClick={() => sendCamera("OBLIQUE_VIEW")}
          >
            3D
          </button>
        </nav>
      </div>

      {/* Persistent 3D disclosures matching Twin contracts */}
      <footer className="cr-3d-disclosures">
        <span>{TWIN_3D_DISCLOSURES.terrain}</span>
        <span>{TWIN_3D_DISCLOSURES.extent}</span>
        <span>{`${TWIN_3D_DISCLOSURES.vehicles} · ${TWIN_SCENE_LABEL}`}</span>
      </footer>
    </div>
  );
}
