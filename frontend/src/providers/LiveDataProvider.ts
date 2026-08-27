/**
 * LiveDataProvider — M12-A Live Integration Foundation.
 *
 * Source of truth: `requirements/task1-data-contract.md` §13, `requirements/DECISIONS.md`.
 *
 * Implements the shared `DataProvider` interface for live/external Task 2 integration.
 * Transport logic is strictly isolated behind the `LiveTransport` interface (architecture
 * skill §Providers and realtime-data skill §9).
 *
 * Load-bearing rules preserved from M2/M3:
 *   1. Validation is SHARED (`data/validate.ts`) — live payloads pass through the real
 *      Zod schemas before normalization.
 *   2. Normalization is SHARED (`data/normalize.ts`) — pure transform to camelCase domain
 *      entities; unknown enums normalize to `UNKNOWN` and are never dropped.
 *   3. `ProviderUpdate.receivedAt` is captured for every delivery to allow clock skew
 *      measurement (RISK-I4).
 *   4. Quality is NOT assigned by the provider — derived downstream by freshness/quality
 *      machinery.
 *   5. `ProviderPatch` explicit deletion semantics (`deletions?: EntityDeletions`) are
 *      preserved.
 *   6. Single status vocabulary (`IDLE`, `CONNECTING`, `CONNECTED`, `RECONNECTING`,
 *      `DISCONNECTED`, `ERROR`).
 *   7. Replay command prohibition: advisory acknowledgement updates local display and
 *      logs event only, with no vehicle command or safety override (PAD-B, PAD-D).
 */

import type { AppStatePatch, ConnectionStatus } from "../contracts/appState";
import type { Alert } from "../contracts/domain";
import type { MessageType } from "../contracts/raw";
import type { ProviderError, ValidationFailure } from "../data/errors";
import { isProviderError, providerError } from "../data/errors";
import {
  normalizeAlert,
  normalizeArrivalPlan,
  normalizeBottleneckState,
  normalizeCvResult,
  normalizeDispatchCommand,
  normalizeEventRecord,
  normalizeHealth,
  normalizeKpiSnapshot,
  normalizeMineTopology,
  normalizeRoadState,
  normalizeSafetyState,
  normalizeSlotState,
  normalizeSystemHealth,
  normalizeVehicleState,
  normalizeVisibilityForecast,
} from "../data/normalize";
import { buildPatch, type NormalizedBatch } from "../data/patch";
import type { Clock } from "../data/sourced";
import { systemClock } from "../data/sourced";
import { validateMessage } from "../data/validate";
import { getScenario } from "../mocks/registry";
import type {
  DataProvider,
  EntityDeletions,
  ProviderPatch,
  StatusListener,
  Unsubscribe,
  UpdateListener,
} from "./DataProvider";
import { resolveTimeTokens } from "./MockDataProvider";
import { type CancelHandle, realScheduler, type Scheduler } from "./scheduler";

// ---------------------------------------------------------------------------
// Normalizer dispatch table (Shared with M3)
// ---------------------------------------------------------------------------

const KEYED_TARGET: Partial<Record<MessageType, keyof NormalizedBatch>> = {
  VehicleState: "vehicles",
  SafetyState: "safety",
  RoadState: "road",
  VisibilityForecast: "forecasts",
  BottleneckState: "bottlenecks",
  ArrivalPlan: "arrivals",
  SlotState: "slots",
  DispatchCommand: "dispatch",
  Alert: "alerts",
  EventRecord: "events",
};

// biome-ignore lint/suspicious/noExplicitAny: dispatch table across 15 distinct schemas
const NORMALIZERS: Record<MessageType, (raw: any) => unknown> = {
  VehicleState: normalizeVehicleState,
  SafetyState: normalizeSafetyState,
  RoadState: normalizeRoadState,
  VisibilityForecast: normalizeVisibilityForecast,
  BottleneckState: normalizeBottleneckState,
  DispatchCommand: normalizeDispatchCommand,
  SlotState: normalizeSlotState,
  ArrivalPlan: normalizeArrivalPlan,
  Alert: normalizeAlert,
  EventRecord: normalizeEventRecord,
  Health: normalizeHealth,
  SystemHealth: normalizeSystemHealth,
  KpiSnapshot: normalizeKpiSnapshot,
  CVResult: normalizeCvResult,
  MineTopology: normalizeMineTopology,
};

// ---------------------------------------------------------------------------
// Transport Abstraction
// ---------------------------------------------------------------------------

/**
 * Isolated transport layer for live data delivery.
 *
 * Keeps transport protocols (WebSocket, MQTT, IPC, Stub) strictly outside of visual
 * components and data stores.
 */
export interface LiveTransport {
  readonly name: string;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  send?(data: string): Promise<void>;
  onMessage(handler: (message: unknown) => void): Unsubscribe;
  onStatus(handler: (status: ConnectionStatus, error: ProviderError | null) => void): Unsubscribe;
}

/**
 * Reconnect and exponential backoff configuration.
 */
export interface LiveReconnectOptions {
  /** Initial delay in ms before first reconnect attempt. Default 1000ms. */
  initialDelayMs?: number;
  /** Maximum delay in ms. Default 30000ms. */
  maxDelayMs?: number;
  /** Exponential backoff multiplier. Default 1.5. */
  factor?: number;
  /** Whether to apply random jitter (0.8 - 1.2x). Default true. */
  jitter?: boolean;
  /** Maximum consecutive retry attempts. Default Infinity. */
  maxRetries?: number;
}

/**
 * Diagnostics surfaced for S6 and verification.
 */
export interface LiveDiagnostics {
  validationFailures: readonly ValidationFailure[];
}

export interface LiveDataProviderOptions {
  /** Transport implementation. If omitted, uses a default StubLiveTransport. */
  transport?: LiveTransport;
  /** Injected clock for deterministic timestamping and testing. */
  clock?: Clock;
  /** Injected scheduler for deterministic timer control and testing. */
  scheduler?: Scheduler;
  /** Reconnect configuration. Set to false to disable automatic reconnection. */
  reconnect?: LiveReconnectOptions | false;
}

// ---------------------------------------------------------------------------
// Stub Live Transport (Test / Verification / Foundation)
// ---------------------------------------------------------------------------

export interface StubLiveTransportOptions {
  /** Sequence of raw payloads to emit after connect. */
  payloads?: readonly unknown[];
  /** Emission interval in ms. Default 1000ms. */
  intervalMs?: number;
  /** Injected scheduler. */
  scheduler?: Scheduler;
  /** Loop through payloads continuously. Default false. */
  loop?: boolean;
  /** Simulate initial connection failure. */
  failConnect?: boolean;
  /** Injected clock for time token resolution. */
  clock?: Clock;
}

/**
 * Stub transport capable of delivering representative Task 2-shaped payloads.
 * Used for testing, offline verification, and live foundation before production endpoints.
 */
export class StubLiveTransport implements LiveTransport {
  readonly name = "STUB";
  private isConnected = false;
  private readonly messageHandlers = new Set<(message: unknown) => void>();
  private readonly statusHandlers = new Set<
    (status: ConnectionStatus, error: ProviderError | null) => void
  >();
  private readonly scheduler: Scheduler;
  private readonly clock: Clock;
  private readonly payloads: readonly unknown[];
  private readonly intervalMs: number;
  private readonly loop: boolean;
  private readonly failConnect: boolean;
  private cancelTicker: CancelHandle | null = null;
  private stepIndex = 0;
  public readonly sentMessages: string[] = [];

  constructor(options: StubLiveTransportOptions = {}) {
    this.payloads = options.payloads ?? [];
    this.intervalMs = options.intervalMs ?? 1000;
    this.scheduler = options.scheduler ?? realScheduler();
    this.clock = options.clock ?? systemClock;
    this.loop = options.loop ?? false;
    this.failConnect = options.failConnect ?? false;
  }

  async connect(): Promise<void> {
    if (this.failConnect) {
      const err = providerError("INITIALIZATION", "Stub transport connection simulated failure", {
        occurredAt: new Date(this.clock()).toISOString(),
        retryable: true,
      });
      this.emitStatus("ERROR", err);
      throw err;
    }
    if (this.isConnected) return;
    this.isConnected = true;
    this.emitStatus("CONNECTED", null);

    if (this.payloads.length > 0) {
      this.scheduleNext();
    }
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
    if (this.cancelTicker) {
      this.cancelTicker();
      this.cancelTicker = null;
    }
    this.emitStatus("DISCONNECTED", null);
  }

  async send(data: string): Promise<void> {
    this.sentMessages.push(data);
  }

  /**
   * Manually feed a payload through the live transport.
   */
  feed(payload: unknown): void {
    if (!this.isConnected) return;
    const nowMs = this.clock();
    const resolved = resolveTimeTokens(payload, nowMs);
    for (const handler of this.messageHandlers) {
      handler(resolved);
    }
  }

  /**
   * Trigger a simulated transport error.
   */
  triggerError(error: ProviderError): void {
    this.emitStatus("ERROR", error);
  }

  /**
   * Trigger a simulated transport drop (useful for reconnect testing).
   */
  triggerDisconnect(error?: ProviderError): void {
    this.isConnected = false;
    if (this.cancelTicker) {
      this.cancelTicker();
      this.cancelTicker = null;
    }
    this.emitStatus("DISCONNECTED", error ?? null);
  }

  onMessage(handler: (message: unknown) => void): Unsubscribe {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  onStatus(handler: (status: ConnectionStatus, error: ProviderError | null) => void): Unsubscribe {
    this.statusHandlers.add(handler);
    return () => {
      this.statusHandlers.delete(handler);
    };
  }

  private scheduleNext(): void {
    if (!this.isConnected || this.payloads.length === 0) return;
    this.cancelTicker = this.scheduler.schedule(this.intervalMs, () => {
      if (!this.isConnected) return;
      const rawPayload = this.payloads[this.stepIndex];
      this.stepIndex++;
      if (this.stepIndex >= this.payloads.length) {
        if (this.loop) {
          this.stepIndex = 0;
        }
      }
      this.feed(rawPayload);
      if (this.loop || this.stepIndex < this.payloads.length) {
        this.scheduleNext();
      }
    });
  }

  private emitStatus(status: ConnectionStatus, error: ProviderError | null): void {
    for (const handler of this.statusHandlers) {
      handler(status, error);
    }
  }
}

/**
 * Creates a StubLiveTransport populated with steps from an authored scenario.
 */
export function createScenarioStubTransport(
  scenarioId = "nominal",
  options: Omit<StubLiveTransportOptions, "payloads"> = {},
): StubLiveTransport {
  const lookup = getScenario(scenarioId);
  const payloads: unknown[] = [];
  if (lookup.ok) {
    for (const step of lookup.scenario.steps) {
      if (step.emit) {
        payloads.push(
          step.effects?.deletions
            ? { emit: step.emit, deletions: step.effects.deletions }
            : step.emit,
        );
      }
    }
  }
  return new StubLiveTransport({ ...options, payloads });
}

// ---------------------------------------------------------------------------
// LiveDataProvider
// ---------------------------------------------------------------------------

export class LiveDataProvider implements DataProvider {
  readonly kind = "LIVE" as const;

  private readonly clock: Clock;
  private readonly scheduler: Scheduler;
  private readonly transport: LiveTransport;
  private readonly reconnectOptions: LiveReconnectOptions | null;

  private status: ConnectionStatus = "IDLE";
  private manualDisconnect = false;
  private reconnectAttempt = 0;
  private reconnectCancel: CancelHandle | null = null;

  private readonly updateListeners = new Set<UpdateListener>();
  private readonly statusListeners = new Set<StatusListener>();
  private readonly failures: ValidationFailure[] = [];
  private lastAlerts: readonly Alert[] = [];

  private unsubscribeTransportMsg: Unsubscribe | null = null;
  private unsubscribeTransportStatus: Unsubscribe | null = null;

  constructor(options: LiveDataProviderOptions = {}) {
    this.clock = options.clock ?? systemClock;
    this.scheduler = options.scheduler ?? realScheduler();
    this.transport =
      options.transport ??
      createScenarioStubTransport("nominal", {
        clock: this.clock,
        scheduler: this.scheduler,
        loop: true,
      });
    this.reconnectOptions =
      options.reconnect === false
        ? null
        : {
            initialDelayMs: options.reconnect?.initialDelayMs ?? 1000,
            maxDelayMs: options.reconnect?.maxDelayMs ?? 30000,
            factor: options.reconnect?.factor ?? 1.5,
            jitter: options.reconnect?.jitter ?? true,
            maxRetries: options.reconnect?.maxRetries ?? Number.POSITIVE_INFINITY,
          };
  }

  get currentStatus(): ConnectionStatus {
    return this.status;
  }

  get diagnostics(): LiveDiagnostics {
    return { validationFailures: [...this.failures] };
  }

  get transportName(): string {
    return this.transport.name;
  }

  // -- lifecycle ------------------------------------------------------------

  async connect(): Promise<void> {
    this.manualDisconnect = false;
    this.clearReconnect();

    this.setStatus("CONNECTING", null);

    // Wire transport listeners
    if (!this.unsubscribeTransportMsg) {
      this.unsubscribeTransportMsg = this.transport.onMessage((msg) => this.ingest(msg));
    }
    if (!this.unsubscribeTransportStatus) {
      this.unsubscribeTransportStatus = this.transport.onStatus((status, error) => {
        this.handleTransportStatus(status, error);
      });
    }

    try {
      await this.transport.connect();
      this.reconnectAttempt = 0;
      this.setStatus("CONNECTED", null);
    } catch (err) {
      const error = isProviderError(err as ProviderError)
        ? (err as ProviderError)
        : providerError("INITIALIZATION", "Failed to connect to live transport", {
            occurredAt: this.nowIso(),
            cause: err instanceof Error ? err.message : String(err),
            retryable: true,
          });
      if (this.reconnectOptions && !this.manualDisconnect) {
        this.setStatus("RECONNECTING", error);
        this.scheduleReconnect();
      } else {
        this.setStatus("ERROR", error);
      }
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    this.manualDisconnect = true;
    this.clearReconnect();

    if (this.unsubscribeTransportMsg) {
      this.unsubscribeTransportMsg();
      this.unsubscribeTransportMsg = null;
    }
    if (this.unsubscribeTransportStatus) {
      this.unsubscribeTransportStatus();
      this.unsubscribeTransportStatus = null;
    }

    try {
      await this.transport.disconnect();
    } finally {
      this.setStatus("DISCONNECTED", null);
    }
  }

  // -- subscriptions --------------------------------------------------------

  subscribe(onUpdate: UpdateListener): Unsubscribe {
    this.updateListeners.add(onUpdate);
    return () => {
      this.updateListeners.delete(onUpdate);
    };
  }

  onStatusChange(listener: StatusListener): Unsubscribe {
    this.statusListeners.add(listener);
    // Emit immediate current status on attachment
    listener(this.status, null);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  // -- acknowledgement ------------------------------------------------------

  /**
   * HMI ALERT/EVENT ACKNOWLEDGEMENT ONLY (PAD-B, PAD-D).
   *
   * Local display state update + advisory forwarding over transport if available.
   * Safety-critical alerts remain non-acknowledgeable.
   */
  async sendAcknowledgement(alertId: string, actor: string): Promise<void> {
    if (this.status !== "CONNECTED") {
      throw providerError("TRANSPORT", "Cannot acknowledge alert while disconnected", {
        occurredAt: this.nowIso(),
        retryable: true,
      });
    }

    const at = this.nowIso();
    const known = this.lastAlerts.find((a) => a.alertId === alertId);

    // Forward over transport if transport provides send capability
    if (this.transport.send) {
      try {
        await this.transport.send(
          JSON.stringify({
            type: "ALERT_ACKNOWLEDGED",
            alertId,
            actor,
            timestamp: at,
          }),
        );
      } catch (err) {
        // Transport advisory forward failure logged as provider error
        const pErr = providerError("TRANSPORT", "Failed to transmit acknowledgement", {
          occurredAt: at,
          cause: err instanceof Error ? err.message : String(err),
          retryable: true,
        });
        this.setStatus(this.status, pErr);
      }
    }

    if (!known) return;

    // Update local alert and emit event for HMI presentation
    const alerts: Alert[] = this.lastAlerts.map((alert) =>
      alert.alertId === alertId ? { ...alert, acknowledged: { by: actor, at } } : alert,
    );

    this.emit({
      changes: {
        alerts,
        events: [
          {
            eventId: `ack-${alertId}-${at}`,
            timestamp: at,
            category: "ALERT_ACKNOWLEDGED",
            subjectId: alertId,
            payload: { alertId, acknowledged: { by: actor, at } },
            actor,
          },
        ],
      },
    });
  }

  // -- data ingestion & validation pipeline ---------------------------------

  /**
   * Primary ingestion entry point for live payloads.
   *
   * Raw payload → validateMessage → normalize → buildPatch → ProviderPatch
   */
  ingest(rawMessage: unknown): AppStatePatch | null {
    const nowMs = this.clock();
    const receivedAt = new Date(nowMs).toISOString();

    let parsed: unknown = rawMessage;
    if (typeof rawMessage === "string") {
      try {
        parsed = JSON.parse(rawMessage);
      } catch (err) {
        const error = providerError("PROTOCOL", "Malformed live payload: unparseable JSON", {
          occurredAt: receivedAt,
          cause: err instanceof Error ? err.message : String(err),
          retryable: false,
        });
        this.setStatus("ERROR", error);
        return null;
      }
    }

    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    const batch: NormalizedBatch = {};
    let deletions: EntityDeletions | undefined;

    const processItems = (type: MessageType, items: unknown) => {
      if (!items) return;
      const arr = Array.isArray(items) ? items : [items];
      for (const rawItem of arr) {
        // Resolve time tokens if present in stub/testing data
        const resolved = resolveTimeTokens(rawItem, nowMs);
        const result = validateMessage(type, resolved, receivedAt);
        if (!result.ok) {
          this.failures.push(result.failure);
          continue;
        }
        const normalizer = NORMALIZERS[type];
        if (normalizer) {
          const normalized = normalizer(result.value);
          this.collect(batch, type, normalized);
        }
      }
    };

    if (Array.isArray(parsed)) {
      // Array of message envelopes: [ { type: "VehicleState", payload: { ... } }, ... ]
      for (const entry of parsed) {
        if (entry && typeof entry === "object" && "type" in entry && "payload" in entry) {
          const t = (entry as { type: string }).type as MessageType;
          if (t in NORMALIZERS) {
            processItems(t, (entry as { payload: unknown }).payload);
          }
        }
      }
    } else {
      const obj = parsed as Record<string, unknown>;
      if ("deletions" in obj && typeof obj.deletions === "object" && obj.deletions !== null) {
        deletions = obj.deletions as EntityDeletions;
      }

      if ("emit" in obj && typeof obj.emit === "object" && obj.emit !== null) {
        // Enveloped batch: { emit: { VehicleState: [...], ... }, deletions?: {...} }
        for (const [tStr, items] of Object.entries(obj.emit as Record<string, unknown>)) {
          const t = tStr as MessageType;
          if (t in NORMALIZERS) {
            processItems(t, items);
          }
        }
      } else if ("type" in obj && "payload" in obj) {
        // Single message envelope: { type: "VehicleState", payload: {...} }
        const t = String(obj.type) as MessageType;
        if (t in NORMALIZERS) {
          processItems(t, obj.payload);
        }
      } else {
        // Direct map: { VehicleState: [...], SafetyState: [...] }
        for (const [tStr, items] of Object.entries(obj)) {
          if (tStr === "deletions") continue;
          const t = tStr as MessageType;
          if (t in NORMALIZERS) {
            processItems(t, items);
          }
        }
      }
    }

    const changes = buildPatch(batch);
    const hasChanges = Object.keys(changes).length > 0;
    const hasDeletions = deletions !== undefined && Object.keys(deletions).length > 0;

    if (!hasChanges && !hasDeletions) return null;

    const patch: ProviderPatch = deletions ? { changes, deletions } : { changes };
    this.emit(patch);
    return changes;
  }

  private collect(batch: NormalizedBatch, type: MessageType, entity: unknown): void {
    const target = KEYED_TARGET[type];
    if (target) {
      const list = (batch[target] as unknown[] | undefined) ?? [];
      list.push(entity);
      (batch as Record<string, unknown>)[target] = list;
      return;
    }
    // Singleton slices
    if (type === "MineTopology")
      batch.topology = entity as NonNullable<NormalizedBatch["topology"]>;
    else if (type === "SystemHealth")
      batch.health = entity as NonNullable<NormalizedBatch["health"]>;
    else if (type === "KpiSnapshot") batch.kpis = entity as NonNullable<NormalizedBatch["kpis"]>;
    else if (type === "CVResult") batch.cv = entity as NonNullable<NormalizedBatch["cv"]>;
  }

  // -- internal transport status & reconnect --------------------------------

  private handleTransportStatus(status: ConnectionStatus, error: ProviderError | null): void {
    if (status === "CONNECTED") {
      this.reconnectAttempt = 0;
      this.clearReconnect();
      this.setStatus("CONNECTED", null);
    } else if (status === "DISCONNECTED" || status === "ERROR") {
      if (this.manualDisconnect) {
        this.setStatus("DISCONNECTED", null);
      } else if (this.reconnectOptions) {
        this.setStatus("RECONNECTING", error);
        this.scheduleReconnect();
      } else {
        this.setStatus(status, error);
      }
    } else {
      this.setStatus(status, error);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectCancel || !this.reconnectOptions || this.manualDisconnect) return;

    if (this.reconnectAttempt >= (this.reconnectOptions.maxRetries ?? Number.POSITIVE_INFINITY)) {
      this.setStatus(
        "ERROR",
        providerError("TRANSPORT", "Maximum reconnect attempts reached", {
          occurredAt: this.nowIso(),
          retryable: false,
        }),
      );
      return;
    }

    this.reconnectAttempt++;
    const baseDelay =
      (this.reconnectOptions.initialDelayMs ?? 1000) *
      (this.reconnectOptions.factor ?? 1.5) ** (this.reconnectAttempt - 1);
    const cappedDelay = Math.min(baseDelay, this.reconnectOptions.maxDelayMs ?? 30000);
    const jitterMultiplier =
      (this.reconnectOptions.jitter ?? true) ? 0.8 + Math.random() * 0.4 : 1.0;
    const delayMs = Math.round(cappedDelay * jitterMultiplier);

    this.reconnectCancel = this.scheduler.schedule(delayMs, async () => {
      this.reconnectCancel = null;
      if (this.manualDisconnect) return;

      try {
        await this.transport.connect();
        this.reconnectAttempt = 0;
        this.setStatus("CONNECTED", null);
      } catch (err) {
        const pErr = isProviderError(err as ProviderError)
          ? (err as ProviderError)
          : providerError("TRANSPORT", "Reconnect attempt failed", {
              occurredAt: this.nowIso(),
              cause: err instanceof Error ? err.message : String(err),
              retryable: true,
            });
        this.setStatus("RECONNECTING", pErr);
        this.scheduleReconnect();
      }
    });
  }

  private clearReconnect(): void {
    if (this.reconnectCancel) {
      this.reconnectCancel();
      this.reconnectCancel = null;
    }
  }

  // -- plumbing -------------------------------------------------------------

  private nowIso(): string {
    return new Date(this.clock()).toISOString();
  }

  private setStatus(status: ConnectionStatus, error: ProviderError | null): void {
    if (this.status === status && error === null) return;
    this.status = status;
    for (const listener of this.statusListeners) {
      listener(status, error);
    }
  }

  private emit(patch: ProviderPatch): void {
    if (patch.changes.alerts !== undefined) {
      this.lastAlerts = patch.changes.alerts;
    }
    for (const listener of this.updateListeners) {
      listener(patch);
    }
  }
}
