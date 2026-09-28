/**
 * S3 Safety / Environment — Phase 6.
 *
 * ==========================================================================
 *  DISPLAY ONLY. NO SAFETY COMPUTATION HAPPENS ON THIS SCREEN.
 *
 *  No v_safe is solved, no stopping distance is calculated, no limiter is inferred and
 *  no safety state is classified from a threshold. Every value shown was SUPPLIED; every
 *  value not supplied says UNAVAILABLE.
 *
 *  AUDITED against the running backend: the live provider supplies vehicle telemetry
 *  (speed, rpm, communication state) with full provenance and freshness, and supplies
 *  NO SafetyState and NO RoadState - `twin_projection` already exposes `environment` and
 *  it returns `{}`. The MOCK and REPLAY providers do supply both, so this same screen
 *  shows real values there. Nothing branches on the provider; it reads the slices.
 * ==========================================================================
 */

import { useMemo, useState } from "react";
import { EmptyState, FreshnessIndicator, MetricCard, Panel } from "../components/primitives";
import type { VehicleId } from "../contracts/primitives";
import { communicationText } from "../state/dataStatus";
import { viewFreshness } from "../state/freshness";
import {
  activeConstraintText,
  envelopeView,
  environmentReadouts,
  operatingReadouts,
  provenanceLabel,
  type Readout,
  safetyStateText,
  stoppingDistanceText,
  UNAVAILABLE,
} from "../state/safetyEnvironment";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";

/** One readout row. An unavailable value is dimmed, never blank and never zero. */
function ReadoutRow({ readout }: { readout: Readout }) {
  return (
    <div className="field">
      <dt>{readout.label}</dt>
      <dd className={readout.available ? undefined : "dim"}>
        {readout.value}
        {readout.available && readout.unit ? (
          <span className="metric-unit"> {readout.unit}</span>
        ) : null}
      </dd>
      {readout.provenance ? <div className="faint">{readout.provenance}</div> : null}
    </div>
  );
}

export function SafetyEnvironment({ vehicleId }: { vehicleId?: VehicleId | null }) {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  /**
   * Selection is UI state only, seeded from the shell's selected vehicle so S3 stays
   * consistent with S2 and S4. The vehicle itself is read from the shared store on every
   * render - this holds an id, never a copy of a vehicle.
   */
  const [picked, setPicked] = useState<VehicleId | null>(null);
  const vehicleIds = useMemo(() => Object.keys(state.vehicles).sort(), [state.vehicles]);
  const activeId = picked ?? vehicleId ?? vehicleIds[0] ?? null;

  const vehicle = activeId ? state.vehicles[activeId] : undefined;
  const safety = activeId ? state.safety[activeId] : undefined;

  // The road a vehicle is on, only when the vehicle itself said which one.
  const segmentId = vehicle?.position?.segmentId ?? vehicle?.routeId ?? null;
  const road = segmentId ? state.road[segmentId] : undefined;

  // Commanded speed is SUPPLIED by the command path, never inferred from anything here.
  const command = useMemo(
    () =>
      activeId ? Object.values(state.dispatch).find((c) => c?.vehicleId === activeId) : undefined,
    [state.dispatch, activeId],
  );

  const freshness = viewFreshness(vehicle?.timestamp, config, nowMs);
  const operating = operatingReadouts(vehicle, safety, command?.targetSpeed ?? null);
  const environment = environmentReadouts(road);
  const envelope = envelopeView(safety);
  const anyEnvironment = environment.some((r) => r.available);

  if (!activeId) {
    return (
      <Panel title="Safety / Environment">
        <EmptyState
          headline="NO VEHICLE SUPPLIED"
          detail="The data layer has supplied no vehicle state, so no safety or environment data can be shown for one."
        />
      </Panel>
    );
  }

  return (
    <>
      {/* A — HEADER: which vehicle, how fresh, and where the data came from. */}
      <Panel title="Safety / Environment" note="display only — no value is computed here">
        <header className="op-header">
          <div className="op-vehicle">{activeId}</div>
          {vehicleIds.length > 1 ? (
            <label className="op-picker">
              <span className="op-picker-label">VEHICLE</span>
              <select
                value={activeId}
                aria-label="Select vehicle"
                onChange={(event) => setPicked(event.target.value as VehicleId)}
              >
                {vehicleIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </header>

        <dl className="fields">
          <div className="field">
            <dt>Mode</dt>
            {/*
              Provenance of the telemetry itself. SIMULATION and PHYSICAL must never look
              alike, and neither is inferred from connectivity.
            */}
            <dd>{provenanceLabel(vehicle)}</dd>
          </div>
          <div className="field">
            <dt>Communication</dt>
            {/* SUPPLIED link state. Independent of telemetry freshness (Phase 8 §15). */}
            <dd>{communicationText(vehicle)}</dd>
          </div>
          <div className="field">
            <dt>Telemetry freshness</dt>
            <dd>
              <FreshnessIndicator view={freshness} />
            </dd>
          </div>
        </dl>
      </Panel>

      {/* B — CURRENT OPERATING STATE */}
      <Panel title="Current operating state" note="supplied values only">
        <dl className="fields">
          {operating.map((row) => (
            <ReadoutRow key={row.label} readout={row} />
          ))}
        </dl>
      </Panel>

      {/* C — ENVIRONMENT */}
      <Panel title="Environment" note="supplied RoadState only">
        <dl className="fields">
          {environment.map((row) => (
            <ReadoutRow key={row.label} readout={row} />
          ))}
        </dl>
        {anyEnvironment ? null : (
          <p className="faint">
            No RoadState has been supplied for this vehicle, so no environment value is shown.
            Simulator scenarios in <span className="mono">game_ui</span> run in a separate process
            and are not evidence about this screen&apos;s data.
          </p>
        )}
      </Panel>

      {/* D — SAFETY ENVELOPE */}
      <Panel title="Safety envelope" note="supplied by the safety layer, never computed here">
        {envelope.anyAvailable ? (
          <dl className="fields">
            {envelope.readouts.map((row) => (
              <ReadoutRow key={row.label} readout={row} />
            ))}
          </dl>
        ) : (
          <EmptyState
            headline="DETAILED LIMITS UNAVAILABLE"
            detail={envelope.unavailableReason ?? ""}
          />
        )}
        <div className="metrics">
          <MetricCard
            label="Stopping distance"
            value={stoppingDistanceText()}
            footer="not supplied by any message; never recomputed in the HMI"
          />
        </div>
      </Panel>

      {/* E — WHY THE SPEED IS LIMITED. Only when a supplier said so. */}
      <Panel title="Safety explanation" note="verbatim from the supplier">
        <dl className="fields">
          <div className="field">
            <dt>Active constraint</dt>
            <dd className={activeConstraintText(safety) === UNAVAILABLE ? "dim" : undefined}>
              {activeConstraintText(safety)}
            </dd>
          </div>
          <div className="field">
            <dt>Safety state</dt>
            <dd className={safetyStateText(safety) === UNAVAILABLE ? "dim" : undefined}>
              {safetyStateText(safety)}
            </dd>
            <div className="faint">Supplied risk level. No threshold is applied in the HMI.</div>
          </div>
        </dl>
        {activeConstraintText(safety) === UNAVAILABLE ? (
          <p className="faint">
            SAFETY REASON UNAVAILABLE — no supplier has stated why speed is limited. A reason is
            never inferred from the environment or from the current speed.
          </p>
        ) : null}
      </Panel>

      {/* F — PROVENANCE AND FRESHNESS */}
      <Panel title="Provenance and freshness" note="NFR-003 · NFR-007">
        <dl className="fields">
          <div className="field">
            <dt>Telemetry source</dt>
            <dd>{provenanceLabel(vehicle)}</dd>
          </div>
          <div className="field">
            <dt>Vehicle timestamp</dt>
            <dd>{vehicle?.timestamp ?? UNAVAILABLE}</dd>
          </div>
          <div className="field">
            <dt>Safety data</dt>
            <dd>{safety ? "SUPPLIED" : UNAVAILABLE}</dd>
          </div>
          <div className="field">
            <dt>Road / environment data</dt>
            <dd>{road ? "SUPPLIED" : UNAVAILABLE}</dd>
          </div>
          <div className="field">
            <dt>Data connection</dt>
            <dd>{state.connection.status}</dd>
          </div>
        </dl>
      </Panel>
    </>
  );
}
