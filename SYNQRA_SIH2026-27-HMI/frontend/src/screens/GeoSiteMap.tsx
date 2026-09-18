/**
 * 2D mine plan — the Control Room's ENGINEERING / OPERATIONS view of the Digital Twin.
 *
 * ==========================================================================
 *  STRICT TOP-DOWN ORTHOGRAPHIC PLAN. SVG. NO MAPPING LIBRARY. NO PERSPECTIVE.
 *
 *  SCENE_METRES -> `planProjection` -> SVG, uniform scale, north up. No tilt, no depth,
 *  no shaded terrain: the pit reads as nested bench rings, the roads as filled corridor
 *  bands with a dashed centreline, the dump as terraces, the trucks as top-down symbols.
 *  Contour lines come from the SAME elevation field the 3D scene is built from.
 *
 *  Everything drawn from `sceneMinePlan` is SYNTHETIC DEMONSTRATION GEOMETRY: not
 *  surveyed, not NMDC infrastructure. The published coordinate extent is the only
 *  verified geography and is drawn as a separate reference rectangle, never merged with
 *  the synthetic plan and never called a boundary.
 * ==========================================================================
 *
 *  THREE PROVENANCE CHAINS ARE VISUALLY DISTINCT AND LABELLED IN TEXT:
 *
 *    published extent   solid cyan rectangle, stated as a COORDINATE EXTENT
 *    OSM-derived        grey dashed context, ODbL attribution rendered whenever drawn
 *    synthetic          every feature carries SYN / SYNTHETIC in its label
 *
 *  Colour is never the only signal - each layer's provenance is written out (NFR-008).
 *
 *  Vehicle positions are the canonical Twin `position_scene` resolved upstream
 *  (`fleetPositions`); this file computes nothing about a vehicle. Route highlighting
 *  uses the route id the Twin stamped on the pose, matched against the shared plan.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, Panel } from "../components/primitives";
import { calloutSlots, SLOT_OFFSET } from "../state/calloutLayout";
import {
  drawableLayers,
  extentSizeMetres,
  formatDms,
  GEO_PROVENANCE_TEXT,
  type GeoSite,
  OSM_ATTRIBUTION,
  projectToLocalMetres,
  requiresOsmAttribution,
  toDecimalExtent,
  unavailableLayers,
} from "../state/geoSite";
import { CORRIDOR_DISCLOSURE } from "../state/sceneCorridors";
import {
  arrowMarks,
  type HaulCorridor,
  type MinePlan,
  PLAN_DISCLOSURE,
  planProjection,
  planScaleBar,
  polylineMidpoint,
  routeCorridorIds,
  type ScenePoint,
  sceneMinePlan,
} from "../state/sceneMinePlan";
import {
  placeablePositions,
  TWIN_SCENE_LABEL,
  unplaceablePositions,
  type VehiclePosition,
} from "../state/vehiclePosition";

/**
 * THE SHEET IS THE PUBLISHED EXTENT. The viewBox matches the extent's aspect (a thin
 * margin around it), everything drawn is clipped to it, and the sheet is fitted (never
 * cropped, never stretched: equal metres in every direction) into its frame. The <svg>
 * takes the height it is given and sets its own width from that, so the map column can
 * size itself to the sheet and the sheet is the only thing in the map zone. Nothing beyond the published coordinate extent is
 * shown: no context ground, no site-access lines, no grid running off the site.
 */
const VIEW_W = 900;
const VIEW_H = 940;

/** Corridor band colours per kind: matte haul-road ochres, no glow. */
const ROAD_FILL: Record<HaulCorridor["kind"], string> = {
  MAIN_HAUL: "#c9a266",
  RAMP: "#d3ac70",
  LOADING_LOOP: "#c4a26b",
  DISPATCH: "#b9955f",
  SERVICE: "#9d917a",
};

/** Control Room selection accent (cyan), used for the selected truck and its route only. */
const SELECT = "#22d3ee";

/** Short id for a marker tag: TRUCK_01 -> T01. Presentation only; the full id stays in text. */
function shortId(vehicleId: string): string {
  const m = /^TRUCK_(\d+)$/.exec(vehicleId);
  return m ? `T${m[1]}` : vehicleId;
}

type ToSvg = (p: ScenePoint) => { x: number; y: number };

function pathOf(points: readonly ScenePoint[], toSvg: ToSvg): string {
  return points
    .map((p) => {
      const s = toSvg(p);
      return `${s.x.toFixed(1)},${s.y.toFixed(1)}`;
    })
    .join(" ");
}

/** Degrees for an SVG `rotate` from a scene heading (counter-clockwise from east). */
function svgDegrees(angleRad: number): number {
  return (-angleRad * 180) / Math.PI;
}

export function GeoSiteMap({
  site,
  positions,
  mode,
  onSelectVehicle,
  ownVehicleId,
  selectedVehicleId,
  routeEmphasis = false,
}: {
  site: GeoSite;
  positions: VehiclePosition[];
  /** LIVE / MOCK / REPLAY, shown so a simulated map is never mistaken for a live one. */
  mode: string;
  onSelectVehicle?: (vehicleId: string) => void;
  /**
   * The vehicle this console belongs to, when it belongs to one. Its marker is ringed
   * and labelled THIS VEHICLE so a driver finds themself among the fleet at a glance.
   */
  ownVehicleId?: string;
  /** Currently selected vehicle in the control room. */
  selectedVehicleId?: string | null;
  /** HAUL ROUTES emphasis: wider bands, labels, direction arrows, selected route lit. */
  routeEmphasis?: boolean;
}) {
  const extent = toDecimalExtent(site.extent);
  const size = extentSizeMetres(extent);
  const drawable = drawableLayers(site);
  const missing = unavailableLayers(site);
  const placed = placeablePositions(positions);
  const unplaced = unplaceablePositions(positions);

  // The shared mine domain: same generators the 3D scene renders. Built once per extent.
  const plan: MinePlan = useMemo(() => sceneMinePlan(site.extent), [site.extent]);

  const proj = useMemo(() => planProjection(plan.size, plan.extent, VIEW_W, VIEW_H), [plan]);

  // Sheet width follows the height the frame gives it (presentation only).
  const frameRef = useRef<SVGSVGElement | null>(null);
  const [sheetWidthPx, setSheetWidthPx] = useState<number | null>(null);
  useEffect(() => {
    const el = frameRef.current;
    if (!el) return;
    const measure = () => {
      const h = el.getBoundingClientRect().height;
      if (h > 0) setSheetWidthPx(Math.floor((h * VIEW_W) / VIEW_H));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const toSvg = proj.toSvg;
  const bar = planScaleBar(proj);

  const selected = placed.find((p) => p.vehicleId === selectedVehicleId) ?? null;
  const selectedRouteCorridors = routeCorridorIds(plan, selected?.routeId);
  const selectedRoute = selected?.routeId
    ? (plan.routes.find((r) => r.routeId === selected.routeId) ?? null)
    : null;

  const zoneOf = (kind: MinePlan["zones"][number]["kind"]) =>
    plan.zones.find((z) => z.kind === kind);
  const active = zoneOf("ACTIVE_AREA");
  const stockpile = zoneOf("STOCKPILE");
  const dump = zoneOf("WASTE_DUMP");
  const rim = plan.benches.find((b) => b.feature.kind === "PIT");
  const floor = plan.benches.find((b) => b.feature.kind === "FLOOR");
  const crests = plan.benches.filter((b) => b.feature.kind === "BENCH");
  const benchLabels = [...(rim ? [rim] : []), ...crests, ...(floor ? [floor] : [])];

  // 500 m grid, an engineering-drawing convention, clipped to the scene box.
  const gridLines: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let m = 500; m < size.widthM; m += 500) {
    const a = toSvg({ x: m, y: 0 });
    const b = toSvg({ x: m, y: size.heightM });
    gridLines.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
  }
  for (let m = 500; m < size.heightM; m += 500) {
    const a = toSvg({ x: 0, y: m });
    const b = toSvg({ x: size.widthM, y: m });
    gridLines.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
  }

  const extentBox = proj.box;
  // Symbolic band width: a plan draws roads wider than true scale so they read as roads.
  // 1.8x true width, never under 5 units; +2 under HAUL ROUTES emphasis.
  const bandWidth = (road: HaulCorridor) =>
    Math.max(5, proj.lengthPx(road.widthM) * 1.8) + (routeEmphasis ? 2 : 0);

  // DIGITAL-TWIN-OPERATIONAL-FLOW-01: deterministic callout slots for trucks that are
  // close together. Decided in scene metres from the canonical pose; the marker never
  // moves, only the label box and its leader do. Same rule as the 3D scene.
  const slots = useMemo(
    () =>
      calloutSlots(
        placed.map((p) => {
          // Back to scene metres: the exact inverse of the pose -> lon/lat step upstream.
          const m = projectToLocalMetres(p.position as NonNullable<VehiclePosition["position"]>, {
            lon: extent.west,
            lat: extent.south,
          });
          return { id: p.vehicleId, x: m.x, y: m.y };
        }),
      ),
    [placed, extent.west, extent.south],
  );

  const arrowLines = selectedRoute
    ? [
        {
          id: selectedRoute.routeId,
          points: selectedRoute.waypoints.map(([x, y]) => ({ x, y })),
          lit: true,
        },
      ]
    : plan.corridors.map((road) => ({ id: road.id, points: road.centreline, lit: false }));

  return (
    <Panel
      title="Bailadila Deposit-5 — Digital Twin mine plan"
      note="prototype · synthetic demonstration plan · not an official NMDC system"
    >
      <div className="cr-map-workspace">
        {/* Compressed site context bar: the VERIFIED geography, kept apart from the plan. */}
        <dl className="fields cr-site-meta-bar">
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

        {/* Compact persistent disclosure above the plan. */}
        <div className="cr-corridor-strip" role="note">
          <span className="cr-corridor-tag cr-3d-provenance">
            {`${PLAN_DISCLOSURE.twin} · ${PLAN_DISCLOSURE.frame}`}
          </span>
          <span className="cr-corridor-tag">{`${CORRIDOR_DISCLOSURE} · DEMONSTRATION`}</span>
          <span className="cr-corridor-tag faint">
            {`${PLAN_DISCLOSURE.routes} · ${PLAN_DISCLOSURE.benches}`}
          </span>
        </div>

        <svg
          ref={frameRef}
          className="map-frame cr-map-frame cr-plan"
          style={sheetWidthPx === null ? undefined : { width: sheetWidthPx }}
          data-sheet-width={sheetWidthPx ?? undefined}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`Mine site: ${drawable.length + plan.corridors.length + plan.zones.length} layers drawn, ${placed.length} vehicles placed, ${unplaced.length} position unavailable`}
          data-projection="TOP_DOWN_ORTHOGRAPHIC"
          data-frame="SCENE_METRES"
        >
          <title>Bailadila Deposit-5 Digital Twin mine plan (synthetic)</title>
          <defs>
            <clipPath id="cr-sheet-clip">
              <rect x={0} y={0} width={VIEW_W} height={VIEW_H} />
            </clipPath>
            <pattern
              id="cr-hatch-dump"
              width="8"
              height="8"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="8" stroke="#8b8f96" strokeWidth="1" opacity="0.55" />
            </pattern>
            <pattern id="cr-dots-active" width="7" height="7" patternUnits="userSpaceOnUse">
              <circle cx="3.5" cy="3.5" r="0.9" fill="#f59e0b" opacity="0.55" />
            </pattern>
            <pattern
              id="cr-hatch-stock"
              width="6"
              height="6"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(-45)"
            >
              <line x1="0" y1="0" x2="0" y2="6" stroke="#d9846a" strokeWidth="1" opacity="0.5" />
            </pattern>
          </defs>

          {/* BASE: neutral plan sheet. Everything below is clipped to the sheet. */}
          <rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill="#0b0f15" />
          <g clipPath="url(#cr-sheet-clip)">
          <rect
            x={extentBox.x}
            y={extentBox.y}
            width={extentBox.width}
            height={extentBox.height}
            fill="#10161f"
          />

          {/* GRID: 500 m scene grid */}
          <g aria-label="Scene grid 500 m" opacity={0.55}>
            {gridLines.map((g, i) => (
              <line
                key={i}
                x1={g.x1}
                y1={g.y1}
                x2={g.x2}
                y2={g.y2}
                stroke="#1f2a37"
                strokeWidth={0.8}
              />
            ))}
          </g>

          {/* TOPOGRAPHY: contours of the shared synthetic field, outside the pit */}
          <g aria-label="Synthetic contours" data-layer="CONTOURS">
            {plan.contours.map((c) => {
              const longest = [...c.polylines].sort((a, b) => b.length - a.length)[0];
              const anchor = longest?.[Math.floor(longest.length / 2)];
              const s = anchor ? toSvg(anchor) : null;
              return (
                <g key={c.levelM} data-contour-level={c.displayM}>
                  {c.polylines.map((line, i) => (
                    <polyline
                      key={i}
                      points={pathOf(line, toSvg)}
                      fill="none"
                      stroke="#3a4a5c"
                      strokeWidth={0.8}
                      strokeLinejoin="round"
                      opacity={0.85}
                    />
                  ))}
                  {s ? (
                    <text
                      x={s.x + 3}
                      y={s.y - 2}
                      fill="#4b5d72"
                      fontSize={9.5}
                      fontFamily="ui-monospace, monospace"
                    >
                      {c.displayM}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </g>

          {/* DRAINAGE: synthetic context lines */}
          <g aria-label="Synthetic drainage" data-layer="DRAINAGE">
            {plan.drainage.map((d) => {
              const mid = toSvg(d.points[Math.floor(d.points.length / 2)] as ScenePoint);
              return (
                <g key={d.id} data-drain-id={d.id}>
                  <polyline
                    points={pathOf(d.points, toSvg)}
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth={1}
                    strokeDasharray="7 4"
                    opacity={0.45}
                    strokeLinejoin="round"
                  />
                  <text
                    x={mid.x + 4}
                    y={mid.y - 4}
                    fill="#22d3ee"
                    fontSize={9.5}
                    opacity={0.7}
                    letterSpacing="0.08em"
                  >
                    DRAINAGE · SYN
                  </text>
                </g>
              );
            })}
          </g>

          {/* WASTE DUMP: terraces, hatched */}
          {dump ? (
            <g aria-label={dump.label} data-zone-id={dump.id} data-layer="WASTE_DUMP">
              {dump.tiers.map((tier, i) => (
                <polygon
                  key={i}
                  points={pathOf(tier.polygon, toSvg)}
                  fill={i === 0 ? "url(#cr-hatch-dump)" : "rgba(139,143,150,0.10)"}
                  stroke="#9aa0a8"
                  strokeWidth={i === 0 ? 1.4 : 0.9}
                  strokeDasharray={i === 0 ? "none" : "4 3"}
                />
              ))}
              <text
                x={toSvg(dump.centre).x}
                y={toSvg(dump.centre).y + 3}
                fill="#c7ccd3"
                fontSize={13}
                fontWeight={700}
                textAnchor="middle"
                letterSpacing="0.1em"
              >
                {dump.planLabel}
                <tspan
                  x={toSvg(dump.centre).x}
                  dy={13}
                  fontSize={9}
                  fontWeight={400}
                  fill="#8b8f96"
                >
                  TERRACED · SYNTHETIC
                </tspan>
              </text>
            </g>
          ) : null}

          {/* ORE STOCKPILE / DISPATCH */}
          {stockpile ? (
            <g aria-label={stockpile.label} data-zone-id={stockpile.id} data-layer="STOCKPILE">
              <polygon
                points={pathOf(stockpile.polygon, toSvg)}
                fill="url(#cr-hatch-stock)"
                stroke="#d9846a"
                strokeWidth={1.4}
              />
              <text
                x={toSvg(stockpile.centre).x}
                y={toSvg(stockpile.centre).y + 3}
                fill="#f0b8a4"
                fontSize={13}
                fontWeight={700}
                textAnchor="middle"
                letterSpacing="0.1em"
              >
                {stockpile.planLabel}
                <tspan
                  x={toSvg(stockpile.centre).x}
                  dy={13}
                  fontSize={9}
                  fontWeight={400}
                  fill="#d9846a"
                >
                  SYNTHETIC
                </tspan>
              </text>
            </g>
          ) : null}

          {/* PIT: rim, stepped bench crests, floor, active working area */}
          <g
            aria-label="Synthetic bench model"
            data-layer="PIT_BENCHES"
            data-bench-model={PLAN_DISCLOSURE.benches}
          >
            {/* Terrace tones: one flat fill per level, outer to inner, so the pit steps down. */}
            {benchLabels.map((bench, i) => (
              <polygon
                key={`${bench.feature.id}-fill`}
                points={pathOf(bench.ring, toSvg)}
                fill={`rgba(${22 - i * 3},${29 - i * 4},${39 - i * 5},0.96)`}
                stroke="none"
                data-bench-fill={bench.displayM}
              />
            ))}
            {rim ? (
              <g data-feature-id={rim.feature.id} aria-label={rim.feature.label}>
                {rim.feature.segments.map((seg, i) => (
                  <polyline
                    key={i}
                    points={pathOf(seg, toSvg)}
                    fill="none"
                    stroke="#cbd5e1"
                    strokeWidth={1.8}
                  />
                ))}
              </g>
            ) : null}
            {crests.map((bench) => (
              <g
                key={bench.feature.id}
                data-feature-id={bench.feature.id}
                aria-label={bench.feature.label}
                data-bench-level={bench.displayM}
              >
                {bench.feature.segments.map((seg, i) => (
                  <polyline
                    key={i}
                    points={pathOf(seg, toSvg)}
                    fill="none"
                    stroke="#94a3b8"
                    strokeWidth={1.1}
                    strokeLinejoin="round"
                    opacity={0.9}
                  />
                ))}
              </g>
            ))}
            {floor ? (
              <g
                data-feature-id={floor.feature.id}
                aria-label={floor.feature.label}
                data-bench-level={floor.displayM}
              >
                {floor.feature.segments.map((seg, i) => (
                  <polyline
                    key={i}
                    points={pathOf(seg, toSvg)}
                    fill="none"
                    stroke="#64748b"
                    strokeWidth={1}
                    strokeLinejoin="round"
                  />
                ))}
              </g>
            ) : null}
            {active ? (
              <g data-zone-id={active.id} aria-label={active.label} data-layer="ACTIVE_AREA">
                <polygon
                  points={pathOf(active.polygon, toSvg)}
                  fill="url(#cr-dots-active)"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                />
              </g>
            ) : null}
            {/* Bench level labels, one per crest, along its first segment. */}
            {benchLabels.map((bench) => {
              const seg = bench.feature.segments[0];
              const p = seg?.[Math.floor((seg.length * 3) / 4)];
              if (!p) return null;
              const s = toSvg(p);
              return (
                <text
                  key={`${bench.feature.id}-lbl`}
                  x={s.x + 4}
                  y={s.y - 3}
                  fill="#b6c2d1"
                  fontSize={10.5}
                  fontFamily="ui-monospace, monospace"
                  letterSpacing="0.06em"
                >
                  {bench.label}
                </text>
              );
            })}
          </g>

          {/* SITE ACCESS CONTEXT: OSM-derived layers, grey, kept apart from operational roads */}
          {drawable
            .filter((layer) => layer.id.startsWith("OSM_"))
            .map((layer) => (
              <g key={layer.id} aria-label={layer.name} data-layer={layer.id}>
                {layer.features.map((feature) => {
                  const points = feature.coordinates.map((c) => proj.lonLatToSvg(c));
                  const asPath = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
                  if (feature.geometryType === "POLYGON" && points.length > 2) {
                    return (
                      <polygon
                        key={feature.id}
                        points={asPath}
                        fill="rgba(107,114,128,0.08)"
                        stroke="#6b7280"
                        strokeWidth={0.9}
                        strokeDasharray="6 4"
                      />
                    );
                  }
                  if (feature.geometryType === "LINESTRING" && points.length > 1) {
                    return (
                      <polyline
                        key={feature.id}
                        points={asPath}
                        fill="none"
                        stroke="#6b7280"
                        strokeWidth={1}
                        strokeDasharray="6 4"
                        strokeLinejoin="round"
                      />
                    );
                  }
                  const first = points[0];
                  if (!first) return null;
                  return (
                    <g key={feature.id}>
                      <circle cx={first.x} cy={first.y} r={4} fill="none" stroke="#6b7280" />
                      <text x={first.x + 7} y={first.y + 3} fill="#6b7280" fontSize={8}>
                        {feature.name}
                      </text>
                    </g>
                  );
                })}
              </g>
            ))}

          {/* HAUL ROADS: filled corridor bands, casing, dashed centreline */}
          <g
            aria-label="Synthetic haul routes"
            data-layer="HAUL_ROUTES"
            data-route-emphasis={routeEmphasis ? "true" : "false"}
          >
            {plan.corridors.map((road) => {
              const pts = pathOf(road.centreline, toSvg);
              const w = bandWidth(road);
              const lit = selectedRouteCorridors.includes(road.id);
              return (
                <g
                  key={road.id}
                  data-corridor-id={road.id}
                  data-corridor-kind={road.kind}
                  aria-label={road.label}
                  data-highlighted={lit ? "true" : undefined}
                >
                  <polyline
                    points={pts}
                    fill="none"
                    stroke={lit ? SELECT : "#2a2f37"}
                    strokeWidth={w + (lit ? 3.5 : 2.4)}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    opacity={lit ? 0.6 : 1}
                  />
                  <polyline
                    points={pts}
                    fill="none"
                    stroke={ROAD_FILL[road.kind]}
                    strokeWidth={w}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <polyline
                    points={pts}
                    fill="none"
                    stroke="#f8fafc"
                    strokeWidth={0.8}
                    strokeDasharray="6 4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    opacity={0.8}
                  />
                </g>
              );
            })}
          </g>

          {/* ROUTE EMPHASIS: direction arrows and engineering labels */}
          {routeEmphasis ? (
            <g aria-label="Route emphasis" data-layer="ROUTE_EMPHASIS">
              {arrowLines.map((line) => (
                <g key={line.id} data-arrows-for={line.id}>
                  {arrowMarks(line.points, 240).map((m, i) => {
                    const s = toSvg(m);
                    return (
                      <polygon
                        key={i}
                        points="0,-3.2 6,0 0,3.2"
                        transform={`translate(${s.x.toFixed(1)} ${s.y.toFixed(1)}) rotate(${svgDegrees(m.angleRad).toFixed(1)})`}
                        fill={line.lit ? SELECT : "#111418"}
                        opacity={0.95}
                      />
                    );
                  })}
                </g>
              ))}
              {plan.corridors.map((road) => {
                const m = polylineMidpoint(road.centreline);
                const s = toSvg(m);
                let deg = svgDegrees(m.angleRad);
                if (deg > 90) deg -= 180;
                if (deg < -90) deg += 180;
                const lit = selectedRouteCorridors.includes(road.id);
                return (
                  <text
                    key={`${road.id}-label`}
                    x={s.x}
                    y={s.y - bandWidth(road) / 2 - 3}
                    transform={`rotate(${deg.toFixed(1)} ${s.x.toFixed(1)} ${s.y.toFixed(1)})`}
                    fill={lit ? SELECT : "#f3e7c9"}
                    fontSize={11}
                    fontWeight={700}
                    textAnchor="middle"
                    letterSpacing="0.12em"
                    data-route-label={road.id}
                  >
                    {`${road.planLabel} · SYN`}
                  </text>
                );
              })}
            </g>
          ) : null}

          {/* PUBLISHED EXTENT: verified geography, separate reference layer, not a boundary */}
          <g aria-label="Published coordinate extent">
            <rect
              className="geo-extent"
              x={extentBox.x}
              y={extentBox.y}
              width={extentBox.width}
              height={extentBox.height}
              fill="none"
              stroke="#38bdf8"
              strokeWidth={1.6}
            />
            <text
              className="geo-extent-label"
              x={extentBox.x + 8}
              y={extentBox.y + 16}
              fill="#38bdf8"
              fontSize={11}
              letterSpacing="0.06em"
            >
              PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary
            </text>
          </g>

          {/* VEHICLES: top-down truck symbols from the canonical Twin scene pose */}
          <g aria-label="Vehicles" data-layer="VEHICLES">
            {placed.map((entry) => {
              const point = proj.lonLatToSvg(
                entry.position as NonNullable<VehiclePosition["position"]>,
              );
              const labelText =
                entry.provenance === "SOFTWARE_ONLY_SYNTHETIC"
                  ? `${entry.vehicleId} · SOFTWARE TEST · SYNTHETIC GNSS`
                  : entry.provenance === "SIMULATED_TWIN_SCENE"
                    ? `${entry.vehicleId} · ${TWIN_SCENE_LABEL}`
                    : `${entry.vehicleId} · ${entry.provenance}`;
              const own = ownVehicleId !== undefined && entry.vehicleId === ownVehicleId;
              const isSelected =
                selectedVehicleId !== undefined &&
                selectedVehicleId !== null &&
                entry.vehicleId === selectedVehicleId;
              const hasHeading =
                typeof entry.headingRad === "number" && Number.isFinite(entry.headingRad);
              const deg = hasHeading ? svgDegrees(entry.headingRad as number) : 0;
              const fullText = own ? `THIS VEHICLE · ${labelText}` : labelText;
              const fill = "#f59e0b";
              const routeLine = entry.routeId
                ? `${entry.routeId}${
                    entry.routeDirection === 1
                      ? " · OUTBOUND"
                      : entry.routeDirection === -1
                        ? " · RETURN"
                        : ""
                  }`
                : "ROUTE UNAVAILABLE";
              const calloutW =
                Math.max(fullText.length, isSelected ? routeLine.length : 0) * 6.6 + 12;
              const calloutH = isSelected ? 30 : 16;
              // Callout box origin: DEFAULT hangs right of the marker; a cluster slot
              // swings it left/right and up by a fixed amount, with a leader polyline.
              const slot = slots.get(entry.vehicleId) ?? "DEFAULT";
              const so = SLOT_OFFSET[slot];
              const boxX =
                slot === "DEFAULT"
                  ? point.x + 12
                  : so.dx > 0
                    ? point.x + 34
                    : point.x - 34 - calloutW;
              const boxY = slot === "DEFAULT" ? point.y + 4 : point.y - 6 - so.dy * 34 - calloutH;
              const leaderEnd =
                so.dx > 0
                  ? { x: boxX, y: boxY + calloutH }
                  : { x: boxX + calloutW, y: boxY + calloutH };

              return (
                <g
                  key={entry.vehicleId}
                  data-vehicle-id={entry.vehicleId}
                  data-own-vehicle={own ? "true" : undefined}
                  data-selected={isSelected ? "true" : undefined}
                  data-route-id={entry.routeId ?? undefined}
                  onClick={onSelectVehicle ? () => onSelectVehicle(entry.vehicleId) : undefined}
                  style={onSelectVehicle ? { cursor: "pointer" } : undefined}
                >
                  {own ? (
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={15}
                      fill="none"
                      stroke="#f0f6fc"
                      strokeWidth={2}
                    />
                  ) : isSelected ? (
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={15}
                      fill="none"
                      stroke={SELECT}
                      strokeWidth={2.2}
                      strokeDasharray="4 2"
                    />
                  ) : null}

                  {/* Heading indicator ONLY if canonical heading exists */}
                  {hasHeading ? (
                    <line
                      x1={point.x}
                      y1={point.y}
                      x2={point.x + 22 * Math.cos(entry.headingRad as number)}
                      y2={point.y - 22 * Math.sin(entry.headingRad as number)}
                      stroke={isSelected ? SELECT : fill}
                      strokeWidth={2}
                      strokeLinecap="round"
                    />
                  ) : null}

                  {/* Top-down truck symbol: tray, cab, oriented by heading when known */}
                  <g
                    transform={`translate(${point.x.toFixed(1)} ${point.y.toFixed(1)}) rotate(${deg.toFixed(1)})`}
                  >
                    <rect
                      x={-8}
                      y={-4.5}
                      width={11}
                      height={9}
                      rx={1}
                      fill={fill}
                      stroke="#0b0f14"
                      strokeWidth={1.2}
                    />
                    <rect
                      x={3}
                      y={-3.5}
                      width={5}
                      height={7}
                      rx={1}
                      fill="#7c4a0c"
                      stroke="#0b0f14"
                      strokeWidth={1}
                    />
                    <rect x={-6.5} y={-3} width={8} height={6} fill="rgba(0,0,0,0.35)" />
                  </g>

                  {/* Short tag beside the symbol; full identity in the callout. */}
                  <text
                    x={point.x + 12}
                    y={point.y - 10}
                    fill="#f8fafc"
                    fontSize={12}
                    fontWeight={800}
                    letterSpacing="0.08em"
                  >
                    {shortId(entry.vehicleId)}
                  </text>

                  {slot !== "DEFAULT" ? (
                    <polyline
                      points={`${point.x.toFixed(1)},${point.y.toFixed(1)} ${leaderEnd.x.toFixed(1)},${leaderEnd.y.toFixed(1)}`}
                      fill="none"
                      stroke={isSelected ? SELECT : "rgba(248,250,252,0.55)"}
                      strokeWidth={1}
                      data-callout-leader={entry.vehicleId}
                    />
                  ) : null}
                  <rect
                    x={boxX}
                    y={boxY}
                    width={calloutW}
                    height={calloutH}
                    rx={2}
                    fill="rgba(11, 15, 20, 0.88)"
                    stroke={isSelected ? SELECT : "rgba(255, 255, 255, 0.18)"}
                    strokeWidth={1}
                    data-callout-slot={slot}
                  />
                  <text
                    x={boxX + 4}
                    y={boxY + 12}
                    fill="#f0f6fc"
                    fontSize={10.5}
                    fontWeight={own || isSelected ? 700 : 400}
                  >
                    {fullText}
                  </text>
                  {isSelected ? (
                    <text
                      x={boxX + 4}
                      y={boxY + 24}
                      fill={SELECT}
                      fontSize={10}
                      fontFamily="ui-monospace, monospace"
                      data-route-state={entry.vehicleId}
                    >
                      {routeLine}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </g>

          {/* NORTH ARROW + SCALE BAR + IN-PLAN LEGEND */}
          <g aria-label="North" transform={`translate(${VIEW_W - 34} 40)`}>
            <polygon points="0,-16 6,6 0,2 -6,6" fill="#e2e8f0" />
            <text x={0} y={20} fill="#e2e8f0" fontSize={11} fontWeight={800} textAnchor="middle">
              N
            </text>
          </g>
          <g
            aria-label="Scale bar"
            transform={`translate(${extentBox.x + 8} ${VIEW_H - 26})`}
            data-scale-metres={bar.metres}
          >
            <rect x={0} y={0} width={bar.px} height={4} fill="#e2e8f0" />
            <rect
              x={0}
              y={0}
              width={bar.px / 2}
              height={4}
              fill="#0b0f15"
              stroke="#e2e8f0"
              strokeWidth={0.8}
            />
            <text x={0} y={-5} fill="#cbd5e1" fontSize={10} fontFamily="ui-monospace, monospace">
              {`0 — ${bar.metres} m · SCENE_METRES · SYNTHETIC SCALE`}
            </text>
          </g>
          <g
            aria-label="Plan legend"
            transform={`translate(${VIEW_W - 204} ${VIEW_H - 122})`}
            fontSize={9.5}
            fill="#cbd5e1"
          >
            <rect
              x={-6}
              y={-14}
              width={200}
              height={112}
              fill="rgba(11,15,21,0.85)"
              stroke="rgba(148,163,184,0.25)"
            />
            <rect x={0} y={-4} width={14} height={6} fill={ROAD_FILL.MAIN_HAUL} />
            <text x={20} y={2}>
              HAUL ROAD · SYN
            </text>
            <polyline points="0,10 14,10" stroke="#94a3b8" strokeWidth={1.2} />
            <text x={20} y={13}>
              BENCH CREST · SYN MODEL
            </text>
            <rect
              x={0}
              y={18}
              width={14}
              height={6}
              fill="url(#cr-dots-active)"
              stroke="#f59e0b"
              strokeWidth={0.6}
            />
            <text x={20} y={24}>
              ACTIVE WORKING AREA
            </text>
            <rect
              x={0}
              y={29}
              width={14}
              height={6}
              fill="url(#cr-hatch-stock)"
              stroke="#d9846a"
              strokeWidth={0.6}
            />
            <text x={20} y={35}>
              ORE STOCKPILE · DISPATCH
            </text>
            <rect
              x={0}
              y={40}
              width={14}
              height={6}
              fill="url(#cr-hatch-dump)"
              stroke="#9aa0a8"
              strokeWidth={0.6}
            />
            <text x={20} y={46}>
              WASTE DUMP (TERRACED)
            </text>
            <polyline points="0,54 14,54" stroke="#22d3ee" strokeWidth={1} strokeDasharray="4 2" />
            <text x={20} y={57}>
              DRAINAGE · SYN
            </text>
            <polyline points="0,65 14,65" stroke="#6b7280" strokeWidth={1} strokeDasharray="4 2" />
            <text x={20} y={68}>
              SITE ACCESS CONTEXT (OSM)
            </text>
            <rect x={0} y={73} width={14} height={6} fill="none" stroke="#38bdf8" strokeWidth={1} />
            <text x={20} y={79}>
              PUBLISHED EXTENT · NOT A BOUNDARY
            </text>
            <rect x={2} y={85} width={9} height={6} fill="#f59e0b" />
            <text x={20} y={90}>
              TRUCK · TWIN SCENE POSE
            </text>
          </g>
          </g>
        </svg>

        {/* Legend drawer — every drawn layer names its provenance chain in words. */}
        <details className="cr-legend-drawer">
          <summary className="faint">
            PLAN LAYERS &amp; PROVENANCE (
            {plan.corridors.length + plan.features.length + plan.zones.length + drawable.length})
          </summary>
          <dl className="fields">
            <div className="field">
              <dt>Synthetic haul routes ({plan.corridors.length})</dt>
              <dd>
                {plan.corridors.map((c) => `${c.id} · ${c.planLabel}`).join(" · ")} —
                SYNTHETIC_DIGITAL_TWIN_ROUTE · NOT SURVEYED · NOT NMDC INFRASTRUCTURE
              </dd>
            </div>
            <div className="field">
              <dt>Vehicle routes ({plan.routes.length})</dt>
              <dd>
                {plan.routes
                  .map((r) => `${r.routeId} (${r.behaviour}, ${(r.lengthM / 1000).toFixed(1)} km)`)
                  .join(" · ")}{" "}
                — SIMULATION · SIMULATED_TWIN_SCENE · SCENE_METRES
              </dd>
            </div>
            <div className="field">
              <dt>Pit, benches, floor ({plan.features.length})</dt>
              <dd>
                {PLAN_DISCLOSURE.benches} — display levels about an invented datum, not surveyed
                bench elevations
              </dd>
            </div>
            <div className="field">
              <dt>Operational zones ({plan.zones.length})</dt>
              <dd>
                ACTIVE WORKING AREA · ORE STOCKPILE · WASTE DUMP — SYNTHETIC — DEMONSTRATION ONLY
              </dd>
            </div>
            <div className="field">
              <dt>Contours &amp; drainage</dt>
              <dd>
                Contours of the synthetic elevation field at 5 m; drainage lines invented for
                context. Not a survey.
              </dd>
            </div>
            {drawable.map((layer) => (
              <div className="field" key={layer.id}>
                <dt>{layer.name}</dt>
                <dd>{GEO_PROVENANCE_TEXT[layer.provenance]}</dd>
              </div>
            ))}
          </dl>
        </details>
      </div>

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
        Synthetic demonstration geometry is invented and is NOT NMDC infrastructure. No official
        NMDC haul-road, crusher, stockpile or dump geometry is claimed. Physical NMDC mine
        integration is NOT VERIFIED and real vehicle positioning is NOT VERIFIED.
      </p>
    </Panel>
  );
}
