/**
 * Mini-map — site context, drawn from the only geometry that actually exists.
 *
 * ==========================================================================
 *  ONE RECTANGLE, BECAUSE ONE RECTANGLE IS ALL THE DATA SUPPORTS.
 *
 *  The published source gives four coordinate EXTREMA. A north/south/east/west extent IS
 *  a rectangle - drawing it as one invents nothing. What would be invented is calling it
 *  a lease boundary, or joining the extrema into a "pit outline", or adding roads and
 *  benches nobody surveyed. None of that happens here: this component draws the extent,
 *  a north arrow, a scale bar, and nothing else.
 *
 *  The rectangle is dashed and captioned PUBLISHED COORDINATE EXTENT / NOT A LEASE
 *  BOUNDARY, so its status travels with the picture.
 * ==========================================================================
 *
 * WHY NO TRUCKS ARE DRAWN
 *
 * A marker needs a GEOGRAPHIC position. Neither vehicle has a GNSS receiver, and
 * TRUCK_01's wheel+IMU pose is LOCAL odometry - metres from a configured origin, with no
 * surveyed anchor tying it to the earth. Projecting it onto this map would fabricate a
 * geographic coordinate out of a local one, so it is listed in words instead. When a
 * legitimate anchor or a real GNSS fix exists, markers appear here and not before.
 *
 * Inline SVG. No WebGL, no map engine, no tiles, so it renders under `renderToString`
 * (M4D-C) and adds no dependency.
 */

import { Panel } from "../components/primitives";
import { extentSizeMetres, toDecimalExtent } from "../state/geoSite";
import type { MineCastState } from "./minecastProjection";

const VIEW_W = 260;
const VIEW_H = 200;
const PAD = 34;

export function MiniMap({ minecast }: { minecast: MineCastState }) {
  const { site } = minecast;
  const extent = toDecimalExtent(site.extent);
  const size = extentSizeMetres(extent);

  // The extent box, inset so the caption and north arrow have room.
  const box = { x: PAD, y: PAD, width: VIEW_W - PAD * 2, height: VIEW_H - PAD * 2 };

  /**
   * Only a GEOGRAPHIC position can be placed on a geographic map. A local odometry pose
   * is counted separately and never plotted.
   */
  const geographic = minecast.vehicles.filter(
    (vehicle) => vehicle.position.kind === "GEOGRAPHIC" && vehicle.position.available,
  );
  const localOnly = minecast.vehicles.filter(
    (vehicle) => vehicle.position.kind === "LOCAL_ODOMETRY",
  );

  const label = `${site.extentLabel}. ${site.extentCaveat}. ${geographic.length} of ${minecast.fleetTotal} vehicles have a geographic position.`;

  return (
    <Panel title="Site context">
      <svg
        className="mc-minimap"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label={label}
        preserveAspectRatio="xMidYMid meet"
      >
        <rect x={0} y={0} width={VIEW_W} height={VIEW_H} className="mc-minimap-bg" />

        {/*
          Dashed, never solid. A solid outline reads as a surveyed boundary; a dashed one
          reads as what this is - an extent derived from four published coordinates.
        */}
        <rect
          x={box.x}
          y={box.y}
          width={box.width}
          height={box.height}
          className="mc-minimap-extent"
          fill="none"
          strokeDasharray="6 4"
        />

        <text x={box.x} y={box.y - 18} className="mc-minimap-caption">
          {site.extentLabel}
        </text>
        <text x={box.x} y={box.y - 7} className="mc-minimap-caveat">
          {site.extentCaveat}
        </text>

        {/* North indicator. The extent is stated N/S/E/W, so up is north. */}
        <g className="mc-minimap-north">
          <line
            x1={VIEW_W - 16}
            y1={box.y + 22}
            x2={VIEW_W - 16}
            y2={box.y + 2}
            markerEnd="url(#mc-north-arrow)"
          />
          <text x={VIEW_W - 16} y={box.y + 34} textAnchor="middle">
            N
          </text>
        </g>
        <defs>
          <marker
            id="mc-north-arrow"
            viewBox="0 0 8 8"
            refX="4"
            refY="4"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M 0 8 L 4 0 L 8 8 z" className="mc-minimap-arrowhead" />
          </marker>
        </defs>

        {/* Scale bar across the extent's own measured width. */}
        <g className="mc-minimap-scale">
          <line x1={box.x} y1={VIEW_H - 16} x2={box.x + box.width} y2={VIEW_H - 16} />
          <text x={box.x} y={VIEW_H - 5}>
            {(size.widthM / 1000).toFixed(2)} km E–W · {(size.heightM / 1000).toFixed(2)} km N–S
          </text>
        </g>

        {/*
          No vehicle markers. There is no geographic position to place, and a marker at a
          guessed coordinate is worse than no marker at all.
        */}
        {geographic.length === 0 ? (
          <text x={VIEW_W / 2} y={VIEW_H / 2} textAnchor="middle" className="mc-minimap-empty">
            NO GEOGRAPHIC POSITION
          </text>
        ) : null}
      </svg>

      <p className="mc-note faint">
        Datum recorded as <span className="mono">{site.coordinateReference}</span>. The extent is
        drawn from four published coordinate extrema and is not a surveyed boundary.
      </p>

      {localOnly.length > 0 ? (
        <p className="mc-note faint">
          {localOnly.map((vehicle) => vehicle.displayId).join(", ")} report LOCAL ODOMETRY only. A
          local pose has no surveyed anchor to the earth, so it is not plotted on this geographic
          view.
        </p>
      ) : null}
    </Panel>
  );
}
