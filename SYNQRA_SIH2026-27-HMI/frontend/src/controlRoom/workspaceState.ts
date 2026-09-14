/**
 * S1 workspace UI state — the ONLY state the [ 2D MAP ] [ 3D TWIN ] toggle touches.
 *
 * Pure and framework-free so the transitions are testable without a DOM:
 * switching the renderer changes `mode` and nothing else; selecting a vehicle changes
 * `selectedVehicleId` and nothing else. Neither touches Twin state, which lives in
 * AppStateStore and is only ever read by both renderers.
 */

export type WorkspaceMode = "2D" | "3D";

export interface S1Workspace {
  readonly mode: WorkspaceMode;
  /** Canonical vehicleId (never an array index). `null` = nothing chosen yet. */
  readonly selectedVehicleId: string | null;
  /** HAUL ROUTES emphasis: wider bands, labels, arrows, selected route lit. UI state only. */
  readonly routeEmphasis: boolean;
}

export type WorkspaceAction =
  | { readonly type: "SET_MODE"; readonly mode: WorkspaceMode }
  | { readonly type: "SELECT_VEHICLE"; readonly vehicleId: string | null }
  | { readonly type: "SET_ROUTE_EMPHASIS"; readonly on: boolean };

export const INITIAL_WORKSPACE: S1Workspace = {
  mode: "2D",
  selectedVehicleId: null,
  routeEmphasis: false,
};

export function workspaceReducer(state: S1Workspace, action: WorkspaceAction): S1Workspace {
  switch (action.type) {
    case "SET_MODE":
      return state.mode === action.mode ? state : { ...state, mode: action.mode };
    case "SELECT_VEHICLE":
      return state.selectedVehicleId === action.vehicleId
        ? state
        : { ...state, selectedVehicleId: action.vehicleId };
    case "SET_ROUTE_EMPHASIS":
      return state.routeEmphasis === action.on ? state : { ...state, routeEmphasis: action.on };
    default:
      return state;
  }
}
