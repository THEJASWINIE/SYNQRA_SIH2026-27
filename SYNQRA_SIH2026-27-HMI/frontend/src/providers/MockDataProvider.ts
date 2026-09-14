/**
 * MockDataProvider — M3. The first real `DataProvider` implementation.
 *
 * A DATA SOURCE, NOT A SIMULATION ENGINE (mock-scenarios skill, Core Rule).
 *
 * Every operational value it emits is an authored literal read from a scenario file.
 * Nothing here computes `v_safe`, `h_safe`, friction, visibility, a bottleneck score, a
 * queue forecast, a dispatch decision or an arrival plan. This module moves authored data
 * onto the shared M2 pipeline and nothing else.
 *
 * Two rules are load-bearing and easy to break later:
 *
 *   1. **The provider never assigns quality.** Not OK, STALE, MISSING or INVALID. It
 *      emits data and status events; M2's validation, normalization, timestamp and
 *      freshness machinery decides quality. A mock that stamped STALE directly would test
 *      the scenario file rather than the freshness machinery the real system depends on.
 *
 *   2. **Mock payloads travel the real path.** validate → normalize → patch, exactly as
 *      live data will. A mock that bypassed validation would prove nothing about M12.
 */

import type { AppStatePatch, ConnectionStatus } from "../contracts/appState";
import type { Alert } from "../contracts/domain";
import type { MessageType } from "../contracts/raw";
import type { ProviderError, ValidationFailure } from "../data/errors";
import { providerError } from "../data/errors";
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
  normalizeTwinSafety,
  normalizeTwinVehicle,
  normalizeVehicleState,
  normalizeVisibilityForecast,
} from "../data/normalize";
import { buildPatch, type NormalizedBatch } from "../data/patch";
import type { Clock } from "../data/sourced";
import { systemClock } from "../data/sourced";
import { validateMessage } from "../data/validate";
import { getScenario } from "../mocks/registry";
import type { Scenario, ScenarioStep } from "../mocks/scenarioTypes";
import type {
  DataProvider,
  EntityDeletions,
  ProviderPatch,
  StatusListener,
  Unsubscribe,
  UpdateListener,
} from "./DataProvider";
import { realScheduler, type Scheduler } from "./scheduler";

// ---------------------------------------------------------------------------
// Time tokens
// ---------------------------------------------------------------------------

/**
 * Scenario files store OFFSETS, never wall-clock timestamps — a committed scenario must
 * not become stale merely by ageing on disk.
 *
 * Any string of the form `@now`, `@now+<ms>` or `@now-<ms>` is replaced at emission with
 * an ISO timestamp taken from the injected clock. This is data-path plumbing: it produces
 * timestamps, never operational values.
 */
const TIME_TOKEN = /^@now(?:([+-])(\d+))?$/;

export function resolveTimeTokens(value: unknown, nowMs: number): unknown {
  if (typeof value === "string") {
    const match = TIME_TOKEN.exec(value);
    if (!match) return value;
    const sign = match[1];
    const offset = match[2] ? Number(match[2]) : 0;
    const at = sign === "-" ? nowMs - offset : nowMs + offset;
    return new Date(at).toISOString();
  }
  if (Array.isArray(value)) {
    return value.map((item) => resolveTimeTokens(item, nowMs));
  }
  if (typeof value === "object" && value !== null) {
    const out: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      out[key] = resolveTimeTokens(item, nowMs);
    }
    return out;
  }
  return value;
}

// ---------------------------------------------------------------------------
// Normalizer dispatch
// ---------------------------------------------------------------------------

/** Where each message type lands in a `NormalizedBatch`. */
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
  TwinVehicle: normalizeTwinVehicle,
  TwinSafety: normalizeTwinSafety,
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
// Provider
// ---------------------------------------------------------------------------

export interface MockDataProviderOptions {
  /** Injected so tests are deterministic and never read wall time. */
  clock?: Clock;
  /** Injected so tests advance virtual time and no timer outlives teardown. */
  scheduler?: Scheduler;
}

/**
 * Deliberately NOT part of `DataProvider`.
 *
 * Validation failures are surfaced for diagnostics and tests. They are mock-only: the
 * shared interface carries no such channel, and adding one would be M12's decision.
 */
export interface MockDiagnostics {
  validationFailures: readonly ValidationFailure[];
}

export class MockDataProvider implements DataProvider {
  readonly kind = "MOCK" as const;

  private readonly clock: Clock;
  private readonly scheduler: Scheduler;

  private scenario: Scenario | null = null;
  private status: ConnectionStatus = "IDLE";
  private emissionHalted = false;
  private connected = false;

  private readonly updateListeners = new Set<UpdateListener>();
  private readonly statusListeners = new Set<StatusListener>();
  private readonly failures: ValidationFailure[] = [];
  /**
   * The alerts most recently emitted.
   *
   * Held so an acknowledgement can re-emit the alert set with `acknowledged` set on
   * the named alert (M9D-D). `alerts` is a replace-whole slice, so a patch carrying
   * only the one alert would silently drop the others.
   */
  private lastAlerts: readonly Alert[] = [];

  constructor(options: MockDataProviderOptions = {}) {
    this.clock = options.clock ?? systemClock;
    this.scheduler = options.scheduler ?? realScheduler();
  }

  // -- scenario selection ---------------------------------------------------

  /**
   * Resolve a scenario by id. No emission occurs here.
   *
   * Returns a typed failure rather than throwing: an unknown id is a normal outcome that
   * callers must handle, and `connect()` turns it into an INITIALIZATION error.
   */
  loadScenario(id: string): { ok: true } | { ok: false; error: ProviderError } {
    const lookup = getScenario(id);
    if (!lookup.ok) {
      return {
        ok: false,
        error: providerError("INITIALIZATION", `Unknown scenario "${id}"`, {
          occurredAt: this.nowIso(),
          cause: `available: ${lookup.error.available.join(", ")}`,
          retryable: false,
        }),
      };
    }
    this.scenario = lookup.scenario;
    return { ok: true };
  }

  get scenarioId(): string | null {
    return this.scenario?.id ?? null;
  }

  get currentStatus(): ConnectionStatus {
    return this.status;
  }

  get diagnostics(): MockDiagnostics {
    return { validationFailures: [...this.failures] };
  }

  // -- lifecycle ------------------------------------------------------------

  async connect(): Promise<void> {
    if (!this.scenario) {
      const error = providerError("INITIALIZATION", "No scenario loaded", {
        occurredAt: this.nowIso(),
        retryable: false,
      });
      this.setStatus("ERROR", error);
      throw error;
    }

    this.connected = true;
    this.emissionHalted = false;
    this.failures.length = 0;
    this.lastAlerts = [];

    this.setStatus("CONNECTING", null);
    this.setStatus("CONNECTED", null);

    for (const step of this.scenario.steps) {
      this.scheduler.schedule(step.atMs, () => {
        // A late timer must never fire after teardown.
        if (!this.connected) return;
        this.runStep(step);
      });
    }
  }

  /** Idempotent. No scheduled work may survive it. */
  async disconnect(): Promise<void> {
    this.scheduler.cancelAll();
    this.emissionHalted = false;
    if (!this.connected && this.status === "DISCONNECTED") return;
    this.connected = false;
    this.setStatus("DISCONNECTED", null);
  }

  subscribe(onUpdate: UpdateListener): Unsubscribe {
    this.updateListeners.add(onUpdate);
    return () => {
      this.updateListeners.delete(onUpdate);
    };
  }

  onStatusChange(listener: StatusListener): Unsubscribe {
    this.statusListeners.add(listener);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  /**
   * HMI ALERT/EVENT ACKNOWLEDGEMENT ONLY (PAD-D).
   *
   * Updates the acknowledged state of an alert and emits the resulting alert patch.
   * Touches nothing else — no vehicle, no safety value, no dispatch. The implementation
   * has no mechanism to do so: it can only rewrite `Alert.acknowledged`.
   *
   * AMB-008 and AMB-009 remain unresolved; this is not a ruling on either.
   */
  async sendAcknowledgement(alertId: string, actor: string): Promise<void> {
    const at = this.nowIso();

    /**
     * D9 fix (M9D-D). The previous implementation emitted the event but carried only
     * `events` in the patch, so `Alert.acknowledged` was never set and the acknowledgement
     * was invisible everywhere except the log. Both now travel together.
     *
     * The whole alert set is re-emitted because `alerts` is replace-whole: a patch
     * carrying only the acknowledged alert would drop every other active alert.
     *
     * Acknowledging an alert that is not present is a no-op with no event, rather than an
     * event about an alert nobody can see.
     */
    const known = this.lastAlerts.some((a) => a.alertId === alertId);
    if (!known) return;

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

  // -- playback -------------------------------------------------------------

  private runStep(step: ScenarioStep): void {
    const effects = step.effects;

    if (effects?.status) {
      const error = effects.error
        ? providerError(effects.error.kind, effects.error.message, {
            occurredAt: this.nowIso(),
            ...(effects.error.retryable === undefined
              ? {}
              : { retryable: effects.error.retryable }),
          })
        : null;
      this.setStatus(effects.status, error);
    }

    if (effects?.haltEmission) this.emissionHalted = true;
    if (effects?.resumeEmission) this.emissionHalted = false;

    const deletions = effects?.deletions as EntityDeletions | undefined;
    const changes = this.emissionHalted ? {} : this.assemble(step);

    const hasChanges = Object.keys(changes).length > 0;
    const hasDeletions = deletions !== undefined && Object.keys(deletions).length > 0;
    if (!hasChanges && !hasDeletions) return;

    this.emit(deletions ? { changes, deletions } : { changes });
  }

  /**
   * Run a step's payloads through the real M2 path.
   *
   * A payload that fails validation is recorded and excluded from the patch. It is NOT
   * silently treated as absent: the failure is a `ValidationFailure`, which is what makes
   * the datum INVALID rather than MISSING downstream.
   */
  private assemble(step: ScenarioStep): AppStatePatch {
    if (!step.emit) return {};

    const nowMs = this.clock();
    const receivedAt = new Date(nowMs).toISOString();
    const batch: NormalizedBatch = {};

    for (const [type, payloads] of Object.entries(step.emit)) {
      const messageType = type as MessageType;
      if (!payloads) continue;

      for (const rawPayload of payloads) {
        const resolved = resolveTimeTokens(rawPayload, nowMs);
        const result = validateMessage(messageType, resolved, receivedAt);

        if (!result.ok) {
          this.failures.push(result.failure);
          continue;
        }

        const normalized = NORMALIZERS[messageType](result.value);
        this.collect(batch, messageType, normalized);
      }
    }

    return buildPatch(batch);
  }

  private collect(batch: NormalizedBatch, type: MessageType, entity: unknown): void {
    const target = KEYED_TARGET[type];
    if (target) {
      const list = (batch[target] as unknown[] | undefined) ?? [];
      list.push(entity);
      (batch as Record<string, unknown>)[target] = list;
      return;
    }
    // Singleton slices.
    if (type === "MineTopology")
      batch.topology = entity as NonNullable<NormalizedBatch["topology"]>;
    else if (type === "SystemHealth")
      batch.health = entity as NonNullable<NormalizedBatch["health"]>;
    else if (type === "KpiSnapshot") batch.kpis = entity as NonNullable<NormalizedBatch["kpis"]>;
    else if (type === "CVResult") batch.cv = entity as NonNullable<NormalizedBatch["cv"]>;
    // `Health` alone is not an AppState slice — it appears inside SystemHealth.components.
  }

  // -- plumbing -------------------------------------------------------------

  private nowIso(): string {
    return new Date(this.clock()).toISOString();
  }

  private setStatus(status: ConnectionStatus, error: ProviderError | null): void {
    this.status = status;
    for (const listener of this.statusListeners) listener(status, error);
  }

  private emit(patch: ProviderPatch): void {
    // Track the alert set so an acknowledgement can re-emit it intact (M9D-D).
    if (patch.changes.alerts !== undefined) this.lastAlerts = patch.changes.alerts;
    for (const listener of this.updateListeners) listener(patch);
  }
}
