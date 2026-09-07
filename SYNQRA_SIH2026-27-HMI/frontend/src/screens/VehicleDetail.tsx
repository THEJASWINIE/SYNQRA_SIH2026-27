/**
 * S2 Vehicle Detail — M5.
 *
 * Satisfies HMI-FR-003 (vehicle state), FR-004 (safety envelope), FR-005 (headway),
 * FR-011 (visibility for the occupied segment), FR-012 (road condition), FR-013
 * (per-vehicle communication) and S2-a (grade).
 *
 * ==========================================================================
 *  EVERY VALUE ON THIS SCREEN IS SUPPLIED.
 *
 *  Nothing here computes v_safe, h_safe, stopping distance, friction, a route,
 *  a trajectory or any other Task 2 output. The screen performs exactly the
 *  derivations on the closed list: data age, display comparison and ordering,
 *  unit formatting, and the M4D-F display-only map coordinate.
 *
 *  No control, no command, no acknowledgement, no actuation. The screen is
 *  read-only by construction — it renders no form and no submit path.
 * ==========================================================================
 *
 * Vehicle selection is UI state held by the shell, per the hmi-frontend skill: operational
 * data lives in the store, and "selected vehicle" is not operational data. This screen
 * reads the vehicle out of `AppState` on every render, so a vehicle that disappears from
 * supplied state is reported as gone rather than rendered from a stale copy.
 */

import { communicationText, vehicleProvenanceLabel } from "../state/dataStatus";
import {
  EmptyState,
  FreshnessIndicator,
  MetricCard,
  Panel,
  StatusBadge,
} from "../components/primitives";
import type { Health, RoadState, SafetyState, VehicleState } from "../contracts/domain";
import {
  fmt,
  HSAFE_UNIT_NOTE,
  headwayView,
  kmh,
  POSITION_UNAVAILABLE_REASON_TEXT,
  resolvePosition,
  speedView,
} from "../state/derive";
import { type FreshnessView, viewFreshness } from "../state/freshness";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { providerStatusToken, riskToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

/** A labelled value. `value` is already formatted; absent values arrive as an explicit token. */
function Field({
  label,
  value,
  unit,
  note,
}: {
  label: string;
  value: string;
  unit?: string | undefined;
  note?: string | undefined;
}) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>
        {value}
        {unit ? <span className="metric-unit">{unit}</span> : null}
      </dd>
      {note ? <div className="faint">{note}</div> : null}
    </div>
  );
}

const UNAVAILABLE = "UNAVAILABLE";

export function VehicleDetail({
  vehicleId,
  onBack,
}: {
  vehicleId: string | null;
  onBack: () => void;
}) {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();
  const fresh = (timestamp: string | null | undefined): FreshnessView =>
    viewFreshness(timestamp, config, nowMs);

  const back = (
    <button type="button" className="link-button" onClick={onBack}>
      ← Back to Operations Overview
    </button>
  );

  if (vehicleId === null) {
    return (
      <Panel title="Vehicle detail" note="S2">
        {back}
        <EmptyState
          headline="NO VEHICLE SELECTED"
          detail="Choose a vehicle from the fleet on Operations Overview."
        />
      </Panel>
    );
  }

  const vehicle: VehicleState | undefined = state.vehicles[vehicleId];

  if (!vehicle) {
    // Covers both an id that never existed and a vehicle removed from supplied state
    // after selection. Either way the honest statement is the same: it is not in the
    // current state, and nothing is rendered from a remembered copy.
    return (
      <Panel title="Vehicle detail" note={`S2 · ${vehicleId}`}>
        {back}
        <EmptyState
          headline="VEHICLE NOT IN CURRENT STATE"
          detail={`No vehicle "${vehicleId}" is present in the data currently supplied. It may never have existed, or it may have been removed since selection. No remembered values are shown.`}
        />
      </Panel>
    );
  }

  const safety: SafetyState | undefined = state.safety[vehicleId];
  const speed = speedView(safety);
  const headway = headwayView(safety);
  const segmentId = vehicle.position.segmentId;
  const road: RoadState | undefined = segmentId ? state.road[segmentId] : undefined;
  const position = resolvePosition(vehicle, state.topology);
  const vehicleFreshness = fresh(vehicle.timestamp);
  const safetyFreshness = safety ? fresh(safety.timestamp) : null;

  /** FR-013: supplied per-link health rows. Link classification is never invented here. */
  const links: Health[] = state.health?.components ?? [];

  return (
    <>
      <Panel
        title={`Vehicle ${vehicle.vehicleId}`}
        note={
          <>
            S2 · {readable(vehicle.mode)}
            {vehicle.vehicleKind ? ` · ${readable(vehicle.vehicleKind)}` : ""}
          </>
        }
      >
        {back}

        {/* FR-004 — the safety envelope, first and largest. */}
        <div className="envelope">
          <div className="envelope-cell">
            <dt>Actual speed</dt>
            <dd className="envelope-value">
              {speed ? fmt(speed.actualKmh) : fmt(kmh(vehicle.speedMps))}
              <span className="metric-unit">km/h</span>
            </dd>
          </div>
          <div className="envelope-cell">
            <dt>Safe speed (supplied)</dt>
            <dd className="envelope-value">
              {speed && speed.safeKmh !== null ? (
                <>
                  {fmt(speed.safeKmh)}
                  <span className="metric-unit">km/h</span>
                </>
              ) : (
                <span className="dim">{UNAVAILABLE}</span>
              )}
            </dd>
          </div>
          <div className="envelope-cell">
            <dt>Status</dt>
            <dd className="envelope-value">
              {speed?.violation ? (
                <strong className="violation-marker">▲ OVER SAFE SPEED</strong>
              ) : speed?.safeSpeedUnavailable ? (
                <span className="dim">NOT COMPARABLE</span>
              ) : speed ? (
                <span>WITHIN SAFE SPEED</span>
              ) : (
                <span className="dim">{UNAVAILABLE}</span>
              )}
            </dd>
          </div>
          <div className="envelope-cell">
            <dt>Active constraint</dt>
            <dd className="envelope-value">
              {safety ? (
                readable(safety.activeConstraint)
              ) : (
                <span className="dim">{UNAVAILABLE}</span>
              )}
            </dd>
          </div>
        </div>

        {speed?.safeSpeedUnavailable ? (
          <p className="faint">
            No safe speed was supplied for this vehicle, so actual and safe speed cannot be
            compared. No comparison result is manufactured.
          </p>
        ) : null}

        {!safety ? (
          <EmptyState
            headline="NO SUPPLIED SAFETY DATA"
            detail="No SafetyState has been supplied for this vehicle. Risk, constraint, headway and safe speed are unavailable — none is derived locally."
          />
        ) : null}
      </Panel>

      <div className="grid-2">
        {/* FR-003 — vehicle state fields. */}
        <Panel title="Vehicle state" note="FR-003 · all values supplied">
          <dl className="fields">
            <Field label="Vehicle id" value={vehicle.vehicleId} />
            <Field label="Segment" value={segmentId ?? UNAVAILABLE} />
            <Field
              label="Map position"
              value={
                position.ok
                  ? `${position.x.toFixed(1)}, ${position.y.toFixed(1)}`
                  : "POSITION UNAVAILABLE"
              }
              note={
                position.ok
                  ? position.source === "SUPPLIED"
                    ? "supplied coordinates"
                    : "derived from supplied segment geometry (M4D-F)"
                  : POSITION_UNAVAILABLE_REASON_TEXT[position.reason]
              }
            />
            <Field
              label="Offset along segment"
              value={fmt(vehicle.position.offsetM, 1)}
              unit={vehicle.position.offsetM === null ? undefined : "m"}
            />
            <Field label="Speed" value={fmt(kmh(vehicle.speedMps))} unit="km/h" />
            <Field label="Acceleration" value={fmt(vehicle.accelMps2, 2)} unit="m/s²" />
            {/* S2-a — grade for the vehicle's segment. Supplied, shown verbatim. */}
            <Field
              label="Grade (vehicle)"
              value={fmt(vehicle.gradeRad, 3)}
              unit="rad"
              note="supplied — S2-a"
            />
            <Field
              label="Risk"
              value={safety ? safety.riskLevel : UNAVAILABLE}
              note={safety ? "supplied — never re-banded" : undefined}
            />
            {/* FR-003 AC2 — friction is never rendered bare. */}
            <Field
              label="Friction estimate"
              value={
                // P6.1: the whole estimate may be absent (the canonical Twin has no
                // friction for a hardware-only vehicle), as may its value. Both read
                // UNAVAILABLE - never a fabricated number.
                vehicle.frictionEst == null || vehicle.frictionEst.value === null
                  ? UNAVAILABLE
                  : `${fmt(vehicle.frictionEst.value, 2)} ± ${
                      vehicle.frictionEst.sigma === null
                        ? "σ not supplied"
                        : fmt(vehicle.frictionEst.sigma, 2)
                    }`
              }
              note="supplied estimate with its uncertainty"
            />
            <Field
              label="Comm confidence"
              value={fmt(vehicle.commConfidence, 2)}
              note="supplied 0..1 — not classified; no threshold is specified"
            />
            {/*
              PHASE 8 §16 — source and communication state, kept apart from each other and
              from freshness. The same three facts read identically here, on S1, S3, S4 and
              S6, because all five ask `dataStatus` rather than re-deciding locally.
            */}
            <Field
              label="Telemetry source"
              value={vehicleProvenanceLabel(vehicle)}
              note="supplied provenance — never inferred from connectivity"
            />
            <Field
              label="Communication"
              value={communicationText(vehicle)}
              note="supplied link state — independent of telemetry freshness"
            />
            <Field label="Route" value={vehicle.routeId ?? UNAVAILABLE} />
          </dl>
          <div className="row-between">
            {safety ? <StatusBadge token={riskToken(safety.riskLevel)} prefix="RISK" /> : null}
            <FreshnessIndicator view={vehicleFreshness} />
          </div>
        </Panel>

        {/* FR-005 — headway. AMB-001 governs every line of this panel. */}
        <Panel title="Headway" note="FR-005 · AMB-001 unresolved">
          {headway === null ? (
            <EmptyState
              headline="HEADWAY DATA UNAVAILABLE"
              detail="No SafetyState has been supplied for this vehicle."
            />
          ) : (
            <>
              <dl className="fields">
                <Field label="Ego vehicle" value={vehicle.vehicleId} />
                <Field label="Lead vehicle" value={headway.leadVehicleId ?? UNAVAILABLE} />
                <Field
                  label="Current headway"
                  value={fmt(headway.current)}
                  note={HSAFE_UNIT_NOTE}
                />
                <Field label="Required H_safe" value={fmt(headway.hSafe)} note={HSAFE_UNIT_NOTE} />
              </dl>

              {headway.suppliedViolation === true ? (
                <strong className="violation-marker">▲ HEADWAY VIOLATION (supplied)</strong>
              ) : headway.suppliedViolation === false ? (
                <p>NO HEADWAY VIOLATION (supplied)</p>
              ) : (
                <p className="dim">HEADWAY VIOLATION NOT SUPPLIED</p>
              )}

              <p className="unresolved">
                AMB-001 is unresolved: the specification does not state whether H_safe is a distance
                or a time. These two values are therefore shown without an assumed unit and are NOT
                compared numerically. Only a violation flag supplied by Task 2 is displayed.
              </p>
            </>
          )}
        </Panel>
      </div>

      <div className="grid-2">
        {/* FR-011 + FR-012 — the occupied segment. */}
        <Panel title="Occupied segment" note="FR-011 · FR-012 · supplied">
          {!segmentId ? (
            <EmptyState
              headline="SEGMENT UNAVAILABLE"
              detail="The supplied vehicle position names no segment."
            />
          ) : !road ? (
            <EmptyState
              headline="NO ROAD STATE SUPPLIED"
              detail={`No RoadState has been supplied for segment ${segmentId}.`}
            />
          ) : (
            <>
              <div className="metrics">
                <MetricCard
                  label="Visibility"
                  value={fmt(road.visibility.value, 0)}
                  unit="m"
                  footer={
                    road.visibility.sigma === null
                      ? "σ not supplied"
                      : `± ${fmt(road.visibility.sigma, 1)} m`
                  }
                />
                <MetricCard
                  label="Friction"
                  value={fmt(road.friction.value, 2)}
                  footer={
                    road.friction.sigma === null
                      ? "σ not supplied"
                      : `± ${fmt(road.friction.sigma, 2)}`
                  }
                />
                <MetricCard label="Grade" value={fmt(road.grade, 3)} unit="rad" />
                <MetricCard
                  label="Surface"
                  value={road.surfaceState ?? UNAVAILABLE}
                  footer="supplied"
                />
                {road.roughness === null ? null : (
                  <MetricCard label="Roughness" value={fmt(road.roughness, 2)} footer="supplied" />
                )}
                <MetricCard label="Queue" value={fmt(road.queue, 0)} unit="veh" />
              </div>
              <div className="row-between">
                <span className="faint">segment {road.segmentId}</span>
                <FreshnessIndicator view={fresh(road.timestamp)} />
              </div>
              <p className="faint">
                Forecast visibility is supplied per segment and is presented on S3/S5. No fog
                modelling or extrapolation is performed here (FR-011 AC4).
              </p>
            </>
          )}
        </Panel>

        {/* FR-013 — per-vehicle communication, plus supplied link rows. */}
        <Panel title="Communication" note="FR-013 · supplied">
          <dl className="fields">
            <Field
              label="Comm confidence (this vehicle)"
              value={fmt(vehicle.commConfidence, 2)}
              note="supplied 0..1"
            />
            <Field
              label="Data connection"
              value={providerStatusToken(state.connection.status).label}
              note={state.connection.error ?? undefined}
            />
            <Field
              label="Connectivity (supplied)"
              value={state.health?.connectivity ?? UNAVAILABLE}
            />
          </dl>

          {links.length === 0 ? (
            <EmptyState
              headline="NO LINK HEALTH SUPPLIED"
              detail="SystemHealth has supplied no component rows."
            />
          ) : (
            <dl className="fields">
              {links.map((link) => (
                <Field
                  key={link.componentId}
                  label={`${link.linkKind ?? "LINK"} · ${link.componentId}`}
                  value={link.state}
                  note={[
                    link.latencyMs === null ? null : `${fmt(link.latencyMs, 0)} ms`,
                    link.ageMs === null ? null : `age ${fmt(link.ageMs, 0)} ms (supplied)`,
                    link.errorCode,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                />
              ))}
            </dl>
          )}

          <p className="faint">
            Communication state is shown from supplied values. It is not classified into a degraded
            band here: the specification states no confidence threshold, and PAD-G forbids inventing
            one.
          </p>
        </Panel>
      </div>

      {/* Provenance and freshness. */}
      <Panel title="Provenance and freshness" note="NFR-003 · NFR-007">
        <dl className="fields">
          <Field label="Vehicle timestamp (source)" value={vehicle.timestamp} />
          <Field
            label="Safety timestamp (source)"
            value={safety ? safety.timestamp : UNAVAILABLE}
          />
          <Field label="Segment timestamp (source)" value={road ? road.timestamp : UNAVAILABLE} />
          <Field label="Provider" value={state.connection.provider} />
          <Field label="Scenario" value={state.connection.scenarioName ?? UNAVAILABLE} />
          <Field
            label="Last delivery received"
            value={state.connection.lastMessageAt ?? UNAVAILABLE}
            note="HMI receipt time, not a datum's age"
          />
        </dl>
        <div className="row-between">
          <span className="faint">Vehicle</span>
          <FreshnessIndicator view={vehicleFreshness} />
        </div>
        {safetyFreshness ? (
          <div className="row-between">
            <span className="faint">Safety</span>
            <FreshnessIndicator view={safetyFreshness} />
          </div>
        ) : null}
      </Panel>

      {/* S2-b — recorded honestly rather than fabricated. */}
      <Panel title="Recent trend" note="S2-b">
        <EmptyState
          headline="TREND DATA NOT SUPPLIED"
          detail="The data contract supplies no per-vehicle history series. A trend is not accumulated locally, because a locally built series is not supplied data and would age and diverge from the source. Recorded as a known limitation pending either a supplied vehicle history or the M9 replay timeline."
        />
      </Panel>
    </>
  );
}
