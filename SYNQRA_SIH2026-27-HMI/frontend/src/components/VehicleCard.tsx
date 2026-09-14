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
import { communicationText, provenanceLabel, vehicleProvenanceLabel } from "../state/dataStatus";
import type { FreshnessView } from "../state/freshness";
import { riskToken } from "../theme/statusTokens";
import { backendLink, LINK_STATE_GLYPH, v2iLink, v2vLink } from "../vehicle/communication";
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
  providerMode,
  connectionStatus,
}: {
  vehicle: VehicleState;
  safety: SafetyState | undefined;
  freshness: FreshnessView;
  /** Opens S2 for this vehicle. Omitted where the card is not a navigation target. */
  onSelect?: (vehicleId: string) => void;
  /**
   * The provider mode (LIVE / MOCK / REPLAY), for the V2I line only. V2I has no physical
   * endpoint, so the line says UNAVAILABLE in every mode and names SIMULATED / REPLAY.
   */
  providerMode?: string;
  /** This browser's feed status, carried into the backend line's reason. */
  connectionStatus?: string;
}) {
  const speed = speedView(safety, vehicle);
  const backend = backendLink(vehicle, connectionStatus ?? "UNKNOWN");
  const v2v = v2vLink(vehicle);
  const v2i = v2iLink(providerMode ?? "LIVE");
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
            {/* HMI-DATA-01: the displayed value is the Twin's canonical speed_mps
                (speedContract). The violation marker below is still judged on the pair
                the solver evaluated; if the two disagree, that is stated, not hidden. */}
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

      {speed?.actual.disagreesWithEvaluated && speed.actual.evaluatedMps !== null ? (
        <div className="faint">
          SAFETY EVALUATED AT {fmt(kmh(speed.actual.evaluatedMps))} km/h
        </div>
      ) : null}
      {speed?.safeSpeedUnavailable ? (
        <div className="faint">No safe speed supplied — speeds cannot be compared.</div>
      ) : null}

      <div className="vehicle-meta">
        {safety ? (
          <>
            {safety.riskLevel ? (
              <StatusBadge token={riskToken(safety.riskLevel)} prefix="RISK" />
            ) : (
              <span>RISK UNAVAILABLE</span>
            )}
            <span>
              CONSTRAINT {safety.activeConstraint ? readable(safety.activeConstraint) : "UNAVAILABLE"}
            </span>
            {safety.provenance?.v_safe_mps ? (
              <span className="faint">SAFETY SOURCE {provenanceLabel(safety.provenance.v_safe_mps)}</span>
            ) : null}
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

      {/*
        HMI-COMMS-01 — three links, three answers. Backend telemetry arriving over Wi-Fi is
        not V2V; V2V is a LoRa frame received by the other truck; V2I has no endpoint.
        Each radio metric is printed under its own radio's label.
      */}
      <div className="vehicle-meta" data-comms-links>
        <span className="faint">
          BACKEND {LINK_STATE_GLYPH[backend.state]} {backend.state}
          {backend.metrics[0]?.available
            ? ` · WI-FI RSSI ${backend.metrics[0].value} dBm`
            : ""}
        </span>
        <span className="faint">
          V2V {LINK_STATE_GLYPH[v2v.state]} {v2v.state}
          {v2v.peerId ? ` · PEER ${v2v.peerId}` : ""}
          {v2v.metrics[0]?.available ? ` · ${v2v.metrics[0].label} ${v2v.metrics[0].value} dBm` : ""}
          {v2v.metrics[1]?.available ? ` · ${v2v.metrics[1].label} ${v2v.metrics[1].value} dB` : ""}
          {v2v.state === "STALE" && v2v.ageS != null ? ` · ${v2v.ageS.toFixed(0)} s ago` : ""}
        </span>
        <span className="faint">
          V2I {LINK_STATE_GLYPH[v2i.state]} {v2i.state}
          {v2i.bearer.includes("(") ? ` ${v2i.bearer.slice(v2i.bearer.indexOf("("))}` : ""}
        </span>
      </div>
    </article>
  );
}
