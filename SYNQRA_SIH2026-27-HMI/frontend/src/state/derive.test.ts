/**
 * Display derivation tests — M4.
 *
 * Covers alert ordering, bottleneck ranking, the actual-versus-safe comparison, headway
 * unit safety (AMB-001), topology projection and vehicle placement.
 */

import { describe, expect, it } from "vitest";
import type {
  Alert,
  BottleneckState,
  DispatchCommand,
  MineTopology,
  SafetyState,
  SlotState,
  VehicleState,
} from "../contracts/domain";
import { emptyAppState } from "../data/patch";
import {
  activeBottleneck,
  conflictingSlots,
  criticalAlerts,
  fleetSummary,
  fmt,
  groupSlotsByResource,
  headwayView,
  isReasonCodeMissing,
  OVER_SAFE_SPEED_TEXT,
  POSITION_UNAVAILABLE_REASON_TEXT,
  placeVehicles,
  projectTopology,
  rankAlerts,
  rankBottlenecks,
  rankDispatch,
  resolvePosition,
  slotTimeAxis,
  speedView,
  TIME_AXIS_TICKS,
  worstVisibility,
} from "./derive";

const T = "2026-01-01T00:00:00.000Z";

function alert(id: string, severity: Alert["severity"], timestamp: string, active = true): Alert {
  return {
    alertId: id,
    timestamp,
    severity,
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: `alert ${id}`,
    reasonCode: null,
    acknowledgeable: true,
    acknowledged: null,
    active,
  };
}

function safety(partial: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "V-1",
    timestamp: T,
    vSafe: 10,
    hSafe: 60,
    actualSpeed: 8,
    headwayCurrent: 41,
    leadVehicleId: "V-0",
    activeConstraint: "VISIBILITY",
    riskLevel: "LOW",
    headwayViolation: null,
    envelopeViolation: null,
    ...partial,
  };
}

function vehicle(id: string, x: number | null, y: number | null): VehicleState {
  return {
    vehicleId: id,
    timestamp: T,
    position: { x, y, segmentId: "S-1", offsetM: 12 },
    speedMps: 8,
    accelMps2: 0,
    gradeRad: 0,
    frictionEst: { value: 0.6, sigma: null },
    mode: "NORMAL",
    commConfidence: 1,
    vehicleKind: "TRUCK",
    routeId: null,
  };
}

function bottleneck(nodeId: string, score: number | null): BottleneckState {
  return {
    nodeId,
    timestamp: T,
    lambdaVph: 12,
    muVph: 10,
    queue: 4,
    queueMax: 8,
    utilization: 0.8,
    criticality: "HIGH",
    bottleneckScore: score,
    queueHistory: null,
    queueForecast: null,
  };
}

// ---------------------------------------------------------------------------

describe("alert ordering (a display sort on supplied severities)", () => {
  it("orders CRITICAL, then WARNING, then INFO", () => {
    const ordered = rankAlerts([
      alert("i", "INFO", T),
      alert("c", "CRITICAL", T),
      alert("w", "WARNING", T),
    ]);
    expect(ordered.map((a) => a.alertId)).toEqual(["c", "w", "i"]);
  });

  it("breaks ties by recency, newest first", () => {
    const ordered = rankAlerts([
      alert("old", "CRITICAL", "2026-01-01T00:00:00.000Z"),
      alert("new", "CRITICAL", "2026-01-01T00:00:09.000Z"),
    ]);
    expect(ordered.map((a) => a.alertId)).toEqual(["new", "old"]);
  });

  it("excludes inactive alerts", () => {
    expect(rankAlerts([alert("x", "CRITICAL", T, false)])).toHaveLength(0);
  });

  it("criticalAlerts returns only CRITICAL", () => {
    const list = criticalAlerts([alert("c", "CRITICAL", T), alert("w", "WARNING", T)]);
    expect(list.map((a) => a.alertId)).toEqual(["c"]);
  });

  it("an empty list is an empty list, not an invented alert", () => {
    expect(rankAlerts([])).toEqual([]);
    expect(criticalAlerts([])).toEqual([]);
  });
});

// ---------------------------------------------------------------------------

describe("bottleneck ranking (by SUPPLIED score)", () => {
  it("orders by supplied score, highest first", () => {
    const ranked = rankBottlenecks({
      "N-1": bottleneck("N-1", 0.2),
      "N-2": bottleneck("N-2", 0.9),
    });
    expect(ranked.map((b) => b.nodeId)).toEqual(["N-2", "N-1"]);
  });

  it("a node with no supplied score sorts last and is NOT given one", () => {
    const ranked = rankBottlenecks({
      "N-1": bottleneck("N-1", null),
      "N-2": bottleneck("N-2", 0.1),
    });
    expect(ranked.map((b) => b.nodeId)).toEqual(["N-2", "N-1"]);
    expect(ranked[1]?.bottleneckScore).toBeNull();
  });

  it("no supplied bottleneck yields null, never a fabricated one", () => {
    expect(activeBottleneck({})).toBeNull();
  });
});

// ---------------------------------------------------------------------------

describe("actual versus safe speed — SAFETY CRITICAL", () => {
  it("flags a violation in TEXT when actual exceeds supplied safe", () => {
    const view = speedView(safety({ actualSpeed: 12, vSafe: 10 }));
    expect(view?.violation).toBe(true);
    expect(view?.violationText).toBe(OVER_SAFE_SPEED_TEXT);
    expect(view?.violationText).toBeTruthy();
  });

  it("does not flag when actual is within safe", () => {
    const view = speedView(safety({ actualSpeed: 8, vSafe: 10 }));
    expect(view?.violation).toBe(false);
    expect(view?.violationText).toBeNull();
  });

  it("equal speeds are not a violation", () => {
    expect(speedView(safety({ actualSpeed: 10, vSafe: 10 }))?.violation).toBe(false);
  });

  it("no supplied safe speed means NO violation marker — nothing to violate", () => {
    const view = speedView(safety({ actualSpeed: 99, vSafe: null }));
    expect(view?.safeSpeedUnavailable).toBe(true);
    expect(view?.violation).toBe(false);
    expect(view?.violationText).toBeNull();
    expect(view?.safeKmh).toBeNull();
  });

  it("never substitutes a safe speed when none was supplied", () => {
    expect(speedView(safety({ vSafe: null }))?.safeKmh).toBeNull();
  });

  it("converts both members of the pair with the same factor", () => {
    const view = speedView(safety({ actualSpeed: 10, vSafe: 20 }));
    expect(view?.actualKmh).toBeCloseTo(36);
    expect(view?.safeKmh).toBeCloseTo(72);
  });

  it("the comparison is made on supplied m/s, so unit formatting cannot change it", () => {
    // 11.1 m/s vs 11.0 m/s is a violation; both render as 40.0 vs 39.6 km/h.
    const view = speedView(safety({ actualSpeed: 11.1, vSafe: 11.0 }));
    expect(view?.violation).toBe(true);
  });

  it("returns null when no safety record exists at all", () => {
    expect(speedView(undefined)).toBeNull();
  });
});

// ---------------------------------------------------------------------------

describe("headway — AMB-001 units unresolved", () => {
  it("carries both numbers but performs NO comparison", () => {
    const view = headwayView(safety({ headwayCurrent: 41, hSafe: 60 }));
    expect(view?.current).toBe(41);
    expect(view?.hSafe).toBe(60);
    expect(view?.unitsUnresolved).toBe(true);
    // There is deliberately no `violation` field derived from these two numbers.
    expect(Object.keys(view ?? {})).not.toContain("derivedViolation");
  });

  it("uses the SUPPLIED violation flag when Task 2 provides one", () => {
    expect(headwayView(safety({ headwayViolation: true }))?.suppliedViolation).toBe(true);
    expect(headwayView(safety({ headwayViolation: false }))?.suppliedViolation).toBe(false);
  });

  it("reports null when Task 2 supplied no flag — it does not decide for itself", () => {
    expect(headwayView(safety({ headwayViolation: null }))?.suppliedViolation).toBeNull();
  });
});

// ---------------------------------------------------------------------------

describe("topology projection — supplied coordinates only", () => {
  it("derives bounds from supplied node coordinates", () => {
    const projection = projectTopology({
      version: "1",
      nodes: [
        { nodeId: "N-1", kind: "SHOVEL", label: "A", x: 100, y: 200 },
        { nodeId: "N-2", kind: "CRUSHER", label: "B", x: 300, y: 400 },
      ],
      segments: [],
    });
    expect(projection?.minX).toBe(60);
    expect(projection?.width).toBe(280);
  });

  it("returns null when no topology was supplied", () => {
    expect(projectTopology(null)).toBeNull();
  });

  it("returns null for an empty node list rather than an invented frame", () => {
    expect(projectTopology({ version: "1", nodes: [], segments: [] })).toBeNull();
  });
});

/**
 * A two-node, one-segment topology with SUPPLIED geometry. Every number a placement test
 * asserts on traces back to one of these literals or to a supplied `offsetM`.
 */
function topology(overrides: Partial<MineTopology> = {}): MineTopology {
  return {
    version: "1",
    nodes: [
      { nodeId: "N-1", kind: "SHOVEL", label: "A", x: 0, y: 0 },
      { nodeId: "N-2", kind: "CRUSHER", label: "B", x: 100, y: 200 },
    ],
    segments: [
      {
        segmentId: "S-1",
        fromNode: "N-1",
        toNode: "N-2",
        lengthM: 100,
        gradeRad: 0,
        bidirectional: true,
      },
    ],
    ...overrides,
  };
}

describe("resolvePosition — supplied coordinates (M4D-F path 1)", () => {
  it("uses supplied x/y exactly and marks the source SUPPLIED", () => {
    const result = resolvePosition(vehicle("V-1", 10, 20), topology());
    expect(result).toEqual({ ok: true, x: 10, y: 20, source: "SUPPLIED" });
  });

  it("supplied coordinates win over segment geometry — nothing is derived needlessly", () => {
    // The vehicle also carries segmentId S-1 and offsetM 12, which would place it
    // elsewhere. The supplied point must be used unchanged.
    const result = resolvePosition(vehicle("V-1", 7, 7), topology());
    expect(result).toMatchObject({ x: 7, y: 7, source: "SUPPLIED" });
  });
});

describe("resolvePosition — geometric transform (M4D-F path 2)", () => {
  it("places the marker at the supplied fraction along the supplied segment", () => {
    // offsetM 12 of lengthM 100 = 0.12 along (0,0) -> (100,200).
    const result = resolvePosition(vehicle("V-1", null, null), topology());
    expect(result).toEqual({ ok: true, x: 12, y: 24, source: "SEGMENT_GEOMETRY" });
  });

  it("output is determined SOLELY by supplied geometry and supplied offsetM", () => {
    // Same offset, different supplied endpoints: the point follows the geometry.
    const moved = topology({
      nodes: [
        { nodeId: "N-1", kind: "SHOVEL", label: "A", x: 1000, y: 500 },
        { nodeId: "N-2", kind: "CRUSHER", label: "B", x: 1100, y: 700 },
      ],
    });
    const result = resolvePosition(vehicle("V-1", null, null), moved);
    expect(result).toEqual({ ok: true, x: 1012, y: 524, source: "SEGMENT_GEOMETRY" });
  });

  it("is deterministic — identical inputs always give an identical point", () => {
    const v = vehicle("V-1", null, null);
    const a = resolvePosition(v, topology());
    const b = resolvePosition(v, topology());
    expect(a).toEqual(b);
  });

  it("reads no clock and no history — repeated calls do not advance the marker", () => {
    // A transform that moved with time would be movement interpolation, which M4D-F
    // explicitly prohibits.
    const v = vehicle("V-1", null, null);
    const first = resolvePosition(v, topology());
    for (let i = 0; i < 5; i += 1) {
      expect(resolvePosition(v, topology())).toEqual(first);
    }
  });

  it("offset 0 sits on the from-node's supplied coordinate", () => {
    const v = vehicle("V-1", null, null);
    v.position.offsetM = 0;
    expect(resolvePosition(v, topology())).toMatchObject({ x: 0, y: 0 });
  });

  it("offset equal to the supplied length sits on the to-node", () => {
    const v = vehicle("V-1", null, null);
    v.position.offsetM = 100;
    expect(resolvePosition(v, topology())).toMatchObject({ x: 100, y: 200 });
  });

  it("clamps an offset beyond the supplied length to the segment end", () => {
    // Clamping bounds the DISPLAY. It alters no supplied value, and a marker drawn
    // outside its own segment would misinform.
    const v = vehicle("V-1", null, null);
    v.position.offsetM = 5000;
    expect(resolvePosition(v, topology())).toMatchObject({ x: 100, y: 200 });
  });
});

describe("resolvePosition — insufficient geometry is never guessed", () => {
  function unavailable(mutate: (v: VehicleState) => void, top: MineTopology | null = topology()) {
    const v = vehicle("V-1", null, null);
    mutate(v);
    return resolvePosition(v, top);
  }

  it("no topology", () => {
    expect(unavailable(() => {}, null)).toEqual({ ok: false, reason: "NO_TOPOLOGY" });
  });

  it("no segment id", () => {
    expect(
      unavailable((v) => {
        v.position.segmentId = null;
      }),
    ).toEqual({
      ok: false,
      reason: "NO_SEGMENT_ID",
    });
  });

  it("segment not present in the supplied topology", () => {
    expect(
      unavailable((v) => {
        v.position.segmentId = "S-UNKNOWN";
      }),
    ).toEqual({
      ok: false,
      reason: "UNKNOWN_SEGMENT",
    });
  });

  it("no supplied offset", () => {
    expect(
      unavailable((v) => {
        v.position.offsetM = null;
      }),
    ).toEqual({
      ok: false,
      reason: "NO_OFFSET",
    });
  });

  it("an endpoint node missing from the supplied topology", () => {
    const broken = topology({
      nodes: [{ nodeId: "N-1", kind: "SHOVEL", label: "A", x: 0, y: 0 }],
    });
    expect(unavailable(() => {}, broken)).toEqual({
      ok: false,
      reason: "SEGMENT_ENDPOINT_MISSING",
    });
  });

  it("a non-positive supplied segment length", () => {
    const broken = topology({
      segments: [
        {
          segmentId: "S-1",
          fromNode: "N-1",
          toNode: "N-2",
          lengthM: 0,
          gradeRad: 0,
          bidirectional: true,
        },
      ],
    });
    expect(unavailable(() => {}, broken)).toEqual({
      ok: false,
      reason: "SEGMENT_LENGTH_MISSING",
    });
  });

  it("every failure names the specific missing input, in text", () => {
    for (const reason of [
      "NO_TOPOLOGY",
      "NO_SEGMENT_ID",
      "UNKNOWN_SEGMENT",
      "NO_OFFSET",
      "SEGMENT_ENDPOINT_MISSING",
      "SEGMENT_LENGTH_MISSING",
    ] as const) {
      expect(POSITION_UNAVAILABLE_REASON_TEXT[reason].length).toBeGreaterThan(0);
    }
  });

  it("never falls back to an endpoint, a midpoint or a previous point", () => {
    const result = unavailable((v) => {
      v.position.offsetM = null;
    });
    expect(result.ok).toBe(false);
    expect(result).not.toHaveProperty("x");
    expect(result).not.toHaveProperty("y");
  });
});

describe("placeVehicles", () => {
  it("places by supplied coordinates and by segment geometry alike", () => {
    const { placed, unplaced } = placeVehicles(
      { "V-1": vehicle("V-1", 10, 20), "V-2": vehicle("V-2", null, null) },
      topology(),
    );
    expect(placed.map((p) => p.vehicle.vehicleId)).toEqual(["V-1", "V-2"]);
    expect(placed[0]?.source).toBe("SUPPLIED");
    expect(placed[1]?.source).toBe("SEGMENT_GEOMETRY");
    expect(unplaced).toHaveLength(0);
  });

  it("never hides an unplaceable vehicle — it is listed with its reason", () => {
    const orphan = vehicle("V-9", null, null);
    orphan.position.segmentId = "S-MISSING";
    const { placed, unplaced } = placeVehicles(
      { "V-9": orphan, "V-2": vehicle("V-2", 1, 1) },
      topology(),
    );
    expect(placed.map((p) => p.vehicle.vehicleId)).toEqual(["V-2"]);
    expect(unplaced.map((u) => u.vehicle.vehicleId)).toEqual(["V-9"]);
    expect(unplaced[0]?.reason).toBe("UNKNOWN_SEGMENT");
  });

  it("treats a half-supplied coordinate as not supplied, then tries the geometry", () => {
    const half = vehicle("V-1", 10, null);
    const { placed } = placeVehicles({ "V-1": half }, topology());
    expect(placed[0]?.source).toBe("SEGMENT_GEOMETRY");
  });

  it("with no topology, only supplied coordinates can place a vehicle", () => {
    const { placed, unplaced } = placeVehicles(
      { "V-1": vehicle("V-1", 3, 4), "V-2": vehicle("V-2", null, null) },
      null,
    );
    expect(placed.map((p) => p.vehicle.vehicleId)).toEqual(["V-1"]);
    expect(unplaced[0]?.reason).toBe("NO_TOPOLOGY");
  });
});

// ---------------------------------------------------------------------------

describe("visibility selection", () => {
  it("selects the lowest supplied reading, without averaging", () => {
    const worst = worstVisibility({
      "S-1": {
        segmentId: "S-1",
        timestamp: T,
        visibility: { value: 300, sigma: 10 },
        friction: { value: 0.6, sigma: null },
        grade: 0,
        capacityVph: null,
        queue: null,
        utilization: null,
        surfaceState: null,
        roughness: null,
      },
      "S-2": {
        segmentId: "S-2",
        timestamp: T,
        visibility: { value: 80, sigma: 5 },
        friction: { value: 0.6, sigma: null },
        grade: 0,
        capacityVph: null,
        queue: null,
        utilization: null,
        surfaceState: null,
        roughness: null,
      },
    });
    expect(worst?.segmentId).toBe("S-2");
    expect(worst?.visibilityM).toBe(80);
  });

  it("returns null when nothing was supplied", () => {
    expect(worstVisibility({})).toBeNull();
  });
});

// ---------------------------------------------------------------------------

describe("fleet summary", () => {
  it("counts positioned, unpositioned and over-safe-speed vehicles", () => {
    const state = emptyAppState(T);
    state.vehicles = { "V-1": vehicle("V-1", 1, 1), "V-2": vehicle("V-2", null, null) };
    state.safety = {
      "V-1": safety({ vehicleId: "V-1", actualSpeed: 30, vSafe: 10 }),
      "V-2": safety({ vehicleId: "V-2", vSafe: null }),
    };

    const summary = fleetSummary(state);
    expect(summary.total).toBe(2);
    expect(summary.withPosition).toBe(1);
    expect(summary.withoutPosition).toBe(1);
    expect(summary.overSafeSpeed).toBe(1);
    expect(summary.safeSpeedUnavailable).toBe(1);
  });

  it("an empty fleet summarizes as zero, not as unknown", () => {
    expect(fleetSummary(emptyAppState(T)).total).toBe(0);
  });
});

describe("fmt", () => {
  it("renders an explicit marker for absent values, never 0", () => {
    expect(fmt(null)).toBe("—");
    expect(fmt(undefined)).toBe("—");
    expect(fmt(Number.NaN)).toBe("—");
  });

  it("renders 0 as 0 — a supplied zero is a value", () => {
    expect(fmt(0)).toBe("0.0");
  });
});

// ---------------------------------------------------------------------------
// M7 — dispatch and slots
// ---------------------------------------------------------------------------

function mkSlot(partial: Partial<SlotState> = {}): SlotState {
  return {
    slotId: "SL-1",
    resourceId: "N-SW-1",
    vehicleId: "V-1",
    startTime: "2026-01-01T00:00:30.000Z",
    endTime: "2026-01-01T00:01:30.000Z",
    status: "RESERVED",
    eta: null,
    conflictWith: null,
    ...partial,
  };
}

function mkCommand(partial: Partial<DispatchCommand> = {}): DispatchCommand {
  return {
    commandId: "C-1",
    vehicleId: "V-1",
    routeId: "R-1",
    departureTime: T,
    targetSpeed: 6,
    slotId: "SL-1",
    reasonCode: "REASON",
    timestamp: T,
    state: "RECOMMENDED",
    limitingVariables: null,
    routeNodeIds: null,
    ...partial,
  };
}

describe("rankDispatch — display ordering only", () => {
  it("orders by supplied timestamp, newest first", () => {
    const ordered = rankDispatch({
      a: mkCommand({ commandId: "a", timestamp: "2026-01-01T00:00:00.000Z" }),
      b: mkCommand({ commandId: "b", timestamp: "2026-01-01T00:00:09.000Z" }),
    });
    expect(ordered.map((c) => c.commandId)).toEqual(["b", "a"]);
  });

  it("breaks ties by command id, so the order is stable", () => {
    const ordered = rankDispatch({
      z: mkCommand({ commandId: "z" }),
      a: mkCommand({ commandId: "a" }),
    });
    expect(ordered.map((c) => c.commandId)).toEqual(["a", "z"]);
  });

  it("expresses no preference — every supplied command survives", () => {
    const ordered = rankDispatch({
      a: mkCommand({ commandId: "a", state: "REJECTED" }),
      b: mkCommand({ commandId: "b", state: "ISSUED" }),
    });
    expect(ordered).toHaveLength(2);
  });

  it("an empty map yields an empty list, never a fabricated command", () => {
    expect(rankDispatch({})).toEqual([]);
  });
});

describe("isReasonCodeMissing — NFR-006", () => {
  it("accepts a supplied non-empty code", () => {
    expect(isReasonCodeMissing("SWITCHBACK_CONTENTION")).toBe(false);
  });

  it("treats empty and whitespace-only as missing", () => {
    expect(isReasonCodeMissing("")).toBe(true);
    expect(isReasonCodeMissing("   ")).toBe(true);
  });
});

describe("slotTimeAxis — bounds come from supplied times only", () => {
  it("spans the earliest supplied start to the latest supplied end", () => {
    const result = slotTimeAxis([
      mkSlot({ startTime: "2026-01-01T00:00:30.000Z", endTime: "2026-01-01T00:01:30.000Z" }),
      mkSlot({
        slotId: "SL-2",
        startTime: "2026-01-01T00:01:00.000Z",
        endTime: "2026-01-01T00:02:00.000Z",
      }),
    ]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.axis.startMs).toBe(Date.parse("2026-01-01T00:00:30.000Z"));
    expect(result.axis.endMs).toBe(Date.parse("2026-01-01T00:02:00.000Z"));
  });

  it("produces evenly spaced ticks inside the supplied window", () => {
    const result = slotTimeAxis([mkSlot()]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.axis.ticks).toHaveLength(TIME_AXIS_TICKS);
    expect(result.axis.ticks[0]).toBe(result.axis.startMs);
    expect(result.axis.ticks[TIME_AXIS_TICKS - 1]).toBe(result.axis.endMs);
  });

  it("never extends the window to now or to a round number", () => {
    const result = slotTimeAxis([mkSlot()]);
    if (!result.ok) return;
    expect(result.axis.startMs).toBe(Date.parse("2026-01-01T00:00:30.000Z"));
    expect(result.axis.endMs).toBe(Date.parse("2026-01-01T00:01:30.000Z"));
  });

  it("is deterministic", () => {
    const slots = [mkSlot()];
    expect(slotTimeAxis(slots)).toEqual(slotTimeAxis(slots));
  });

  it("reports NO_SLOTS rather than inventing a window", () => {
    expect(slotTimeAxis([])).toEqual({ ok: false, reason: "NO_SLOTS" });
  });

  it("reports UNPARSEABLE_TIME for an unusable supplied timestamp", () => {
    expect(slotTimeAxis([mkSlot({ startTime: "nope" })])).toEqual({
      ok: false,
      reason: "UNPARSEABLE_TIME",
    });
  });

  it("reports ZERO_WINDOW when supplied times span nothing", () => {
    expect(slotTimeAxis([mkSlot({ startTime: T, endTime: T })])).toEqual({
      ok: false,
      reason: "ZERO_WINDOW",
    });
  });

  it("returns no coordinates on any failure path", () => {
    expect(slotTimeAxis([])).not.toHaveProperty("axis");
  });
});

describe("groupSlotsByResource — grouping and lane packing", () => {
  const overlapping = {
    "SL-1": mkSlot(),
    "SL-2": mkSlot({
      slotId: "SL-2",
      vehicleId: "V-2",
      startTime: "2026-01-01T00:01:00.000Z",
      endTime: "2026-01-01T00:02:00.000Z",
      status: "CONFLICT" as const,
      conflictWith: ["SL-1"],
    }),
  };

  it("groups by supplied resourceId", () => {
    const groups = groupSlotsByResource({
      "SL-1": mkSlot(),
      "SL-9": mkSlot({ slotId: "SL-9", resourceId: "N-INT-2" }),
    });
    expect(groups.map((g) => g.resourceId)).toEqual(["N-INT-2", "N-SW-1"]);
  });

  it("puts overlapping slots in separate lanes (FR-009 AC4)", () => {
    const [group] = groupSlotsByResource(overlapping);
    expect(group?.laneCount).toBe(2);
    expect(group?.bands.map((b) => b.lane)).toEqual([0, 1]);
  });

  it("reuses a lane when slots do not overlap", () => {
    const [group] = groupSlotsByResource({
      "SL-1": mkSlot(),
      "SL-2": mkSlot({
        slotId: "SL-2",
        startTime: "2026-01-01T00:02:00.000Z",
        endTime: "2026-01-01T00:03:00.000Z",
      }),
    });
    expect(group?.laneCount).toBe(1);
    expect(group?.bands.map((b) => b.lane)).toEqual([0, 0]);
  });

  it("positions bands from supplied times as a fraction of the supplied window", () => {
    const [group] = groupSlotsByResource(overlapping);
    // Window 00:00:30 -> 00:02:00 = 90 s. SL-1 starts at 0 s and runs 60 s.
    expect(group?.bands[0]?.left).toBeCloseTo(0);
    expect(group?.bands[0]?.width).toBeCloseTo(60 / 90);
    expect(group?.bands[1]?.left).toBeCloseTo(30 / 90);
  });

  it("is deterministic across repeated calls", () => {
    expect(groupSlotsByResource(overlapping)).toEqual(groupSlotsByResource(overlapping));
  });

  it("flags a group carrying a supplied conflict", () => {
    expect(groupSlotsByResource(overlapping)[0]?.hasConflict).toBe(true);
    expect(groupSlotsByResource({ "SL-1": mkSlot() })[0]?.hasConflict).toBe(false);
  });

  it("produces no bands when the axis is unusable, and does not guess", () => {
    const [group] = groupSlotsByResource({ "SL-1": mkSlot({ startTime: "nope" }) });
    expect(group?.axis.ok).toBe(false);
    expect(group?.bands).toEqual([]);
  });

  it("never invents, merges, moves or drops a supplied slot", () => {
    const [group] = groupSlotsByResource(overlapping);
    expect(group?.slots.map((s) => s.slotId).sort()).toEqual(["SL-1", "SL-2"]);
  });
});

describe("conflictingSlots — a filter over supplied values", () => {
  it("selects slots whose supplied status is CONFLICT", () => {
    const list = conflictingSlots({
      "SL-1": mkSlot(),
      "SL-2": mkSlot({ slotId: "SL-2", status: "CONFLICT" }),
    });
    expect(list.map((s) => s.slotId)).toEqual(["SL-2"]);
  });

  it("selects slots naming a supplied conflictWith, whatever their status", () => {
    const list = conflictingSlots({
      "SL-3": mkSlot({ slotId: "SL-3", status: "RESERVED", conflictWith: ["SL-1"] }),
    });
    expect(list).toHaveLength(1);
  });

  it("detects nothing on its own — no supplied conflict means no conflict", () => {
    expect(conflictingSlots({ "SL-1": mkSlot(), "SL-2": mkSlot({ slotId: "SL-2" }) })).toEqual([]);
  });

  it("ignores an empty conflictWith list", () => {
    expect(conflictingSlots({ "SL-1": mkSlot({ conflictWith: [] }) })).toEqual([]);
  });

  it("is deterministically ordered by slot id", () => {
    const list = conflictingSlots({
      "SL-9": mkSlot({ slotId: "SL-9", status: "CONFLICT" }),
      "SL-2": mkSlot({ slotId: "SL-2", status: "CONFLICT" }),
    });
    expect(list.map((s) => s.slotId)).toEqual(["SL-2", "SL-9"]);
  });
});
