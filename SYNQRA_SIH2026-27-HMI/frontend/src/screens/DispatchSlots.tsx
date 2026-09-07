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
import { submitCommand } from "../api/commandClient";
import {
  EmptyState,
  FreshnessIndicator,
  MetricCard,
  Panel,
  StatusBadge,
} from "../components/primitives";
import type { DispatchCommand, SlotState } from "../contracts/domain";
import {
  DATA_STATE_TEXT,
  UNAVAILABLE_LABEL,
  UNAVAILABLE_VALUE,
  communicationText,
  fieldDataState,
  isStale,
  vehicleProvenanceLabel,
} from "../state/dataStatus";
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
import {
  buildCommandPayload,
  DEFAULT_REASON,
  DISPATCH_ACTIONS,
  type DispatchAction,
  nextCommandId,
  outcomeDetail,
  outcomeLabel,
  requiresConfirmation,
  requiresTargetSpeed,
  validateTargetSpeed,
} from "../state/dispatchCommand";
import { viewFreshness } from "../state/freshness";
import { useHmi } from "../state/ProviderHost";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { dispatchStateToken, providerStatusToken, slotStatusToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

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
            <td className="mono">{slot.vehicleId ?? UNAVAILABLE_LABEL}</td>
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

/**
 * S4 command panel — the operator's dispatch interface.
 *
 * WHAT THIS COMPONENT DOES NOT DO
 *   It computes no safe speed, holds no vehicle state, and decides nothing about safety.
 *   It collects operator input, hands it to `api/commandClient` (the single command path
 *   to POST /api/commands -> CommandGateway), and renders the answer that comes back.
 *
 *   Validation, payload construction and result classification live in
 *   `state/dispatchCommand.ts` so they are testable without a DOM (M4D-C).
 */
function DispatchCommandPanel() {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  const vehicleIds = Object.keys(state.vehicles).sort();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeId = selectedId ?? vehicleIds[0] ?? null;
  const vehicle = activeId ? state.vehicles[activeId] : undefined;
  const safety = activeId ? state.safety[activeId] : undefined;

  const [action, setAction] = useState<DispatchAction>("TARGET_SPEED");
  const [targetSpeedRaw, setTargetSpeedRaw] = useState("");
  const [reason, setReason] = useState("");
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  /**
   * Phase 3 — command history is SHARED STATE, read from the same AppStateStore the
   * WebSocket writes into. The panel keeps no private copy, so an HTTP response and a
   * `command_issued` frame converge on one record.
   */
  const { store } = useHmi();
  const history = state.commands;
  const latest = history[0] ?? null;
  const speedValidation = requiresTargetSpeed(action) ? validateTargetSpeed(targetSpeedRaw) : null;

  /**
   * Provenance and freshness of the selected vehicle's speed — Phase 8.
   *
   * SIMULATION and PHYSICAL must never look alike (project rule 17), and they must not
   * look DIFFERENT from how the same field reads on S1, S2, S3 and S6 either. This screen
   * previously had its own labeller that omitted the DERIVED case, so a hardware-derived
   * speed read "PHYSICAL" here and "PHYSICAL (derived)" on S3.
   */
  const speedProv = vehicle?.provenance?.speed_mps;
  const provenanceText = vehicleProvenanceLabel(vehicle);
  const telemetryState = fieldDataState(speedProv);

  async function send(payloadAction: DispatchAction) {
    setFormError(null);
    const commandId = nextCommandId(activeId ?? "NO_VEHICLE", payloadAction);
    const built = buildCommandPayload(
      { vehicleId: activeId, action: payloadAction, targetSpeedRaw, reason },
      commandId,
    );
    if (!built.ok) {
      setFormError(built.error);
      return;
    }

    const submittedAtIso = new Date(nowMs).toISOString();

    // The record itself is created by the shared merge, so the panel keeps no copy.
    store.recordCommandEvent({
      commandId,
      origin: "HTTP",
      observedAtIso: submittedAtIso,
      vehicleId: built.payload.vehicle_id,
      action: payloadAction,
      targetSpeedMps: requiresTargetSpeed(payloadAction) ? built.payload.target_speed : null,
      reason: built.payload.reason,
      outcome: "PENDING",
    });
    setBusy(true);

    const result = await submitCommand(built.payload);

    // Correlated by command_id, so one command is one row - never two.
    store.recordCommandEvent({
      commandId,
      origin: "HTTP",
      observedAtIso: new Date().toISOString(),
      outcome: result.outcome,
      message: result.message,
    });
    setBusy(false);
    setAwaitingConfirm(false);
  }

  function onSubmit() {
    if (busy) return; // guards double-click / double submission
    if (requiresConfirmation(action)) {
      setAwaitingConfirm(true);
      return;
    }
    void send(action);
  }

  return (
    <Panel title="Dispatch command" note="POST /api/commands · validated by the Command Gateway">
      {vehicleIds.length === 0 ? (
        <EmptyState
          headline="NO VEHICLE SUPPLIED"
          detail="The data layer has supplied no vehicle state, so no vehicle can be commanded."
        />
      ) : (
        <>
          {/* -- vehicle selection + summary ------------------------------- */}
          <div className="field">
            <label htmlFor="dispatch-vehicle">Vehicle</label>
            <select
              id="dispatch-vehicle"
              value={activeId ?? ""}
              disabled={busy}
              onChange={(event) => {
                setSelectedId(event.target.value);
                setAwaitingConfirm(false);
              }}
            >
              {vehicleIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>

          {/*
            PHASE 8 §18 — the operator must be able to see that the state they are acting
            on is behind reality. This WARNS; it never rejects. The CommandGateway remains
            the sole authority on acceptance, and no command is blocked or pre-failed here.
          */}
          {isStale(telemetryState) ? (
            <p className="warn" role="status">
              ▲ TELEMETRY STALE — the vehicle state shown below is the last supplied value
              and is no longer updating. Commands are still submitted normally; the
              CommandGateway decides acceptance.
            </p>
          ) : null}

          <dl className="fields">
            <div className="field">
              <dt>Selected vehicle</dt>
              <dd>{activeId ?? UNAVAILABLE_VALUE}</dd>
            </div>
            <div className="field">
              <dt>Telemetry state</dt>
              <dd>{DATA_STATE_TEXT[telemetryState]}</dd>
            </div>
            <div className="field">
              <dt>Current speed</dt>
              <dd>
                {vehicle?.speedMps === null || vehicle?.speedMps === undefined
                  ? "--"
                  : `${(vehicle.speedMps * 3.6).toFixed(1)} km/h`}
              </dd>
            </div>
            <div className="field">
              <dt>Safe speed</dt>
              {/* ONLY when the authoritative state supplies it. Never computed here. */}
              <dd>
                {safety?.vSafe === null || safety?.vSafe === undefined
                  ? "--"
                  : `${(safety.vSafe * 3.6).toFixed(1)} km/h`}
              </dd>
            </div>
            <div className="field">
              <dt>Communication</dt>
              <dd>
                {/* SUPPLIED link state. Independent of telemetry freshness (Phase 8 §15). */}
                {communicationText(vehicle)}
              </dd>
            </div>
            <div className="field">
              <dt>Telemetry source</dt>
              <dd>{provenanceText}</dd>
            </div>
            <div className="field">
              <dt>Freshness</dt>
              <dd>
                <FreshnessIndicator view={viewFreshness(vehicle?.timestamp, config, nowMs)} />
              </dd>
            </div>
          </dl>

          {/* -- command form ---------------------------------------------- */}
          <div className="field">
            <label htmlFor="dispatch-action">Action</label>
            <select
              id="dispatch-action"
              value={action}
              disabled={busy}
              onChange={(event) => {
                setAction(event.target.value as DispatchAction);
                setAwaitingConfirm(false);
                setFormError(null);
              }}
            >
              {DISPATCH_ACTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          {requiresTargetSpeed(action) ? (
            <div className="field">
              <label htmlFor="dispatch-target-speed">Target speed (m/s)</label>
              <input
                id="dispatch-target-speed"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.1"
                value={targetSpeedRaw}
                disabled={busy}
                aria-invalid={speedValidation !== null && !speedValidation.ok}
                onChange={(event) => setTargetSpeedRaw(event.target.value)}
              />
              {/* The wire unit is m/s. km/h is shown only as a read-back, never sent. */}
              <div className="faint">
                {speedValidation?.ok && speedValidation.value !== null
                  ? `= ${(speedValidation.value * 3.6).toFixed(1)} km/h · sent as m/s`
                  : "Sent to the gateway in m/s, exactly as typed."}
              </div>
              {speedValidation && !speedValidation.ok && targetSpeedRaw !== "" ? (
                <div className="faint" role="alert">
                  {speedValidation.error}
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="field">
            <label htmlFor="dispatch-reason">Reason</label>
            <input
              id="dispatch-reason"
              type="text"
              value={reason}
              disabled={busy}
              placeholder={DEFAULT_REASON}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="faint">Optional. Defaults to {DEFAULT_REASON}.</div>
          </div>

          {formError ? (
            <p className="empty" role="alert">
              <strong>{formError}</strong>
            </p>
          ) : null}

          {/* -- submit / confirm ------------------------------------------ */}
          {awaitingConfirm ? (
            <div className="hmi-banner" role="alertdialog" aria-label="Confirm stop">
              <div className="hmi-banner-title">Stop {activeId}?</div>
              <p>This sends a STOP command through the Command Gateway.</p>
              <button type="button" disabled={busy} onClick={() => setAwaitingConfirm(false)}>
                CANCEL
              </button>
              <button
                type="button"
                className="destructive"
                disabled={busy}
                onClick={() => void send("STOP")}
              >
                CONFIRM STOP
              </button>
            </div>
          ) : (
            <button
              type="button"
              className={action === "STOP" ? "destructive" : undefined}
              disabled={busy || activeId === null}
              onClick={onSubmit}
            >
              {busy ? "SUBMITTING…" : `SEND ${action.replace("_", " ")}`}
            </button>
          )}

          {/* -- latest result --------------------------------------------- */}
          {latest ? (
            <dl className="fields" role="status">
              <div className="field">
                <dt>Result</dt>
                <dd>{outcomeLabel(latest.outcome)}</dd>
                <div className="faint">{outcomeDetail(latest.outcome)}</div>
                {latest.message ? <div className="faint">Backend: {latest.message}</div> : null}
              </div>
            </dl>
          ) : null}

          {/* -- session history ------------------------------------------- */}
          <table className="hmi-table">
            <caption>Session command history</caption>
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Command ID</th>
                <th scope="col">Vehicle</th>
                <th scope="col">Action</th>
                <th scope="col">Target (m/s)</th>
                <th scope="col">Result</th>
                <th scope="col">Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={7}>NO COMMANDS THIS SESSION</td>
                </tr>
              ) : (
                history.map((row) => (
                  <tr key={row.commandId}>
                    <td>{clockTime(row.submittedAtIso)}</td>
                    <td className="mono">{row.commandId}</td>
                    <td>{row.vehicleId}</td>
                    <td>{row.action.replace("_", " ")}</td>
                    <td>{row.targetSpeedMps === null ? "--" : row.targetSpeedMps.toFixed(2)}</td>
                    <td>{outcomeLabel(row.outcome)}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </>
      )}
    </Panel>
  );
}

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
      {/* 0 — COMMAND. S4's primary purpose: the operator's only command path. */}
      <DispatchCommandPanel />

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
            <dd>{state.connection.scenarioName ?? UNAVAILABLE_VALUE}</dd>
          </div>
          <div className="field">
            <dt>Last delivery received</dt>
            <dd>{state.connection.lastMessageAt ?? UNAVAILABLE_VALUE}</dd>
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
