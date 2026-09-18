/**
 * Resizable decks: the pure track arithmetic, and the invariant that resizing is
 * presentation state only - every HMI deck has gutters, the page still never scrolls, and
 * nothing about a vehicle passes through the layout code.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  CENTRE_SHARE,
  clampTrack,
  growSign,
  parseTrackPx,
  sanitizeStoredSizes,
  TRACK_STEP_PX,
  type TrackSpec,
  trackStyle,
  trackVar,
} from "./trackLayout";

const SPEC: TrackSpec = { axis: "x", index: 0, minPx: 180, maxPx: 560 };
const SRC = join(__dirname, "..");
const read = (rel: string) =>
  readFileSync(join(SRC, rel), "utf-8")
    .replace(/\r\n/g, "\n")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");

describe("clampTrack", () => {
  it("holds the floor and the ceiling", () => {
    expect(clampTrack(10, SPEC, 1366)).toBe(180);
    expect(clampTrack(9000, SPEC, 1366)).toBe(560);
    expect(clampTrack(300, SPEC, 1366)).toBe(300);
  });

  it("never lets a side track take more than the centre share of the grid", () => {
    expect(clampTrack(560, SPEC, 800)).toBe(Math.floor(800 * CENTRE_SHARE));
  });

  it("falls back to the spec ceiling when the grid size is unknown", () => {
    expect(clampTrack(560, SPEC, Number.NaN)).toBe(560);
    expect(clampTrack(560, SPEC, 0)).toBe(560);
  });

  it("returns the floor for a non-finite request instead of throwing", () => {
    expect(clampTrack(Number.NaN, SPEC, 1366)).toBe(180);
    expect(clampTrack(Number.POSITIVE_INFINITY, SPEC, 1366)).toBe(180);
  });

  it("rounds to whole pixels", () => {
    expect(clampTrack(233.4, SPEC, 1366)).toBe(233);
  });
});

describe("parseTrackPx", () => {
  it("reads a resolved template list", () => {
    expect(parseTrackPx("232px 813px 272px", 0)).toBe(232);
    expect(parseTrackPx("232px 813px 272px", 2)).toBe(272);
    expect(parseTrackPx("24.5px 133px", 0)).toBe(24.5);
  });

  it("refuses unresolved or out-of-range entries", () => {
    expect(parseTrackPx("none", 0)).toBeNull();
    expect(parseTrackPx("1fr 2fr", 1)).toBeNull();
    expect(parseTrackPx("232px 813px", 5)).toBeNull();
    expect(parseTrackPx("", 0)).toBeNull();
  });
});

describe("trackStyle / trackVar", () => {
  it("publishes only resized tracks as --track-* pixel values", () => {
    expect(trackVar("fleet")).toBe("--track-fleet");
    expect(trackStyle({ fleet: 300 })).toEqual({ "--track-fleet": "300px" });
    expect(trackStyle({})).toEqual({});
  });
});

describe("sanitizeStoredSizes", () => {
  const specs = { fleet: SPEC, selected: { ...SPEC, index: 2 } };

  it("keeps known finite values, clamped", () => {
    expect(sanitizeStoredSizes({ fleet: 300, selected: 9999 }, specs)).toEqual({
      fleet: 300,
      selected: 560,
    });
  });

  it("drops unknown tracks and bad values, never throws", () => {
    expect(sanitizeStoredSizes({ ghost: 300, fleet: "300", selected: Number.NaN }, specs)).toEqual(
      {},
    );
    expect(sanitizeStoredSizes(null, specs)).toEqual({});
    expect(sanitizeStoredSizes([1, 2], specs)).toEqual({});
    expect(sanitizeStoredSizes("junk", specs)).toEqual({});
  });
});

describe("growSign", () => {
  it("grows past an end edge, shrinks past a start edge", () => {
    expect(growSign("end")).toBe(1);
    expect(growSign("start")).toBe(-1);
    expect(TRACK_STEP_PX).toBeGreaterThan(0);
  });
});

describe("every HMI deck is resizable, and only its presentation", () => {
  const decks = [
    { file: "screens/OperationsOverview.tsx", grid: "s1", gutters: 2 },
    { file: "vehicle/DriverScreen.tsx", grid: "operator", gutters: 4 },
    { file: "minecast/MineCastApp.tsx", grid: "mine-cast", gutters: 2 },
  ];

  it("each deck mounts the shared hook, flags its grid, and places its gutters", () => {
    for (const deck of decks) {
      const src = read(deck.file);
      expect(src, deck.file).toMatch(/useTrackLayout\(/);
      expect(src, deck.file).toContain(`data-track-grid="${deck.grid}"`);
      expect(src.match(/<TrackGutter\b/g)?.length, deck.file).toBe(deck.gutters);
    }
  });

  it("the layout code touches no vehicle state and no network", () => {
    const layout = read("components/TrackLayout.tsx") + read("state/trackLayout.ts");
    expect(layout).not.toMatch(/AppStateStore|useAppState|VehicleState|speed|safety|position/i);
    expect(layout).not.toMatch(/fetch\(|WebSocket|Math\.random|Date\.now/);
  });

  it("the grids are sized by --track-* variables with the previous defaults kept", () => {
    const css = readFileSync(join(SRC, "theme/hmi.css"), "utf-8").replace(/\r\n/g, "\n");
    expect(css).toMatch(/\.cr-workspace \{\s*grid-template-columns: var\(--track-fleet, 232px\)/);
    expect(css).toMatch(/var\(--track-left, minmax\(0, 1fr\)\) auto var\(--track-right, minmax\(0, 1fr\)\)/);
    expect(css).toMatch(/minmax\(0, var\(--track-row2, 1fr\)\)/);
    expect(css).toMatch(/var\(--track-left, minmax\(15rem, 17%\)\)/);
    // The frame stays viewport-bound: resizing trades space, it never adds a page scroll.
    expect(css).toMatch(/body \{[^}]*overflow: hidden/);
  });
});
