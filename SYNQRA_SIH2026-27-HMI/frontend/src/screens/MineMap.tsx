/**
 * Mine map — M4.
 *
 * ============================================================================
 *  SUPPLIED COORDINATES ONLY.
 *
 *  Nodes are drawn at `TopologyNode.x/y`. Vehicles are drawn at
 *  `VehiclePosition.x/y`. There is deliberately NO other path to a coordinate:
 *
 *    - no dead reckoning from speed and elapsed time
 *    - no tweening or animated movement between updates
 *    - no reuse of a previous point as if it were current
 *    - no placement at a "near enough" node
 *    - no trajectory prediction or future position estimate
 *
 *  A marker is placed from supplied `x`/`y`, or by the M4D-F geometric
 *  transform over supplied `segmentId`, supplied `offsetM` and supplied node
 *  geometry — see `resolvePosition`. Where those inputs are insufficient the
 *  vehicle is listed as POSITION UNAVAILABLE with the specific missing input
 *  named. A guessed truck on an operator's map is worse than an absent one,
 *  because the operator cannot tell that it is guessed.
 *
 *  A vehicle moves when, and only when, a new supplied position or offset
 *  arrives. Nothing here advances a marker with the clock.
 * ============================================================================
 *
 * An SVG graph, not a photorealistic mine — the specification does not require one.
 */

import { EmptyState } from "../components/primitives";
import type { AppState } from "../contracts/appState";
import {
  POSITION_UNAVAILABLE_REASON_TEXT,
  placeVehicles,
  projectTopology,
  speedView,
} from "../state/derive";

export function MineMap({ state }: { state: AppState }) {
  const projection = projectTopology(state.topology);
  const { placed, unplaced } = placeVehicles(state.vehicles, state.topology);

  if (state.topology === null || projection === null) {
    return (
      <EmptyState
        headline="TOPOLOGY UNAVAILABLE"
        detail="No mine topology has been supplied. The map is not rendered rather than shown empty, which would read as an empty mine."
      />
    );
  }

  const nodeById = new Map(state.topology.nodes.map((n) => [n.nodeId, n]));

  return (
    <>
      <svg
        className="map-frame"
        viewBox={`${projection.minX} ${projection.minY} ${projection.width} ${projection.height}`}
        role="img"
        aria-label={`Mine map: ${state.topology.nodes.length} nodes, ${placed.length} vehicles placed, ${unplaced.length} position unavailable`}
        style={{ aspectRatio: `${projection.width} / ${projection.height}`, maxHeight: "60vh" }}
      >
        <title>Mine topology and fleet</title>

        {state.topology.segments.map((segment) => {
          const from = nodeById.get(segment.fromNode);
          const to = nodeById.get(segment.toNode);
          // A segment whose endpoints were not supplied is not drawn to a guessed point.
          if (!from || !to) return null;
          return (
            <line
              key={segment.segmentId}
              className="map-segment"
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
            />
          );
        })}

        {state.topology.nodes.map((node) => (
          <g key={node.nodeId}>
            <circle className="map-node" cx={node.x} cy={node.y} r={5} />
            <text className="map-node-label" x={node.x + 8} y={node.y - 6}>
              {node.label}
            </text>
          </g>
        ))}

        {placed.map(({ vehicle, x, y }) => {
          const violation = speedView(state.safety[vehicle.vehicleId])?.violation === true;
          return (
            <g key={vehicle.vehicleId}>
              {/* Shape carries the violation as well as colour: a violating vehicle is
                  drawn as a triangle, so the map survives greyscale (NFR-008). */}
              {violation ? (
                <polygon
                  className="map-vehicle violation"
                  points={`${x},${y - 7} ${x - 6},${y + 5} ${x + 6},${y + 5}`}
                />
              ) : (
                <rect className="map-vehicle" x={x - 4} y={y - 4} width={8} height={8} />
              )}
              <text className="map-vehicle-label" x={x + 9} y={y + 4}>
                {vehicle.vehicleId}
                {violation ? " ▲" : ""}
              </text>
            </g>
          );
        })}
      </svg>

      {placed.length === 0 && unplaced.length === 0 ? (
        <EmptyState
          headline="NO VEHICLES SUPPLIED"
          detail="Topology is drawn; the data layer has supplied no vehicle state."
        />
      ) : null}

      {placed.length === 0 && unplaced.length > 0 ? (
        <EmptyState
          headline="NO VEHICLE POSITIONS AVAILABLE"
          detail="Topology is drawn; no vehicle carries supplied coordinates, and no supplied segment geometry was sufficient to place one."
        />
      ) : null}

      {unplaced.length > 0 ? (
        <div className="faint" style={{ marginTop: "0.5rem" }}>
          <strong>POSITION UNAVAILABLE ({unplaced.length})</strong>{" "}
          {unplaced
            .map((u) => `${u.vehicle.vehicleId} (${POSITION_UNAVAILABLE_REASON_TEXT[u.reason]})`)
            .join(", ")}{" "}
          — listed rather than placed. No position is guessed.
        </div>
      ) : null}
    </>
  );
}
