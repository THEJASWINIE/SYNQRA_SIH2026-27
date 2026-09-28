/**
 * Render-time freshness tests — M4.
 * Covers freshness classification per quality, and the AMB-014 unconfigured-threshold
 * behaviour.
 */

import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import { formatAge, freshnessLabel, viewFreshness } from "./freshness";

const NOW = Date.parse("2026-01-01T00:00:10.000Z");
const CONFIG = freshnessConfig(5000);

describe("classification with a configured threshold", () => {
  it("a recent timestamp is OK", () => {
    const view = viewFreshness("2026-01-01T00:00:08.000Z", CONFIG, NOW);
    expect(view.quality).toBe("OK");
    expect(view.ageMs).toBe(2000);
    expect(view.thresholdConfigured).toBe(true);
  });

  it("an old timestamp is STALE and keeps its age", () => {
    const view = viewFreshness("2026-01-01T00:00:00.000Z", CONFIG, NOW);
    expect(view.quality).toBe("STALE");
    expect(view.ageMs).toBe(10_000);
  });

  it("exactly at the threshold is still OK — stale means BEYOND the timeout", () => {
    const view = viewFreshness("2026-01-01T00:00:05.000Z", CONFIG, NOW);
    expect(view.quality).toBe("OK");
  });

  it("an absent timestamp is MISSING", () => {
    expect(viewFreshness(null, CONFIG, NOW).quality).toBe("MISSING");
    expect(viewFreshness(undefined, CONFIG, NOW).quality).toBe("MISSING");
    expect(viewFreshness("", CONFIG, NOW).quality).toBe("MISSING");
  });

  it("an unparseable timestamp is INVALID, never MISSING", () => {
    // A payload that arrived and could not be used is an integration fault. Reporting it
    // as MISSING would hide that behind what looks like a quiet link.
    const view = viewFreshness("not-a-timestamp", CONFIG, NOW);
    expect(view.quality).toBe("INVALID");
    expect(view.quality).not.toBe("MISSING");
  });

  it("an INVALID datum is not also reported as STALE", () => {
    const view = viewFreshness("nonsense", CONFIG, NOW);
    expect(view.quality).toBe("INVALID");
    expect(view.ageMs).toBeNull();
  });
});

describe("AMB-014 — no configured threshold", () => {
  it("reports the age but REFUSES to classify", () => {
    const view = viewFreshness("2026-01-01T00:00:00.000Z", null, NOW);
    expect(view.ageMs).toBe(10_000);
    expect(view.quality).toBeNull();
    expect(view.thresholdConfigured).toBe(false);
  });

  it("does not silently call an old datum OK", () => {
    expect(viewFreshness("2020-01-01T00:00:00.000Z", null, NOW).quality).not.toBe("OK");
  });

  it("does not invent STALE either", () => {
    expect(viewFreshness("2020-01-01T00:00:00.000Z", null, NOW).quality).not.toBe("STALE");
  });

  it("still distinguishes MISSING and INVALID without a threshold", () => {
    expect(viewFreshness(null, null, NOW).quality).toBe("MISSING");
    expect(viewFreshness("bad", null, NOW).quality).toBe("INVALID");
  });

  it("labels the unclassified state in words, not by omission", () => {
    const view = viewFreshness("2026-01-01T00:00:00.000Z", null, NOW);
    expect(freshnessLabel(view)).toBe("AGE ONLY — NOT CLASSIFIED");
  });
});

describe("labels are text — colour is never the only signal", () => {
  it("every quality has non-empty text", () => {
    const cases = [
      viewFreshness("2026-01-01T00:00:09.000Z", CONFIG, NOW),
      viewFreshness("2026-01-01T00:00:00.000Z", CONFIG, NOW),
      viewFreshness(null, CONFIG, NOW),
      viewFreshness("bad", CONFIG, NOW),
      viewFreshness("2026-01-01T00:00:09.000Z", null, NOW),
    ];
    for (const view of cases) {
      expect(freshnessLabel(view).length).toBeGreaterThan(0);
    }
  });

  it("stale reads as STALE", () => {
    expect(freshnessLabel(viewFreshness("2026-01-01T00:00:00.000Z", CONFIG, NOW))).toBe("STALE");
  });

  it("missing reads as UNAVAILABLE", () => {
    expect(freshnessLabel(viewFreshness(null, CONFIG, NOW))).toBe("UNAVAILABLE");
  });
});

describe("formatAge", () => {
  it("returns null when age is not assessable", () => {
    expect(formatAge(null)).toBeNull();
  });

  it("uses milliseconds below a second", () => {
    expect(formatAge(400)).toBe("400 ms ago");
  });

  it("uses seconds with one decimal", () => {
    expect(formatAge(13_400)).toBe("13.4 s ago");
  });

  it("uses minutes and seconds beyond a minute", () => {
    expect(formatAge(125_000)).toBe("2 m 5 s ago");
  });
});
