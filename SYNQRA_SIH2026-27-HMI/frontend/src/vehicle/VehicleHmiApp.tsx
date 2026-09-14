/**
 * Vehicle HMI standalone application — M4 / Task 1 HMI.
 *
 * Dedicated console for ONE vehicle (TRUCK_01 or TRUCK_02), fixed at build/entry-point time.
 *
 * ==========================================================================
 *  ONE BACKEND. ONE CANONICAL TWIN. THREE CLIENT VIEWS.
 *
 *  Control Room HMI (index.html)  ──┐
 *  TRUCK_01 HMI (truck01.html)    ──┼──> SAME CANONICAL BACKEND / DIGITAL TWIN
 *  TRUCK_02 HMI (truck02.html)    ──┘
 *
 *  Vehicle identity is passed as a fixed prop ("TRUCK_01" or "TRUCK_02") from the entry
 *  module (src/truck01.tsx or src/truck02.tsx). There is NO vehicle picker, NO runtime
 *  selector, NO query param switching, and NO localStorage switching.
 * ==========================================================================
 */

import { useEffect, useState } from "react";
import { fetchOperatorContext, type OperatorContext } from "../api/operatorClient";
import { BackendHealth } from "../components/BackendHealth";
import { StatusBadge } from "../components/primitives";
import { ProviderHost, useHmi } from "../state/ProviderHost";
import { displayedModeFor, MODE_SOURCE_TEXT } from "../state/systemMode";
import { useAppState } from "../state/useAppState";
import { providerStatusToken, systemModeToken } from "../theme/statusTokens";
import {
  AlertsEventsPanel,
  CommandPanel,
  CommunicationPanel,
  dataSourceLabel,
  OperatorBadge,
  PositionPanel,
  SafetyPanel,
  TelemetryPanel,
} from "./panels";
import { DriverScreen } from "./DriverScreen";
import { type ConfiguredVehicleId, vehicleConfig } from "./vehicleConfig";
import { projectVehicle } from "./vehicleProjection";

import "../theme/hmi.css";

function VehicleHmiContent({ vehicleId }: { vehicleId: ConfiguredVehicleId }) {
  const config = vehicleConfig(vehicleId);
  const state = useAppState();
  const { freshness, freshnessReason } = useHmi();

  const projection = projectVehicle(state, vehicleId);

  const [operator, setOperator] = useState<OperatorContext | null>(null);
  const [operatorProblem, setOperatorProblem] = useState<string | null>(null);

  useEffect(() => {
    let unmounted = false;

    const checkOperator = async () => {
      const result = await fetchOperatorContext();
      if (unmounted) return;
      if (result.kind === "ok") {
        setOperator(result.context);
        setOperatorProblem(null);
      } else {
        setOperator(null);
        setOperatorProblem(result.message);
      }
    };

    void checkOperator();
    const timer = setInterval(() => void checkOperator(), 5000);
    return () => {
      unmounted = true;
      clearInterval(timer);
    };
  }, []);

  const displayedMode = displayedModeFor(state);
  const mode = displayedMode.mode;

  return (
    <div className="hmi vehicle-hmi-standalone" data-vehicle-id={vehicleId}>
      <header className="op-header">
        <div className="op-header-left">
          <span className="op-brand-mark" aria-hidden="true">
            ⛰
          </span>
          <div>
            <div className="op-brand-title">FOG-ORCHESTRATOR 2.0</div>
            <div className="op-brand-sub">SYNQRA · AUTONOMOUS MINING</div>
          </div>
        </div>

        <div className="op-header-center">
          <div className="op-header-page-title">{config.displayName} OPERATOR HMI</div>
          <div className="op-header-page-sub">VEHICLE OPERATIONS</div>
        </div>

        <div className="op-header-right">
          {/* Honest per HMI Rule 3: this shows the actual provider, never LIVE for MOCK/REPLAY. */}
          <span
            className={`op-live-badge op-live-${state.connection.provider.toLowerCase()}`}
            data-provider={state.connection.provider}
          >
            {state.connection.provider === "REPLAY"
              ? "▶ REPLAY — NOT LIVE"
              : state.connection.provider === "MOCK"
                ? "● MOCK — NOT LIVE"
                : "● LIVE"}
          </span>
          <span className="op-header-clock faint mono">{state.clock.now.slice(0, 19).replace("T", " ")}</span>
          <span className="op-header-role faint">OPERATOR VIEW</span>
        </div>
      </header>

      <div className="op-status-strip">
        <dl className="hmi-header-slot">
          <dt>Vehicle Identity</dt>
          <dd>
            <span className="mono bold">{config.displayName}</span>
            <div className="faint">Fixed target · Port {config.devPort}</div>
          </dd>
        </dl>

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

        <dl className="hmi-header-slot">
          <dt>Operator session</dt>
          <dd>
            <OperatorBadge operator={operator} config={config} problem={operatorProblem} />
          </dd>
        </dl>

        <dl className="hmi-header-slot">
          <dt>Vehicle data source</dt>
          <dd>
            <span className="mono">{dataSourceLabel(projection)}</span>
          </dd>
        </dl>

        <dl>
          <BackendHealth />
        </dl>
      </div>

      <main className="hmi-main">
        {freshness === null ? (
          <div className="hmi-banner" role="status">
            <div className="hmi-banner-title">▲ FRESHNESS THRESHOLD NOT CONFIGURED</div>
            <p>
              Data age is still shown. Stale classification is <strong>not evaluated</strong> (AMB-014).
            </p>
            {freshnessReason ? <p className="faint">{freshnessReason}</p> : null}
          </div>
        ) : null}

        {/*
          The driver display (spec §8-§11): one dominant state, the very-high-priority
          values, no graphs. Everything else on this console is operator/technician
          detail and sits below it, collapsed by default.
        */}
        {/* The mine-site map now lives inside DriverScreen's own card grid. */}
        <DriverScreen projection={projection} config={config} />

        <details className="veh-details">
          <summary>Operator commands and technician detail</summary>

        <div className="grid-2">
          <SafetyPanel projection={projection} />
          <CommandPanel projection={projection} config={config} operator={operator} />
        </div>

        <div className="grid-2">
          <TelemetryPanel projection={projection} config={config} />
          <CommunicationPanel projection={projection} mode={state.connection.provider} />
        </div>

        <div className="grid-1">
          <PositionPanel projection={projection} config={config} mode={state.connection.provider} />
        </div>

        <div className="grid-1">
          <AlertsEventsPanel projection={projection} />
        </div>
        </details>
      </main>
    </div>
  );
}

export function VehicleHmiApp({ vehicleId }: { vehicleId: ConfiguredVehicleId }) {
  return (
    <ProviderHost>
      <VehicleHmiContent vehicleId={vehicleId} />
    </ProviderHost>
  );
}
