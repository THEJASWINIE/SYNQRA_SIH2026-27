/**
 * Provenance panel — what on this screen is real, and what is not.
 *
 * ==========================================================================
 *  THE ANSWER TO "IS THIS REAL?" IS ALWAYS ON SCREEN.
 *
 *  A spatial view is persuasive in a way a table is not: a truck drawn on a mine map
 *  looks measured whether or not anything measured it. This panel exists so the operator
 *  - and an SIH judge - can tell at a glance which of these applies:
 *
 *    HARDWARE            a sensor measured it
 *    DERIVED             computed from a measurement, by a named method
 *    SOFTWARE TEST       produced by a test harness (synthetic GNSS, emulator)
 *    SYNTHETIC_FOR_DEMO  invented for demonstration; a measurement of nothing
 *    UNAVAILABLE         nothing supplied it
 *
 *  Nothing here is collapsible away to a tooltip, and no class is ever promoted into a
 *  stronger one.
 * ==========================================================================
 *
 * THE SITE EXTENT IS NOT A BOUNDARY
 *
 * The four published coordinates come from a government Environmental Clearance document.
 * They are coordinate EXTREMA, not a surveyed lease polygon, not a cadastral boundary and
 * not a pillar list. The caveat is rendered next to them every time, and the datum is
 * recorded as ASSUMED_WGS84_UNVERIFIED because the source does not state it.
 *
 * VERIFICATION BOUNDARY
 *
 * Software tests can prove an algorithm, a contract or an integration. They cannot prove
 * that an ESP32, an encoder, an IMU or a LoRa modem behaved on a real vehicle. That line
 * is stated here rather than left for someone to assume.
 *
 * Plain React, no WebGL, so it renders under `renderToString` (M4D-C).
 */

import { Panel } from "../components/primitives";
import { OSM_ATTRIBUTION } from "../state/geoSite";
import { CORRIDOR_PROVENANCE } from "./haulRoads";
import {
  extentText,
  type MineCastProvenance,
  type MineCastState,
  PROVENANCE_TEXT,
} from "./minecastProjection";

/** The classes, in the order an operator should read them: strongest evidence first. */
const CLASS_ORDER: readonly MineCastProvenance[] = [
  "HARDWARE",
  "DERIVED",
  "SOFTWARE_TEST",
  "SYNTHETIC_FOR_DEMO",
  "SIMULATION",
  "REPLAY",
  "UNAVAILABLE",
];

export function ProvenancePanel({ minecast }: { minecast: MineCastState }) {
  const { site } = minecast;
  const extent = extentText(site);

  return (
    <Panel title="Provenance">
      <h4>Site</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Mine</td>
            <td>{site.name}</td>
          </tr>
          <tr>
            <td>Operator</td>
            <td>{site.operator}</td>
          </tr>
          <tr>
            <td>Location</td>
            <td>
              {site.district}, {site.state}
            </td>
          </tr>
          <tr>
            <td>Published M.L. area</td>
            <td>{site.publishedAreaHa.toFixed(2)} ha</td>
          </tr>
          <tr>
            <td>Source File No.</td>
            <td className="mono">{site.sourceFileNo}</td>
          </tr>
        </tbody>
      </table>
      <p className="mc-note faint">{site.sourceDescription}</p>

      <h4>Coordinate extent</h4>
      {/*
        The caveat is a first-class part of the data, not decoration. It renders with the
        coordinates every time they are shown.
      */}
      <div className="mc-extent-caveat" role="note">
        <strong>{site.extentLabel}</strong>
        <span className="mc-extent-not"> — {site.extentCaveat}</span>
      </div>
      <table className="data-table">
        <tbody>
          <tr>
            <td>North</td>
            <td className="mono">{extent.north}</td>
          </tr>
          <tr>
            <td>South</td>
            <td className="mono">{extent.south}</td>
          </tr>
          <tr>
            <td>East</td>
            <td className="mono">{extent.east}</td>
          </tr>
          <tr>
            <td>West</td>
            <td className="mono">{extent.west}</td>
          </tr>
          <tr>
            <td>Coordinate reference</td>
            <td className="mono">{site.coordinateReference}</td>
          </tr>
        </tbody>
      </table>
      <p className="mc-note faint">
        Four coordinate extrema from a published clearance document. They are not a surveyed
        boundary and are not joined into a lease polygon anywhere in this application.
      </p>

      <h4>Provenance classes</h4>
      <table className="data-table">
        <tbody>
          {CLASS_ORDER.map((cls) => (
            <tr key={cls} data-provenance={cls}>
              <td className="mono">{cls}</td>
              <td className="faint">{PROVENANCE_TEXT[cls]}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>This session</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Feed</td>
            <td>{minecast.feedState}</td>
          </tr>
          <tr>
            <td>Provider</td>
            <td>{minecast.mode}</td>
          </tr>
          {minecast.vehicles.map((vehicle) => (
            <tr key={vehicle.canonicalVehicleId}>
              <td>
                {vehicle.displayId} position
                <span className="faint mono"> ({vehicle.canonicalVehicleId})</span>
              </td>
              <td className="mono">
                {vehicle.position.provenance} · {vehicle.position.method}
              </td>
            </tr>
          ))}
          {minecast.vehicles.map((vehicle) => (
            <tr key={`${vehicle.canonicalVehicleId}-telemetry`}>
              <td>{vehicle.displayId} telemetry</td>
              <td className="mono">{vehicle.dataSource}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Synthetic mine geometry</h4>
      <table className="data-table">
        <tbody>
          <tr>
            <td>Haul corridors</td>
            <td className="mono">
              {CORRIDOR_PROVENANCE.source} · {CORRIDOR_PROVENANCE.classification}
            </td>
          </tr>
          <tr>
            <td>Verified</td>
            <td className="mono">{String(CORRIDOR_PROVENANCE.verified).toUpperCase()}</td>
          </tr>
          <tr>
            <td>Confidence</td>
            <td className="mono">{CORRIDOR_PROVENANCE.confidence}</td>
          </tr>
        </tbody>
      </table>
      <div className="mc-extent-caveat" role="note">
        <strong>{CORRIDOR_PROVENANCE.disclosure}</strong>
      </div>
      <p className="mc-note faint">{CORRIDOR_PROVENANCE.detail}</p>

      <h4>Hardware verification boundary</h4>
      <p className="mc-note">
        Software tests in this repository prove ALGORITHM, CONTRACT and INTEGRATION behaviour only.
        They do <strong>not</strong> constitute PHYSICAL HARDWARE VERIFICATION, which requires a
        connected ESP32, encoder, IMU, LoRa modem and network.
      </p>
      {minecast.noPhysicalPositioning ? (
        <p className="mc-note">
          No physical GNSS receiver is fitted to either vehicle. No position shown in this view is a
          physical geographic measurement.
        </p>
      ) : null}
      <p className="mc-note faint">
        No physical roadside infrastructure unit exists, so V2I is UNAVAILABLE rather than
        disconnected. Open geographic context, where drawn, is {OSM_ATTRIBUTION}.
      </p>
    </Panel>
  );
}
