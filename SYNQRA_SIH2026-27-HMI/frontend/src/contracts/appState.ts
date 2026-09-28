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
import type { ObservabilitySnapshot } from "../api/observabilityClient";
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

/**
 * One operator command, as this session has observed it — Phase 3.
 *
 * SESSION STATE, NOT TWIN STATE. The Digital Twin owns vehicle state; this records what
 * the HMI submitted and what the backend said back, so S4 has one shared source rather
 * than a component-local copy.
 *
 * `outcome` is only ever a status the backend returned, or a client-side transport state
 * (PENDING / NETWORK_ERROR). Nothing here is inferred, and acceptance is never read as
 * execution.
 */
export interface SessionCommand {
  commandId: string;
  vehicleId: string;
  action: string;
  /** m/s, or null when the action carries no speed. */
  targetSpeedMps: number | null;
  outcome: string;
  /** The backend's own message, verbatim. Null before any response. */
  message: string | null;
  reason: string;
  submittedAtIso: string;
  /** Last time any source updated this record. */
  updatedAtIso: string;
  /** Whether the gateway confirmed the command over the WebSocket. */
  gatewayConfirmed: boolean;
  /**
   * Authoritative execution acknowledgement, when one exists.
   * Null means NOT acknowledged - never "assume executed".
   */
  executionAckIso: string | null;
}

/**
 * Control-plane observability — Phase 4.
 *
 * METRICS ONLY. `twinVehicleCount` is a count, not vehicle state; `commandGateway.*` are
 * counters, not command records. Vehicle state stays in `vehicles`, command history in
 * `commands`; nothing is duplicated here.
 *
 * `data` is the LAST KNOWN GOOD snapshot and survives a failed refresh, so a transient
 * outage marks the panel stale instead of blanking every counter to zero.
 */
export interface ObservabilityState {
  /** IDLE = never fetched. CURRENT = last fetch succeeded. STALE/ERROR = it did not. */
  status: "IDLE" | "CURRENT" | "STALE" | "ERROR";
  /** Last successful snapshot, retained through failures. Null until the first success. */
  data: ObservabilitySnapshot | null;
  /** When `data` was last successfully fetched. Null while none has succeeded. */
  fetchedAt: Iso8601 | null;
  /** Why the most recent attempt failed. Null when the last attempt succeeded. */
  error: string | null;
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
  /**
   * Phase 3 — the session's command log. Newest first, bounded.
   * ONE record per command_id, updated as HTTP and WebSocket information arrives.
   */
  commands: readonly SessionCommand[];
  /** Phase 4 — control-plane counters from GET /api/observability. Metrics only. */
  observability: ObservabilityState;
}

/**
 * What a provider emits. Contract §13 specifies `Partial<AppState>`.
 *
 * Known limitation, recorded rather than solved: `Partial` cannot express "this vehicle
 * was removed" as distinct from "no news about this vehicle". The contract specifies it,
 * so M2 follows it. If Task 2 turns out to send deletions, this needs revisiting at M12.
 */
export type AppStatePatch = Partial<AppState>;
