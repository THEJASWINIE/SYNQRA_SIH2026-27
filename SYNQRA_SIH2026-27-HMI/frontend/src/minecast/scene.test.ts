/**
 * Scene maths — terrain field, mine geometry, camera framing.
 *
 * The three pure modules behind the 3D view. They are tested here rather than through the
 * renderer because a WebGL context cannot exist in this Node test environment (M4D-C):
 * putting the arithmetic in `.ts` modules is what makes the scene testable at all.
 *
 * The strongest assertions are the honesty ones. A rendered landform is persuasive, so
 * these hold that every feature it is built from is stamped SYNTHETIC_FOR_DEMO,
 * unverified, low confidence - and that nothing in it is labelled as NMDC survey data.
 *
 * SOFTWARE ONLY. No hardware, no WebGL, no DOM.
 */

import { describe, expect, it } from "vitest";

import { FRAME_MARGIN, fitOrtho, overviewFraming, scaleBar } from "./mineCamera";
import {
  benchFeatures,
  floorFeature,
  mineFeatures,
  pitFeature,
  SYNTHETIC_GEOMETRY_PROVENANCE,
} from "./mineFeatures";
import {
  elevationAt,
  gridElevationAt,
  sampleHeightGrid,
  TERRAIN_PROVENANCE,
  terrainConfig,
  VERTICAL_EXAGGERATION,
} from "./terrainField";

// The published Deposit-5 extent measures roughly 3.2 km east-west by 3.4 km north-south.
const WIDTH_M = 3200;
const HEIGHT_M = 3400;
const CONFIG = terrainConfig(WIDTH_M, HEIGHT_M);

// ---------------------------------------------------------------------------
// terrain honesty
// ---------------------------------------------------------------------------

describe("terrain provenance", () => {
  it("is SYNTHETIC_FOR_DEMO, unverified, low confidence", () => {
    expect(TERRAIN_PROVENANCE.source).toBe("SYNTHETIC_FOR_DEMO");
    expect(TERRAIN_PROVENANCE.verified).toBe(false);
    expect(TERRAIN_PROVENANCE.confidence).toBe("LOW");
  });

  it("says on its own label that it is not surveyed", () => {
    expect(TERRAIN_PROVENANCE.label).toContain("SYNTHETIC");
    expect(TERRAIN_PROVENANCE.label).toContain("NOT SURVEYED");
    expect(TERRAIN_PROVENANCE.detail).toContain("No DEM");
  });

  it("records a LOCAL vertical datum, never mean sea level", () => {
    // An absolute altitude would imply a vertical reference nobody established.
    expect(TERRAIN_PROVENANCE.verticalDatum).toContain("LOCAL");
    expect(TERRAIN_PROVENANCE.verticalDatum).toContain("UNSURVEYED");
    expect(TERRAIN_PROVENANCE.verticalDatum.toUpperCase()).not.toContain("MSL");
    expect(TERRAIN_PROVENANCE.verticalDatum.toUpperCase()).not.toContain("SEA LEVEL");
  });

  it("never claims to be NMDC survey data", () => {
    const words = `${TERRAIN_PROVENANCE.label} ${TERRAIN_PROVENANCE.detail}`.toUpperCase();
    expect(words).not.toContain("NMDC INFRASTRUCTURE");
    expect(words).not.toContain("OFFICIAL");
    expect(words).not.toContain("SURVEY-GRADE");
  });

  it("discloses the vertical exaggeration rather than applying it silently", () => {
    // Exaggerating relief is standard in mine visualisation and dishonest only if hidden:
    // it makes every on-screen slope steeper than the ground it depicts.
    expect(VERTICAL_EXAGGERATION).toBeGreaterThan(1);
    expect(TERRAIN_PROVENANCE.verticalExaggeration).toBe(VERTICAL_EXAGGERATION);
    expect(TERRAIN_PROVENANCE.detail).toContain("exaggerated");
    expect(TERRAIN_PROVENANCE.detail).toContain("no slope shown is a real gradient");
  });

  it("keeps the field in TRUE metres, so exaggeration is a draw-time choice only", () => {
    // A grid whose stored heights were pre-multiplied would make the real depth
    // unrecoverable, and any future consumer would inherit the distortion silently.
    const config = terrainConfig(3200, 3400);
    const grid = sampleHeightGrid(config);
    expect(grid.verticalExaggeration).toBe(VERTICAL_EXAGGERATION);
    expect(grid.maxM - grid.minM).toBeLessThan(
      (config.pitDepthM + config.reliefM * 2) * VERTICAL_EXAGGERATION,
    );
  });

  it("carries its provenance on the sampled grid, not only in a constant", () => {
    // A grid handed to a renderer keeps its caveat even if separated from this module.
    expect(sampleHeightGrid(terrainConfig(600, 600)).provenance.source).toBe("SYNTHETIC_FOR_DEMO");
  });
});

// ---------------------------------------------------------------------------
// terrain determinism and shape
// ---------------------------------------------------------------------------

describe("terrain field", () => {
  it("is deterministic — the same point always returns the same elevation", () => {
    const a = elevationAt(1234, 567, CONFIG);
    const b = elevationAt(1234, 567, CONFIG);
    expect(a).toBe(b);
  });

  it("produces an identical grid on repeated sampling", () => {
    const small = terrainConfig(600, 600);
    expect(sampleHeightGrid(small).heights).toEqual(sampleHeightGrid(small).heights);
  });

  it("uses no Math.random — a different seed gives a different landform", () => {
    const seeded = { ...CONFIG, seed: 99 };
    const here = elevationAt(1000, 1000, CONFIG);
    const there = elevationAt(1000, 1000, seeded);
    expect(here).not.toBe(there);
  });

  it("returns finite elevations everywhere on the grid", () => {
    const grid = sampleHeightGrid(terrainConfig(800, 800));
    for (const h of grid.heights) expect(Number.isFinite(h)).toBe(true);
  });

  it("digs a pit — the centre is well below the rim", () => {
    const centreX = CONFIG.pitCentre.fx * WIDTH_M;
    const centreY = CONFIG.pitCentre.fy * HEIGHT_M;
    const floor = elevationAt(centreX, centreY, CONFIG);
    const outside = elevationAt(centreX + CONFIG.pitRadiusM * 1.6, centreY, CONFIG);

    expect(floor).toBeLessThan(outside);
    // Most of the configured depth should be realised at the centre.
    expect(outside - floor).toBeGreaterThan(CONFIG.pitDepthM * 0.6);
  });

  it("cuts benches — the wall descends in steps, not a smooth cone", () => {
    const centreX = CONFIG.pitCentre.fx * WIDTH_M;
    const centreY = CONFIG.pitCentre.fy * HEIGHT_M;

    /*
      Sample inward along a bearing the ramp does not cross (south-south-west) and count
      riser-sized drops. A smooth cone would have none; a terraced wall has one per bench.
    */
    const riser = CONFIG.pitDepthM / CONFIG.benchCount;
    const bearing = -1.9;
    let drops = 0;
    let previous = elevationAt(
      centreX + Math.cos(bearing) * CONFIG.pitRadiusM * 1.4,
      centreY + Math.sin(bearing) * CONFIG.pitRadiusM * 1.4,
      CONFIG,
    );
    for (let r = CONFIG.pitRadiusM * 1.4; r > 0; r -= 4) {
      const here = elevationAt(
        centreX + Math.cos(bearing) * r,
        centreY + Math.sin(bearing) * r,
        CONFIG,
      );
      if (previous - here >= riser * 0.5) drops += 1;
      previous = here;
    }
    expect(drops).toBeGreaterThanOrEqual(3);
    expect(drops).toBeLessThanOrEqual(CONFIG.benchCount + 2);
  });

  it("keeps relief bounded by the configured amplitude outside the pit", () => {
    const far = elevationAt(50, 50, CONFIG);
    expect(Math.abs(far)).toBeLessThanOrEqual(CONFIG.reliefM + 1);
  });

  it("sizes the grid from the segment count", () => {
    const grid = sampleHeightGrid(terrainConfig(400, 400));
    expect(grid.size).toBe(CONFIG.segments + 1);
    expect(grid.heights.length).toBe(grid.size * grid.size);
  });

  it("the mesh interpolation equals the field exactly at grid vertices", () => {
    const grid = sampleHeightGrid(CONFIG);
    for (const [row, col] of [
      [0, 0],
      [10, 7],
      [48, 48],
      [CONFIG.segments, CONFIG.segments],
    ] as const) {
      const x = (col / CONFIG.segments) * WIDTH_M;
      const y = (row / CONFIG.segments) * HEIGHT_M;
      expect(gridElevationAt(grid, x, y)).toBeCloseTo(elevationAt(x, y, CONFIG), 6);
    }
  });

  it("the mesh interpolation follows the drawn triangles, not a bilinear patch", () => {
    // MineTerrain splits each cell on the top-right / bottom-left diagonal. At the centre
    // of the first triangle the drawn height is the plane through its three corners.
    const grid = sampleHeightGrid(CONFIG);
    const cell = WIDTH_M / CONFIG.segments;
    const cellY = HEIGHT_M / CONFIG.segments;
    const at = (r: number, c: number) => grid.heights[r * grid.size + c] as number;
    const row = 40;
    const col = 44;
    const probeX = (col + 0.25) * cell;
    const probeY = (row + 0.25) * cellY;
    const triangleA =
      at(row, col) +
      (at(row, col + 1) - at(row, col)) * 0.25 +
      (at(row + 1, col) - at(row, col)) * 0.25;
    expect(gridElevationAt(grid, probeX, probeY)).toBeCloseTo(triangleA, 6);
  });

  it("the mesh interpolation is finite and clamped off the grid edge", () => {
    const grid = sampleHeightGrid(CONFIG);
    const probes: readonly (readonly [number, number])[] = [
      [-100, -100],
      [WIDTH_M + 100, HEIGHT_M + 100],
      [WIDTH_M / 3, HEIGHT_M / 7],
    ];
    for (const [x, y] of probes) {
      expect(Number.isFinite(gridElevationAt(grid, x, y))).toBe(true);
    }
  });

  it("scales the pit to the site rather than a fixed radius", () => {
    expect(terrainConfig(6000, 6000).pitRadiusM).toBeGreaterThan(
      terrainConfig(1400, 1400).pitRadiusM,
    );
  });
});

// ---------------------------------------------------------------------------
// mine geometry honesty
// ---------------------------------------------------------------------------

describe("mine geometry provenance", () => {
  it("stamps every single feature SYNTHETIC_FOR_DEMO", () => {
    const features = mineFeatures(CONFIG);
    expect(features.length).toBeGreaterThan(1);
    for (const feature of features) {
      expect(feature.source, feature.id).toBe("SYNTHETIC_FOR_DEMO");
      expect(feature.verified, feature.id).toBe(false);
      expect(feature.confidence, feature.id).toBe("LOW");
    }
  });

  it("labels each feature as synthetic in its own words", () => {
    for (const feature of mineFeatures(CONFIG)) {
      expect(feature.label.toLowerCase(), feature.id).toContain("synthetic");
    }
  });

  it("never labels invented geometry as NMDC infrastructure", () => {
    const words = mineFeatures(CONFIG)
      .map((f) => `${f.id} ${f.label}`)
      .join(" ")
      .toUpperCase();
    expect(words).not.toContain("NMDC");
    expect(words).not.toContain("OFFICIAL");
    expect(words).not.toContain("LEASE");
    expect(SYNTHETIC_GEOMETRY_PROVENANCE.detail).toContain("not NMDC infrastructure");
  });

  it("uses the id shape the specification asked for", () => {
    expect(benchFeatures(CONFIG)[0]?.id).toBe("BENCH-01");
    expect(pitFeature(CONFIG).id).toBe("PIT-01");
  });
});

// ---------------------------------------------------------------------------
// mine geometry shape
// ---------------------------------------------------------------------------

describe("mine geometry", () => {
  it("produces the rim, one crest per bench, and the floor outline", () => {
    const features = mineFeatures(CONFIG);
    expect(pitFeature(CONFIG).kind).toBe("PIT");
    expect(floorFeature(CONFIG).kind).toBe("FLOOR");
    expect(benchFeatures(CONFIG).length).toBe(CONFIG.benchCount - 1);
    expect(features.length).toBe(CONFIG.benchCount + 1);
  });

  it("descends — each crest sits below the one above it", () => {
    const benches = benchFeatures(CONFIG);
    for (let i = 1; i < benches.length; i += 1) {
      const above = benches[i - 1];
      const below = benches[i];
      if (!above || !below) throw new Error("bench missing");
      expect(below.elevationM).toBeLessThan(above.elevationM);
    }
    expect(floorFeature(CONFIG).elevationM).toBeLessThan(
      benches[benches.length - 1]?.elevationM ?? 0,
    );
  });

  it("nests inward — each crest is at greater inwardness than the one above", () => {
    const benches = benchFeatures(CONFIG);
    for (let i = 1; i < benches.length; i += 1) {
      expect(benches[i]?.inwardness ?? 0).toBeGreaterThan(benches[i - 1]?.inwardness ?? 1);
    }
    expect(pitFeature(CONFIG).inwardness).toBe(0);
    expect(floorFeature(CONFIG).inwardness).toBe(1);
  });

  it("interrupts bench crests where the ramp cuts through", () => {
    // The whole point of the morphology pass: a bench the ramp passes through has no
    // crest there, so it is several open segments rather than one closed ring.
    const interrupted = benchFeatures(CONFIG).filter((b) => b.interrupted);
    expect(interrupted.length).toBeGreaterThanOrEqual(3);
    for (const bench of interrupted) {
      expect(bench.segments.length, bench.id).toBeGreaterThanOrEqual(2);
    }
  });

  it("keeps the rim as one closed loop", () => {
    const rim = pitFeature(CONFIG);
    expect(rim.interrupted).toBe(false);
    expect(rim.segments.length).toBe(1);
    const loop = rim.segments[0] ?? [];
    const first = loop[0];
    const last = loop[loop.length - 1];
    expect(first?.x).toBe(last?.x);
    expect(first?.y).toBe(last?.y);
  });

  it("has finite coordinates on every segment of every feature", () => {
    for (const feature of mineFeatures(CONFIG)) {
      for (const segment of feature.segments) {
        expect(segment.length, feature.id).toBeGreaterThanOrEqual(2);
        for (const point of segment) {
          expect(Number.isFinite(point.x), feature.id).toBe(true);
          expect(Number.isFinite(point.y), feature.id).toBe(true);
        }
      }
    }
  });

  it("is deterministic", () => {
    expect(JSON.stringify(mineFeatures(CONFIG))).toBe(JSON.stringify(mineFeatures(CONFIG)));
  });
});

// ---------------------------------------------------------------------------
// camera framing
// ---------------------------------------------------------------------------

describe("orthographic framing", () => {
  it("fits the whole site with a margin, on a wide viewport", () => {
    const frustum = fitOrtho(WIDTH_M, HEIGHT_M, 16 / 9);
    const visibleWidth = frustum.right - frustum.left;
    const visibleHeight = frustum.top - frustum.bottom;

    expect(visibleWidth).toBeGreaterThanOrEqual(WIDTH_M);
    expect(visibleHeight).toBeGreaterThanOrEqual(HEIGHT_M);
  });

  it("fits the whole site on a tall viewport too", () => {
    const frustum = fitOrtho(WIDTH_M, HEIGHT_M, 0.6);
    expect(frustum.right - frustum.left).toBeGreaterThanOrEqual(WIDTH_M);
    expect(frustum.top - frustum.bottom).toBeGreaterThanOrEqual(HEIGHT_M);
  });

  it("matches the viewport aspect, so the site is never stretched", () => {
    const aspect = 16 / 9;
    const frustum = fitOrtho(WIDTH_M, HEIGHT_M, aspect);
    const ratio = (frustum.right - frustum.left) / (frustum.top - frustum.bottom);
    expect(ratio).toBeCloseTo(aspect, 6);
  });

  it("leaves the configured margin on the binding axis", () => {
    // Height binds here, so visible height should be the site plus both margins.
    const frustum = fitOrtho(1000, 4000, 1.6);
    const visibleHeight = frustum.top - frustum.bottom;
    expect(visibleHeight).toBeCloseTo(4000 * (1 + FRAME_MARGIN * 2), 6);
  });

  it("survives a degenerate aspect instead of producing NaN", () => {
    for (const aspect of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
      const frustum = fitOrtho(WIDTH_M, HEIGHT_M, aspect);
      expect(Number.isFinite(frustum.left), String(aspect)).toBe(true);
      expect(Number.isFinite(frustum.top), String(aspect)).toBe(true);
    }
  });

  it("gives a depth range wide enough for a tilted view of the pit floor", () => {
    const frustum = fitOrtho(WIDTH_M, HEIGHT_M, 1.7);
    expect(frustum.far - frustum.near).toBeGreaterThan(WIDTH_M * 2);
  });
});

describe("overview framing", () => {
  it("looks at the centre of the site", () => {
    const framing = overviewFraming(WIDTH_M, HEIGHT_M, 1.7);
    expect(framing.target[0]).toBeCloseTo(WIDTH_M / 2, 6);
    expect(framing.target[2]).toBeCloseTo(HEIGHT_M / 2, 6);
  });

  it("is tilted, not a plan view — the camera is above and offset", () => {
    const framing = overviewFraming(WIDTH_M, HEIGHT_M, 1.7);
    expect(framing.position[1]).toBeGreaterThan(0);
    expect(framing.position[0]).toBeGreaterThan(framing.target[0]);
    expect(framing.position[2]).toBeGreaterThan(framing.target[2]);
  });

  it("returns finite numbers throughout", () => {
    const framing = overviewFraming(WIDTH_M, HEIGHT_M, 1.7);
    for (const value of [...framing.position, ...framing.target]) {
      expect(Number.isFinite(value)).toBe(true);
    }
  });

  it("is deterministic", () => {
    expect(JSON.stringify(overviewFraming(WIDTH_M, HEIGHT_M, 1.7))).toBe(
      JSON.stringify(overviewFraming(WIDTH_M, HEIGHT_M, 1.7)),
    );
  });
});

describe("scale bar", () => {
  it("picks a round number of metres", () => {
    const { metres } = scaleBar(1200, 3400);
    const mantissa = metres / 10 ** Math.floor(Math.log10(metres));
    expect([1, 2, 5]).toContain(Math.round(mantissa));
  });

  it("reports a pixel width consistent with the metres it chose", () => {
    const viewportPx = 1200;
    const visibleM = 3400;
    const { metres, pixels } = scaleBar(viewportPx, visibleM);
    expect(pixels).toBeCloseTo(metres / (visibleM / viewportPx), 6);
  });

  it("grows the bar as the view zooms out", () => {
    expect(scaleBar(1200, 8000).metres).toBeGreaterThan(scaleBar(1200, 800).metres);
  });
});
