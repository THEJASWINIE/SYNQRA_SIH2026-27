/**
 * Operational state legend.
 *
 * Names the five states the spatial view will use for roads, corridors and markers, so
 * the colour scheme is documented on screen rather than learned by guessing.
 *
 * ==========================================================================
 *  THE LEGEND DESCRIBES A SCHEME. IT DOES NOT ASSERT A STATE.
 *
 *  Nothing here reads vehicle data, and nothing here claims any road or vehicle currently
 *  IS one of these states. Colour is assigned in the spatial layers (Pass 3+) strictly
 *  from Twin-supplied route and safety state, never animated or randomised.
 * ==========================================================================
 *
 * Every swatch pairs its colour with a GLYPH and a word, so state is never carried by
 * colour alone (accessibility, and legible on a washed-out control-room projector).
 *
 * Plain React, no WebGL, so it renders under `renderToString` (M4D-C).
 */

import { Panel } from "../components/primitives";

export interface LegendEntry {
  readonly id: string;
  readonly label: string;
  readonly glyph: string;
  readonly meaning: string;
}

export const LEGEND_ENTRIES: readonly LegendEntry[] = [
  {
    id: "NORMAL",
    label: "Normal",
    glyph: "━",
    meaning: "Available for haulage. No restriction supplied.",
  },
  {
    id: "CAUTION",
    label: "Caution",
    glyph: "┅",
    meaning: "A supplied constraint applies. Reduced speed or attention required.",
  },
  {
    id: "DEGRADED",
    label: "Degraded / restricted",
    glyph: "┄",
    meaning: "Supplied as degraded or restricted. Not fully available.",
  },
  {
    id: "HIGH_RISK",
    label: "High risk / restricted",
    glyph: "╍",
    meaning: "Supplied high risk. Restricted until the constraint clears.",
  },
  {
    id: "SELECTED",
    label: "Selected",
    glyph: "▬",
    meaning: "The operator's current selection. A view state, not an operational state.",
  },
];

export function Legend() {
  return (
    <Panel title="Legend">
      <ul className="mc-legend">
        {LEGEND_ENTRIES.map((entry) => (
          <li key={entry.id} className="mc-legend-row" data-state={entry.id}>
            <span
              className={`mc-legend-swatch mc-legend-${entry.id.toLowerCase()}`}
              aria-hidden="true"
            >
              {entry.glyph}
            </span>
            <span className="mc-legend-label">{entry.label}</span>
            <span className="mc-legend-meaning faint">{entry.meaning}</span>
          </li>
        ))}
      </ul>
      <p className="mc-note faint">
        Colour is assigned from Twin-supplied route and safety state only. No road state is
        animated, randomised or inferred in this view.
      </p>
    </Panel>
  );
}
