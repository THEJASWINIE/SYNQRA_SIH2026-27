/**
 * AppStateStore — M4. M4D-D.
 *
 * The single holder of normalized application state. React subscribes through
 * `useSyncExternalStore`; no state library is involved, because React already ships the
 * external-store subscription primitive.
 *
 * Three rules this module exists to hold:
 *
 *   1. **Patch semantics are not re-interpreted here.** Merging is delegated to the
 *      shared `data/patch.ts`, which Mock (M3), Replay (M9) and Live (M12) all use. A
 *      second merge implementation would be a second definition, free to drift.
 *   2. **The store computes no operational value.** It stores what the data path gives
 *      it. Nothing here derives a speed, a headway, a queue or a risk.
 *   3. **The clock advances presentation only.** `tick()` moves `clock.now` and touches
 *      nothing else, so displayed ages advance without any datum being altered.
 */

import type { AppState, ConnectionStatus, ProviderKind } from "../contracts/appState";
import { emptyAppState, mergePatch } from "../data/patch";
import type { ProviderPatch } from "../providers/DataProvider";

export type StoreListener = () => void;

export class AppStateStore {
  private state: AppState;
  private readonly listeners = new Set<StoreListener>();

  constructor(nowIso: string, provider: ProviderKind = "MOCK") {
    this.state = {
      ...emptyAppState(nowIso),
      connection: { ...emptyAppState(nowIso).connection, provider },
    };
  }

  /**
   * Stable-identity read. `useSyncExternalStore` compares by reference, so every mutator
   * below must produce a new top-level object and non-mutators must not.
   */
  getSnapshot = (): AppState => this.state;

  subscribe = (listener: StoreListener): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private commit(next: AppState): void {
    this.state = next;
    for (const listener of this.listeners) listener();
  }

  /**
   * Apply one provider delivery.
   *
   * `lastMessageAt` records when the HMI received it — a property of the delivery, not of
   * any datum. Per-datum freshness comes from each entity's own supplied timestamp at
   * render time (M4D-E), never from this field.
   */
  applyPatch(patch: ProviderPatch, receivedAtIso: string): void {
    const merged = mergePatch(this.state, patch);
    this.commit({
      ...merged,
      connection: { ...merged.connection, lastMessageAt: receivedAtIso },
    });
  }

  setStatus(status: ConnectionStatus, error: string | null): void {
    this.commit({
      ...this.state,
      connection: { ...this.state.connection, status, error },
    });
  }

  /**
   * Which provider is driving the store. Display provenance only — it changes no datum,
   * and FR-017 AC2 needs replay to be unmistakable on every screen.
   */
  setProvider(provider: ProviderKind): void {
    this.commit({
      ...this.state,
      connection: { ...this.state.connection, provider },
    });
  }

  setScenarioName(scenarioName: string | null): void {
    this.commit({
      ...this.state,
      connection: { ...this.state.connection, scenarioName },
    });
  }

  /**
   * Discard all operational state.
   *
   * Required when switching scenarios: without it, vehicles, alerts and bottlenecks from
   * the previous scenario would linger and be read as current. Provider identity is
   * preserved because the provider did not change; the data did.
   */
  reset(nowIso: string): void {
    const fresh = emptyAppState(nowIso);
    this.commit({
      ...fresh,
      connection: { ...fresh.connection, provider: this.state.connection.provider },
    });
  }

  /**
   * DISPLAY TICKER — presentation only.
   *
   * Advances the render clock so `ageMs` recomputes and displayed ages move. It must
   * never generate, interpolate, extrapolate or modify an operational value: no vehicle
   * moves, no visibility decays, no queue advances toward a forecast. Doing any of those
   * would make this a simulation, which Task 1 is forbidden to be (M4D-E).
   */
  tick(nowIso: string): void {
    /**
     * M9D-E — during replay the clock follows `replayPosition`, which the replay provider
     * sets through its patches. The live ticker must not advance it, or every replayed
     * value would age against the wall clock and read stale for a moment that was in fact
     * current. Guarded here, in the store, so no caller can break it.
     */
    if (this.state.clock.replayPosition !== null) return;
    if (this.state.clock.now === nowIso) return;
    this.commit({
      ...this.state,
      clock: { ...this.state.clock, now: nowIso },
    });
  }
}
