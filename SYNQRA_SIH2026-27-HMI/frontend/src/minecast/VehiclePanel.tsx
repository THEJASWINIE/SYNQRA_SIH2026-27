/**
 * Selected-vehicle panel — right side of the Mine-Cast shell.
 *
 * ==========================================================================
 *  READ-ONLY. THERE IS NO COMMAND PATH THROUGH THIS FILE.
 *
 *  Mine-Cast is a viewer. It deliberately does not import `submitCommand`, does not
 *  render a command control, and offers no way to reach the command gateway. Commanding a
 *  vehicle stays in the operational consoles (truck01.html / truck02.html) where the
 *  operator's assignment is authenticated and authorized server-side.
 * ==========================================================================
 *
 * Every number here is SUPPLIED. An absent value renders as UNAVAILABLE, never as 0:
 * `0.0 m/s` is a claim that the truck is stopped, and "we have no reading" is a different
 * claim entirely.
 *
 * Plain React, no WebGL, so it renders under `renderToString` (M4D-C).
 */

import { EmptyState, Panel } from "../components/primitives";
import { DATA_STATE_TEXT, UNAVAILABLE_LABEL, UNAVAILABLE_VALUE } from "../state/dataStatus";
import { LINK_STATE_GLYPH, type LinkStatus } from "../vehicle/communication";
import { type MineCastVehicle, metresText, PROVENANCE_TEXT, speedText } from "./minecastProjection";

function LinkRows({ link }: { link: LinkStatus }) {
  return (
    <>
      <tr data-link={link.label} data-state={link.state}>
        <td>
          {link.label} · {link.bearer}
        </td>
        <td>
          <span aria-hidden="true">{LINK_STATE_GLYPH[link.state]}</span> {link.state}
        </td>
      </tr>
      <tr>
        <td colSpan={2} className="faint mc-link-reason">
          {link.reason}
        </td>
      </tr>
      {link.metrics.map((metric) => (
        <tr key={`${link.label}-${metric.label}`} className={metric.available ? undefined : "dim"}>
          <td>{metric.label}</td>
          <td>
            {metric.value}
            {metric.available && metric.unit ? (
              <span className="metric-unit"> {metric.unit}</span>
            ) : null}
          </td>
        </tr>
      ))}
    </>
  );
}

export function VehiclePanel({ vehicle }: { vehicle: MineCastVehicle | null }) {
  if (!vehicle) {
    return (
      <Panel title="Selected vehicle">
        <EmptyState
          headline="NO VEHICLE SELECTED"
          detail="Select a vehicle in the fleet panel to inspect its state."
        />
      </Panel>
    );
  }

  const { position, safety } = vehicle;

  return (
    <Panel title={`Vehicle ${vehicle.displayId}`}>
      <div className="mc-vehicle-head" data-availability={vehicle.availability}>
        <span className="mc-vehicle-id">{vehicle.displayId}</span>
        {/* The canonical id is shown, not hidden: it is what every other system uses. */}
        <span className="faint mono">{vehicle.canonicalVehicleId}</span>
        <span className="mc-vehicle-avail">{vehicle.availability}</span>
      </div>

      {!vehicle.present ? (
        <p className="mc-note">
          The Digital Twin carries no state for this vehicle. Nothing below is assumed about it.
        </p>
      ) : null}

      <h4>Motion</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Speed</td>
            <td>{speedText(vehicle.speedMps)}</td>
          </tr>
          <tr>
            <td>Mode</td>
            <td>{vehicle.mode ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Freshness</td>
            <td>{DATA_STATE_TEXT[vehicle.dataState]}</td>
          </tr>
          <tr>
            <td>Data source</td>
            <td className="mono">{vehicle.dataSource}</td>
          </tr>
        </tbody>
      </table>

      <h4>Safety</h4>
      {safety.unavailable ? (
        <p className="mc-note">
          SAFETY DATA UNAVAILABLE. The safety subsystem has supplied nothing for this vehicle.
          Nothing here is calculated in Mine-Cast.
        </p>
      ) : null}
      <table className="data-table">
        <tbody>
          <tr>
            <td>Actual speed</td>
            <td>{speedText(safety.actualSpeedMps)}</td>
          </tr>
          <tr>
            <td>V_safe</td>
            <td>{speedText(safety.vSafeMps)}</td>
          </tr>
          <tr>
            <td>H_safe</td>
            <td>{metresText(safety.hSafeM)}</td>
          </tr>
          <tr>
            <td>Headway</td>
            <td>{metresText(safety.headwayM)}</td>
          </tr>
          <tr>
            <td>Lead vehicle</td>
            <td>{safety.leadVehicleId ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Risk</td>
            <td>{safety.riskLevel ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Active constraint</td>
            <td>{safety.activeConstraint ?? UNAVAILABLE_LABEL}</td>
          </tr>
          <tr>
            <td>Headway violation</td>
            <td>
              {safety.headwayViolation === null
                ? UNAVAILABLE_VALUE
                : String(safety.headwayViolation)}
            </td>
          </tr>
          <tr>
            <td>Envelope violation</td>
            <td>
              {safety.envelopeViolation === null
                ? UNAVAILABLE_VALUE
                : String(safety.envelopeViolation)}
            </td>
          </tr>
        </tbody>
      </table>

      <h4>Position</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Kind</td>
            <td>{position.kind}</td>
          </tr>
          <tr>
            <td>Method</td>
            <td>{position.method}</td>
          </tr>
          <tr>
            <td>Provenance</td>
            <td>{PROVENANCE_TEXT[position.provenance]}</td>
          </tr>
          {/*
            Local-frame metres, and labelled as such. A local odometry pose is a distance
            from a configured origin with accumulating error - it is NOT a coordinate on
            the earth, and it is never printed as latitude/longitude.
          */}
          <tr className={position.xM === null ? "dim" : undefined}>
            <td>X (local, m)</td>
            <td>{position.xM === null ? UNAVAILABLE_VALUE : position.xM.toFixed(2)}</td>
          </tr>
          <tr className={position.yM === null ? "dim" : undefined}>
            <td>Y (local, m)</td>
            <td>{position.yM === null ? UNAVAILABLE_VALUE : position.yM.toFixed(2)}</td>
          </tr>
          <tr className={position.headingRad === null ? "dim" : undefined}>
            <td>Heading (rad)</td>
            <td>
              {position.headingRad === null ? UNAVAILABLE_VALUE : position.headingRad.toFixed(3)}
            </td>
          </tr>
          <tr className={position.distanceM === null ? "dim" : undefined}>
            <td>Distance travelled</td>
            <td>{metresText(position.distanceM)}</td>
          </tr>
          <tr>
            <td>Freshness</td>
            <td>{DATA_STATE_TEXT[position.dataState]}</td>
          </tr>
        </tbody>
      </table>
      <p className="mc-note faint">{position.reason}</p>

      <h4>Communications</h4>
      <table className="data-table">
        <tbody>
          <LinkRows link={vehicle.v2v} />
          <LinkRows link={vehicle.v2i} />
          <tr>
            <td>Peer</td>
            <td>
              {vehicle.peerDisplayId ?? UNAVAILABLE_LABEL}
              {vehicle.peerVehicleId ? (
                <span className="faint mono"> ({vehicle.peerVehicleId})</span>
              ) : null}
            </td>
          </tr>
          <tr>
            <td>Peer in Twin</td>
            {/*
              Peer PRESENCE is not a link claim. Both trucks reporting to the backend over
              Wi-Fi says nothing about whether they can hear each other over LoRa - that is
              what the V2V row above answers, from measured evidence only.
            */}
            <td>{vehicle.peerPresent ? "PRESENT" : "NOT PRESENT"}</td>
          </tr>
        </tbody>
      </table>

      <h4>Alerts</h4>
      <p className="mc-note">
        {vehicle.activeAlertCount} active / {vehicle.alertCount} total for this vehicle.
      </p>
    </Panel>
  );
}
