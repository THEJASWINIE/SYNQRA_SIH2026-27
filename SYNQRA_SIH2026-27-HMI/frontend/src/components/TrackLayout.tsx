/**
 * Resizable HMI decks — drag a gutter to resize a panel, the way a window edge resizes.
 *
 * ============================================================================
 *  PRESENTATION STATE ONLY.
 *
 *  Track sizes are per-viewer layout preferences. They are not vehicle state, they do not
 *  pass through the AppStateStore, and they never reach the backend. The page still never
 *  scrolls: the deck stays viewport-bound and the tracks trade space between themselves.
 * ============================================================================
 *
 *  useTrackLayout(deck, specs)  -> { style, ...handlers }   spread `style` on the grid
 *  <TrackGutter layout track edge/>                          an explicitly placed grid item
 *
 *  Drag: pointer capture, so the drag survives crossing the WebGL canvas or an iframe.
 *  Double-click: reset that track to its CSS default.  Arrow keys: +/- TRACK_STEP_PX.
 */

import {
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  clampTrack,
  growSign,
  parseTrackPx,
  sanitizeStoredSizes,
  TRACK_STEP_PX,
  type TrackSizes,
  type TrackSpec,
  trackStyle,
} from "../state/trackLayout";

const STORAGE_PREFIX = "fog.hmi.tracks.";

export interface TrackLayout {
  /** Spread on the grid element. Carries `--track-*` for resized tracks only. */
  style: CSSProperties;
  specs: Record<string, TrackSpec>;
  sizes: TrackSizes;
  setTrack(name: string, px: number, gridSizePx: number): void;
  resetTrack(name: string): void;
}

function readStored(deck: string, specs: Record<string, TrackSpec>): TrackSizes {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + deck);
    return raw ? sanitizeStoredSizes(JSON.parse(raw), specs) : {};
  } catch {
    return {};
  }
}

function writeStored(deck: string, sizes: TrackSizes): void {
  try {
    if (Object.keys(sizes).length === 0) localStorage.removeItem(STORAGE_PREFIX + deck);
    else localStorage.setItem(STORAGE_PREFIX + deck, JSON.stringify(sizes));
  } catch {
    /* private window / blocked storage: sizes simply do not persist */
  }
}

export function useTrackLayout(deck: string, specs: Record<string, TrackSpec>): TrackLayout {
  const [sizes, setSizes] = useState<TrackSizes>(() => readStored(deck, specs));

  useEffect(() => {
    writeStored(deck, sizes);
  }, [deck, sizes]);

  const setTrack = useCallback(
    (name: string, px: number, gridSizePx: number) => {
      const spec = specs[name];
      if (!spec) return;
      setSizes((prev) => ({ ...prev, [name]: clampTrack(px, spec, gridSizePx) }));
    },
    [specs],
  );

  const resetTrack = useCallback((name: string) => {
    setSizes((prev) => {
      if (!(name in prev)) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  const style = useMemo(() => trackStyle(sizes) as CSSProperties, [sizes]);

  return { style, specs, sizes, setTrack, resetTrack };
}

/** The grid this gutter resizes: its nearest ancestor flagged `data-track-grid`. */
function gridOf(el: HTMLElement): HTMLElement | null {
  return el.closest<HTMLElement>("[data-track-grid]");
}

/** Current used size of a track, read back from the grid (works for fr defaults too). */
function currentPx(grid: HTMLElement, spec: TrackSpec): number | null {
  const computed = getComputedStyle(grid);
  const template = spec.axis === "x" ? computed.gridTemplateColumns : computed.gridTemplateRows;
  return parseTrackPx(template, spec.index);
}

function gridSizePx(grid: HTMLElement, spec: TrackSpec): number {
  const rect = grid.getBoundingClientRect();
  return spec.axis === "x" ? rect.width : rect.height;
}

export function TrackGutter({
  layout,
  track,
  edge,
  label,
  className = "",
}: {
  layout: TrackLayout;
  /** Track name from the layout's specs. */
  track: string;
  /** Which edge of the track this gutter sits on: pointer travel past an `end` edge grows it. */
  edge: "start" | "end";
  label: string;
  /** Placement class (grid-column / grid-row) supplied by the owning deck's CSS. */
  className?: string;
}) {
  const spec = layout.specs[track];
  const drag = useRef<{ startPos: number; startPx: number; gridPx: number } | null>(null);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!spec || event.button !== 0) return;
    const grid = gridOf(event.currentTarget);
    if (!grid) return;
    const startPx = currentPx(grid, spec);
    if (startPx === null) return;
    drag.current = {
      startPos: spec.axis === "x" ? event.clientX : event.clientY,
      startPx,
      gridPx: gridSizePx(grid, spec),
    };
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      /* no active pointer with that id (synthetic events): the drag still tracks moves over the gutter */
    }
    event.preventDefault();
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!spec || !drag.current) return;
    const pos = spec.axis === "x" ? event.clientX : event.clientY;
    const delta = (pos - drag.current.startPos) * growSign(edge);
    layout.setTrack(track, drag.current.startPx + delta, drag.current.gridPx);
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!spec) return;
    const grow =
      spec.axis === "x"
        ? { ArrowRight: 1, ArrowLeft: -1 }[event.key]
        : { ArrowDown: 1, ArrowUp: -1 }[event.key];
    if (grow === undefined) return;
    const grid = gridOf(event.currentTarget);
    if (!grid) return;
    const startPx = currentPx(grid, spec);
    if (startPx === null) return;
    layout.setTrack(track, startPx + grow * growSign(edge) * TRACK_STEP_PX, gridSizePx(grid, spec));
    event.preventDefault();
  };

  if (!spec) return null;
  return (
    <div
      className={`track-gutter track-gutter-${spec.axis} ${className}`.trim()}
      role="separator"
      aria-orientation={spec.axis === "x" ? "vertical" : "horizontal"}
      aria-label={`${label} — drag to resize, double-click to reset`}
      title={`${label}: drag to resize · double-click to reset`}
      tabIndex={0}
      data-track={track}
      data-edge={edge}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={() => layout.resetTrack(track)}
      onKeyDown={onKeyDown}
    />
  );
}
