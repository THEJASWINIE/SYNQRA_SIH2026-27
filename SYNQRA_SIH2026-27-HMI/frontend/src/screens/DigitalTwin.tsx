/**
 * S6 Digital Twin — Phase 7.
 *
 * ==========================================================================
 *  A MINE NETWORK DIAGRAM, NOT A MAP.
 *
 *  Topology coordinates are abstract graph units supplied by the provider. They are
 *  NOT surveyed positions, so nothing here claims a geographic scale, a bearing or a
 *  fix. The heading is labelled "MINE TOPOLOGY" for that reason.
 *
 *  No vehicle is drawn at an invented coordinate. Placement is the existing
 *  `MineMap` / `placeVehicles` path (M4D-F), reused unmodified: a vehicle appears
 *  only where supplied inputs put it, and is otherwise LISTED as position
 *  unavailable with the missing input named.
 * ==========================================================================
 *
 *  AUDITED: the live backend supplies no topology, no position, no road id and no
 *  environment, so S6 in LIVE mode correctly shows an attached Twin with an empty
 *  model. MOCK and REPLAY supply real topology and the same screen draws it. Nothing
 *  branches on the provider.
 */

import { useMemo, useState } from "react";
import { EmptyState, Panel } from "../components/primitives";
import type { VehicleId } from "../contracts/primitives";
import {
  legendEntries,
  nodeRows,
  segmentRows,
  twinDataStatus,
  twinVehicleCountText,
  vehicleContextRows,
} from "../state/digitalTwin";
import { provenanceLabel, UNAVAILABLE } from "../state/safetyEnvironment";
import { HEALTH_GLYPH, type HealthLine, twinLine } from "../state/systemHealth";
import { useAppState } from "../state/useAppState";
import { MineMap } from "./MineMap";

/** One status line. The glyph never carries the meaning alone (NFR-008). */
function StatusRow({ line }: { line: HealthLine }) {
  return (
    <div className="field">
      <dt>{line.label}</dt>
      <dd className={line.state === "OK" ? undefined : "dim"}>
        <span aria-hidden="true">{HEALTH_GLYPH[line.state]}</span> {line.value}
      </dd>
      {line.detail ? <div className="faint">{line.detail}</div> : null}
    </div>
  );
}

export function DigitalTwin({ vehicleId }: { vehicleId?: VehicleId | null }) {
  const state = useAppState();

  /**
   * Selection is UI state only, seeded from the shell's selected vehicle so S6 stays
   * consistent with S2, S3 and S4. It holds an id; the vehicle is read from the shared
   * store on every render.
   */
  const [picked, setPicked] = useState<VehicleId | null>(null);
  const vehicleIds = useMemo(() => Object.keys(state.vehicles).sort(), [state.vehicles]);
  const activeId = picked ?? vehicleId ?? vehicleIds[0] ?? null;
  const vehicle = activeId ? state.vehicles[activeId] : undefined;

  const attachment = twinLine(state.observability);
  const status = twinDataStatus(state, vehicle);
  const legend = legendEntries(state.topology);
  const nodes = nodeRows(state.topology);
  const segments = segmentRows(state.topology);
  const context = vehicleContextRows(vehicle, state.topology);
  const topologyStatus = status[0];

  return (
    <>
      {/* A — TWIN STATUS. Attachment is a software fact; it says nothing about hardware. */}
      <Panel title="Digital Twin" note="Twin attachment is not hardware connectivity">
        <dl className="fields">
          <StatusRow line={attachment} />
          <div className="field">
            <dt>Mode</dt>
            <dd>{provenanceLabel(vehicle)}</dd>
            <div className="faint">
              From the supplied per-field provenance of the selected vehicle, never from
              connectivity.
            </div>
          </div>
          <div className="field">
            <dt>Vehicles in Twin</dt>
            <dd>{twinVehicleCountText(state.observability)}</dd>
            <div className="faint">
              Backend counter. Not a count of physically connected vehicles.
            </div>
          </div>
          <div className="field">
            <dt>Vehicles in this view</dt>
            <dd>{vehicleIds.length}</dd>
          </div>
        </dl>
      </Panel>

      {/* B — MINE TOPOLOGY. The existing MineMap, reused unmodified. */}
      <Panel
        title="Mine topology"
        note="abstract network diagram — topology units, not geographic coordinates"
      >
        <MineMap state={state} />
        {legend.length > 0 ? (
          <div className="faint" style={{ marginTop: "0.5rem" }}>
            {legend.map((entry) => (
              <span key={entry.label} style={{ marginRight: "1rem" }}>
                <span aria-hidden="true">{entry.glyph}</span> {entry.label}
              </span>
            ))}
          </div>
        ) : null}
      </Panel>

      {/* C — MODELLED NODES AND ROADS, so every supplied id is legible as text. */}
      <Panel title="Modelled nodes and roads" note="supplied topology only">
        {nodes.length === 0 && segments.length === 0 ? (
          <EmptyState
            headline="NOTHING MODELLED"
            detail="The supplied topology contains no nodes and no roads, or none was supplied. No node or road is invented to fill the table."
          />
        ) : (
          <>
            <table className="data-table" aria-label="Modelled nodes">
              <caption className="faint">Nodes ({nodes.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Node</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Label</th>
                  <th scope="col">x, y (topology units)</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node) => (
                  <tr key={node.nodeId}>
                    <td className="mono">{node.nodeId}</td>
                    <td>{node.kind}</td>
                    <td>{node.label}</td>
                    <td className="mono">{node.coordText}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <table
              className="data-table"
              aria-label="Modelled roads"
              style={{ marginTop: "0.75rem" }}
            >
              <caption className="faint">Roads ({segments.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Road</th>
                  <th scope="col">From</th>
                  <th scope="col">To</th>
                  <th scope="col">Length</th>
                  <th scope="col">Grade</th>
                  <th scope="col">Direction</th>
                </tr>
              </thead>
              <tbody>
                {segments.map((segment) => (
                  <tr key={segment.segmentId}>
                    <td className="mono">{segment.segmentId}</td>
                    <td className="mono">{segment.fromNode}</td>
                    <td className="mono">{segment.toNode}</td>
                    <td>{segment.lengthText}</td>
                    <td>{segment.gradeText}</td>
                    <td>{segment.direction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Panel>

      {/* D — SELECTED VEHICLE. Shown with or without a position. */}
      <Panel title="Selected vehicle" note="context only — no position is inferred">
        {activeId === null ? (
          <EmptyState
            headline="NO VEHICLE SUPPLIED"
            detail="The data layer has supplied no vehicle state."
          />
        ) : (
          <>
            <header className="op-header">
              <div className="op-vehicle">{activeId}</div>
              {vehicleIds.length > 1 ? (
                <label className="op-picker">
                  <span className="op-picker-label">VEHICLE</span>
                  <select
                    value={activeId}
                    aria-label="Select vehicle"
                    onChange={(event) => setPicked(event.target.value as VehicleId)}
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
            <dl className="fields">
              {context.map((row) => (
                <div className="field" key={row.label}>
                  <dt>{row.label}</dt>
                  <dd className={row.available ? undefined : "dim"}>
                    {row.value}
                    {row.available && row.unit ? (
                      <span className="metric-unit"> {row.unit}</span>
                    ) : null}
                  </dd>
                  {row.provenance ? <div className="faint">{row.provenance}</div> : null}
                </div>
              ))}
            </dl>
            {context.some((row) => row.label === "Position" && !row.available) ? (
              <p className="faint">
                LIVE VEHICLE POSITION UNAVAILABLE — no coordinate is drawn or written for this
                vehicle. Position is never inferred from the selection, the speed or the node order.
              </p>
            ) : null}
          </>
        )}
      </Panel>

      {/* E — TWIN DATA STATUS. Distinguishes "no Twin" from "Twin with an empty model". */}
      <Panel title="Twin data status" note="what the Twin actually contains">
        <dl className="fields">
          {status.map((line) => (
            <StatusRow key={line.label} line={line} />
          ))}
        </dl>
        {attachment.value === "ATTACHED" && topologyStatus && topologyStatus.state !== "OK" ? (
          <p className="faint">
            The Twin is attached and running; it simply models no topology yet. That is a
            data-source gap, not a connection fault, and it is reported as {UNAVAILABLE} rather than
            as an empty mine.
          </p>
        ) : null}
      </Panel>
    </>
  );
}
