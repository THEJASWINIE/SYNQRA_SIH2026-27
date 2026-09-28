/**
 * Session recorder — M9. M9D-A, M9D-C.
 *
 * ==========================================================================
 *  A PASSIVE OBSERVER. It never emits, never writes to the store, and never
 *  participates in rendering. Given the same observations it produces the
 *  same recording.
 *
 *  IT DERIVES ONLY WHAT THE HMI ITSELF OBSERVED (M9D-C):
 *    ALERT_RAISED         — an alert APPEARED in state, or the HMI's own feed
 *                           went down (see the contract-gap note below)
 *    RECOVERY             — the HMI's own feed came back
 *    MODE_TRANSITION      — the SUPPLIED system mode changed
 *    COMMAND_RECEIVED     — a supplied dispatch command APPEARED in state
 *
 *  IT NEVER DERIVES: FOG_CHANGE, QUEUE_CHANGE, VIOLATION. Deciding that a
 *  visibility reading constitutes a fog *change*, or that a value constitutes
 *  a *violation*, classifies operational meaning — that is Task 2's judgement.
 *  Those three appear only when a producer supplies them as `EventRecord`
 *  data. Observing that an entity APPEARED is a data-path fact; deciding what
 *  a value MEANS is not, and the line between them is the whole of M9D-C.
 *
 *  Supplied `EventRecord`s pass through verbatim, marked SUPPLIED.
 * ==========================================================================
 */

import type { AppState } from "../contracts/appState";
import type { EventRecord } from "../contracts/domain";
import { EventLog } from "./eventLog";
import { isFeedLost } from "./systemMode";

/** Prefix for every HMI-observed event id, so provenance survives a raw dump. */
export const HMI_EVENT_ID_PREFIX = "HMI-EV:";

function hmiEvent(
  category: EventRecord["category"],
  subjectId: string | null,
  atIso: string,
  payload: unknown,
): EventRecord {
  return {
    eventId: `${HMI_EVENT_ID_PREFIX}${category}:${subjectId ?? "SYSTEM"}:${atIso}`,
    timestamp: atIso,
    category,
    subjectId,
    payload,
    // No operator is involved in an observation. Actor is for operator-initiated events.
    actor: null,
  };
}

export class SessionRecorder {
  readonly log = new EventLog();
  private previous: AppState | null = null;

  /**
   * Observe one state transition.
   *
   * Called after the store has applied a patch. The recorder reads; it never writes back,
   * and it never returns anything the caller could mistake for an instruction.
   */
  observe(state: AppState, atMs: number, atIso: string): void {
    this.log.appendFrame(state, atMs, atIso);

    // 1. Supplied events pass through verbatim. The producer's classification is kept.
    for (const event of state.events) {
      this.log.append(event, "SUPPLIED");
    }

    const prev = this.previous;
    this.previous = state;
    if (prev === null) return; // First observation: nothing has transitioned yet.

    // 2. The HMI's own feed. A data-path fact, not an operational one.
    const wasLost = isFeedLost(prev.connection.status);
    const isLost = isFeedLost(state.connection.status);

    if (!wasLost && isLost) {
      /**
       * CONTRACT GAP (reported, not worked around): `EVENT_CATEGORIES` has `RECOVERY` but
       * no category for communication LOSS — `COMM_LOSS` is an ALERT category, not an
       * event one. Rather than amend the frozen enum or misfile the loss under an
       * unrelated category, it is logged as `ALERT_RAISED` carrying the supplied
       * `COMM_LOSS` category in its payload. That is literally what happened: the HMI
       * raised a COMM_LOSS alert (M8D-A). Nothing is invented.
       */
      this.log.append(
        hmiEvent("ALERT_RAISED", "DATA_PATH", atIso, {
          category: "COMM_LOSS",
          status: state.connection.status,
          error: state.connection.error,
        }),
        "HMI_OBSERVED",
      );
    } else if (wasLost && !isLost) {
      this.log.append(
        hmiEvent("RECOVERY", "DATA_PATH", atIso, { status: state.connection.status }),
        "HMI_OBSERVED",
      );
    }

    // 3. A SUPPLIED system mode changed. The transition is observed; the mode is not
    //    computed. The DEGRADED display floor (M8D-A) is deliberately NOT logged — it is
    //    a presentation result, not a transition the producer reported.
    const prevMode = prev.health?.systemMode ?? null;
    const nextMode = state.health?.systemMode ?? null;
    if (prevMode !== nextMode && nextMode !== null) {
      this.log.append(
        hmiEvent("MODE_TRANSITION", "SYSTEM", atIso, { from: prevMode, to: nextMode }),
        "HMI_OBSERVED",
      );
    }

    // 4. An alert APPEARED. Its severity and category are the producer's, carried through.
    const knownAlerts = new Set(prev.alerts.map((a) => a.alertId));
    for (const alert of state.alerts) {
      if (knownAlerts.has(alert.alertId)) continue;
      this.log.append(
        hmiEvent("ALERT_RAISED", alert.alertId, atIso, {
          category: alert.category,
          severity: alert.severity,
          message: alert.message,
          origin: alert.origin,
        }),
        "HMI_OBSERVED",
      );
    }

    // 5. A supplied dispatch command APPEARED. Receipt is logged; nothing is issued.
    //    This is what FR-010 AC3 asks for — every displayed command also in the log.
    for (const commandId of Object.keys(state.dispatch)) {
      if (commandId in prev.dispatch) continue;
      const command = state.dispatch[commandId];
      if (!command) continue;
      this.log.append(
        hmiEvent("COMMAND_RECEIVED", commandId, atIso, {
          vehicleId: command.vehicleId,
          state: command.state,
          reasonCode: command.reasonCode,
        }),
        "HMI_OBSERVED",
      );
    }
  }

  /** True once anything has been recorded. */
  get hasRecording(): boolean {
    return this.log.frameCount > 0;
  }

  recording() {
    return this.log.recording();
  }
}
