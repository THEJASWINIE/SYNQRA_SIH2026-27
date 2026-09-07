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
import { EmptyState, Panel, StatusBadge } from "../components/primitives";
import { useHmi } from "../state/ProviderHost";
import { displayedModeFor, MODE_SOURCE_TEXT } from "../state/systemMode";
import { useAppState } from "../state/useAppState";
import { providerStatusToken, systemModeToken } from "../theme/statusTokens";
import { AlertList } from "./AlertList";
import { BottleneckQueue } from "./BottleneckQueue";
import { Diagnostics } from "./Diagnostics";
import { DigitalTwin } from "./DigitalTwin";
import { DispatchSlots } from "./DispatchSlots";
import { EventReplay } from "./EventReplay";
import { OperationsOverview } from "./OperationsOverview";
import { OperatorView } from "./OperatorView";
import { SafetyEnvironment } from "./SafetyEnvironment";
import { VehicleDetail } from "./VehicleDetail";
import { FailureInjectionLab } from "./FailureInjectionLab";

/**
 * CANONICAL SIH SCREENS — S1..S7.
 *
 * The numbering is the contract; the component behind each number is an implementation
 * detail. Screens are therefore RE-LABELLED here rather than renamed on disk, so no test,
 * import or file path churns over a numbering decision.
 *
 * Every canonical number now has a screen. `PENDING_SCREENS` is retained and empty: it is
 * the mechanism by which a declared-but-unbuilt screen says so instead of rendering an
 * empty dashboard, and a future S8 would use it again.
 */
const OVERVIEW_ID = "overview"; // S1 Operations
export const VEHICLE_ID = "vehicle"; // S2 Vehicle Detail
const SAFETY_ID = "safety"; // S3 Safety / Environment
const DISPATCH_ID = "dispatch"; // S4 Dispatch
const ALERTS_ID = "alerts"; // S5 Alerts
const TWIN_ID = "twin"; // S6 Digital Twin
const DIAGNOSTICS_ID = "diagnostics"; // S7 System Health

/**
 * ADDITIONAL UTILITY SCREENS.
 *
 * Retained in full. They are not replacements for any canonical screen, and they are left
 * unnumbered so the S1..S7 structure stays unambiguous.
 */
/** P8 — dumper-operator view (root CLAUDE.md §12). Not the control-room dashboard. */
export const OPERATOR_ID = "operator";
const BOTTLENECK_ID = "bottleneck";
const REPLAY_ID = "replay";
/** Phase 10 — Failure Injection / Demo Lab. Simulation / Test only. */
export const DEMO_LAB_ID = "demo-lab";

/**
 * Canonical screens not yet built. Declared so the shell never implies they exist.
 * Empty since Phase 7 built S6; the mechanism stays for whatever is declared next.
 */
export const PENDING_SCREENS: Record<string, { title: string; detail: string }> = {};

/**
 * A canonical screen that is declared but not yet built.
 *
 * Says so plainly rather than rendering an empty dashboard. An empty safety panel and a
 * safe one look identical, which is the substitution this HMI exists to avoid. Exported so
 * it is covered by the real code path rather than a reconstruction of it.
 */
export function PendingScreen({ screenId }: { screenId: string }) {
  const pending = PENDING_SCREENS[screenId];
  if (!pending) return null;
  return (
    <section className="hmi-screen" aria-label={pending.title}>
      <Panel title={pending.title}>
        <EmptyState headline="NOT BUILT YET" detail={pending.detail} />
      </Panel>
    </section>
  );
}

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

      {/* Canonical SIH screens, in order. */}
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
          S2 Vehicle Detail
          {selectedVehicleId ? ` · ${selectedVehicleId}` : ""}
        </button>
        <button
          type="button"
          aria-current={screenId === SAFETY_ID ? "page" : undefined}
          onClick={() => setScreenId(SAFETY_ID)}
        >
          S3 Safety / Environment
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
          S5 Alerts
        </button>
        <button
          type="button"
          aria-current={screenId === TWIN_ID ? "page" : undefined}
          onClick={() => setScreenId(TWIN_ID)}
        >
          S6 Digital Twin
        </button>
        <button
          type="button"
          aria-current={screenId === DIAGNOSTICS_ID ? "page" : undefined}
          onClick={() => setScreenId(DIAGNOSTICS_ID)}
        >
          S7 System Health
        </button>
      </nav>

      {/* Additional screens. Unnumbered on purpose: they do not replace any canonical
          screen, and numbering them would blur the S1-S7 structure. */}
      <nav className="hmi-nav hmi-nav-secondary" aria-label="Additional screens">
        <span className="hmi-nav-group-label">Additional</span>
        <button
          type="button"
          aria-current={screenId === OPERATOR_ID ? "page" : undefined}
          onClick={() => setScreenId(OPERATOR_ID)}
        >
          Operator
        </button>
        <button
          type="button"
          aria-current={screenId === BOTTLENECK_ID ? "page" : undefined}
          onClick={() => setScreenId(BOTTLENECK_ID)}
        >
          Bottleneck
        </button>
        <button
          type="button"
          aria-current={screenId === REPLAY_ID ? "page" : undefined}
          onClick={() => setScreenId(REPLAY_ID)}
        >
          Replay
        </button>
        <button
          type="button"
          className="hmi-nav-demo-lab"
          aria-current={screenId === DEMO_LAB_ID ? "page" : undefined}
          onClick={() => setScreenId(DEMO_LAB_ID)}
        >
          ⚠ Demo Lab
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

        {PENDING_SCREENS[screenId] ? (
          <PendingScreen screenId={screenId} />
        ) : screenId === VEHICLE_ID ? (
          <VehicleDetail vehicleId={selectedVehicleId} onBack={() => setScreenId(OVERVIEW_ID)} />
        ) : screenId === SAFETY_ID ? (
          <SafetyEnvironment vehicleId={selectedVehicleId} />
        ) : screenId === TWIN_ID ? (
          <DigitalTwin vehicleId={selectedVehicleId} />
        ) : screenId === OPERATOR_ID ? (
          <OperatorView vehicleId={selectedVehicleId} />
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
        ) : screenId === DEMO_LAB_ID ? (
          <FailureInjectionLab />
        ) : (
          <OperationsOverview onSelectVehicle={openVehicle} />
        )}
      </main>
    </div>
  );
}
