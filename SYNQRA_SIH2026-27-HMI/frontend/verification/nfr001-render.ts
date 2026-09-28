/**
 * NFR-001 render-performance measurement — M11.
 *
 * Run:  npx vite-node verification/nfr001-render.ts
 *
 * ==========================================================================
 *  THIS SCRIPT MEASURES. IT DOES NOT JUDGE.
 *
 *  NFR-001's threshold is the unfilled placeholder PLACEHOLDER_NFR001_REFRESH
 *  (AMB-004). No pass/fail can be computed against a number the specification
 *  does not state, so this reports the measured distribution and stops there.
 *  The verdict is recorded in docs/verification/perf.md as
 *  NOT VERIFIABLE YET.
 *
 *  It is deliberately NOT a vitest file: a timing measurement that runs in the
 *  gating suite either asserts an invented budget or flakes. Neither is wanted.
 * ==========================================================================
 */

import { renderToString } from "react-dom/server";
import { createElement, type ReactNode } from "react";
import type { AppState } from "../src/contracts/appState";
import { emptyAppState, mergePatch } from "../src/data/patch";
import type { ProviderPatch } from "../src/providers/DataProvider";
import { MockDataProvider } from "../src/providers/MockDataProvider";
import { manualScheduler } from "../src/providers/scheduler";
import { Diagnostics } from "../src/screens/Diagnostics";
import { OperationsOverview } from "../src/screens/OperationsOverview";
import { HmiContext } from "../src/state/ProviderHost";
import { AppStateStore } from "../src/state/store";
import { testHmiContext } from "../src/state/testHmiContext";

const START_MS = Date.parse("2026-01-01T00:00:00.000Z");
const START_ISO = new Date(START_MS).toISOString();
const SAMPLES = 200;
const WARMUP = 20;

interface Loaded {
  store: AppStateStore;
  state: AppState;
  patches: ProviderPatch[];
  vehicles: number;
  nodes: number;
}

async function load(scenarioId: string, advanceMs = 20_000): Promise<Loaded> {
  const scheduler = manualScheduler(0);
  const provider = new MockDataProvider({
    clock: () => START_MS + scheduler.nowMs(),
    scheduler,
  });

  const store = new AppStateStore(START_ISO);
  const patches: ProviderPatch[] = [];
  let state = emptyAppState(START_ISO);

  provider.subscribe((patch) => {
    patches.push(patch);
    state = mergePatch(state, patch);
    store.applyPatch(patch, new Date(START_MS + scheduler.nowMs()).toISOString());
  });

  const loaded = provider.loadScenario(scenarioId);
  if (!loaded.ok) throw new Error(`scenario ${scenarioId} did not load`);
  await provider.connect();
  scheduler.advance(advanceMs);
  await provider.disconnect();

  return {
    store,
    state,
    patches,
    vehicles: Object.keys(state.vehicles).length,
    nodes: state.topology.nodes.length,
  };
}

function mount(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: null });
  return renderToString(createElement(HmiContext.Provider, { value }, node));
}

interface Stats {
  n: number;
  min: number;
  p50: number;
  p95: number;
  max: number;
  mean: number;
}

function stats(samples: number[]): Stats {
  const sorted = [...samples].sort((a, b) => a - b);
  const at = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] ?? 0;
  return {
    n: sorted.length,
    min: sorted[0] ?? 0,
    p50: at(0.5),
    p95: at(0.95),
    max: sorted[sorted.length - 1] ?? 0,
    mean: sorted.reduce((a, b) => a + b, 0) / sorted.length,
  };
}

const ms = (x: number) => x.toFixed(3);

function measure(label: string, run: () => void): void {
  for (let i = 0; i < WARMUP; i += 1) run();
  const samples: number[] = [];
  for (let i = 0; i < SAMPLES; i += 1) {
    const t0 = performance.now();
    run();
    samples.push(performance.now() - t0);
  }
  const s = stats(samples);
  console.log(
    `${label.padEnd(34)} n=${s.n}  min=${ms(s.min)}  p50=${ms(s.p50)}  ` +
      `p95=${ms(s.p95)}  max=${ms(s.max)}  mean=${ms(s.mean)}  (ms)`,
  );
}

async function main(): Promise<void> {
  console.log("NFR-001 render measurement — M11");
  console.log(`node ${process.version} · ${process.platform} ${process.arch}`);
  console.log(`samples=${SAMPLES} warmup=${WARMUP}`);
  console.log("");

  for (const scenarioId of ["nominal", "scale"]) {
    const loaded = await load(scenarioId);
    console.log(`--- scenario "${scenarioId}": ${loaded.vehicles} vehicles, ${loaded.nodes} nodes`);

    measure(`S1 render (${scenarioId})`, () => {
      mount(loaded.store, createElement(OperationsOverview, { onSelectVehicle: () => {} }));
    });
    measure(`S6 render (${scenarioId})`, () => {
      mount(loaded.store, createElement(Diagnostics, null));
    });

    // The 1 Hz presentation tick: NFR-001's "refresh" is this plus a re-render.
    let tick = 0;
    measure(`store tick (${scenarioId})`, () => {
      tick += 1000;
      loaded.store.tick(new Date(START_MS + 20_000 + tick).toISOString());
    });

    // Merge cost of one delivery at this scale.
    const last = loaded.patches[loaded.patches.length - 1];
    if (last) {
      measure(`mergePatch (${scenarioId})`, () => {
        mergePatch(loaded.state, last);
      });
    }
    console.log("");
  }

  console.log("Threshold: PLACEHOLDER_NFR001_REFRESH — UNFILLED (AMB-004).");
  console.log("Verdict cannot be computed. See docs/verification/perf.md.");
}

await main();
