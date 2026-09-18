/**
 * Vehicle callout — the instrument label pinned to a machine in the 3D scene.
 *
 * ==========================================================================
 *  EVERY FIGURE ON THIS LABEL IS SUPPLIED. NOTHING HERE IS COMPUTED.
 *
 *  Speed, mode, freshness, risk and the V2V state come straight off the Mine-Cast
 *  projection, which took them from the canonical Twin. An absent value prints as
 *  UNAVAILABLE - never 0, never a reassuring default. The provenance stripe along the
 *  bottom edge is part of the silhouette on purpose: the data is pinned to the machine,
 *  and its truthfulness is pinned to the data.
 * ==========================================================================
 *
 * Pure DOM. Rendered through drei's `Html`, so it costs the GPU nothing and stays crisp
 * at any zoom - the SDF-text alternative lost the WebGL context on this hardware.
 */

import type { CSSProperties } from "react";

import { UNAVAILABLE_LABEL } from "../state/dataStatus";
import { LINK_STATE_GLYPH } from "../vehicle/communication";
import type { MineCastVehicle } from "./minecastProjection";
import type { SpatialPosition } from "./spatialPosition";

function speedText(mps: number | null): string {
  return mps === null || !Number.isFinite(mps) ? UNAVAILABLE_LABEL : `${mps.toFixed(1)} m/s`;
}

/** Status-dot tone from the vehicle's own availability. Text carries the meaning too. */
function availabilityTone(availability: MineCastVehicle["availability"]): string {
  switch (availability) {
    case "AVAILABLE":
      return "ok";
    case "DEGRADED":
      return "warn";
    case "UNAVAILABLE":
      return "crit";
  }
}

function riskText(vehicle: MineCastVehicle): string {
  if (vehicle.safety.unavailable) return `SAFETY ${UNAVAILABLE_LABEL}`;
  return `RISK ${vehicle.safety.riskLevel ?? UNAVAILABLE_LABEL}`;
}

export function VehicleCallout({
  vehicle,
  position,
  accent,
  compact = false,
}: {
  vehicle: MineCastVehicle;
  position: SpatialPosition;
  /** The marker's own colour, so label and machine read as one object. */
  accent: string;
  /**
   * DIGITAL-TWIN-OPERATIONAL-FLOW-01: a neighbour in a label cluster that is NOT the
   * selection folds to identity + speed + provenance, so two trucks at a junction stay
   * readable. The figures are still in the fleet and selected-vehicle panels.
   */
  compact?: boolean;
}) {
  const tone = availabilityTone(vehicle.availability);
  const highRisk = !vehicle.safety.unavailable && vehicle.safety.riskLevel === "HIGH";

  return (
    <div
      className={`mc-callout${compact ? " mc-callout-compact" : ""}`}
      style={{ "--mc-callout-accent": accent } as CSSProperties}
      data-vehicle-id={vehicle.canonicalVehicleId}
      data-compact={compact ? "true" : undefined}
    >
      <div className="mc-callout-head">
        <span className={`mc-callout-dot mc-tone-${tone}`} aria-hidden="true" />
        <span className="mc-callout-id">{vehicle.displayId}</span>
        <span className="mc-callout-avail">{vehicle.availability}</span>
      </div>

      <dl className="mc-callout-chips">
        <div className="mc-chip">
          <dt>SPD</dt>
          <dd className="mono">{speedText(vehicle.speedMps)}</dd>
        </div>
        {compact ? null : (
          <>
            <div className="mc-chip">
              <dt>MODE</dt>
              <dd>{vehicle.mode ?? UNAVAILABLE_LABEL}</dd>
            </div>
            <div className={`mc-chip mc-chip-${vehicle.dataState === "CURRENT" ? "ok" : "warn"}`}>
              <dt>DATA</dt>
              <dd>{vehicle.dataState}</dd>
            </div>
            <div className={`mc-chip${highRisk ? " mc-chip-crit" : ""}`}>
              <dt>SAF</dt>
              <dd>{riskText(vehicle)}</dd>
            </div>
            <div className="mc-chip">
              <dt>V2V</dt>
              <dd>
                <span aria-hidden="true">{LINK_STATE_GLYPH[vehicle.v2v.state]}</span>{" "}
                {vehicle.v2v.state}
              </dd>
            </div>
          </>
        )}
      </dl>

      {/*
        The stripe is what makes this label honest at a glance: the machine is drawn at a
        Digital Twin demonstration position, and the label says so as part of its shape.
      */}
      <div className="mc-callout-provenance">
        {position.synthetic ? "SIMULATION · DIGITAL TWIN" : position.provenance}
        <span className="mc-callout-frame">{position.frame}</span>
      </div>
    </div>
  );
}
