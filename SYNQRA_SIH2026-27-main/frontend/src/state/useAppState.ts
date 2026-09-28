/**
 * Application state hooks — M4. M4D-D.
 *
 * `useSyncExternalStore` is a React built-in and is exactly the external-store
 * subscription primitive, so no state library is involved. It also gives correct
 * behaviour under concurrent rendering, which a `useState` + subscribe pairing does not.
 *
 * Components import from here. They never import a provider.
 */

import { useSyncExternalStore } from "react";
import type { FreshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import { type FreshnessView, viewFreshness } from "./freshness";
import { useHmi } from "./ProviderHost";

/** The whole normalized application state. */
export function useAppState(): AppState {
  const { store } = useHmi();
  // Server snapshot is the same object: the store is created before first render and
  // holds a valid empty state, so SSR and hydration observe identical data.
  return useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
}

/**
 * The render clock, in epoch milliseconds.
 *
 * Read from `AppState.clock.now`, which the display ticker advances. Components never
 * call `Date.now()` themselves — a second clock would make ages disagree between panels
 * rendered in the same pass.
 */
export function useNowMs(): number {
  const state = useAppState();
  const parsed = Date.parse(state.clock.now);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function useFreshnessConfig(): FreshnessConfig | null {
  return useHmi().freshness;
}

/** Freshness for one supplied timestamp, against the configured threshold if there is one. */
export function useFreshness(timestamp: string | null | undefined): FreshnessView {
  const config = useFreshnessConfig();
  const nowMs = useNowMs();
  return viewFreshness(timestamp, config, nowMs);
}
