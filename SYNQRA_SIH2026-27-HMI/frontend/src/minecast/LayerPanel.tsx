/**
 * Layer drawer.
 *
 * ==========================================================================
 *  A TOGGLE THAT DRAWS NOTHING SAYS SO.
 *
 *  Pass 1 has no 3D scene, so every spatial layer here reports NOT BUILT and its switch
 *  is disabled. The alternative - a switch that flips happily while nothing appears -
 *  would teach an operator that a layer is on when it is not, which is the same class of
 *  defect as a fabricated sensor reading.
 *
 *  `implemented` comes from the layer catalogue in `minecastProjection.ts`, so a layer
 *  becomes operable by gaining a renderer, never by editing this file.
 * ==========================================================================
 *
 * Each row also carries the PROVENANCE the layer's geometry would have. Synthetic mine
 * geometry is labelled SYNTHETIC_FOR_DEMO here, before it is ever drawn, so nobody can
 * mistake an invented pit for NMDC survey data.
 *
 * Plain React, no WebGL, so it renders under `renderToString` (M4D-C).
 */

import { Panel } from "../components/primitives";
import type { LayerDescriptor, LayerId } from "./minecastProjection";

export function LayerPanel({
  layers,
  visibility,
  onToggle,
}: {
  layers: readonly LayerDescriptor[];
  visibility: Readonly<Record<LayerId, boolean>>;
  onToggle: (layerId: LayerId) => void;
}) {
  return (
    <Panel title="Layers">
      <ul className="mc-layer-list">
        {layers.map((layer) => {
          const checked = visibility[layer.id] ?? false;
          return (
            <li
              key={layer.id}
              className={layer.implemented ? "mc-layer" : "mc-layer mc-layer-unbuilt"}
              data-layer-id={layer.id}
              data-implemented={String(layer.implemented)}
            >
              <label className="mc-layer-row">
                <input
                  type="checkbox"
                  checked={checked}
                  // Disabled while no renderer exists: the control must not imply capability.
                  disabled={!layer.implemented}
                  aria-label={`${layer.label} layer`}
                  onChange={() => onToggle(layer.id)}
                />
                <span className="mc-layer-label">{layer.label}</span>
                <span className="mc-layer-provenance">{layer.provenance}</span>
                {!layer.implemented ? <span className="mc-layer-tag">NOT BUILT</span> : null}
              </label>
              <div className="mc-layer-note faint">{layer.note}</div>
            </li>
          );
        })}
      </ul>
      <p className="mc-note faint">
        Layer visibility is view state only in this pass. No spatial renderer exists yet, so a layer
        marked NOT BUILT draws nothing regardless of this switch.
      </p>
    </Panel>
  );
}
