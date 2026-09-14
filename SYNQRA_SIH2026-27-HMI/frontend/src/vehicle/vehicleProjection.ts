/**
 * Vehicle projection — the isolation boundary of the vehicle HMI.
 *
 * ==========================================================================
 *  ONE CANONICAL STATE. THREE VIEWS OF IT. NO THIRD STORE.
 *
 *      canonical Digital Twin
 *              |
 *          AppState                (one store, filled by one provider)
 *         /        \
 *  control room    projectVehicle(state, "TRUCK_01")
 *  (whole fleet)   projectVehicle(state, "TRUCK_02")
 *
 *  This module is a SELECTOR. It reads `AppState` and returns the slice belonging to one
 *  vehicle. It holds no state of its own, caches nothing, computes no physical quantity
 *  and never writes back. A vehicle HMI that reached into `AppState` directly could
 *  accidentally render the other truck's speed under its own heading; routing every read
 *  through here makes that a single, testable place instead of a habit.
 * ==========================================================================
 *
 * WHAT ISOLATION MEANS HERE
 *
 * Isolation is about OWNERSHIP, not visibility. TRUCK_01's console may legitimately learn
 * things about TRUCK_02 - a V2V peer is the whole point of V2V - but it must never treat
 * TRUCK_02's telemetry as its own. So the peer is returned in its own named field,
 * `peer`, and can never be mistaken for `vehicle` by a caller reading the type.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { AppState, ConnectionState, SessionCommand } from "../contracts/appState";
import type {
  Alert,
  DispatchCommand,
  EventRecord,
  RoadState,
  SafetyState,
  VehicleState,
} from "../contracts/domain";
import { type ConfiguredVehicleId, VEHICLE_IDS } from "./vehicleConfig";

export interface VehicleProjection {
  /** The vehicle this projection is FOR. Fixed by the caller, never inferred from data. */
  readonly vehicleId: string;
  /**
   * True when the canonical Twin currently carries this vehicle.
   *
   * False is a real state and is rendered as such: the vehicle HMI stays up and says the
   * Twin has supplied nothing, rather than showing a blank console that looks nominal.
   */
  readonly present: boolean;

  readonly vehicle: VehicleState | null;
  readonly safety: SafetyState | null;
  /** The road the Twin associates with this vehicle, when it associates one. */
  readonly road: RoadState | null;

  /** Alerts whose SUBJECT is this vehicle. Fleet-wide alerts are the control room's. */
  readonly alerts: readonly Alert[];
  /** Session commands issued to this vehicle, newest first. */
  readonly commands: readonly SessionCommand[];
  /** The dispatch command the Twin holds for this vehicle, when it holds one. */
  readonly dispatch: DispatchCommand | null;
  /** Events whose subject is this vehicle. */
  readonly events: readonly EventRecord[];

  /**
   * The OTHER vehicle, when the Twin carries it.
   *
   * Present so a V2V panel can name its peer and so the console can say "TRUCK_02 has
   * gone stale" without pretending that is its own state. Never rendered as this
   * vehicle's telemetry.
   */
  readonly peer: VehicleState | null;
  /**
   * The peer's CANONICAL safety state (HMI-SAFETY-01), when the producer supplied one.
   * Read from the same `safety` slice as this vehicle's own; never derived here.
   */
  readonly peerSafety: SafetyState | null;
  readonly peerVehicleId: string | null;

  /** Shared, not vehicle-specific: this browser's link to the backend. */
  readonly connection: ConnectionState;
}

/**
 * The other truck.
 *
 * A two-vehicle prototype has exactly one peer. Returns null for anything else rather
 * than guessing, so a third vehicle would show UNAVAILABLE instead of an arbitrary pick.
 */
export function peerOf(vehicleId: string): ConfiguredVehicleId | null {
  const others = VEHICLE_IDS.filter((id) => id !== vehicleId);
  return others.length === 1 ? (others[0] as ConfiguredVehicleId) : null;
}

/** The road id the Twin associates with a vehicle, or null. Never invented. */
function roadIdOf(vehicle: VehicleState | null): string | null {
  return vehicle?.position?.segmentId ?? vehicle?.routeId ?? null;
}

/**
 * Project the canonical state onto one vehicle.
 *
 * Every filter below compares against the vehicle id the CALLER supplied. Nothing is
 * selected by "the first vehicle" or "the only vehicle", because both of those quietly
 * become the wrong vehicle the moment a second one appears.
 */
export function projectVehicle(state: AppState, vehicleId: string): VehicleProjection {
  const vehicle = state.vehicles?.[vehicleId] ?? null;
  const safety = state.safety?.[vehicleId] ?? null;

  const roadId = roadIdOf(vehicle);
  const road = roadId ? (state.road?.[roadId] ?? null) : null;

  const alerts = (state.alerts ?? []).filter(
    (alert) => alert.subject.kind === "VEHICLE" && alert.subject.id === vehicleId,
  );

  const commands = (state.commands ?? []).filter((command) => command.vehicleId === vehicleId);

  const dispatch =
    Object.values(state.dispatch ?? {}).find((command) => command?.vehicleId === vehicleId) ?? null;

  const events = (state.events ?? []).filter((event) => event.subjectId === vehicleId);

  const peerId = peerOf(vehicleId);
  const peer = peerId ? (state.vehicles?.[peerId] ?? null) : null;
  const peerSafety = peerId ? (state.safety?.[peerId] ?? null) : null;

  return {
    vehicleId,
    present: vehicle !== null,
    vehicle,
    safety,
    road,
    alerts,
    commands,
    dispatch,
    events,
    peer,
    peerSafety,
    peerVehicleId: peerId,
    connection: state.connection,
  };
}
