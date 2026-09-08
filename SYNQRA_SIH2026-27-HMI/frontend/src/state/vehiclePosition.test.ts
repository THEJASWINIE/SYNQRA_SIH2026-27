/**
 * Vehicle position provider tests — geospatial Digital Twin prototype.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: LIVE never receives a coordinate. There is no GNSS
 * on this prototype, so the only honest live answer is UNAVAILABLE — and no code path,
 * fallback or default can turn a simulated position into a physical one.
 */

import { describe, expect, it } from "vitest";
import type { VehicleState } from "../contracts/domain";
import { bailadilaDeposit5, toDecimalExtent } from "./geoSite";
import {
  NO_PHYSICAL_POSITION_REASON,
  PhysicalVehiclePositionProvider,
  placeablePositions,
  positionsFor,
  providerForMode,
  ReplayVehiclePositionProvider,
  SimulatedVehiclePositionProvider,
  unplaceablePositions,
} from "./vehiclePosition";

const EXTENT = toDecimalExtent(bailadilaDeposit5().extent);

function vehicle(vehicleId: string): VehicleState {
  return {
    vehicleId,
    timestamp: "2026-01-01T00:00:00.000Z",
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: 0.72,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
  };
}

const FLEET: Record<string, VehicleState> = {
  TRUCK_01: vehicle("TRUCK_01"),
  TRUCK_02: vehicle("TRUCK_02"),
};

// ---------------------------------------------------------------------------
// LIVE / PHYSICAL
// ---------------------------------------------------------------------------

describe("LIVE never receives a position", () => {
  it("the physical provider returns UNAVAILABLE with a reason", () => {
    const result = new PhysicalVehiclePositionProvider().positionFor(vehicle("TRUCK_01"));
    expect(result.position).toBeNull();
    expect(result.provenance).toBe("UNAVAILABLE");
    expect(result.reason).toBe(NO_PHYSICAL_POSITION_REASON);
  });

  it("LIVE mode maps to the physical provider and to nothing else", () => {
    const provider = providerForMode("LIVE", EXTENT);
    expect(provider).toBeInstanceOf(PhysicalVehiclePositionProvider);
    expect(provider).not.toBeInstanceOf(SimulatedVehiclePositionProvider);
    expect(provider).not.toBeInstanceOf(ReplayVehiclePositionProvider);
  });

  it("NO vehicle gets a coordinate in LIVE, however many are supplied", () => {
    const positions = positionsFor(FLEET, providerForMode("LIVE", EXTENT));
    expect(positions).toHaveLength(2);
    for (const p of positions) {
      expect(p.position, p.vehicleId).toBeNull();
      expect(p.provenance, p.vehicleId).toBe("UNAVAILABLE");
    }
    expect(placeablePositions(positions)).toHaveLength(0);
    expect(unplaceablePositions(positions)).toHaveLength(2);
  });

  it("LIVE never reports a position as PHYSICAL — that would claim a measurement", () => {
    for (const p of positionsFor(FLEET, providerForMode("LIVE", EXTENT))) {
      expect(p.provenance).not.toBe("PHYSICAL");
      expect(p.provenance).not.toBe("SIMULATED");
    }
  });

  it("the physical provider is not given the extent, so it cannot produce a coordinate", () => {
    // Constructed with no arguments at all: there is nothing to place a vehicle inside.
    expect(new PhysicalVehiclePositionProvider().positionFor(vehicle("X")).position).toBeNull();
  });

  it("position is never derived from speed or RPM", () => {
    const fast = { ...vehicle("TRUCK_01"), speedMps: 25 };
    const stopped = { ...vehicle("TRUCK_01"), speedMps: 0 };
    const provider = new PhysicalVehiclePositionProvider();
    expect(provider.positionFor(fast).position).toBeNull();
    expect(provider.positionFor(stopped).position).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SIMULATION
// ---------------------------------------------------------------------------

describe("SIMULATION positions are marked SIMULATED", () => {
  const provider = providerForMode("MOCK", EXTENT);

  it("produces a coordinate inside the published extent", () => {
    const result = provider.positionFor(vehicle("TRUCK_01"));
    expect(result.position).not.toBeNull();
    const pos = result.position as { lon: number; lat: number };
    expect(pos.lon).toBeGreaterThanOrEqual(EXTENT.west);
    expect(pos.lon).toBeLessThanOrEqual(EXTENT.east);
    expect(pos.lat).toBeGreaterThanOrEqual(EXTENT.south);
    expect(pos.lat).toBeLessThanOrEqual(EXTENT.north);
  });

  it("EVERY simulated position says SIMULATED, never PHYSICAL", () => {
    for (const p of positionsFor(FLEET, provider)) {
      expect(p.provenance, p.vehicleId).toBe("SIMULATED");
      expect(p.provenance, p.vehicleId).not.toBe("PHYSICAL");
      expect(p.reason, p.vehicleId).toContain("Not a measurement");
    }
  });

  it("is deterministic — the same vehicle lands in the same place every run", () => {
    const a = provider.positionFor(vehicle("TRUCK_01")).position;
    const b = providerForMode("MOCK", EXTENT).positionFor(vehicle("TRUCK_01")).position;
    expect(a).toEqual(b);
  });

  it("different vehicles land in different places", () => {
    const a = provider.positionFor(vehicle("TRUCK_01")).position;
    const b = provider.positionFor(vehicle("TRUCK_02")).position;
    expect(a).not.toEqual(b);
  });
});

// ---------------------------------------------------------------------------
// REPLAY
// ---------------------------------------------------------------------------

describe("REPLAY positions are marked REPLAY", () => {
  const recorded = { TRUCK_01: { lon: 81.19, lat: 18.68 } };
  const provider = providerForMode("REPLAY", EXTENT, recorded);

  it("returns the recorded coordinate, labelled REPLAY", () => {
    const result = provider.positionFor(vehicle("TRUCK_01"));
    expect(result.position).toEqual({ lon: 81.19, lat: 18.68 });
    expect(result.provenance).toBe("REPLAY");
    expect(result.reason).toContain("Historical, not current");
  });

  it("never promotes a replayed position to PHYSICAL or SIMULATED", () => {
    const result = provider.positionFor(vehicle("TRUCK_01"));
    expect(result.provenance).not.toBe("PHYSICAL");
    expect(result.provenance).not.toBe("SIMULATED");
  });

  it("a vehicle absent from the recording is UNAVAILABLE, not invented", () => {
    const result = provider.positionFor(vehicle("TRUCK_02"));
    expect(result.position).toBeNull();
    expect(result.provenance).toBe("UNAVAILABLE");
    expect(result.reason).toContain("No recorded position");
  });

  it("REPLAY does not fall back to the simulated provider", () => {
    expect(providerForMode("REPLAY", EXTENT)).toBeInstanceOf(ReplayVehiclePositionProvider);
    // With an empty recording every vehicle is unavailable — never simulated.
    for (const p of positionsFor(FLEET, providerForMode("REPLAY", EXTENT))) {
      expect(p.provenance).toBe("UNAVAILABLE");
    }
  });
});

// ---------------------------------------------------------------------------
// isolation between modes
// ---------------------------------------------------------------------------

describe("the three modes stay isolated", () => {
  it("each mode selects a distinct provider kind", () => {
    expect(providerForMode("LIVE", EXTENT).kind).toBe("PHYSICAL");
    expect(providerForMode("MOCK", EXTENT).kind).toBe("SIMULATED");
    expect(providerForMode("REPLAY", EXTENT).kind).toBe("REPLAY");
  });

  it("switching MOCK -> LIVE removes every coordinate", () => {
    const simulated = positionsFor(FLEET, providerForMode("MOCK", EXTENT));
    expect(placeablePositions(simulated)).toHaveLength(2);

    const live = positionsFor(FLEET, providerForMode("LIVE", EXTENT));
    expect(placeablePositions(live)).toHaveLength(0);
  });

  it("positions come back in a stable order regardless of insertion order", () => {
    const reversed: Record<string, VehicleState> = {
      TRUCK_02: vehicle("TRUCK_02"),
      TRUCK_01: vehicle("TRUCK_01"),
    };
    const ids = positionsFor(reversed, providerForMode("MOCK", EXTENT)).map((p) => p.vehicleId);
    expect(ids).toEqual(["TRUCK_01", "TRUCK_02"]);
  });
});
