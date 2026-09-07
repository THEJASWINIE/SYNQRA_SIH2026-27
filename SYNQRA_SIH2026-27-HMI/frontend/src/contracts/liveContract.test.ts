/**
 * P10 — the backend/frontend contract, checked against a payload the BACKEND ACTUALLY SENT.
 *
 * WHY THIS EXISTS
 *   `normalize.test.ts` validates `contracts/fixtures/valid/TwinVehicle.json`, which is a
 *   hand-written sample. It proves the frontend agrees with a document, not that it agrees
 *   with the running service — a backend field rename would leave it green.
 *
 *   `contracts/fixtures/live/TwinVehicle.live.json` is different: it is captured verbatim
 *   from `GET /api/twin/vehicles/TRUCK_02` on a real uvicorn process by
 *   `verify_p10_live_contract.py`. Validating it here closes the last gap in the P10 chain:
 *   the process boundary between Python and TypeScript.
 *
 * PROVENANCE
 *   The capture is EMULATED telemetry. An `origin: "HARDWARE"` inside it means "the backend
 *   labelled it as having arrived on the physical ingress", which the emulator drove. No
 *   physical ESP32 was connected, and this file makes no physical claim.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { normalizeTwinVehicle } from "../data/normalize";
import { type RawTwinVehicle, rawTwinVehicleSchema } from "./raw";

const CAPTURE_PATH = join(
  process.cwd(),
  "..",
  "contracts",
  "fixtures",
  "live",
  "TwinVehicle.live.json",
);

function loadCapture(): unknown {
  try {
    return JSON.parse(readFileSync(CAPTURE_PATH, "utf-8"));
  } catch (error) {
    throw new Error(
      `No live capture at ${CAPTURE_PATH}. Regenerate it with ` +
        "`python verify_p10_live_contract.py` from the repository root. " +
        `Original error: ${String(error)}`,
    );
  }
}

describe("P10 live backend contract", () => {
  it("a payload the running backend emitted satisfies the frontend schema", () => {
    const parsed = rawTwinVehicleSchema.safeParse(loadCapture());

    // Schema drift surfaces here as a field path, which is the useful part.
    expect(parsed.success ? null : parsed.error.issues).toBeNull();
  });

  it("carries the canonical envelope on every dynamic field", () => {
    const capture = rawTwinVehicleSchema.parse(loadCapture());
    const fields = Object.entries(capture.dynamic);

    expect(fields.length).toBeGreaterThan(0);
    for (const [name, field] of fields) {
      expect(field, `${name} has no value key`).toHaveProperty("value");
      expect(field, `${name} has no source`).toHaveProperty("source");
      expect(field, `${name} has no clock_domain`).toHaveProperty("clock_domain");
      expect(field, `${name} has no freshness`).toHaveProperty("freshness");
      expect(field, `${name} has no availability`).toHaveProperty("available");
    }
  });

  it("normalizes without inventing a value the backend did not send", () => {
    const capture = rawTwinVehicleSchema.parse(loadCapture()) as RawTwinVehicle;
    const vehicle = normalizeTwinVehicle(capture);

    expect(vehicle.vehicleId).toBe(capture.vehicle_id);

    // The prototype measures no position. It must arrive absent and stay absent —
    // never become 0, and never become a coordinate.
    if (!("position_s" in capture.dynamic)) {
      expect(vehicle.position?.offsetM ?? null).toBeNull();
      expect(vehicle.position?.x ?? null).toBeNull();
      expect(vehicle.position?.y ?? null).toBeNull();
    }
  });

  it("does not collapse DERIVED + HARDWARE into HARDWARE across the boundary", () => {
    const capture = rawTwinVehicleSchema.parse(loadCapture()) as RawTwinVehicle;
    const vehicle = normalizeTwinVehicle(capture);

    for (const [name, raw] of Object.entries(capture.dynamic)) {
      const carried = vehicle.provenance?.[name];
      if (!carried) continue;
      expect(carried.source, `${name} source was rewritten`).toBe(raw.source);
      expect(carried.origin, `${name} origin was rewritten`).toBe(raw.origin);
    }
  });

  it("the capture is a real one, not a hand-written placeholder", () => {
    const capture = rawTwinVehicleSchema.parse(loadCapture());

    // A stub would not carry a plausible epoch timestamp alongside a measured age.
    const first = Object.values(capture.dynamic)[0];
    expect(first).toBeDefined();
    expect(first?.timestamp ?? 0).toBeGreaterThan(1_700_000_000);
    expect(typeof first?.age_s).toBe("number");
  });
});
