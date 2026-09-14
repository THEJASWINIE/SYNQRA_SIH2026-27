/**
 * Mine geometry overlay — bench shelves, bench faces, the floor, and subtle edges.
 *
 * Pass 3B-M2: the benches are drawn as SURFACES with area - a light shelf, a dark face,
 * a light floor - draped on the terrain mesh, so the excavation reads as shelf / face /
 * shelf / face rather than as contour lines over a bowl. The crest polylines from
 * `mineFeatures.ts` remain, but only as faint edges: they are no longer the primary
 * representation of a bench. A shelf the ramp crosses is genuinely interrupted, because
 * the strips stop at the ramp corridor.
 *
 * ==========================================================================
 *  DRAWN IN A MUTED, DELIBERATELY UNAUTHORITATIVE STYLE.
 *
 *  Everything here is SYNTHETIC_FOR_DEMO. Surfaces are near-grey and translucent; edges
 *  are faint. No saturated colour - that is reserved for real operational state in a
 *  later pass. Every feature carries its own `source` / `verified` / `confidence`.
 *
 *  Nothing here is NMDC survey data and nothing here is labelled as such.
 * ==========================================================================
 *
 * Every vertex is draped on `gridElevationAt` - the mesh's own triangulation - with the
 * SAME disclosed vertical exaggeration the terrain uses, so a shelf lies on its bench
 * and a face spans its riser exactly as drawn.
 *
 * WebGL only. Not unit tested - the geometry it consumes is asserted in the tests of
 * `mineFeatures.ts` and `pitMorphology.ts`.
 */

import { useMemo } from "react";
import {
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshStandardMaterial,
} from "three";

import type { BenchSurface, BenchSurfaceKind, MineFeature, ScenePoint } from "./mineFeatures";
import { gridElevationAt, type HeightGrid } from "./terrainField";

/** Edges sit a little above the surface so they do not z-fight the mesh. */
const EDGE_LIFT_M = 3;
/** Surfaces sit a hair above the terrain; polygon offset settles the rest. */
const SURFACE_LIFT_M = 1.5;

/** Neutral surface tints. Shelves and floor lighter than ground, faces darker. */
const SURFACE_COLOUR: Record<BenchSurfaceKind, number> = {
  SHELF: 0x8e887f,
  FACE: 0x1d1a18,
  FLOOR_SURFACE: 0x938d84,
};

const SURFACE_OPACITY: Record<BenchSurfaceKind, number> = {
  SHELF: 0.28,
  FACE: 0.42,
  FLOOR_SURFACE: 0.3,
};

function drapedY(grid: HeightGrid, x: number, y: number, liftM: number): number {
  return gridElevationAt(grid, x, y) * grid.verticalExaggeration + liftM;
}

function drapedPolyline(
  points: readonly ScenePoint[],
  grid: HeightGrid,
  colour: number,
  opacity: number,
): Line {
  const positions = new Float32Array(points.length * 3);
  points.forEach((point, index) => {
    positions[index * 3] = point.x;
    positions[index * 3 + 1] = drapedY(grid, point.x, point.y, EDGE_LIFT_M);
    positions[index * 3 + 2] = point.y;
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  return new Line(geometry, new LineBasicMaterial({ color: colour, transparent: true, opacity }));
}

/** One mesh per surface: every strip's quads, draped on the drawn terrain. */
function surfaceMesh(surface: BenchSurface, grid: HeightGrid): Mesh {
  const positions: number[] = [];
  const indices: number[] = [];

  for (const strip of surface.strips) {
    const base = positions.length / 3;
    for (let i = 0; i < strip.outer.length; i += 1) {
      const o = strip.outer[i] as ScenePoint;
      const n = strip.inner[i] as ScenePoint;
      positions.push(o.x, drapedY(grid, o.x, o.y, SURFACE_LIFT_M), o.y);
      positions.push(n.x, drapedY(grid, n.x, n.y, SURFACE_LIFT_M), n.y);
    }
    for (let i = 0; i < strip.outer.length - 1; i += 1) {
      const o0 = base + i * 2;
      const n0 = o0 + 1;
      const o1 = o0 + 2;
      const n1 = o0 + 3;
      indices.push(o0, n0, o1, o1, n0, n1);
    }
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  geometry.setIndex(new BufferAttribute(new Uint32Array(indices), 1));
  geometry.computeVertexNormals();

  return new Mesh(
    geometry,
    new MeshStandardMaterial({
      color: SURFACE_COLOUR[surface.kind],
      transparent: true,
      opacity: SURFACE_OPACITY[surface.kind],
      roughness: 1,
      metalness: 0,
      side: DoubleSide,
      depthWrite: false,
      // Tie-break toward the overlay where it is coplanar with the ground. It must not
      // let a shelf show through a wall, and it does not.
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
    }),
  );
}

function FeatureEdges({ feature, grid }: { feature: MineFeature; grid: HeightGrid }) {
  const lines = useMemo(() => {
    const colour = feature.kind === "PIT" ? 0x9aa3ae : feature.kind === "FLOOR" ? 0x8a9199 : 0x777d85;
    // Faint: the surfaces carry the bench now, the crest is only an edge cue.
    const opacity = feature.kind === "PIT" ? 0.7 : 0.3;
    return feature.segments.map((segment) => drapedPolyline(segment, grid, colour, opacity));
  }, [feature, grid]);

  return (
    <group>
      {lines.map((line, index) => (
        <primitive key={`${feature.id}-${index}`} object={line} />
      ))}
    </group>
  );
}

function SurfacePatch({ surface, grid }: { surface: BenchSurface; grid: HeightGrid }) {
  const mesh = useMemo(() => surfaceMesh(surface, grid), [surface, grid]);
  return <primitive object={mesh} />;
}

export function MineGeometryOverlay({
  features,
  surfaces,
  grid,
  showPit = true,
  showBenches = true,
}: {
  features: readonly MineFeature[];
  surfaces: readonly BenchSurface[];
  /** The rendered terrain the geometry is draped on. */
  grid: HeightGrid;
  showPit?: boolean;
  showBenches?: boolean;
}) {
  return (
    <group>
      {surfaces.map((surface) => {
        // The floor belongs to the pit layer; shelves and faces are the bench layer.
        const isPitLayer = surface.kind === "FLOOR_SURFACE";
        if (isPitLayer && !showPit) return null;
        if (!isPitLayer && !showBenches) return null;
        return <SurfacePatch key={surface.id} surface={surface} grid={grid} />;
      })}
      {features.map((feature) => {
        const isPitLayer = feature.kind === "PIT" || feature.kind === "FLOOR";
        if (isPitLayer && !showPit) return null;
        if (!isPitLayer && !showBenches) return null;
        return <FeatureEdges key={feature.id} feature={feature} grid={grid} />;
      })}
    </group>
  );
}
