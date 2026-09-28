/**
 * Normalization tests — M2.
 * Covers required test categories 4, 6, 7, 16 (TS half of parity).
 */

import { describe, expect, it } from "vitest";
import type { MessageType } from "../contracts/raw";
import { loadUnknownEnum, loadValid } from "./fixtures";
import {
  normalizeAlert,
  normalizeArrivalPlan,
  normalizeBottleneckState,
  normalizeCvResult,
  normalizeDispatchCommand,
  normalizeEventRecord,
  normalizeHealth,
  normalizeKpiSnapshot,
  normalizeMineTopology,
  normalizeRoadState,
  normalizeSafetyState,
  normalizeSlotState,
  normalizeSystemHealth,
  normalizeTwinSafety,
  normalizeTwinVehicle,
  normalizeVehicleState,
  normalizeVisibilityForecast,
} from "./normalize";
import { validateMessage } from "./validate";

const RECEIVED_AT = "2026-01-01T00:00:01.000Z";

/** Validate then normalize, the only permitted order. */
// biome-ignore lint/suspicious/noExplicitAny: test harness dispatches across 15 schemas
const NORMALIZERS: Record<MessageType, (raw: any) => unknown> = {
  TwinVehicle: normalizeTwinVehicle,
  TwinSafety: normalizeTwinSafety,
  VehicleState: normalizeVehicleState,
  SafetyState: normalizeSafetyState,
  RoadState: normalizeRoadState,
  VisibilityForecast: normalizeVisibilityForecast,
  BottleneckState: normalizeBottleneckState,
  DispatchCommand: normalizeDispatchCommand,
  SlotState: normalizeSlotState,
  ArrivalPlan: normalizeArrivalPlan,
  Alert: normalizeAlert,
  EventRecord: normalizeEventRecord,
  Health: normalizeHealth,
  SystemHealth: normalizeSystemHealth,
  KpiSnapshot: normalizeKpiSnapshot,
  CVResult: normalizeCvResult,
  MineTopology: normalizeMineTopology,
};

function validateAndNormalize(messageType: MessageType, payload: unknown): unknown {
  const result = validateMessage(messageType, payload, RECEIVED_AT);
  expect(result.ok).toBe(true);
  if (!result.ok) throw new Error("fixture failed validation");
  return NORMALIZERS[messageType](result.value);
}

describe("normalization round-trip (category 6)", () => {
  const types = Object.keys(NORMALIZERS) as MessageType[];

  it.each(types)("normalizes %s without throwing", (messageType) => {
    expect(() => validateAndNormalize(messageType, loadValid(messageType))).not.toThrow();
  });

  it("converts snake_case wire fields to camelCase domain fields", () => {
    const v = validateAndNormalize("VehicleState", loadValid("VehicleState")) as Record<
      string,
      unknown
    >;
    expect(v.vehicleId).toBe("V-1");
    expect(v.speedMps).toBe(0);
    expect(v).not.toHaveProperty("vehicle_id");
    expect(v).not.toHaveProperty("speed_mps");
  });

  it("preserves nested structure", () => {
    const v = validateAndNormalize("VehicleState", loadValid("VehicleState")) as {
      position: Record<string, unknown>;
    };
    expect(v.position.segmentId).toBe("S-1");
    expect(v.position).not.toHaveProperty("segment_id");
  });

  it("copies supplied Task 2 values verbatim without computing them", () => {
    const s = validateAndNormalize("SafetyState", loadValid("SafetyState")) as Record<
      string,
      unknown
    >;
    // Values come straight from the fixture; nothing is derived.
    expect(s.vSafe).toBe(0);
    expect(s.hSafe).toBe(0);
    expect(s.headwayCurrent).toBeNull();
  });

  it("leaves unsupplied optional values null rather than substituting 0", () => {
    const k = validateAndNormalize("KpiSnapshot", loadValid("KpiSnapshot")) as Record<
      string,
      unknown
    >;
    expect(k.throughputTph).toBeNull();
    expect(k.cycleTimeS).toBeNull();
    expect(k.throughputTph).not.toBe(0);
  });
});

describe("unknown enum handling (category 4)", () => {
  const fixtures = loadUnknownEnum();

  it("has unknown-enum fixtures", () => {
    expect(fixtures.length).toBeGreaterThan(0);
  });

  it.each(fixtures.map((f) => [f.file, f] as const))(
    "%s is accepted, not rejected",
    (_file, fixture) => {
      const result = validateMessage(fixture.messageType, fixture.payload, RECEIVED_AT);
      expect(result.ok).toBe(true);
    },
  );

  it("maps an unrecognised vehicle mode to UNKNOWN rather than dropping it", () => {
    const fixture = fixtures.find((f) => f.file === "VehicleState__unknown_enum.json");
    expect(fixture).toBeDefined();
    if (!fixture) return;
    const v = validateAndNormalize("VehicleState", fixture.payload) as Record<string, unknown>;
    expect(v.mode).toBe("UNKNOWN");
    // The rest of the message survives — an unknown enum must not discard sibling data.
    expect(v.vehicleId).toBe("V-1");
  });

  it("maps an unrecognised risk level to UNKNOWN", () => {
    const fixture = fixtures.find((f) => f.file === "SafetyState__unknown_enum.json");
    if (!fixture) throw new Error("fixture missing");
    const s = validateAndNormalize("SafetyState", fixture.payload) as Record<string, unknown>;
    expect(s.riskLevel).toBe("UNKNOWN");
  });

  it("maps an unrecognised slot status to UNKNOWN", () => {
    const fixture = fixtures.find((f) => f.file === "SlotState__unknown_enum.json");
    if (!fixture) throw new Error("fixture missing");
    const s = validateAndNormalize("SlotState", fixture.payload) as Record<string, unknown>;
    expect(s.status).toBe("UNKNOWN");
  });
});

describe("source metadata preservation (category 7)", () => {
  it("keeps the original timestamp string untouched", () => {
    const s = validateAndNormalize("SafetyState", loadValid("SafetyState")) as Record<
      string,
      unknown
    >;
    expect(s.timestamp).toBe("2026-01-01T00:00:00.000Z");
  });

  it("keeps identifiers untouched", () => {
    const c = validateAndNormalize("CVResult", loadValid("CVResult")) as Record<string, unknown>;
    expect(c.sourceId).toBe("CAM-1");
  });
});
