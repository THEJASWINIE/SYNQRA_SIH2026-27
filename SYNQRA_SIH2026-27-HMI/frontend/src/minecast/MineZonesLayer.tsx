/**
 * Zone renderer — the active working area, the ore stockpile and the terraced waste dump,
 * draped on the terrain as tinted patches with outlines.
 *
 * DRAWS INVENTED ZONES, AND LOOKS LIKE IT. Every polygon comes from `mineZones` (pure,
 * SYNTHETIC_FOR_DEMO). The dump and stockpile mounds are already IN the terrain field, so
 * this layer only tints them; the tier outlines sit on the steps the landform actually has.
 *
 * Geometry: each outline is star-shaped about its centre, so a fan from the centre is a
 * valid triangulation. Elevations come from the rendered mesh's own interpolation.
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
  Mesh,
  MeshStandardMaterial,
} from "three";

import type { MineZone, MineZoneKind, ZonePoint } from "./mineZones";
import { gridElevationAt, type HeightGrid } from "./terrainField";

/** Tints per kind: ore is iron-red, waste is grey-brown, the working area is the amber accent. */
const FILL: Record<MineZoneKind, number> = {
  ACTIVE_AREA: 0xf59e0b,
  STOCKPILE: 0x9c4a3a,
  WASTE_DUMP: 0x6e6a63,
};
const OPACITY: Record<MineZoneKind, number> = {
  ACTIVE_AREA: 0.22,
  STOCKPILE: 0.5,
  WASTE_DUMP: 0.45,
};
const EDGE: Record<MineZoneKind, number> = {
  ACTIVE_AREA: 0xf59e0b,
  STOCKPILE: 0xd9846a,
  WASTE_DUMP: 0xb4b0a8,
};

/** Metres above the surface, so a patch never z-fights the ground it tints. */
const LIFT_M = 2.5;

function draped(p: ZonePoint, grid: HeightGrid, lift: number): [number, number, number] {
  return [p.x, gridElevationAt(grid, p.x, p.y) * grid.verticalExaggeration + lift, p.y];
}

function fan(
  polygon: readonly ZonePoint[],
  centre: ZonePoint,
  grid: HeightGrid,
  lift: number,
): Mesh {
  const ring = polygon.slice(0, -1);
  const positions: number[] = [...draped(centre, grid, lift)];
  for (const p of ring) positions.push(...draped(p, grid, lift));
  const indices: number[] = [];
  for (let i = 0; i < ring.length; i += 1) {
    indices.push(0, 1 + i, 1 + ((i + 1) % ring.length));
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  geometry.setIndex(new BufferAttribute(new Uint32Array(indices), 1));
  geometry.computeVertexNormals();
  return new Mesh(
    geometry,
    new MeshStandardMaterial({
      transparent: true,
      side: DoubleSide,
      roughness: 1,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
    }),
  );
}

function outline(
  polygon: readonly ZonePoint[],
  grid: HeightGrid,
  lift: number,
  colour: number,
): Line {
  const flat: number[] = [];
  for (const p of polygon) flat.push(...draped(p, grid, lift + 1));
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(flat), 3));
  return new Line(
    geometry,
    new LineBasicMaterial({ color: colour, transparent: true, opacity: 0.9 }),
  );
}

function Zone({ zone, grid, labelled }: { zone: MineZone; grid: HeightGrid; labelled: boolean }) {
  const { patches, edges, anchor } = useMemo(() => {
    const built = zone.tiers.map((tier) => {
      const mesh = fan(tier.polygon, zone.centre, grid, LIFT_M);
      const material = mesh.material as MeshStandardMaterial;
      material.color.setHex(FILL[zone.kind]);
      material.emissive.setHex(FILL[zone.kind]);
      material.emissiveIntensity = 0.25;
      material.opacity = OPACITY[zone.kind];
      return mesh;
    });
    const lines = zone.tiers.map((tier) => outline(tier.polygon, grid, LIFT_M, EDGE[zone.kind]));
    const top = zone.tiers[zone.tiers.length - 1]?.liftM ?? 0;
    return { patches: built, edges: lines, anchor: draped(zone.centre, grid, top + 24) };
  }, [zone, grid]);

  return (
    <group>
      {patches.map((mesh, i) => (
        <primitive key={`p${i}`} object={mesh} />
      ))}
      {edges.map((line, i) => (
        <primitive key={`e${i}`} object={line} />
      ))}
      {labelled ? (
        <Html position={anchor} center zIndexRange={[15, 0]} style={{ pointerEvents: "none" }}>
          <div className="mc-zone-label" data-zone-id={zone.id}>
            {zone.planLabel}
            <span className="mc-route-label-syn">SYN</span>
          </div>
        </Html>
      ) : null}
    </group>
  );
}

export function MineZonesLayer({
  zones,
  grid,
  visible,
  labelled = true,
}: {
  zones: readonly MineZone[];
  grid: HeightGrid;
  visible: boolean;
  labelled?: boolean;
}) {
  if (!visible) return null;
  return (
    <group>
      {zones.map((zone) => (
        <Zone key={zone.id} zone={zone} grid={grid} labelled={labelled} />
      ))}
    </group>
  );
}
