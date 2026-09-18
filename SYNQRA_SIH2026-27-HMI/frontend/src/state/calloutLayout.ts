/**
 * Callout slot assignment — deterministic label de-collision shared by the 2D plan and
 * the 3D scene.
 *
 * DIGITAL-TWIN-OPERATIONAL-FLOW-01. When two trucks are close (a junction, the ramp
 * access, the loading loop) their callouts overlapped. This decides, for every vehicle,
 * which SLOT its callout hangs in - and nothing else. The vehicle position is never
 * touched: the marker stays exactly on the canonical Twin pose, only the label's anchor
 * moves and a leader line joins the two.
 *
 * Deterministic by construction:
 *   - no randomness, no time, no per-frame state;
 *   - vehicles are grouped by proximity (`nearM`, scene metres), then ordered by
 *     canonical id within a group, and the slot is a pure function of that rank;
 *   - a vehicle near nobody keeps the DEFAULT slot, so labels never wander when the
 *     fleet is spread out;
 *   - the same input after a reload, or with the array in any order, yields the same map.
 *
 * Pure: no React, no DOM, no Three.js.
 */

export type CalloutSlot = "DEFAULT" | "LEFT" | "RIGHT" | "LEFT_HIGH" | "RIGHT_HIGH";

export interface CalloutSubject {
  readonly id: string;
  /** Scene metres (the canonical pose). Read only. */
  readonly x: number;
  readonly y: number;
}

/** Vehicles closer than this (scene metres) share a cluster and get distinct slots. */
export const CALLOUT_NEAR_M = 320;

/** Slot order within a cluster, by canonical-id rank. Four is plenty for a two-truck demo. */
const CLUSTER_SLOTS: readonly CalloutSlot[] = ["LEFT", "RIGHT", "LEFT_HIGH", "RIGHT_HIGH"];

/**
 * Unit offset of a slot, in "label units": x to the right, y up (screen sense). The
 * renderer scales this into its own pixels or metres. DEFAULT is the renderer's own
 * customary placement (right of the marker in 2D, above the mast in 3D).
 */
export const SLOT_OFFSET: Readonly<Record<CalloutSlot, { readonly dx: number; readonly dy: number }>> = {
  DEFAULT: { dx: 0, dy: 0 },
  // Alternating sides AND heights, so two neighbours separate on both axes even when
  // the renderer's sideways reach is short at its current zoom.
  LEFT: { dx: -1, dy: 0.3 },
  RIGHT: { dx: 1, dy: 0.9 },
  LEFT_HIGH: { dx: -1, dy: 1.5 },
  RIGHT_HIGH: { dx: 1, dy: 2.1 },
};

/**
 * Slot per vehicle id. Clusters are the connected components of the "closer than
 * `nearM`" relation, so three trucks in a row all separate even if the ends are far apart.
 */
export function calloutSlots(
  subjects: readonly CalloutSubject[],
  nearM: number = CALLOUT_NEAR_M,
): ReadonlyMap<string, CalloutSlot> {
  // Sort a COPY by id so the result never depends on the caller's array order.
  const sorted = [...subjects].sort((a, b) => a.id.localeCompare(b.id));
  const clusterOf = new Map<string, number>();
  let next = 0;
  for (const s of sorted) {
    if (clusterOf.has(s.id)) continue;
    // Flood-fill this vehicle's proximity component.
    const stack = [s];
    clusterOf.set(s.id, next);
    while (stack.length > 0) {
      const cur = stack.pop() as CalloutSubject;
      for (const other of sorted) {
        if (clusterOf.has(other.id)) continue;
        if (Math.hypot(other.x - cur.x, other.y - cur.y) < nearM) {
          clusterOf.set(other.id, next);
          stack.push(other);
        }
      }
    }
    next += 1;
  }

  const size = new Map<number, number>();
  for (const c of clusterOf.values()) size.set(c, (size.get(c) ?? 0) + 1);

  const rank = new Map<number, number>();
  const out = new Map<string, CalloutSlot>();
  for (const s of sorted) {
    const c = clusterOf.get(s.id) as number;
    if ((size.get(c) ?? 1) < 2) {
      out.set(s.id, "DEFAULT");
      continue;
    }
    const r = rank.get(c) ?? 0;
    rank.set(c, r + 1);
    out.set(s.id, CLUSTER_SLOTS[r % CLUSTER_SLOTS.length] as CalloutSlot);
  }
  return out;
}
