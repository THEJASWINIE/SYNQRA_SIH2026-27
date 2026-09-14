/**
 * Vehicle position providers — geospatial Digital Twin prototype.
 *
 * ==========================================================================
 *  THERE IS NO PHYSICAL POSITIONING SOURCE ON THIS PROTOTYPE.
 *
 *  No GNSS receiver exists on either vehicle. `position` and `heading` are in the
 *  ingestor's `NEVER_FROM_HARDWARE` set. Therefore the PHYSICAL provider returns
 *  UNAVAILABLE - always, unconditionally, with no fallback path to a simulated value.
 *
 *  A geographic coordinate is NEVER derived from wheel RPM, from speed, from elapsed
 *  time or from anything else this prototype measures. Dead reckoning from a wheel
 *  encoder without an absolute fix accumulates unbounded error, and a truck shown at a
 *  confidently wrong coordinate is worse than a truck not shown at all.
 * ==========================================================================
 *
 * THE THREE MODES ARE ISOLATED BY CONSTRUCTION
 *
 *   LIVE       -> PhysicalVehiclePositionProvider   always UNAVAILABLE
 *   SIMULATION -> SimulatedVehiclePositionProvider  deterministic, marked SIMULATED
 *   REPLAY     -> ReplayVehiclePositionProvider     recorded, marked REPLAY
 *
 * `providerForMode` is a total function over the three modes with no default branch, so
 * LIVE cannot silently acquire simulated positions. That is asserted in the tests.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { VehicleState } from "../contracts/domain";
import { type DecimalExtent, type LonLat, unprojectFromLocalMetres } from "./geoSite";

/** How a position was obtained. Distinct from the geographic provenance of a feature. */
export type PositionProvenance =
  | "PHYSICAL"
  | "SIMULATED"
  | "REPLAY"
  | "UNAVAILABLE"
  | "SOFTWARE_ONLY_SYNTHETIC"
  /**
   * MAP-02: a Digital Twin DEMONSTRATION pose the canonical Twin supplied in
   * SCENE_METRES. Invented for the demonstration, never measured, and never a fix.
   */
  | "SIMULATED_TWIN_SCENE";

export interface VehiclePosition {
  vehicleId: string;
  /** Null whenever no position exists. Never a placeholder coordinate. */
  position: LonLat | null;
  provenance: PositionProvenance;
  /** Why a position is absent, stated rather than implied. */
  reason?: string | undefined;
  /** Canonical heading in radians, when supplied. */
  headingRad?: number | null | undefined;
  /** MINE-ROUTES-02: Twin-supplied route metadata for a scene pose. Null when absent. */
  routeId?: string | null | undefined;
  routeDirection?: number | null | undefined;
}

/**
 * The interface a future real positioning source would implement.
 *
 * Adding GNSS later means adding one implementation here; no screen changes.
 */
export interface VehiclePositionProvider {
  readonly kind: PositionProvenance;
  positionFor(vehicle: VehicleState): VehiclePosition;
}

export const NO_PHYSICAL_POSITION_REASON =
  "No positioning hardware on this vehicle. Position is never derived from wheel RPM.";

/**
 * LIVE. Always UNAVAILABLE.
 *
 * Deliberately has no access to the site extent, so it is structurally incapable of
 * producing a coordinate even if someone later edited it carelessly.
 */
export class PhysicalVehiclePositionProvider implements VehiclePositionProvider {
  readonly kind = "PHYSICAL" as const;

  positionFor(vehicle: VehicleState): VehiclePosition {
    const gnss = vehicle.positionGnss;
    if (
      gnss &&
      (gnss.status === "VALID" || gnss.status === "OK" || gnss.status === "FIX") &&
      typeof gnss.latitude === "number" &&
      Number.isFinite(gnss.latitude) &&
      typeof gnss.longitude === "number" &&
      Number.isFinite(gnss.longitude) &&
      gnss.latitude >= -90 &&
      gnss.latitude <= 90 &&
      gnss.longitude >= -180 &&
      gnss.longitude <= 180
    ) {
      const origin = gnss.origin ?? vehicle.provenance?.position_gnss?.origin;
      const isSynthetic = origin === "SOFTWARE_ONLY" || origin === "SOFTWARE_ONLY_SYNTHETIC" || origin === "SIMULATION";
      return {
        vehicleId: vehicle.vehicleId,
        position: { lon: gnss.longitude, lat: gnss.latitude },
        provenance: isSynthetic ? "SOFTWARE_ONLY_SYNTHETIC" as PositionProvenance : "PHYSICAL",
        reason: isSynthetic ? "SOFTWARE TEST · SYNTHETIC GNSS" : "Physical GNSS fix",
      };
    }

    return {
      vehicleId: vehicle.vehicleId,
      position: null,
      provenance: "UNAVAILABLE",
      reason: NO_PHYSICAL_POSITION_REASON,
    };
  }
}

/** Deterministic hash of a vehicle id, so a demo is reproducible across runs. */
function hashId(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return hash;
}

/**
 * SIMULATION. Places a vehicle inside the demonstration extent.
 *
 * Marked SIMULATED on every single position it returns. Deterministic from the vehicle id
 * so the demo is reproducible and so nothing drifts about the map for no reason.
 *
 * These coordinates are INVENTED. They are not where any truck is.
 */
export class SimulatedVehiclePositionProvider implements VehiclePositionProvider {
  readonly kind = "SIMULATED" as const;

  constructor(private readonly extent: DecimalExtent) {}

  positionFor(vehicle: VehicleState): VehiclePosition {
    const hash = hashId(vehicle.vehicleId);
    // Kept away from the extent edges so markers stay legible against the border.
    const fx = 0.2 + ((hash % 1000) / 1000) * 0.6;
    const fy = 0.2 + (((hash >> 10) % 1000) / 1000) * 0.6;
    return {
      vehicleId: vehicle.vehicleId,
      position: {
        lon: this.extent.west + (this.extent.east - this.extent.west) * fx,
        lat: this.extent.south + (this.extent.north - this.extent.south) * fy,
      },
      provenance: "SIMULATED",
      reason: "Simulated position. Not a measurement of any physical vehicle.",
    };
  }
}

/**
 * REPLAY. Returns a recorded position, marked REPLAY.
 *
 * A replayed position is historical. It is never promoted to PHYSICAL, and it is never
 * presented as the vehicle's current location.
 */
export class ReplayVehiclePositionProvider implements VehiclePositionProvider {
  readonly kind = "REPLAY" as const;

  constructor(private readonly recorded: Record<string, LonLat>) {}

  positionFor(vehicle: VehicleState): VehiclePosition {
    const recorded = this.recorded[vehicle.vehicleId];
    if (!recorded) {
      return {
        vehicleId: vehicle.vehicleId,
        position: null,
        provenance: "UNAVAILABLE",
        reason: "No recorded position for this vehicle in the replay.",
      };
    }
    return {
      vehicleId: vehicle.vehicleId,
      position: recorded,
      provenance: "REPLAY",
      reason: "Recorded position. Historical, not current.",
    };
  }
}

/** The HMI's three system modes, matching `AppState.connection.provider`. */
export type SystemMode = "LIVE" | "MOCK" | "REPLAY";

/**
 * Select the provider for a mode.
 *
 * Exhaustive over the three modes with NO default branch: LIVE maps to PHYSICAL and
 * nothing else can. Any future mode forces a compile error rather than silently
 * inheriting simulated behaviour.
 */
export function providerForMode(
  mode: SystemMode,
  extent: DecimalExtent,
  recorded: Record<string, LonLat> = {},
): VehiclePositionProvider {
  switch (mode) {
    case "LIVE":
      return new PhysicalVehiclePositionProvider();
    case "MOCK":
      return new SimulatedVehiclePositionProvider(extent);
    case "REPLAY":
      return new ReplayVehiclePositionProvider(recorded);
  }
}

/** Positions for a fleet, in a stable order. */
export function positionsFor(
  vehicles: Record<string, VehicleState>,
  provider: VehiclePositionProvider,
): VehiclePosition[] {
  return Object.keys(vehicles)
    .sort()
    .map((id) => provider.positionFor(vehicles[id] as VehicleState));
}

// ---------------------------------------------------------------------------
// MAP-02 — the Digital Twin demonstration scene pose
// ---------------------------------------------------------------------------

/** The label a Twin scene pose carries wherever it is shown. Never says GNSS. */
export const TWIN_SCENE_LABEL = "SIMULATION · DIGITAL TWIN";

/** The only frame a drawable scene pose may be expressed in. */
export const SCENE_FRAME = "SCENE_METRES";

/**
 * A Digital Twin DEMONSTRATION position, when the canonical Twin supplied one.
 *
 * ==========================================================================
 *  THIS IS THE ONE PLACE SCENE_METRES BECOMES A MAP COORDINATE.
 *
 *  The Twin supplies metres east/north of the published extent's south-west corner
 *  (`scene_position_sim` on the backend). Turning that into a lon/lat needs the extent
 *  and nothing else - no vehicle id, no hardcoded coordinate, no per-screen maths - so
 *  it happens here and every screen consumes the result.
 *
 *  THE REFUSALS, all of which leave the vehicle undrawn rather than plausible:
 *    * a pose in any frame other than SCENE_METRES
 *    * a pose whose status is not VALID
 *    * a pose without finite numbers
 *    * a pose CLAIMING a physical/hardware origin - a scene coordinate is invented by
 *      construction, so a hardware claim on one is a contradiction, not evidence
 * ==========================================================================
 *
 * The result is stamped `SIMULATED_TWIN_SCENE` and captioned SIMULATION · DIGITAL TWIN.
 * It is never labelled GNSS, GPS, physical, surveyed or hardware-derived.
 */
export function twinScenePosition(
  vehicle: VehicleState,
  extent: DecimalExtent,
): VehiclePosition | null {
  const scene = drawableScenePose(vehicle);
  if (!scene) return null;

  const southWest: LonLat = { lon: extent.west, lat: extent.south };
  return {
    vehicleId: vehicle.vehicleId,
    position: unprojectFromLocalMetres({ x: scene.xM, y: scene.yM }, southWest),
    provenance: "SIMULATED_TWIN_SCENE",
    reason: scene.reason,
    headingRad: scene.headingRad,
    routeId: scene.routeId,
    routeDirection: scene.routeDirection,
  };
}

/** A scene pose the Twin supplied and this application is willing to draw. */
export interface DrawableScenePose {
  /** Metres east of the published extent's south-west corner. */
  readonly xM: number;
  /** Metres north of the same corner. */
  readonly yM: number;
  readonly headingRad: number | null;
  /** Always SCENE_METRES — a pose in any other frame is refused, not converted. */
  readonly frame: string;
  readonly method: string;
  readonly provenanceLabel: string;
  readonly reason: string;
  /** Twin-supplied route metadata, when present. */
  readonly routeId: string | null;
  readonly routeDirection: number | null;
}

/**
 * THE one validator for a Twin scene pose. Both consumers go through it.
 *
 * The 2D site map (`twinScenePosition`) turns the result into a lon/lat; Mine-Cast's 3D
 * scene consumes the scene metres directly, since its terrain is built in this very
 * frame. Sharing this function is what stops the two views from ever disagreeing about
 * whether a truck may be drawn, or about where it is.
 *
 * Returns null - drawing nothing - for every case in the refusal list on
 * `twinScenePosition`.
 */
export function drawableScenePose(vehicle: VehicleState): DrawableScenePose | null {
  const scene = vehicle.positionScene;
  if (!scene) return null;
  if (scene.frame !== SCENE_FRAME) return null;
  if (scene.status !== "VALID") return null;
  if (
    typeof scene.xM !== "number" ||
    typeof scene.yM !== "number" ||
    !Number.isFinite(scene.xM) ||
    !Number.isFinite(scene.yM)
  ) {
    return null;
  }
  // A scene pose is invented by definition. One that claims hardware is malformed.
  const origin = (scene.origin || "").toUpperCase();
  const source = (scene.source || "").toUpperCase();
  if (origin !== "SIMULATION" || source !== "SIMULATION") return null;

  const headingRad =
    typeof scene.headingRad === "number" && Number.isFinite(scene.headingRad)
      ? scene.headingRad
      : null;

  return {
    xM: scene.xM,
    yM: scene.yM,
    headingRad,
    frame: scene.frame,
    method: scene.method,
    routeId: typeof scene.routeId === "string" ? scene.routeId : null,
    routeDirection: scene.routeDirection === 1 || scene.routeDirection === -1 ? scene.routeDirection : null,
    provenanceLabel: scene.provenanceLabel,
    reason: scene.reason ?? `${TWIN_SCENE_LABEL}. Demonstration position, not a measurement.`,
  };
}

/**
 * One vehicle's position for the map: a real fix first, the Twin's demo pose second.
 *
 * The mode provider is asked FIRST and always wins when it produced a coordinate, so a
 * genuine physical fix can never be displaced by a demonstration pose. Only when the
 * provider has nothing - which is every LIVE case today, since no GNSS exists - does the
 * Twin's explicitly simulated scene pose get drawn, under its own label.
 *
 * When neither supplies anything the provider's own UNAVAILABLE answer is returned
 * unchanged, so its reason survives.
 */
export function resolveVehiclePosition(
  vehicle: VehicleState,
  provider: VehiclePositionProvider,
  extent: DecimalExtent,
): VehiclePosition {
  const fromProvider = provider.positionFor(vehicle);
  if (fromProvider.position !== null) return fromProvider;
  return twinScenePosition(vehicle, extent) ?? fromProvider;
}

/**
 * Positions for a fleet, in a stable order, including Twin demo poses.
 *
 * The map-facing counterpart of `positionsFor`, which stays provider-only for callers
 * that must see exactly what the mode provider said.
 */
export function fleetPositions(
  vehicles: Record<string, VehicleState>,
  provider: VehiclePositionProvider,
  extent: DecimalExtent,
): VehiclePosition[] {
  return Object.keys(vehicles)
    .sort()
    .map((id) => resolveVehiclePosition(vehicles[id] as VehicleState, provider, extent));
}

/** Only the vehicles that genuinely have a position to draw. */
export function placeablePositions(positions: VehiclePosition[]): VehiclePosition[] {
  return positions.filter((p) => p.position !== null);
}

/** Vehicles with no position. Listed on the map rather than hidden. */
export function unplaceablePositions(positions: VehiclePosition[]): VehiclePosition[] {
  return positions.filter((p) => p.position === null);
}
