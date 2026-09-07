/**
 * Vehicle card — M4. SAFETY-CRITICAL PRESENTATION.
 *
 * Governed by `.claude/skills/safety-visualization/SKILL.md`. Four rules hold this
 * component together; breaking any of them is a safety defect, not a styling nit.
 *
 *   1. **Actual and safe speed appear together, both labelled, both with units.** A safe
 *      speed on another screen from the actual speed answers nothing.
 *   2. **The violation is stated in TEXT.** `OVER SAFE SPEED` is rendered as words. The
 *      red border is an enhancement; strip every colour and the violation still reads.
 *   3. **`v_safe` is SUPPLIED.** Never computed, never buffered, never clamped, never
 *      rounded in a direction that changes meaning. When absent, the pair is incomparable
 *      and NO violation marker may appear — there is nothing to violate.
 *   4. **`h_safe` units are UNRESOLVED (AMB-001).** Current headway and `h_safe` are
 *      shown as bare numbers and are NOT compared. Where Task 2 supplies
 *      `headwayViolation`, that supplied flag is what is displayed.
 */

import type { SafetyState, VehicleState } from "../contracts/domain";
import { fmt, HSAFE_UNIT_NOTE, headwayView, kmh, speedView } from "../state/derive";
import { communicationText, vehicleProvenanceLabel } from "../state/dataStatus";
import type { FreshnessView } from "../state/freshness";
import { riskToken } from "../theme/statusTokens";
import { FreshnessIndicator, StatusBadge } from "./primitives";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

export function VehicleCard({
  vehicle,
  safety,
  freshness,
  onSelect,
}: {
  vehicle: VehicleState;
  safety: SafetyState | undefined;
  freshness: FreshnessView;
  /** Opens S2 for this vehicle. Omitted where the card is not a navigation target. */
  onSelect?: (vehicleId: string) => void;
}) {
  const speed = speedView(safety);
  const headway = headwayView(safety);
  const hasPosition = vehicle.position.x !== null && vehicle.position.y !== null;

  return (
    <article
      className={`vehicle${speed?.violation ? " violation" : ""}`}
      aria-label={`Vehicle ${vehicle.vehicleId}`}
    >
      {/* FR-002: selecting a vehicle navigates to S2. A real button, so it is keyboard
          reachable and announced; the card itself is not a click target. */}
      {onSelect ? (
        <button
          type="button"
          className="vehicle-id link-button"
          onClick={() => onSelect(vehicle.vehicleId)}
        >
          {vehicle.vehicleId} →
        </button>
      ) : (
        <div className="vehicle-id">{vehicle.vehicleId}</div>
      )}

      <dl className="speed-pair">
        <div className="speed-cell">
          <dt>Actual speed</dt>
          <dd>
            {/* The safety record's actual speed is the one compared against v_safe, so it
                is the one displayed when supplied. Falling back to the vehicle telemetry
                speed keeps the card honest when no safety record arrived. */}
            {fmt(speed ? speed.actualKmh : kmh(vehicle.speedMps))}{" "}
            <span className="metric-unit">km/h</span>
          </dd>
        </div>
        <div className="speed-cell">
          <dt>Safe speed</dt>
          <dd>
            {speed === null || speed.safeKmh === null ? (
              <span className="dim">UNAVAILABLE</span>
            ) : (
              <>
                {fmt(speed.safeKmh)} <span className="metric-unit">km/h</span>
              </>
            )}
          </dd>
        </div>
      </dl>

      {/* Text, not colour. This is the assertion the safety test looks for. */}
      {speed?.violationText ? (
        <strong className="violation-marker">▲ {speed.violationText}</strong>
      ) : null}

      {speed?.safeSpeedUnavailable ? (
        <div className="faint">No safe speed supplied — speeds cannot be compared.</div>
      ) : null}

      <div className="vehicle-meta">
        {safety ? (
          <>
            <StatusBadge token={riskToken(safety.riskLevel)} prefix="RISK" />
            <span>CONSTRAINT {readable(safety.activeConstraint)}</span>
          </>
        ) : (
          <span>SAFETY STATE UNAVAILABLE</span>
        )}
        <span>MODE {readable(vehicle.mode)}</span>
        {vehicle.vehicleKind ? <span>{readable(vehicle.vehicleKind)}</span> : null}
      </div>

      {headway ? (
        <div className="vehicle-meta">
          <span>
            HEADWAY {fmt(headway.current)} · H_SAFE {fmt(headway.hSafe)}{" "}
            <span className="unresolved">({HSAFE_UNIT_NOTE})</span>
          </span>
          {headway.leadVehicleId ? <span>LEAD {headway.leadVehicleId}</span> : null}
          {headway.suppliedViolation === true ? (
            <strong className="violation-marker">▲ HEADWAY VIOLATION</strong>
          ) : null}
        </div>
      ) : null}

      <div className="vehicle-meta">
        {hasPosition ? (
          <span className="faint">SEGMENT {vehicle.position.segmentId ?? "—"}</span>
        ) : (
          <span className="faint">POSITION UNAVAILABLE</span>
        )}
        <FreshnessIndicator view={freshness} />
      </div>

      {/*
        PHASE 8 §15 — provenance and communication, as separate facts from each other and
        from freshness. Until Phase 8 the fleet overview showed neither, so a SIMULATED
        speed was indistinguishable from a measured one on the most-used screen in the HMI.
      */}
      <div className="vehicle-meta">
        <span className="faint">SOURCE {vehicleProvenanceLabel(vehicle)}</span>
        <span className="faint">COMMS {communicationText(vehicle)}</span>
      </div>
    </article>
  );
}
