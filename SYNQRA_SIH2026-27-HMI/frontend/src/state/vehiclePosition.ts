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
import type { DecimalExtent, LonLat } from "./geoSite";

/** How a position was obtained. Distinct from the geographic provenance of a feature. */
export type PositionProvenance = "PHYSICAL" | "SIMULATED" | "REPLAY" | "UNAVAILABLE";

export interface VehiclePosition {
  vehicleId: string;
  /** Null whenever no position exists. Never a placeholder coordinate. */
  position: LonLat | null;
  provenance: PositionProvenance;
  /** Why a position is absent, stated rather than implied. */
  reason?: string | undefined;
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

/** Only the vehicles that genuinely have a position to draw. */
export function placeablePositions(positions: VehiclePosition[]): VehiclePosition[] {
  return positions.filter((p) => p.position !== null);
}

/** Vehicles with no position. Listed on the map rather than hidden. */
export function unplaceablePositions(positions: VehiclePosition[]): VehiclePosition[] {
  return positions.filter((p) => p.position === null);
}
