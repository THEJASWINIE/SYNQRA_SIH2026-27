/**
 * Normalized application state — TYPE ONLY. M2.
 *
 * Source of truth: `requirements/task1-data-contract.md` §12.
 *
 * This is the single shape every future screen reads. No component reads a provider or
 * raw JSON (architecture skill).
 *
 * DELIBERATELY NOT IN M2: any store, context, hook, reducer or React binding. This file
 * declares a type and nothing else. State management arrives with the screens that need
 * it (M4).
 */

import type {
  Alert,
  ArrivalPlan,
  BottleneckState,
  CVResult,
  DispatchCommand,
  EventRecord,
  KpiSnapshot,
  MineTopology,
  RoadState,
  SafetyState,
  SlotState,
  SystemHealth,
  VehicleState,
  VisibilityForecast,
} from "./domain";
import type { CommandId, Iso8601, NodeId, SegmentId, SlotId, VehicleId } from "./primitives";

/** Contract §12. Describes the pipe, not any datum's quality. */
export type ConnectionStatus =
  | "IDLE"
  | "CONNECTING"
  | "CONNECTED"
  | "RECONNECTING"
  | "DISCONNECTED"
  | "ERROR";

/** Contract §12. The three implementations arrive in M3, M9 and M12. */
export type ProviderKind = "MOCK" | "LIVE" | "REPLAY";

export interface ConnectionState {
  status: ConnectionStatus;
  provider: ProviderKind;
  /** FR-019 active scenario name. Null outside the mock provider. */
  scenarioName: string | null;
  lastMessageAt: Iso8601 | null;
  error: string | null;
}

export interface ClockState {
  now: Iso8601;
  /** Non-null only while replaying (FR-017). */
  replayPosition: Iso8601 | null;
}

export interface AppState {
  connection: ConnectionState;
  clock: ClockState;

  topology: MineTopology | null;
  vehicles: Record<VehicleId, VehicleState>;
  safety: Record<VehicleId, SafetyState>;
  road: Record<SegmentId, RoadState>;
  forecasts: Record<SegmentId, VisibilityForecast>;
  bottlenecks: Record<NodeId, BottleneckState>;
  arrivals: Record<NodeId, ArrivalPlan>;
  slots: Record<SlotId, SlotState>;
  dispatch: Record<CommandId, DispatchCommand>;
  alerts: Alert[];
  events: EventRecord[];
  health: SystemHealth | null;
  kpis: KpiSnapshot | null;
  cv: CVResult | null;
}

/**
 * What a provider emits. Contract §13 specifies `Partial<AppState>`.
 *
 * Known limitation, recorded rather than solved: `Partial` cannot express "this vehicle
 * was removed" as distinct from "no news about this vehicle". The contract specifies it,
 * so M2 follows it. If Task 2 turns out to send deletions, this needs revisiting at M12.
 */
export type AppStatePatch = Partial<AppState>;
