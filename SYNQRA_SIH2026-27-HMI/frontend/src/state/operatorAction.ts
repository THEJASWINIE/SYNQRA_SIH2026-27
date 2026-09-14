/**
 * Operator action state — P8.
 *
 * ==========================================================================
 *  THIS IS NOT A SAFETY ENGINE.
 *
 *  It computes no physics. It compares two SUPPLIED numbers — the actual speed
 *  and the authoritative v_safe, both produced by Task 2 / fog_safe and carried
 *  through the canonical Twin — and names the resulting operator instruction.
 *  That is the same thing the existing envelope-violation screen already does:
 *  "the HMI compares two supplied numbers; it computes neither".
 *
 *  IT NEVER BECOMES MORE PERMISSIVE WHEN DATA IS MISSING.
 *  No v_safe => SAFETY_DATA_UNAVAILABLE, never NORMAL.
 * ==========================================================================
 */

import type { SafetyState, VehicleState } from "../contracts/domain";
import { type ActualSpeed, resolveActualSpeed } from "./speedContract";

/** The single dominant instruction shown to the operator. */
export type OperatorAction =
  | "NORMAL"
  | "CAUTION"
  | "SLOW_DOWN"
  | "STOP"
  | "SAFETY_DATA_UNAVAILABLE";

/** Operator-facing wording for each action. Never colour-only (accessibility). */
export const ACTION_LABEL: Record<OperatorAction, string> = {
  NORMAL: "NORMAL",
  CAUTION: "CAUTION",
  SLOW_DOWN: "SLOW DOWN",
  STOP: "STOP",
  SAFETY_DATA_UNAVAILABLE: "SAFETY DATA UNAVAILABLE",
};

export const ACTION_DETAIL: Record<OperatorAction, string> = {
  NORMAL: "Within the supplied safe speed.",
  CAUTION: "Close to the supplied safe speed.",
  SLOW_DOWN: "Above the supplied safe speed — reduce speed.",
  STOP: "Safe speed is zero — do not proceed.",
  SAFETY_DATA_UNAVAILABLE: "No safe speed supplied. Do not assume it is safe to proceed.",
};

/**
 * Fraction of v_safe at or above which the operator is warned.
 *
 * REUSED, NOT INVENTED: this is the 0.88 ratio the existing `game_ui` operator display
 * already used for its CAUTION band. It is a presentation threshold for an advisory
 * banner, not a safety limit — the safety limit is v_safe itself, and it is supplied.
 */
export const CAUTION_RATIO = 0.88;

export interface OperatorReadout {
  action: OperatorAction;
  /**
   * m/s, the DISPLAYED actual speed per `speedContract`: the Twin's canonical
   * `speed_mps` when it exists, else the solver's evaluated speed. Null when neither.
   */
  actualSpeedMps: number | null;
  /** Where `actualSpeedMps` came from, and the solver's own operand, kept apart. */
  actualSpeed: ActualSpeed;
  /** m/s, supplied by Task 2 / fog_safe. Null when unavailable. NEVER computed here. */
  safeSpeedMps: number | null;
  /** Why the speed is restricted, in operator wording. Null when not supplied. */
  reason: string | null;
}

const CONSTRAINT_TEXT: Record<string, string> = {
  v_stop: "STOPPING DISTANCE",
  v_curve: "CURVE LIMIT",
  v_mine: "MINE SPEED LIMIT",
  v_traction: "TRACTION",
  v_traction_ceiling: "TRACTION LIMIT",
  v_retarder: "RETARDER",
  VISIBILITY: "FOG VISIBILITY",
  STOPPING_DISTANCE: "STOPPING DISTANCE",
  CURVE: "CURVE LIMIT",
  SITE_SPEED_LIMIT: "MINE SPEED LIMIT",
  TRACTION: "TRACTION",
  RETARDER: "RETARDER",
  INVALID_FRICTION: "FRICTION DATA INVALID",
  INVALID_INPUT: "SAFETY INPUT INVALID",
};

/** Operator-readable wording for a supplied constraint. Never invents a cause. */
export function constraintText(constraint: string | null | undefined): string | null {
  if (!constraint || constraint === "UNKNOWN") return null;
  // An explicit NONE from the producer is a statement, not an absence.
  if (constraint === "NONE") return "NONE";
  const mapped = CONSTRAINT_TEXT[constraint];
  if (mapped) return mapped;
  // A supplied-but-unrecognised constraint is still real; say something honest and
  // generic, and show the producer's own name for it, rather than inventing a cause.
  return `SAFETY LIMIT ACTIVE (${constraint})`;
}

/**
 * Derive the operator instruction from SUPPLIED values only.
 *
 * @param safety supplied SafetyState for the vehicle, if any
 * @param vehicle supplied VehicleState for the vehicle, if any
 */
export function deriveOperatorReadout(
  safety: SafetyState | null | undefined,
  vehicle: VehicleState | null | undefined,
): OperatorReadout {
  // HMI-DATA-01: the displayed actual speed is the canonical Twin `speed_mps`. The band
  // below is judged on the operand the safety solver itself evaluated, so the HMI never
  // re-judges the solver with a different number; the two are shown apart if they differ.
  const actualSpeed = resolveActualSpeed(vehicle, safety);
  const actualSpeedMps = actualSpeed.mps;
  const comparedMps = actualSpeed.evaluatedMps ?? actualSpeedMps;

  const safeSpeedMps = safety?.vSafe ?? null;
  const reason = constraintText(safety?.activeConstraint);

  // No authoritative safe speed => the operator is told so. NEVER "NORMAL".
  if (safeSpeedMps === null || !Number.isFinite(safeSpeedMps)) {
    return { action: "SAFETY_DATA_UNAVAILABLE", actualSpeedMps, actualSpeed, safeSpeedMps: null, reason };
  }

  // A zero ceiling is an explicit instruction not to proceed.
  if (safeSpeedMps <= 0) {
    return { action: "STOP", actualSpeedMps, actualSpeed, safeSpeedMps, reason };
  }

  // Without an actual speed we cannot compare, so we cannot claim NORMAL either.
  if (comparedMps === null || !Number.isFinite(comparedMps)) {
    return { action: "SAFETY_DATA_UNAVAILABLE", actualSpeedMps: null, actualSpeed, safeSpeedMps, reason };
  }

  if (comparedMps > safeSpeedMps) {
    return { action: "SLOW_DOWN", actualSpeedMps, actualSpeed, safeSpeedMps, reason };
  }
  if (comparedMps >= safeSpeedMps * CAUTION_RATIO) {
    return { action: "CAUTION", actualSpeedMps, actualSpeed, safeSpeedMps, reason };
  }
  return { action: "NORMAL", actualSpeedMps, actualSpeed, safeSpeedMps, reason };
}

/** m/s -> km/h, preserving UNAVAILABLE as null. Never substitutes a number. */
export function toKmh(mps: number | null | undefined): number | null {
  return mps === null || mps === undefined || !Number.isFinite(mps) ? null : mps * 3.6;
}
