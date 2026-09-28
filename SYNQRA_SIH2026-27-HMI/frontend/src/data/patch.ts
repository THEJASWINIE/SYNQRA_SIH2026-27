/**
 * Patch assembly and merge — M3 (MID-A).
 *
 * SHARED DATA-PATH INFRASTRUCTURE, deliberately outside the provider boundary.
 * Mock (M3), Replay (M9) and Live (M12) all need this identical path; putting it inside
 * a provider would guarantee three divergent copies and break the architecture rule that
 * validation and normalization are shared rather than per-provider.
 *
 * Two responsibilities:
 *   1. Turn validated + normalized messages into an `AppStatePatch`.
 *   2. Merge a `ProviderPatch` into an `AppState` with explicit deletion semantics.
 *
 * Scope: this module moves data. It computes no operational value.
 */

import type { AppState, AppStatePatch } from "../contracts/appState";
import { mergeCommandEvent } from "../state/dispatchCommand";
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
} from "../contracts/domain";
import type { EntityDeletions, ProviderPatch } from "../providers/DataProvider";

/**
 * Normalized messages ready to become a patch.
 *
 * Keyed collections accumulate as arrays here and are folded into `Record`s by
 * `buildPatch`. Singletons are set directly. A field left `undefined` means "no news"
 * and produces no key in the patch — which is what makes NO CHANGE the default.
 */
export interface NormalizedBatch {
  vehicles?: VehicleState[];
  safety?: SafetyState[];
  road?: RoadState[];
  forecasts?: VisibilityForecast[];
  bottlenecks?: BottleneckState[];
  arrivals?: ArrivalPlan[];
  slots?: SlotState[];
  dispatch?: DispatchCommand[];
  alerts?: Alert[];
  events?: EventRecord[];
  topology?: MineTopology;
  health?: SystemHealth;
  kpis?: KpiSnapshot;
  cv?: CVResult;
}

function index<T>(items: readonly T[], key: (item: T) => string): Record<string, T> {
  const out: Record<string, T> = {};
  for (const item of items) {
    out[key(item)] = item;
  }
  return out;
}

/**
 * Assemble an `AppStatePatch` from normalized messages.
 *
 * Only slices actually present in the batch appear in the patch. An empty batch produces
 * an empty patch, not a patch full of empty collections — the difference matters, because
 * an empty collection would read as "everything was removed".
 */
export function buildPatch(batch: NormalizedBatch): AppStatePatch {
  const patch: AppStatePatch = {};

  if (batch.vehicles) patch.vehicles = index(batch.vehicles, (v) => v.vehicleId);
  if (batch.safety) patch.safety = index(batch.safety, (s) => s.vehicleId);
  if (batch.road) patch.road = index(batch.road, (r) => r.segmentId);
  if (batch.forecasts) patch.forecasts = index(batch.forecasts, (f) => f.segmentId);
  if (batch.bottlenecks) patch.bottlenecks = index(batch.bottlenecks, (b) => b.nodeId);
  if (batch.arrivals) patch.arrivals = index(batch.arrivals, (a) => a.nodeId);
  if (batch.slots) patch.slots = index(batch.slots, (s) => s.slotId);
  if (batch.dispatch) patch.dispatch = index(batch.dispatch, (d) => d.commandId);

  // Collection-valued slices are replace-whole: the contract models them as ordered
  // arrays, and merging arrays by identity would invent an ordering rule nobody specified.
  if (batch.alerts) patch.alerts = batch.alerts;
  if (batch.events) patch.events = batch.events;

  if (batch.topology) patch.topology = batch.topology;
  if (batch.health) patch.health = batch.health;
  if (batch.kpis) patch.kpis = batch.kpis;
  if (batch.cv) patch.cv = batch.cv;

  return patch;
}

/** The eight keyed collections that support entity-level deletion. */
const KEYED_SLICES = [
  "vehicles",
  "safety",
  "road",
  "forecasts",
  "bottlenecks",
  "arrivals",
  "slots",
  "dispatch",
] as const;

type KeyedSlice = (typeof KEYED_SLICES)[number];

function removeIds<T>(
  collection: Record<string, T>,
  ids: readonly string[] | undefined,
): Record<string, T> {
  if (!ids || ids.length === 0) return collection;
  const next = { ...collection };
  for (const id of ids) {
    delete next[id];
  }
  return next;
}

/**
 * Merge a `ProviderPatch` into state. MID-C semantics, in one place.
 *
 *   - key missing from `changes`  → NO CHANGE
 *   - key present with an entity  → UPSERT
 *   - id listed in `deletions`    → DELETE
 *
 * Order is deletions first, then changes. An entity both deleted and changed in the same
 * patch therefore EXISTS afterwards — that is a re-add, and treating it as a race would
 * make the outcome depend on key order, which is not a property anyone should rely on.
 *
 * Returns a new object. The input state is never mutated.
 */
export function mergePatch(state: AppState, patch: ProviderPatch): AppState {
  const next: AppState = { ...state };

  // Phase 3 — a command observation carried by the provider (a `command_issued` frame).
  // Merged through the SAME pure function the S4 panel uses for HTTP results, so one
  // command_id yields exactly one record regardless of which arrived first.
  if (patch.commandEvent) {
    next.commands = mergeCommandEvent(state.commands, patch.commandEvent);
  }

  // 1. Deletions.
  const deletions: EntityDeletions = patch.deletions ?? {};
  for (const slice of KEYED_SLICES) {
    const ids = deletions[slice];
    if (!ids || ids.length === 0) continue;
    // Each keyed slice is a Record of its own entity type; the cast is confined here and
    // is safe because KEYED_SLICES lists only Record-valued keys of AppState.
    next[slice] = removeIds(
      state[slice] as Record<string, unknown>,
      ids,
    ) as AppState[KeyedSlice] as never;
  }

  // 2. Changes.
  const changes = patch.changes;

  for (const slice of KEYED_SLICES) {
    const incoming = changes[slice];
    if (incoming === undefined) continue; // NO CHANGE
    next[slice] = {
      ...(next[slice] as Record<string, unknown>),
      ...(incoming as Record<string, unknown>),
    } as AppState[KeyedSlice] as never;
  }

  // Replace-whole slices.
  if (changes.alerts !== undefined) next.alerts = changes.alerts;
  if (changes.events !== undefined) next.events = changes.events;

  // Singletons. `undefined` means no news; an explicit `null` is a real value meaning
  // "not available", and is applied.
  if (changes.topology !== undefined) next.topology = changes.topology;
  if (changes.health !== undefined) next.health = changes.health;
  if (changes.kpis !== undefined) next.kpis = changes.kpis;
  if (changes.cv !== undefined) next.cv = changes.cv;
  if (changes.connection !== undefined) next.connection = changes.connection;
  if (changes.clock !== undefined) next.clock = changes.clock;

  return next;
}

/** An empty starting state. Used by tests and, later, by the store M4 introduces. */
export function emptyAppState(nowIso: string): AppState {
  return {
    connection: {
      status: "IDLE",
      provider: "MOCK",
      scenarioName: null,
      lastMessageAt: null,
      error: null,
    },
    clock: { now: nowIso, replayPosition: null },
    topology: null,
    vehicles: {},
    safety: {},
    road: {},
    forecasts: {},
    bottlenecks: {},
    arrivals: {},
    slots: {},
    dispatch: {},
    alerts: [],
    events: [],
    health: null,
    kpis: null,
    cv: null,
    // Phase 3 — the session command log starts empty and is never inferred.
    commands: [],
    // Phase 4 — IDLE, not zeroed: nothing has been measured yet.
    observability: { status: "IDLE", data: null, fetchedAt: null, error: null },
  };
}
