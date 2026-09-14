/**
 * HMI-DATA-01 — operational telemetry truth contract (brief tests 1-25).
 *
 * SOFTWARE ONLY. Twin frames here are fixtures shaped exactly like the backend's
 * `twin_vehicle_update` projection; nothing physical executed. Node environment,
 * `renderToString` only.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VehicleCard } from "../components/VehicleCard";
import { freshnessConfig } from "../config/freshness";
import type { DispatchCommand, SafetyState, VehicleState } from "../contracts/domain";
import type { RawTwinVehicle } from "../contracts/raw";
import { normalizeTwinVehicle } from "../data/normalize";
import { LiveDataProvider, StubLiveTransport } from "../providers/LiveDataProvider";
import { manualScheduler } from "../providers/scheduler";
import { OperationsOverview } from "../screens/OperationsOverview";
import { DriverScreen } from "../vehicle/DriverScreen";
import { vehicleConfig } from "../vehicle/vehicleConfig";
import { projectVehicle } from "../vehicle/vehicleProjection";
import { fieldDataState, provenanceLabel } from "./dataStatus";
import { speedView } from "./derive";
import { viewFreshness } from "./freshness";
import { derivedSpeedReadout, hardwareReadouts, reportedSpeedReadout } from "./hardwareTelemetry";
import { deriveOperatorReadout } from "./operatorAction";
import { HmiContext } from "./ProviderHost";
import { actualSpeedSourceText, CANONICAL_SPEED_FIELD, resolveActualSpeed } from "./speedContract";
import { AppStateStore } from "./store";
import { testHmiContext } from "./testHmiContext";

const NOW_S = 1_788_000_000;
const T = new Date(NOW_S * 1000).toISOString();
const CONFIG = freshnessConfig(5000);

// ---------------------------------------------------------------------------
// fixtures: a Twin projection frame, as the backend emits it
// ---------------------------------------------------------------------------

type FieldOver = Partial<{
  source: string;
  origin: string;
  quality: string;
  freshness: string;
  available: boolean;
  age_s: number | null;
  timestamp: number | null;
}>;

function field(value: unknown, over: FieldOver = {}) {
  return {
    value,
    timestamp: NOW_S,
    source: "DERIVED",
    origin: "HARDWARE",
    quality: "GOOD",
    age_s: 0.4,
    available: true,
    clock_domain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...over,
  };
}

/** TRUCK_01 physical frame: measured rpm, encoder-derived speed_mps, firmware-reported speed. */
function truck01Frame(
  over: Partial<Record<string, ReturnType<typeof field>>> = {},
): RawTwinVehicle {
  return {
    vehicle_id: "TRUCK_01",
    static: {},
    has_hardware_data: true,
    dynamic: {
      rpm: field(1450, { source: "HARDWARE" }),
      speed_mps: field(7.592), // 1450 rpm x 2*pi*0.05 / 60, computed by the backend
      speed_mps_reported: field(7.8),
      ...over,
    },
  } as RawTwinVehicle;
}

/** Simulated frame through POST /api/telemetry: every field SIMULATION. */
function simulatedFrame(id: string, speedMps: number, reported: number): RawTwinVehicle {
  const sim = { source: "SIMULATION", origin: "SIMULATION" };
  return {
    vehicle_id: id,
    static: {},
    has_hardware_data: false,
    dynamic: {
      rpm: field(1450, sim),
      speed_mps: field(speedMps, sim),
      speed_mps_reported: field(reported, sim),
    },
  } as RawTwinVehicle;
}

function safety(id: string, over: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: id,
    timestamp: T,
    vSafe: 10,
    hSafe: 20,
    actualSpeed: 7.592,
    headwayCurrent: 30,
    leadVehicleId: null,
    activeConstraint: "VISIBILITY",
    riskLevel: "LOW",
    headwayViolation: false,
    envelopeViolation: false,
    ...over,
  };
}

function dispatch(id: string, targetSpeed: number): DispatchCommand {
  return {
    commandId: `CMD-${id}-${targetSpeed}`,
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

function liveStore(frames: RawTwinVehicle[]): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  const vehicles: Record<string, VehicleState> = {};
  for (const f of frames) vehicles[f.vehicle_id] = normalizeTwinVehicle(f);
  store.applyPatch({ changes: { vehicles } }, T);
  store.setStatus("CONNECTED", null);
  return store;
}

/** SSR markup with React's text-node separators removed, so labels read as on screen. */
const text = (html: string) => html.replace(/<!-- -->/g, "");

function render(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: CONFIG });
  return text(renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>));
}

function driver(store: AppStateStore, id: "TRUCK_01" | "TRUCK_02"): string {
  const projection = projectVehicle(store.getSnapshot(), id);
  return render(store, <DriverScreen projection={projection} config={vehicleConfig(id)} />);
}

function speedCell(html: string): string {
  const m = html.match(/SPEED<\/div><div class="drv-cell-value">([^<]*)</);
  return m?.[1] ?? "";
}

const src = (rel: string) =>
  readFileSync(join(__dirname, "..", rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");

// ===========================================================================
// 1-3. the fields are distinct, named, and one is canonical
// ===========================================================================

describe("speed fields (1-3)", () => {
  it("1. reported speed is preserved separately from the derived speed", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    expect(v.speedMps).toBeCloseTo(7.592);
    expect(v.provenance?.speed_mps_reported?.value).toBe(7.8);
    expect(v.provenance?.speed_mps?.value).toBeCloseTo(7.592);
    expect(v.speedMps).not.toBe(7.8);
  });

  it("2. encoder-derived speed has explicit semantics: DERIVED from a HARDWARE rpm", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    expect(v.provenance?.speed_mps?.source).toBe("DERIVED");
    expect(v.provenance?.speed_mps?.origin).toBe("HARDWARE");
    expect(provenanceLabel(v.provenance?.speed_mps)).toBe("PHYSICAL (derived)");
    expect(derivedSpeedReadout(v).label).toContain("derived from wheel RPM");
    expect(reportedSpeedReadout(v)?.label).toContain("telemetry-reported");
    expect(reportedSpeedReadout(v)?.value).toBe("7.80");
  });

  it("3. canonical speed has ONE documented meaning: Twin speed_mps -> VehicleState.speedMps", () => {
    expect(CANONICAL_SPEED_FIELD).toBe("speed_mps");
    expect(src("data/normalize.ts")).toMatch(/speedMps:\s*numberOf\("speed_mps"\)/);
    // No screen or vehicle module picks a speed field of its own.
    for (const rel of [
      "vehicle/DriverScreen.tsx",
      "vehicle/panels.tsx",
      "components/VehicleCard.tsx",
      "screens/VehicleDetail.tsx",
      "screens/OperationsOverview.tsx",
    ]) {
      expect(src(rel), rel).not.toMatch(/speed_mps_reported|speed_mps_pwm_derived/);
    }
  });
});

// ===========================================================================
// 4-10. what the HMI displays as actual speed
// ===========================================================================

describe("displayed actual speed (4-10)", () => {
  it("4. HMI actual speed uses the canonical value, with its source stated", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    const actual = resolveActualSpeed(v, null);
    expect(actual.mps).toBeCloseTo(7.592);
    expect(actual.source).toBe("TWIN_SPEED_MPS");
    expect(actualSpeedSourceText(actual)).toBe(
      "ENCODER-DERIVED (rpm × wheel radius) · PHYSICAL (derived)",
    );
    const html = driver(liveStore([truck01Frame()]), "TRUCK_01");
    expect(speedCell(html)).toBe("27 km/h"); // 7.592 m/s, not 7.8 (28 km/h)
    expect(html).toContain("ENCODER-DERIVED (rpm × wheel radius)");
  });

  it("5. reported speed cannot silently overwrite the canonical speed", () => {
    const a = normalizeTwinVehicle(truck01Frame());
    const b = normalizeTwinVehicle(truck01Frame({ speed_mps_reported: field(9.9) }));
    expect(b.speedMps).toBe(a.speedMps);
    expect(b.provenance?.speed_mps_reported?.value).toBe(9.9);
  });

  it("6. canonical speed cannot silently overwrite the reported speed", () => {
    const b = normalizeTwinVehicle(truck01Frame({ speed_mps: field(9.0) }));
    expect(b.speedMps).toBe(9.0);
    expect(b.provenance?.speed_mps_reported?.value).toBe(7.8);
  });

  it("7. target speed cannot become actual speed", () => {
    const store = liveStore([truck01Frame()]);
    store.applyPatch({ changes: { dispatch: { X: dispatch("TRUCK_01", 12) } } }, T);
    const html = driver(store, "TRUCK_01");
    expect(speedCell(html)).toBe("27 km/h");
    expect(html).toContain("COMMAND / TARGET");
    expect(html).toMatch(/COMMAND \/ TARGET<\/div><div class="drv-cell-value">43 km\/h/);
  });

  it("8. command speed (Twin v_command_mps) cannot become actual speed", () => {
    const v = normalizeTwinVehicle(
      truck01Frame({ v_command_mps: field(12), v_dispatch_mps: field(12) } as never),
    );
    expect(v.speedMps).toBeCloseTo(7.592);
    expect(resolveActualSpeed(v, null).mps).toBeCloseTo(7.592);
  });

  it("9. safe speed is not substituted for actual speed", () => {
    const v = normalizeTwinVehicle(truck01Frame({ speed_mps: field(null, { available: false }) }));
    const readout = deriveOperatorReadout(safety("TRUCK_01", { vSafe: 5, actualSpeed: NaN }), v);
    expect(readout.actualSpeedMps).toBeNull();
    expect(readout.safeSpeedMps).toBe(5);
    expect(readout.action).toBe("SAFETY_DATA_UNAVAILABLE");
    expect(speedCell(driver(liveStore([v as never]), "TRUCK_01"))).toBe("UNAVAILABLE");
  });

  it("10. actual speed is not substituted for safe speed", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    const readout = deriveOperatorReadout(safety("TRUCK_01", { vSafe: null }), v);
    expect(readout.actualSpeedMps).toBeCloseTo(7.592);
    expect(readout.safeSpeedMps).toBeNull();
    expect(readout.action).toBe("SAFETY_DATA_UNAVAILABLE");
    const html = driver(liveStore([truck01Frame()]), "TRUCK_01");
    expect(html).toMatch(/SAFE SPEED<\/div><div class="drv-cell-value">UNAVAILABLE/);
  });

  it("solver-evaluated speed is shown apart from the canonical one, never merged", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    const readout = deriveOperatorReadout(safety("TRUCK_01", { vSafe: 10, actualSpeed: 9.5 }), v);
    expect(readout.actualSpeedMps).toBeCloseTo(7.592); // displayed: Twin
    expect(readout.actualSpeed.evaluatedMps).toBe(9.5); // judged: solver's operand
    expect(readout.actualSpeed.disagreesWithEvaluated).toBe(true);
    expect(readout.action).toBe("CAUTION"); // 9.5 >= 0.88 * 10, the solver's own pair
    const view = speedView(safety("TRUCK_01", { vSafe: 10, actualSpeed: 9.5 }), v);
    expect(view?.actualKmh).toBeCloseTo(7.592 * 3.6);
    expect(view?.actual.evaluatedMps).toBe(9.5);
    const html = text(
      renderToString(
        <VehicleCard
          vehicle={v}
          safety={safety("TRUCK_01", { vSafe: 10, actualSpeed: 9.5 })}
          freshness={viewFreshness(T, CONFIG, NOW_S * 1000)}
        />,
      ),
    );
    expect(html).toContain("SAFETY EVALUATED AT 34.2 km/h");
  });
});

// ===========================================================================
// 11-15. provenance, freshness, absence, invalidity
// ===========================================================================

describe("provenance and freshness (11-15)", () => {
  it("11. simulated telemetry remains SIMULATION on every display", () => {
    const store = liveStore([
      simulatedFrame("TRUCK_01", 7.592, 7.8),
      simulatedFrame("TRUCK_02", 6.5, 6.7),
    ]);
    const t01 = driver(store, "TRUCK_01");
    expect(t01).toContain("ENCODER-DERIVED (rpm × wheel radius) · SIMULATION");
    expect(t01).not.toMatch(/PHYSICAL|HARDWARE/);
    const cr = render(store, <OperationsOverview onSelectVehicle={() => {}} />);
    expect(cr).toContain("SOURCE SIMULATION");
    expect(cr).not.toContain("SOURCE PHYSICAL");
  });

  it("12. derived hardware telemetry remains correctly marked", () => {
    const v = normalizeTwinVehicle(truck01Frame());
    expect(hardwareReadouts(v).find((r) => r.label.includes("derived"))?.provenance).toBe(
      "PHYSICAL (derived)",
    );
    expect(hardwareReadouts(v).find((r) => r.label === "Wheel RPM")?.provenance).toBe("PHYSICAL");
    // A derived value never claims to be a direct measurement.
    expect(provenanceLabel(v.provenance?.speed_mps)).not.toBe("PHYSICAL");
  });

  it("13. stale telemetry remains STALE (Twin verdict used as-is; not re-decided)", () => {
    const v = normalizeTwinVehicle(
      truck01Frame({ speed_mps: field(7.592, { freshness: "STALE", age_s: 4.1 }) }),
    );
    expect(fieldDataState(v.provenance?.speed_mps)).toBe("STALE");
    expect(derivedSpeedReadout(v).freshness).toBe("STALE");
    expect(derivedSpeedReadout(v).value).toBe("7.59"); // the value is kept, flagged, not zeroed
    // Entity-level: the configured 5000 ms placeholder threshold.
    expect(viewFreshness(T, CONFIG, NOW_S * 1000 + 6000).quality).toBe("STALE");
    expect(viewFreshness(T, CONFIG, NOW_S * 1000 + 4000).quality).toBe("OK");
  });

  it("13b. a stale speed is flagged STALE on the driver SPEED cell even with no safety slice", () => {
    const s = liveStore([truck01Frame()]);
    s.tick(new Date(NOW_S * 1000 + 6000).toISOString()); // 6 s > 5000 ms placeholder
    const html = driver(s, "TRUCK_01");
    expect(speedCell(html)).toBe("27 km/h"); // value kept
    expect(html).toMatch(
      /SPEED<\/div><div class="drv-cell-value">27 km\/h<\/div><div class="drv-cell-sub">[^<]*STALE/,
    );
    // and not before the threshold
    const fresh = liveStore([truck01Frame()]);
    fresh.tick(new Date(NOW_S * 1000 + 4000).toISOString());
    expect(driver(fresh, "TRUCK_01")).not.toMatch(/drv-cell-sub">[^<]*STALE/);
    // The peer cell carries the peer's own staleness too.
    const both = liveStore([truck01Frame(), simulatedFrame("TRUCK_02", 3.5, 4.0)]);
    both.tick(new Date(NOW_S * 1000 + 6000).toISOString());
    expect(driver(both, "TRUCK_02")).toMatch(
      /PEER TRUCK_01<\/div><div class="drv-cell-value">27 km\/h<\/div><div class="drv-cell-sub">[^<]*STALE/,
    );
  });

  it("14. missing telemetry remains UNAVAILABLE, never 0", () => {
    const v = normalizeTwinVehicle({
      vehicle_id: "TRUCK_02",
      static: {},
      dynamic: {},
    } as RawTwinVehicle);
    expect(v.speedMps).toBeNull();
    expect(resolveActualSpeed(v, null)).toMatchObject({ mps: null, source: null });
    expect(derivedSpeedReadout(v).value).toBe("--");
    expect(speedCell(driver(liveStore([v as never]), "TRUCK_02"))).toBe("UNAVAILABLE");
  });

  it("15. invalid / non-finite telemetry does not create a plausible value", () => {
    for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, "7.8", null, true]) {
      const v = normalizeTwinVehicle(truck01Frame({ speed_mps: field(bad) }));
      expect(v.speedMps, String(bad)).toBeNull();
      expect(resolveActualSpeed(v, null).mps, String(bad)).toBeNull();
    }
    // A non-finite timestamp does not become a fabricated time either.
    const v = normalizeTwinVehicle(
      truck01Frame({
        rpm: field(1450, { timestamp: null, source: "HARDWARE" }),
        speed_mps: field(7.592, { timestamp: null }),
        speed_mps_reported: field(7.8, { timestamp: null }),
      }),
    );
    expect(v.timestamp).toBe(new Date(0).toISOString());
    expect(viewFreshness(v.timestamp, CONFIG, NOW_S * 1000).quality).toBe("STALE");
  });
});

// ===========================================================================
// 16-22. identity, peers, synchronization
// ===========================================================================

describe("identity and synchronization (16-22)", () => {
  const store = () =>
    liveStore([simulatedFrame("TRUCK_01", 9.0, 9.2), simulatedFrame("TRUCK_02", 3.5, 4.0)]);

  it("16/17. T01 and T02 speed projections are fixed to their own vehicle", () => {
    const s = store();
    expect(projectVehicle(s.getSnapshot(), "TRUCK_01").vehicle?.speedMps).toBe(9.0);
    expect(projectVehicle(s.getSnapshot(), "TRUCK_02").vehicle?.speedMps).toBe(3.5);
    expect(speedCell(driver(s, "TRUCK_01"))).toBe("32 km/h");
    expect(speedCell(driver(s, "TRUCK_02"))).toBe("13 km/h");
  });

  it("18. peer speed uses the peer's canonical state", () => {
    const s = store();
    expect(projectVehicle(s.getSnapshot(), "TRUCK_01").peer?.speedMps).toBe(3.5);
    expect(driver(s, "TRUCK_01")).toMatch(
      /PEER TRUCK_02<\/div><div class="drv-cell-value">13 km\/h/,
    );
    expect(driver(s, "TRUCK_02")).toMatch(
      /PEER TRUCK_01<\/div><div class="drv-cell-value">32 km\/h/,
    );
  });

  it("19/20. Control Room and both trucks observe the same canonical speed after an update", () => {
    const s = store();
    s.applyPatch(
      {
        changes: {
          vehicles: { TRUCK_01: normalizeTwinVehicle(simulatedFrame("TRUCK_01", 5.0, 9.2)) },
        },
      },
      T,
    );
    const cr = render(s, <OperationsOverview onSelectVehicle={() => {}} />);
    const cards = cr.match(/<dt>Actual speed<\/dt><dd>([\d.]+)/g) ?? [];
    expect(cards).toContain("<dt>Actual speed</dt><dd>18.0"); // 5.0 m/s on the fleet card
    expect(cards).not.toContain("<dt>Actual speed</dt><dd>32.4"); // the old value is gone
    expect(speedCell(driver(s, "TRUCK_01"))).toBe("18 km/h");
    expect(driver(s, "TRUCK_02")).toMatch(
      /PEER TRUCK_01<\/div><div class="drv-cell-value">18 km\/h/,
    );
    // The reported field changed nowhere: still 9.2, still separate.
    expect(s.getSnapshot().vehicles.TRUCK_01?.provenance?.speed_mps_reported?.value).toBe(9.2);
  });

  it("21. target speed changes do not change actual speed", () => {
    const s = store();
    s.applyPatch({ changes: { dispatch: { A: dispatch("TRUCK_01", 2) } } }, T);
    s.applyPatch({ changes: { dispatch: { A: dispatch("TRUCK_01", 14) } } }, T);
    expect(s.getSnapshot().vehicles.TRUCK_01?.speedMps).toBe(9.0);
    expect(speedCell(driver(s, "TRUCK_01"))).toBe("32 km/h");
  });

  it("22. actual telemetry changes do not mutate target speed", () => {
    const s = store();
    s.applyPatch({ changes: { dispatch: { A: dispatch("TRUCK_01", 2) } } }, T);
    s.applyPatch(
      {
        changes: {
          vehicles: { TRUCK_01: normalizeTwinVehicle(simulatedFrame("TRUCK_01", 1.0, 1.0)) },
        },
      },
      T,
    );
    expect(s.getSnapshot().dispatch.A?.targetSpeed).toBe(2);
    expect(projectVehicle(s.getSnapshot(), "TRUCK_01").dispatch?.targetSpeed).toBe(2);
  });
});

// ===========================================================================
// 23-25. no frontend calculation, one store, ProviderHost boundary
// ===========================================================================

describe("architecture (23-25)", () => {
  it("23. no frontend calculation contradicts the canonical speed", () => {
    // The only arithmetic on a speed anywhere in presentation is the unit conversion.
    for (const rel of [
      "state/speedContract.ts",
      "state/operatorAction.ts",
      "vehicle/DriverScreen.tsx",
      "components/VehicleCard.tsx",
    ]) {
      const text = src(rel);
      expect(text, rel).not.toMatch(/rpm\s*\*|\*\s*Math\.PI|wheel_radius|pulses/i);
      expect(text, rel).not.toMatch(/\(\s*\w*[sS]peed\w*\s*\+\s*\w*[sS]peed\w*\s*\)\s*\/\s*2/); // no averaging
    }
    // The live provider invents no VehicleState from a snapshot without a Twin.
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
    const result = provider.ingest({
      type: "connection_established",
      vehicles: { TRUCK_01: { speed_value: 3.0, timestamp: NOW_S } },
    });
    expect(result).toBeNull();
    expect(src("providers/LiveDataProvider.ts")).not.toMatch(/speed_value/);
  });

  it("24. no second telemetry store exists", () => {
    const text = src("providers/LiveDataProvider.ts") + src("state/ProviderHost.tsx");
    expect(text.match(/new AppStateStore\(/g)?.length ?? 0).toBeLessThanOrEqual(1);
    for (const rel of [
      "vehicle/DriverScreen.tsx",
      "vehicle/panels.tsx",
      "components/VehicleCard.tsx",
      "state/speedContract.ts",
    ]) {
      expect(src(rel), rel).not.toMatch(/new AppStateStore|new Map<|useState<.*VehicleState/);
    }
  });

  it("25. ProviderHost remains the transport/state boundary", () => {
    for (const rel of [
      "vehicle/DriverScreen.tsx",
      "vehicle/panels.tsx",
      "components/VehicleCard.tsx",
      "state/speedContract.ts",
      "state/operatorAction.ts",
    ]) {
      expect(src(rel), rel).not.toMatch(/new WebSocket|fetch\(|EventSource|setInterval/);
    }
    expect(src("vehicle/DriverScreen.tsx")).toMatch(/useHmi\(|useAppState\(/);
  });
});
