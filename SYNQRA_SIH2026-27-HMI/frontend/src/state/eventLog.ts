/**
 * Append-only event log and session recording — M9. M9D-A, M9D-B.
 *
 * ==========================================================================
 *  THIS IS THE AUDIT TRAIL. `AppState.events` IS NOT.
 *
 *  Contract §13 makes `AppState.events` a REPLACE-WHOLE slice, which is right
 *  for "the events in this delivery" and unusable as a trail: every delivery
 *  replaces the array. Rather than amend the frozen contract (D8), the log
 *  lives here, outside `AppState`, and appends from it (M9D-B).
 *
 *  APPEND-ONLY MEANS APPEND-ONLY. Entries are never mutated, never reordered
 *  and never dropped. There is deliberately no `remove`, no `update` and no
 *  `truncate` — an audit trail that can lose an entry is not an audit trail.
 *
 *  IN MEMORY ONLY (M9D-A). Nothing here survives a page reload. NFR-007's
 *  "persisted" is therefore NOT satisfied, and is recorded as an open
 *  non-conformance pending AMB-010.
 * ==========================================================================
 */

import type { AppState } from "../contracts/appState";
import type { EventRecord } from "../contracts/domain";

/** Where an entry came from. Shown, so provenance is never guessed. */
export type EventOrigin =
  /** Supplied by the producer as an `EventRecord`. */
  | "SUPPLIED"
  /** Observed by the HMI in its own state or data path (M9D-C). */
  | "HMI_OBSERVED";

export interface LoggedEvent {
  readonly event: EventRecord;
  readonly origin: EventOrigin;
  /** Epoch ms of the event's own timestamp, for ordering and scrubbing. */
  readonly atMs: number;
  /** Monotonic arrival index. Breaks timestamp ties without reordering history. */
  readonly sequence: number;
}

/**
 * One recorded moment: the complete application state as it stood.
 *
 * Full snapshots, not deltas. FR-017 AC1 requires scrubbing to *t* to reproduce the state
 * recorded at *t* exactly, and a snapshot reproduces it by definition — no replaying of
 * deltas, no interpolation, no reconstruction that could drift. Sessions are seconds long
 * and states are small, so the cost is not worth the risk of an approximate reconstruction.
 */
export interface Frame {
  readonly atMs: number;
  readonly atIso: string;
  readonly state: AppState;
  readonly sequence: number;
}

export interface Recording {
  readonly frames: readonly Frame[];
  readonly events: readonly LoggedEvent[];
  readonly startMs: number;
  readonly endMs: number;
}

export class EventLog {
  private readonly loggedEvents: LoggedEvent[] = [];
  private readonly loggedFrames: Frame[] = [];
  private nextSequence = 0;

  /**
   * Append one event. The only way in.
   *
   * Duplicate `eventId`s are dropped: a supplied event re-delivered in a later patch is
   * the same event, and logging it twice would inflate the trail. The FIRST occurrence is
   * kept — history is never rewritten by a later copy.
   */
  append(event: EventRecord, origin: EventOrigin): boolean {
    if (this.loggedEvents.some((e) => e.event.eventId === event.eventId)) return false;

    const parsed = Date.parse(event.timestamp);
    this.loggedEvents.push({
      event,
      origin,
      // An unparseable timestamp must not silently sort to 1970; it keeps arrival order.
      atMs: Number.isFinite(parsed) ? parsed : Number.NaN,
      sequence: this.nextSequence++,
    });
    return true;
  }

  /** Record the complete state at a moment. */
  appendFrame(state: AppState, atMs: number, atIso: string): void {
    this.loggedFrames.push({ atMs, atIso, state, sequence: this.nextSequence++ });
  }

  /**
   * Every event, in deterministic order: by timestamp, then by arrival sequence.
   *
   * Sorting a COPY. The stored order is arrival order and is never disturbed — this is a
   * display ordering, exactly like `rankAlerts`. Entries whose timestamp could not be
   * parsed sort last, by arrival, rather than to the epoch.
   */
  entries(): LoggedEvent[] {
    return [...this.loggedEvents].sort((a, b) => {
      const aBad = Number.isNaN(a.atMs);
      const bBad = Number.isNaN(b.atMs);
      if (aBad !== bBad) return aBad ? 1 : -1;
      if (!aBad && a.atMs !== b.atMs) return a.atMs - b.atMs;
      return a.sequence - b.sequence;
    });
  }

  /** Events at or before `atMs`, for the replay timeline. Unparseable ones are excluded. */
  entriesUpTo(atMs: number): LoggedEvent[] {
    return this.entries().filter((e) => !Number.isNaN(e.atMs) && e.atMs <= atMs);
  }

  frames(): readonly Frame[] {
    return this.loggedFrames;
  }

  get eventCount(): number {
    return this.loggedEvents.length;
  }

  get frameCount(): number {
    return this.loggedFrames.length;
  }

  /**
   * The recorded session, for a `ReplayProvider`.
   *
   * Returns copies, so a replay in progress cannot be disturbed by continued recording.
   */
  recording(): Recording {
    const frames = [...this.loggedFrames].sort(
      (a, b) => a.atMs - b.atMs || a.sequence - b.sequence,
    );
    return {
      frames,
      events: this.entries(),
      startMs: frames[0]?.atMs ?? 0,
      endMs: frames[frames.length - 1]?.atMs ?? 0,
    };
  }
}

/**
 * The state recorded at `atMs`: the latest frame at or before it.
 *
 * EXACT, NEVER APPROXIMATE. No interpolation between frames, no prediction of a state
 * that was never recorded. Before the first frame there is nothing to show, and null says
 * so rather than inventing an initial state.
 */
export function frameAt(recording: Recording, atMs: number): Frame | null {
  let found: Frame | null = null;
  for (const frame of recording.frames) {
    if (frame.atMs > atMs) break;
    found = frame;
  }
  return found;
}
