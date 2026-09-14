/**
 * HMI-SAFETY-01 — canonical safety state contract (brief tests 1-29).
 *
 * SOFTWARE ONLY. The safety values here are TEST-ONLY deterministic fixtures shaped like
 * the backend's `twin_vehicle_update` projection (source DERIVED / SIMULATION). No safety
 * algorithm runs in these tests and none exists in the HMI. `renderToString` only.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { DispatchCommand, SafetyState, VehicleState } from "../contracts/domain";
import type { RawTwinVehicle } from "../contracts/raw";
import { normalizeSafetyState, normalizeTwinSafety, normalizeTwinVehicle } from "../data/normalize";
import { LiveDataProvider, StubLiveTransport } from "../providers/LiveDataProvider";
import { manualScheduler } from "../providers/scheduler";
import { OperationsOverview } from "../screens/OperationsOverview";
import { DriverScreen } from "../vehicle/DriverScreen";
import { followingStatus } from "../vehicle/driverState";
import { vehicleConfig } from "../vehicle/vehicleConfig";
import { projectVehicle } from "../vehicle/vehicleProjection";
import { HmiContext } from "./ProviderHost";
import { AppStateStore } from "./store";
import { testHmiContext } from "./testHmiContext";

const NOW_S = 1_788_000_000;
const T = new Date(NOW_S * 1000).toISOString();
const CONFIG = freshnessConfig(5000);

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

type Over = Partial<{
  source: string;
  origin: string;
  freshness: string;
  available: boolean;
  timestamp: number | null;
}>;

function field(value: unknown, over: Over = {}) {
  return {
    value,
    timestamp: NOW_S,
    source: "DERIVED",
    origin: "SIMULATION",
    quality: "GOOD",
    age_s: 0.2,
    available: true,
    clock_domain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...over,
  };
}

/** The brief's canonical fixture for TRUCK_01, as a Twin projection frame. */
function t01Frame(over: Record<string, ReturnType<typeof field> | undefined> = {}): RawTwinVehicle {
  const dynamic: Record<string, ReturnType<typeof field>> = {
    speed_mps: field(8.0),
    rpm: field(1528, { source: "SIMULATION" }),
    v_safe_mps: field(6.0),
    safe_headway_m: field(25.0),
    headway_m: field(18.0),
    lead_vehicle_id: field("TRUCK_02"),
    active_constraint: field("HEADWAY"),
    risk_level: field("HIGH"),
    headway_violation: field(false),
    envelope_violation: field(false),
  };
  for (const [k, v] of Object.entries(over)) {
    if (v === undefined) delete dynamic[k];
    else dynamic[k] = v;
  }
  return {
    vehicle_id: "TRUCK_01",
    static: {},
    dynamic,
    has_hardware_data: false,
  } as RawTwinVehicle;
}

/** TRUCK_02: telemetry only, no safety producer output. */
function t02Frame(): RawTwinVehicle {
  return {
    vehicle_id: "TRUCK_02",
    static: {},
    dynamic: { speed_mps: field(3.5), rpm: field(700, { source: "SIMULATION" }) },
    has_hardware_data: false,
  } as RawTwinVehicle;
}

function storeFrom(frames: RawTwinVehicle[]): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  const vehicles: Record<string, VehicleState> = {};
  const safety: Record<string, SafetyState> = {};
  for (const f of frames) {
    vehicles[f.vehicle_id] = normalizeTwinVehicle(f);
    const s = normalizeTwinSafety(f);
    if (s) safety[f.vehicle_id] = s;
  }
  store.applyPatch({ changes: { vehicles, safety } }, T);
  store.setStatus("CONNECTED", null);
  return store;
}

const text = (html: string) => html.replace(/<!-- -->/g, "");

function render(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: CONFIG });
  return text(renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>));
}
const controlRoom = (s: AppStateStore) =>
  render(s, <OperationsOverview onSelectVehicle={() => {}} />);
function driver(store: AppStateStore, id: "TRUCK_01" | "TRUCK_02"): string {
  const projection = projectVehicle(store.getSnapshot(), id);
  return render(store, <DriverScreen projection={projection} config={vehicleConfig(id)} />);
}
const esc = (label: string) => label.replace(/[()/]/g, (c) => `\\${c}`);
const cell = (html: string, label: string): string =>
  html.match(new RegExp(`${esc(label)}</div><div class="drv-cell-value">([^<]*)<`))?.[1] ?? "";
const cellSub = (html: string, label: string): string =>
  html.match(
    new RegExp(
      `${esc(label)}</div><div class="drv-cell-value">[^<]*</div><div class="drv-cell-sub">([^<]*)<`,
    ),
  )?.[1] ?? "";
const banner = (html: string) => html.match(/data-driver-state="([A-Z_]+)"/)?.[1] ?? "";
const card = (html: string, id: string) =>
  html.match(
    new RegExp(`<article class="vehicle[^"]*" aria-label="[^"]*${id}[^"]*">[\\s\\S]*?</article>`),
  )?.[0] ?? "";

const src = (rel: string) =>
  readFileSync(join(__dirname, "..", rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
const sourcesIn = (dir: string) =>
  readdirSync(join(__dirname, "..", dir))
    .filter((f) => /\.(ts|tsx)$/.test(f) && !/\.test\./.test(f))
    .map((f) => ({ name: `${dir}/${f}`, text: src(`${dir}/${f}`) }));
/** Everything that renders or derives for the HMIs. ProviderHost is excluded: it IS the store owner and boundary. */
const HMI_SOURCES = () =>
  [
    ...sourcesIn("vehicle"),
    ...sourcesIn("screens"),
    ...sourcesIn("components"),
    ...sourcesIn("state"),
  ].filter((f) => f.name !== "state/ProviderHost.tsx");

function dispatch(id: string, targetSpeed: number): DispatchCommand {
  return {
    commandId: `CMD-${targetSpeed}`,
    vehicleId: id,
    routeId: null,
    departureTime: null,
    targetSpeed,
    slotId: null,
    reasonCode: "TEST",
    timestamp: T,
    state: "ISSUED",
    limitingVariables: null,
    routeNodeIds: null,
  } as DispatchCommand;
}

// ===========================================================================
// 1-9. source and distinctness
// ===========================================================================

describe("canonical source (1-9)", () => {
  const s = normalizeTwinSafety(t01Frame());

  it("1. safety state comes from the canonical Twin projection, field for field", () => {
    expect(s).not.toBeNull();
    expect(s).toMatchObject({
      vehicleId: "TRUCK_01",
      vSafe: 6.0,
      hSafe: 25.0,
      actualSpeed: 8.0,
      headwayCurrent: 18.0,
      leadVehicleId: "TRUCK_02",
      activeConstraint: "HEADWAY",
      riskLevel: "HIGH",
      headwayViolation: false,
      envelopeViolation: false,
    });
    // And the contract §3 message path yields the same shape from a producer message.
    const m = normalizeSafetyState({
      vehicle_id: "TRUCK_01",
      timestamp: T,
      v_safe: 6,
      h_safe: 25,
      actual_speed: 8,
      headway_current: 18,
      lead_vehicle_id: "TRUCK_02",
      active_constraint: "HEADWAY",
      risk_level: "HIGH",
      headway_violation: false,
      envelope_violation: false,
    });
    expect(m.riskLevel).toBe("HIGH");
    expect(m.activeConstraint).toBe("HEADWAY");
  });

  it("2/26. the HMI does not calculate safety anywhere", () => {
    for (const f of HMI_SOURCES()) {
      expect(f.text, f.name).not.toMatch(
        /nearestVehicle|calculateHeadway|calculateVsafe|calculateRisk|calculateLeadVehicle/i,
      );
      expect(f.text, f.name).not.toMatch(/risk(Level)?\s*=\s*["'](LOW|MODERATE|HIGH|CRITICAL)["']/);
      expect(f.text, f.name).not.toMatch(
        /headwayCurrent\s*[<>]=?\s*\w*hSafe|hSafe\s*[<>]=?\s*\w*headwayCurrent/,
      );
      expect(f.text, f.name).not.toMatch(/leadVehicleId\s*=\s*(state\.)?vehicles|\[0\]\.vehicleId/);
    }
    // The one judgement the driver screen makes about headway is the producer's flag.
    expect(src("vehicle/driverState.ts")).not.toMatch(/gap\s*<\s*required/);
  });

  it("3/4/5. actual speed, v_safe, H_safe and headway are four distinct values on screen", () => {
    const html = driver(storeFrom([t01Frame(), t02Frame()]), "TRUCK_01");
    expect(cell(html, "SPEED")).toBe("29 km/h"); // 8.0 m/s
    expect(cell(html, "SAFE SPEED")).toBe("22 km/h"); // 6.0 m/s
    expect(cell(html, "REQUIRED GAP (H_safe)")).toBe("25 m");
    expect(cell(html, "GAP")).toBe("18 m");
  });

  it("6/7/8/9. lead vehicle, constraint, risk and violations are the producer's, verbatim", () => {
    const html = driver(storeFrom([t01Frame(), t02Frame()]), "TRUCK_01");
    expect(cell(html, "LEAD TRUCK")).toBe("TRUCK_02");
    expect(html).toContain("RISK: HIGH");
    expect(s?.activeConstraint).toBe("HEADWAY"); // not collapsed to UNKNOWN or NONE
    expect(followingStatus(s)).toBe("FOLLOWING"); // headwayViolation=false, lead named
    const violated = normalizeTwinSafety(t01Frame({ headway_violation: field(true) }));
    expect(followingStatus(violated)).toBe("STOP");
    expect(
      banner(
        driver(storeFrom([t01Frame({ headway_violation: field(true) }), t02Frame()]), "TRUCK_01"),
      ),
    ).toBe("STOP");
  });
});

// ===========================================================================
// 10-17. unavailable, stale, provenance
// ===========================================================================

describe("unavailable / stale / provenance (10-17)", () => {
  it("10. missing v_safe produces SAFE SPEED UNAVAILABLE, never 0 or the actual speed", () => {
    expect(normalizeTwinSafety(t01Frame({ v_safe_mps: undefined }))).toBeNull();
    const html = driver(storeFrom([t01Frame({ v_safe_mps: undefined }), t02Frame()]), "TRUCK_01");
    expect(cell(html, "SAFE SPEED")).toBe("UNAVAILABLE");
    expect(cell(html, "SPEED")).toBe("29 km/h");
    const msg = normalizeSafetyState({
      vehicle_id: "TRUCK_01",
      timestamp: T,
      v_safe: null,
      h_safe: 25,
      actual_speed: 8,
      headway_current: 18,
      lead_vehicle_id: null,
      active_constraint: "NONE",
      risk_level: "LOW",
      headway_violation: null,
      envelope_violation: null,
    });
    expect(msg.vSafe).toBeNull();
  });

  it("11. missing safety state produces SAFETY DATA UNAVAILABLE on all three HMIs, never SAFE", () => {
    const s = storeFrom([t01Frame({ v_safe_mps: undefined }), t02Frame()]);
    for (const id of ["TRUCK_01", "TRUCK_02"] as const) {
      const html = driver(s, id);
      expect(banner(html)).toBe("SAFETY_DATA_UNAVAILABLE");
      expect(html).toContain("SAFETY DATA UNAVAILABLE");
      expect(html).not.toMatch(/data-driver-state="SAFE"/);
      expect(html).toContain("RISK: UNAVAILABLE");
      expect(cell(html, "LEAD TRUCK")).toBe("UNAVAILABLE");
    }
    const cr = controlRoom(s);
    expect(card(cr, "TRUCK_01")).toContain("SAFETY STATE UNAVAILABLE");
    expect(card(cr, "TRUCK_01")).not.toMatch(/RISK LOW|LOW RISK/);
  });

  it("12/13/14. missing risk, constraint, headway do not default to LOW, NONE, 0", () => {
    const s = normalizeTwinSafety(
      t01Frame({
        risk_level: undefined,
        active_constraint: undefined,
        headway_m: undefined,
        lead_vehicle_id: undefined,
      }),
    );
    expect(s?.riskLevel).toBeNull();
    expect(s?.activeConstraint).toBeNull();
    expect(s?.headwayCurrent).toBeNull();
    const store = storeFrom([
      t01Frame({
        risk_level: undefined,
        active_constraint: undefined,
        headway_m: undefined,
        lead_vehicle_id: undefined,
      }),
      t02Frame(),
    ]);
    const html = driver(store, "TRUCK_01");
    expect(html).toContain("RISK: UNAVAILABLE");
    expect(html).not.toMatch(/RISK: LOW/);
    expect(cell(html, "GAP")).toBe("UNAVAILABLE");
    expect(cell(html, "LEAD TRUCK")).toBe("UNAVAILABLE"); // never NONE unless the producer said so
    const c = card(controlRoom(store), "TRUCK_01");
    expect(c).toContain("RISK UNAVAILABLE");
    expect(c).toContain("CONSTRAINT UNAVAILABLE");
    expect(c).not.toContain("CONSTRAINT NONE");
    // An explicit NONE from the producer IS shown as NONE.
    const explicit = storeFrom([
      t01Frame({ active_constraint: field("NONE"), lead_vehicle_id: field(null) }),
      t02Frame(),
    ]);
    expect(card(controlRoom(explicit), "TRUCK_01")).toContain("CONSTRAINT NONE");
  });

  it("15. stale safety is displayed as STALE, its values kept and flagged", () => {
    const s = storeFrom([t01Frame(), t02Frame()]);
    s.tick(new Date(NOW_S * 1000 + 6000).toISOString());
    const html = driver(s, "TRUCK_01");
    expect(banner(html)).toBe("DATA_STALE");
    expect(cell(html, "SAFE SPEED")).toBe("22 km/h");
    expect(cellSub(html, "SAFE SPEED")).toMatch(/STALE/);
    expect(card(controlRoom(s), "TRUCK_01")).toContain("STALE");
  });

  it("16/17. simulated safety remains SIMULATION with provenance preserved; never PHYSICAL", () => {
    const s = normalizeTwinSafety(t01Frame());
    expect(s?.provenance?.v_safe_mps?.origin).toBe("SIMULATION");
    expect(s?.provenance?.v_safe_mps?.source).toBe("DERIVED");
    const store = storeFrom([t01Frame(), t02Frame()]);
    expect(cellSub(driver(store, "TRUCK_01"), "SAFE SPEED")).toContain("SIMULATION");
    expect(card(controlRoom(store), "TRUCK_01")).toContain("SAFETY SOURCE SIMULATION");
    expect(driver(store, "TRUCK_01")).not.toMatch(/PHYSICAL|HARDWARE/);
    // A solver output derived from hardware is labelled as such, not as a measurement.
    const hw = normalizeTwinSafety(t01Frame({ v_safe_mps: field(6.0, { origin: "HARDWARE" }) }));
    expect(hw?.provenance?.v_safe_mps?.origin).toBe("HARDWARE");
    expect(hw?.provenance?.v_safe_mps?.source).toBe("DERIVED");
  });
});

// ===========================================================================
// 18-25. identity, synchronization, commands
// ===========================================================================

describe("identity, synchronization, commands (18-25)", () => {
  it("18/19/20/21/22. one canonical update reaches own, peer and fleet projections", () => {
    const s = storeFrom([t01Frame(), t02Frame()]);
    expect(banner(driver(s, "TRUCK_01"))).not.toBe("SAFETY_DATA_UNAVAILABLE");
    expect(driver(s, "TRUCK_01")).toContain("RISK: HIGH");
    expect(cellSub(driver(s, "TRUCK_02"), "PEER TRUCK_01")).toContain("RISK HIGH");
    expect(banner(driver(s, "TRUCK_02"))).toBe("SAFETY_DATA_UNAVAILABLE"); // T02 has no producer output
    expect(cellSub(driver(s, "TRUCK_01"), "PEER TRUCK_02")).toContain("RISK UNAVAILABLE");
    expect(card(controlRoom(s), "TRUCK_01")).toContain("HIGH");
    expect(card(controlRoom(s), "TRUCK_02")).toContain("SAFETY STATE UNAVAILABLE");

    // risk HIGH -> LOW, one patch, three projections.
    const low = normalizeTwinSafety(t01Frame({ risk_level: field("LOW") }));
    if (!low) throw new Error("fixture");
    s.applyPatch({ changes: { safety: { TRUCK_01: low } } }, T);
    expect(driver(s, "TRUCK_01")).toContain("RISK: LOW");
    expect(cellSub(driver(s, "TRUCK_02"), "PEER TRUCK_01")).toContain("RISK LOW");
    expect(card(controlRoom(s), "TRUCK_01")).toContain("LOW");

    // Remove v_safe: the slice is deleted, nothing becomes 0.
    s.applyPatch({ deletions: { safety: ["TRUCK_01"] }, changes: {} }, T);
    expect(cell(driver(s, "TRUCK_01"), "SAFE SPEED")).toBe("UNAVAILABLE");
    expect(banner(driver(s, "TRUCK_01"))).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(cellSub(driver(s, "TRUCK_02"), "PEER TRUCK_01")).toContain("RISK UNAVAILABLE");
    expect(driver(s, "TRUCK_01")).not.toMatch(/SAFE SPEED<\/div><div class="drv-cell-value">0 km/);
  });

  it("live provider: a Twin frame with v_safe fills the safety slice; one without deletes it", () => {
    const provider = new LiveDataProvider({
      transport: new StubLiveTransport({
        clock: () => NOW_S * 1000,
        scheduler: manualScheduler(0),
        intervalMs: 1000,
      }),
      clock: () => NOW_S * 1000,
      scheduler: manualScheduler(0),
      reconnect: false,
    });
    const patches: unknown[] = [];
    provider.subscribe((p) => patches.push(p));
    provider.ingest({ type: "twin_vehicle_update", data: t01Frame() });
    expect(
      (patches[0] as { changes: { safety?: Record<string, SafetyState> } }).changes.safety?.TRUCK_01
        ?.riskLevel,
    ).toBe("HIGH");
    provider.ingest({ type: "twin_vehicle_update", data: t01Frame({ v_safe_mps: undefined }) });
    const second = patches[1] as {
      deletions?: { safety?: string[] };
      changes: { safety?: unknown };
    };
    expect(second.deletions?.safety).toContain("TRUCK_01");
    expect(second.changes.safety).toBeUndefined();
  });

  it("23/24. a command target becomes neither actual speed nor v_safe", () => {
    const s = storeFrom([t01Frame(), t02Frame()]);
    s.applyPatch({ changes: { dispatch: { X: dispatch("TRUCK_01", 12) } } }, T);
    const html = driver(s, "TRUCK_01");
    expect(cell(html, "COMMAND / TARGET")).toBe("43 km/h");
    expect(cell(html, "SPEED")).toBe("29 km/h");
    expect(cell(html, "SAFE SPEED")).toBe("22 km/h");
    expect(s.getSnapshot().safety.TRUCK_01?.vSafe).toBe(6.0);
  });

  it("25. the HMI cannot bypass fail-closed command behaviour: one path, no Twin writes", () => {
    const client = src("api/commandClient.ts");
    expect(client).toMatch(/\/api\/commands/);
    expect(client).toMatch(/Authorization/);
    expect(client).not.toMatch(/v_safe|\/api\/twin|\/api\/telemetry|\/api\/hardware/);
    for (const f of HMI_SOURCES()) {
      expect(f.text, f.name).not.toMatch(/\/api\/twin\/|\/api\/telemetry/);
      // Only the store itself applies patches; no screen writes state around it.
      if (f.name !== "state/store.ts") expect(f.text, f.name).not.toMatch(/applyPatch\(/);
    }
  });
});

// ===========================================================================
// 27-29. one store, one boundary, Mine-Cast apart
// ===========================================================================

describe("architecture (27-29)", () => {
  it("27. no second safety store", () => {
    for (const f of HMI_SOURCES()) {
      expect(f.text, f.name).not.toMatch(
        /new Map<string,\s*SafetyState>|useState<[^>]*SafetyState|new AppStateStore\(/,
      );
    }
    expect(src("providers/LiveDataProvider.ts").match(/TwinSafety: "safety"/)).not.toBeNull();
  });

  it("28. ProviderHost remains the state boundary", () => {
    for (const f of [...sourcesIn("vehicle"), ...sourcesIn("components")]) {
      expect(f.text, f.name).not.toMatch(/new WebSocket|fetch\(|EventSource/);
    }
    expect(src("vehicle/DriverScreen.tsx")).toMatch(/useAppState\(/);
  });

  it("29. Mine-Cast remains separate", () => {
    for (const f of [
      ...sourcesIn("vehicle"),
      ...sourcesIn("screens"),
      ...sourcesIn("components"),
    ]) {
      expect(f.text, f.name).not.toMatch(/from "\.\.?\/minecast|from "three"/);
    }
    // Mine-Cast reads the same canonical projections (read-only) and owns no safety of its own.
    for (const f of sourcesIn("minecast")) {
      expect(f.text, f.name).not.toMatch(
        /nearestVehicle|calculateHeadway|calculateVsafe|calculateRisk|new AppStateStore\(/,
      );
    }
  });
});
