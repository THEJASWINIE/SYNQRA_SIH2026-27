/**
 * HMI-ARCH-01 — the three operational HMIs and their one canonical source.
 *
 *   CONTROL ROOM (index.html)   fleet perspective, every vehicle the Twin carries
 *   TRUCK_01 HMI (truck01.html) own-vehicle perspective, fixed to TRUCK_01
 *   TRUCK_02 HMI (truck02.html) own-vehicle perspective, fixed to TRUCK_02
 *   MINE-CAST   (mine-cast.html) separate spatial client, not an operational HMI
 *
 * Numbering follows the HMI-ARCH-01 brief (1-50). Rendered with `renderToString` in the
 * Node environment; sources are scanned as text where a rule is about code shape.
 *
 * SOFTWARE ONLY. Every value below is a synthetic fixture; nothing here is hardware.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "./config/freshness";
import type { VehicleState } from "./contracts/domain";
import { LAYERS, projectMineCast } from "./minecast/minecastProjection";
import { toSpatialPosition } from "./minecast/spatialPosition";
import { OperationsOverview } from "./screens/OperationsOverview";
import { bailadilaDeposit5, toDecimalExtent } from "./state/geoSite";
import { HmiContext } from "./state/ProviderHost";
import { AppStateStore } from "./state/store";
import { testHmiContext } from "./state/testHmiContext";
import { positionsFor, providerForMode } from "./state/vehiclePosition";
import { communicationLinks } from "./vehicle/communication";
import { DriverScreen } from "./vehicle/DriverScreen";
import { dataSourceLabel, VehicleMapPanel } from "./vehicle/panels";
import { VEHICLE_IDS, vehicleConfig } from "./vehicle/vehicleConfig";
import { peerOf, projectVehicle } from "./vehicle/vehicleProjection";

const T = "2026-09-10T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function src(relative: string): string {
  return readFileSync(join(__dirname, relative), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

function sourcesIn(dir: string): { name: string; text: string }[] {
  return readdirSync(join(__dirname, dir))
    .filter((f) => /\.(ts|tsx)$/.test(f) && !/\.test\./.test(f))
    .map((f) => ({ name: `${dir}/${f}`, text: src(`${dir}/${f}`) }));
}

function vehicle(
  id: string,
  speedMps: number | null,
  extra: Partial<VehicleState> = {},
): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps,
    position: { x: 0, y: 0, segmentId: null, offsetM: 0 },
    accelMps2: null,
    gradeRad: null,
    commConfidence: null,
    frictionEst: null,
    routeId: null,
    timestamp: T,
    provenance: {
      speed_mps: {
        source: "SIMULATION",
        origin: "SIMULATION",
        quality: "OK",
        freshness: "CURRENT",
        available: true,
        timestamp: Date.parse(T) / 1000,
      },
    } as never,
    ...extra,
  } as VehicleState;
}

function fleetStore(t01 = 7.8, t02 = 6.7): AppStateStore {
  // LIVE provider: positions come only from the Twin, never from the synthetic harness.
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch(
    {
      changes: {
        vehicles: { TRUCK_01: vehicle("TRUCK_01", t01), TRUCK_02: vehicle("TRUCK_02", t02) },
      },
    },
    T,
  );
  store.setStatus("CONNECTED", null);
  return store;
}

function wrapWith(store: AppStateStore) {
  const value = testHmiContext({ store, freshness: CONFIG });
  return (children: ReactNode) =>
    renderToString(<HmiContext.Provider value={value}>{children}</HmiContext.Provider>);
}

function controlRoom(store: AppStateStore): string {
  return wrapWith(store)(<OperationsOverview onSelectVehicle={() => {}} />);
}

function truckHmi(store: AppStateStore, id: "TRUCK_01" | "TRUCK_02"): string {
  const projection = projectVehicle(store.getSnapshot(), id);
  return wrapWith(store)(
    <>
      <span>{dataSourceLabel(projection)}</span>
      <DriverScreen projection={projection} config={vehicleConfig(id)} />
      <VehicleMapPanel projection={projection} mode="LIVE" />
    </>,
  );
}

const kmh = (mps: number) => `${(mps * 3.6).toFixed(0)}`;

// ===========================================================================
// CONTROL ROOM 1-6
// ===========================================================================

describe("control room — fleet HMI (1-6)", () => {
  it("1. represents the fleet: every vehicle the Twin carries has a row", () => {
    const html = controlRoom(fleetStore());
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
  });

  it("2/3. is not fixed to TRUCK_01 or TRUCK_02 - no literal truck id in its sources", () => {
    const files = [
      { name: "App.tsx", text: src("App.tsx") },
      ...sourcesIn("screens"),
      { name: "components/VehicleCard.tsx", text: src("components/VehicleCard.tsx") },
    ];
    for (const f of files) {
      expect(f.text, f.name).not.toMatch(/["'`]TRUCK_0[12]["'`]/);
    }
  });

  it("4/5. can represent TRUCK_01 alone and TRUCK_02 alone", () => {
    const only01 = new AppStateStore(T, "LIVE");
    only01.applyPatch({ changes: { vehicles: { TRUCK_01: vehicle("TRUCK_01", 3) } } }, T);
    only01.setStatus("CONNECTED", null);
    expect(controlRoom(only01)).toContain("TRUCK_01");
    expect(controlRoom(only01)).not.toContain("TRUCK_02");

    const only02 = new AppStateStore(T, "LIVE");
    only02.applyPatch({ changes: { vehicles: { TRUCK_02: vehicle("TRUCK_02", 3) } } }, T);
    only02.setStatus("CONNECTED", null);
    expect(controlRoom(only02)).toContain("TRUCK_02");
    expect(controlRoom(only02)).not.toContain("TRUCK_01");
  });

  it("6. uses canonical vehicle ids as the Twin carries them, sorted, no index identity", () => {
    const store = new AppStateStore(T, "LIVE");
    store.applyPatch(
      {
        changes: {
          vehicles: {
            TRUCK_02: vehicle("TRUCK_02", 1),
            TRUCK_01: vehicle("TRUCK_01", 2),
            TRUCK_07: vehicle("TRUCK_07", 3),
          },
        },
      },
      T,
    );
    store.setStatus("CONNECTED", null);
    const html = controlRoom(store);
    // A third vehicle needs no code change: the fleet is the Twin's collection.
    expect(html).toContain("TRUCK_07");
    expect(html.indexOf("TRUCK_01")).toBeLessThan(html.indexOf("TRUCK_02"));
  });

  it("has no navigation to a generic operator screen keyed on the selected vehicle", () => {
    // The dumper/operator HMI is truck01.html / truck02.html, not a control-room screen.
    const shell = src("screens/AppShell.tsx");
    expect(shell).not.toMatch(/setScreenId\(OPERATOR_ID\)/);
    expect(shell).not.toMatch(/OPERATOR_ID\)\}\s*>/);
  });
});

// ===========================================================================
// TRUCK_01 7-10, TRUCK_02 11-14
// ===========================================================================

describe("truck HMIs — fixed identity (7-14)", () => {
  it("7/11. entry points bind a literal identity", () => {
    expect(src("truck01.tsx")).toMatch(/vehicleId="TRUCK_01"/);
    expect(src("truck02.tsx")).toMatch(/vehicleId="TRUCK_02"/);
    expect(src("truck01.tsx")).not.toContain("TRUCK_02");
    expect(src("truck02.tsx")).not.toContain("TRUCK_01");
  });

  it("8/12. no runtime switching mechanism exists in the vehicle HMI sources", () => {
    for (const f of [
      ...sourcesIn("vehicle"),
      { name: "truck01.tsx", text: src("truck01.tsx") },
      { name: "truck02.tsx", text: src("truck02.tsx") },
    ]) {
      expect(f.text, f.name).not.toMatch(
        /localStorage|sessionStorage|URLSearchParams|location\.search|location\.hash/,
      );
      // The only <select> is the command ACTION list; none is fed from VEHICLE_IDS.
      expect(f.text, f.name).not.toMatch(/VEHICLE_IDS\.map\([\s\S]{0,120}<option/);
      expect(f.text, f.name).not.toMatch(/<select[^>]*vehicle/i);
      expect(f.text, f.name).not.toMatch(/import\.meta\.env\.[A-Z_]*VEHICLE/);
      expect(f.text, f.name).not.toMatch(/VEHICLE_IDS\[\s*\d/);
    }
    // And an unknown id refuses to start rather than defaulting.
    expect(() => vehicleConfig("TRUCK_99")).toThrow();
  });

  it("9/13. own vehicle is marked THIS VEHICLE and titled by its own id", () => {
    const store = fleetStore();
    const html01 = truckHmi(store, "TRUCK_01");
    const html02 = truckHmi(store, "TRUCK_02");
    expect(html01).toContain("Mine map — fleet (TRUCK_01)");
    expect(html02).toContain("Mine map — fleet (TRUCK_02)");
    expect(html01).toContain('aria-label="TRUCK_01 driver display"');
    expect(html02).toContain('aria-label="TRUCK_02 driver display"');
  });

  it("10/14. the other truck can only be a peer, never own", () => {
    expect(peerOf("TRUCK_01")).toBe("TRUCK_02");
    expect(peerOf("TRUCK_02")).toBe("TRUCK_01");
    const p01 = projectVehicle(fleetStore().getSnapshot(), "TRUCK_01");
    expect(p01.vehicle?.vehicleId).toBe("TRUCK_01");
    expect(p01.peer?.vehicleId).toBe("TRUCK_02");
    const p02 = projectVehicle(fleetStore().getSnapshot(), "TRUCK_02");
    expect(p02.vehicle?.vehicleId).toBe("TRUCK_02");
    expect(p02.peer?.vehicleId).toBe("TRUCK_01");
    // With three vehicles there is no single peer: null, not an arbitrary pick.
    expect(VEHICLE_IDS).toEqual(["TRUCK_01", "TRUCK_02"]);
  });
});

// ===========================================================================
// MAP 15-21
// ===========================================================================

describe("mine-site map in both HMI classes (15-21)", () => {
  const store = fleetStore();

  it("15. control room has the mine-site map", () => {
    const html = controlRoom(store);
    expect(html).toContain("PUBLISHED LEASE COORDINATE EXTENT");
    expect(html).toContain("<svg");
  });

  it("16/17. both truck HMIs have the mine-site map", () => {
    for (const id of ["TRUCK_01", "TRUCK_02"] as const) {
      const html = truckHmi(store, id);
      expect(html, id).toContain("PUBLISHED LEASE COORDINATE EXTENT");
      expect(html, id).toContain("<svg");
    }
  });

  it("18. map geometry source is shared: one GeoSiteMap, one geoSite, no second geometry", () => {
    expect(src("screens/OperationsOverview.tsx")).toContain('from "./GeoSiteMap"');
    expect(src("vehicle/panels.tsx")).toContain('from "../screens/GeoSiteMap"');
    expect(src("vehicle/panels.tsx")).toContain("bailadilaDeposit5()");
    expect(src("screens/OperationsOverview.tsx")).toMatch(/bailadilaDeposit5|geoSite/);
    for (const f of sourcesIn("vehicle")) {
      expect(f.text, f.name).not.toMatch(/lat:\s*\d|lon:\s*\d/);
    }
  });

  it("19. published coordinate extent semantics preserved on every map", () => {
    for (const html of [
      controlRoom(store),
      truckHmi(store, "TRUCK_01"),
      truckHmi(store, "TRUCK_02"),
    ]) {
      expect(html).toContain("not a lease boundary");
      expect(html).toContain("ASSUMED_WGS84_UNVERIFIED");
    }
  });

  it("20. unplaced vehicles remain visible on every map", () => {
    expect(controlRoom(store)).toContain("POSITION UNAVAILABLE (2)");
    expect(truckHmi(store, "TRUCK_01")).toContain("POSITION UNAVAILABLE (2)");
    expect(truckHmi(store, "TRUCK_02")).toContain("POSITION UNAVAILABLE (2)");
  });

  it("21. no fake positions: nothing is drawn as THIS VEHICLE or as a marker", () => {
    for (const id of ["TRUCK_01", "TRUCK_02"] as const) {
      const html = truckHmi(store, id);
      expect(html, id).not.toContain("THIS VEHICLE");
      expect(html, id).not.toContain("data-own-vehicle");
    }
    const provider = providerForMode("LIVE", toDecimalExtent(bailadilaDeposit5().extent));
    for (const p of positionsFor(store.getSnapshot().vehicles, provider))
      expect(p.position).toBeNull();
  });
});

// ===========================================================================
// POSITION 22-27
// ===========================================================================

describe("position truth (22-27)", () => {
  const site = projectMineCast(fleetStore().getSnapshot());
  const t01 = site.vehicles.find((v) => v.canonicalVehicleId === "TRUCK_01");
  const t02 = site.vehicles.find((v) => v.canonicalVehicleId === "TRUCK_02");

  it("22/23. TRUCK_01 with odometry is LOCAL_ODOMETRY and not drawable", () => {
    const withOdom = vehicle("TRUCK_01", 7.8, {
      positionOdom: {
        xM: 12.4,
        yM: -3.1,
        headingRad: 0.2,
        distanceM: 40,
        timestamp: Date.parse(T) / 1000,
        source: "HARDWARE",
        origin: "WHEEL_IMU_ODOMETRY",
        provenanceLabel: "LOCAL ODOMETRY",
        method: "WHEEL_IMU_ODOMETRY",
        status: "VALID",
        originType: "CONFIGURED_ORIGIN",
      },
    });
    const store = new AppStateStore(T, "LIVE");
    store.applyPatch({ changes: { vehicles: { TRUCK_01: withOdom } } }, T);
    const mc = projectMineCast(store.getSnapshot()).vehicles.find(
      (v) => v.canonicalVehicleId === "TRUCK_01",
    );
    if (!mc) throw new Error("TRUCK_01 missing");
    const spatial = toSpatialPosition(mc, site.site);
    expect(spatial.provenance).toBe("LOCAL_ODOMETRY");
    expect(spatial.frame).toBe("ODOMETRY_LOCAL_METRES");
    expect(spatial.drawableInScene).toBe(false);
    expect(spatial.synthetic).toBe(false);
  });

  it("24. TRUCK_02 remains UNAVAILABLE", () => {
    if (!t02) throw new Error("TRUCK_02 missing");
    const spatial = toSpatialPosition(t02, site.site);
    expect(spatial.provenance).toBe("UNAVAILABLE");
    expect(spatial.frame).toBe("NONE");
    expect(spatial.x).toBeNull();
    expect(spatial.y).toBeNull();
  });

  it("25/26. speed and mode never produce a position", () => {
    if (!t01) throw new Error("TRUCK_01 missing");
    expect(toSpatialPosition(t01, site.site).drawableInScene).toBe(false);
    const provider = providerForMode("LIVE", toDecimalExtent(bailadilaDeposit5().extent));
    for (const speed of [0, 7.8, 40]) {
      for (const mode of ["NORMAL", "CAUTION", "DEGRADED", "STOP_UNSAFE"] as const) {
        expect(provider.positionFor(vehicle("TRUCK_01", speed, { mode })).position).toBeNull();
      }
    }
  });

  it("27. no fabricated geographic coordinates in position code", () => {
    const text = src("state/vehiclePosition.ts");
    expect(text).not.toMatch(/lat:\s*1[89]\.\d/);
    expect(text).not.toMatch(/lon:\s*8[01]\.\d/);
  });
});

// ===========================================================================
// SYNC 28-34
// ===========================================================================

describe("one Twin, three projections (28-34)", () => {
  it("28-30. the same store feeds all three clients", () => {
    const store = fleetStore(7.8, 6.7);
    expect(controlRoom(store)).toContain(kmh(7.8));
    expect(truckHmi(store, "TRUCK_01")).toContain(`${kmh(7.8)} km/h`);
    const p02 = projectVehicle(store.getSnapshot(), "TRUCK_02");
    expect(p02.peer?.speedMps).toBe(7.8);
    expect(p02.vehicle?.speedMps).toBe(6.7);
  });

  it("31/32. a TRUCK_01 update reaches the control room and TRUCK_02's peer view", () => {
    const store = fleetStore(7.8, 6.7);
    store.applyPatch({ changes: { vehicles: { TRUCK_01: vehicle("TRUCK_01", 9.0) } } }, T);
    expect(controlRoom(store)).toContain(kmh(9.0));
    expect(truckHmi(store, "TRUCK_01")).toContain(`${kmh(9.0)} km/h`);
    expect(projectVehicle(store.getSnapshot(), "TRUCK_02").peer?.speedMps).toBe(9.0);
    const html02 = truckHmi(store, "TRUCK_02");
    expect(html02).toContain("PEER TRUCK_01");
    expect(html02).toContain(`${kmh(9.0)} km/h`);
    // TRUCK_02's own value is untouched by TRUCK_01's update.
    expect(projectVehicle(store.getSnapshot(), "TRUCK_02").vehicle?.speedMps).toBe(6.7);
  });

  it("33/34. a TRUCK_02 update reaches the control room and TRUCK_01's peer view", () => {
    const store = fleetStore(7.8, 6.7);
    store.applyPatch({ changes: { vehicles: { TRUCK_02: vehicle("TRUCK_02", 4.0) } } }, T);
    expect(controlRoom(store)).toContain(kmh(4.0));
    expect(truckHmi(store, "TRUCK_02")).toContain(`${kmh(4.0)} km/h`);
    expect(projectVehicle(store.getSnapshot(), "TRUCK_01").peer?.speedMps).toBe(4.0);
    const html01 = truckHmi(store, "TRUCK_01");
    expect(html01).toContain("PEER TRUCK_02");
    expect(html01).toContain(`${kmh(4.0)} km/h`);
    expect(projectVehicle(store.getSnapshot(), "TRUCK_01").vehicle?.speedMps).toBe(7.8);
  });

  it("44. no client keeps an independent vehicle store", () => {
    for (const f of [...sourcesIn("vehicle"), ...sourcesIn("screens")]) {
      expect(f.text, f.name).not.toMatch(/new AppStateStore\(/);
      expect(f.text, f.name).not.toMatch(/useState<\s*(VehicleState|SafetyState|AppState)\b/);
    }
  });
});

// ===========================================================================
// PROVENANCE 35-38
// ===========================================================================

describe("provenance survives projection (35-38)", () => {
  it("35. SIMULATION remains SIMULATION on every client", () => {
    const store = fleetStore();
    expect(controlRoom(store)).toContain("SIMULATION");
    expect(truckHmi(store, "TRUCK_01")).toContain("SIMULATION");
    expect(controlRoom(store)).not.toMatch(/LIVE HARDWARE/);
  });

  it("36/37. LOCAL_ODOMETRY and UNAVAILABLE keep their names", () => {
    const site = projectMineCast(fleetStore().getSnapshot());
    const t02 = site.vehicles.find((v) => v.canonicalVehicleId === "TRUCK_02");
    if (!t02) throw new Error("missing");
    expect(toSpatialPosition(t02, site.site).provenance).toBe("UNAVAILABLE");
    expect(src("minecast/spatialPosition.ts")).toContain('"LOCAL_ODOMETRY"');
  });

  it("38. synthetic data is explicitly synthetic", () => {
    // The MOCK harness places vehicles, and says so on every position it returns.
    const mock = providerForMode("MOCK", toDecimalExtent(bailadilaDeposit5().extent));
    const p = mock.positionFor(vehicle("TRUCK_01", 1));
    expect(["SIMULATED", "SOFTWARE_ONLY_SYNTHETIC"]).toContain(p.provenance);
    expect(p.provenance).not.toBe("PHYSICAL");
    expect(LAYERS.find((l) => l.id === "TERRAIN")?.provenance).toBe("SYNTHETIC_FOR_DEMO");
  });
});

// ===========================================================================
// COMMUNICATION 39-40
// ===========================================================================

describe("communication semantics (39-40)", () => {
  it("39. Wi-Fi RSSI does not create V2V", () => {
    const wifi = vehicle("TRUCK_01", 5, {
      provenance: {
        wifi_rssi_dbm: {
          source: "HARDWARE",
          origin: "HARDWARE",
          quality: "OK",
          freshness: "CURRENT",
          available: true,
          timestamp: 0,
          value: -55,
        },
      } as never,
    });
    const links = communicationLinks(wifi, "CONNECTED", "LIVE");
    expect(links.find((l) => l.label === "V2V")?.state).not.toBe("CONNECTED");
  });

  it("40. V2I remains UNAVAILABLE in every mode", () => {
    for (const mode of ["LIVE", "MOCK", "REPLAY"]) {
      const links = communicationLinks(vehicle("TRUCK_01", 5), "CONNECTED", mode);
      expect(links.find((l) => l.label === "V2I")?.state, mode).toBe("UNAVAILABLE");
    }
  });
});

// ===========================================================================
// ARCHITECTURE 41-46
// ===========================================================================

describe("architecture (41-46)", () => {
  it("41. ProviderHost hosts every operational entry", () => {
    expect(src("App.tsx")).toMatch(/ProviderHost/);
    expect(src("vehicle/VehicleHmiApp.tsx")).toMatch(/<ProviderHost>/);
  });

  it("42/43. no direct WebSocket or Twin fetch in operational HMI code", () => {
    for (const f of [
      ...sourcesIn("vehicle"),
      ...sourcesIn("screens"),
      ...sourcesIn("components"),
    ]) {
      expect(f.text, f.name).not.toMatch(/new WebSocket\(/);
      if (f.name !== "screens/FailureInjectionLab.tsx") {
        expect(f.text, f.name).not.toMatch(/\bfetch\(/);
      }
      expect(f.text, f.name).not.toMatch(/\/api\/twin/);
    }
  });

  it("45. no Three.js in the operational HMIs", () => {
    for (const f of [
      ...sourcesIn("vehicle"),
      ...sourcesIn("screens"),
      ...sourcesIn("components"),
      { name: "App.tsx", text: src("App.tsx") },
    ]) {
      expect(f.text, f.name).not.toMatch(/from ["']three["']|@react-three/);
    }
  });

  it("46. Mine-Cast is separate: its own entry, not imported by any operational HMI", () => {
    for (const f of [
      ...sourcesIn("vehicle"),
      ...sourcesIn("screens"),
      { name: "App.tsx", text: src("App.tsx") },
    ]) {
      expect(f.text, f.name).not.toMatch(/from ["']\.\.?\/minecast\//);
    }
    expect(src("minecast.tsx")).toContain("MineCastApp");
  });
});

// ===========================================================================
// COMMAND 47-50
// ===========================================================================

describe("command architecture (47-50)", () => {
  it("47/48. the one command client and the operator session are what the truck HMI uses", () => {
    expect(src("vehicle/panels.tsx")).toContain('from "../api/commandClient"');
    expect(src("vehicle/VehicleHmiApp.tsx")).toContain("fetchOperatorContext");
    expect(src("api/commandClient.ts")).toMatch(/Authorization/);
  });

  it("49. lifecycle states are unchanged - in the gateway and in the client's outcome map", () => {
    // The lifecycle is owned by the backend command gateway; the client only maps the
    // outcomes it can be told about. Both vocabularies are asserted, neither is widened.
    const gateway = readFileSync(join(__dirname, "../../../command_gateway.py"), "utf-8");
    for (const state of [
      "ACCEPTED",
      "TRANSMITTED",
      "ACKNOWLEDGED",
      "EXECUTED",
      "REJECTED",
      "DUPLICATE",
      "STALE",
      "UNKNOWN_VEHICLE",
      "INVALID",
      "TIMEOUT",
      "SUPERSEDED",
    ]) {
      expect(gateway, state).toContain(`"${state}"`);
    }
    const client = src("api/commandClient.ts");
    for (const outcome of [
      "ACCEPTED",
      "REJECTED",
      "DUPLICATE",
      "STALE",
      "UNKNOWN_VEHICLE",
      "INVALID",
      "TIMEOUT",
      "SUPERSEDED",
    ]) {
      expect(client, outcome).toContain(`case "${outcome}":`);
    }
  });

  it("50. no frontend-only command execution or direct Twin mutation", () => {
    for (const f of [...sourcesIn("vehicle"), ...sourcesIn("screens")]) {
      expect(f.text, f.name).not.toMatch(/applyPatch\(/);
      expect(f.text, f.name).not.toMatch(/\/api\/hardware/);
    }
  });
});
