/**
 * Mine-Cast layout guards.
 *
 * These pin the four CSS decisions that stop the Mine-Cast shell producing horizontal
 * overflow. Each was a real defect observed in a browser at 1366x768, and each is a
 * one-token regression away from coming back:
 *
 *   1. `minmax(0, 1fr)` on the centre grid track   - `1fr` alone cannot shrink
 *   2. `min-width: 0` on the three columns         - a grid item defaults to min-content
 *   3. a `.minecast`-scoped `.data-table` override - the shared table is `nowrap` + scroll
 *   4. `overflow-wrap` on `.mono` cells            - table min-content ignores break-word
 *
 * A layout engine is not available in this Node test environment, so these assert the
 * stylesheet's CONTENT rather than computed geometry. The geometry itself was verified in
 * Chrome at 1366x768 and 1920x1080; this file is the cheap guard against silent removal.
 *
 * SOFTWARE ONLY. No DOM, no jsdom, no browser.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const CSS_PATH = "src/theme/hmi.css";

/**
 * Line endings normalised, because the stylesheet is CRLF on this checkout and the
 * multi-line selector lookups below match on `\n`.
 */
const css = readFileSync(CSS_PATH, "utf-8").replace(/\r\n/g, "\n");

/** Only the Mine-Cast section. The shared HMI styles above it are not ours to police. */
const MINECAST_SOURCE = css.slice(css.indexOf("MINE-CAST — spatial view shell"));

/**
 * Comments stripped before scanning.
 *
 * The CSS explains WHY each guard exists, and those explanations quote the very values
 * they replaced - `max-width: 1366px` among them. Prose naming a removed value must not
 * read as the value still being present.
 */
const MINECAST_BLOCK = MINECAST_SOURCE.replace(/\/\*[\s\S]*?\*\//g, "");

/** Extract one rule body by selector, from the Mine-Cast block. */
function rule(selector: string): string {
  const index = MINECAST_BLOCK.indexOf(`${selector} {`);
  if (index === -1) return "";
  const open = MINECAST_BLOCK.indexOf("{", index);
  const close = MINECAST_BLOCK.indexOf("}", open);
  return MINECAST_BLOCK.slice(open + 1, close);
}

describe("the Mine-Cast CSS block is present", () => {
  it("finds the section to scan", () => {
    expect(MINECAST_BLOCK.length).toBeGreaterThan(1000);
    expect(MINECAST_BLOCK).toContain(".mc-body");
  });
});

describe("the grid can shrink", () => {
  it("sizes the centre track with minmax(0, 1fr), not a bare 1fr", () => {
    // `1fr` is `minmax(auto, 1fr)`, and an `auto` minimum is min-content - which lets a
    // wide child push the grid past the viewport and scroll the whole page.
    const body = rule(".mc-body");
    expect(body).toContain("minmax(0, 1fr)");
    expect(body).not.toMatch(/grid-template-columns:[^;]*\s1fr\s/);
  });

  it("opts all three columns out of their default min-content floor", () => {
    const columns = rule(".mc-left,\n.mc-right,\n.mc-centre");
    expect(columns).toContain("min-width: 0");
  });

  it("caps the grid at the viewport width", () => {
    expect(rule(".mc-body")).toContain("max-width: 100%");
  });

  it("guards the root against page-level horizontal scroll", () => {
    const root = rule(".minecast");
    expect(root).toContain("overflow-x: hidden");
    expect(root).toContain("max-width: 100%");
  });
});

describe("Mine-Cast tables wrap instead of scrolling sideways", () => {
  it("overrides the shared nowrap table, scoped to .minecast", () => {
    // The shared `.data-table` is `display: block; overflow-x: auto; white-space: nowrap`,
    // which is correct for the control room's wide tables and wrong in a 280px panel.
    const table = rule(".minecast .data-table");
    expect(table).toContain("white-space: normal");
    expect(table).toContain("display: table");
    expect(table).toContain("max-width: 100%");
  });

  it("leaves the shared .data-table rule untouched for every other screen", () => {
    // The global rule keeps its horizontal scroll: the control room needs it.
    const globalRule = css.slice(css.indexOf(".data-table {"));
    expect(globalRule.slice(0, 200)).toContain("white-space: nowrap");
  });

  it("breaks machine tokens but not human status words", () => {
    // `anywhere` on `.mono` (enum names, DMS strings) is what lets an auto-layout table
    // shrink; prose keeps `break-word` so UNAVAILABLE never renders as UNAVAIL/ABLE.
    expect(MINECAST_BLOCK).toContain(".minecast .data-table td.mono");
    const cells = rule(".minecast .data-table td,\n.minecast .data-table th");
    expect(cells).toContain("overflow-wrap: break-word");
    expect(cells).not.toContain("overflow-wrap: anywhere");
  });

  it("uses auto table layout, so no column is forced to break a word", () => {
    expect(rule(".minecast .data-table")).toContain("table-layout: auto");
  });
});

describe("panels never widen their column", () => {
  it("constrains the shared panel primitive inside Mine-Cast only", () => {
    expect(rule(".minecast .panel")).toContain("max-width: 100%");
    expect(rule(".minecast .panel-body")).toContain("min-width: 0");
  });

  it("keeps vertical scrolling and drops horizontal in the side columns", () => {
    const sides = rule(".mc-left,\n.mc-right");
    expect(sides).toContain("overflow-y: auto");
    expect(sides).toContain("overflow-x: hidden");
  });

  it("lets the layer drawer wrap its badges rather than stretch", () => {
    const row = rule(".mc-layer-row");
    expect(row).toContain("flex-wrap: wrap");
    expect(row).toContain("min-width: 0");
  });

  it("lays the fleet row out so availability is never clipped", () => {
    const row = rule(".mc-fleet-row");
    expect(row).toContain("minmax(0, 1fr)");
    // No fixed rem track that only fits at one font size.
    expect(row).not.toContain("6.5rem");
  });
});

describe("the collapse threshold sits below the target resolutions", () => {
  it("keeps three columns at 1366 wide", () => {
    // A `max-width: 1366px` query matches a 1366-wide viewport exactly and would drop the
    // inspector under the map at the primary target resolution.
    expect(MINECAST_BLOCK).not.toContain("max-width: 1366px");
    expect(MINECAST_BLOCK).toContain("max-width: 1200px");
  });
});

describe("scope", () => {
  it("changes only .minecast / .mc-* selectors", () => {
    // Every selector introduced by this block must be scoped, so no other screen shifts.
    const selectors = MINECAST_BLOCK.match(/^\.[a-zA-Z][^{,\n]*(?=[,{])/gm) ?? [];
    expect(selectors.length).toBeGreaterThan(10);
    for (const selector of selectors) {
      expect(selector.trim(), selector).toMatch(/^\.(minecast|mc-)/);
    }
  });
});
