/**
 * Displayed system mode tests — M8. FR-016, OPS-003, NFR-012, M8D-A.
 *
 * The DEGRADED floor must raise severity and never lower it. The tests that matter most
 * here are the two that prove a supplied LOCAL_SAFE or STOP_UNSAFE survives feed loss:
 * softening a severe supplied mode would be the worst defect this module could carry.
 */

import { describe, expect, it } from "vitest";
import type { ConnectionStatus } from "../contracts/appState";
import { SYSTEM_MODES } from "../contracts/enums";
import { emptyAppState } from "../data/patch";
import { displayedModeFor, displayedSystemMode, isFeedLost, MODE_SOURCE_TEXT } from "./systemMode";

const T = "2026-01-01T00:00:00.000Z";

const FEED_UP: ConnectionStatus[] = ["IDLE", "CONNECTING", "CONNECTED", "RECONNECTING"];
const FEED_LOST: ConnectionStatus[] = ["DISCONNECTED", "ERROR"];

describe("isFeedLost", () => {
  it.each(FEED_LOST)("%s means the feed is lost", (status) => {
    expect(isFeedLost(status)).toBe(true);
  });

  it.each(FEED_UP)("%s does not mean the feed is lost", (status) => {
    expect(isFeedLost(status)).toBe(false);
  });

  it("RECONNECTING is not feed loss — the link is being re-established, not gone", () => {
    expect(isFeedLost("RECONNECTING")).toBe(false);
  });
});

describe("supplied mode passes through untouched while the feed is up", () => {
  it.each(SYSTEM_MODES)("%s is displayed as supplied", (mode) => {
    const result = displayedSystemMode(mode, "CONNECTED");
    expect(result.mode).toBe(mode);
    expect(result.source).toBe("SUPPLIED");
    expect(result.flooredByFeedLoss).toBe(false);
    expect(result.suppliedMode).toBe(mode);
  });

  it("no supplied mode yields null — NEVER a default of NORMAL", () => {
    const result = displayedSystemMode(null, "CONNECTED");
    expect(result.mode).toBeNull();
    expect(result.mode).not.toBe("NORMAL");
    expect(result.source).toBe("NOT_SUPPLIED");
  });

  it("undefined is treated as not supplied, not as NORMAL", () => {
    expect(displayedSystemMode(undefined, "CONNECTED").mode).toBeNull();
  });
});

describe("DEGRADED floor on feed loss (FR-016 AC3, OPS-003, NFR-012)", () => {
  it("NORMAL becomes DEGRADED", () => {
    const result = displayedSystemMode("NORMAL", "DISCONNECTED");
    expect(result.mode).toBe("DEGRADED");
    expect(result.source).toBe("DEGRADED_FLOOR");
    expect(result.flooredByFeedLoss).toBe(true);
  });

  it("CAUTION becomes DEGRADED", () => {
    expect(displayedSystemMode("CAUTION", "DISCONNECTED").mode).toBe("DEGRADED");
  });

  it("a supplied DEGRADED stays DEGRADED, and is not reported as floored", () => {
    const result = displayedSystemMode("DEGRADED", "DISCONNECTED");
    expect(result.mode).toBe("DEGRADED");
    expect(result.source).toBe("SUPPLIED");
    expect(result.flooredByFeedLoss).toBe(false);
  });

  it("a provider ERROR floors the mode just as a disconnect does", () => {
    expect(displayedSystemMode("NORMAL", "ERROR").mode).toBe("DEGRADED");
  });

  it("feed lost with nothing supplied yields DEGRADED, not null and not NORMAL", () => {
    const result = displayedSystemMode(null, "DISCONNECTED");
    expect(result.mode).toBe("DEGRADED");
    expect(result.source).toBe("DEGRADED_FLOOR_NO_SUPPLIED_MODE");
    expect(result.suppliedMode).toBeNull();
  });

  it("the supplied value is always preserved for provenance, never overwritten", () => {
    expect(displayedSystemMode("NORMAL", "DISCONNECTED").suppliedMode).toBe("NORMAL");
  });
});

describe("the floor RAISES severity and never lowers it", () => {
  it("LOCAL_SAFE survives feed loss unchanged", () => {
    const result = displayedSystemMode("LOCAL_SAFE", "DISCONNECTED");
    expect(result.mode).toBe("LOCAL_SAFE");
    expect(result.mode).not.toBe("DEGRADED");
    expect(result.flooredByFeedLoss).toBe(false);
  });

  it("STOP_UNSAFE survives feed loss unchanged", () => {
    const result = displayedSystemMode("STOP_UNSAFE", "DISCONNECTED");
    expect(result.mode).toBe("STOP_UNSAFE");
    expect(result.mode).not.toBe("DEGRADED");
  });

  it("STOP_UNSAFE survives a provider error too", () => {
    expect(displayedSystemMode("STOP_UNSAFE", "ERROR").mode).toBe("STOP_UNSAFE");
  });

  it("no supplied mode is ever softened by feed loss", () => {
    for (const mode of SYSTEM_MODES) {
      for (const status of FEED_LOST) {
        const result = displayedSystemMode(mode, status);
        // Either the supplied mode survives, or it was raised to DEGRADED.
        expect(result.mode === mode || result.mode === "DEGRADED").toBe(true);
        if (result.mode === "DEGRADED" && mode !== "DEGRADED") {
          expect(["NORMAL", "CAUTION"]).toContain(mode);
        }
      }
    }
  });
});

describe("no calculation of an operational mode", () => {
  it("the result is always either the supplied mode or DEGRADED", () => {
    for (const mode of [...SYSTEM_MODES, null]) {
      for (const status of [...FEED_UP, ...FEED_LOST]) {
        const result = displayedSystemMode(mode, status);
        expect(result.mode === mode || result.mode === "DEGRADED" || result.mode === null).toBe(
          true,
        );
      }
    }
  });

  it("is deterministic — the same inputs always give the same result", () => {
    expect(displayedSystemMode("CAUTION", "DISCONNECTED")).toEqual(
      displayedSystemMode("CAUTION", "DISCONNECTED"),
    );
  });

  it("reads no clock and no history", () => {
    const first = displayedSystemMode("NORMAL", "CONNECTED");
    for (let i = 0; i < 5; i += 1) {
      expect(displayedSystemMode("NORMAL", "CONNECTED")).toEqual(first);
    }
  });

  it("every source has explanatory text, so the operator is never guessing", () => {
    for (const source of Object.keys(MODE_SOURCE_TEXT) as (keyof typeof MODE_SOURCE_TEXT)[]) {
      expect(MODE_SOURCE_TEXT[source].length).toBeGreaterThan(0);
    }
  });
});

describe("displayedModeFor — one result every screen shares", () => {
  it("reads the supplied mode and the connection status out of AppState", () => {
    const state = emptyAppState(T);
    state.health = {
      timestamp: T,
      systemMode: "CAUTION",
      connectivity: "CONNECTED",
      fleetCount: 1,
      components: [],
    };
    state.connection = { ...state.connection, status: "CONNECTED" };
    expect(displayedModeFor(state).mode).toBe("CAUTION");
  });

  it("applies the floor from AppState's connection status", () => {
    const state = emptyAppState(T);
    state.health = {
      timestamp: T,
      systemMode: "NORMAL",
      connectivity: "DISCONNECTED",
      fleetCount: 1,
      components: [],
    };
    state.connection = { ...state.connection, status: "DISCONNECTED" };
    const result = displayedModeFor(state);
    expect(result.mode).toBe("DEGRADED");
    // The supplied value in state is untouched.
    expect(state.health.systemMode).toBe("NORMAL");
  });

  it("never mutates AppState", () => {
    const state = emptyAppState(T);
    state.health = {
      timestamp: T,
      systemMode: "NORMAL",
      connectivity: "CONNECTED",
      fleetCount: 0,
      components: [],
    };
    const before = JSON.parse(JSON.stringify(state));
    displayedModeFor(state);
    expect(JSON.parse(JSON.stringify(state))).toEqual(before);
  });

  it("with no health supplied and the feed up, reports not supplied", () => {
    expect(displayedModeFor(emptyAppState(T)).mode).toBeNull();
  });
});
