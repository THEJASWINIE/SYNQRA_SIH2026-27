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

/** Stroke style per layer, so the three chains are separable without reading colour. */
const LAYER_STROKE: Record<LayerId, string> = {
  SITE_EXTENT: "none",
  OSM_CONTEXT_ROADS: "10 6",
  SYNTHETIC_HAUL_ROADS: "3 5",
  SYNTHETIC_JUNCTIONS: "none",
  SYNTHETIC_OPERATIONAL_ZONES: "none",
  VEHICLES: "none",
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
  const projection = screenProjection(extent, VIEW_W, VIEW_H);
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
        aria-label={`Bailadila Deposit-5 published coordinate extent, ${drawable.length} layers drawn, ${placed.length} vehicles placed`}
        style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}`, maxHeight: "70vh", width: "100%" }}
      >
        <title>Bailadila Deposit-5 geospatial prototype</title>

        {/*
          THE PUBLISHED EXTENT. Drawn as a rectangle because it IS a rectangle of four
          published bounds — not because the lease is rectangular. The label says so.
        */}
        <rect
          className="geo-extent"
          x={0}
          y={0}
          width={VIEW_W}
          height={VIEW_H}
          fill="none"
          stroke="#38bdf8"
          strokeWidth={2}
        />
        <text className="geo-extent-label" x={10} y={22} fill="#38bdf8" fontSize={14}>
          PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary
        </text>

        {drawable
          .filter((layer) => layer.id !== "SITE_EXTENT")
          .map((layer) => (
            <g key={layer.id} aria-label={layer.name}>
              {layer.features.map((feature) => {
                const points = feature.coordinates.map((c) => projection.project(c));
                if (feature.geometryType === "LINESTRING" && points.length > 1) {
                  return (
                    <polyline
                      key={feature.id}
                      points={points.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill="none"
                      stroke="#8b949e"
                      strokeWidth={3}
                      strokeDasharray={LAYER_STROKE[layer.id]}
                    />
                  );
                }
                const first = points[0];
                if (!first) return null;
                return (
                  <g key={feature.id}>
                    <circle cx={first.x} cy={first.y} r={6} fill="none" stroke="#8b949e" />
                    <text x={first.x + 10} y={first.y + 4} fill="#8b949e" fontSize={11}>
                      {feature.name}
                    </text>
                  </g>
                );
              })}
            </g>
          ))}

        {/* Vehicles. Only those with a real position from the active provider. */}
        {placed.map((entry) => {
          const point = projection.project(
            entry.position as NonNullable<VehiclePosition["position"]>,
          );
          return (
            <g
              key={entry.vehicleId}
              onClick={onSelectVehicle ? () => onSelectVehicle(entry.vehicleId) : undefined}
              style={onSelectVehicle ? { cursor: "pointer" } : undefined}
            >
              <rect x={point.x - 6} y={point.y - 6} width={12} height={12} fill="#fbbf24" />
              <text x={point.x + 12} y={point.y + 4} fill="#f0f6fc" fontSize={12}>
                {entry.vehicleId} · {entry.provenance}
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
