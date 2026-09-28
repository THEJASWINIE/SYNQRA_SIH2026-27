/**
 * Architectural boundary guards — Phase 8 §23.
 *
 * These scan the real screen sources rather than a reconstruction of them. They exist
 * because each boundary below has already been crossed at least once in this project, and
 * a crossing is invisible in rendered output: a screen that computes its own safe speed
 * looks exactly like one that was given a correct value.
 *
 * SCOPE IS DELIBERATELY NARROW. Only the boundaries below, each of which would be an
 * architectural regression rather than a style preference. Wording, ordering and layout
 * are not policed here — that is what the per-screen tests do.
 *
 * The per-screen scans in diagnostics.test.tsx, digitalTwin.test.tsx and
 * safetyEnvironment.test.tsx are unaffected and still run; this covers the whole set.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SCREEN_DIR = "src/screens";

/** Every production screen, discovered rather than listed, so a new one is covered too. */
const SCREENS = readdirSync(SCREEN_DIR)
  .filter((name) => name.endsWith(".tsx") && !name.includes(".test."))
  .sort();

/** Strip comments, so prose that NAMES a forbidden thing does not count as doing it. */
function code(name: string): string {
  return readFileSync(join(SCREEN_DIR, name), "utf-8")
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("screens do not compute safety (§23)", () => {
  it("finds the screens to scan", () => {
    expect(SCREENS.length).toBeGreaterThan(10);
    expect(SCREENS).toContain("SafetyEnvironment.tsx");
    expect(SCREENS).toContain("DispatchSlots.tsx");
  });

  it("no screen computes a minimum — v_safe is solved by Task 2, never here", () => {
    for (const name of SCREENS) {
      expect(code(name), `${name} computes a minimum`).not.toContain("Math.min");
    }
  });

  it("no screen computes a stopping distance", () => {
    for (const name of SCREENS) {
      const body = code(name);
      // S_stop = v*tau + v^2/(2*a) needs a square or a root somewhere.
      expect(body, `${name} uses a square root`).not.toContain("Math.sqrt");
      expect(body, `${name} raises a power`).not.toContain("Math.pow");
      expect(body, `${name} raises a power`).not.toContain("**");
    }
  });
});

describe("screens own no transport (§23)", () => {
  it("no screen calls fetch directly — the API clients are the only callers", () => {
    for (const name of SCREENS) {
      expect(code(name), `${name} calls fetch`).not.toMatch(/\bfetch\s*\(/);
    }
  });

  it("no screen constructs a WebSocket — the provider owns the one connection", () => {
    for (const name of SCREENS) {
      expect(code(name), `${name} constructs a WebSocket`).not.toContain("new WebSocket");
    }
  });

  it("no screen starts a polling loop of its own", () => {
    for (const name of SCREENS) {
      expect(code(name), `${name} starts an interval`).not.toContain("setInterval");
    }
  });

  it("submitCommand is the single command transport, used by exactly one screen", () => {
    const users = SCREENS.filter((name) => code(name).includes("submitCommand"));
    expect(users).toEqual(["DispatchSlots.tsx"]);
  });

  it("fetchObservability is called by the shared host, never by a screen", () => {
    for (const name of SCREENS) {
      expect(code(name), `${name} fetches observability`).not.toContain("fetchObservability");
    }
    // The one legitimate caller is the provider host, outside src/screens.
    expect(readFileSync("src/state/ProviderHost.tsx", "utf-8")).toContain("fetchObservability");
  });
});

describe("one interpretation of data state (Phase 8)", () => {
  it("no screen re-implements the provenance label", () => {
    // The tell is a screen deciding for itself what HARDWARE means. Three screens each had
    // their own version before Phase 8, and all three disagreed about the same field.
    for (const name of SCREENS) {
      expect(code(name), `${name} re-implements provenance`).not.toContain('=== "HARDWARE"');
    }
  });

  it("no screen infers communication state from the presence of a vehicle", () => {
    for (const name of SCREENS) {
      const body = code(name);
      expect(body, `${name} fakes a connected link`).not.toContain('"CONNECTED" : "UNKNOWN"');
      expect(body, `${name} reads comm state directly`).not.toContain(
        "provenance?.communication_state",
      );
    }
  });

  it("dataStatus derives no freshness of its own", () => {
    const body = readFileSync("src/state/dataStatus.ts", "utf-8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    // It reads verdicts. It must never compute an age or consult a clock.
    expect(body).not.toContain("Date.now");
    expect(body).not.toContain("Date.parse");
    expect(body).not.toContain("setInterval");
    expect(body).not.toContain("staleTimeoutMs");
  });
});
