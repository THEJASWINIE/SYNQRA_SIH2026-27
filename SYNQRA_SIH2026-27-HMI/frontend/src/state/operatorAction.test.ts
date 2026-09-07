/**
 * P8 — operator action derivation.
 *
 * Proves the derivation compares SUPPLIED numbers and never becomes more permissive
 * when data is missing. All values here are authored test data (SIMULATION).
 */

import { describe, expect, it } from "vitest";

import type { SafetyState, VehicleState } from "../contracts/domain";
import { CAUTION_RATIO, constraintText, deriveOperatorReadout, toKmh } from "./operatorAction";

function safety(over: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: "2026-01-01T00:00:00.000Z",
    vSafe: 10,
    hSafe: null,
    actualSpeed: 5,
    headwayCurrent: null,
    leadVehicleId: null,
    activeConstraint: "v_stop",
    riskLevel: "LOW",
    headwayViolation: null,
    envelopeViolation: null,
    ...over,
  } as SafetyState;
}

function vehicle(over: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: "2026-01-01T00:00:00.000Z",
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: 5,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "TRAVELING",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    ...over,
  } as VehicleState;
}

describe("P8 operator action — the safety-critical cases", () => {
  it("reports SAFETY DATA UNAVAILABLE when no v_safe is supplied — never NORMAL", () => {
    const readout = deriveOperatorReadout(safety({ vSafe: null }), vehicle());
    expect(readout.action).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(readout.action).not.toBe("NORMAL");
    expect(readout.safeSpeedMps).toBeNull();
  });

  it("reports SAFETY DATA UNAVAILABLE with no safety slice at all", () => {
    expect(deriveOperatorReadout(null, vehicle()).action).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(deriveOperatorReadout(undefined, undefined).action).toBe("SAFETY_DATA_UNAVAILABLE");
  });

  it("never claims NORMAL when the actual speed is unknown", () => {
    const readout = deriveOperatorReadout(
      safety({ actualSpeed: Number.NaN }),
      vehicle({ speedMps: null }),
    );
    expect(readout.action).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(readout.actualSpeedMps).toBeNull();
  });

  it("reports STOP when the supplied safe speed is zero", () => {
    expect(deriveOperatorReadout(safety({ vSafe: 0, actualSpeed: 0 }), vehicle()).action).toBe(
      "STOP",
    );
  });

  it("reports SLOW DOWN when actual exceeds safe", () => {
    const readout = deriveOperatorReadout(safety({ vSafe: 6.86, actualSpeed: 8.72 }), vehicle());
    expect(readout.action).toBe("SLOW_DOWN");
    // Actual is NOT overwritten by safe.
    expect(readout.actualSpeedMps).toBe(8.72);
    expect(readout.safeSpeedMps).toBe(6.86);
  });

  it("reports CAUTION near the supplied ceiling and NORMAL well below it", () => {
    expect(deriveOperatorReadout(safety({ vSafe: 10, actualSpeed: 9.5 }), vehicle()).action).toBe(
      "CAUTION",
    );
    expect(deriveOperatorReadout(safety({ vSafe: 10, actualSpeed: 2 }), vehicle()).action).toBe(
      "NORMAL",
    );
    // Exactly at the reused 0.88 band boundary.
    expect(
      deriveOperatorReadout(safety({ vSafe: 10, actualSpeed: 10 * CAUTION_RATIO }), vehicle())
        .action,
    ).toBe("CAUTION");
  });

  it("treats a zero actual speed as a real value, not as missing", () => {
    const readout = deriveOperatorReadout(safety({ vSafe: 10, actualSpeed: 0 }), vehicle());
    expect(readout.action).toBe("NORMAL");
    expect(readout.actualSpeedMps).toBe(0);
  });
});

describe("P8 operator action — reason wording", () => {
  it("maps supplied constraints to operator wording", () => {
    expect(constraintText("v_stop")).toBe("STOPPING DISTANCE");
    expect(constraintText("v_curve")).toBe("CURVE LIMIT");
    expect(constraintText("v_mine")).toBe("MINE SPEED LIMIT");
    expect(constraintText("VISIBILITY")).toBe("FOG VISIBILITY");
    expect(constraintText("v_traction_ceiling")).toBe("TRACTION LIMIT");
  });

  it("never invents a cause", () => {
    expect(constraintText(null)).toBeNull();
    expect(constraintText(undefined)).toBeNull();
    expect(constraintText("UNKNOWN")).toBeNull();
    // Supplied but unrecognised: honest and generic, never a specific invented cause.
    expect(constraintText("SOMETHING_NEW")).toBe("SAFETY LIMIT ACTIVE");
  });
});

describe("P8 unit conversion", () => {
  it("preserves UNAVAILABLE rather than substituting a number", () => {
    expect(toKmh(null)).toBeNull();
    expect(toKmh(undefined)).toBeNull();
    expect(toKmh(Number.NaN)).toBeNull();
    expect(toKmh(0)).toBe(0);
    expect(toKmh(10)).toBeCloseTo(36);
  });
});
