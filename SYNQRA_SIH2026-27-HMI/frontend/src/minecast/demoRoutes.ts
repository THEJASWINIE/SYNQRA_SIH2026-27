/**
 * Demonstration routes — where the two Digital Twin trucks drive (MINECAST-02).
 *
 * ==========================================================================
 *  SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE
 *
 *  A route here is a sequence of SCENE_METRES waypoints COMPOSED FROM the existing
 *  synthetic corridors in `haulRoads.ts`. Nothing is drawn anew and nothing is guessed
 *  about the real mine: the trucks drive on the same invented roads the scene already
 *  renders and already discloses. Every route carries the corridors' own provenance.
 * ==========================================================================
 *
 * ONE GEOMETRY OWNER, TWO CONSUMERS
 *
 * The corridor geometry is procedural TypeScript (Bezier alignments, the pit's own
 * switchback). Re-implementing it in Python would be a second geometry engine that could
 * drift from the first. So this module is the single owner, and the backend simulation
 * (`scene_position_sim.py`) follows an EXPORTED copy of these routes:
 *
 *   demoRoutes()  ->  scripts/exportSceneRoutes.ts  ->  contracts/scene_routes.json
 *                                                          ^ read by the backend
 *
 * `demoRoutes.test.ts` asserts the committed JSON equals what this module generates, so
 * an edit here without a re-export fails the suite rather than silently desynchronising
 * the trucks from the roads.
 *
 * Pure and framework-free. No Three.js, no React, no `Math.random`.
 */

import {
  CORRIDOR_ID,
  CORRIDOR_PROVENANCE,
  type HaulCorridor,
  haulCorridors,
  ROUTE_CLASSIFICATION,
} from "./haulRoads";
import type { TerrainConfig } from "./terrainField";

/** A scene-metres waypoint: [east, north] from the published extent's south-west corner. */
export type Waypoint = readonly [number, number];

/**
 * What a truck does at the end of its route.
 *
 *   PING_PONG   drive to the far end and come back the same way - a haul cycle. The only
 *               behaviour used today, because none of the corridor networks close into a
 *               loop and inventing a return road would put a truck off the drawn network.
 *   LOOP        wrap smoothly from the last waypoint to the first. Declared so the
 *               follower is total over the vocabulary; unused until a closed corridor exists.
 */
export type RouteBehaviour = "PING_PONG" | "LOOP";

/**
 * One leg of a route: a slice of a corridor centreline between two of its indices.
 * `from > to` drives the corridor in reverse. Junction indices come from the corridor's
 * own `junctions`, so a leg starts exactly where the previous one ended.
 */
export interface RouteLeg {
  readonly corridorId: string;
  readonly from: number;
  readonly to: number;
}

/**
 * MINE-ROUTES-02: the stamp every route carries. The route is followed by the SIMULATION
 * and surfaces on the Twin as `position_scene` with exactly this provenance; nothing on it
 * is measured or surveyed.
 */
export const ROUTE_METADATA = {
  source: "SIMULATION",
  provenance: "SIMULATED_TWIN_SCENE",
  frame: "SCENE_METRES",
  method: "DIGITAL_TWIN_SCENE_SIM",
  classification: ROUTE_CLASSIFICATION,
} as const;

export interface DemoRoute {
  readonly routeId: string;
  readonly vehicleId: string;
  /** Engineering label for the plan, e.g. `T01 ORE CYCLE`. */
  readonly label: string;
  readonly behaviour: RouteBehaviour;
  readonly metadata: typeof ROUTE_METADATA;
  /** The legs the waypoints were composed from, in order. */
  readonly legs: readonly RouteLeg[];
  /** Demonstration travel speed along the route, metres per second. A declared parameter. */
  readonly speedMps: number;
  /** Where along the route the truck is at simulation time zero, metres from waypoint 0. */
  readonly startProgressM: number;
  /** The corridors the waypoints were taken from, in order. */
  readonly corridorIds: readonly string[];
  readonly waypoints: readonly Waypoint[];
  /** Total polyline length, metres. */
  readonly lengthM: number;
}

export const ROUTE_DISCLOSURE = `${CORRIDOR_PROVENANCE.disclosure} · SYNTHETIC DIGITAL TWIN ROUTE · NOT A SURVEY`;

function polylineLength(points: readonly Waypoint[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i += 1) {
    const [x0, y0] = points[i - 1] as Waypoint;
    const [x1, y1] = points[i] as Waypoint;
    total += Math.hypot(x1 - x0, y1 - y0);
  }
  return total;
}

function corridorById(corridors: readonly HaulCorridor[], id: string): HaulCorridor {
  const found = corridors.find((c) => c.id === id);
  if (!found) {
    throw new Error(`demo route needs corridor ${id}, which haulCorridors() did not produce`);
  }
  return found;
}

/** A named junction index of a corridor, which must exist. */
function junction(corridor: HaulCorridor, name: string): number {
  const index = corridor.junctions[name];
  if (index === undefined) throw new Error(`corridor ${corridor.id} has no junction ${name}`);
  return index;
}

/**
 * Compose legs end to end into one polyline. Each leg is a slice of a corridor centreline
 * (reversed when `from > to`); a point equal to the previous one - the shared junction -
 * is dropped rather than producing a zero-length segment.
 */
function composed(corridors: readonly HaulCorridor[], legs: readonly RouteLeg[]): Waypoint[] {
  const out: Waypoint[] = [];
  for (const leg of legs) {
    const line = corridorById(corridors, leg.corridorId).centreline;
    const step = leg.from <= leg.to ? 1 : -1;
    for (let i = leg.from; step > 0 ? i <= leg.to : i >= leg.to; i += step) {
      const point = line[i];
      if (!point) throw new Error(`leg ${leg.corridorId} index ${i} is off the centreline`);
      const last = out[out.length - 1];
      if (last && Math.hypot(last[0] - point.x, last[1] - point.y) < 1e-6) continue;
      out.push([point.x, point.y]);
    }
  }
  return out;
}

function route(
  routeId: string,
  vehicleId: string,
  label: string,
  behaviour: RouteBehaviour,
  speedMps: number,
  startProgressM: number,
  corridors: readonly HaulCorridor[],
  legs: readonly RouteLeg[],
): DemoRoute {
  const waypoints = composed(corridors, legs);
  const corridorIds = [...new Set(legs.map((leg) => leg.corridorId))];
  if (waypoints.length < 2) throw new Error(`route ${routeId} needs at least two waypoints`);
  if (behaviour === "LOOP") {
    const first = waypoints[0] as Waypoint;
    const last = waypoints[waypoints.length - 1] as Waypoint;
    if (Math.hypot(first[0] - last[0], first[1] - last[1]) > 1e-6) {
      throw new Error(`route ${routeId} is a LOOP but does not end where it starts`);
    }
  }
  const lengthM = polylineLength(waypoints);
  if (startProgressM < 0 || startProgressM > lengthM) {
    throw new Error(
      `route ${routeId}: start progress ${startProgressM} m is off a ${lengthM} m route`,
    );
  }
  return {
    routeId,
    vehicleId,
    label,
    behaviour,
    metadata: ROUTE_METADATA,
    legs,
    speedMps,
    startProgressM,
    corridorIds,
    waypoints,
    lengthM,
  };
}

/** Route ids. Exported so the plan, the scene and the tests name them once. */
export const ROUTE_ID = {
  T01: "SYNTH-ROUTE-T01-ORE-CYCLE",
  T02: "SYNTH-ROUTE-T02-DISPATCH-SHUTTLE",
} as const;

/**
 * The two demonstration routes, composed from the corridor network's named junctions.
 *
 *   TRUCK_01  ORE CYCLE (LOOP): pit access -> PIT RAMP down -> LOADING LOOP around the
 *             working area -> PIT RAMP up -> MAIN HAUL rim road -> ORE DISPATCH to the
 *             stockpile -> back along ORE DISPATCH and the rim road to the access, where
 *             the cycle wraps. Loaded out of the pit, empty back in.
 *   TRUCK_02  DISPATCH SHUTTLE (PING_PONG): waste dump -> SERVICE ROAD -> MAIN HAUL
 *             (approach past the access, then the rim road) -> ORE DISPATCH to the
 *             stockpile, and back the same way.
 *
 * Speeds and start offsets are round demonstration numbers, chosen so the two trucks are
 * not at the same place at the same time on the shared rim road. They are not measured
 * from anything and are not claimed to be.
 */
export function demoRoutes(config: TerrainConfig): readonly DemoRoute[] {
  const corridors = haulCorridors(config);
  const main = corridorById(corridors, CORRIDOR_ID.MAIN);
  const ramp = corridorById(corridors, CORRIDOR_ID.RAMP);
  const loop = corridorById(corridors, CORRIDOR_ID.LOOP);
  const dispatch = corridorById(corridors, CORRIDOR_ID.DISPATCH);
  const service = corridorById(corridors, CORRIDOR_ID.SERVICE);
  const leg = (c: HaulCorridor, from: string, to: string): RouteLeg => ({
    corridorId: c.id,
    from: junction(c, from),
    to: junction(c, to),
  });
  const loopEnd = loop.centreline.length - 1;

  return [
    route(ROUTE_ID.T01, "TRUCK_01", "T01 ORE CYCLE", "LOOP", 8.0, 250, corridors, [
      leg(ramp, "ACCESS", "FOOT"),
      { corridorId: loop.id, from: 0, to: loopEnd },
      leg(ramp, "FOOT", "ACCESS"),
      leg(main, "ACCESS", "RIM_END"),
      leg(dispatch, "RIM", "STOCKPILE"),
      leg(dispatch, "STOCKPILE", "RIM"),
      leg(main, "RIM_END", "ACCESS"),
    ]),
    route(ROUTE_ID.T02, "TRUCK_02", "T02 DISPATCH SHUTTLE", "PING_PONG", 6.5, 200, corridors, [
      leg(service, "DUMP", "MAIN"),
      leg(main, "SERVICE", "RIM_END"),
      leg(dispatch, "RIM", "STOCKPILE"),
    ]),
  ];
}

// ---------------------------------------------------------------------------
// the exported contract
// ---------------------------------------------------------------------------

/** The shape written to `contracts/scene_routes.json` and read by the backend. */
export interface SceneRoutesDocument {
  readonly _provenance: {
    readonly source: string;
    readonly disclosure: string;
    readonly route_classification: typeof ROUTE_CLASSIFICATION;
    readonly frame: "SCENE_METRES";
    readonly generated_by: string;
    readonly geometry_owner: string;
    readonly extent_m: { readonly width: number; readonly height: number };
    readonly note: string;
  };
  readonly routes: readonly {
    readonly route_id: string;
    readonly vehicle_id: string;
    readonly label: string;
    readonly classification: typeof ROUTE_CLASSIFICATION;
    readonly metadata: typeof ROUTE_METADATA;
    readonly legs: readonly RouteLeg[];
    readonly behaviour: RouteBehaviour;
    readonly speed_mps: number;
    readonly start_progress_m: number;
    readonly corridor_ids: readonly string[];
    readonly length_m: number;
    readonly waypoints: readonly (readonly [number, number])[];
  }[];
}

const round3 = (value: number) => Math.round(value * 1000) / 1000;

export function toSceneRoutesDocument(config: TerrainConfig): SceneRoutesDocument {
  return {
    _provenance: {
      source: CORRIDOR_PROVENANCE.source,
      disclosure: ROUTE_DISCLOSURE,
      route_classification: ROUTE_CLASSIFICATION,
      frame: "SCENE_METRES",
      generated_by: "frontend/scripts/exportSceneRoutes.ts",
      geometry_owner: "frontend/src/minecast/haulRoads.ts (via demoRoutes.ts)",
      extent_m: { width: round3(config.widthM), height: round3(config.heightM) },
      note:
        "Invented demonstration routes composed from the scene's synthetic corridors. NOT NMDC " +
        "haul roads, not surveyed, not inferred from the real mine. Regenerate with " +
        "`npx vite-node scripts/exportSceneRoutes.ts` whenever the corridors change; " +
        "demoRoutes.test.ts fails if this file is stale.",
    },
    routes: demoRoutes(config).map((r) => ({
      route_id: r.routeId,
      vehicle_id: r.vehicleId,
      label: r.label,
      classification: ROUTE_CLASSIFICATION,
      metadata: r.metadata,
      legs: r.legs,
      behaviour: r.behaviour,
      speed_mps: r.speedMps,
      start_progress_m: r.startProgressM,
      corridor_ids: r.corridorIds,
      length_m: round3(r.lengthM),
      waypoints: r.waypoints.map(([x, y]) => [round3(x), round3(y)] as const),
    })),
  };
}
