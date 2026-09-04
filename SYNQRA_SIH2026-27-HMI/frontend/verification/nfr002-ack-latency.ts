/**
 * NFR-002 acknowledgement-latency measurement — M11.
 *
 * Run:  npx vite-node verification/nfr002-ack-latency.ts
 *
 * ==========================================================================
 *  WHAT IS MEASURED, AND WHAT IS NOT.
 *
 *  NFR-002 speaks of command latency. PAD-B and AMB-008 leave command issuance
 *  OUT OF SCOPE for Task 1, so the only command-shaped path that exists is
 *  `DataProvider.sendAcknowledgement`. That is what is timed here: the interval
 *  from the call to the resulting patch arriving at the store subscriber —
 *  the HMI-internal half of the round trip.
 *
 *  NO COMMAND ISSUANCE IS ADDED BY THIS SCRIPT. It calls only the method that
 *  already ships.
 *
 *  Two limits are stated rather than hidden:
 *    1. There is no transport. The mock provider emits in-process, so this is a
 *       floor for the HMI's own contribution, not an end-to-end figure. The
 *       transport half is M12 (TECH-001).
 *    2. No acknowledgement UI exists (M9D-F, blocked on ROLE-001), so this is
 *       measured at the provider boundary, not from an operator gesture.
 *
 *  The threshold PLACEHOLDER_NFR002_COMMAND_LATENCY is unfilled (AMB-004), so
 *  no verdict is computed. See docs/verification/latency.md.
 * ==========================================================================
 */

import type { Alert } from "../src/contracts/domain";
import { emptyAppState, mergePatch } from "../src/data/patch";
import { MockDataProvider } from "../src/providers/MockDataProvider";
import { manualScheduler } from "../src/providers/scheduler";
import { AppStateStore } from "../src/state/store";

const START_MS = Date.parse("2026-01-01T00:00:00.000Z");
const START_ISO = new Date(START_MS).toISOString();
const SAMPLES = 200;
const WARMUP = 20;

interface Harness {
  provider: MockDataProvider;
  store: AppStateStore;
  alerts: () => Alert[];
  /** Resolves when the next patch reaches the store. */
  onPatch: (fn: () => void) => void;
}

async function harness(scenarioId: string, advanceMs = 20_000): Promise<Harness> {
  const scheduler = manualScheduler(0);
  const provider = new MockDataProvider({
    clock: () => START_MS + scheduler.nowMs(),
    scheduler,
  });

  const store = new AppStateStore(START_ISO);
  let state = emptyAppState(START_ISO);
  let listener: (() => void) | null = null;

  provider.subscribe((patch) => {
    state = mergePatch(state, patch);
    store.applyPatch(patch, new Date(START_MS + scheduler.nowMs()).toISOString());
    listener?.();
  });

  const loaded = provider.loadScenario(scenarioId);
  if (!loaded.ok) throw new Error(`scenario ${scenarioId} did not load`);
  await provider.connect();
  scheduler.advance(advanceMs);

  return {
    provider,
    store,
    alerts: () => state.alerts,
    onPatch: (fn) => {
      listener = fn;
    },
  };
}

function stats(samples: number[]) {
  const sorted = [...samples].sort((a, b) => a - b);
  const at = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] ?? 0;
  return {
    n: sorted.length,
    min: sorted[0] ?? 0,
    p50: at(0.5),
    p95: at(0.95),
    p99: at(0.99),
    max: sorted[sorted.length - 1] ?? 0,
    mean: sorted.reduce((a, b) => a + b, 0) / sorted.length,
  };
}

const ms = (x: number) => x.toFixed(4);

async function main(): Promise<void> {
  console.log("NFR-002 acknowledgement-latency measurement — M11");
  console.log(`node ${process.version} · ${process.platform} ${process.arch}`);
  console.log(`samples=${SAMPLES} warmup=${WARMUP}`);
  console.log("");

  const h = await harness("envelope-violation");
  const supplied = h.alerts();
  console.log(`scenario "envelope-violation" supplies ${supplied.length} alert(s)`);

  const target = supplied.find((a) => a.acknowledgeable);
  if (!target) {
    console.log("NO ACKNOWLEDGEABLE ALERT SUPPLIED — measurement not possible.");
    return;
  }
  console.log(`target alert: ${target.alertId} (${target.severity} ${target.category})`);
  console.log("");

  const samples: number[] = [];
  for (let i = 0; i < WARMUP + SAMPLES; i += 1) {
    const patched = new Promise<number>((resolve) => {
      const t0 = performance.now();
      h.onPatch(() => resolve(performance.now() - t0));
      void h.provider.sendAcknowledgement(target.alertId, `operator-${i}`);
    });
    const elapsed = await patched;
    if (i >= WARMUP) samples.push(elapsed);
  }

  const s = stats(samples);
  console.log(
    `ack call -> patch at store        n=${s.n}  min=${ms(s.min)}  p50=${ms(s.p50)}  ` +
      `p95=${ms(s.p95)}  p99=${ms(s.p99)}  max=${ms(s.max)}  mean=${ms(s.mean)}  (ms)`,
  );

  // The acknowledgement must be OBSERVABLE, not merely fast.
  const after = h.alerts().find((a) => a.alertId === target.alertId);
  console.log("");
  console.log(`Alert.acknowledged after the call: ${JSON.stringify(after?.acknowledged)}`);
  console.log(`Acknowledgement visible on the alert: ${after?.acknowledged ? "YES" : "NO"}`);

  console.log("");
  console.log("Transport: NONE (in-process mock). This is the HMI-side floor only.");
  console.log("Threshold: PLACEHOLDER_NFR002_COMMAND_LATENCY — UNFILLED (AMB-004).");
  console.log("Verdict cannot be computed. See docs/verification/latency.md.");

  await h.provider.disconnect();
}

await main();
