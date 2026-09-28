/**
 * One-time bookkeeping: writes the 50-vehicle / 20-node scale scenario.
 *
 * APPROVED SCOPE (MID / M3 correction pass): this script is an editor, not a runtime
 * generator. The committed JSON it produces is the authoritative artifact. Nothing in the
 * application imports or runs this file.
 *
 * It contains CONSTANTS ONLY. Explicitly absent, by requirement:
 *   - physics or kinematics
 *   - trajectory calculations
 *   - spacing formulas
 *   - queue models or queue evolution
 *   - random generation
 *
 * Vehicles are placed by cycling a fixed, hand-written list of segments and by repeating
 * a fixed, hand-written list of authored value sets. Index arithmetic selects WHICH
 * authored constant to use; it never computes an operational value.
 *
 * Run:  node scripts/generate-scale-scenario.mjs
 */

import { writeFileSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const MOCKS = join(HERE, "..", "frontend", "src", "mocks");
const OUT = join(MOCKS, "scenarios", "scale.json");

const topology = JSON.parse(readFileSync(join(MOCKS, "topology.json"), "utf-8"));

/** Hand-written segment rotation. Placement only — not a route or a trajectory. */
const SEGMENTS = ["S-1", "S-5", "S-6", "S-8", "S-9", "S-11", "S-13", "S-15", "S-18", "S-20"];

/**
 * Hand-written authored value sets. Each row is a complete set of operational constants
 * chosen by hand. Vehicle N uses row (N mod 5). No value is derived from another.
 */
const VALUE_SETS = [
  { speed: 8.0, grade: 0.00, friction: 0.62, sigma: 0.04, vSafe: 11.0, hSafe: 45.0, headway: 60.0, constraint: "NONE", risk: "LOW", mode: "NORMAL" },
  { speed: 7.0, grade: 0.05, friction: 0.60, sigma: 0.05, vSafe: 10.0, hSafe: 45.0, headway: 55.0, constraint: "GRADE", risk: "LOW", mode: "NORMAL" },
  { speed: 6.0, grade: 0.08, friction: 0.58, sigma: 0.05, vSafe: 8.0, hSafe: 50.0, headway: 48.0, constraint: "GRADE", risk: "MODERATE", mode: "NORMAL" },
  { speed: 5.0, grade: 0.02, friction: 0.45, sigma: 0.08, vSafe: 7.0, hSafe: 55.0, headway: 42.0, constraint: "FRICTION", risk: "MODERATE", mode: "CAUTION" },
  { speed: 9.0, grade: -0.03, friction: 0.65, sigma: 0.03, vSafe: 12.0, hSafe: 40.0, headway: 70.0, constraint: "NONE", risk: "LOW", mode: "NORMAL" },
];

const VEHICLE_COUNT = 50;

const vehicles = [];
const safety = [];

for (let n = 1; n <= VEHICLE_COUNT; n++) {
  const id = `V-${n}`;
  // Index selection only — picks which authored constant applies to this vehicle.
  const v = VALUE_SETS[n % VALUE_SETS.length];
  const segment = SEGMENTS[n % SEGMENTS.length];

  vehicles.push({
    vehicle_id: id,
    timestamp: "@now",
    position: { x: null, y: null, segment_id: segment, offset_m: 10.0 },
    speed_mps: v.speed,
    accel_mps2: 0.0,
    grade_rad: v.grade,
    friction_est: { value: v.friction, sigma: v.sigma },
    mode: v.mode,
    comm_confidence: 1.0,
    vehicle_kind: "TRUCK",
    route_id: "R-1",
  });

  safety.push({
    vehicle_id: id,
    timestamp: "@now",
    v_safe: v.vSafe,
    h_safe: v.hSafe,
    actual_speed: v.speed,
    headway_current: v.headway,
    lead_vehicle_id: null,
    active_constraint: v.constraint,
    risk_level: v.risk,
    headway_violation: false,
    envelope_violation: false,
  });
}

/** One authored road state per segment in the rotation. */
const ROAD_VALUES = [
  { visibility: 900.0, vSigma: 25.0, friction: 0.62, fSigma: 0.04, surface: "DRY" },
  { visibility: 750.0, vSigma: 30.0, friction: 0.60, fSigma: 0.05, surface: "DRY" },
  { visibility: 500.0, vSigma: 35.0, friction: 0.55, fSigma: 0.06, surface: "WET" },
];

const road = topology.segments.map((segment, i) => {
  const r = ROAD_VALUES[i % ROAD_VALUES.length];
  return {
    segment_id: segment.segment_id,
    timestamp: "@now",
    visibility: { value: r.visibility, sigma: r.vSigma },
    friction: { value: r.friction, sigma: r.fSigma },
    grade: segment.grade_rad,
    capacity_vph: 60.0,
    queue: null,
    utilization: null,
    surface_state: r.surface,
    roughness: null,
  };
});

const scenario = {
  id: "scale",
  name: "Scale — 50 vehicles, 20 nodes",
  description:
    "NFR-009 scale fixture. 50 authored vehicles across the 20-node topology. Generated once by scripts/generate-scale-scenario.mjs from hand-written constants; this JSON is the authoritative artifact.",
  family: "test",
  provider: "MOCK",
  stepIntervalMs: 1000,
  steps: [
    {
      index: 0,
      atMs: 0,
      emit: {
        MineTopology: [topology],
        SystemHealth: [
          {
            timestamp: "@now",
            system_mode: "NORMAL",
            connectivity: "CONNECTED",
            fleet_count: VEHICLE_COUNT,
            components: [
              {
                component_id: "LINK-V2I",
                timestamp: "@now",
                state: "UP",
                latency_ms: 12.0,
                age_ms: 40.0,
                error_code: null,
                link_kind: "V2I",
                messages_received: 100.0,
                messages_dropped: 0.0,
              },
            ],
          },
        ],
      },
    },
    { index: 1, atMs: 1000, emit: { VehicleState: vehicles, SafetyState: safety } },
    { index: 2, atMs: 2000, emit: { RoadState: road } },
  ],
};

writeFileSync(OUT, `${JSON.stringify(scenario, null, 2)}\n`, "utf-8");
console.log(
  `wrote ${OUT}: ${vehicles.length} vehicles, ${topology.nodes.length} nodes, ${road.length} segments`,
);
