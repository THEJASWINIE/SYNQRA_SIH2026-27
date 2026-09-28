/**
 * Driver state — spec §11 table, plus the fail-closed rules.
 *
 * SOFTWARE ONLY. No hardware executed. Every input is a synthetic fixture standing in for
 * values the Twin would supply.
 */

import { describe, expect, it } from "vitest";

import type { SafetyState, VehicleState } from "../contracts/domain";
import { deriveOperatorReadout } from "../state/operatorAction";
import {
  DRIVER_ACTION_TEXT,
  DRIVER_STATE_TEXT,
  type DriverStateInput,
  deriveDriverState,
  fogBand,
  followingStatus,
  gradePercent,
} from "./driverState";

const T = "2026-09-10T12:00:00.000Z";

function safety(overrides: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: T,
    vSafe: 5,
    hSafe: 20,
    actualSpeed: 4,
    headwayCurrent: 30,
    leadVehicleId: "TRUCK_01",
    activeConstraint: "VISIBILITY",
    riskLevel: "LOW",
    headwayViolation: false,
    envelopeViolation: false,
    ...overrides,
  };
}

function vehicle(overrides: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: T,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps: 4,
    position: { x: 0, y: 0, segmentId: "ROAD_1", offsetM: 0 },
    accelMps2: null,
    gradeRad: null,
    commConfidence: 1,
    frictionEst: null,
    routeId: null,
    ...overrides,
  } as VehicleState;
}

function input(
  s: SafetyState | null,
  v: VehicleState | null,
  extra: Partial<DriverStateInput> = {},
): DriverStateInput {
  return {
    readout: deriveOperatorReadout(s, v),
    safety: s,
    vehicle: v,
    safetyData: "CURRENT",
    vehicleData: "CURRENT",
    backendLink: "CONNECTED",
    ...extra,
  };
}

describe("driver state — spec §11 table", () => {
  it("SAFE when speed <= v_safe and the producer names no lead vehicle", () => {
    const r = deriveDriverState(input(safety({ leadVehicleId: null }), vehicle()));
    expect(r.state).toBe("SAFE");
    expect(DRIVER_ACTION_TEXT[r.state]).toBe("CONTINUE");
  });

  it("FOLLOWING when the producer names a lead and has judged the gap not violated", () => {
    // HMI-SAFETY-01: the fixture's gap (30) vs H_safe (20) is NOT compared here; the
    // producer's headwayViolation=false is the verdict.
    const r = deriveDriverState(input(safety(), vehicle()));
    expect(r.state).toBe("FOLLOWING");
    expect(DRIVER_ACTION_TEXT[r.state]).toBe("FOLLOW SAFELY");
  });

  it("CAUTION when approaching v_safe", () => {
    const r = deriveDriverState(input(safety({ actualSpeed: 4.6 }), vehicle()));
    expect(r.state).toBe("CAUTION");
  });

  it("SLOW DOWN when actual speed > v_safe (spec example: 24 km/h vs 18 km/h)", () => {
    const r = deriveDriverState(
      input(safety({ actualSpeed: 24 / 3.6, vSafe: 18 / 3.6 }), vehicle()),
    );
    expect(r.state).toBe("SLOW_DOWN");
    expect(DRIVER_STATE_TEXT[r.state]).toBe("SLOW DOWN");
  });

  it("FOLLOWING when the gap is below the required gap (spec example: 12 m vs 20 m)", () => {
    const r = deriveDriverState(input(safety({ headwayCurrent: 12, hSafe: 20 }), vehicle()));
    expect(r.state).toBe("FOLLOWING");
    expect(r.why).toContain("TRUCK_01");
    expect(DRIVER_ACTION_TEXT[r.state]).toBe("FOLLOW SAFELY");
  });

  it("STOP on a supplied headway violation, even when the speed is fine", () => {
    const r = deriveDriverState(input(safety({ headwayViolation: true }), vehicle()));
    expect(r.state).toBe("STOP");
  });

  it("STOP on a supplied envelope violation", () => {
    const r = deriveDriverState(input(safety({ envelopeViolation: true }), vehicle()));
    expect(r.state).toBe("STOP");
  });

  it("STOP when the supplied safe speed is zero", () => {
    const r = deriveDriverState(input(safety({ vSafe: 0 }), vehicle()));
    expect(r.state).toBe("STOP");
  });

  it("STOP when the vehicle mode is STOP_UNSAFE", () => {
    const r = deriveDriverState(input(safety(), vehicle({ mode: "STOP_UNSAFE" })));
    expect(r.state).toBe("STOP");
  });

  it("DEGRADED when the vehicle mode is DEGRADED", () => {
    const r = deriveDriverState(input(safety(), vehicle({ mode: "DEGRADED" })));
    expect(r.state).toBe("DEGRADED");
  });

  it("DEGRADED when the backend link is not CONNECTED", () => {
    const r = deriveDriverState(input(safety(), vehicle(), { backendLink: "DISCONNECTED" }));
    expect(r.state).toBe("DEGRADED");
    expect(r.why).toContain("DISCONNECTED");
  });

  it("DATA STALE when the Twin marks the safety slice stale", () => {
    const r = deriveDriverState(input(safety(), vehicle(), { safetyData: "STALE" }));
    expect(r.state).toBe("DATA_STALE");
  });

  it("DATA STALE when the Twin marks the vehicle slice stale", () => {
    const r = deriveDriverState(input(safety(), vehicle(), { vehicleData: "STALE" }));
    expect(r.state).toBe("DATA_STALE");
  });
});

describe("driver state — never more permissive when data is missing", () => {
  it("no safety slice at all is SAFETY DATA UNAVAILABLE, never SAFE", () => {
    const r = deriveDriverState(input(null, vehicle()));
    expect(r.state).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(DRIVER_ACTION_TEXT[r.state]).toBe("DO NOT ASSUME SAFE");
  });

  it("no v_safe is SAFETY DATA UNAVAILABLE", () => {
    const r = deriveDriverState(input(safety({ vSafe: null }), vehicle()));
    expect(r.state).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(r.why).toContain("No safe speed");
  });

  it("no vehicle slice with a safety slice still compares the supplied actualSpeed", () => {
    const r = deriveDriverState(input(safety({ leadVehicleId: null }), null));
    expect(r.state).toBe("SAFE");
  });

  it("a stale STOP is still a STOP (severity wins over staleness)", () => {
    const r = deriveDriverState(
      input(safety({ headwayViolation: true }), vehicle(), { safetyData: "STALE" }),
    );
    expect(r.state).toBe("STOP");
  });

  it("stale data outranks SLOW DOWN and FOLLOWING", () => {
    const r = deriveDriverState(
      input(safety({ actualSpeed: 9, headwayCurrent: 5 }), vehicle(), { safetyData: "STALE" }),
    );
    expect(r.state).toBe("DATA_STALE");
  });

  it("SLOW DOWN outranks FOLLOWING when both apply", () => {
    const r = deriveDriverState(input(safety({ actualSpeed: 9, headwayCurrent: 5 }), vehicle()));
    expect(r.state).toBe("SLOW_DOWN");
  });

  it("has a text and an action for every state (never colour-only)", () => {
    for (const state of Object.keys(DRIVER_STATE_TEXT) as (keyof typeof DRIVER_STATE_TEXT)[]) {
      expect(DRIVER_STATE_TEXT[state].length).toBeGreaterThan(0);
      expect(DRIVER_ACTION_TEXT[state].length).toBeGreaterThan(0);
    }
  });
});

describe("following status", () => {
  it("FOLLOWING is the producer's verdict, never a local gap comparison", () => {
    // gap 30 >= H_safe 20 and gap 12 < H_safe 20 give the SAME answer: the numbers are
    // displayed, the judgement is the supplied headwayViolation flag (HMI-SAFETY-01).
    expect(followingStatus(safety())).toBe("FOLLOWING");
    expect(followingStatus(safety({ headwayCurrent: 12 }))).toBe("FOLLOWING");
    expect(followingStatus(safety({ headwayCurrent: 100, hSafe: 1 }))).toBe("FOLLOWING");
  });
  it("STOP on a violation flag regardless of the numbers", () => {
    expect(followingStatus(safety({ headwayViolation: true, headwayCurrent: 100 }))).toBe("STOP");
  });
  it("NO LEAD when there is no lead vehicle", () => {
    expect(followingStatus(safety({ leadVehicleId: null }))).toBe("NO_LEAD");
  });
  it("UNAVAILABLE when the producer has not evaluated headway", () => {
    expect(followingStatus(safety({ headwayViolation: null }))).toBe("UNAVAILABLE");
    expect(followingStatus(safety({ headwayViolation: null, headwayCurrent: 12 }))).toBe("UNAVAILABLE");
    expect(followingStatus(null)).toBe("UNAVAILABLE");
  });
});

describe("fog band and grade — presentation of supplied numbers only", () => {
  it("bands a supplied visibility; spec example 15 m reads DENSE", () => {
    expect(fogBand(15)).toBe("DENSE");
    expect(fogBand(500)).toBe("CLEAR");
    expect(fogBand(120)).toBe("MODERATE");
    expect(fogBand(5)).toBe("EXTREME");
  });
  it("has no band when visibility is not supplied", () => {
    expect(fogBand(null)).toBeNull();
    expect(fogBand(Number.NaN)).toBeNull();
  });
  it("converts grade radians to percent and keeps UNAVAILABLE as null", () => {
    expect(gradePercent(Math.atan(0.04))).toBeCloseTo(4, 6);
    expect(gradePercent(null)).toBeNull();
  });
});
