/**
 * Driver state — the single dominant instruction on the dumper screen (spec §11).
 *
 * ==========================================================================
 *  THIS IS NOT A SAFETY ENGINE. IT NAMES A STATE FROM SUPPLIED VALUES.
 *
 *  Every input below is produced by the safety subsystem or the Digital Twin and carried
 *  through the canonical state: v_safe, H_safe, the current gap, the violation flags,
 *  the vehicle mode, the Twin's freshness verdicts and the link states. This module
 *  compares supplied numbers with each other and ranks supplied flags by severity. It
 *  computes no physics, no envelope and no headway of its own.
 *
 *  IT NEVER BECOMES MORE PERMISSIVE WHEN DATA IS MISSING. No safe speed means
 *  SAFETY_DATA_UNAVAILABLE, never SAFE. Stale safety data means DATA_STALE, never the
 *  last good state.
 * ==========================================================================
 *
 * Spec §11 states, in priority order (highest first):
 *
 *   STOP            supplied stop condition: v_safe = 0, headway or envelope violation,
 *                   or vehicle mode STOP_UNSAFE
 *   DATA_STALE      safety-critical data too old (the Twin's verdict, not a local timer)
 *   SLOW_DOWN       actual speed above the supplied v_safe
 *   DEGRADED        vehicle mode DEGRADED, or the backend link is DISCONNECTED or STALE
 *                   (UNAVAILABLE link evidence is shown as such, not promoted to DEGRADED)
 *   CAUTION         approaching v_safe (the existing presentation ratio)
 *   FOLLOWING       the safety producer names a lead vehicle and has judged the gap safe
 *   SAFE            speed within v_safe and no lead vehicle named
 *
 * The contract has no emergency-stop signal (no E-STOP mode exists in VEHICLE_MODES), so
 * no E_STOP state is shown. Fabricating one from another flag would be a lie.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { SafetyState, VehicleState } from "../contracts/domain";
import type { DataState } from "../state/dataStatus";
import type { OperatorReadout } from "../state/operatorAction";
import type { LinkState } from "./communication";

export type DriverState =
  | "SAFE"
  | "CAUTION"
  | "SLOW_DOWN"
  | "FOLLOWING"
  | "STOP"
  | "DEGRADED"
  | "DATA_STALE"
  | "SAFETY_DATA_UNAVAILABLE";

/** Driver-facing wording. Never colour-only (accessibility). */
export const DRIVER_STATE_TEXT: Record<DriverState, string> = {
  SAFE: "SAFE",
  CAUTION: "CAUTION",
  SLOW_DOWN: "SLOW DOWN",
  FOLLOWING: "FOLLOWING",
  STOP: "STOP",
  DEGRADED: "DEGRADED",
  DATA_STALE: "DATA STALE",
  SAFETY_DATA_UNAVAILABLE: "SAFETY DATA UNAVAILABLE",
};

/** The action the driver takes. Spec §11, verbatim where it gives one. */
export const DRIVER_ACTION_TEXT: Record<DriverState, string> = {
  SAFE: "CONTINUE",
  CAUTION: "CAUTION",
  SLOW_DOWN: "SLOW DOWN",
  FOLLOWING: "FOLLOW SAFELY",
  STOP: "STOP",
  DEGRADED: "USE SAFE FALLBACK",
  DATA_STALE: "SAFE FALLBACK — DATA STALE",
  SAFETY_DATA_UNAVAILABLE: "DO NOT ASSUME SAFE",
};

export interface DriverStateInput {
  /** The speed-vs-v_safe readout, already derived from supplied values. */
  readonly readout: OperatorReadout;
  readonly safety: SafetyState | null;
  readonly vehicle: VehicleState | null;
  /** The Twin's freshness verdict on the safety slice. */
  readonly safetyData: DataState;
  /** The Twin's freshness verdict on the vehicle slice. */
  readonly vehicleData: DataState;
  readonly backendLink: LinkState;
}

export interface DriverStateResult {
  readonly state: DriverState;
  /** One line saying why, in driver wording. */
  readonly why: string;
}

export type FollowingStatus = "FOLLOWING" | "STOP" | "NO_LEAD" | "UNAVAILABLE";

export const FOLLOWING_STATUS_TEXT: Record<FollowingStatus, string> = {
  FOLLOWING: "FOLLOWING",
  STOP: "STOP",
  NO_LEAD: "NO LEAD VEHICLE",
  UNAVAILABLE: "UNAVAILABLE",
};

/**
 * Following status from the CANONICAL safety state only (HMI-SAFETY-01).
 *
 *   headwayViolation === true   -> STOP        the producer judged the gap unsafe
 *   leadVehicleId === null      -> NO_LEAD     the producer names no lead vehicle
 *   headwayViolation === false  -> FOLLOWING   a lead exists and the producer judged the gap
 *   otherwise                   -> UNAVAILABLE the producer has not evaluated headway
 *
 * The gap and H_safe are displayed beside each other but are NEVER compared here: the
 * headway judgement is the safety producer's (`headwayViolation`), and H_safe's unit is
 * unresolved (AMB-001), so a local `gap < H_safe` would be a second safety engine.
 */
export function followingStatus(safety: SafetyState | null): FollowingStatus {
  if (!safety) return "UNAVAILABLE";
  if (safety.headwayViolation === true) return "STOP";
  if (safety.leadVehicleId === null) return "NO_LEAD";
  if (safety.headwayViolation === false) return "FOLLOWING";
  return "UNAVAILABLE";
}

export type FogBand = "CLEAR" | "MODERATE" | "DENSE" | "EXTREME";

/**
 * Fog wording for a SUPPLIED visibility distance (spec §9 "Fog state").
 *
 * The Twin supplies visibility in metres and no fog enum, so these are PRESENTATION
 * bands - lower bounds in metres - that put a word next to the number. The number is
 * always shown too; the band never replaces it and nothing downstream decides on it.
 * v_safe already reflects visibility and is supplied separately.
 */
export const FOG_BANDS: readonly { readonly band: FogBand; readonly minVisibilityM: number }[] = [
  { band: "CLEAR", minVisibilityM: 200 },
  { band: "MODERATE", minVisibilityM: 100 },
  { band: "DENSE", minVisibilityM: 15 },
  { band: "EXTREME", minVisibilityM: 0 },
];

export function fogBand(visibilityM: number | null | undefined): FogBand | null {
  if (visibilityM === null || visibilityM === undefined || !Number.isFinite(visibilityM)) {
    return null;
  }
  for (const entry of FOG_BANDS) if (visibilityM >= entry.minVisibilityM) return entry.band;
  return "EXTREME";
}

function stale(state: DataState): boolean {
  return state === "STALE";
}

/**
 * Rank the supplied conditions into one driver state.
 *
 * Order matters and is the order of the spec table, most severe first. A more severe
 * condition always wins: a stale STOP is still a STOP, and a following vehicle that is
 * also above v_safe is told to SLOW DOWN, because that is the action that fixes both.
 */
export function deriveDriverState(input: DriverStateInput): DriverStateResult {
  const { readout, safety, vehicle, safetyData, vehicleData, backendLink } = input;

  // -- STOP: any supplied stop condition ------------------------------------
  if (vehicle?.mode === "STOP_UNSAFE") {
    return { state: "STOP", why: "Vehicle mode is STOP_UNSAFE." };
  }
  if (safety?.headwayViolation === true) {
    return { state: "STOP", why: "Headway violation reported: gap is below the safe threshold." };
  }
  if (safety?.envelopeViolation === true) {
    return { state: "STOP", why: "Stopping envelope violation reported." };
  }
  if (readout.action === "STOP") {
    return { state: "STOP", why: "Supplied safe speed is zero." };
  }

  // -- no safety data: never assumed safe ------------------------------------
  if (readout.action === "SAFETY_DATA_UNAVAILABLE") {
    return {
      state: "SAFETY_DATA_UNAVAILABLE",
      why:
        readout.safeSpeedMps === null
          ? "No safe speed supplied by the safety subsystem."
          : "No actual speed supplied, so it cannot be compared with the safe speed.",
    };
  }

  // -- stale: the Twin's verdict --------------------------------------------
  if (stale(safetyData)) {
    return { state: "DATA_STALE", why: "Safety data is older than the freshness threshold." };
  }
  if (stale(vehicleData)) {
    return { state: "DATA_STALE", why: "Vehicle telemetry is older than the freshness threshold." };
  }

  // -- speed ----------------------------------------------------------------
  if (readout.action === "SLOW_DOWN") {
    return { state: "SLOW_DOWN", why: "Actual speed is above the supplied safe speed." };
  }

  // -- degraded -------------------------------------------------------------
  if (vehicle?.mode === "DEGRADED") {
    return { state: "DEGRADED", why: "Vehicle mode is DEGRADED." };
  }
  if (backendLink === "DISCONNECTED" || backendLink === "STALE") {
    return { state: "DEGRADED", why: `Backend link is ${backendLink}.` };
  }

  // -- caution --------------------------------------------------------------
  if (readout.action === "CAUTION") {
    return { state: "CAUTION", why: "Approaching the supplied safe speed." };
  }

  // -- following / safe -----------------------------------------------------
  // FOLLOWING is the producer's verdict (a named lead, gap judged and not violated); a
  // violated gap is STOP above. No gap arithmetic happens here.
  if (followingStatus(safety) === "FOLLOWING") {
    return {
      state: "FOLLOWING",
      why: `Following ${safety?.leadVehicleId ?? "lead vehicle"} - keep the required gap.`,
    };
  }
  return { state: "SAFE", why: "Within the supplied safe speed." };
}

/** rad -> % grade, preserving UNAVAILABLE as null. A unit conversion, not an estimate. */
export function gradePercent(gradeRad: number | null | undefined): number | null {
  if (gradeRad === null || gradeRad === undefined || !Number.isFinite(gradeRad)) return null;
  return Math.tan(gradeRad) * 100;
}
