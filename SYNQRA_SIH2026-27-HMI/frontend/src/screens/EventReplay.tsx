/**
 * S5 Event / Replay — M9. FR-017, S5-a, NFR-007.
 *
 * ==========================================================================
 *  NO OPERATIONAL CONTROL EXISTS ON THIS SCREEN.
 *
 *  The only interactive elements are replay transport — enter/exit, play,
 *  pause, scrub, speed. Every one of them changes WHAT IS DISPLAYED and
 *  nothing else. There is no command, no dispatch, no override, no
 *  actuation, and no acknowledgement (M9D-F: acknowledgement stays unavailable
 *  while role gating is not enforced server-side, per NFR-011 and
 *  GAP-ROLE-001).
 *
 *  FR-017 AC3 is enforced at the provider boundary, not here: the replay
 *  provider REJECTS `sendAcknowledgement` unconditionally, so no screen can
 *  bypass it and no future screen can forget it.
 *
 *  NFR-007 is PARTIAL, stated on screen: events are timestamped and visible
 *  in S5, but the recording is in memory only (M9D-A) and does not survive a
 *  reload. AMB-010 owes the persistence answer.
 * ==========================================================================
 */

import { EmptyState, MetricCard, Panel, StatusBadge } from "../components/primitives";
import { EVENT_CATEGORIES } from "../contracts/enums";
import { REPLAY_SPEEDS, type ReplaySpeed } from "../providers/ReplayProvider";
import type { LoggedEvent } from "../state/eventLog";
import { useHmi } from "../state/ProviderHost";
import { useAppState } from "../state/useAppState";
import { providerStatusToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

function clockTime(iso: string): string {
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return "INVALID TIMESTAMP";
  return new Date(ms).toISOString().slice(11, 23);
}

/** Categories the HMI may observe. The rest are producer-supplied only (M9D-C). */
const HMI_OBSERVABLE = new Set([
  "ALERT_RAISED",
  "RECOVERY",
  "MODE_TRANSITION",
  "COMMAND_RECEIVED",
  "ALERT_ACKNOWLEDGED",
]);

function EventRow({ entry }: { entry: LoggedEvent }) {
  const fromHmi = entry.origin === "HMI_OBSERVED";
  return (
    <tr>
      <td className="mono">{clockTime(entry.event.timestamp)}</td>
      <td>
        <span className={`event-cat cat-${entry.event.category.toLowerCase()}`}>
          {readable(entry.event.category)}
        </span>
      </td>
      <td className="mono">{entry.event.subjectId ?? "—"}</td>
      <td className="mono">{entry.event.actor ?? "—"}</td>
      <td>
        {fromHmi ? (
          <span className="origin-hmi">HMI OBSERVED</span>
        ) : (
          <span className="faint">SUPPLIED</span>
        )}
      </td>
    </tr>
  );
}

export function EventReplay() {
  const state = useAppState();
  const {
    recording,
    replaying,
    replayPosition,
    enterReplay,
    exitReplay,
    replayPlay,
    replayPause,
    replayScrubTo,
    replaySetSpeed,
  } = useHmi();

  const entries = recording.events;
  const present = new Set(entries.map((e) => e.event.category));
  const durationMs = Math.max(recording.endMs - recording.startMs, 0);

  return (
    <>
      {/* Replay transport. Display-only controls. */}
      <Panel
        title="Replay"
        note={`FR-017 · ${recording.frames.length} recorded frame(s) · ${entries.length} event(s)`}
      >
        <div className="replay-bar">
          <StatusBadge token={providerStatusToken(state.connection.status)} />
          <span className={replaying ? "replay-live replay-on" : "replay-live"}>
            {replaying ? "▶ REPLAY" : "● LIVE"}
          </span>

          {replaying ? (
            <>
              <button type="button" className="replay-button" onClick={exitReplay}>
                Exit replay — return to live
              </button>
              <button
                type="button"
                className="replay-button"
                onClick={replayPosition?.playing ? replayPause : replayPlay}
              >
                {replayPosition?.playing ? "Pause" : "Play"}
              </button>
              {REPLAY_SPEEDS.map((speed: ReplaySpeed) => (
                <button
                  key={speed}
                  type="button"
                  className="replay-button"
                  aria-pressed={replayPosition?.speed === speed}
                  onClick={() => replaySetSpeed(speed)}
                >
                  {speed}×
                </button>
              ))}
            </>
          ) : (
            <button
              type="button"
              className="replay-button"
              disabled={recording.frames.length === 0}
              onClick={enterReplay}
            >
              Enter replay
            </button>
          )}
        </div>

        {replaying && replayPosition ? (
          <>
            <div className="replay-scrub">
              {/* Scrub marks: recorded frames only. No position between frames is
                  offered, because no state was recorded between them (FR-017 AC1). */}
              {recording.frames.map((frame) => (
                <button
                  key={`${frame.atMs}-${frame.sequence}`}
                  type="button"
                  className="scrub-mark"
                  aria-pressed={replayPosition.positionMs === frame.atMs}
                  onClick={() => replayScrubTo(frame.atMs)}
                  title={frame.atIso}
                >
                  {clockTime(frame.atIso)}
                </button>
              ))}
            </div>
            <div className="metrics">
              <MetricCard
                label="Replay position"
                value={new Date(replayPosition.positionMs).toISOString().slice(11, 23)}
                footer="UTC — recorded time, not wall clock"
              />
              <MetricCard
                label="Recorded window"
                value={`${(durationMs / 1000).toFixed(1)}`}
                unit="s"
                footer={`${recording.frames.length} frames`}
              />
              <MetricCard
                label="Playback speed"
                value={`${replayPosition.speed}×`}
                footer={replayPosition.playing ? "playing" : "paused"}
              />
            </div>
            <p className="faint">
              The clock follows the replay position, so ages reproduce what they were at the
              recorded moment rather than ageing against the wall clock (M9D-E).
            </p>
          </>
        ) : null}

        {!replaying && recording.frames.length === 0 ? (
          <EmptyState
            headline="NOTHING RECORDED YET"
            detail="Load a scenario on Operations Overview; the session records as it runs."
          />
        ) : null}

        {state.connection.error ? (
          <p className="unresolved">Provider error: {state.connection.error}</p>
        ) : null}
      </Panel>

      {/* S5-a — the event timeline. */}
      <Panel title="Event timeline" note={`S5-a · ${entries.length} logged event(s)`}>
        {entries.length === 0 ? (
          <EmptyState
            headline="EVENT LOG EMPTY"
            detail="No event has been supplied or observed yet. Nothing is fabricated to fill the timeline."
          />
        ) : (
          <table className="data-table" aria-label="Event timeline">
            <thead>
              <tr>
                <th>Time (UTC)</th>
                <th>Category</th>
                <th>Subject</th>
                <th>Actor</th>
                <th>Origin</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <EventRow key={entry.event.eventId} entry={entry} />
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {/* Honest coverage. S5-a names six subjects; three are producer-supplied only. */}
      <Panel title="Category coverage" note="S5-a · M9D-C">
        <table className="data-table" aria-label="Event category coverage">
          <thead>
            <tr>
              <th>Category</th>
              <th>Source</th>
              <th>Present in this session</th>
            </tr>
          </thead>
          <tbody>
            {EVENT_CATEGORIES.map((category) => (
              <tr key={category}>
                <td className="mono">{readable(category)}</td>
                <td>
                  {HMI_OBSERVABLE.has(category) ? (
                    <span className="faint">HMI-observable or supplied</span>
                  ) : (
                    <span className="unresolved">producer-supplied only</span>
                  )}
                </td>
                <td>{present.has(category) ? "YES" : <span className="dim">no</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="faint">
          FOG_CHANGE, QUEUE_CHANGE and VIOLATION classify operational meaning and are Task 2's to
          report. The HMI never derives them; they appear only when supplied (M9D-C). No authored
          scenario currently supplies any EventRecord, so they are absent rather than invented.
        </p>
        <p className="unresolved">
          NFR-007 is PARTIAL. Events are timestamped and visible here, but the recording is held in
          memory for this session only and does not survive a reload. Persistence awaits AMB-010
          (M9D-A).
        </p>
        <p className="unresolved">
          FR-015 acknowledgement remains unavailable. Role gating must be enforced server-side
          (NFR-011, GAP-ROLE-001), and a frontend-only check would be gating in appearance only
          (M9D-F).
        </p>
      </Panel>
    </>
  );
}
