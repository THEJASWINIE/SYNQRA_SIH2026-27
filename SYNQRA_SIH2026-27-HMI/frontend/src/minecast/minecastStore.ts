/**
 * Mine-Cast view state — what the OPERATOR has chosen to look at.
 *
 * ==========================================================================
 *  THIS IS UI STATE. IT IS NOT OPERATIONAL STATE.
 *
 *  Selection, layer visibility and panel collapse live here. Vehicle speed, safety,
 *  position, provenance and link state do NOT - those come from `projectMineCast`, which
 *  reads the canonical Twin. Nothing in this file can influence a physical quantity,
 *  because nothing in this file is ever read by a projection.
 *
 *  Rule 6 (root CLAUDE.md): frontend state may hold selection and presentation, and must
 *  never hold or invent authoritative vehicle state. That line is the reason this module
 *  is separate from `minecastProjection.ts` rather than one convenient blob.
 * ==========================================================================
 *
 * TOGGLING A LAYER DOES NOT MAKE IT EXIST
 *
 * `LAYERS` declares which layers have a renderer. Pass 1 has no 3D scene, so the toggles
 * record intent and the drawer says NOT BUILT next to each one. A switch that silently
 * does nothing would teach an operator that a layer is on while nothing is drawn - which
 * is the exact class of lie this project exists to avoid.
 *
 * The reducer is a pure function so it can be tested without React (M4D-C). The hook is a
 * thin `useReducer` wrapper.
 */

import { useCallback, useMemo, useReducer } from "react";

import { LAYERS, type LayerId } from "./minecastProjection";

/** Which floating panels are open. Collapsible per the specification. */
export interface PanelVisibility {
  readonly fleet: boolean;
  readonly vehicle: boolean;
  readonly layers: boolean;
  readonly legend: boolean;
  readonly provenance: boolean;
  readonly miniMap: boolean;
}

/**
 * MINECAST-03: a one-shot camera request from the DOM map controls.
 *
 * The camera lives inside the WebGL canvas; the buttons live outside it. Rather than
 * reaching across with a ref (which would make a panel depend on a Three.js object), the
 * shell records WHAT was asked for and a sequence number, and the scene applies it once
 * when the sequence changes. View state only - no operational data.
 */
export type CameraCommand = "FIT" | "ZOOM_IN" | "ZOOM_OUT" | "PLAN_VIEW" | "OBLIQUE_VIEW";

export interface CameraRequest {
  readonly command: CameraCommand;
  /** Monotonic, so the same command twice in a row is applied twice. */
  readonly seq: number;
}

export interface MineCastViewState {
  /**
   * The CANONICAL id of the selected vehicle, or null.
   *
   * Canonical, not the display label: a selection has to be usable as a key into the
   * projection, and "T01" is not a key the Twin would recognise.
   */
  readonly selectedVehicleId: string | null;
  readonly layerVisibility: Readonly<Record<LayerId, boolean>>;
  readonly panels: PanelVisibility;
  /** The latest camera request, or null before any button has been pressed. */
  readonly cameraRequest: CameraRequest | null;
}

export type MineCastAction =
  | { readonly type: "SELECT_VEHICLE"; readonly canonicalVehicleId: string | null }
  | { readonly type: "TOGGLE_LAYER"; readonly layerId: LayerId }
  | { readonly type: "SET_LAYER"; readonly layerId: LayerId; readonly visible: boolean }
  | { readonly type: "TOGGLE_PANEL"; readonly panel: keyof PanelVisibility }
  | { readonly type: "REQUEST_CAMERA"; readonly command: CameraCommand }
  | { readonly type: "RESET_VIEW" };

/** Layer defaults come from the catalogue, so there is one source for them. */
function defaultLayerVisibility(): Record<LayerId, boolean> {
  const visibility = {} as Record<LayerId, boolean>;
  for (const layer of LAYERS) visibility[layer.id] = layer.defaultVisible;
  return visibility;
}

export const DEFAULT_PANELS: PanelVisibility = {
  fleet: true,
  vehicle: true,
  layers: true,
  legend: true,
  provenance: true,
  miniMap: true,
};

/**
 * The opening view.
 *
 * No vehicle is selected. Deliberately not "select the first truck": a console that
 * pre-selects a vehicle invites an operator to read the wrong one's panel, and with two
 * trucks the odds of that are even.
 */
export function initialViewState(): MineCastViewState {
  return {
    selectedVehicleId: null,
    layerVisibility: defaultLayerVisibility(),
    panels: DEFAULT_PANELS,
    cameraRequest: null,
  };
}

/** Pure reducer. Same input, same output, no side effects, no clock, no I/O. */
export function minecastReducer(
  state: MineCastViewState,
  action: MineCastAction,
): MineCastViewState {
  switch (action.type) {
    case "SELECT_VEHICLE":
      return { ...state, selectedVehicleId: action.canonicalVehicleId };

    case "TOGGLE_LAYER":
      return {
        ...state,
        layerVisibility: {
          ...state.layerVisibility,
          [action.layerId]: !state.layerVisibility[action.layerId],
        },
      };

    case "SET_LAYER":
      return {
        ...state,
        layerVisibility: { ...state.layerVisibility, [action.layerId]: action.visible },
      };

    case "TOGGLE_PANEL":
      return {
        ...state,
        panels: { ...state.panels, [action.panel]: !state.panels[action.panel] },
      };

    case "REQUEST_CAMERA":
      return {
        ...state,
        cameraRequest: {
          command: action.command,
          seq: (state.cameraRequest?.seq ?? 0) + 1,
        },
      };

    case "RESET_VIEW":
      return initialViewState();
  }
}

export interface MineCastStore {
  readonly view: MineCastViewState;
  readonly selectVehicle: (canonicalVehicleId: string | null) => void;
  readonly toggleLayer: (layerId: LayerId) => void;
  readonly setLayer: (layerId: LayerId, visible: boolean) => void;
  readonly togglePanel: (panel: keyof PanelVisibility) => void;
  readonly requestCamera: (command: CameraCommand) => void;
  readonly resetView: () => void;
}

/** React binding for the reducer above. Holds no operational data. */
export function useMineCastStore(initial: MineCastViewState = initialViewState()): MineCastStore {
  const [view, dispatch] = useReducer(minecastReducer, initial);

  const selectVehicle = useCallback(
    (canonicalVehicleId: string | null) => dispatch({ type: "SELECT_VEHICLE", canonicalVehicleId }),
    [],
  );
  const toggleLayer = useCallback(
    (layerId: LayerId) => dispatch({ type: "TOGGLE_LAYER", layerId }),
    [],
  );
  const setLayer = useCallback(
    (layerId: LayerId, visible: boolean) => dispatch({ type: "SET_LAYER", layerId, visible }),
    [],
  );
  const togglePanel = useCallback(
    (panel: keyof PanelVisibility) => dispatch({ type: "TOGGLE_PANEL", panel }),
    [],
  );
  const requestCamera = useCallback(
    (command: CameraCommand) => dispatch({ type: "REQUEST_CAMERA", command }),
    [],
  );
  const resetView = useCallback(() => dispatch({ type: "RESET_VIEW" }), []);

  return useMemo(
    () => ({ view, selectVehicle, toggleLayer, setLayer, togglePanel, requestCamera, resetView }),
    [view, selectVehicle, toggleLayer, setLayer, togglePanel, requestCamera, resetView],
  );
}
