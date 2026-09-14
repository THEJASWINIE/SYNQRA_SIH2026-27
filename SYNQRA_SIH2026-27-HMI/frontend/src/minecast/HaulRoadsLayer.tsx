/**
 * Corridor renderer — ribbons for the synthetic haul-road network.
 *
 * ==========================================================================
 *  DRAWS INVENTED ROADS, AND LOOKS LIKE IT.
 *
 *  Every corridor this draws is SYNTHETIC_FOR_DEMO. The styling is deliberately
 *  restrained - a matte surface a shade lighter than the ground, with two thin edge
 *  lines - so the network reads as operational context, not as an authoritative map
 *  layer. No glow and no colour: saturated colour is reserved for Twin-supplied
 *  operational state, and a road that is merely present has no state to show. The only
 *  emphasis is the selected truck's route (a UI selection, drawn lighter) and the
 *  ROUTES layer's engineering labels, each stamped SYN for synthetic.
 * ==========================================================================
 *
 * The geometry is computed by `corridorRibbon` in the pure module, so the vertex maths is
 * under test; this file only uploads it. Built once per corridor and memoised.
 *
 * WebGL only. Not unit tested (M4D-C).
 */

import { Html } from "@react-three/drei";
import { useMemo } from "react";
import {
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  Line,
  LineBasicMaterial,
  LineDashedMaterial,
  Mesh,
  MeshStandardMaterial,
} from "three";

import { type CorridorKind, corridorRibbon, type HaulCorridor } from "./haulRoads";
import { gridElevationAt, type HeightGrid } from "./terrainField";

/**
 * Surface tints per kind (MINECAST-03).
 *
 * The project's amber ACCENT family - the same hue the Instrument Deck uses for the
 * published-extent outline and the panel ticks - so a corridor reads as an operational
 * element against the grey landform rather than as more terrain. Amber is the deck's
 * accent, not a safety state: red / green / cyan stay reserved for FOG state passes,
 * and no corridor is coloured by any speed or status value, because none exists.
 */
const SURFACE: Record<CorridorKind, number> = {
  MAIN_HAUL: 0xb8812f,
  RAMP: 0xc9924a,
  LOADING_LOOP: 0xa8823c,
  DISPATCH: 0x9a6f2e,
  SERVICE: 0x8a7150,
};

/** Edge line tints: bright accent, so the ribbon's outline holds at overview scale. */
const EDGE: Record<CorridorKind, number> = {
  MAIN_HAUL: 0xf2a54a,
  RAMP: 0xf7b86a,
  LOADING_LOOP: 0xf0c070,
  DISPATCH: 0xe0973f,
  SERVICE: 0xcdb48a,
};

/** The selected truck's route: its corridors are lifted to this bright amber. */
const HIGHLIGHT = 0xf5c04a;

/** Centreline tint: a light neutral, so the direction of the corridor reads on any tint. */
const CENTRELINE = 0xf0f6fc;

/** Metres the centreline is lifted above the ribbon, so the dashes never z-fight it. */
const CENTRELINE_LIFT_M = 1.5;

/** Metres the ribbon is lifted above the terrain, so it never z-fights the surface. */
const LIFT_M = 4;

function polyline(flat: readonly number[], colour: number): Line {
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(flat), 3));
  return new Line(geometry, new LineBasicMaterial({ color: colour, transparent: true, opacity: 0.95 }));
}

/**
 * The corridor's own centreline as a dashed line, draped exactly where the ribbon is.
 *
 * Direction-of-travel is the dash rhythm along the polyline; it invents no arrow, no
 * flow and no state. Dashes need `computeLineDistances`, or nothing is drawn at all.
 */
function centreline(road: HaulCorridor, grid: HeightGrid): Line {
  const flat: number[] = [];
  for (const point of road.centreline) {
    flat.push(
      point.x,
      gridElevationAt(grid, point.x, point.y) * grid.verticalExaggeration + LIFT_M + CENTRELINE_LIFT_M,
      point.y,
    );
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(flat), 3));
  const line = new Line(
    geometry,
    new LineDashedMaterial({
      color: CENTRELINE,
      dashSize: 22,
      gapSize: 16,
      transparent: true,
      opacity: 0.85,
    }),
  );
  line.computeLineDistances();
  return line;
}

function CorridorRibbon({
  road,
  grid,
  highlighted,
  emphasis,
  labelled,
}: {
  road: HaulCorridor;
  grid: HeightGrid;
  /** On the selected truck's route. */
  highlighted: boolean;
  /** HAUL ROUTES emphasis: brighter ribbon. */
  emphasis: boolean;
  /** ROUTES layer: the engineering label at the corridor's midpoint. */
  labelled: boolean;
}) {
  const { surface, left, right, centre, mid } = useMemo(() => {
    // Draped on the MESH's interpolation, so the ribbon follows the surface that is drawn.
    const ribbon = corridorRibbon(road, grid.verticalExaggeration, LIFT_M, (x, y) =>
      gridElevationAt(grid, x, y),
    );

    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(new Float32Array(ribbon.positions), 3));
    geometry.setIndex(new BufferAttribute(new Uint32Array(ribbon.indices), 1));
    geometry.computeVertexNormals();

    const tint = highlighted ? HIGHLIGHT : SURFACE[road.kind];
    const surfaceMesh = new Mesh(
      geometry,
      new MeshStandardMaterial({
        color: tint,
        // A little self-illumination so the ribbon stays readable on the shaded pit
        // wall side, where a purely lit surface fell into the same grey as the rock.
        emissive: tint,
        emissiveIntensity: highlighted ? 0.55 : emphasis ? 0.42 : 0.28,
        roughness: 0.9,
        metalness: 0,
        // Both faces, so a ramp seen from below the rim is not culled away.
        side: DoubleSide,
        // Depth bias toward the camera. Where the ribbon is all but coplanar with the
        // ground, this decides the tie in the road's favour instead of leaving it to
        // z-fighting. It does not (and must not) let a road show through a pit wall.
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2,
      }),
    );

    const midPoint = road.centreline[Math.floor(road.centreline.length / 2)] as {
      x: number;
      y: number;
    };
    const edge = highlighted ? HIGHLIGHT : EDGE[road.kind];
    return {
      surface: surfaceMesh,
      left: polyline(ribbon.leftEdge, edge),
      right: polyline(ribbon.rightEdge, edge),
      centre: centreline(road, grid),
      mid: [
        midPoint.x,
        gridElevationAt(grid, midPoint.x, midPoint.y) * grid.verticalExaggeration + LIFT_M + 30,
        midPoint.y,
      ] as const,
    };
  }, [road, grid, highlighted, emphasis]);

  return (
    <group>
      <primitive object={surface} />
      <primitive object={left} />
      <primitive object={right} />
      <primitive object={centre} />
      {labelled ? (
        <Html position={[mid[0], mid[1], mid[2]]} center zIndexRange={[20, 0]} style={{ pointerEvents: "none" }}>
          <div className={`mc-route-label${highlighted ? " mc-route-label-hl" : ""}`} data-corridor-id={road.id}>
            {road.planLabel}
            <span className="mc-route-label-syn">SYN</span>
          </div>
        </Html>
      ) : null}
    </group>
  );
}

export function HaulRoadsLayer({
  corridors,
  grid,
  showHaulRoads,
  showRamps,
  showRouteLabels = false,
  emphasis = false,
  highlightCorridorIds = [],
}: {
  corridors: readonly HaulCorridor[];
  /** The rendered terrain, whose interpolation and vertical exaggeration the ribbons follow. */
  grid: HeightGrid;
  /** HAUL_ROADS layer: every corridor but the ramp. */
  showHaulRoads: boolean;
  /** RAMPS layer: the pit ramp. Independent, so the two can be compared. */
  showRamps: boolean;
  /** ROUTES layer: engineering labels at corridor midpoints. */
  showRouteLabels?: boolean;
  /** HAUL ROUTES emphasis from the console: brighter ribbons. */
  emphasis?: boolean;
  /** Corridors on the selected truck's route (from the Twin's route id), drawn lighter. */
  highlightCorridorIds?: readonly string[];
}) {
  return (
    <group>
      {corridors.map((road) => {
        const isRamp = road.kind === "RAMP";
        if (isRamp && !showRamps) return null;
        if (!isRamp && !showHaulRoads) return null;
        return (
          <CorridorRibbon
            key={road.id}
            road={road}
            grid={grid}
            highlighted={highlightCorridorIds.includes(road.id)}
            emphasis={emphasis}
            labelled={showRouteLabels}
          />
        );
      })}
    </group>
  );
}
