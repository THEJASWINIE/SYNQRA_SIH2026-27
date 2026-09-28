/**
 * Camera framing maths.
 *
 * ==========================================================================
 *  THE FRAMING IS COMPUTED HERE SO IT CAN BE TESTED HERE.
 *
 *  A camera that frames the site slightly wrong is a bug you can only see, not one a
 *  test can catch - unless the arithmetic lives in a pure function. This module holds no
 *  Three.js object and imports no Three.js: it turns site dimensions and a viewport
 *  aspect into numbers, and the scene applies them.
 * ==========================================================================
 *
 * ORTHOGRAPHIC, DELIBERATELY
 *
 * An orthographic projection keeps scale constant across the viewport, so equal distances
 * on screen are equal distances on the ground. That is the right choice for a dispatch
 * view where an operator compares positions and gaps. A perspective camera would make the
 * near side of the pit read as larger than the far side, which is exactly the sort of
 * quiet distortion this HMI avoids.
 *
 * PASS 2 PROVIDES OVERVIEW ONLY
 *
 * The remaining camera modes (TACTICAL, FOLLOW, INCIDENT, FREE) are a later pass. This
 * file exposes the one mode the static scene needs, plus the frustum arithmetic those
 * modes will reuse.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

/** Half-extents of an orthographic frustum, in scene metres. */
export interface OrthoFrustum {
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;
  readonly near: number;
  readonly far: number;
}

export interface CameraFraming {
  /** Where the camera sits, scene metres, y up. */
  readonly position: readonly [number, number, number];
  /** What it looks at, scene metres. */
  readonly target: readonly [number, number, number];
  readonly frustum: OrthoFrustum;
  /** Metres of ground per screen unit at this framing. Useful for a scale bar. */
  readonly metresPerUnit: number;
}

/** Fraction of margin left around the site so the extent edge is not flush to the viewport. */
export const FRAME_MARGIN = 0.015;

/**
 * An orthographic frustum that fits a site of `widthM` x `heightM` into a viewport of the
 * given aspect ratio, whichever dimension is the binding constraint.
 *
 * Fitting the LARGER requirement is what guarantees the whole site is visible: fitting
 * the smaller one would crop the site on its long axis, and an operator would not be able
 * to tell that anything was missing.
 */
export function fitOrtho(widthM: number, heightM: number, aspect: number): OrthoFrustum {
  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : 1;

  const margin = 1 + FRAME_MARGIN * 2;
  const paddedWidth = widthM * margin;
  const paddedHeight = heightM * margin;

  // Half-height needed if width binds, versus if height binds. Take the larger.
  const halfHeightForWidth = paddedWidth / safeAspect / 2;
  const halfHeightForHeight = paddedHeight / 2;
  const halfHeight =
    halfHeightForWidth > halfHeightForHeight ? halfHeightForWidth : halfHeightForHeight;
  const halfWidth = halfHeight * safeAspect;

  /*
    Depth range spans the diagonal, so a tilted camera cannot clip the far corner of the
    site or the floor of the pit. Generous rather than tight: a clipped landform reads as
    missing terrain.
  */
  const diagonal = Math.sqrt(widthM * widthM + heightM * heightM);

  return {
    left: -halfWidth,
    right: halfWidth,
    top: halfHeight,
    bottom: -halfHeight,
    near: -diagonal * 2,
    far: diagonal * 4,
  };
}

/**
 * OVERVIEW: the whole site, viewed from the south-east and above.
 *
 * A tilted view rather than a plan view, so benches and depth are legible - a straight-
 * down orthographic view of a pit is nearly indistinguishable from a flat disc. The
 * bearing is fixed and stated so a reader knows which way north is; it is not a free
 * camera.
 */
export function overviewFraming(widthM: number, heightM: number, aspect: number): CameraFraming {
  const target: readonly [number, number, number] = [widthM / 2, 0, heightM / 2];
  const frustum = fitOrtho(widthM, heightM, aspect);

  /*
    Offset along +x / +z with a strong +y component. Magnitude is irrelevant to an
    orthographic projection's framing - only direction matters - but it is scaled to the
    site so the near plane never sits inside the terrain.
  */
  const reach = Math.sqrt(widthM * widthM + heightM * heightM);

  return {
    // MINE-ROUTES-02: elevated oblique (~50 deg) so the route topology reads at once, with
    // enough tilt left that the benches still show as steps.
    position: [target[0] + reach * 0.34, reach * 0.8, target[2] + reach * 0.52],
    target,
    frustum,
    metresPerUnit: 1,
  };
}

/**
 * A round number of metres for a scale bar, and how wide it is on screen.
 *
 * Picks from a 1/2/5 sequence so the bar reads as 200 m or 500 m rather than 437 m.
 * Returned rather than drawn, so the caller decides where it goes.
 */
export function scaleBar(
  viewportWidthPx: number,
  visibleWidthM: number,
): { readonly metres: number; readonly pixels: number } {
  const targetPx = viewportWidthPx * 0.18;
  const metresPerPx = visibleWidthM / viewportWidthPx;
  const rawMetres = targetPx * metresPerPx;

  const magnitude = 10 ** Math.floor(Math.log10(rawMetres > 0 ? rawMetres : 1));
  const normalised = rawMetres / magnitude;
  const step = normalised >= 5 ? 5 : normalised >= 2 ? 2 : 1;
  const metres = step * magnitude;

  return { metres, pixels: metres / metresPerPx };
}
