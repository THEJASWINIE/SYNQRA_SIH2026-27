/**
 * Resizable grid tracks — the pure part.
 *
 * Every HMI deck is a CSS grid whose side columns (and, on the operator deck, two rows)
 * are sized by custom properties: `--track-<name>`. Dragging a gutter writes a pixel value
 * into that property; the grid does the rest. Nothing here is vehicle state: track sizes
 * are per-viewer presentation state and never leave the browser.
 *
 * The DOM-facing hook and the gutter element live in `components/TrackLayout.tsx`; this
 * module is DOM-free so the arithmetic can be tested in the node environment.
 */

export type TrackAxis = "x" | "y";

export interface TrackSpec {
  /** Which grid template list the track lives in. */
  axis: TrackAxis;
  /** Index into the resolved `grid-template-columns` / `-rows` list. */
  index: number;
  /** Hard floor in CSS px: the panel stays readable. */
  minPx: number;
  /** Hard ceiling in CSS px, further capped by `CENTRE_SHARE` of the grid. */
  maxPx: number;
}

export type TrackSizes = Readonly<Record<string, number>>;

/** Keyboard step for a focused gutter. */
export const TRACK_STEP_PX = 16;

/** A side track may never take more than this share of the grid: the centre stays dominant. */
export const CENTRE_SHARE = 0.6;

/** Clamp a requested size to the spec and to the grid it lives in. */
export function clampTrack(sizePx: number, spec: TrackSpec, gridSizePx: number): number {
  if (!Number.isFinite(sizePx)) return spec.minPx;
  const cap =
    Number.isFinite(gridSizePx) && gridSizePx > 0
      ? Math.min(spec.maxPx, Math.floor(gridSizePx * CENTRE_SHARE))
      : spec.maxPx;
  return Math.round(Math.min(Math.max(sizePx, spec.minPx), Math.max(cap, spec.minPx)));
}

/**
 * Read one resolved track from a computed `grid-template-columns` / `-rows` string, which
 * the browser reports as a space-separated list of used pixel values ("232px 813px 272px").
 * Returns null when the list is not resolved (e.g. `none`) or the index is out of range.
 */
export function parseTrackPx(template: string, index: number): number | null {
  const parts = template.trim().split(/\s+/);
  const part = parts[index];
  if (!part || !/^-?\d+(\.\d+)?px$/.test(part)) return null;
  const value = Number.parseFloat(part);
  return Number.isFinite(value) ? value : null;
}

/** The CSS custom property a track is published under. */
export function trackVar(name: string): string {
  return `--track-${name}`;
}

/** Inline style for a grid: only tracks the viewer has actually resized are set. */
export function trackStyle(sizes: TrackSizes): Record<string, string> {
  const style: Record<string, string> = {};
  for (const [name, px] of Object.entries(sizes)) style[trackVar(name)] = `${px}px`;
  return style;
}

/**
 * Validate stored sizes: unknown tracks are dropped, non-finite values are dropped, and
 * every kept value is clamped to its spec (a stale or hand-edited entry cannot hide a
 * panel). Anything unparseable yields an empty set, never a throw.
 */
export function sanitizeStoredSizes(raw: unknown, specs: Record<string, TrackSpec>): TrackSizes {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return {};
  const out: Record<string, number> = {};
  for (const [name, spec] of Object.entries(specs)) {
    const value = (raw as Record<string, unknown>)[name];
    if (typeof value === "number" && Number.isFinite(value)) {
      out[name] = clampTrack(value, spec, Number.NaN);
    }
  }
  return out;
}

/** Sign of pointer travel that GROWS a track: end-edge gutters grow with +delta, start-edge shrink. */
export function growSign(edge: "start" | "end"): 1 | -1 {
  return edge === "end" ? 1 : -1;
}
