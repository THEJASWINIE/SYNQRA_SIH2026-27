/**
 * Canonical scene corridors and pit geometry — shared between Control Room S1 and Mine-Cast.
 *
 * ==========================================================================
 *  ONE GEOMETRY SOURCE, TWO CLIENTS (2D S1 & 3D MINE-CAST)
 *
 *  Neither S1 nor Mine-Cast invents or approximates its own roads. Both consume the exact
 *  same pure TypeScript functions:
 *    - haulCorridors()   from src/minecast/haulRoads.ts
 *    - mineFeatures()    from src/minecast/mineFeatures.ts
 *    - terrainConfig()   from src/minecast/terrainField.ts
 *
 *  All coordinates are SCENE_METRES east/north of the published extent's south-west corner.
 *  S1 maps them to SVG pixels using the exact same unprojectFromLocalMetres transformation
 *  used for canonical vehicle positions (twinScenePosition in vehiclePosition.ts).
 *  This guarantees pixel-level alignment between drawn corridors and vehicle markers.
 * ==========================================================================
 *
 * PROVENANCE & DISCLOSURES
 *
 * Every corridor and feature is explicitly SYNTHETIC_FOR_DEMO.
 * Not NMDC infrastructure. Not surveyed.
 *
 * Framework-free: no Three.js, no React, no DOM. Pure maths and contracts.
 */

import {
  type CorridorClassification,
  type CorridorKind,
  type CorridorPoint,
  CORRIDOR_DISCLOSURE,
  CORRIDOR_PROVENANCE,
  type HaulCorridor,
  haulCorridors,
} from "../minecast/haulRoads";
import {
  type MineFeature,
  type MineFeatureKind,
  mineFeatures,
  type ScenePoint,
  SYNTHETIC_GEOMETRY_PROVENANCE,
} from "../minecast/mineFeatures";
import { type TerrainConfig, terrainConfig } from "../minecast/terrainField";
import {
  type DecimalExtent,
  extentSizeMetres,
  type LonLat,
  type SiteExtent,
  toDecimalExtent,
  unprojectFromLocalMetres,
} from "./geoSite";

export {
  CORRIDOR_DISCLOSURE,
  CORRIDOR_PROVENANCE,
  SYNTHETIC_GEOMETRY_PROVENANCE,
  type CorridorClassification,
  type CorridorKind,
  type CorridorPoint,
  type HaulCorridor,
  type MineFeature,
  type MineFeatureKind,
  type ScenePoint,
  type TerrainConfig,
};

export interface CanonicalSceneData {
  readonly config: TerrainConfig;
  readonly size: { widthM: number; heightM: number };
  readonly corridors: readonly HaulCorridor[];
  readonly features: readonly MineFeature[];
  readonly decimalExtent: DecimalExtent;
}

/**
 * Normalise any extent representation (DMS SiteExtent or DecimalExtent) into DecimalExtent.
 */
export function resolveDecimalExtent(extent: SiteExtent | DecimalExtent): DecimalExtent {
  if (
    typeof (extent as DecimalExtent).north === "number" &&
    typeof (extent as DecimalExtent).south === "number" &&
    typeof (extent as DecimalExtent).east === "number" &&
    typeof (extent as DecimalExtent).west === "number"
  ) {
    return extent as DecimalExtent;
  }
  return toDecimalExtent(extent as SiteExtent);
}

/**
 * Compute the authoritative scene corridors and pit features for a given site extent.
 *
 * Uses the exact same terrainConfig(size.widthM, size.heightM) derivation as Mine-Cast's
 * MineCanvas.tsx.
 */
export function getSceneCorridors(extent: SiteExtent | DecimalExtent): CanonicalSceneData {
  const decimalExtent = resolveDecimalExtent(extent);
  const size = extentSizeMetres(decimalExtent);
  const config = terrainConfig(size.widthM, size.heightM);

  return {
    config,
    size,
    corridors: haulCorridors(config),
    features: mineFeatures(config),
    decimalExtent,
  };
}

/**
 * Convert a SCENE_METRES point { x, y } (origin at extent south-west) into LonLat.
 * Matches the exact unprojectFromLocalMetres logic in twinScenePosition.
 */
export function scenePointToLonLat(
  point: { x: number; y: number },
  extent: DecimalExtent,
): LonLat {
  const southWest: LonLat = { lon: extent.west, lat: extent.south };
  return unprojectFromLocalMetres(point, southWest);
}

export interface ProjectedPoint {
  readonly x: number;
  readonly y: number;
}

/**
 * Project a corridor centreline into 2D SVG canvas points.
 */
export function projectCorridorCentreline(
  corridor: HaulCorridor,
  extent: DecimalExtent,
  project: (lonLat: LonLat) => ProjectedPoint,
): ProjectedPoint[] {
  return corridor.centreline.map((pt) => {
    const lonLat = scenePointToLonLat({ x: pt.x, y: pt.y }, extent);
    return project(lonLat);
  });
}

/**
 * Project all segments of a mine feature into 2D SVG canvas points.
 */
export function projectFeatureSegments(
  feature: MineFeature,
  extent: DecimalExtent,
  project: (lonLat: LonLat) => ProjectedPoint,
): ProjectedPoint[][] {
  return feature.segments.map((segment) =>
    segment.map((pt) => {
      const lonLat = scenePointToLonLat({ x: pt.x, y: pt.y }, extent);
      return project(lonLat);
    }),
  );
}
