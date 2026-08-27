/**
 * Test-only `HmiContextValue` builder — M9.
 *
 * Screens are mounted in tests against a controlled `AppStateStore` through `HmiContext`
 * (M5D-B). Five test files now need that context value, and M9 widened it with the replay
 * fields, so the shape lives in one place rather than being repeated — and re-fixed —
 * five times whenever the context grows.
 *
 * PRODUCTION CODE MUST NOT IMPORT THIS. `ProviderHost` builds the real value; this returns
 * inert defaults whose replay controls do nothing, so a test cannot accidentally drive a
 * replay that was never started.
 */

import type { FreshnessConfig } from "../config/freshness";
import { EventLog } from "./eventLog";
import type { HmiContextValue } from "./ProviderHost";
import type { AppStateStore } from "./store";

const EMPTY_RECORDING = new EventLog().recording();

export interface TestContextOptions {
  store: AppStateStore;
  freshness?: FreshnessConfig | null;
  overrides?: Partial<HmiContextValue>;
}

export function testHmiContext({
  store,
  freshness = null,
  overrides = {},
}: TestContextOptions): HmiContextValue {
  return {
    store,
    freshness,
    freshnessReason: null,
    scenarios: [],
    activeScenarioId: "test",
    selectScenario: () => {},
    recording: EMPTY_RECORDING,
    validationFailures: [],
    replaying: false,
    replayPosition: null,
    enterReplay: () => {},
    exitReplay: () => {},
    replayPlay: () => {},
    replayPause: () => {},
    replayScrubTo: () => {},
    replaySetSpeed: () => {},
    ...overrides,
  };
}
