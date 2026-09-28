/**
 * ProviderHost — M4 (M4D-D) / M12-A.
 *
 * ============================================================================
 *  THIS IS THE ONLY MODULE IN THE APPLICATION THAT IMPORTS CONCRETE PROVIDERS.
 *
 *  A screen or component that imports `MockDataProvider` or `LiveDataProvider`
 *  is a defect, and so is one that receives a provider instance as a prop.
 *  Everything below this boundary reads normalized `AppState` and cannot tell
 *  whether the data came from Mock (M3), Replay (M9) or Live (M12) — which is
 *  precisely what makes those three interchangeable (`DataProvider.ts` property 4).
 * ============================================================================
 */

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { type FreshnessConfig, readFreshnessConfig } from "../config/freshness";
import type { ProviderKind } from "../contracts/appState";
import type { ValidationFailure } from "../data/errors";
import { listScenarios } from "../mocks/registry";
import type { ScenarioDescriptor } from "../mocks/scenarioTypes";
import type { DataProvider } from "../providers/DataProvider";
import { LiveDataProvider } from "../providers/LiveDataProvider";
import { MockDataProvider } from "../providers/MockDataProvider";
import {
  type ReplayPositionState,
  ReplayProvider,
  type ReplaySpeed,
} from "../providers/ReplayProvider";
import type { Recording } from "./eventLog";
import { SessionRecorder } from "./recorder";
import { AppStateStore } from "./store";

/** The scenario the HMI opens with in mock mode. Nominal shows honest empty states (M4D-A). */
export const DEFAULT_SCENARIO_ID = "nominal";

/** Display ticker period. Presentation only — see `AppStateStore.tick`. */
export const TICK_INTERVAL_MS = 1000;

export interface HmiContextValue {
  store: AppStateStore;
  /**
   * Null when AMB-014's threshold is unconfigured. Null is a real state, not an error to
   * paper over: it means staleness is NOT evaluated, and the shell says so.
   */
  freshness: FreshnessConfig | null;
  freshnessReason: string | null;
  scenarios: readonly ScenarioDescriptor[];
  activeScenarioId: string | null;
  selectScenario: (id: string) => void;

  // -- M9 replay ------------------------------------------------------------
  /** The append-only session recording. Empty until something has been observed. */
  recording: Recording;
  /** True while the REPLAY provider is driving the store. */
  replaying: boolean;
  /** Null outside replay. */
  replayPosition: ReplayPositionState | null;
  /**
   * Validation failures recorded by the active provider — READ-ONLY (M10D-B).
   *
   * A copy of what the provider already recorded. Nothing here retries, mutates,
   * re-injects or resets anything, and the provider's behaviour is not altered to
   * populate it. Surfaced so an INVALID payload — the case M2 exists to distinguish from
   * MISSING — is visible on S6 instead of being recorded where nothing can read it (D11).
   */
  validationFailures: readonly ValidationFailure[];
  enterReplay: () => void;
  exitReplay: () => void;
  replayPlay: () => void;
  replayPause: () => void;
  replayScrubTo: (atMs: number) => void;
  replaySetSpeed: (speed: ReplaySpeed) => void;
}

/**
 * Exported ONLY so tests can mount a screen against a controlled store without starting a
 * real provider. Production code must use `useHmi`; a component that reads this context
 * directly, or a second provider of it, is a defect.
 */
export const HmiContext = createContext<HmiContextValue | null>(null);

export function useHmi(): HmiContextValue {
  const context = useContext(HmiContext);
  if (!context) throw new Error("useHmi must be used inside <ProviderHost>");
  return context;
}

export interface ProviderHostProps {
  children: ReactNode;
  /** Overridable for tests. Production opens on the registry default. */
  initialScenarioId?: string;
  /** Provider mode: "MOCK" | "LIVE". Defaults to VITE_PROVIDER env or "MOCK". */
  providerKind?: ProviderKind;
  /** Optional injected LiveDataProvider (for tests and custom transports). */
  liveProvider?: LiveDataProvider;
  /** Optional injected MockDataProvider (for tests). */
  mockProvider?: MockDataProvider;
}

export function ProviderHost({
  children,
  initialScenarioId,
  providerKind: providerKindProp,
  liveProvider: liveProviderProp,
  mockProvider: mockProviderProp,
}: ProviderHostProps) {
  const envKind: ProviderKind =
    import.meta.env.VITE_PROVIDER?.toUpperCase() === "LIVE" ? "LIVE" : "MOCK";
  const targetKind: ProviderKind = providerKindProp ?? envKind;

  const startId = initialScenarioId ?? DEFAULT_SCENARIO_ID;

  // Created once. A provider or store rebuilt on re-render would drop every subscription.
  const storeRef = useRef<AppStateStore | null>(null);
  if (storeRef.current === null) storeRef.current = new AppStateStore(new Date().toISOString());
  const store = storeRef.current;

  const liveWsUrl = import.meta.env.VITE_LIVE_WS_URL?.trim() || null;

  const mockProviderRef = useRef<MockDataProvider | null>(null);
  if (mockProviderRef.current === null)
    mockProviderRef.current = mockProviderProp ?? new MockDataProvider();
  const mockProvider = mockProviderRef.current;

  const liveProviderRef = useRef<LiveDataProvider | null>(null);
  if (liveProviderRef.current === null)
    liveProviderRef.current = liveProviderProp ?? new LiveDataProvider({ url: liveWsUrl });
  const liveProvider = liveProviderRef.current;

  const activeProvider: DataProvider & {
    diagnostics: { validationFailures: readonly ValidationFailure[] };
  } = targetKind === "LIVE" ? liveProvider : mockProvider;

  /**
   * The session recorder. A passive observer of the live provider's patches — it never
   * emits and never writes to the store (M9D-A).
   */
  const recorderRef = useRef<SessionRecorder | null>(null);
  if (recorderRef.current === null) recorderRef.current = new SessionRecorder();
  const recorder = recorderRef.current;

  const replayRef = useRef<ReplayProvider | null>(null);

  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [replayPosition, setReplayPosition] = useState<ReplayPositionState | null>(null);
  const [recordingVersion, setRecordingVersion] = useState(0);

  const freshnessResult = useMemo(() => readFreshnessConfig(), []);
  const freshness = freshnessResult.ok ? freshnessResult.config : null;
  const freshnessReason = freshnessResult.ok ? null : freshnessResult.reason;

  const scenarios = useMemo(() => listScenarios(), []);

  // -- provider wiring ------------------------------------------------------

  useEffect(() => {
    const observe = () => {
      const nowMs = Date.now();
      recorder.observe(store.getSnapshot(), nowMs, new Date(nowMs).toISOString());
      setRecordingVersion((v) => v + 1);
    };

    const unsubscribeUpdates = activeProvider.subscribe((patch) => {
      store.applyPatch(patch, new Date().toISOString());
      observe();
    });
    const unsubscribeStatus = activeProvider.onStatusChange((status, error) => {
      store.setStatus(status, error ? error.message : null);
      observe();
    });

    return () => {
      unsubscribeUpdates();
      unsubscribeStatus();
      void activeProvider.disconnect();
    };
  }, [activeProvider, store, recorder]);

  // -- scenario / live connection lifecycle ---------------------------------

  /**
   * Switching scenarios is a full restart, in this order:
   *
   *   disconnect → reset → load → connect
   *
   * Reset is not optional. Without it, vehicles, alerts and bottlenecks from the previous
   * scenario would survive into the next one and be read as the current state of a
   * different mine. Disconnect comes first so no emission scheduled by the old scenario
   * can land after the reset.
   */
  const switchTo = useCallback(
    async (id: string): Promise<void> => {
      if (replayRef.current) {
        await replayRef.current.disconnect();
        replayRef.current = null;
        setReplaying(false);
        setReplayPosition(null);
      }

      await activeProvider.disconnect();
      store.reset(new Date().toISOString());

      if (targetKind === "LIVE") {
        store.setProvider("LIVE");
        if (liveProvider.transportName === "STUB") {
          store.setScenarioName("Stub Feed — Test Only");
        } else if (liveProvider.transportName === "WEBSOCKET") {
          store.setScenarioName("Live Feed");
        } else {
          store.setScenarioName(null);
        }
        setActiveScenarioId(null);
        try {
          await liveProvider.connect();
        } catch {
          // Status listener already recorded the error
        }
        return;
      }

      store.setProvider("MOCK");
      const loaded = mockProvider.loadScenario(id);
      if (!loaded.ok) {
        store.setStatus("ERROR", loaded.error.message);
        store.setScenarioName(null);
        setActiveScenarioId(null);
        return;
      }

      store.setScenarioName(scenarios.find((s) => s.id === id)?.name ?? id);
      setActiveScenarioId(id);

      try {
        await mockProvider.connect();
      } catch {
        // `connect` rejects with a ProviderError; the status listener already recorded it.
      }
    },
    [activeProvider, targetKind, liveProvider, mockProvider, store, scenarios],
  );

  useEffect(() => {
    void switchTo(startId);
  }, [switchTo, startId]);

  // -- display ticker -------------------------------------------------------

  useEffect(() => {
    const handle = setInterval(() => store.tick(new Date().toISOString()), TICK_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [store]);

  // -- replay lifecycle -----------------------------------------------------

  /**
   * Enter replay: stop the live provider, reset the store, then let the REPLAY provider
   * drive it. Identical shape to a scenario switch (M4D-D) — no screen is aware which
   * provider is connected, which is what FR-017 AC4 requires.
   */
  const enterReplay = useCallback(() => {
    void (async () => {
      if (replayRef.current || !recorder.hasRecording) return;

      await activeProvider.disconnect();
      const replay = new ReplayProvider(recorder.recording());
      replayRef.current = replay;

      replay.subscribe((patch) => store.applyPatch(patch, new Date().toISOString()));
      replay.onStatusChange((status, error) => {
        store.setStatus(status, error ? error.message : null);
      });
      replay.onPositionChange(setReplayPosition);

      store.reset(new Date().toISOString());
      store.setProvider("REPLAY");
      store.setScenarioName(`Replay — ${activeScenarioId ?? "session"}`);
      setReplaying(true);

      try {
        await replay.connect();
      } catch {
        // `connect` rejects with a ProviderError; the status listener recorded it.
      }
    })();
  }, [activeProvider, store, recorder, activeScenarioId]);

  /** Leave replay and return to the active scenario or live feed. */
  const exitReplay = useCallback(() => {
    void (async () => {
      if (!replayRef.current) return;
      await replayRef.current.disconnect();
      replayRef.current = null;
      setReplaying(false);
      setReplayPosition(null);
      store.setProvider(targetKind);
      if (targetKind === "LIVE") {
        store.reset(new Date().toISOString());
        if (liveProvider.transportName === "STUB") {
          store.setScenarioName("Stub Feed — Test Only");
        } else if (liveProvider.transportName === "WEBSOCKET") {
          store.setScenarioName("Live Feed");
        } else {
          store.setScenarioName(null);
        }
        try {
          await liveProvider.connect();
        } catch {
          // Status listener handles it
        }
      } else if (activeScenarioId) {
        await switchTo(activeScenarioId);
      }
    })();
  }, [store, targetKind, liveProvider, switchTo, activeScenarioId]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: recordingVersion is a deliberate dependency so S5 re-renders as the session recording grows
  const value = useMemo<HmiContextValue>(
    () => ({
      store,
      freshness,
      freshnessReason,
      scenarios,
      activeScenarioId,
      selectScenario: (id: string) => void switchTo(id),
      recording: recorder.recording(),
      // A fresh copy each render, so the panel reflects the provider's own record and
      // nothing outside the provider can alter it.
      validationFailures: activeProvider.diagnostics.validationFailures,
      replaying,
      replayPosition,
      enterReplay,
      exitReplay,
      replayPlay: () => replayRef.current?.play(),
      replayPause: () => replayRef.current?.pause(),
      replayScrubTo: (atMs: number) => replayRef.current?.scrubTo(atMs),
      replaySetSpeed: (speed: ReplaySpeed) => replayRef.current?.setSpeed(speed),
    }),
    [
      store,
      activeProvider,
      freshness,
      freshnessReason,
      scenarios,
      activeScenarioId,
      switchTo,
      recorder,
      replaying,
      replayPosition,
      enterReplay,
      exitReplay,
      // `recordingVersion` is a deliberate dependency: the recording is rebuilt when new
      // observations arrive, so S5 re-renders as the session grows.
      recordingVersion,
    ],
  );

  return <HmiContext.Provider value={value}>{children}</HmiContext.Provider>;
}
