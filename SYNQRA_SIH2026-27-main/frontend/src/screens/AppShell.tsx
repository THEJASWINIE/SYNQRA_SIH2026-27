/**
 * Application shell — M4.
 *
 * Owns navigation and the global status header. Four things are visible on EVERY screen,
 * because an operator must never have to navigate to find out that the system is degraded:
 *
 *   system mode · connection · active scenario · freshness state
 *
 * System mode is SUPPLIED on `SystemHealth.systemMode`. When it has not been supplied the
 * shell says so. It never falls back to NORMAL — displaying a reassuring mode nobody sent
 * is the most dangerous substitution this HMI can make.
 */

import { useState } from "react";
import { BackendHealth } from "../components/BackendHealth";
import { StatusBadge } from "../components/primitives";
import { useHmi } from "../state/ProviderHost";
import { displayedModeFor, MODE_SOURCE_TEXT } from "../state/systemMode";
import { useAppState } from "../state/useAppState";
import { providerStatusToken, systemModeToken } from "../theme/statusTokens";
import { AlertList } from "./AlertList";
import { BottleneckQueue } from "./BottleneckQueue";
import { Diagnostics } from "./Diagnostics";
import { DispatchSlots } from "./DispatchSlots";
import { EventReplay } from "./EventReplay";
import { OperationsOverview } from "./OperationsOverview";
import { VehicleDetail } from "./VehicleDetail";

const OVERVIEW_ID = "overview";
export const VEHICLE_ID = "vehicle";
const BOTTLENECK_ID = "bottleneck";
const DISPATCH_ID = "dispatch";
const ALERTS_ID = "alerts";
const REPLAY_ID = "replay";
const DIAGNOSTICS_ID = "diagnostics";

export function AppShell() {
  const state = useAppState();
  const { freshness, freshnessReason } = useHmi();
  const [screenId, setScreenId] = useState<string>(OVERVIEW_ID);
  /**
   * Which vehicle S2 shows. UI state, not operational data — the vehicle itself is read
   * out of the store on every render, so this holds an id and never a copy of a vehicle.
   */
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);

  const openVehicle = (vehicleId: string) => {
    setSelectedVehicleId(vehicleId);
    setScreenId(VEHICLE_ID);
  };

  /**
   * FR-016 AC3 / OPS-003 / NFR-012 — the displayed mode is raised to at least DEGRADED
   * when the HMI's own feed is lost. `state.health.systemMode` is never mutated; this is
   * a display result (M8D-A). A supplied LOCAL_SAFE or STOP_UNSAFE is never softened.
   */
  const displayedMode = displayedModeFor(state);
  const mode = displayedMode.mode;

  return (
    <div className="hmi">
      <header className="hmi-header">
        <h1 className="hmi-title">FOG-ORCHESTRATOR 2.0 — TASK 1 HMI</h1>

        <dl className="hmi-header-slot">
          <dt>System mode</dt>
          <dd>
            {mode === null ? (
              <span className="dim">NOT SUPPLIED</span>
            ) : (
              <StatusBadge token={systemModeToken(mode)} />
            )}
            {displayedMode.flooredByFeedLoss ? (
              <div className="faint">{MODE_SOURCE_TEXT[displayedMode.source]}</div>
            ) : null}
          </dd>
        </dl>

        <dl className="hmi-header-slot">
          <dt>Data connection</dt>
          <dd>
            <StatusBadge token={providerStatusToken(state.connection.status)} />
            {state.connection.error ? <div className="faint">{state.connection.error}</div> : null}
          </dd>
        </dl>

        {/* FR-017 AC2 — replay must be flagged globally and must never be mistakable for
            live. Rendered in the shell, so it appears on every screen. */}
        <dl className="hmi-header-slot">
          <dt>Mode</dt>
          <dd>
            {state.connection.provider === "REPLAY" ? (
              <span className="replay-live replay-on">▶ REPLAY — NOT LIVE</span>
            ) : (
              <span className="replay-live">● LIVE</span>
            )}
            {state.clock.replayPosition ? (
              <div className="faint">at {state.clock.replayPosition.slice(11, 23)} UTC</div>
            ) : null}
          </dd>
        </dl>

        <dl className="hmi-header-slot">
          <dt>Provider / scenario</dt>
          <dd>
            <span className="mono">{state.connection.provider}</span>{" "}
            <span className="faint">{state.connection.scenarioName ?? "none"}</span>
          </dd>
        </dl>

        <dl className="hmi-header-slot">
          <dt>Fleet / connectivity</dt>
          <dd>
            <span className="mono">{Object.keys(state.vehicles).length}</span>{" "}
            <span className="faint">
              vehicles · {state.health?.connectivity ?? "connectivity not supplied"}
            </span>
          </dd>
        </dl>

        <dl>
          <BackendHealth />
        </dl>
      </header>

      <nav className="hmi-nav" aria-label="Screens">
        <button
          type="button"
          aria-current={screenId === OVERVIEW_ID ? "page" : undefined}
          onClick={() => setScreenId(OVERVIEW_ID)}
        >
          S1 Operations
        </button>
        <button
          type="button"
          aria-current={screenId === VEHICLE_ID ? "page" : undefined}
          onClick={() => setScreenId(VEHICLE_ID)}
        >
          S2 Vehicle
          {selectedVehicleId ? ` · ${selectedVehicleId}` : ""}
        </button>
        <button
          type="button"
          aria-current={screenId === BOTTLENECK_ID ? "page" : undefined}
          onClick={() => setScreenId(BOTTLENECK_ID)}
        >
          S3 Bottleneck
        </button>
        <button
          type="button"
          aria-current={screenId === DISPATCH_ID ? "page" : undefined}
          onClick={() => setScreenId(DISPATCH_ID)}
        >
          S4 Dispatch
        </button>
        <button
          type="button"
          aria-current={screenId === ALERTS_ID ? "page" : undefined}
          onClick={() => setScreenId(ALERTS_ID)}
        >
          Alerts
        </button>
        <button
          type="button"
          aria-current={screenId === REPLAY_ID ? "page" : undefined}
          onClick={() => setScreenId(REPLAY_ID)}
        >
          S5 Replay
        </button>
        <button
          type="button"
          aria-current={screenId === DIAGNOSTICS_ID ? "page" : undefined}
          onClick={() => setScreenId(DIAGNOSTICS_ID)}
        >
          S6 Diagnostics
        </button>
      </nav>

      <main className="hmi-main">
        {/*
         * AMB-014 — UNRESOLVED. HMI-NFR-003 requires a configurable staleness timeout and
         * the specification states no value. PAD-G forbids inventing one, so when it is
         * unconfigured the HMI says so permanently and does not classify staleness at all.
         */}
        {freshness === null ? (
          <div className="hmi-banner" role="status">
            <div className="hmi-banner-title">▲ FRESHNESS THRESHOLD NOT CONFIGURED</div>
            <p>
              Data age is still shown. Stale classification is <strong>not evaluated</strong>. No
              authoritative timeout has been configured — HMI-NFR-003 requires one and the
              specification states no value (AMB-014, unresolved). No default is assumed.
            </p>
            {freshnessReason ? <p className="faint">{freshnessReason}</p> : null}
          </div>
        ) : (
          <div className="hmi-banner" role="status">
            <div className="hmi-banner-title">
              Freshness threshold {freshness.staleTimeoutMs} ms — DEVELOPMENT VALUE
            </div>
            <p>
              Not authoritative. Supplied by local configuration for development only; AMB-014
              remains unresolved and the specification states no value.
            </p>
          </div>
        )}

        {screenId === VEHICLE_ID ? (
          <VehicleDetail vehicleId={selectedVehicleId} onBack={() => setScreenId(OVERVIEW_ID)} />
        ) : screenId === BOTTLENECK_ID ? (
          <BottleneckQueue />
        ) : screenId === DISPATCH_ID ? (
          <DispatchSlots />
        ) : screenId === ALERTS_ID ? (
          <AlertList />
        ) : screenId === REPLAY_ID ? (
          <EventReplay />
        ) : screenId === DIAGNOSTICS_ID ? (
          <Diagnostics />
        ) : (
          <OperationsOverview onSelectVehicle={openVehicle} />
        )}
      </main>
    </div>
  );
}
