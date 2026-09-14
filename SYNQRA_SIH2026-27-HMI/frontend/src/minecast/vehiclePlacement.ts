/**
 * Vehicle placement on the terrain — the vertical, and nothing else (MINECAST-02).
 *
 * The Twin supplies scene X/Y. The scene supplies the ground. This module joins them:
 *
 *     scene X/Y  ->  terrain surface lookup  ->  terrain Z  ->  truck Z = terrain Z + clearance
 *
 * `gridElevationAt` samples the exact triangulation the GPU rasterises, so a truck sits
 * on the drawn ground rather than on the continuous field it was sampled from (the two
 * differ by metres at a bench riser). The clearance is the one explicit constant: enough
 * to keep the box's underside from z-fighting the surface, small enough that a truck never
 * reads as floating.
 *
 * Pure and framework-free, so "not floating, not underground" is a unit test rather than
 * a screenshot.
 */

import { gridElevationAt, type HeightGrid } from "./terrainField";

/** TRUE metres above the sampled terrain. Kept small on purpose. */
export const VEHICLE_CLEARANCE_M = 0.6;

/** The terrain surface height, in DRAW units, under a scene X/Y. */
export function terrainSurfaceY(grid: HeightGrid, x: number, y: number): number {
  return gridElevationAt(grid, x, y) * grid.verticalExaggeration;
}

/** Where a vehicle's underside sits, in DRAW units: the surface plus the clearance. */
export function vehicleSurfaceY(grid: HeightGrid, x: number, y: number): number {
  return terrainSurfaceY(grid, x, y) + VEHICLE_CLEARANCE_M * grid.verticalExaggeration;
}
