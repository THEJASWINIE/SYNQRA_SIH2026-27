/**
 * Freshness, timestamp and quality tests — M2.
 * Covers required test categories 5, 8, 9, 10, 11.
 *
 * The clock and the staleness threshold are both INJECTED. Nothing here depends on wall
 * time, and nothing depends on the unresolved real value of
 * PLACEHOLDER_NFR003_STALE_TIMEOUT_MS (AMB-014).
 */

import { describe, expect, it } from "vitest";
import { freshnessConfig, readFreshnessConfig } from "../config/freshness";
import type { Clock } from "./sourced";
import { hasValue, invalid, missing, refresh, supplied } from "./sourced";
import { ageMsFrom, FUTURE_TOLERANCE_MS, normalizeTimestamp } from "./timestamps";

const NOW_ISO = "2026-01-01T00:00:00.000Z";
const NOW_MS = Date.parse(NOW_ISO);
const fixedClock: Clock = () => NOW_MS;

/** Injected threshold — deliberately arbitrary, since the real value is unresolved. */
const THRESHOLD_MS = 5_000;
const config = freshnessConfig(THRESHOLD_MS);

describe("timestamp normalization (category 5)", () => {
  it("accepts a UTC timestamp with Z", () => {
    const r = normalizeTimestamp("2025-12-31T23:59:59.000Z", NOW_MS);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.iso).toBe("2025-12-31T23:59:59.000Z");
  });

  it("accepts an explicit numeric offset", () => {
    const r = normalizeTimestamp("2025-12-31T23:59:59.000+05:30", NOW_MS);
    expect(r.ok).toBe(true);
  });

  it("rejects a timestamp with no timezone rather than assuming local time", () => {
    const r = normalizeTimestamp("2025-12-31T23:59:59.000", NOW_MS);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.reason).toBe("NO_TIMEZONE");
  });

  it("rejects an unparseable string", () => {
    const r = normalizeTimestamp("not-a-timestamp-Z", NOW_MS);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.reason).toBe("UNPARSEABLE");
  });

  it("rejects an absent timestamp", () => {
    expect(normalizeTimestamp(null, NOW_MS).ok).toBe(false);
    expect(normalizeTimestamp(undefined, NOW_MS).ok).toBe(false);
    expect(normalizeTimestamp("", NOW_MS).ok).toBe(false);
  });

  it("rejects a non-string", () => {
    const r = normalizeTimestamp(1234567890, NOW_MS);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.reason).toBe("NOT_A_STRING");
  });

  it("rejects a timestamp too far in the future", () => {
    const future = new Date(NOW_MS + FUTURE_TOLERANCE_MS + 1_000).toISOString();
    const r = normalizeTimestamp(future, NOW_MS);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.reason).toBe("TOO_FAR_FUTURE");
  });

  it("tolerates small clock skew within the future tolerance", () => {
    const slightlyAhead = new Date(NOW_MS + 1_000).toISOString();
    expect(normalizeTimestamp(slightlyAhead, NOW_MS).ok).toBe(true);
  });
});

describe("age calculation with an injected clock (category 8)", () => {
  it("computes an exact age", () => {
    expect(ageMsFrom(NOW_MS - 3_000, NOW_MS)).toBe(3_000);
  });

  it("is never negative for a future timestamp", () => {
    expect(ageMsFrom(NOW_MS + 10_000, NOW_MS)).toBe(0);
  });

  it("is never NaN", () => {
    expect(Number.isNaN(ageMsFrom(Number.NaN, NOW_MS))).toBe(false);
    expect(ageMsFrom(Number.NaN, NOW_MS)).toBe(0);
    expect(ageMsFrom(NOW_MS, Number.NaN)).toBe(0);
  });
});

describe("quality states (category 9)", () => {
  it("OK for a current valid datum", () => {
    const d = supplied(1, NOW_ISO, NOW_MS, "SRC", config, fixedClock);
    expect(d.quality).toBe("OK");
    expect(d.value).toBe(1);
    expect(d.ageMs).toBe(0);
  });

  it("STALE for a valid datum past the threshold", () => {
    const old = NOW_MS - (THRESHOLD_MS + 1);
    const d = supplied(1, new Date(old).toISOString(), old, "SRC", config, fixedClock);
    expect(d.quality).toBe("STALE");
  });

  it("MISSING when nothing was supplied", () => {
    const d = missing<number>("SRC");
    expect(d.quality).toBe("MISSING");
    expect(d.value).toBeNull();
  });

  it("INVALID when a payload was supplied but failed validation", () => {
    const d = invalid<number>(NOW_ISO, "SRC");
    expect(d.quality).toBe("INVALID");
    expect(d.value).toBeNull();
  });

  it("all four states are reachable and distinct", () => {
    const states = new Set([
      supplied(1, NOW_ISO, NOW_MS, "S", config, fixedClock).quality,
      supplied(1, NOW_ISO, NOW_MS - THRESHOLD_MS - 1, "S", config, fixedClock).quality,
      missing<number>().quality,
      invalid<number>().quality,
    ]);
    expect(states).toEqual(new Set(["OK", "STALE", "MISSING", "INVALID"]));
  });
});

describe("staleness transition (category 10)", () => {
  it("flips OK to STALE as age crosses the configured threshold", () => {
    const producedAt = NOW_MS;
    const iso = new Date(producedAt).toISOString();

    const justInside: Clock = () => producedAt + THRESHOLD_MS;
    const justOutside: Clock = () => producedAt + THRESHOLD_MS + 1;

    expect(supplied(1, iso, producedAt, "S", config, justInside).quality).toBe("OK");
    expect(supplied(1, iso, producedAt, "S", config, justOutside).quality).toBe("STALE");
  });

  it("a STALE datum KEEPS its value for rendering", () => {
    const old = NOW_MS - (THRESHOLD_MS + 10_000);
    const d = supplied(42, new Date(old).toISOString(), old, "S", config, fixedClock);
    expect(d.quality).toBe("STALE");
    expect(d.value).toBe(42);
    expect(hasValue(d)).toBe(true);
  });

  it("ages on its own as the clock advances with no new data (NFR-012)", () => {
    const producedAt = NOW_MS;
    const fresh = supplied(
      7,
      new Date(producedAt).toISOString(),
      producedAt,
      "S",
      config,
      () => producedAt,
    );
    expect(fresh.quality).toBe("OK");

    const later = refresh(fresh, config, () => producedAt + THRESHOLD_MS + 1);
    expect(later.quality).toBe("STALE");
    expect(later.value).toBe(7);
  });
});

describe("MISSING is distinct from INVALID and STALE (category 11)", () => {
  it("MISSING and INVALID are different qualities", () => {
    expect(missing<number>().quality).not.toBe(invalid<number>().quality);
  });

  it("a malformed payload must never become MISSING", () => {
    // The datum arrived and failed validation. That is INVALID, not MISSING.
    const d = invalid<number>(NOW_ISO, "SRC");
    expect(d.quality).toBe("INVALID");
    expect(d.quality).not.toBe("MISSING");
  });

  it("INVALID is never simultaneously treated as STALE", () => {
    const ancient = NOW_MS - 10 * (THRESHOLD_MS + 1);
    const d = invalid<number>(new Date(ancient).toISOString(), "SRC");
    expect(d.quality).toBe("INVALID");
    // Even re-evaluated against a much later clock, it stays INVALID.
    const later = refresh(d, config, () => NOW_MS + 1_000_000);
    expect(later.quality).toBe("INVALID");
    expect(later.ageMs).toBe(0);
  });

  it("MISSING stays MISSING regardless of elapsed time", () => {
    const d = missing<number>();
    const later = refresh(d, config, () => NOW_MS + 1_000_000);
    expect(later.quality).toBe("MISSING");
  });

  it("MISSING has no value; STALE does", () => {
    const old = NOW_MS - (THRESHOLD_MS + 1);
    expect(hasValue(missing<number>())).toBe(false);
    expect(hasValue(supplied(1, new Date(old).toISOString(), old, "S", config, fixedClock))).toBe(
      true,
    );
  });
});

describe("freshness configuration refuses to invent a threshold (PAD-G, AMB-014)", () => {
  it("fails rather than defaulting when the placeholder is unset", () => {
    const result = readFreshnessConfig({});
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.reason).toContain("PLACEHOLDER_NFR003_STALE_TIMEOUT_MS");
  });

  it("fails on a non-numeric value", () => {
    const result = readFreshnessConfig({
      VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS: "soon",
    });
    expect(result.ok).toBe(false);
  });

  it("fails on a non-positive value", () => {
    const result = readFreshnessConfig({
      VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS: "0",
    });
    expect(result.ok).toBe(false);
  });

  it("accepts an explicitly configured value but never marks it authoritative", () => {
    const result = readFreshnessConfig({
      VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS: "5000",
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.config.staleTimeoutMs).toBe(5000);
    expect(result.config.isAuthoritative).toBe(false);
  });

  it("an explicitly built config is also non-authoritative", () => {
    expect(freshnessConfig(1234).isAuthoritative).toBe(false);
  });
});
