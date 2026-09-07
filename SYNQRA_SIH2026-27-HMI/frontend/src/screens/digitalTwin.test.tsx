/**
 * S6 Digital Twin tests — Phase 7.
 *
 * `react-dom/server`, mounted against a real `AppStateStore` via `HmiContext` (M5D-B).
 * No jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: no coordinate is invented. A truck drawn at a
 * guessed point is worse than an absent one, because the operator cannot tell it was
 * guessed — so most of these tests are about what must be ABSENT, and about the
 * difference between "no Twin" and "a Twin that models nothing".
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ObservabilitySnapshot } from "../api/observabilityClient";
import { freshnessConfig } from "../config/freshness";
import type { MineTopology, RoadState, VehicleState } from "../contracts/domain";
import {
  environmentLine,
  HEADING_ABSENT_TEXT,
  legendEntries,
  nodeRows,
  positionLine,
  segmentRows,
  topologyLine,
  vehicleContextRows,
} from "../state/digitalTwin";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { DigitalTwin } from "./DigitalTwin";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const SCREEN_SOURCE = "src/screens/DigitalTwin.tsx";

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

async function screenSource(): Promise<string> {
  const fs = await import("node:fs");
  return fs.readFileSync(SCREEN_SOURCE, "utf-8");
}

/** Provenance exactly as the live backend supplies it for the simulated producer. */
const SIMULATED_PROVENANCE = {
  speed_mps: {
    value: 0.9797,
    timestamp: 1_788_681_152,
    source: "SIMULATION",
    origin: "SIMULATION",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
  },
  communication_state: {
    value: "HEALTHY",
    timestamp: 1_788_681_152,
    source: "SIMULATION",
    origin: "SIMULATION",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
  },
};

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_01",
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: 0.9797,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    provenance: SIMULATED_PROVENANCE,
    ...partial,
  };
}

/** A topology in the same shape the MOCK scenarios supply. */
function topology(partial: Partial<MineTopology> = {}): MineTopology {
  return {
    version: "test-topology-1",
    nodes: [
      { nodeId: "N-SHOVEL-1", kind: "SHOVEL", label: "Shovel 1", x: 0, y: 0 },
      { nodeId: "N-CRUSHER-1", kind: "CRUSHER", label: "Crusher 1", x: 600, y: 60 },
      { nodeId: "N-INT-1", kind: "INTERSECTION", label: "Intersection 1", x: 300, y: 30 },
    ],
    segments: [
      {
        segmentId: "S-SHOVEL-INT",
        fromNode: "N-SHOVEL-1",
        toNode: "N-INT-1",
        lengthM: 320,
        gradeRad: 0.04,
        bidirectional: true,
      },
      {
        segmentId: "S-INT-CRUSHER",
        fromNode: "N-INT-1",
        toNode: "N-CRUSHER-1",
        lengthM: 305,
        gradeRad: -0.02,
        bidirectional: false,
      },
    ],
    ...partial,
  };
}

function roadState(): RoadState {
  return {
    segmentId: "S-SHOVEL-INT",
    timestamp: T,
    visibility: { value: 15, sigma: 2 },
    friction: { value: 0.3, sigma: 0.05 },
    grade: 0.04,
    capacityVph: null,
    queue: null,
    utilization: null,
    surfaceState: "WET",
    roughness: null,
  };
}

function observability(partial: Partial<ObservabilitySnapshot> = {}): ObservabilitySnapshot {
  return {
    twinAttached: true,
    twinVehicleCount: 2,
    telemetryIngest: null,
    commandGateway: null,
    hardware: null,
    mode: null,
    ...partial,
  } as ObservabilitySnapshot;
}

interface MountOptions {
  vehicles?: Record<string, VehicleState>;
  topology?: MineTopology;
  road?: Record<string, RoadState>;
  vehicleId?: string | null;
  observability?: ObservabilitySnapshot | null;
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        vehicles: options.vehicles ?? { TRUCK_01: vehicle() },
        ...(options.topology ? { topology: options.topology } : {}),
        ...(options.road ? { road: options.road } : {}),
      },
    },
    T,
  );

  // Reach the observability slice the way production does — through the result shape.
  if (options.observability !== null) {
    store.setObservability({ kind: "ok", snapshot: options.observability ?? observability() }, T);
  }

  const value = testHmiContext({ store, freshness: CONFIG });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );

  return renderToString(wrap(<DigitalTwin vehicleId={options.vehicleId ?? null} />));
}

// ---------------------------------------------------------------------------
// 1, 2 — renders
// ---------------------------------------------------------------------------

describe("S6 renders (1, 2)", () => {
  it("1 — renders the digital twin screen", () => {
    const html = render();
    expect(html).toContain("Digital Twin");
    expect(html).toContain("Mine topology");
    expect(html).toContain("Selected vehicle");
    expect(html).toContain("Twin data status");
  });

  it("2 — renders Twin status from the supplied observability snapshot", () => {
    const html = render();
    expect(html).toContain("ATTACHED");
    expect(html).toContain("Vehicles in Twin");
    expect(html).toContain("Twin attachment is not hardware connectivity");
  });

  it("2b — an unqueried Twin is unavailable, not reported as attached", () => {
    const html = greyscale(render({ observability: null }));
    expect(html).toContain("--");
    expect(html).not.toContain("ATTACHED");
  });

  it("2c — Twin attachment is never conflated with hardware connectivity", () => {
    expect(render()).toContain("Not a count of physically connected vehicles");
  });
});

// ---------------------------------------------------------------------------
// 3, 4, 5, 6, 7, 15 — topology and legend
// ---------------------------------------------------------------------------

describe("topology (3, 4, 5, 6, 7, 15)", () => {
  it("3 — renders the supplied topology", () => {
    const html = render({ topology: topology() });
    expect(html).toContain("AVAILABLE");
    expect(html).toContain("3 node(s), 2 road(s)");
    expect(html).toContain("test-topology-1");
  });

  it("4 — no topology gives an intentional unavailable state, not a blank map", () => {
    const html = render(); // no topology — the current live condition
    expect(html).toContain("TOPOLOGY UNAVAILABLE");
    expect(html).toContain("NOT SUPPLIED");
    expect(html).toContain("NOTHING MODELLED");
    expect(html).toContain("None is synthesized");
  });

  it("4b — a supplied but empty topology is distinguished from no topology at all", () => {
    expect(topologyLine({ version: "v0", nodes: [], segments: [] }).value).toBe(
      "SUPPLIED BUT EMPTY",
    );
    expect(topologyLine(null).value).toBe("NOT SUPPLIED");
  });

  it("5 — nodes render with id, kind and label", () => {
    const html = render({ topology: topology() });
    expect(html).toContain("N-SHOVEL-1");
    expect(html).toContain("Shovel 1");
    expect(html).toContain("SHOVEL");
    expect(html).toContain("N-INT-1");
  });

  it("6 — roads render with their endpoints and geometry", () => {
    const html = render({ topology: topology() });
    expect(html).toContain("320 m");
    expect(html).toContain("0.040 rad");
    expect(html).toContain("bidirectional");
    expect(html).toContain("one-way");
  });

  it("7 — every supplied road id renders as text", () => {
    const html = render({ topology: topology() });
    expect(html).toContain("S-SHOVEL-INT");
    expect(html).toContain("S-INT-CRUSHER");
  });

  it("7b — node and road tables are empty when nothing was supplied", () => {
    expect(nodeRows(null)).toEqual([]);
    expect(segmentRows(null)).toEqual([]);
  });

  it("15 — the legend lists only entity kinds the data actually defines", () => {
    const entries = legendEntries(topology());
    expect(entries.map((e) => e.label)).toEqual(["CRUSHER", "INTERSECTION", "SHOVEL", "ROAD"]);
    expect(entries.map((e) => e.label)).not.toContain("SWITCHBACK");
    expect(legendEntries(null)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 8, 9, 10, 11 — selected-vehicle context
// ---------------------------------------------------------------------------

describe("selected vehicle (8, 9, 10, 11)", () => {
  it("8 — renders the selected vehicle and its available telemetry", () => {
    const html = render();
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("3.5"); // 0.9797 m/s -> km/h
    expect(html).toContain("HEALTHY");
  });

  it("8b — a supplied coordinate IS shown, labelled as topology units", () => {
    const placed = vehicle({
      position: { x: 120, y: 45, segmentId: "S-SHOVEL-INT", offsetM: null },
    });
    const rows = vehicleContextRows(placed, topology());
    const position = rows.find((r) => r.label === "Position");
    expect(position?.available).toBe(true);
    expect(position?.value).toBe("x 120.0, y 45.0");
    expect(position?.provenance).toContain("not geographic");
    expect(rows.find((r) => r.label === "Road segment")?.value).toBe("S-SHOVEL-INT");
  });

  it("9 — an unavailable position stays unavailable", () => {
    const html = greyscale(render());
    expect(html).toContain("LIVE VEHICLE POSITION UNAVAILABLE");
    expect(html).toContain("no topology supplied");
    const position = vehicleContextRows(vehicle(), null).find((r) => r.label === "Position");
    expect(position?.available).toBe(false);
    expect(position?.value).toBe("--");
  });

  it("10 — an unavailable road segment stays unavailable", () => {
    const road = vehicleContextRows(vehicle(), null).find((r) => r.label === "Road segment");
    expect(road?.available).toBe(false);
    expect(road?.value).toBe("--");
    expect(render()).toContain("no segment id supplied");
  });

  it("11 — heading is unavailable, and says why it can never be supplied", () => {
    const heading = vehicleContextRows(vehicle(), topology()).find((r) => r.label === "Heading");
    expect(heading?.available).toBe(false);
    expect(heading?.value).toBe("--");
    expect(render()).toContain(HEADING_ABSENT_TEXT);
  });

  it("11b — every context row is unavailable when no vehicle was supplied", () => {
    for (const row of vehicleContextRows(undefined, topology())) {
      expect(row.available, row.label).toBe(false);
      expect(row.value, row.label).toBe("--");
    }
  });
});

// ---------------------------------------------------------------------------
// 12, 13 — no invented coordinates
// ---------------------------------------------------------------------------

describe("no coordinate is invented (12, 13)", () => {
  it("12 — no vehicle marker exists when nothing could be placed", () => {
    const html = render({ topology: topology() });
    // MineMap draws a placed vehicle as <rect class="map-vehicle"> or a polygon.
    expect(html).not.toContain("map-vehicle");
    expect(html).toContain("NO VEHICLE POSITIONS AVAILABLE");
  });

  it("12b — the fleet position line names the missing input rather than guessing", () => {
    const store = new AppStateStore(T);
    store.applyPatch({ changes: { vehicles: { TRUCK_01: vehicle() } } }, T);
    const line = positionLine(store.getSnapshot());
    expect(line.state).toBe("UNAVAILABLE");
    expect(line.value).toBe("UNAVAILABLE");
    expect(line.detail).toContain("no topology supplied");
    expect(line.detail).toContain("No position is guessed");
  });

  it("13 — no GPS semantics are claimed anywhere on the screen", () => {
    const html = render({ topology: topology() });
    expect(html).not.toContain("GPS");
    expect(html).not.toContain("latitude");
    expect(html).not.toContain("longitude");
    expect(html).toContain("topology units, not geographic coordinates");
  });

  it("13b — the screen computes no coordinate of its own", async () => {
    const source = await screenSource();
    expect(source).not.toContain("Math.random");
    expect(source).not.toContain("Math.sin");
    expect(source).not.toContain("Math.cos");
    expect(source).not.toContain("Math.atan2");
  });
});

// ---------------------------------------------------------------------------
// 14, 15, 16, 19 — provenance and environment
// ---------------------------------------------------------------------------

describe("provenance and environment (14, 16, 19)", () => {
  it("14 — supplied provenance is preserved verbatim", () => {
    const html = render();
    expect(html).toContain("SIMULATION");
    expect(html).toContain("quality GOOD");
  });

  it("16 — no physical claim is made from simulated data", () => {
    const html = greyscale(render());
    expect(html).not.toContain("PHYSICAL");
    expect(html).not.toContain("HARDWARE");
  });

  it("16b — PHYSICAL appears only with hardware-origin provenance", () => {
    const hardware = vehicle({
      provenance: {
        speed_mps: { ...SIMULATED_PROVENANCE.speed_mps, source: "MEASURED", origin: "HARDWARE" },
      },
    });
    expect(render({ vehicles: { TRUCK_01: hardware } })).toContain("PHYSICAL");
  });

  it("19 — environment is unavailable unless a RoadState was supplied", () => {
    expect(environmentLine({}).value).toBe("--");
    expect(environmentLine({}).detail).toContain("No RoadState supplied");
    const html = greyscale(render());
    expect(html).toContain("Environment");
    expect(html).toContain("--");
  });

  it("19b — a supplied road segment is reported as available environment", () => {
    const line = environmentLine({ "S-SHOVEL-INT": roadState() });
    expect(line.value).toBe("AVAILABLE");
    expect(line.detail).toContain("1 road segment(s)");
    expect(render({ road: { "S-SHOVEL-INT": roadState() } })).toContain("AVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// 17, 18, 20, 21, 22 — architecture
// ---------------------------------------------------------------------------

describe("architecture (17, 18, 20, 21, 22)", () => {
  it("17 — the vehicle selector is driven by the shared vehicle state", () => {
    const html = render({
      vehicles: { TRUCK_01: vehicle(), TRUCK_02: vehicle({ vehicleId: "TRUCK_02" }) },
    });
    expect(html).toContain("Select vehicle");
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
  });

  it("17b — honours the vehicle the shell already selected", () => {
    const html = render({
      vehicles: { TRUCK_01: vehicle(), TRUCK_02: vehicle({ vehicleId: "TRUCK_02" }) },
      vehicleId: "TRUCK_02",
    });
    expect(html).toContain('value="TRUCK_02"');
  });

  it("18 — live mode fabricates no topology when the Twin is attached but empty", () => {
    const html = render({ observability: observability({ twinAttached: true }) });
    expect(html).toContain("ATTACHED");
    expect(html).toContain("NOT SUPPLIED");
    expect(html).toContain("attached and running; it simply models no topology yet");
    expect(html).not.toContain("N-SHOVEL-1");
  });

  it("20/21 — S6 opens no socket and starts no fetch loop of its own", async () => {
    const source = await screenSource();
    expect(source).not.toContain("fetch(");
    expect(source).not.toContain("WebSocket");
    expect(source).not.toContain("setInterval");
    expect(source).not.toContain("useEffect");
  });

  it("21b — the shared store is read, never duplicated", async () => {
    const source = await screenSource();
    expect(source).toContain("useAppState");
    // The only local state is the selected-vehicle id: one import, one call.
    expect((source.match(/useState/g) ?? []).length).toBe(2);
  });

  it("22 — MineMap is reused, not reimplemented", async () => {
    const source = await screenSource();
    expect(source).toContain("<MineMap state={state} />");
    expect(source).not.toContain("<svg");
    // No placement CALL of its own — the doc comment naturally names the reused path.
    expect(source).not.toContain("placeVehicles(");
  });
});
