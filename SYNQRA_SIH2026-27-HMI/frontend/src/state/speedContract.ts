/**
 * Operational speed truth contract — HMI-DATA-01.
 *
 * ==========================================================================
 *  ONE DEFINITION OF "ACTUAL SPEED". READ, NEVER COMPUTED.
 *
 *  The canonical Twin carries several speed-shaped fields and they are NOT the same
 *  quantity. This module names each one, says which is authoritative, and is the only
 *  place the HMI decides what to show as the vehicle's actual speed. No screen picks a
 *  field on its own.
 * ==========================================================================
 *
 * FIELD SEMANTICS (traced from telemetry_ingest.py `_build_twin_fields` and
 * twin_projection.py `VEHICLE_PROJECTION_FIELDS`; this file mirrors, never redefines):
 *
 *   speed_mps               CANONICAL OPERATIONAL ACTUAL SPEED. Encoder-derived:
 *                           rpm x 2*pi*wheel_radius_m / 60, computed by the backend
 *                           UnitConverter from the MEASURED wheel RPM and the calibrated
 *                           radius in config/physical_vehicle_parameters.json.
 *                           source=DERIVED origin=HARDWARE for a physical packet,
 *                           source=SIMULATION origin=SIMULATION for /api/telemetry.
 *                           ABSENT (never 0) when there is no RPM or no calibrated radius.
 *                           -> VehicleState.speedMps
 *
 *   speed_mps_reported      What the telemetry producer put in its SPEED field, for a
 *                           vehicle whose firmware measures it. Stored beside speed_mps,
 *                           never merged with it, never displayed as actual speed.
 *                           -> VehicleState.provenance.speed_mps_reported only
 *
 *   speed_mps_pwm_derived   TRUCK_02's SPEED field: the commanded prototype velocity
 *                           derived from motor PWM, NOT an encoder measurement. Kept
 *                           under its own name so it cannot be mistaken for one.
 *                           -> VehicleState.provenance.speed_mps_pwm_derived only
 *
 *   rpm                     MEASURED wheel RPM. The input to speed_mps, not a speed.
 *
 *   v_safe_mps / SafetyState.vSafe
 *                           SAFE speed, supplied by the safety solver. Never a
 *                           substitute for actual speed and never substituted by it.
 *
 *   SafetyState.actualSpeed The speed the safety solver EVALUATED against vSafe. It is
 *                           the right operand for the violation comparison (the HMI
 *                           must not re-judge the solver with a different number), but
 *                           it is not the canonical actual speed and is only displayed
 *                           as one, labelled SAFETY-EVALUATED, when the Twin has none.
 *
 *   DispatchCommand.targetSpeed / v_command_mps / v_dispatch_mps
 *                           COMMAND / TARGET speed. A request. It becomes actual speed
 *                           only when telemetry says so.
 *
 * Pure and framework-free (M4D-C).
 */

import type { SafetyState, TwinFieldProvenance, VehicleState } from "../contracts/domain";
import { provenanceLabel } from "./dataStatus";

/** The Twin field that IS the actual speed. Everything else is something else. */
export const CANONICAL_SPEED_FIELD = "speed_mps" as const;

/** Where a displayed actual speed came from. Never absent when a value is shown. */
export type ActualSpeedSource = "TWIN_SPEED_MPS" | "SAFETY_EVALUATED";

export const ACTUAL_SPEED_SOURCE_TEXT: Record<ActualSpeedSource, string> = {
  TWIN_SPEED_MPS: "ENCODER-DERIVED (rpm × wheel radius)",
  SAFETY_EVALUATED: "SAFETY-EVALUATED",
};

export interface ActualSpeed {
  /** m/s. Null when neither the Twin nor the safety solver supplied a finite value. */
  mps: number | null;
  /** Null exactly when `mps` is null. */
  source: ActualSpeedSource | null;
  /** m/s the safety solver evaluated, when it supplied one. Kept apart from `mps`. */
  evaluatedMps: number | null;
  /** True when both exist and disagree — surfaced, never hidden or averaged. */
  disagreesWithEvaluated: boolean;
  /** Twin provenance of speed_mps, for the SIMULATION / PHYSICAL (derived) badge. */
  provenance: TwinFieldProvenance | null;
}

const finite = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

/** Two speeds shown at 0.1 km/h resolution are "equal" below this (m/s). */
const AGREEMENT_TOLERANCE_MPS = 0.05 / 3.6;

/**
 * Resolve the actual speed to display. The Twin's canonical `speed_mps` wins whenever it
 * exists; the solver's evaluated speed is used only in its absence and says so via
 * `source`. No averaging, no "best available".
 */
export function resolveActualSpeed(
  vehicle: VehicleState | null | undefined,
  safety: SafetyState | null | undefined,
): ActualSpeed {
  const canonical = finite(vehicle?.speedMps) ? vehicle.speedMps : null;
  const evaluated = finite(safety?.actualSpeed) ? safety.actualSpeed : null;
  const provenance = vehicle?.provenance?.[CANONICAL_SPEED_FIELD] ?? null;

  if (canonical !== null) {
    return {
      mps: canonical,
      source: "TWIN_SPEED_MPS",
      evaluatedMps: evaluated,
      disagreesWithEvaluated:
        evaluated !== null && Math.abs(evaluated - canonical) > AGREEMENT_TOLERANCE_MPS,
      provenance,
    };
  }
  return {
    mps: evaluated,
    source: evaluated === null ? null : "SAFETY_EVALUATED",
    evaluatedMps: evaluated,
    disagreesWithEvaluated: false,
    provenance,
  };
}

/** Source badge for a displayed actual speed, e.g. "ENCODER-DERIVED … · SIMULATION". */
export function actualSpeedSourceText(actual: ActualSpeed): string | null {
  if (actual.source === null) return null;
  if (actual.source === "SAFETY_EVALUATED") return ACTUAL_SPEED_SOURCE_TEXT.SAFETY_EVALUATED;
  return `${ACTUAL_SPEED_SOURCE_TEXT.TWIN_SPEED_MPS} · ${provenanceLabel(actual.provenance)}`;
}
