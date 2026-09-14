/**
 * Vehicle HMI panels.
 *
 * ==========================================================================
 *  EVERY VALUE ON THIS SCREEN IS SUPPLIED. NOTHING HERE IS COMPUTED.
 *
 *  No speed is derived, no safe speed is calculated, no position is estimated, no link
 *  state is assumed. Each panel selects already-stamped values out of the projection and
 *  labels them with the provenance and freshness the Twin gave them. A value the Twin did
 *  not supply renders as UNAVAILABLE - never as 0, never as a reassuring default.
 * ==========================================================================
 *
 * These are the panels of ONE shared vehicle console. `truck01.tsx` and `truck02.tsx`
 * render the same components against different projections; there is no per-truck copy of
 * any of this.
 */

import { useMemo, useState } from "react";

import { submitCommand } from "../api/commandClient";
import type { OperatorContext } from "../api/operatorClient";
import { EmptyState, Panel } from "../components/primitives";
import { GeoSiteMap } from "../screens/GeoSiteMap";
import {
  DATA_STATE_TEXT,
  fieldDataState,
  UNAVAILABLE_LABEL,
  UNAVAILABLE_VALUE,
  vehicleProvenanceLabel,
} from "../state/dataStatus";
import {
  buildCommandPayload,
  DISPATCH_ACTIONS,
  type DispatchAction,
  nextCommandId,
  outcomeDetail,
  outcomeLabel,
  requiresConfirmation,
  requiresTargetSpeed,
} from "../state/dispatchCommand";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { type HardwareReadout, hardwareReadouts } from "../state/hardwareTelemetry";
import { ACTION_DETAIL, ACTION_LABEL, deriveOperatorReadout, toKmh } from "../state/operatorAction";
import {
  providerForMode,
  resolveVehiclePosition,
  type SystemMode,
} from "../state/vehiclePosition";
import { communicationLinks, LINK_STATE_GLYPH, type LinkStatus } from "./communication";
import type { VehicleHmiConfig } from "./vehicleConfig";
import type { VehicleProjection } from "./vehicleProjection";

// ---------------------------------------------------------------------------
// shared bits
// ---------------------------------------------------------------------------

/** One supplied value with its provenance and freshness. Absence is rendered, not hidden. */
export function ReadoutRow({ row }: { row: HardwareReadout }) {
  return (
    <tr className={row.available ? undefined : "dim"}>
      <td>{row.label}</td>
      <td>
        {row.value}
        {row.available && row.unit ? <span className="metric-unit"> {row.unit}</span> : null}
      </td>
      <td>{row.provenance}</td>
      <td>{row.freshness}</td>
      <td className="faint">{row.reason ?? ""}</td>
    </tr>
  );
}

function speedText(mps: number | null): string {
  const kmh = toKmh(mps);
  return kmh === null ? UNAVAILABLE_LABEL : kmh.toFixed(1);
}

// ---------------------------------------------------------------------------
// COMMUNICATION
// ---------------------------------------------------------------------------

function LinkBlock({ link }: { link: LinkStatus }) {
  return (
    <div className="veh-link" data-link={link.label} data-state={link.state}>
      <div className="veh-link-head">
        <span className="veh-link-name">
          {link.label} · {link.bearer}
        </span>
        <span className="veh-link-state">
          <span aria-hidden="true">{LINK_STATE_GLYPH[link.state]}</span> {link.state}
        </span>
      </div>
      {link.peerId ? <div className="veh-link-peer">PEER: {link.peerId}</div> : null}
      <div className="veh-link-reason faint">{link.reason}</div>
      {link.metrics.length > 0 ? (
        <table className="data-table">
          <tbody>
            {link.metrics.map((metric) => (
              <tr key={metric.label} className={metric.available ? undefined : "dim"}>
                <td>{metric.label}</td>
                <td>
                  {metric.value}
                  {metric.available && metric.unit ? (
                    <span className="metric-unit"> {metric.unit}</span>
                  ) : null}
                </td>
                <td className="faint">
                  {metric.available ? metric.freshness : (metric.reason ?? "")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

/**
 * V2V, V2I and the backend link, computed independently.
 *
 * A browser socket that is up is not evidence that two trucks can hear each other, so the
 * three states are never merged into one "communication OK".
 */
export function CommunicationPanel({
  projection,
  mode,
}: {
  projection: VehicleProjection;
  mode: string;
}) {
  const links = communicationLinks(projection.vehicle, projection.connection.status, mode);
  return (
    <Panel title="Communication">
      <div className="veh-links">
        {links.map((link) => (
          <LinkBlock key={link.label} link={link} />
        ))}
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// TELEMETRY
// ---------------------------------------------------------------------------

/**
 * The physical fields this vehicle actually reports.
 *
 * PWM-derived speed carries its own label and its own warning; it is never shown under an
 * encoder heading. A vehicle whose firmware does not transmit encoder-derived speed says
 * so explicitly rather than leaving an empty row that reads as a sensor fault.
 */
export function TelemetryPanel({
  projection,
  config,
}: {
  projection: VehicleProjection;
  config: VehicleHmiConfig;
}) {
  const rows = hardwareReadouts(projection.vehicle);

  return (
    <Panel title={`Telemetry · ${projection.vehicleId}`}>
      {!projection.present ? (
        <EmptyState
          headline="NO TELEMETRY SUPPLIED"
          detail="The Digital Twin carries no state for this vehicle. Nothing is assumed about it."
        />
      ) : (
        <>
          {!config.transmitsEncoderDerivedSpeed ? (
            <p className="veh-note">
              This vehicle's firmware does not transmit encoder-derived speed. Any speed shown is
              PWM-derived — a commanded prototype velocity, not a measurement.
            </p>
          ) : null}
          <table className="data-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
                <th>Source</th>
                <th>Freshness</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <ReadoutRow key={row.label} row={row} />
              ))}
            </tbody>
          </table>
        </>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// POSITION
// ---------------------------------------------------------------------------

/**
 * Where the vehicle is, and how that was established.
 *
 * The METHOD is shown next to the position at all times, because "we measured it" and
 * "we made it up for a demo" must never look the same. With no GNSS fitted and no
 * odometry implemented, LIVE mode reports UNAVAILABLE and the console stays usable.
 */
export function PositionPanel({
  projection,
  config,
  mode,
}: {
  projection: VehicleProjection;
  config: VehicleHmiConfig;
  mode: SystemMode;
}) {
  const site = bailadilaDeposit5();
  const extent = toDecimalExtent(site.extent);
  const provider = providerForMode(mode, extent);
  // Same resolver the map uses, so this panel can never contradict the marker beside it.
  const position = projection.vehicle
    ? resolveVehiclePosition(projection.vehicle, provider, extent)
    : null;

  const heading = projection.vehicle?.provenance?.heading_rad;
  const headingState = fieldDataState(heading);
  const located = Boolean(position?.position);

  const odom = projection.vehicle?.positionOdom;
  const odomValid = Boolean(
    odom && odom.status === "VALID" && typeof odom.xM === "number" && typeof odom.yM === "number",
  );

  return (
    <Panel title="Position">
      <table className="data-table">
        <tbody>
          <tr>
            <td>Status</td>
            <td>{located ? "SUPPLIED" : "POSITION UNAVAILABLE"}</td>
          </tr>
          <tr>
            <td>Source</td>
            <td>{position?.provenance ?? UNAVAILABLE_LABEL}</td>
          </tr>
          {/* Method is what was RUN, not what could be run. No estimator, no method. */}
          <tr>
            <td>Method</td>
            <td>{located ? (position?.provenance ?? UNAVAILABLE_LABEL) : UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Longitude</td>
            <td>{position?.position ? position.position.lon.toFixed(6) : UNAVAILABLE_VALUE}</td>
          </tr>
          <tr>
            <td>Latitude</td>
            <td>{position?.position ? position.position.lat.toFixed(6) : UNAVAILABLE_VALUE}</td>
          </tr>
          <tr className={headingState === "UNAVAILABLE" ? "dim" : undefined}>
            <td>Heading</td>
            <td>
              {typeof heading?.value === "number" && Number.isFinite(heading.value)
                ? `${heading.value.toFixed(3)} rad`
                : UNAVAILABLE_VALUE}
            </td>
          </tr>
          <tr>
            <td>Freshness</td>
            <td>{DATA_STATE_TEXT[headingState]}</td>
          </tr>
        </tbody>
      </table>

      <h4>Local Wheel + IMU Odometry</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Origin Frame</td>
            <td>{odom?.originType ?? "LOCAL ODOMETRY ORIGIN"}</td>
          </tr>
          <tr>
            <td>Odometry Status</td>
            <td>{odomValid ? "VALID" : (odom?.status ?? "POSITION ODOMETRY: UNAVAILABLE")}</td>
          </tr>
          <tr>
            <td>Local X (m)</td>
            <td>
              {odomValid && typeof odom?.xM === "number" ? odom.xM.toFixed(3) : UNAVAILABLE_VALUE}
            </td>
          </tr>
          <tr>
            <td>Local Y (m)</td>
            <td>
              {odomValid && typeof odom?.yM === "number" ? odom.yM.toFixed(3) : UNAVAILABLE_VALUE}
            </td>
          </tr>
          <tr>
            <td>Local Heading (rad)</td>
            <td>
              {odomValid && typeof odom?.headingRad === "number"
                ? odom.headingRad.toFixed(3)
                : UNAVAILABLE_VALUE}
            </td>
          </tr>
          <tr>
            <td>Distance Travelled (m)</td>
            <td>
              {odomValid && typeof odom?.distanceM === "number"
                ? odom.distanceM.toFixed(3)
                : UNAVAILABLE_VALUE}
            </td>
          </tr>
          <tr>
            <td>Provenance</td>
            <td>{odom?.provenanceLabel ?? "UNAVAILABLE"}</td>
          </tr>
          <tr>
            <td>Method</td>
            <td>{odom?.method ?? "NONE"}</td>
          </tr>
          <tr>
            <td>Verification</td>
            <td>{odom?.verificationLabel ?? "CONTRACT VERIFIED"}</td>
          </tr>
        </tbody>
      </table>

      <p className="veh-note faint">{position?.reason ?? config.positionLimitation}</p>
      <p className="veh-note faint">
        Supportable methods for this vehicle: {config.supportedPositionMethods.join(", ")}. Listed
        as supportable, not as available.
      </p>
    </Panel>
  );
}

/** The site map, with this vehicle's marker when — and only when — a position exists. */
export function VehicleMapPanel({
  projection,
  mode,
}: {
  projection: VehicleProjection;
  mode: SystemMode;
}) {
  const site = bailadilaDeposit5();
  const extent = toDecimalExtent(site.extent);
  const provider = providerForMode(mode, extent);
  // The fleet as the Twin carries it - this vehicle first, ringed as THIS VEHICLE, then
  // the peer. Each marker keeps its own provenance; nothing is placed without a position.
  // MAP-02: `resolveVehiclePosition` falls back to the Twin's explicitly simulated scene
  // pose when the mode provider has none, so both trucks appear on both consoles.
  const fleet = [projection.vehicle, projection.peer].filter(
    (vehicle): vehicle is NonNullable<typeof vehicle> => vehicle !== null,
  );
  const positions = fleet.map((vehicle) => resolveVehiclePosition(vehicle, provider, extent));
  return (
    <Panel title={`Mine map — fleet (${projection.vehicleId})`}>
      <GeoSiteMap
        site={site}
        positions={positions}
        mode={mode}
        ownVehicleId={projection.vehicleId}
      />
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// SAFETY
// ---------------------------------------------------------------------------

/**
 * Actual vs safe vs commanded — three numbers that are never merged.
 *
 * `deriveOperatorReadout` names the instruction by comparing two SUPPLIED values. No
 * physics is recomputed here, and no v_safe is invented: with none supplied the panel
 * says SAFETY DATA UNAVAILABLE rather than NORMAL.
 */
export function SafetyPanel({ projection }: { projection: VehicleProjection }) {
  const readout = useMemo(
    () => deriveOperatorReadout(projection.safety, projection.vehicle),
    [projection.safety, projection.vehicle],
  );
  const visibility = projection.road?.visibility?.value ?? null;

  return (
    <Panel title="Safety">
      <div
        className={`veh-action veh-action-${readout.action.toLowerCase()}`}
        role="status"
        aria-live="polite"
        data-action={readout.action}
      >
        <span className="veh-action-label">{ACTION_LABEL[readout.action]}</span>
        <span className="veh-action-detail">{ACTION_DETAIL[readout.action]}</span>
      </div>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Actual speed</td>
            <td>{speedText(readout.actualSpeedMps)} km/h</td>
          </tr>
          <tr>
            <td>Safe speed</td>
            <td>{speedText(readout.safeSpeedMps)} km/h</td>
          </tr>
          <tr>
            <td>Commanded speed</td>
            <td>{speedText(projection.dispatch?.targetSpeed ?? null)} km/h</td>
          </tr>
          <tr>
            <td>Active constraint</td>
            <td>{readout.reason ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Risk</td>
            <td>{projection.safety?.riskLevel ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Visibility</td>
            <td>{visibility === null ? UNAVAILABLE_LABEL : `${visibility.toFixed(0)} m`}</td>
          </tr>
        </tbody>
      </table>
      <p className="veh-note faint">
        Supplied by the safety subsystem through the Digital Twin. Never calculated in this console.
      </p>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// COMMANDS
// ---------------------------------------------------------------------------

/**
 * The operator's command form, permanently addressed to THIS vehicle.
 *
 * The vehicle id comes from the build-time config and is not an input. That is a
 * convenience: the backend still authenticates the operator and checks the assignment
 * before the command gateway is reached, so a tampered id changes nothing.
 */
export function CommandPanel({
  projection,
  config,
  operator,
}: {
  projection: VehicleProjection;
  config: VehicleHmiConfig;
  operator: OperatorContext | null;
}) {
  const [action, setAction] = useState<DispatchAction>("TARGET_SPEED");
  const [speedRaw, setSpeedRaw] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ outcome: string; message: string } | null>(null);

  const send = async () => {
    const built = buildCommandPayload(
      {
        vehicleId: config.vehicleId,
        action,
        targetSpeedRaw: speedRaw,
        reason: `VEHICLE_HMI_${config.vehicleId}`,
      },
      nextCommandId(config.vehicleId, action),
    );

    if (!built.ok) {
      setResult({ outcome: "INVALID", message: built.error });
      return;
    }

    setBusy(true);
    // The token travels in the Authorization header, added by `api/commandClient`.
    const response = await submitCommand(built.payload);
    setBusy(false);
    setConfirming(false);
    setResult({ outcome: response.outcome, message: response.message });
  };

  const onSubmit = () => {
    if (requiresConfirmation(action) && !confirming) {
      setConfirming(true);
      return;
    }
    void send();
  };

  return (
    <Panel title={`Commands · ${config.vehicleId}`}>
      {operator === null ? (
        <p className="veh-note">
          NO AUTHENTICATED OPERATOR. Commands will be refused by the backend until a session is
          opened.
        </p>
      ) : null}

      <div className="veh-command-form">
        <label>
          <span>ACTION</span>
          <select
            value={action}
            aria-label="Command action"
            onChange={(event) => {
              setAction(event.target.value as DispatchAction);
              setConfirming(false);
            }}
          >
            {DISPATCH_ACTIONS.map((candidate) => (
              <option key={candidate} value={candidate}>
                {candidate}
              </option>
            ))}
          </select>
        </label>

        {requiresTargetSpeed(action) ? (
          <label>
            <span>TARGET SPEED (m/s)</span>
            <input
              value={speedRaw}
              aria-label="Target speed"
              onChange={(event) => setSpeedRaw(event.target.value)}
            />
          </label>
        ) : null}

        <button type="button" onClick={onSubmit} disabled={busy}>
          {busy ? "SENDING…" : confirming ? `CONFIRM ${action}` : `SEND ${action}`}
        </button>
      </div>

      {result ? (
        <div className="veh-command-result" data-outcome={result.outcome}>
          <strong>{outcomeLabel(result.outcome)}</strong>
          <div className="faint">{outcomeDetail(result.outcome)}</div>
          <div>{result.message}</div>
        </div>
      ) : null}

      <h4>Session commands</h4>
      {projection.commands.length === 0 ? (
        <EmptyState headline="NO COMMANDS THIS SESSION" />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Command</th>
              <th>Action</th>
              <th>Outcome</th>
              <th>Acknowledged</th>
            </tr>
          </thead>
          <tbody>
            {projection.commands.map((command) => (
              <tr key={command.commandId}>
                <td>{command.commandId}</td>
                <td>{command.action}</td>
                <td>{command.outcome}</td>
                {/* Null acknowledgement means NOT acknowledged. Never "assume executed". */}
                <td>{command.executionAckIso ?? UNAVAILABLE_VALUE}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// ALERTS AND EVENTS
// ---------------------------------------------------------------------------

/**
 * This vehicle's alerts and events, from the shared alert and event systems.
 *
 * Acknowledgement means the operator SAW it. It does not mean the condition cleared, so
 * an acknowledged alert stays listed while it is active.
 */
export function AlertsEventsPanel({ projection }: { projection: VehicleProjection }) {
  return (
    <Panel title="Alerts and events">
      <h4>Alerts</h4>
      {projection.alerts.length === 0 ? (
        <EmptyState headline="NO ALERTS FOR THIS VEHICLE" />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Category</th>
              <th>Message</th>
              <th>Acknowledged</th>
            </tr>
          </thead>
          <tbody>
            {projection.alerts.map((alert) => (
              <tr key={alert.alertId}>
                <td>{alert.severity}</td>
                <td>{alert.category}</td>
                <td>{alert.message}</td>
                <td>{alert.acknowledged ? "SEEN" : UNAVAILABLE_VALUE}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Events</h4>
      {projection.events.length === 0 ? (
        <EmptyState headline="NO EVENTS FOR THIS VEHICLE" />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Category</th>
              <th>Actor</th>
            </tr>
          </thead>
          <tbody>
            {projection.events.slice(0, 20).map((event) => (
              <tr key={event.eventId}>
                <td>{event.timestamp}</td>
                <td>{event.category}</td>
                <td>{event.actor ?? UNAVAILABLE_VALUE}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// OPERATOR
// ---------------------------------------------------------------------------

/**
 * Who the BACKEND says is signed in, and what it has them assigned to.
 *
 * Every field here was read back from `GET /api/operator/context`. None of it is chosen by
 * this application. When the server's assignment disagrees with the vehicle this console
 * is built for, that disagreement is displayed rather than hidden - the operator is
 * looking at a console they are not authorized to command, and should be told before they
 * try.
 */
export function OperatorBadge({
  operator,
  config,
  problem,
}: {
  operator: OperatorContext | null;
  config: VehicleHmiConfig;
  problem: string | null;
}) {
  if (!operator) {
    return (
      <span className="veh-operator veh-operator-none">
        {problem ?? "NO AUTHENTICATED OPERATOR"}
      </span>
    );
  }

  const mismatch =
    operator.assignedVehicleId !== null && operator.assignedVehicleId !== config.vehicleId;

  return (
    <span className="veh-operator">
      <strong>{operator.operator.operatorId}</strong> {operator.operator.name} ·{" "}
      {operator.operator.role}
      {operator.operator.provenance === "DEMO" ? <em> · DEMO</em> : null}
      {operator.shiftId ? <> · {operator.shiftId}</> : null}
      {mismatch ? (
        <strong className="veh-operator-mismatch">
          {" "}
          · ASSIGNED TO {operator.assignedVehicleId}, NOT {config.vehicleId}
        </strong>
      ) : null}
    </span>
  );
}

/** Provenance of the vehicle's own data, for the header. */
export function dataSourceLabel(projection: VehicleProjection): string {
  return vehicleProvenanceLabel(projection.vehicle);
}
