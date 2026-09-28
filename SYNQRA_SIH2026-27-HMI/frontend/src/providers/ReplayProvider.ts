/**
 * ReplayProvider — M9. The third `DataProvider`, exactly as M2 declared it would be.
 *
 * ==========================================================================
 *  FR-017 AC4: "Replay is implemented as a third provider behind the same
 *  interface, not as a parallel UI." No screen knows this exists. Every
 *  screen replays because it reads the same normalized `AppState`.
 *
 *  FR-017 AC1 is exact: scrubbing to *t* reproduces the state recorded at *t*.
 *  This provider REPLAYS RECORDED FRAMES ONLY. It does not interpolate
 *  between them, does not predict a state that was never recorded, and does
 *  not reconstruct anything from deltas. Before the first frame there is
 *  nothing to show, and it says so rather than inventing a starting state.
 *
 *  FR-017 AC3: NO COMMAND MAY BE ISSUED WHILE IN REPLAY. There is exactly one
 *  method on the interface that could act — `sendAcknowledgement` — and it
 *  REJECTS unconditionally here. The rejection lives at the provider
 *  boundary, so no screen can bypass it and no future screen can forget it.
 *
 *  M9D-E: the replay clock. Each emission carries `clock.now` = the replay
 *  position, so freshness reproduces what it was at *t* instead of ageing
 *  every replayed value against the wall clock.
 * ==========================================================================
 */

import type { AppStatePatch, ConnectionStatus } from "../contracts/appState";
import type { ProviderError } from "../data/errors";
import { providerError } from "../data/errors";
import { type Frame, frameAt, type Recording } from "../state/eventLog";
import type {
  DataProvider,
  EntityDeletions,
  ProviderPatch,
  StatusListener,
  Unsubscribe,
  UpdateListener,
} from "./DataProvider";
import { realScheduler, type Scheduler } from "./scheduler";

/** The keyed slices, mirroring `data/patch.ts`. A frame swap must account for all of them. */
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

export const REPLAY_COMMAND_REJECTED =
  "Rejected: no command or acknowledgement may be issued while replaying (FR-017 AC3).";

/** How often playback advances. Presentation cadence only; it moves no operational value. */
export const REPLAY_TICK_MS = 250;

export const REPLAY_SPEEDS = [0.5, 1, 2, 4] as const;
export type ReplaySpeed = (typeof REPLAY_SPEEDS)[number];

export interface ReplayProviderOptions {
  scheduler?: Scheduler;
}

export interface ReplayPositionState {
  positionMs: number;
  startMs: number;
  endMs: number;
  playing: boolean;
  speed: ReplaySpeed;
  frameCount: number;
}

export type PositionListener = (position: ReplayPositionState) => void;

export class ReplayProvider implements DataProvider {
  readonly kind = "REPLAY" as const;

  private readonly recording: Recording;
  private readonly scheduler: Scheduler;

  private status: ConnectionStatus = "IDLE";
  private connected = false;
  private playing = false;
  private speed: ReplaySpeed = 1;
  private positionMs: number;

  /** The frame last emitted, so the next emission can compute an exact delta. */
  private emitted: Frame | null = null;

  private readonly updateListeners = new Set<UpdateListener>();
  private readonly statusListeners = new Set<StatusListener>();
  private readonly positionListeners = new Set<PositionListener>();

  constructor(recording: Recording, options: ReplayProviderOptions = {}) {
    this.recording = recording;
    this.scheduler = options.scheduler ?? realScheduler();
    this.positionMs = recording.startMs;
  }

  // -- lifecycle ------------------------------------------------------------

  async connect(): Promise<void> {
    if (this.recording.frames.length === 0) {
      const error = providerError("INITIALIZATION", "No recorded session to replay", {
        occurredAt: new Date().toISOString(),
        retryable: false,
      });
      this.setStatus("ERROR", error);
      throw error;
    }

    this.connected = true;
    this.setStatus("CONNECTING", null);
    this.setStatus("CONNECTED", null);
    this.scrubTo(this.recording.startMs);
  }

  /** Idempotent. No scheduled playback may survive it. */
  async disconnect(): Promise<void> {
    this.scheduler.cancelAll();
    this.playing = false;
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

  onPositionChange(listener: PositionListener): Unsubscribe {
    this.positionListeners.add(listener);
    return () => {
      this.positionListeners.delete(listener);
    };
  }

  /**
   * FR-017 AC3 — ALWAYS REJECTS.
   *
   * Replay is a view of what already happened. Acknowledging inside it would either write
   * into history, which is a lie, or do nothing, which is worse because the operator would
   * believe they had acted. The signature is kept so the interface stays uniform; the
   * behaviour is a typed rejection at the boundary.
   */
  async sendAcknowledgement(_alertId: string, _actor: string): Promise<void> {
    throw providerError("ABORTED", REPLAY_COMMAND_REJECTED, {
      occurredAt: new Date().toISOString(),
      retryable: false,
    });
  }

  // -- replay controls ------------------------------------------------------

  get position(): ReplayPositionState {
    return {
      positionMs: this.positionMs,
      startMs: this.recording.startMs,
      endMs: this.recording.endMs,
      playing: this.playing,
      speed: this.speed,
      frameCount: this.recording.frames.length,
    };
  }

  play(): void {
    if (!this.connected || this.playing) return;
    // Replaying from the end restarts, rather than sitting on a dead play button.
    if (this.positionMs >= this.recording.endMs) this.scrubTo(this.recording.startMs);
    this.playing = true;
    this.emitPosition();
    this.schedulePlaybackStep();
  }

  pause(): void {
    if (!this.playing) return;
    this.playing = false;
    this.scheduler.cancelAll();
    this.emitPosition();
  }

  setSpeed(speed: ReplaySpeed): void {
    this.speed = speed;
    this.emitPosition();
  }

  /**
   * Move to `atMs` and emit the state recorded there.
   *
   * Clamped to the recorded window: a position outside it has no recorded state, and
   * showing the nearest one unlabelled would misrepresent when it was.
   */
  scrubTo(atMs: number): void {
    const clamped = Math.min(Math.max(atMs, this.recording.startMs), this.recording.endMs);
    this.positionMs = clamped;
    this.emitFrameAt(clamped);
    this.emitPosition();
  }

  private schedulePlaybackStep(): void {
    this.scheduler.schedule(REPLAY_TICK_MS, () => {
      if (!this.playing || !this.connected) return;

      const next = this.positionMs + REPLAY_TICK_MS * this.speed;
      if (next >= this.recording.endMs) {
        this.positionMs = this.recording.endMs;
        this.emitFrameAt(this.positionMs);
        this.playing = false;
        this.emitPosition();
        return;
      }

      this.positionMs = next;
      this.emitFrameAt(next);
      this.emitPosition();
      this.schedulePlaybackStep();
    });
  }

  // -- emission -------------------------------------------------------------

  /**
   * Emit the recorded state at `atMs` as a patch that transforms whatever the store holds
   * into exactly that state.
   *
   * Scrubbing BACKWARDS is why deletions matter: entities present in the previously
   * emitted frame but absent from the target must be removed, or the store would keep
   * vehicles that did not exist at *t*. The explicit deletions channel (MID-C) is exactly
   * the mechanism for this, which is why no new merge semantics are needed.
   */
  private emitFrameAt(atMs: number): void {
    const frame = frameAt(this.recording, atMs);
    if (!frame) return;

    const target = frame.state;
    const previous = this.emitted?.state ?? null;
    const atIso = new Date(atMs).toISOString();

    const deletions: EntityDeletions = {};
    if (previous !== null) {
      for (const slice of KEYED_SLICES) {
        const gone = Object.keys(previous[slice]).filter((id) => !(id in target[slice]));
        if (gone.length > 0) deletions[slice] = gone;
      }
    }

    const changes: AppStatePatch = {
      topology: target.topology,
      vehicles: target.vehicles,
      safety: target.safety,
      road: target.road,
      forecasts: target.forecasts,
      bottlenecks: target.bottlenecks,
      arrivals: target.arrivals,
      slots: target.slots,
      dispatch: target.dispatch,
      alerts: target.alerts,
      events: target.events,
      health: target.health,
      kpis: target.kpis,
      cv: target.cv,
      /**
       * M9D-E — the replay clock. `now` follows the replay position so ages reproduce
       * what they were at *t*. Without this every replayed value would age against the
       * wall clock and read stale, which would be a false signal about a moment that was
       * in fact current.
       */
      clock: { now: atIso, replayPosition: atIso },
    };

    this.emitted = frame;
    const patch: ProviderPatch =
      Object.keys(deletions).length > 0 ? { changes, deletions } : { changes };

    for (const listener of this.updateListeners) listener(patch);
  }

  private emitPosition(): void {
    const position = this.position;
    for (const listener of this.positionListeners) listener(position);
  }

  private setStatus(status: ConnectionStatus, error: ProviderError | null): void {
    this.status = status;
    for (const listener of this.statusListeners) listener(status, error);
  }

  get currentStatus(): ConnectionStatus {
    return this.status;
  }
}
