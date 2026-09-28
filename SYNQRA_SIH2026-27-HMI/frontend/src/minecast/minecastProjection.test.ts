/**
 * Mine-Cast projection — anti-fabrication tests.
 *
 * A spatial view is persuasive in a way a table is not: a truck drawn on a mine map looks
 * measured whether or not anything measured it. These tests hold that door shut. Each one
 * feeds the projection a state the prototype can genuinely be in, and asserts it does NOT
 * invent its way out of it.
 *
 * SOFTWARE ONLY. No hardware, no network, no DOM.
 */

import { describe, expect, it } from "vitest";

import type { AppState } from "../contracts/appState";
import type { VehicleState } from "../contracts/domain";
import {
  DISPLAY_LABELS,
  displayLabelFor,
  EXTENT_CAVEAT,
  EXTENT_LABEL,
  extentText,
  LAYERS,
  MINECAST_SITE,
  metresText,
  positionOf,
  projectMineCast,
  projectMineCastVehicle,
  speedText,
} from "./minecastProjection";

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const ISO = "2026-09-10T12:00:00Z";

function vehicle(id: string, overrides: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps: 4.2,
    position: { x: 0, y: 0, segmentId: null, offsetM: 0 },
    accelMps2: 0,
    gradeRad: 0,
    commConfidence: 1,
    frictionEst: null,
    routeId: null,
    timestamp: ISO,
    ...overrides,
  } as VehicleState;
}

function appState(
  vehicles: Record<string, VehicleState>,
  overrides: Partial<AppState> = {},
): AppState {
  return {
    connection: {
      status: "CONNECTED",
      provider: "LIVE",
      scenarioName: null,
      lastMessageAt: ISO,
      error: null,
    },
    clock: { now: ISO, replayPosition: null },
    vehicles,
    safety: {},
    road: {},
    forecasts: {},
    bottlenecks: {},
    arrivals: {},
    slots: {},
    dispatch: {},
    alerts: [],
    events: [],
    health: null,
    kpis: null,
    cv: null,
    commands: [],
    observability: { status: "CURRENT", data: null, fetchedAt: ISO, error: null },
    topology: null,
    ...overrides,
  } as AppState;
}

// ---------------------------------------------------------------------------
// 3 + 4. canonical ids are preserved; display labels are T01/T02
// ---------------------------------------------------------------------------

describe("identity", () => {
  it("labels the trucks T01 and T02 for display", () => {
    expect(displayLabelFor("TRUCK_01")).toBe("T01");
    expect(displayLabelFor("TRUCK_02")).toBe("T02");
    expect(DISPLAY_LABELS.TRUCK_01).toBe("T01");
    expect(DISPLAY_LABELS.TRUCK_02).toBe("T02");
  });

  it("carries the CANONICAL id alongside every display label", () => {
    const state = appState({ TRUCK_01: vehicle("TRUCK_01"), TRUCK_02: vehicle("TRUCK_02") });
    const projected = projectMineCast(state);

    expect(projected.vehicles.map((v) => v.canonicalVehicleId)).toEqual(["TRUCK_01", "TRUCK_02"]);
    expect(projected.vehicles.map((v) => v.displayId)).toEqual(["T01", "T02"]);
  });

  it("does not rename a vehicle the labels do not cover", () => {
    // A short label is an addition, never a substitution. An unknown id reads as itself.
    expect(displayLabelFor("SHOVEL_09")).toBe("SHOVEL_09");
  });
});

// ---------------------------------------------------------------------------
// 2. T01 and T02 remain separate
// ---------------------------------------------------------------------------

describe("vehicle isolation", () => {
  it("never presents one truck's telemetry as the other's", () => {
    const state = appState({
      TRUCK_01: vehicle("TRUCK_01", { speedMps: 12.5 }),
      TRUCK_02: vehicle("TRUCK_02", { speedMps: 3.1 }),
    });

    const t01 = projectMineCastVehicle(state, "TRUCK_01", "LIVE");
    const t02 = projectMineCastVehicle(state, "TRUCK_02", "LIVE");

    expect(t01.speedMps).toBe(12.5);
    expect(t02.speedMps).toBe(3.1);
    expect(t01.canonicalVehicleId).toBe("TRUCK_01");
    expect(t02.canonicalVehicleId).toBe("TRUCK_02");
  });

  it("keeps the peer in its own field, never as the vehicle's own state", () => {
    const state = appState({
      TRUCK_01: vehicle("TRUCK_01", { speedMps: 12.5 }),
      TRUCK_02: vehicle("TRUCK_02", { speedMps: 3.1 }),
    });

    const t01 = projectMineCastVehicle(state, "TRUCK_01", "LIVE");
    expect(t01.peerVehicleId).toBe("TRUCK_02");
    expect(t01.peerDisplayId).toBe("T02");
    expect(t01.peerPresent).toBe(true);
    // The peer's speed is NOT reachable as this vehicle's speed.
    expect(t01.speedMps).not.toBe(3.1);
  });

  it("shows a silent truck as UNAVAILABLE rather than dropping it from the fleet", () => {
    // TRUCK_02 stops reporting. A vehicle vanishing off the view is the failure an
    // operator must never be shown, so the fleet is enumerated from configuration.
    const state = appState({ TRUCK_01: vehicle("TRUCK_01") });
    const projected = projectMineCast(state);

    expect(projected.fleetTotal).toBe(2);
    const t02 = projected.vehicles.find((v) => v.canonicalVehicleId === "TRUCK_02");
    expect(t02).toBeDefined();
    expect(t02?.present).toBe(false);
    expect(t02?.availability).toBe("UNAVAILABLE");
  });

  it("a vehicle absent from the Twin has no invented speed", () => {
    const projected = projectMineCastVehicle(appState({}), "TRUCK_01", "LIVE");
    expect(projected.speedMps).toBeNull();
    expect(projected.speedMps).not.toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 5 + 6. missing position stays unavailable; no fake GNSS
// ---------------------------------------------------------------------------

describe("position", () => {
  it("reports UNAVAILABLE when nothing supplied a position", () => {
    const position = positionOf(vehicle("TRUCK_01"));
    expect(position.kind).toBe("UNAVAILABLE");
    expect(position.available).toBe(false);
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.xM).toBeNull();
    expect(position.yM).toBeNull();
  });

  it("invents no coordinate for a vehicle that has none", () => {
    const state = appState({ TRUCK_01: vehicle("TRUCK_01"), TRUCK_02: vehicle("TRUCK_02") });
    const projected = projectMineCast(state);

    expect(projected.placeableCount).toBe(0);
    expect(projected.noPhysicalPositioning).toBe(true);
    for (const v of projected.vehicles) {
      expect(v.position.available).toBe(false);
    }
  });

  it("reports a wheel+IMU pose as LOCAL_ODOMETRY and PHYSICAL_DERIVED, never as GNSS", () => {
    const withOdom = vehicle("TRUCK_01", {
      positionOdom: {
        xM: 12.4,
        yM: -3.2,
        headingRad: 0.42,
        distanceM: 88.1,
        timestamp: 1,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "PHYSICAL_DERIVED",
        method: "WHEEL_IMU_ODOMETRY",
        status: "VALID",
        originType: "LOCAL_ODOMETRY",
      },
    } as Partial<VehicleState>);

    const position = positionOf(withOdom);
    expect(position.kind).toBe("LOCAL_ODOMETRY");
    expect(position.provenance).toBe("DERIVED");
    expect(position.method).toBe("WHEEL_IMU_ODOMETRY");
    expect(position.method).not.toBe("GNSS");
    // A local pose is metres from an origin. It is never widened into a lat/lon.
    expect(position.xM).toBe(12.4);
    expect(position.yM).toBe(-3.2);
  });

  it("does not turn a local odometry pose into a geographic position", () => {
    const withOdom = vehicle("TRUCK_01", {
      positionOdom: {
        xM: 5,
        yM: 5,
        headingRad: 0,
        distanceM: 10,
        timestamp: 1,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "PHYSICAL_DERIVED",
        method: "WHEEL_IMU_ODOMETRY",
        status: "VALID",
        originType: "LOCAL_ODOMETRY",
      },
    } as Partial<VehicleState>);

    const position = positionOf(withOdom);
    expect(position.kind).not.toBe("GEOGRAPHIC");
    // There is no latitude or longitude field on the projected position at all.
    expect(Object.keys(position)).not.toContain("latitude");
    expect(Object.keys(position)).not.toContain("longitude");
  });

  it("keeps an invalid odometry status unavailable", () => {
    const stalled = vehicle("TRUCK_01", {
      positionOdom: {
        xM: null,
        yM: null,
        headingRad: null,
        distanceM: null,
        timestamp: null,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "UNAVAILABLE",
        method: "WHEEL_IMU_ODOMETRY",
        status: "UNAVAILABLE",
        originType: "NONE",
        reason: "TRUCK_02 odometry is not supported",
      },
    } as Partial<VehicleState>);

    const position = positionOf(stalled);
    expect(position.available).toBe(false);
    expect(position.kind).toBe("UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// 11. synthetic data stays synthetic
// ---------------------------------------------------------------------------

describe("synthetic provenance is never promoted", () => {
  it("keeps a software-only GNSS fix labelled SOFTWARE_TEST", () => {
    const synthetic = vehicle("TRUCK_01", {
      positionGnss: {
        latitude: 18.68,
        longitude: 81.19,
        status: "VALID",
        origin: "SOFTWARE_ONLY",
      },
    } as Partial<VehicleState>);

    const position = positionOf(synthetic);
    expect(position.kind).toBe("GEOGRAPHIC");
    expect(position.provenance).toBe("SOFTWARE_TEST");
    expect(position.provenance).not.toBe("HARDWARE");
    expect(position.method).toBe("SYNTHETIC_GNSS");
    expect(position.reason).toContain("SYNTHETIC GNSS");
  });

  it("does not count a synthetic fix as physical positioning", () => {
    const synthetic = vehicle("TRUCK_01", {
      positionGnss: {
        latitude: 18.68,
        longitude: 81.19,
        status: "VALID",
        origin: "SOFTWARE_ONLY_SYNTHETIC",
      },
    } as Partial<VehicleState>);

    const projected = projectMineCast(appState({ TRUCK_01: synthetic }));
    expect(projected.noPhysicalPositioning).toBe(true);
  });

  it("marks every invented mine geometry layer SYNTHETIC_FOR_DEMO", () => {
    const invented = ["PIT", "BENCHES", "HAUL_ROADS", "RAMPS", "MINE_ZONES", "TERRAIN"];
    for (const id of invented) {
      const layer = LAYERS.find((candidate) => candidate.id === id);
      expect(layer, id).toBeDefined();
      expect(layer?.provenance, id).toBe("SYNTHETIC_FOR_DEMO");
    }
  });

  it("treats an unrecognised provenance label as UNAVAILABLE, never HARDWARE", () => {
    const odd = vehicle("TRUCK_01", {
      positionOdom: {
        xM: 1,
        yM: 1,
        headingRad: 0,
        distanceM: 1,
        timestamp: 1,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "SOMETHING_NOBODY_DEFINED",
        method: "WHEEL_IMU_ODOMETRY",
        status: "VALID",
        originType: "LOCAL_ODOMETRY",
      },
    } as Partial<VehicleState>);

    expect(positionOf(odd).provenance).toBe("UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// 7 + 8. V2V needs measured LoRa evidence; V2I is unavailable in LIVE
// ---------------------------------------------------------------------------

describe("communications", () => {
  it("does not report V2V connected without measured LoRa evidence", () => {
    // Both trucks present and reporting over Wi-Fi. That is not V2V evidence.
    const state = appState({
      TRUCK_01: vehicle("TRUCK_01", {
        provenance: {
          wifi_rssi_dbm: {
            value: -58,
            timestamp: 1,
            source: "HARDWARE",
            origin: "HARDWARE",
            quality: "GOOD",
            ageS: 0,
            available: true,
            clockDomain: "DEVICE",
            freshness: "CURRENT",
          },
          telemetry_transport: {
            value: "DIRECT_WIFI",
            timestamp: 1,
            source: "CONFIGURED",
            origin: "CONFIGURED",
            quality: "GOOD",
            ageS: 0,
            available: true,
            clockDomain: "DEVICE",
            freshness: "CURRENT",
          },
        },
      } as Partial<VehicleState>),
      TRUCK_02: vehicle("TRUCK_02"),
    });

    const t01 = projectMineCastVehicle(state, "TRUCK_01", "LIVE");
    expect(t01.peerPresent).toBe(true);
    expect(t01.v2v.state).toBe("UNAVAILABLE");
    expect(t01.v2v.state).not.toBe("CONNECTED");
  });

  it("never lets a Wi-Fi RSSI appear as a LoRa metric", () => {
    const state = appState({
      TRUCK_01: vehicle("TRUCK_01", {
        provenance: {
          wifi_rssi_dbm: {
            value: -58,
            timestamp: 1,
            source: "HARDWARE",
            origin: "HARDWARE",
            quality: "GOOD",
            ageS: 0,
            available: true,
            clockDomain: "DEVICE",
            freshness: "CURRENT",
          },
        },
      } as Partial<VehicleState>),
    });

    const t01 = projectMineCastVehicle(state, "TRUCK_01", "LIVE");
    for (const metric of t01.v2v.metrics) {
      expect(metric.label).toContain("LoRa");
      expect(metric.available, metric.label).toBe(false);
      expect(metric.value).not.toBe("-58");
    }
  });

  it("reports V2I UNAVAILABLE in LIVE mode", () => {
    const t01 = projectMineCastVehicle(appState({}), "TRUCK_01", "LIVE");
    expect(t01.v2i.state).toBe("UNAVAILABLE");
    expect(t01.v2i.reason).toContain("No physical roadside infrastructure");
  });

  it("labels a simulated V2I as simulated, and still not connected", () => {
    const t01 = projectMineCastVehicle(appState({}), "TRUCK_01", "MOCK");
    expect(t01.v2i.state).toBe("UNAVAILABLE");
    expect(t01.v2i.bearer).toContain("SIMULATED");
  });
});

// ---------------------------------------------------------------------------
// safety values are supplied, never computed
// ---------------------------------------------------------------------------

describe("safety", () => {
  it("reports UNAVAILABLE when the safety subsystem supplied nothing", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_01: vehicle("TRUCK_01") }),
      "TRUCK_01",
      "LIVE",
    );

    expect(projected.safety.unavailable).toBe(true);
    expect(projected.safety.vSafeMps).toBeNull();
    expect(projected.safety.hSafeM).toBeNull();
    expect(projected.safety.riskLevel).toBeNull();
    // Absent safety must never read as a reassuring value.
    expect(projected.safety.vSafeMps).not.toBe(0);
    expect(projected.safety.riskLevel).not.toBe("LOW");
  });
});

// ---------------------------------------------------------------------------
// staleness
// ---------------------------------------------------------------------------

describe("freshness", () => {
  it("does not call the feed LIVE while a vehicle is stale", () => {
    const stale = vehicle("TRUCK_01", {
      provenance: {
        received_at: {
          value: 1,
          timestamp: 1,
          source: "HARDWARE",
          origin: "HARDWARE",
          quality: "STALE",
          ageS: 900,
          available: true,
          clockDomain: "DEVICE",
          freshness: "STALE",
        },
      },
    } as Partial<VehicleState>);

    const projected = projectMineCast(appState({ TRUCK_01: stale, TRUCK_02: vehicle("TRUCK_02") }));
    expect(projected.feedState).not.toBe("LIVE");
  });

  it("labels a replay feed REPLAY, never LIVE", () => {
    const state = appState(
      { TRUCK_01: vehicle("TRUCK_01") },
      {
        connection: {
          status: "CONNECTED",
          provider: "REPLAY",
          scenarioName: "Replay — session",
          lastMessageAt: ISO,
          error: null,
        },
      },
    );

    expect(projectMineCast(state).feedState).toBe("REPLAY");
  });

  it("reports OFFLINE when the feed is disconnected", () => {
    const state = appState(
      { TRUCK_01: vehicle("TRUCK_01") },
      {
        connection: {
          status: "DISCONNECTED",
          provider: "LIVE",
          scenarioName: null,
          lastMessageAt: null,
          error: "socket closed",
        },
      },
    );

    expect(projectMineCast(state).feedState).toBe("OFFLINE");
  });
});

// ---------------------------------------------------------------------------
// the published extent
// ---------------------------------------------------------------------------

describe("published coordinate extent", () => {
  it("labels the extent, and states it is not a lease boundary", () => {
    expect(MINECAST_SITE.extentLabel).toBe(EXTENT_LABEL);
    expect(MINECAST_SITE.extentCaveat).toBe(EXTENT_CAVEAT);
    expect(EXTENT_LABEL).toBe("PUBLISHED COORDINATE EXTENT");
    expect(EXTENT_CAVEAT).toBe("NOT A LEASE BOUNDARY");
  });

  it("never calls the extent a boundary or a polygon", () => {
    const words = `${MINECAST_SITE.extentLabel} ${MINECAST_SITE.sourceDescription}`.toUpperCase();
    expect(words).not.toContain("LEASE BOUNDARY");
    expect(words).not.toContain("POLYGON");
  });

  it("records the datum as unverified", () => {
    expect(MINECAST_SITE.coordinateReference).toBe("ASSUMED_WGS84_UNVERIFIED");
  });

  it("carries the verified site identity and published area", () => {
    expect(MINECAST_SITE.operator).toBe("NMDC Limited");
    expect(MINECAST_SITE.name).toContain("Deposit-5");
    expect(MINECAST_SITE.publishedAreaHa).toBe(540.05);
    expect(MINECAST_SITE.sourceFileNo).toBe("J-11015/261/2007-IA.II(M)");
  });

  it("renders the four extrema as DMS, not as a coordinate list", () => {
    const extent = extentText();
    expect(extent.north).toContain("18°");
    expect(extent.south).toContain("18°");
    expect(extent.east).toContain("81°");
    expect(extent.west).toContain("81°");
  });
});

// ---------------------------------------------------------------------------
// layer honesty
// ---------------------------------------------------------------------------

describe("layer catalogue", () => {
  it("declares exactly the layers a renderer exists for", () => {
    // Pass 2 built the terrain, the pit and the benches; Pass 3B added the corridor
    // layers; MINECAST-01 added VEHICLES, drawn from the canonical Twin scene position.
    // MINE-ROUTES-02 added MINE_ZONES (working area, stockpile, dump) and ROUTES (route
    // labels). Everything else - orthophoto, safety, V2V, V2I - still has no renderer
    // and must still say so rather than offering a switch that draws nothing.
    const drawn = [
      "TERRAIN",
      "PUBLISHED_EXTENT",
      "PIT",
      "BENCHES",
      "HAUL_ROADS",
      "RAMPS",
      "MINE_ZONES",
      "VEHICLES",
      "ROUTES",
    ];
    for (const layer of LAYERS) {
      const shouldBeDrawn = drawn.includes(layer.id);
      expect(layer.implemented, layer.id).toBe(shouldBeDrawn);
      if (!shouldBeDrawn) {
        expect(layer.note, layer.id).toContain("No renderer exists yet");
      }
    }
  });

  it("keeps the published extent drawn and captioned", () => {
    const extent = LAYERS.find((layer) => layer.id === "PUBLISHED_EXTENT");
    expect(extent?.implemented).toBe(true);
    expect(extent?.note).toContain(EXTENT_CAVEAT);
  });

  it("marks the drawn landform layers SYNTHETIC_FOR_DEMO, now that they are visible", () => {
    // Becoming drawable must not make invented geometry look authoritative.
    for (const id of ["TERRAIN", "PIT", "BENCHES", "HAUL_ROADS", "RAMPS"]) {
      const layer = LAYERS.find((candidate) => candidate.id === id);
      expect(layer?.provenance, id).toBe("SYNTHETIC_FOR_DEMO");
      expect(layer?.note, id).toMatch(/No (DEM|authoritative|surveyed)|NOT NMDC/);
    }
  });

  it("lists every layer the specification requires", () => {
    const required = [
      "TERRAIN",
      "ORTHOPHOTO",
      "PUBLISHED_EXTENT",
      "PIT",
      "BENCHES",
      "HAUL_ROADS",
      "RAMPS",
      "MINE_ZONES",
      "VEHICLES",
      "ROUTES",
      "SAFETY",
      "V2V",
      "V2I_RSU",
    ];
    expect(LAYERS.map((layer) => layer.id)).toEqual(required);
  });

  it("leaves V2I off by default, because no roadside unit exists", () => {
    expect(LAYERS.find((layer) => layer.id === "V2I_RSU")?.defaultVisible).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// formatting never fabricates
// ---------------------------------------------------------------------------

describe("formatting", () => {
  it("renders an absent number as UNAVAILABLE, not as zero", () => {
    expect(speedText(null)).toBe("UNAVAILABLE");
    expect(metresText(null)).toBe("UNAVAILABLE");
    expect(speedText(null)).not.toContain("0");
  });

  it("renders a genuine zero as zero", () => {
    // A stopped truck is a real measurement and must not be hidden behind UNAVAILABLE.
    expect(speedText(0)).toBe("0.0 m/s");
  });

  it("refuses a non-finite value", () => {
    expect(speedText(Number.NaN)).toBe("UNAVAILABLE");
    expect(metresText(Number.POSITIVE_INFINITY)).toBe("UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// determinism
// ---------------------------------------------------------------------------

describe("determinism", () => {
  it("returns the same projection for the same input", () => {
    const state = appState({ TRUCK_01: vehicle("TRUCK_01"), TRUCK_02: vehicle("TRUCK_02") });
    expect(JSON.stringify(projectMineCast(state))).toBe(JSON.stringify(projectMineCast(state)));
  });
});
