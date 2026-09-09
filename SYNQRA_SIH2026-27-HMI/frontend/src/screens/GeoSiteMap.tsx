/**
 * Geospatial site map — NMDC Bailadila geospatial Digital Twin prototype.
 *
 * ==========================================================================
 *  SVG, exactly like `MineMap.tsx`. NO MAPPING LIBRARY.
 *
 *  No Leaflet, no MapLibre, no tile layer, no satellite imagery. A tile basemap would
 *  put an aerial photograph under invented geometry, which is precisely the impression
 *  this prototype must not create. `MineMap.tsx` is untouched: it renders the abstract
 *  topology graph, this renders geographic coordinates, and mixing two coordinate
 *  systems in one component is how a projection bug becomes invisible.
 * ==========================================================================
 *
 *  THREE PROVENANCE CHAINS ARE VISUALLY DISTINCT AND LABELLED IN TEXT:
 *
 *    published extent   solid, stated as a COORDINATE EXTENT, never a boundary
 *    OSM-derived        dashed, ODbL attribution rendered whenever drawn
 *    synthetic          dotted, every feature says DEMONSTRATION ONLY
 *
 *  Colour is never the only signal - each layer's provenance is written out (NFR-008).
 */

import { EmptyState, Panel } from "../components/primitives";
import {
  drawableLayers,
  extentSizeMetres,
  formatDms,
  GEO_PROVENANCE_TEXT,
  type GeoSite,
  type LayerId,
  OSM_ATTRIBUTION,
  requiresOsmAttribution,
  screenProjection,
  toDecimalExtent,
  unavailableLayers,
} from "../state/geoSite";
import {
  placeablePositions,
  unplaceablePositions,
  type VehiclePosition,
} from "../state/vehiclePosition";

const VIEW_W = 900;
const VIEW_H = 720;

/**
 * Per-layer drawing style.
 *
 * `dash` keeps the three provenance chains separable WITHOUT colour: the published extent
 * is solid, OSM is long-dashed, and every synthetic layer is short-dashed or dotted. The
 * legend still writes each chain out in words (NFR-008).
 */
interface LayerStyle {
  stroke: string;
  fill: string;
  width: number;
  dash: string;
}

const LAYER_STYLE: Record<LayerId, LayerStyle> = {
  SITE_EXTENT: { stroke: "#38bdf8", fill: "none", width: 2, dash: "none" },
  OSM_CONTEXT_ROADS: { stroke: "#a78bfa", fill: "none", width: 2, dash: "10 6" },
  OSM_SITE_AREAS: { stroke: "#34d399", fill: "rgba(52,211,153,0.12)", width: 2, dash: "8 4" },
  OSM_SITE_ROADS: { stroke: "#a78bfa", fill: "none", width: 2, dash: "10 6" },
  OSM_TOWNSHIP_ROADS: { stroke: "#6b7280", fill: "none", width: 1, dash: "4 4" },
  SYNTHETIC_PIT: { stroke: "#f0a35e", fill: "rgba(240,163,94,0.10)", width: 2, dash: "6 4" },
  SYNTHETIC_BENCHES: { stroke: "#b07d4a", fill: "rgba(176,125,74,0.10)", width: 1, dash: "4 4" },
  SYNTHETIC_HAUL_ROADS: { stroke: "#d8c9a3", fill: "none", width: 3, dash: "6 4" },
  SYNTHETIC_JUNCTIONS: { stroke: "#d8c9a3", fill: "none", width: 1, dash: "none" },
  SYNTHETIC_LOADING_FACES: { stroke: "#34d399", fill: "none", width: 1, dash: "none" },
  SYNTHETIC_PROCESSING: { stroke: "#60a5fa", fill: "rgba(96,165,250,0.14)", width: 2, dash: "4 3" },
  SYNTHETIC_DUMPS: { stroke: "#8b949e", fill: "rgba(139,148,158,0.12)", width: 2, dash: "4 3" },
  SYNTHETIC_SUPPORT: { stroke: "#c084fc", fill: "none", width: 1, dash: "none" },
  SYNTHETIC_OPERATIONAL_ZONES: {
    stroke: "#fbbf24",
    fill: "rgba(251,191,36,0.08)",
    width: 1,
    dash: "2 4",
  },
  VEHICLES: { stroke: "#fbbf24", fill: "none", width: 1, dash: "none" },
};

export function GeoSiteMap({
  site,
  positions,
  mode,
  onSelectVehicle,
}: {
  site: GeoSite;
  positions: VehiclePosition[];
  /** LIVE / MOCK / REPLAY, shown so a simulated map is never mistaken for a live one. */
  mode: string;
  onSelectVehicle?: (vehicleId: string) => void;
}) {
  const extent = toDecimalExtent(site.extent);
  const paddedExtent = {
    west: extent.west - (extent.east - extent.west) * 0.06,
    east: extent.east + (extent.east - extent.west) * 0.06,
    south: extent.south - (extent.north - extent.south) * 0.06,
    north: extent.north + (extent.north - extent.south) * 0.06,
  };
  const projection = screenProjection(paddedExtent, VIEW_W, VIEW_H);
  const extNW = projection.project({ lon: extent.west, lat: extent.north });
  const extSE = projection.project({ lon: extent.east, lat: extent.south });
  const extBox = {
    x: extNW.x,
    y: extNW.y,
    width: extSE.x - extNW.x,
    height: extSE.y - extNW.y,
  };

  const size = extentSizeMetres(extent);
  const drawable = drawableLayers(site);
  const missing = unavailableLayers(site);
  const placed = placeablePositions(positions);
  const unplaced = unplaceablePositions(positions);

  return (
    <Panel
      title="Bailadila Deposit-5 — geospatial Digital Twin prototype"
      note="prototype · not an official NMDC system"
    >
      <dl className="fields">
        <div className="field">
          <dt>Site</dt>
          <dd>{site.siteName}</dd>
          <div className="faint">
            {site.district}, {site.state} · lease {site.leaseAreaHa} ha · toposheet{" "}
            {site.toposheet}
          </div>
        </div>
        <div className="field">
          <dt>Published extent</dt>
          <dd className="mono">
            {formatDms(site.extent.south)} – {formatDms(site.extent.north)} ·{" "}
            {formatDms(site.extent.west)} – {formatDms(site.extent.east)}
          </dd>
          <div className="faint">{site.extentSource}</div>
        </div>
        <div className="field">
          <dt>Coordinate reference</dt>
          <dd className="mono">{site.coordinateReference}</dd>
          <div className="faint">
            The source document states no datum. WGS84 is assumed and that assumption is
            unverified.
          </div>
        </div>
        <div className="field">
          <dt>Extent size</dt>
          <dd className="mono">
            {(size.widthM / 1000).toFixed(2)} × {(size.heightM / 1000).toFixed(2)} km
          </dd>
          <div className="faint">
            Larger than the {site.leaseAreaHa} ha lease — a bounding extent is not the lease
            shape.
          </div>
        </div>
        <div className="field">
          <dt>Mode</dt>
          <dd>{mode}</dd>
        </div>
      </dl>

      <svg
        className="map-frame"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label={`Mine site: ${drawable.length} layers drawn, ${placed.length} vehicles placed, ${unplaced.length} position unavailable`}
        style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}`, maxHeight: "52vh", width: "100%" }}
      >
        <title>Bailadila Deposit-5 geospatial prototype</title>

        {/*
          THE PUBLISHED EXTENT. Drawn as a rectangle inside the padded viewport so all
          four corners and bounds are completely visible without clipping.
        */}
        <rect
          className="geo-extent"
          x={extBox.x}
          y={extBox.y}
          width={extBox.width}
          height={extBox.height}
          fill="none"
          stroke="#38bdf8"
          strokeWidth={2}
        />
        <text className="geo-extent-label" x={extBox.x + 10} y={extBox.y + 22} fill="#38bdf8" fontSize={14}>
          PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary
        </text>

        {drawable
          .filter((layer) => layer.id !== "SITE_EXTENT")
          .map((layer) => {
            const style = LAYER_STYLE[layer.id];
            return (
              <g key={layer.id} aria-label={layer.name}>
                {layer.features.map((feature) => {
                  const points = feature.coordinates.map((c) => projection.project(c));
                  const asPath = points.map((p) => `${p.x},${p.y}`).join(" ");

                  if (feature.geometryType === "POLYGON" && points.length > 2) {
                    return (
                      <polygon
                        key={feature.id}
                        points={asPath}
                        fill={style.fill}
                        stroke={style.stroke}
                        strokeWidth={style.width}
                        strokeDasharray={style.dash}
                      />
                    );
                  }

                  if (feature.geometryType === "LINESTRING" && points.length > 1) {
                    return (
                      <polyline
                        key={feature.id}
                        points={asPath}
                        fill="none"
                        stroke={style.stroke}
                        strokeWidth={style.width}
                        strokeDasharray={style.dash}
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                    );
                  }

                  const first = points[0];
                  if (!first) return null;
                  return (
                    <g key={feature.id}>
                      <circle cx={first.x} cy={first.y} r={5} fill="none" stroke={style.stroke} />
                      <text x={first.x + 9} y={first.y + 4} fill={style.stroke} fontSize={10}>
                        {feature.name.replace("Demonstration ", "")}
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })}

        {/* Vehicles. Only those with a real position from the active provider. */}
        {placed.map((entry) => {
          const point = projection.project(
            entry.position as NonNullable<VehiclePosition["position"]>,
          );
          const labelText =
            entry.provenance === "SOFTWARE_ONLY_SYNTHETIC"
              ? `${entry.vehicleId} · SOFTWARE TEST · SYNTHETIC GNSS`
              : `${entry.vehicleId} · ${entry.provenance}`;
          const fill = entry.provenance === "SOFTWARE_ONLY_SYNTHETIC" ? "#f59e0b" : "#fbbf24";
          return (
            <g
              key={entry.vehicleId}
              onClick={onSelectVehicle ? () => onSelectVehicle(entry.vehicleId) : undefined}
              style={onSelectVehicle ? { cursor: "pointer" } : undefined}
            >
              <rect x={point.x - 6} y={point.y - 6} width={12} height={12} fill={fill} />
              <text x={point.x + 12} y={point.y + 4} fill="#f0f6fc" fontSize={12}>
                {labelText}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend — every drawn layer names its provenance chain in words. */}
      <dl className="fields">
        {drawable.map((layer) => (
          <div className="field" key={layer.id}>
            <dt>{layer.name}</dt>
            <dd>{GEO_PROVENANCE_TEXT[layer.provenance]}</dd>
          </div>
        ))}
      </dl>

      {requiresOsmAttribution(site) ? <p className="faint">{OSM_ATTRIBUTION}</p> : null}

      {/* Vehicles with no position are LISTED, never dropped and never guessed. */}
      {unplaced.length > 0 ? (
        <EmptyState
          headline={`POSITION UNAVAILABLE (${unplaced.length})`}
          detail={`${unplaced.map((u) => u.vehicleId).join(", ")} — ${
            unplaced[0]?.reason ?? "no position supplied"
          }`}
        />
      ) : null}

      {/* Declared-but-empty layers say why, rather than being silently absent. */}
      {missing.length > 0 ? (
        <dl className="fields">
          {missing.map((layer) => (
            <div className="field" key={layer.id}>
              <dt>{layer.name}</dt>
              <dd className="dim">UNAVAILABLE</dd>
              {layer.unavailableReason ? (
                <div className="faint">{layer.unavailableReason}</div>
              ) : null}
            </div>
          ))}
        </dl>
      ) : null}

      <p className="faint">
        Synthetic demonstration geometry is invented and is NOT NMDC infrastructure. No
        official NMDC haul-road, crusher or dump geometry is claimed. Physical NMDC mine
        integration is NOT VERIFIED and real vehicle positioning is NOT VERIFIED.
      </p>
    </Panel>
  );
}
