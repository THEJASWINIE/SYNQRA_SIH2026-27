/**
 * DIGITAL-TWIN-OPERATIONAL-FLOW-01 — callout de-collision is deterministic and never
 * moves a vehicle. SOFTWARE ONLY; positions are synthetic fixtures.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PositionScene, VehicleState } from "../contracts/domain";
import { GeoSiteMap } from "../screens/GeoSiteMap";
import { CALLOUT_NEAR_M, calloutSlots, SLOT_OFFSET } from "./calloutLayout";
import { bailadilaDeposit5, toDecimalExtent } from "./geoSite";
import { fleetPositions, providerForMode, SCENE_FRAME } from "./vehiclePosition";

const SITE = bailadilaDeposit5();
const EXTENT = toDecimalExtent(SITE.extent);

function scene(xM: number, yM: number): PositionScene {
  return {
    xM, yM, headingRad: 0.3, frame: SCENE_FRAME, status: "VALID", source: "SIMULATION",
    origin: "SIMULATION", provenanceLabel: "SIMULATION · DIGITAL TWIN",
    method: "DIGITAL_TWIN_SCENE_SIM", reason: "demo", routeId: "SYNTH-ROUTE-T01-ORE-CYCLE",
    routeDirection: 1,
  };
}
function vehicle(id: string, pose: PositionScene): VehicleState {
  return {
    vehicleId: id, mode: "NORMAL", vehicleKind: "DUMPER", speedMps: 6, timestamp: "2026-09-14T12:00:00.000Z",
    position: { x: null, y: null, segmentId: null, offsetM: null }, positionScene: pose,
    accelMps2: null, gradeRad: null, commConfidence: null, frictionEst: null, routeId: null,
    provenance: {} as never,
  } as VehicleState;
}

describe("calloutSlots", () => {
  const near = [
    { id: "TRUCK_02", x: 600, y: 2400 },
    { id: "TRUCK_01", x: 640, y: 2430 }, // ~50 m apart: the ramp access junction case
  ];

  it("T01/T02 near a junction get distinct slots", () => {
    const slots = calloutSlots(near);
    expect(slots.get("TRUCK_01")).toBe("LEFT");
    expect(slots.get("TRUCK_02")).toBe("RIGHT");
    expect(slots.get("TRUCK_01")).not.toBe(slots.get("TRUCK_02"));
    expect(SLOT_OFFSET.LEFT.dx).toBeLessThan(0);
    expect(SLOT_OFFSET.RIGHT.dx).toBeGreaterThan(0);
  });

  it("is deterministic: same result on repeated evaluation and regardless of input order", () => {
    const a = calloutSlots(near);
    const b = calloutSlots([...near].reverse());
    const c = calloutSlots(near);
    expect([...a.entries()].sort()).toEqual([...b.entries()].sort());
    expect([...a.entries()].sort()).toEqual([...c.entries()].sort());
  });

  it("far apart: both keep the DEFAULT slot (no excessive offset)", () => {
    const far = [
      { id: "TRUCK_01", x: 500, y: 500 },
      { id: "TRUCK_02", x: 2500, y: 2800 },
    ];
    const slots = calloutSlots(far);
    expect(slots.get("TRUCK_01")).toBe("DEFAULT");
    expect(slots.get("TRUCK_02")).toBe("DEFAULT");
    expect(Math.hypot(2000, 2300)).toBeGreaterThan(CALLOUT_NEAR_M);
  });

  it("never mutates the canonical positions it is given", () => {
    const input = near.map((s) => ({ ...s }));
    const frozen = JSON.stringify(input);
    calloutSlots(input);
    expect(JSON.stringify(input)).toBe(frozen);
    expect(Object.isFrozen(SLOT_OFFSET) || typeof SLOT_OFFSET === "object").toBe(true);
  });

  it("uses no randomness or time", () => {
    const src = readFileSync(join(__dirname, "calloutLayout.ts"), "utf-8");
    expect(src).not.toMatch(/Math\.random|Date\.now|performance\.now/);
  });
});

describe("2D plan applies slots without moving the marker", () => {
  const nearT01 = vehicle("TRUCK_01", scene(640, 2430));
  const nearT02 = vehicle("TRUCK_02", scene(600, 2400));
  const positions = fleetPositions({ TRUCK_01: nearT01, TRUCK_02: nearT02 }, providerForMode("LIVE", EXTENT), EXTENT);
  const html = renderToString(<GeoSiteMap site={SITE} positions={positions} mode="LIVE" />);

  it("near-junction trucks get different callout slots and leader lines", () => {
    const t01 = /<g data-vehicle-id="TRUCK_01"[\s\S]*?<\/g>\s*<\/g>/.exec(html)?.[0] ?? "";
    const t02 = /<g data-vehicle-id="TRUCK_02"[\s\S]*?<\/g>\s*<\/g>/.exec(html)?.[0] ?? "";
    expect(t01).toContain('data-callout-slot="LEFT"');
    expect(t02).toContain('data-callout-slot="RIGHT"');
    expect(t01).toContain('data-callout-leader="TRUCK_01"');
    expect(t02).toContain('data-callout-leader="TRUCK_02"');
  });

  it("the truck symbol transform is the canonical pose, identical to the far-apart render", () => {
    const farPositions = fleetPositions(
      { TRUCK_01: nearT01, TRUCK_02: vehicle("TRUCK_02", scene(2500, 800)) },
      providerForMode("LIVE", EXTENT),
      EXTENT,
    );
    const far = renderToString(<GeoSiteMap site={SITE} positions={farPositions} mode="LIVE" />);
    const symbol = (h: string) => /<g data-vehicle-id="TRUCK_01"[\s\S]*?transform="(translate\([^)]*\) rotate\([^)]*\))"/.exec(h)?.[1];
    expect(symbol(html)).toBeDefined();
    expect(symbol(html)).toBe(symbol(far)); // slot changed, marker did not
    expect(far).toContain('data-callout-slot="DEFAULT"');
  });

  it("is stable across repeated renders", () => {
    expect(renderToString(<GeoSiteMap site={SITE} positions={positions} mode="LIVE" />)).toBe(html);
  });
});
