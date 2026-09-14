/**
 * Fleet operations panel — left side of the Mine-Cast shell.
 *
 * Answers, at a glance: how many trucks are reporting, which ones can be trusted right
 * now, and whether the safety subsystem has anything to say about them.
 *
 * ==========================================================================
 *  A TRUCK THAT STOPS REPORTING DOES NOT DISAPPEAR FROM THIS LIST.
 *
 *  The fleet is enumerated from the CONFIGURED vehicles, so a silent truck is shown as
 *  UNAVAILABLE rather than dropping off the panel. A vehicle vanishing is precisely the
 *  failure an operator must never be shown - an empty list and a healthy list must not
 *  look the same.
 * ==========================================================================
 *
 * Renders SUPPLIED values only. No count is estimated, no risk is inferred, no safe speed
 * is computed. Plain React with no WebGL, so it renders under `renderToString` (M4D-C).
 */

import { Panel } from "../components/primitives";
import { UNAVAILABLE_LABEL } from "../state/dataStatus";
import {
  type MineCastAvailability,
  type MineCastState,
  type MineCastVehicle,
  speedText,
} from "./minecastProjection";

/** Non-colour cue, so availability is never carried by colour alone (accessibility). */
const AVAILABILITY_GLYPH: Record<MineCastAvailability, string> = {
  AVAILABLE: "●",
  DEGRADED: "◐",
  UNAVAILABLE: "○",
};

function VehicleRow({
  vehicle,
  selected,
  onSelect,
}: {
  vehicle: MineCastVehicle;
  selected: boolean;
  onSelect: (canonicalVehicleId: string) => void;
}) {
  return (
    <button
      type="button"
      className={`mc-fleet-row${selected ? " mc-selected" : ""}`}
      data-vehicle-id={vehicle.canonicalVehicleId}
      data-availability={vehicle.availability}
      aria-pressed={selected}
      // Selection carries the CANONICAL id. The label is display only.
      onClick={() => onSelect(vehicle.canonicalVehicleId)}
    >
      <span className="mc-fleet-id">
        <span aria-hidden="true">{AVAILABILITY_GLYPH[vehicle.availability]}</span>{" "}
        {vehicle.displayId}
      </span>
      <span className="mc-fleet-mode">{vehicle.mode ?? UNAVAILABLE_LABEL}</span>
      <span className="mc-fleet-speed">{speedText(vehicle.speedMps)}</span>
      <span className="mc-fleet-avail">{vehicle.availability}</span>
    </button>
  );
}

export function FleetPanel({
  minecast,
  selectedVehicleId,
  onSelect,
}: {
  minecast: MineCastState;
  selectedVehicleId: string | null;
  onSelect: (canonicalVehicleId: string) => void;
}) {
  return (
    <Panel title="Fleet operations">
      <div className="mc-kpis">
        <div className="mc-kpi">
          <div className="mc-kpi-label">REPORTING</div>
          <div className="mc-kpi-value">
            {minecast.fleetAvailable} / {minecast.fleetTotal}
          </div>
        </div>
        <div className="mc-kpi">
          <div className="mc-kpi-label">DEGRADED</div>
          <div className="mc-kpi-value">{minecast.fleetDegraded}</div>
        </div>
        <div className="mc-kpi">
          <div className="mc-kpi-label">UNAVAILABLE</div>
          <div className="mc-kpi-value">{minecast.fleetUnavailable}</div>
        </div>
        <div className="mc-kpi">
          <div className="mc-kpi-label">ACTIVE ALERTS</div>
          <div className="mc-kpi-value">{minecast.activeAlertCount}</div>
        </div>
      </div>

      <h4>Vehicles</h4>
      <div className="mc-fleet-list">
        {minecast.vehicles.map((vehicle) => (
          <VehicleRow
            key={vehicle.canonicalVehicleId}
            vehicle={vehicle}
            selected={vehicle.canonicalVehicleId === selectedVehicleId}
            onSelect={onSelect}
          />
        ))}
      </div>

      <h4>Safety</h4>
      {/*
        Each truck's safety line is SUPPLIED or UNAVAILABLE. There is no fleet-wide
        "NORMAL" aggregate: rolling two trucks into one reassuring word would hide the one
        that is in trouble, and an absent v_safe would become a safe-looking summary.
      */}
      <table className="data-table">
        <tbody>
          {minecast.vehicles.map((vehicle) => (
            <tr key={vehicle.canonicalVehicleId}>
              <td>{vehicle.displayId}</td>
              <td>{vehicle.safety.riskLevel ?? UNAVAILABLE_LABEL}</td>
              <td className="faint">
                {vehicle.safety.unavailable
                  ? "SAFETY DATA UNAVAILABLE"
                  : (vehicle.safety.activeConstraint ?? UNAVAILABLE_LABEL)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Positioning</h4>
      <p className="mc-note faint">
        {minecast.placeableCount} of {minecast.fleetTotal} vehicles have a position that can be
        drawn.
        {minecast.noPhysicalPositioning
          ? " No physical GNSS is fitted to either vehicle, so no position on this view is a physical geographic measurement: what the scene draws is the Digital Twin's own SIMULATION placement."
          : null}
      </p>
    </Panel>
  );
}
