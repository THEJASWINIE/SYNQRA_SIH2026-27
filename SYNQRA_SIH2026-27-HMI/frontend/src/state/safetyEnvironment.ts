/**
 * S3 Safety / Environment — presentation derivation. Phase 6.
 *
 * ==========================================================================
 *  THIS MODULE COMPUTES NO SAFETY VALUE.
 *
 *  It does not solve v_safe, does not compute a stopping distance, does not infer a
 *  limiter, and does not classify a safety state. It READS values Task 2 supplied and
 *  formats them. Where nothing was supplied, it says UNAVAILABLE.
 *
 *  Why this matters more here than anywhere else: a fabricated safe speed is the single
 *  most dangerous thing this HMI could display. An operator who sees a number believes a
 *  solver produced it. So there is exactly one rule - if it was not supplied, it does not
 *  appear.
 * ==========================================================================
 *
 * AUDITED AVAILABILITY (live HMI/Twin path, measured, not assumed):
 *
 *   AVAILABLE      speed_mps, speed_mps_reported, rpm, communication_state,
 *                  sequence, telemetry_transport, received_at, plus per-field
 *                  source/origin/freshness
 *   UNAVAILABLE    v_safe, v_stop, v_retarder, v_traction, v_curve, v_mine, v_command,
 *                  active constraint, stopping distance, safety state,
 *                  visibility, friction, surface, fog state,
 *                  position, heading, grade, curvature, road_id
 *
 * The unavailable set is empty in the LIVE provider because no safety solver and no
 * environment source runs inside the HMI backend process - `twin_projection` already
 * exposes `environment`, and it comes back `{}`. The MOCK and REPLAY providers DO supply
 * `SafetyState` and `RoadState`, so the same screen shows real values there. Both cases
 * are handled by reading the slices, never by branching on which provider is connected.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { RoadState, SafetyState, VehicleState } from "../contracts/domain";

/**
 * PHASE 8 — the shared vocabulary now lives in `state/dataStatus.ts`.
 *
 * These are re-exports, not copies. S3 keeps importing them from here so no Phase 6 call
 * site churns, but there is exactly ONE definition of "--", of SIMULATION vs PHYSICAL and
 * of what counts as hardware-origin data across the whole HMI.
 */
export { isPhysical, UNAVAILABLE_VALUE as UNAVAILABLE } from "./dataStatus";
import { UNAVAILABLE_VALUE as UNAVAILABLE, vehicleProvenanceLabel } from "./dataStatus";

/** S3/S6 spelling of the shared provenance label. One implementation, one wording. */
export const provenanceLabel = vehicleProvenanceLabel;

/** A single labelled readout. `available: false` means nothing was supplied. */
export interface Readout {
  label: string;
  value: string;
  unit?: string | undefined;
  available: boolean;
  /** Where the value came from, when the supplier said. */
  provenance?: string | undefined;
}

function readout(
  label: string,
  value: number | null | undefined,
  unit: string,
  transform: (v: number) => number = (v) => v,
  provenance?: string,
): Readout {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return { label, value: UNAVAILABLE, available: false };
  }
  return {
    label,
    value: transform(value).toFixed(1),
    unit,
    available: true,
    provenance: provenance ?? undefined,
  };
}

/** m/s -> km/h. A unit conversion, not a derivation of new information. */
const toKmh = (mps: number) => mps * 3.6;

// ---------------------------------------------------------------------------
// operating state
// ---------------------------------------------------------------------------

/**
 * Current / safe / command speed.
 *
 * Safe speed comes from the SUPPLIED `SafetyState.vSafe` and from nowhere else. When no
 * SafetyState exists - the current live condition - it is UNAVAILABLE, never derived from
 * the current speed and never defaulted.
 */
export function operatingReadouts(
  vehicle: VehicleState | undefined,
  safety: SafetyState | undefined,
  commandSpeedMps: number | null,
): Readout[] {
  return [
    readout("Current speed", vehicle?.speedMps, "km/h", toKmh, provenanceLabel(vehicle)),
    readout("Safe speed", safety?.vSafe, "km/h", toKmh, "supplied by the safety layer"),
    readout("Command speed", commandSpeedMps, "km/h", toKmh, "supplied by the command path"),
  ];
}

// ---------------------------------------------------------------------------
// environment
// ---------------------------------------------------------------------------

/**
 * Environment readouts from the SUPPLIED RoadState.
 *
 * The game_ui simulator has fog scenarios; that is a different process with its own state
 * and is NOT evidence about this screen's data. With no RoadState supplied, every field
 * is UNAVAILABLE - none is borrowed from the scenario selector.
 */
export function environmentReadouts(road: RoadState | undefined): Readout[] {
  return [
    readout("Visibility", road?.visibility?.value, "m"),
    readout("Friction (μ)", road?.friction?.value, ""),
    {
      label: "Surface",
      value: road?.surfaceState ?? UNAVAILABLE,
      available: Boolean(road?.surfaceState),
    },
    readout("Grade", road?.grade, "rad"),
    {
      label: "Road segment",
      value: road?.segmentId ?? UNAVAILABLE,
      available: Boolean(road?.segmentId),
    },
  ];
}

// ---------------------------------------------------------------------------
// safety envelope
// ---------------------------------------------------------------------------

export interface EnvelopeView {
  /** True when at least one authoritative safety value exists. */
  anyAvailable: boolean;
  readouts: Readout[];
  /** Shown when nothing is available. Explains why, accurately. */
  unavailableReason: string | null;
}

/**
 * The safety envelope, limited to what was actually supplied.
 *
 * The individual limiters (v_stop, v_retarder, v_traction, v_curve, v_mine) are NOT part
 * of the HMI contract - no supplied message carries them - so they are never listed as
 * empty rows that could read as "measured zero". Only v_safe and h_safe exist in the
 * contract, and each appears only when supplied.
 */
export function envelopeView(safety: SafetyState | undefined): EnvelopeView {
  const readouts: Readout[] = [
    readout("v_safe", safety?.vSafe, "km/h", toKmh),
    readout("h_safe", safety?.hSafe, ""),
  ];
  const anyAvailable = readouts.some((r) => r.available);

  return {
    anyAvailable,
    readouts,
    unavailableReason: anyAvailable
      ? null
      : "The current live provider does not expose safety solver output. No v_safe, " +
        "limiter breakdown or stopping distance is supplied, so none is shown.",
  };
}

/**
 * Active constraint, verbatim from the supplier.
 *
 * Never inferred. In particular, the smallest of several numbers is NOT treated as the
 * dominant limiter, because the limiter values are not supplied at all.
 */
export function activeConstraintText(safety: SafetyState | undefined): string {
  const constraint = safety?.activeConstraint;
  if (!constraint || constraint === "UNKNOWN") return UNAVAILABLE;
  return constraint;
}

/**
 * Safety state, mapped from the SUPPLIED risk level.
 *
 * No threshold is invented here: there is no "speed > X means WARNING" rule, because that
 * would be a second safety engine. If Task 2 supplied no risk level, the state is
 * UNAVAILABLE.
 */
export function safetyStateText(safety: SafetyState | undefined): string {
  return safety?.riskLevel ?? UNAVAILABLE;
}

/**
 * Stopping distance.
 *
 * S_stop = v*tau + v^2/(2*a_dec) belongs to the authoritative safety layer and is NOT
 * recomputed here. No supplied message carries the result, so it is always UNAVAILABLE.
 */
export function stoppingDistanceText(): string {
  return UNAVAILABLE;
}
