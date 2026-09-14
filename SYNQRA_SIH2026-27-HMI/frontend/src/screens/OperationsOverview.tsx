/**
 * S1 Digital Twin — CONTROL ROOM OPERATIONS OVERVIEW.
 *
 * Dense operations control-room layout matching the Mine-Cast-03 visual language:
 * - 2D mine map as the dominant workspace
 * - Compact fleet panel on the left (sorted by canonical vehicleId)
 * - Selected vehicle context panel on the right (with strict safety/communication truthfulness)
 * - Compact top status strip with explicit Twin provenance
 * - Persistent footer disclosure: DIGITAL TWIN · SCENE_METRES · SIMULATION · NOT GNSS
 *
 * READ-ONLY PROJECTION: Computes no operational values. All data originates from the
 * authoritative Digital Twin via ProviderHost and AppStateStore.
 */

import { useMemo, useReducer } from "react";
import { BackendHealth } from "../components/BackendHealth";
import { EmptyState, Panel, StatusBadge } from "../components/primitives";
import { VehicleCard } from "../components/VehicleCard";
import { communicationText, vehicleProvenanceLabel } from "../state/dataStatus";
import { fleetSummary } from "../state/derive";
import { viewFreshness } from "../state/freshness";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import {
  fleetPositions,
  providerForMode,
  type SystemMode,
} from "../state/vehiclePosition";
import { providerStatusToken } from "../theme/statusTokens";
import { communicationLinks, LINK_STATE_GLYPH } from "../vehicle/communication";
import { ControlRoom3DTwin } from "../controlRoom/ControlRoom3DTwin";
import {
  INITIAL_WORKSPACE,
  type S1Workspace,
  workspaceReducer,
} from "../controlRoom/workspaceState";
import { GeoSiteMap } from "./GeoSiteMap";

/** Format m/s speed to km/h and m/s string, or UNAVAILABLE. Never coerce null to 0. */
function formatSpeed(speedMps: number | null): string {
  if (speedMps === null || !Number.isFinite(speedMps)) {
    return "UNAVAILABLE";
  }
  return `${(speedMps * 3.6).toFixed(0)} km/h (${speedMps.toFixed(1)} m/s)`;
}

export function OperationsOverview({
  onSelectVehicle,
  initialWorkspace,
}: {
  /** Opens S2 Vehicle Detail. Selection is UI state and lives in the shell. */
  onSelectVehicle: (vehicleId: string) => void;
  /** Starting UI state (mode + selection). Defaults to 2D MAP with nothing selected. */
  initialWorkspace?: Partial<S1Workspace> | undefined;
}) {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  const fresh = (timestamp: string | null | undefined) => viewFreshness(timestamp, config, nowMs);

  const geoSite = bailadilaDeposit5();
  const geoExtent = toDecimalExtent(geoSite.extent);
  const geoPositions = fleetPositions(
    state.vehicles,
    providerForMode(state.connection.provider as SystemMode, geoExtent),
    geoExtent,
  );

  const fleet = fleetSummary(state);
  const vehicles = useMemo(
    () => Object.values(state.vehicles).sort((a, b) => a.vehicleId.localeCompare(b.vehicleId)),
    [state.vehicles],
  );

  /*
    S1 owns the workspace UI state: renderer mode and selected vehicle. The toggle only
    changes `mode`; Twin state is never touched. See controlRoom/workspaceState.ts.
  */
  const [workspace, dispatch] = useReducer(workspaceReducer, {
    ...INITIAL_WORKSPACE,
    ...initialWorkspace,
  });
  const { mode: workspaceMode, selectedVehicleId: selectedId, routeEmphasis } = workspace;
  const setSelectedId = (vehicleId: string) => dispatch({ type: "SELECT_VEHICLE", vehicleId });
  const setWorkspaceMode = (mode: S1Workspace["mode"]) => dispatch({ type: "SET_MODE", mode });
  const setRouteEmphasis = (on: boolean) => dispatch({ type: "SET_ROUTE_EMPHASIS", on });

  // Active selected vehicle (uses vehicleId, never array index)
  const activeSelectedId =
    (selectedId && state.vehicles[selectedId] ? selectedId : null) ??
    vehicles[0]?.vehicleId ??
    null;

  const selectedVehicle = activeSelectedId ? state.vehicles[activeSelectedId] ?? null : null;
  const selectedSafety = selectedVehicle ? state.safety[selectedVehicle.vehicleId] : undefined;
  const selectedPosition = selectedVehicle
    ? geoPositions.find((p) => p.vehicleId === selectedVehicle.vehicleId)
    : undefined;

  const links = useMemo(() => {
    if (!selectedVehicle) return [];
    return communicationLinks(selectedVehicle, state.connection.status, state.connection.provider);
  }, [selectedVehicle, state.connection.status, state.connection.provider]);

  const v2vLink = links.find((l) => l.label === "V2V");
  const v2iLink = links.find((l) => l.label === "V2I");

  // Truthful live feed state
  const isReplay = state.connection.provider === "REPLAY";
  const isConnected = state.connection.status.toUpperCase() === "CONNECTED";
  const feedStateText = isReplay ? "REPLAY ▶" : isConnected ? "LIVE ●" : "DISCONNECTED ○";

  return (
    <section className="hmi-screen cr-deck" aria-label="Control Room Digital Twin">
      {/* ---- TOP STATUS STRIP ---- */}
      <header className="cr-topbar" role="banner">
        <div className="cr-identity">
          <span className="cr-title">CONTROL ROOM / DIGITAL TWIN</span>
          <span className="cr-subtitle">NMDC BAILADILA · DEPOSIT-5 OPERATIONS</span>
        </div>

        <div className="cr-status-group">
          <div className="cr-status-pill" data-feed={isReplay ? "REPLAY" : isConnected ? "LIVE" : "DISCONNECTED"}>
            <span className="cr-pill-label">STATUS</span>
            <span className="cr-pill-value">{feedStateText}</span>
          </div>

          <div className="cr-status-pill">
            <span className="cr-pill-label">BACKEND</span>
            <span className="cr-pill-value">
              <StatusBadge token={providerStatusToken(state.connection.status)} />
              {" "}
              {isConnected ? "BACKEND CONNECTED" : state.connection.status}
            </span>
          </div>

          <div className="cr-status-pill">
            <span className="cr-pill-label">FLEET</span>
            <span className="cr-pill-value mono">{`TWIN ${vehicles.length} VEHICLES`}</span>
          </div>

          <div className="cr-status-pill">
            <span className="cr-pill-label">MODE</span>
            <span className="cr-pill-value mono">{state.connection.provider}</span>
          </div>

          <BackendHealth />
        </div>

        {state.connection.error ? (
          <div className="cr-topbar-error" role="alert">
            {state.connection.error}
          </div>
        ) : null}
      </header>

      {/* ---- 3-COLUMN OPERATIONS WORKSPACE ---- */}
      <div className="cr-workspace">
        <div className="grid-2" style={{ display: "contents" }}>
          {/* LEFT: FLEET PANEL */}
          <aside className="cr-col-fleet" aria-label="Fleet Overview">
          <Panel
            title="Fleet"
            note={`${fleet.total} total · ${fleet.withPosition} positioned · ${fleet.overSafeSpeed} over safe`}
          >
            {vehicles.length === 0 ? (
              <EmptyState
                headline="NO VEHICLES SUPPLIED"
                detail="No vehicle state has been received for this scenario yet."
              />
            ) : (
              <div className="cr-fleet-list" role="list">
                {vehicles.map((v) => {
                  const isSelected = v.vehicleId === activeSelectedId;

                  return (
                    <div
                      key={v.vehicleId}
                      className={`cr-fleet-card-wrapper ${isSelected ? "cr-selected" : ""}`}
                      data-vehicle-id={v.vehicleId}
                      onClick={() => setSelectedId(v.vehicleId)}
                    >
                      <VehicleCard
                        vehicle={v}
                        safety={state.safety[v.vehicleId]}
                        freshness={fresh(v.timestamp)}
                        onSelect={onSelectVehicle}
                        providerMode={state.connection.provider}
                        connectionStatus={state.connection.status}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        </aside>

        {/* CENTRE: DOMINANT DIGITAL TWIN WORKSPACE (2D MAP / 3D TWIN) */}
        <main className="cr-col-map" aria-label="Digital Twin Workspace">
          <header className="cr-workspace-header">
            <div className="cr-workspace-title-group">
              <span className="cr-workspace-title">OPERATIONAL WORKSPACE</span>
              <span className="cr-workspace-subtitle mono">
                {workspaceMode === "2D" ? "2D SCENE MAP" : "3D DIGITAL TWIN"}
              </span>
            </div>
            <div className="cr-header-controls">
            <button
              type="button"
              className={`cr-route-toggle ${routeEmphasis ? "active" : ""}`}
              onClick={() => setRouteEmphasis(!routeEmphasis)}
              aria-pressed={routeEmphasis}
              data-route-emphasis={routeEmphasis ? "on" : "off"}
              title="Emphasise the synthetic haul routes: labels, direction arrows, selected route"
            >
              HAUL ROUTES
            </button>
            <div className="cr-view-toggle" role="group" aria-label="Workspace View Mode">
              <button
                type="button"
                className={`cr-view-btn ${workspaceMode === "2D" ? "active" : ""}`}
                onClick={() => setWorkspaceMode("2D")}
                data-view-mode="2D"
                aria-pressed={workspaceMode === "2D"}
              >
                2D MAP
              </button>
              <button
                type="button"
                className={`cr-view-btn ${workspaceMode === "3D" ? "active" : ""}`}
                onClick={() => setWorkspaceMode("3D")}
                data-view-mode="3D"
                aria-pressed={workspaceMode === "3D"}
              >
                3D TWIN
              </button>
            </div>
            </div>
          </header>

          {workspaceMode === "2D" ? (
            <GeoSiteMap
              site={geoSite}
              positions={geoPositions}
              mode={state.connection.provider}
              selectedVehicleId={activeSelectedId}
              onSelectVehicle={(vid) => setSelectedId(vid)}
              routeEmphasis={routeEmphasis}
            />
          ) : (
            <ControlRoom3DTwin
              selectedVehicleId={activeSelectedId}
              onSelectVehicle={(vid) => setSelectedId(vid)}
              routeEmphasis={routeEmphasis}
            />
          )}
        </main>

        {/* RIGHT: SELECTED VEHICLE CONTEXT PANEL */}
        <aside className="cr-col-selected" aria-label="Selected Vehicle Context">
          <Panel
            title="SELECTED VEHICLE"
            note={selectedVehicle ? selectedVehicle.vehicleId : "None"}
          >
            {!selectedVehicle ? (
              <EmptyState
                headline="NO VEHICLE SELECTED"
                detail="Select a vehicle in the fleet panel or on the map to inspect its state."
              />
            ) : (
              <div className="cr-selected-body" data-vehicle-id={selectedVehicle.vehicleId}>
                <div className="cr-selected-head">
                  <span className="cr-selected-title mono">{selectedVehicle.vehicleId}</span>
                  <span className="cr-badge cr-badge-info">{selectedVehicle.mode ?? "UNAVAILABLE"}</span>
                </div>

                <h4>MOTION</h4>
                <table className="data-table cr-compact-table">
                  <tbody>
                    <tr>
                      <td>Speed</td>
                      <td className="mono">{formatSpeed(selectedVehicle.speedMps)}</td>
                    </tr>
                    <tr>
                      <td>Mode</td>
                      <td>{selectedVehicle.mode ?? "UNAVAILABLE"}</td>
                    </tr>
                    <tr>
                      <td>Freshness</td>
                      <td>{fresh(selectedVehicle.timestamp).quality ?? "UNEVALUATED"}</td>
                    </tr>
                    <tr>
                      <td>Data Source</td>
                      <td className="mono faint">{vehicleProvenanceLabel(selectedVehicle)}</td>
                    </tr>
                  </tbody>
                </table>

                <h4>POSITION</h4>
                <table className="data-table cr-compact-table">
                  <tbody>
                    <tr>
                      <td>Status</td>
                      <td>{selectedPosition?.position ? "POSITIONED" : "UNAVAILABLE"}</td>
                    </tr>
                    <tr>
                      <td>Provenance</td>
                      <td className="mono">
                        {selectedPosition?.provenance === "SIMULATED_TWIN_SCENE"
                          ? "SIMULATED_TWIN_SCENE"
                          : selectedPosition?.provenance ?? "UNAVAILABLE"}
                      </td>
                    </tr>
                    <tr>
                      <td>Frame</td>
                      <td className="mono">SCENE_METRES</td>
                    </tr>
                    <tr>
                      <td>Route</td>
                      <td
                        className="mono"
                        data-selected-route={selectedPosition?.routeId ?? "UNAVAILABLE"}
                      >
                        {selectedPosition?.routeId
                          ? `${selectedPosition.routeId}${
                              selectedPosition.routeDirection === 1
                                ? " · OUTBOUND"
                                : selectedPosition.routeDirection === -1
                                  ? " · RETURN"
                                  : ""
                            }`
                          : "UNAVAILABLE"}
                      </td>
                    </tr>
                    <tr>
                      <td>Route class</td>
                      <td className="mono faint">
                        {selectedPosition?.routeId ? "SYNTHETIC_DIGITAL_TWIN_ROUTE" : "UNAVAILABLE"}
                      </td>
                    </tr>
                    {selectedPosition?.reason ? (
                      <tr>
                        <td colSpan={2} className="faint">{selectedPosition.reason}</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>

                <h4>SAFETY</h4>
                {!selectedSafety ||
                (selectedSafety.actualSpeed === null &&
                  selectedSafety.vSafe === null &&
                  selectedSafety.riskLevel === null) ? (
                  <p className="cr-safety-alert">SAFETY DATA UNAVAILABLE · DO NOT ASSUME SAFE</p>
                ) : (
                  <table className="data-table cr-compact-table">
                    <tbody>
                      <tr>
                        <td>Actual Speed</td>
                        <td className="mono">{formatSpeed(selectedSafety.actualSpeed)}</td>
                      </tr>
                      <tr>
                        <td>V_safe</td>
                        <td className="mono">{formatSpeed(selectedSafety.vSafe)}</td>
                      </tr>
                      <tr>
                        <td>H_safe</td>
                        <td className="mono">
                          {selectedSafety.hSafe !== null && Number.isFinite(selectedSafety.hSafe)
                            ? `${selectedSafety.hSafe.toFixed(1)} m`
                            : "UNAVAILABLE"}
                        </td>
                      </tr>
                      <tr>
                        <td>Headway</td>
                        <td className="mono">
                          {selectedSafety.headwayCurrent !== null && Number.isFinite(selectedSafety.headwayCurrent)
                            ? `${selectedSafety.headwayCurrent.toFixed(1)} m`
                            : "UNAVAILABLE"}
                        </td>
                      </tr>
                      <tr>
                        <td>Active Constraint</td>
                        <td>{selectedSafety.activeConstraint ?? "UNAVAILABLE"}</td>
                      </tr>
                      <tr>
                        <td>Risk Level</td>
                        <td>{selectedSafety.riskLevel ?? "UNAVAILABLE"}</td>
                      </tr>
                    </tbody>
                  </table>
                )}

                <h4>COMMUNICATION</h4>
                <table className="data-table cr-compact-table">
                  <tbody>
                    <tr>
                      <td>Status</td>
                      <td className="mono">{communicationText(selectedVehicle)}</td>
                    </tr>
                    <tr>
                      <td>V2V Link</td>
                      <td>
                        <span aria-hidden="true">{LINK_STATE_GLYPH[v2vLink?.state ?? "UNAVAILABLE"]}</span>{" "}
                        {v2vLink?.state ?? "UNAVAILABLE"}
                      </td>
                    </tr>
                    <tr>
                      <td>V2I Link</td>
                      <td>
                        <span aria-hidden="true">{LINK_STATE_GLYPH[v2iLink?.state ?? "UNAVAILABLE"]}</span>{" "}
                        {v2iLink?.state ?? "UNAVAILABLE"}
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div className="cr-selected-actions">
                  <button
                    type="button"
                    className="cr-btn-detail"
                    onClick={() => onSelectVehicle(selectedVehicle.vehicleId)}
                  >
                    INSPECT S2 VEHICLE DETAIL ▸
                  </button>
                </div>
              </div>
            )}
          </Panel>
        </aside>
        </div>
      </div>

      {/* ---- PERSISTENT PROVENANCE FOOTER ---- */}
      <footer className="cr-footer" role="contentinfo">
        <div className="cr-footer-item">
          <span className="cr-footer-tag">DIGITAL TWIN · SCENE_METRES · SIMULATION · NOT GNSS</span>
        </div>
        <div className="cr-footer-item">
          <span className="cr-footer-tag faint">
            SYNTHETIC ROUTES · NOT SURVEYED · SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC
            INFRASTRUCTURE · DEMONSTRATION
          </span>
        </div>
      </footer>
    </section>
  );
}
