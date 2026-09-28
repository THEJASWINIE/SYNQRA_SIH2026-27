/**
 * Operator HMI — P8 (root CLAUDE.md §12).
 *
 * PURPOSE
 *   Answers one question for the dumper operator: what should I do RIGHT NOW?
 *   This is deliberately NOT the control-room dashboard. Low density, large numerals,
 *   one dominant instruction.
 *
 * DATA SOURCES — all canonical, none computed here
 *   actual speed   supplied SafetyState.actualSpeed / VehicleState.speedMps
 *   safe speed     supplied SafetyState.vSafe            <- fog_safe, via the Twin
 *   commanded      supplied DispatchCommand.targetSpeed  <- command gateway
 *   visibility     supplied RoadState.visibility (Estimate)
 *   reason         supplied SafetyState.activeConstraint
 *
 * UNAVAILABLE SEMANTICS (P7.1)
 *   A missing value renders as UNAVAILABLE. It never becomes 0, and never becomes a
 *   reassuring state. No v_safe => SAFETY DATA UNAVAILABLE, never NORMAL.
 *
 * ACTION SEMANTICS
 *   `state/operatorAction.ts` names the instruction by comparing two SUPPLIED numbers.
 *   No physics is recomputed here.
 *
 * COMMAND SEMANTICS
 *   A command being ACCEPTED is not evidence the truck reached that speed. Commanded
 *   speed is shown in its own field, separate from actual speed, and never merged.
 */

import { useMemo, useState } from "react";

import type { VehicleId } from "../contracts/primitives";
import {
  communicationText,
  DATA_STATE_TEXT,
  fieldDataState,
  vehicleProvenanceLabel,
} from "../state/dataStatus";
import {
  ACTION_DETAIL,
  ACTION_LABEL,
  deriveOperatorReadout,
  type OperatorAction,
  toKmh,
} from "../state/operatorAction";
import { useAppState } from "../state/useAppState";

const UNAVAILABLE = "UNAVAILABLE";

/** Non-colour cue, so state is never communicated by colour alone (accessibility). */
const ACTION_GLYPH: Record<OperatorAction, string> = {
  NORMAL: "OK",
  CAUTION: "!",
  SLOW_DOWN: "▼",
  STOP: "■",
  SAFETY_DATA_UNAVAILABLE: "?",
};

function speedText(mps: number | null): string {
  const kmh = toKmh(mps);
  return kmh === null ? UNAVAILABLE : kmh.toFixed(1);
}

function Readout({
  label,
  value,
  unit,
  note,
}: {
  label: string;
  value: string;
  unit?: string;
  note?: string | null;
}) {
  const unavailable = value === UNAVAILABLE;
  return (
    <div className="op-readout">
      <div className="op-readout-label">{label}</div>
      <div className={unavailable ? "op-readout-value dim" : "op-readout-value"}>
        {value}
        {!unavailable && unit ? <span className="op-readout-unit"> {unit}</span> : null}
      </div>
      {note ? <div className="op-readout-note">{note}</div> : null}
    </div>
  );
}

export function OperatorView({ vehicleId }: { vehicleId?: VehicleId | null }) {
  const state = useAppState();
  const [picked, setPicked] = useState<VehicleId | null>(null);

  const vehicleIds = useMemo(
    () =>
      Array.from(
        new Set([...Object.keys(state.vehicles ?? {}), ...Object.keys(state.safety ?? {})]),
      ).sort(),
    [state.vehicles, state.safety],
  );

  const activeId = picked ?? vehicleId ?? vehicleIds[0] ?? null;
  const vehicle = activeId ? (state.vehicles?.[activeId] ?? null) : null;
  const safety = activeId ? (state.safety?.[activeId] ?? null) : null;

  const readout = useMemo(() => deriveOperatorReadout(safety, vehicle), [safety, vehicle]);

  // Commanded speed is SUPPLIED by the command gateway. It is never inferred from the
  // action state, and never conflated with the speed the truck is actually doing.
  const command = useMemo(
    () =>
      activeId
        ? Object.values(state.dispatch ?? {}).find((c) => c?.vehicleId === activeId)
        : undefined,
    [state.dispatch, activeId],
  );
  const commandStatus = command?.state ?? null;

  // Visibility for the vehicle's supplied road, when one is supplied.
  const roadId = vehicle?.position?.segmentId ?? vehicle?.routeId ?? null;
  const road = roadId ? (state.road?.[roadId] ?? null) : null;
  const visibility = road?.visibility?.value ?? null;

  /**
   * Provenance, freshness and communication are THREE SEPARATE FACTS (Phase 8).
   *
   * All three now come from the shared `dataStatus` helpers, so this screen cannot drift
   * from S1-S7. It previously had its own provenance wording ("DERIVED · HARDWARE") that
   * disagreed with every other screen about the same field.
   */
  const speedProvenance = vehicle?.provenance?.speed_mps;
  const dataSource = vehicleProvenanceLabel(vehicle);
  const freshness = DATA_STATE_TEXT[fieldDataState(speedProvenance)];

  if (!activeId) {
    return (
      <section className="op-root" aria-label="Operator view">
        <h2 className="op-empty-title">NO VEHICLE SUPPLIED</h2>
        <p className="op-empty-note">
          The data layer has supplied no vehicle state. Nothing is assumed about safety.
        </p>
      </section>
    );
  }

  return (
    <section className="op-root" aria-label="Operator view">
      <header className="op-header">
        <div className="op-vehicle" aria-label="Vehicle">
          {activeId}
        </div>
        {vehicleIds.length > 1 ? (
          <label className="op-picker">
            <span className="op-picker-label">VEHICLE</span>
            <select
              value={activeId}
              onChange={(event) => setPicked(event.target.value as VehicleId)}
              aria-label="Select vehicle"
            >
              {vehicleIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </header>

      {/* MOST IMPORTANT: what to do now. */}
      <div
        className={`op-action op-action-${readout.action.toLowerCase()}`}
        role="status"
        aria-live="polite"
        data-action={readout.action}
      >
        <span className="op-action-glyph" aria-hidden="true">
          {ACTION_GLYPH[readout.action]}
        </span>
        <span className="op-action-label">{ACTION_LABEL[readout.action]}</span>
        <span className="op-action-detail">{ACTION_DETAIL[readout.action]}</span>
      </div>

      {/* SECOND: actual vs safe, never merged. */}
      <div className="op-speeds">
        <Readout label="ACTUAL SPEED" value={speedText(readout.actualSpeedMps)} unit="km/h" />
        <Readout
          label="SAFE SPEED"
          value={speedText(readout.safeSpeedMps)}
          unit="km/h"
          note="supplied — never calculated here"
        />
        <Readout
          label="COMMANDED SPEED"
          value={speedText(command?.targetSpeed ?? null)}
          unit="km/h"
          note={commandStatus ? `command ${commandStatus}` : "no command supplied"}
        />
      </div>

      {/* THIRD: visibility and reason. */}
      <div className="op-conditions">
        <Readout
          label="VISIBILITY"
          value={visibility === null ? UNAVAILABLE : visibility.toFixed(0)}
          unit="m"
        />
        <Readout label="REASON" value={readout.reason ?? UNAVAILABLE} />
      </div>

      {/* FOURTH: trust / system status. Compact, not the operator's main concern. */}
      <footer className="op-status">
        {/*
          COMMUNICATION is the SUPPLIED link state, not the presence of a vehicle object.
          It previously read CONNECTED whenever a vehicle existed at all, which reported a
          healthy link while the Twin was supplying COMMUNICATION_DEGRADED.
        */}
        <span>
          COMMUNICATION: <strong>{communicationText(vehicle)}</strong>
        </span>
        <span>
          DATA: <strong>{dataSource}</strong>
        </span>
        <span>
          FRESHNESS: <strong>{freshness}</strong>
        </span>
        <span>
          COMMAND: <strong>{commandStatus ?? "NONE"}</strong>
        </span>
      </footer>
    </section>
  );
}
