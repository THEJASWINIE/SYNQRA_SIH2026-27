/**
 * P6.1 — canonical Twin projection consumed by the React HMI.
 *
 * All payloads here are SIMULATED / REPLAYED shapes of the real backend projection.
 * No physical hardware was involved.
 */

import { describe, expect, it } from "vitest";
import type { RawTwinVehicle } from "../contracts/raw";
import { normalizeTwinVehicle } from "./normalize";
import { validateMessage } from "./validate";

const NOW_S = 1_788_000_000;

function field(
  value: unknown,
  over: Partial<{
    source: string;
    origin: string;
    quality: string;
    clock_domain: string;
    freshness: string;
    available: boolean;
    age_s: number | null;
    timestamp: number | null;
  }> = {},
) {
  return {
    value,
    timestamp: NOW_S,
    source: "HARDWARE",
    origin: "HARDWARE",
    quality: "GOOD",
    age_s: 0.5,
    available: true,
    clock_domain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...over,
  };
}

/** A hardware-only truck: measured rpm, derived speed, NO position/road/visibility. */
const HARDWARE_ONLY: RawTwinVehicle = {
  vehicle_id: "TRUCK_02",
  static: {},
  dynamic: {
    rpm: field(180),
    speed_mps: field(0.8011, { source: "DERIVED", origin: "HARDWARE" }),
    ax_mps2: field(0.1),
    speed_mps_pwm_derived: field(2.5, { source: "DERIVED", origin: "HARDWARE" }),
  },
  has_hardware_data: true,
};

/** A simulation-only truck: position/road/solver output, no measurements. */
const SIMULATION_ONLY: RawTwinVehicle = {
  vehicle_id: "TRUCK_01",
  static: {},
  dynamic: {
    position_s: field(40, {
      source: "SIMULATION",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
    road_id: field("ROAD_2", {
      source: "SIMULATION",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
    speed_mps: field(7.5, {
      source: "SIMULATION",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
    state: field("traveling", {
      source: "SIMULATION",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
    v_safe_mps: field(9.5, {
      source: "DERIVED",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
  },
  has_hardware_data: false,
};

/** A hybrid truck: measured rpm AND simulated position on the same vehicle. */
const HYBRID: RawTwinVehicle = {
  vehicle_id: "TRUCK_02",
  static: {},
  dynamic: {
    rpm: field(190),
    position_s: field(25, {
      source: "SIMULATION",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
    v_safe_mps: field(4.66, {
      source: "DERIVED",
      origin: "SIMULATION",
      clock_domain: "SIMULATION",
      timestamp: 120,
    }),
  },
  has_hardware_data: true,
};

describe("P6.1 canonical Twin projection — validation", () => {
  it("validates a well-formed twin_vehicle_update payload", () => {
    const result = validateMessage("TwinVehicle", HARDWARE_ONLY, new Date().toISOString());
    expect(result.ok).toBe(true);
  });

  it("rejects a malformed payload rather than accepting it", () => {
    for (const bad of [
      null,
      {},
      { vehicle_id: "TRUCK_02" },
      { vehicle_id: "TRUCK_02", dynamic: "not-an-object" },
      { vehicle_id: 42, dynamic: {} },
      { vehicle_id: "TRUCK_02", dynamic: { rpm: { value: 1 } } },
    ]) {
      const result = validateMessage("TwinVehicle", bad, new Date().toISOString());
      expect(result.ok).toBe(false);
    }
  });
});

describe("P6.1 canonical Twin projection — normalization", () => {
  it("keeps a hardware-only vehicle visible instead of dropping it", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);
    expect(v.vehicleId).toBe("TRUCK_02");
    expect(v.speedMps).toBeCloseTo(0.8011);
    expect(v.hasHardwareData).toBe(true);
  });

  it("represents unavailable fields as null, never as zero", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);

    expect(v.position.offsetM).toBeNull();
    expect(v.position.segmentId).toBeNull();
    expect(v.gradeRad).toBeNull();
    expect(v.frictionEst).toBeNull();
    expect(v.commConfidence).toBeNull();

    // The distinction that matters: unavailable is NOT zero.
    expect(v.position.offsetM).not.toBe(0);
    expect(v.commConfidence).not.toBe(0);
    expect(v.frictionEst).not.toEqual({ value: 0, sigma: 0 });
  });

  it("never invents map coordinates", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);
    expect(v.position.x).toBeNull();
    expect(v.position.y).toBeNull();
    // The old fabricated values must never reappear.
    expect(v.position.x).not.toBe(120);
    expect(v.position.y).not.toBe(50);
  });

  it("never invents friction or communication confidence", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);
    expect(v.frictionEst).toBeNull();
    expect(v.commConfidence).toBeNull();
  });

  it("preserves source, origin, clock_domain, freshness and age", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);
    const speed = v.provenance?.speed_mps;

    expect(speed).toBeDefined();
    expect(speed?.source).toBe("DERIVED");
    expect(speed?.origin).toBe("HARDWARE"); // derived FROM a real measurement
    expect(speed?.clockDomain).toBe("WALL_CLOCK");
    expect(speed?.freshness).toBe("CURRENT");
    expect(speed?.quality).toBe("GOOD");
    expect(speed?.ageS).toBeCloseTo(0.5);
    expect(speed?.available).toBe(true);

    expect(v.provenance?.rpm?.source).toBe("HARDWARE");
  });

  it("does not collapse DERIVED+HARDWARE into HARDWARE", () => {
    const v = normalizeTwinVehicle(HARDWARE_ONLY);
    expect(v.provenance?.speed_mps?.source).not.toBe("HARDWARE");
    expect(v.provenance?.speed_mps?.origin).toBe("HARDWARE");
  });

  it("keeps a simulation-only vehicle simulation-sourced", () => {
    const v = normalizeTwinVehicle(SIMULATION_ONLY);

    expect(v.position.offsetM).toBe(40);
    expect(v.position.segmentId).toBe("ROAD_2");
    expect(v.provenance?.position_s?.source).toBe("SIMULATION");
    expect(v.provenance?.position_s?.clockDomain).toBe("SIMULATION");
    expect(v.hasHardwareData).toBe(false);

    // A solver output for a simulated truck.
    expect(v.provenance?.v_safe_mps?.source).toBe("DERIVED");
    expect(v.provenance?.v_safe_mps?.origin).toBe("SIMULATION");
  });

  it("keeps both domains on a hybrid vehicle", () => {
    const v = normalizeTwinVehicle(HYBRID);

    expect(v.provenance?.rpm?.source).toBe("HARDWARE");
    expect(v.provenance?.rpm?.clockDomain).toBe("WALL_CLOCK");
    expect(v.provenance?.position_s?.source).toBe("SIMULATION");
    expect(v.provenance?.position_s?.clockDomain).toBe("SIMULATION");
    expect(v.position.offsetM).toBe(25);
  });

  it("consumes v_safe rather than recalculating it", () => {
    const v = normalizeTwinVehicle(HYBRID);
    // The value is carried through verbatim from the Twin.
    expect(v.provenance?.v_safe_mps?.value).toBe(4.66);
  });

  it("marks an unavailable field as unavailable in provenance", () => {
    const withUnavailable: RawTwinVehicle = {
      vehicle_id: "TRUCK_02",
      dynamic: {
        rpm: field(180),
        speed_mps: field(null, { available: false, source: "UNKNOWN", origin: "UNKNOWN" }),
      },
    };
    const v = normalizeTwinVehicle(withUnavailable);

    expect(v.speedMps).toBeNull();
    expect(v.provenance?.speed_mps?.available).toBe(false);
  });

  it("does not use Date.now() against a simulation timestamp", () => {
    const v = normalizeTwinVehicle(SIMULATION_ONLY);
    // Simulation timestamp 120 s -> 1970-01-01T00:02:00Z, not "now".
    expect(v.timestamp).toBe(new Date(120 * 1000).toISOString());
    expect(v.provenance?.position_s?.clockDomain).toBe("SIMULATION");
    expect(v.provenance?.position_s?.freshness).toBe("CURRENT");
  });
});
