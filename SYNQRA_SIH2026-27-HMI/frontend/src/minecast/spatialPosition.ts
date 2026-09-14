/**
 * Spatial position contract — where a vehicle may be drawn, and on whose authority.
 *
 * ==========================================================================
 *  THIS MODULE EXISTS TO REFUSE THINGS.
 *
 *  Pass 3B will draw vehicle markers. Before any marker exists, the question "is this
 *  vehicle's position good enough to draw, and in WHICH frame" has to have exactly one
 *  answer, computed in one place, and testable without a GPU. That is this file.
 *
 *  The refusals it encodes:
 *
 *    * A LOCAL ODOMETRY pose is NEVER converted into a geographic coordinate. There is
 *      no surveyed anchor tying TRUCK_01's odometry origin to the earth, so any latitude
 *      it produced would be invented precision. `lonLat` is null on every odometry path
 *      and there is no code here that fills it.
 *
 *    * A vehicle with no position gets NO scene position. Not (0, 0) - the pit floor is
 *      near the scene origin, so a zero coordinate would park an unlocated truck in the
 *      middle of the mine and look entirely plausible.
 *
 *    * TRUCK_02 is not placed because the scene happens to contain two trucks. It has no
 *      verified position source, so it stays UNAVAILABLE.
 *
 *    * A synthetic placement is reachable only through `syntheticScenePlacement`, is
 *      never the default, and every result it produces is stamped SYNTHETIC_FOR_DEMO and
 *      captioned SOFTWARE TEST · SYNTHETIC SPATIAL PLACEMENT.
 * ==========================================================================
 *
 * TWO FRAMES, AND THEY ARE NOT INTERCHANGEABLE
 *
 *   ODOMETRY_LOCAL_METRES   metres from TRUCK_01's own LOCAL ODOMETRY ORIGIN. Where the
 *                           origin sits in the mine is UNKNOWN, so a pose in this frame
 *                           cannot be drawn on the terrain without an explicit anchor.
 *
 *   SCENE_METRES            metres east/north of the published extent's south-west
 *                           corner - the frame the terrain mesh is built in.
 *
 * Going from the first to the second requires an anchor nobody surveyed. So it is a
 * DEMO transform, isolated behind one function, and labelled.
 *
 * Pure and framework-free - no Three.js, no React, no browser global - so the whole
 * contract is testable in the Node test environment (M4D-C).
 */

import type { DataState } from "../state/dataStatus";
import { type LonLat, projectToLocalMetres, toDecimalExtent } from "../state/geoSite";
import type { MineCastSite, MineCastVehicle } from "./minecastProjection";

// ---------------------------------------------------------------------------
// vocabulary
// ---------------------------------------------------------------------------

/**
 * On whose authority a spatial position may be drawn.
 *
 * Deliberately NOT the same enum as `MineCastProvenance`. That one describes where a
 * VALUE came from; this one describes whether a position is fit to place on a map. A
 * synthetic GNSS fix is `SOFTWARE_TEST` as a value and `SYNTHETIC_FOR_DEMO` as a
 * placement, and collapsing the two would lose exactly the distinction that matters here.
 */
export type SpatialPositionProvenance =
  /** A physical GNSS fix, projected through an established projection. */
  | "VERIFIED_GEOGRAPHIC"
  /** A wheel+IMU pose in its own local frame. Not geographic, not anchored. */
  | "LOCAL_ODOMETRY"
  /** Invented or software-test placement. Never a measurement of a real vehicle. */
  | "SYNTHETIC_FOR_DEMO"
  /** Nothing supplied a position. No marker may be drawn. */
  | "UNAVAILABLE";

export const SPATIAL_PROVENANCE_TEXT: Record<SpatialPositionProvenance, string> = {
  VERIFIED_GEOGRAPHIC: "VERIFIED GEOGRAPHIC — physical fix, projected",
  LOCAL_ODOMETRY: "LOCAL ODOMETRY — relative pose, not geographic",
  SYNTHETIC_FOR_DEMO: "SOFTWARE TEST · SYNTHETIC SPATIAL PLACEMENT",
  UNAVAILABLE: "POSITION UNAVAILABLE — nothing to draw",
};

/** Which coordinate frame a position's numbers are expressed in. */
export type SpatialFrame =
  /** Metres east/north of the published extent's south-west corner. Drawable. */
  | "SCENE_METRES"
  /** Metres from TRUCK_01's local odometry origin. NOT a mine-map coordinate. */
  | "ODOMETRY_LOCAL_METRES"
  /** No frame, because there is no position. */
  | "NONE";

/** The caption a synthetic placement must carry, wherever it is shown. */
export const SYNTHETIC_PLACEMENT_LABEL = "SOFTWARE TEST · SYNTHETIC SPATIAL PLACEMENT";

// ---------------------------------------------------------------------------
// the contract
// ---------------------------------------------------------------------------

export interface SpatialPosition {
  /** Canonical id — TRUCK_01 / TRUCK_02. Never the short display label. */
  readonly canonicalVehicleId: string;
  /** Short spatial label, carried alongside and never used as an identifier. */
  readonly displayId: string;

  readonly provenance: SpatialPositionProvenance;
  readonly frame: SpatialFrame;

  /**
   * True only when a marker may be drawn ON THE TERRAIN.
   *
   * An odometry pose that has no scene anchor is a real position in its own frame and is
   * still NOT drawable - `frame` says which, and `drawableInScene` is the single boolean
   * a renderer should branch on.
   */
  readonly drawableInScene: boolean;

  /**
   * Coordinates in `frame`, or null.
   *
   * Null when there is no position. NEVER zero as a stand-in: the scene origin is real
   * ground, so (0, 0) would place an unlocated vehicle somewhere specific.
   */
  readonly x: number | null;
  readonly y: number | null;
  /** Radians, as supplied. Null when no heading was supplied. */
  readonly headingRad: number | null;

  /**
   * Geographic coordinate, ONLY for a genuinely geographic position.
   *
   * Permanently null for LOCAL_ODOMETRY. There is no code path in this module that
   * derives it from a local pose.
   */
  readonly lonLat: LonLat | null;

  /** The estimator that produced the underlying position. */
  readonly method: string;
  /** Freshness of the underlying position, carried through unchanged. */
  readonly dataState: DataState;
  /** Why this position is drawable, or why it is not. Always populated. */
  readonly reason: string;
  /** True when this placement was invented rather than measured. */
  readonly synthetic: boolean;
}

/** A position that may not be drawn. The default answer. */
function unavailable(
  vehicle: MineCastVehicle,
  reason: string,
  method = "NONE",
  dataState: DataState = "UNAVAILABLE",
): SpatialPosition {
  return {
    canonicalVehicleId: vehicle.canonicalVehicleId,
    displayId: vehicle.displayId,
    provenance: "UNAVAILABLE",
    frame: "NONE",
    drawableInScene: false,
    x: null,
    y: null,
    headingRad: null,
    lonLat: null,
    method,
    dataState,
    reason,
    synthetic: false,
  };
}

/**
 * The one conversion.
 *
 * Total over the three position kinds, with no default branch, so a new kind forces a
 * decision here rather than silently inheriting drawable behaviour.
 *
 * A GEOGRAPHIC fix is projected into scene metres using `projectToLocalMetres`, the
 * projection this application already uses for the site map. That projection is a local
 * equirectangular approximation and the source datum is recorded as
 * ASSUMED_WGS84_UNVERIFIED, so the result is fit for placing a marker on this
 * demonstration terrain and is NOT survey grade. That caveat travels in `reason`.
 */
export function toSpatialPosition(vehicle: MineCastVehicle, site: MineCastSite): SpatialPosition {
  const position = vehicle.position;

  /*
    MINECAST-01 — the canonical Digital Twin demonstration pose.

    Consulted BEFORE the instrument-derived branches below, and deliberately so: a scene
    pose is the only thing either truck has that may be drawn on this terrain. A local
    odometry pose is real but unplaceable (its origin is unsurveyed), and no GNSS exists
    at all, so without this branch the scene stays empty while the Twin knows exactly
    where it is placing both trucks.

    NOTHING IS CONVERTED HERE. The Twin publishes SCENE_METRES - metres east/north of the
    published extent's south-west corner - which is the frame this very module defines and
    the frame the terrain mesh is built in. The numbers are passed through untouched.

    The placement is stamped SYNTHETIC_FOR_DEMO whatever else the vehicle carries, because
    it is invented; the instrument truth is not overwritten, it stays on
    `vehicle.position` and is reported by the vehicle panel beside the scene.
  */
  const scene = vehicle.scenePose;
  if (scene) {
    return {
      canonicalVehicleId: vehicle.canonicalVehicleId,
      displayId: vehicle.displayId,
      provenance: "SYNTHETIC_FOR_DEMO",
      frame: "SCENE_METRES",
      drawableInScene: true,
      x: scene.xM,
      y: scene.yM,
      headingRad: scene.headingRad,
      // A scene coordinate is not a coordinate on the earth. Permanently null.
      lonLat: null,
      method: scene.method,
      dataState: position.dataState,
      reason: `${SYNTHETIC_PLACEMENT_LABEL}. ${scene.reason}`,
      synthetic: true,
    };
  }

  switch (position.kind) {
    case "UNAVAILABLE":
      return unavailable(vehicle, position.reason, position.method, position.dataState);

    case "LOCAL_ODOMETRY": {
      /*
        A real, physically derived pose - in ITS OWN frame.

        It is reported as LOCAL_ODOMETRY with `frame: ODOMETRY_LOCAL_METRES` and
        `drawableInScene: false`, because where the odometry origin sits in the mine is
        not known. Anchoring it is a separate, explicitly synthetic step.
      */
      if (position.xM === null || position.yM === null) {
        return unavailable(
          vehicle,
          "Local odometry supplied no usable pose.",
          position.method,
          position.dataState,
        );
      }

      return {
        canonicalVehicleId: vehicle.canonicalVehicleId,
        displayId: vehicle.displayId,
        provenance: "LOCAL_ODOMETRY",
        frame: "ODOMETRY_LOCAL_METRES",
        drawableInScene: false,
        x: position.xM,
        y: position.yM,
        headingRad: position.headingRad,
        // Never derived from a local pose.
        lonLat: null,
        method: position.method,
        dataState: position.dataState,
        reason:
          "Physically derived local pose, in metres from this vehicle's own odometry origin. " +
          "NOT a geographic coordinate and not anchored to the mine: the origin's location is " +
          "unsurveyed, so no marker is placed on the terrain from it.",
        synthetic: false,
      };
    }

    case "GEOGRAPHIC": {
      const lonLat = position.lonLat;
      if (!lonLat) {
        return unavailable(
          vehicle,
          "Geographic position carried no coordinate.",
          position.method,
          position.dataState,
        );
      }

      // Metres from the extent's south-west corner: the frame the terrain is built in.
      const extent = toDecimalExtent(site.extent);
      const southWest: LonLat = { lon: extent.west, lat: extent.south };
      const scene = projectToLocalMetres(lonLat, southWest);

      /*
        A software-test or simulated fix is geographic but NOT verified. It keeps its
        synthetic provenance all the way to the renderer, so a demo marker can never be
        mistaken for a measured one.
      */
      const synthetic =
        position.provenance === "SOFTWARE_TEST" ||
        position.provenance === "SIMULATION" ||
        position.provenance === "SYNTHETIC_FOR_DEMO" ||
        position.provenance === "REPLAY";

      return {
        canonicalVehicleId: vehicle.canonicalVehicleId,
        displayId: vehicle.displayId,
        provenance: synthetic ? "SYNTHETIC_FOR_DEMO" : "VERIFIED_GEOGRAPHIC",
        frame: "SCENE_METRES",
        drawableInScene: true,
        x: scene.x,
        y: scene.y,
        headingRad: position.headingRad,
        lonLat,
        method: position.method,
        dataState: position.dataState,
        reason: synthetic
          ? `${SYNTHETIC_PLACEMENT_LABEL}. ${position.reason}`
          : "Physical geographic fix, projected into scene metres by the site map's local " +
            "equirectangular projection. Source datum recorded as ASSUMED_WGS84_UNVERIFIED; " +
            "adequate for placement on this demonstration terrain, not survey grade.",
        synthetic,
      };
    }
  }
}

// ---------------------------------------------------------------------------
// the explicitly synthetic escape hatch
// ---------------------------------------------------------------------------

/** Where a demo chooses to pretend a vehicle's local origin sits, in scene metres. */
export interface SyntheticSceneAnchor {
  readonly xM: number;
  readonly yM: number;
  /** Rotation applied to the local frame before placing it, radians. */
  readonly rotationRad?: number;
}

/**
 * Anchor a LOCAL ODOMETRY pose into the scene, for demonstration only.
 *
 * ==========================================================================
 *  CALLING THIS IS A CHOICE TO SHOW SOMETHING INVENTED.
 *
 *  The transform needs to know where TRUCK_01's odometry origin sits in the mine. Nobody
 *  surveyed that. So the anchor is supplied by the CALLER, the result is stamped
 *  SYNTHETIC_FOR_DEMO regardless of how real the underlying pose was, and its reason
 *  carries SOFTWARE TEST · SYNTHETIC SPATIAL PLACEMENT.
 *
 *  The odometry itself stays physically derived - that fact is preserved in
 *  `underlyingProvenance` and `method` - but the PLACEMENT is not a measurement, and the
 *  provenance a renderer reads reflects the weaker of the two. There is deliberately no
 *  way to obtain a drawable position from odometry without going through this function.
 * ==========================================================================
 *
 * Anything that is not an unanchored local pose is returned unchanged, so this can never
 * upgrade an UNAVAILABLE position into a drawable one.
 */
export function syntheticScenePlacement(
  position: SpatialPosition,
  anchor: SyntheticSceneAnchor,
): SpatialPosition & { readonly underlyingProvenance: SpatialPositionProvenance } {
  if (position.provenance !== "LOCAL_ODOMETRY" || position.x === null || position.y === null) {
    // Nothing to anchor. An absent position must not become a placed one.
    return { ...position, underlyingProvenance: position.provenance };
  }

  const rotation = anchor.rotationRad ?? 0;
  const cos = Math.cos(rotation);
  const sin = Math.sin(rotation);

  return {
    ...position,
    provenance: "SYNTHETIC_FOR_DEMO",
    frame: "SCENE_METRES",
    drawableInScene: true,
    x: anchor.xM + position.x * cos - position.y * sin,
    y: anchor.yM + position.x * sin + position.y * cos,
    headingRad: position.headingRad === null ? null : position.headingRad + rotation,
    // Still not geographic. Anchoring to a demo scene creates no coordinate on the earth.
    lonLat: null,
    reason:
      `${SYNTHETIC_PLACEMENT_LABEL}. A physically derived local pose has been placed at a ` +
      "CHOSEN scene anchor because the odometry origin's real location is unsurveyed. " +
      "The pose is real; this position on the map is not.",
    synthetic: true,
    underlyingProvenance: "LOCAL_ODOMETRY",
  };
}

// ---------------------------------------------------------------------------
// fleet helpers
// ---------------------------------------------------------------------------

/** Spatial positions for the whole fleet, in the projection's own order. */
export function spatialPositions(
  vehicles: readonly MineCastVehicle[],
  site: MineCastSite,
): readonly SpatialPosition[] {
  return vehicles.map((vehicle) => toSpatialPosition(vehicle, site));
}

/** Only the positions a renderer may actually draw on the terrain. */
export function drawablePositions(
  positions: readonly SpatialPosition[],
): readonly SpatialPosition[] {
  return positions.filter((position) => position.drawableInScene);
}

/**
 * Vehicles that exist but cannot be drawn, with the reason.
 *
 * Surfaced rather than filtered away: an operator must be able to see that a truck is
 * missing from the map and why, instead of it silently not being there.
 */
export function undrawablePositions(
  positions: readonly SpatialPosition[],
): readonly SpatialPosition[] {
  return positions.filter((position) => !position.drawableInScene);
}
