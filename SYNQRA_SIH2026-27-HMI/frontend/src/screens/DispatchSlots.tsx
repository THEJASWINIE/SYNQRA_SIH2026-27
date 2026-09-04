/**
 * S4 Dispatch & Slots — M7.
 *
 * Satisfies HMI-FR-009 (slot reservation) and FR-010 (dispatch decision).
 *
 * ==========================================================================
 *  EVERY VALUE ON THIS SCREEN IS SUPPLIED. DISPLAY ONLY.
 *
 *  Nothing here selects or optimizes an assignment, generates or resolves a
 *  slot, runs a slot solver, detects a conflict, calculates an ETA, computes
 *  or optimizes a route, calculates a target speed, or produces any other
 *  Task 2 output.
 *
 *  The screen performs exactly the derivations on the closed list: data age,
 *  display ordering, unit formatting, and — per M7D-B — positioning supplied
 *  slot times on a time axis, the same class of transform as M4D-F's map
 *  coordinate.
 *
 *  NO CONTROL SURFACE EXISTS. No dispatch, approve, apply, override, release,
 *  hold, send, execute or modify control. No form and no submit path. The only
 *  interactive elements are the resource selector and the back link, both of
 *  which change what is displayed and nothing else.
 *
 *  AMB-008 (may the HMI issue commands) and AMB-009 (what "override" means)
 *  remain UNRESOLVED. Rendering a supplied `RECOMMENDED` or `ISSUED` state is
 *  producer-reported metadata and is not a ruling on either (M7D-A).
 * ==========================================================================
 */

import { useState } from "react";
import {
  EmptyState,
  FreshnessIndicator,
  MetricCard,
  Panel,
  StatusBadge,
} from "../components/primitives";
import type { DispatchCommand, SlotState } from "../contracts/domain";
import {
  conflictingSlots,
  fmt,
  groupSlotsByResource,
  isReasonCodeMissing,
  kmh,
  REASON_CODE_MISSING_TEXT,
  type ResourceSlots,
  rankDispatch,
  TIME_AXIS_UNAVAILABLE_REASON_TEXT,
} from "../state/derive";
import { viewFreshness } from "../state/freshness";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { dispatchStateToken, providerStatusToken, slotStatusToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

const UNAVAILABLE = "UNAVAILABLE";
const NOT_SUPPLIED = "NOT SUPPLIED";

/** Clock time from a supplied ISO timestamp. Formatting only; the value is unchanged. */
function clockTime(iso: string | null): string {
  if (iso === null) return NOT_SUPPLIED;
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return "INVALID TIMESTAMP";
  return new Date(ms).toISOString().slice(11, 19);
}

// ---------------------------------------------------------------------------
// FR-009 — Conflicts. First, and never behind colour alone.
// ---------------------------------------------------------------------------

function ConflictSection({ slots }: { slots: SlotState[] }) {
  if (slots.length === 0) {
    return (
      <EmptyState
        headline="NO ACTIVE SLOT CONFLICT"
        detail="No supplied slot reports a conflict. The HMI runs no conflict detection of its own — if Task 2 reports none, none is shown."
      />
    );
  }

  return (
    <div className="conflict-list">
      {slots.map((slot) => (
        <div className="conflict-row" key={slot.slotId}>
          <strong className="violation-marker">▲ SLOT CONFLICT</strong>
          <div>
            <span className="mono">{slot.slotId}</span> on resource{" "}
            <span className="mono">{slot.resourceId}</span>
            {slot.vehicleId ? (
              <>
                {" "}
                held by <span className="mono">{slot.vehicleId}</span>
              </>
            ) : (
              " — no holder supplied"
            )}
          </div>
          <div>
            {slot.conflictWith !== null && slot.conflictWith.length > 0 ? (
              <>
                CONFLICTS WITH <span className="mono">{slot.conflictWith.join(", ")}</span>
              </>
            ) : (
              <span className="dim">CONFLICTING SLOT IDS NOT SUPPLIED</span>
            )}
          </div>
          <div className="faint">
            {clockTime(slot.startTime)} – {clockTime(slot.endTime)} · status supplied as{" "}
            {readable(slot.status)}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FR-009 — Slot timeline
// ---------------------------------------------------------------------------

function SlotTimeline({ group }: { group: ResourceSlots }) {
  if (!group.axis.ok) {
    return (
      <>
        <EmptyState
          headline="TIMELINE UNAVAILABLE"
          detail={`Bands cannot be positioned for ${group.resourceId}: ${
            TIME_AXIS_UNAVAILABLE_REASON_TEXT[group.axis.reason]
          }. No time is guessed.`}
        />
        <SlotTable slots={group.slots} />
      </>
    );
  }

  const { axis } = group.axis;

  return (
    <>
      <section
        className="timeline"
        style={{ ["--lanes" as string]: String(group.laneCount) }}
        aria-label={`Slot timeline for ${group.resourceId}`}
      >
        {group.bands.map((band) => {
          const conflict =
            band.slot.status === "CONFLICT" ||
            (band.slot.conflictWith !== null && band.slot.conflictWith.length > 0);
          return (
            <div
              key={band.slot.slotId}
              className={`slot-band${conflict ? " conflict" : ""}`}
              style={{
                left: `${band.left * 100}%`,
                width: `${band.width * 100}%`,
                top: `${band.lane * 2.4}rem`,
              }}
              title={`${band.slot.slotId} ${band.slot.status}`}
            >
              <span className="mono">{band.slot.slotId}</span>{" "}
              <span>{band.slot.vehicleId ?? "no holder"}</span>{" "}
              <span aria-hidden="true">{slotStatusToken(band.slot.status).glyph}</span>{" "}
              <span>{band.slot.status}</span>
            </div>
          );
        })}
      </section>

      <div className="timeline-axis" aria-hidden="true">
        {axis.ticks.map((tick) => (
          <span key={tick}>{new Date(tick).toISOString().slice(11, 19)}</span>
        ))}
      </div>
      <p className="faint">
        Axis spans the supplied slot times {clockTime(new Date(axis.startMs).toISOString())} to{" "}
        {clockTime(new Date(axis.endMs).toISOString())} (UTC). Bands are positioned from supplied
        start and end times only.
      </p>

      <SlotTable slots={group.slots} />
    </>
  );
}

/** Every band is also a table row, so an overlap is readable without reading the chart. */
function SlotTable({ slots }: { slots: SlotState[] }) {
  return (
    <table className="data-table" aria-label="Supplied slot reservations">
      <thead>
        <tr>
          <th>Slot</th>
          <th>Holder</th>
          <th>Status</th>
          <th>Window (UTC)</th>
          <th>ETA (supplied)</th>
          <th>Conflicts with</th>
        </tr>
      </thead>
      <tbody>
        {slots.map((slot) => (
          <tr key={slot.slotId} className={slot.status === "CONFLICT" ? "row-conflict" : undefined}>
            <td className="mono">{slot.slotId}</td>
            <td className="mono">{slot.vehicleId ?? UNAVAILABLE}</td>
            <td>
              <StatusBadge token={slotStatusToken(slot.status)} />
            </td>
            <td className="mono">
              {clockTime(slot.startTime)} – {clockTime(slot.endTime)}
            </td>
            <td className="mono">{slot.eta === null ? NOT_SUPPLIED : clockTime(slot.eta)}</td>
            <td className="mono">
              {slot.conflictWith !== null && slot.conflictWith.length > 0
                ? slot.conflictWith.join(", ")
                : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// FR-010 — Dispatch assignments
// ---------------------------------------------------------------------------

function DispatchRow({
  command,
  slots,
}: {
  command: DispatchCommand;
  slots: Record<string, SlotState>;
}) {
  const missingReason = isReasonCodeMissing(command.reasonCode);
  const slot = command.slotId ? slots[command.slotId] : undefined;

  return (
    <tr>
      <td className="mono">{command.commandId}</td>
      <td className="mono">{command.vehicleId}</td>
      <td>
        <StatusBadge token={dispatchStateToken(command.state)} />
      </td>
      <td className="mono">{command.routeId ?? NOT_SUPPLIED}</td>
      <td className="mono">{clockTime(command.departureTime)}</td>
      <td className="mono">
        {command.targetSpeed === null ? (
          <span className="dim">{NOT_SUPPLIED}</span>
        ) : (
          <>
            {fmt(kmh(command.targetSpeed))}
            <span className="metric-unit">km/h</span>
          </>
        )}
      </td>
      <td className="mono">{command.slotId ?? NOT_SUPPLIED}</td>
      <td className="mono">
        {slot === undefined ? (
          command.slotId ? (
            <span className="dim">SLOT NOT SUPPLIED</span>
          ) : (
            "—"
          )
        ) : slot.eta === null ? (
          <span className="dim">{NOT_SUPPLIED}</span>
        ) : (
          clockTime(slot.eta)
        )}
      </td>
      <td>
        {missingReason ? (
          <strong className="violation-marker">▲ {REASON_CODE_MISSING_TEXT}</strong>
        ) : (
          <span className="mono">{command.reasonCode}</span>
        )}
      </td>
    </tr>
  );
}

function DispatchDetail({ command }: { command: DispatchCommand }) {
  return (
    <div className="dispatch-detail">
      <h3 className="mono">
        {command.commandId} · {command.vehicleId}
      </h3>
      <div className="metrics">
        <MetricCard
          label="State (supplied)"
          value={command.state}
          footer="reported by the producer"
        />
        <MetricCard
          label="Departure (UTC)"
          value={clockTime(command.departureTime)}
          footer="supplied"
        />
        <MetricCard
          label="Target speed"
          value={command.targetSpeed === null ? NOT_SUPPLIED : fmt(kmh(command.targetSpeed))}
          {...(command.targetSpeed !== null ? { unit: "km/h" } : {})}
          footer={
            command.targetSpeed === null
              ? "not supplied"
              : `supplied ${fmt(command.targetSpeed, 2)} m/s`
          }
        />
        <MetricCard label="Slot" value={command.slotId ?? NOT_SUPPLIED} footer="supplied" />
      </div>

      <dl className="fields">
        <div className="field">
          <dt>Route (supplied)</dt>
          <dd>{command.routeId ?? NOT_SUPPLIED}</dd>
          <div className="faint">
            {command.routeNodeIds !== null && command.routeNodeIds.length > 0
              ? command.routeNodeIds.join(" → ")
              : "route node chain not supplied"}
          </div>
        </div>
        <div className="field">
          <dt>Reason code</dt>
          <dd>
            {isReasonCodeMissing(command.reasonCode) ? (
              <strong className="violation-marker">▲ {REASON_CODE_MISSING_TEXT}</strong>
            ) : (
              command.reasonCode
            )}
          </dd>
          <div className="faint">mandatory per NFR-006</div>
        </div>
        <div className="field">
          <dt>Limiting variables</dt>
          <dd>
            {command.limitingVariables !== null && command.limitingVariables.length > 0
              ? command.limitingVariables.map(readable).join(", ")
              : NOT_SUPPLIED}
          </dd>
          <div className="faint">supplied — NFR-006 key limiting variables</div>
        </div>
        <div className="field">
          <dt>Command timestamp (source)</dt>
          <dd>{command.timestamp}</dd>
        </div>
      </dl>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function DispatchSlots() {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();
  const fresh = (timestamp: string | null | undefined) => viewFreshness(timestamp, config, nowMs);

  const conflicts = conflictingSlots(state.slots);
  const groups = groupSlotsByResource(state.slots);
  const commands = rankDispatch(state.dispatch);

  /** Which resource's timeline is expanded. UI state, not operational data. */
  const [openResource, setOpenResource] = useState<string | null>(null);
  const selected = groups.find((g) => g.resourceId === openResource) ?? groups[0] ?? null;

  const newestSlot = Object.values(state.slots).reduce<string | null>(
    (latest, s) => (latest === null || s.startTime > latest ? s.startTime : latest),
    null,
  );
  const newestCommand = commands[0]?.timestamp ?? null;

  return (
    <>
      {/* 1 — CONFLICTS. Above the timeline, never collapsed. */}
      <Panel
        title="Slot conflicts"
        note={
          conflicts.length > 0
            ? `${conflicts.length} supplied conflict(s)`
            : "supplied by the data layer"
        }
      >
        <ConflictSection slots={conflicts} />
      </Panel>

      {/* 2 — SLOT TIMELINE */}
      <Panel
        title="Slot timeline"
        note={`FR-009 · ${groups.length} resource(s) · supplied times only`}
      >
        {groups.length === 0 ? (
          <EmptyState
            headline="SLOT DATA UNAVAILABLE"
            detail="No SlotState has been supplied. Task 1 does not generate slots."
          />
        ) : (
          <>
            {groups.length > 1 ? (
              <div className="resource-tabs">
                {groups.map((group) => (
                  <button
                    key={group.resourceId}
                    type="button"
                    className="resource-tab"
                    aria-pressed={group.resourceId === selected?.resourceId}
                    onClick={() => setOpenResource(group.resourceId)}
                  >
                    {group.resourceId}
                    {group.hasConflict ? " ▲" : ""}
                  </button>
                ))}
              </div>
            ) : null}

            {selected ? (
              <>
                <h3 className="mono">
                  {selected.resourceId}
                  {selected.hasConflict ? " — ▲ CONFLICT SUPPLIED" : ""}
                </h3>
                <SlotTimeline group={selected} />
              </>
            ) : null}
          </>
        )}
      </Panel>

      {/* 3 — DISPATCH ASSIGNMENTS */}
      <Panel
        title="Dispatch assignments"
        note={`FR-010 · ${commands.length} supplied command(s) · display only`}
      >
        {commands.length === 0 ? (
          <EmptyState
            headline="DISPATCH DATA UNAVAILABLE"
            detail="No DispatchCommand has been supplied. Task 1 neither selects nor optimizes an assignment."
          />
        ) : (
          <>
            <table className="data-table" aria-label="Supplied dispatch commands">
              <thead>
                <tr>
                  <th>Command</th>
                  <th>Vehicle</th>
                  <th>State</th>
                  <th>Route</th>
                  <th>Departure (UTC)</th>
                  <th>Target speed</th>
                  <th>Slot</th>
                  <th>ETA (supplied)</th>
                  <th>Reason code</th>
                </tr>
              </thead>
              <tbody>
                {commands.map((command) => (
                  <DispatchRow key={command.commandId} command={command} slots={state.slots} />
                ))}
              </tbody>
            </table>

            {commands.map((command) => (
              <DispatchDetail key={command.commandId} command={command} />
            ))}
          </>
        )}

        {/* M7D-C — recorded on screen rather than implied complete. */}
        <p className="unresolved">
          FR-010 AC3 — "every displayed command also appears in the event log" — is NOT verified in
          this milestone. No event log exists yet; it arrives with S5 at M9. No event records are
          manufactured here to close the gap.
        </p>
      </Panel>

      {/* 4 — PROVENANCE */}
      <Panel title="Provenance and freshness" note="NFR-003 · NFR-007">
        <dl className="fields">
          <div className="field">
            <dt>Data connection</dt>
            <dd>{providerStatusToken(state.connection.status).label}</dd>
            {state.connection.error ? <div className="faint">{state.connection.error}</div> : null}
          </div>
          <div className="field">
            <dt>Provider</dt>
            <dd>{state.connection.provider}</dd>
          </div>
          <div className="field">
            <dt>Scenario</dt>
            <dd>{state.connection.scenarioName ?? UNAVAILABLE}</dd>
          </div>
          <div className="field">
            <dt>Last delivery received</dt>
            <dd>{state.connection.lastMessageAt ?? UNAVAILABLE}</dd>
            <div className="faint">HMI receipt time, not a datum's age</div>
          </div>
        </dl>

        <div className="row-between">
          <span className="faint">Newest supplied dispatch command</span>
          <FreshnessIndicator view={fresh(newestCommand)} />
        </div>
        <div className="row-between">
          <span className="faint">Newest supplied slot window start</span>
          <FreshnessIndicator view={fresh(newestSlot)} />
        </div>
      </Panel>
    </>
  );
}
