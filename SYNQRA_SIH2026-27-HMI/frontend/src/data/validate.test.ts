/**
 * Validation tests — M2.
 * Covers required test categories 1, 2, 3, 14, 15.
 */

import { describe, expect, it } from "vitest";
import { MESSAGE_TYPES } from "../contracts/raw";
import { loadInvalid, loadValid } from "./fixtures";
import { validateMany, validateMessage } from "./validate";

const RECEIVED_AT = "2026-01-01T00:00:01.000Z";

describe("valid payloads (category 1)", () => {
  it.each(MESSAGE_TYPES)("accepts the %s fixture", (messageType) => {
    const result = validateMessage(messageType, loadValid(messageType), RECEIVED_AT);
    expect(result.ok).toBe(true);
  });

  it("covers all sixteen contract messages", () => {
    expect(MESSAGE_TYPES).toHaveLength(16);
  });
});

describe("invalid payloads (categories 2, 3)", () => {
  const fixtures = loadInvalid();

  it("has invalid fixtures to test against", () => {
    expect(fixtures.length).toBeGreaterThan(0);
  });

  it.each(fixtures.map((f) => [f.file, f] as const))("rejects %s", (_file, fixture) => {
    const result = validateMessage(fixture.messageType, fixture.payload, RECEIVED_AT);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.kind).toBe("VALIDATION");
    expect(result.failure.issues.length).toBeGreaterThan(0);
  });

  it("reports the offending field path for a missing required field", () => {
    const fixture = fixtures.find((f) => f.file === "SafetyState__missing_required_field.json");
    expect(fixture).toBeDefined();
    if (!fixture) return;
    const result = validateMessage("SafetyState", fixture.payload, RECEIVED_AT);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.issues.some((i) => i.path === "actual_speed")).toBe(true);
  });

  it("reports a nested field path", () => {
    const fixture = fixtures.find((f) => f.file === "VehicleState__invalid_nested_type.json");
    expect(fixture).toBeDefined();
    if (!fixture) return;
    const result = validateMessage("VehicleState", fixture.payload, RECEIVED_AT);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.issues.some((i) => i.path === "position.x")).toBe(true);
  });
});

describe("validation failure typing (category 14)", () => {
  it("carries the message type and receipt time", () => {
    const result = validateMessage("SafetyState", { nonsense: true }, RECEIVED_AT);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.messageType).toBe("SafetyState");
    expect(result.failure.receivedAt).toBe(RECEIVED_AT);
  });

  it("one bad item does not discard valid siblings in the batch", () => {
    const good = loadValid("SafetyState");
    const bad = { vehicle_id: "V-2" };
    const { valid, failures } = validateMany("SafetyState", [good, bad, good], RECEIVED_AT);
    expect(valid).toHaveLength(2);
    expect(failures).toHaveLength(1);
  });
});

describe("no unexpected throws across the data boundary (category 15)", () => {
  const hostile: unknown[] = [null, undefined, 42, "string", [], {}, { vehicle_id: 1 }, Number.NaN];

  it.each(MESSAGE_TYPES)("%s survives hostile input without throwing", (messageType) => {
    for (const payload of hostile) {
      expect(() => validateMessage(messageType, payload, RECEIVED_AT)).not.toThrow();
    }
  });
});
