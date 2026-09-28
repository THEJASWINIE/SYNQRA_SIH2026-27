/**
 * Mine-Cast — spatial view of the canonical Digital Twin.
 *
 * ==========================================================================
 *  ONE BACKEND. ONE CANONICAL TWIN. FOUR CLIENT VIEWS.
 *
 *  Control Room HMI (index.html)      ──┐
 *  TRUCK_01 HMI     (truck01.html)    ──┤
 *  TRUCK_02 HMI     (truck02.html)    ──┼──> SAME BACKEND / SAME CANONICAL TWIN
 *  Mine-Cast        (mine-cast.html)  ──┘
 *
 *  Mine-Cast mounts `ProviderHost` exactly as `VehicleHmiApp` does. `ProviderHost` is the
 *  ONLY module in this application permitted to import a concrete data provider, so there
 *  is one ingestion path and one store no matter how many views are open. Mine-Cast does
 *  not fetch telemetry, does not open a WebSocket, and does not poll: it reads `AppState`
 *  and projects it.
 * ==========================================================================
 *
 * READ-ONLY BY CONSTRUCTION
 *
 * There is no command control anywhere in `src/minecast/`, and no module here imports
 * `submitCommand`. Commanding a vehicle stays in the operational consoles, where the
 * operator is authenticated and their vehicle assignment is authorized server-side, fail
 * closed. A viewer that could also drive a truck would be a second command path, and the
 * project has exactly one.
 *
 * THE SPATIAL VIEW
 *
 * The centre column holds the WebGL scene, loaded on demand behind `MineCanvas`. It shows
 * a SYNTHETIC landform - captioned as such over the viewport itself - the published
 * coordinate extent (the only real geometry in it), synthetic operational corridors, and
 * the Twin's two trucks at their canonical SCENE_METRES demonstration positions. No route
 * state, haul-road state or communication link is drawn: each needs evidence the Twin does
 * not supply, and a placeholder for any of them would be a fabrication.
 *
 * MINECAST-03 lays the layer rail and the map controls over the scene itself, so the map
 * keeps the width the side columns would otherwise take. Both rails are VIEW controls.
 */

import { lazy, type ReactNode, Suspense, useEffect, useRef, useState } from "react";

import { BackendHealth } from "../components/BackendHealth";
import { StatusBadge } from "../components/primitives";
import { ProviderHost, useHmi } from "../state/ProviderHost";
import { useAppState } from "../state/useAppState";
import { providerStatusToken } from "../theme/statusTokens";
import { FleetPanel } from "./FleetPanel";
import { CORRIDOR_DISCLOSURE } from "./haulRoads";
import { LayerPanel } from "./LayerPanel";
import { Legend } from "./Legend";
import { MiniMap } from "./MiniMap";
import { type MineCastFeedState, projectMineCast } from "./minecastProjection";
import { type CameraCommand, type CameraRequest, useMineCastStore } from "./minecastStore";
import { ProvenancePanel } from "./ProvenancePanel";
import { MORPHOLOGY_DISCLOSURE } from "./pitMorphology";
import {
  drawablePositions,
  type SpatialPosition,
  spatialPositions,
  undrawablePositions,
} from "./spatialPosition";
import { TERRAIN_PROVENANCE, VERTICAL_EXAGGERATION } from "./terrainField";
import { VehiclePanel } from "./VehiclePanel";

import "../theme/hmi.css";

/**
 * The WebGL scene, loaded on demand.
 *
 * `lazy` is load-bearing, not an optimisation. It keeps Three.js out of the server render
 * — which is what lets this shell be tested in the project's Node environment without
 * jsdom or a WebGL context (M4D-C) — and code-splits the 3D bundle off the initial page.
 */
const MineCanvas = lazy(() => import("./MineCanvas"));

/** Does this browser actually have WebGL? Answered once, honestly. */
function detectWebgl(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl2") ??
        canvas.getContext("webgl") ??
        canvas.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}

/**
 * The spatial viewport.
 *
 * Three distinct states, each stated in words rather than left to be inferred from an
 * empty rectangle:
 *
 *   * server render / before mount  — the scene has not loaded yet
 *   * no WebGL in this browser      — it cannot load, and why
 *   * loaded                        — the scene, under a persistent synthetic-terrain caption
 *
 * An operator must never be unable to tell "still loading" from "broken" from "there is
 * genuinely nothing to show".
 */
function SpatialViewport({
  site,
  layerVisibility,
  vehiclePositions,
  vehicles,
  cameraRequest,
  selectedVehicleId,
  onSelectVehicle,
  highlightRouteId,
  children,
}: {
  site: Parameters<typeof MineCanvas>[0]["site"];
  layerVisibility: Parameters<typeof MineCanvas>[0]["layerVisibility"];
  vehiclePositions: readonly SpatialPosition[];
  vehicles: Parameters<typeof MineCanvas>[0]["vehicles"];
  cameraRequest: CameraRequest | null;
  selectedVehicleId: string | null;
  onSelectVehicle: (canonicalVehicleId: string) => void;
  /** MINE-ROUTES-02: the selected truck's Twin-stamped route id, for highlighting. */
  highlightRouteId: string | null;
  /** MINECAST-03: DOM rails laid over the scene (layer rail, map controls). */
  children?: ReactNode;
}) {
  const host = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const [webgl, setWebgl] = useState(false);
  const [aspect, setAspect] = useState(16 / 9);

  // Counted, never assumed: the caption below states what was actually drawn.
  const drawn = drawablePositions(vehiclePositions).length;
  const undrawn = undrawablePositions(vehiclePositions);

  useEffect(() => {
    setMounted(true);
    setWebgl(detectWebgl());

    const element = host.current;
    if (!element) return;

    // Track the viewport's own aspect so the initial framing fits the column it is in.
    const measure = () => {
      const rect = element.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) setAspect(rect.width / rect.height);
    };
    measure();

    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="mc-viewport" ref={host}>
      {!mounted ? (
        <div className="mc-canvas-notice" role="status">
          <h2 className="mc-placeholder-title">LOADING SPATIAL VIEW</h2>
          <p className="faint">The 3D scene is fetched on demand.</p>
        </div>
      ) : !webgl ? (
        <div className="mc-canvas-notice" role="note">
          <h2 className="mc-placeholder-title">WEBGL UNAVAILABLE</h2>
          <p>
            This browser reports no WebGL context, so the spatial view cannot be rendered. Every
            operational value remains available in the panels around this area.
          </p>
        </div>
      ) : (
        <Suspense
          fallback={
            <div className="mc-canvas-notice" role="status">
              <h2 className="mc-placeholder-title">LOADING SPATIAL VIEW</h2>
            </div>
          }
        >
          <MineCanvas
            site={site}
            layerVisibility={layerVisibility}
            aspect={aspect}
            vehiclePositions={vehiclePositions}
            vehicles={vehicles}
            cameraRequest={cameraRequest}
            selectedVehicleId={selectedVehicleId}
            onSelectVehicle={onSelectVehicle}
            highlightRouteId={highlightRouteId}
          />
        </Suspense>
      )}

      {children}

      {/*
        THE CAPTION IS PART OF THE VIEW, NOT DECORATION.

        A rendered landform is persuasive in a way a table is not, so the fact that it is
        invented is painted over the viewport itself - visible in any screenshot, and not
        dismissible.
      */}
      <div className="mc-viewport-caption">
        <span className="mc-viewport-synthetic">
          {TERRAIN_PROVENANCE.label} · VERTICAL SCALE {VERTICAL_EXAGGERATION}x
        </span>
        <span className="mc-viewport-synthetic">{MORPHOLOGY_DISCLOSURE}</span>
        <span className="mc-viewport-synthetic">{CORRIDOR_DISCLOSURE}</span>
        <span className="mc-viewport-extent">
          {site.extentLabel} — {site.extentCaveat}
        </span>
        {/*
          MINECAST-01: the marker provenance is painted over the viewport for the same
          reason the synthetic-terrain caption is - a rendered truck on a rendered
          landform is persuasive, and the fact that its position is a Digital Twin
          demonstration value must be visible in any screenshot of it.
        */}
        <span className="mc-viewport-synthetic">
          {drawn === 0
            ? "NO VEHICLE DRAWN — the Digital Twin has placed none."
            : `VEHICLES: ${drawn} DRAWN FROM DIGITAL TWIN SIMULATION (SCENE_METRES) — not GNSS, not a measured position.`}
        </span>
        {undrawn.length > 0 ? (
          <span className="faint">
            NOT DRAWN: {undrawn.map((position) => position.displayId).join(", ")} — the Twin
            supplied no drawable scene position.
          </span>
        ) : null}
      </div>
    </div>
  );
}

/**
 * MINECAST-03 — the map-control rail.
 *
 * Fit, zoom and two named camera orientations. Each button records a request in the view
 * store; `MineScene` applies it through the same MapControls the mouse drives. Text on
 * every button, so the rail survives greyscale and a screen reader.
 */
const MAP_COMMANDS: readonly { readonly command: CameraCommand; readonly label: string; readonly title: string }[] = [
  { command: "FIT", label: "FIT", title: "Fit the whole site in view" },
  { command: "ZOOM_IN", label: "+", title: "Zoom in" },
  { command: "ZOOM_OUT", label: "−", title: "Zoom out" },
  { command: "PLAN_VIEW", label: "PLAN", title: "Plan view, north up" },
  { command: "OBLIQUE_VIEW", label: "3D", title: "Oblique operations view" },
];

function MapControlRail({ onCommand }: { onCommand: (command: CameraCommand) => void }) {
  return (
    <div className="mc-map-rail" role="toolbar" aria-label="Map controls">
      {MAP_COMMANDS.map((entry) => (
        <button
          key={entry.command}
          type="button"
          className="mc-map-btn"
          title={entry.title}
          onClick={() => onCommand(entry.command)}
        >
          {entry.label}
        </button>
      ))}
    </div>
  );
}

/** Non-colour cue for the feed state, so it is never carried by colour alone. */
const FEED_GLYPH: Record<MineCastFeedState, string> = {
  LIVE: "●",
  DEGRADED: "◐",
  REPLAY: "▶",
  OFFLINE: "○",
};

const FEED_DETAIL: Record<MineCastFeedState, string> = {
  LIVE: "Every configured vehicle is reporting current telemetry.",
  DEGRADED: "At least one vehicle is stale or absent. Values on screen are not all current.",
  REPLAY: "A recording is driving this view. Nothing here is current.",
  OFFLINE: "No data feed. Values on screen are the last received, not the current state.",
};

/**
 * The shell itself, separate from the provider boundary.
 *
 * Exported so tests can mount it against a controlled store through `HmiContext`, exactly
 * as the control-room screens are tested - the real code path, not a reconstruction of
 * it. Production mounts `MineCastApp`, which supplies the real `ProviderHost`.
 */
export function MineCastContent() {
  const state = useAppState();
  const { freshness, freshnessReason } = useHmi();
  const { view, selectVehicle, toggleLayer, togglePanel, requestCamera } = useMineCastStore();

  const minecast = projectMineCast(state);

  /*
    MINECAST-01 — the trucks' places in the scene.

    `spatialPositions` is the existing shared contract: it decides, per vehicle, whether
    there is anything fit to draw and in which frame. Mine-Cast adds no coordinate of its
    own here, and holds no fallback for a vehicle the Twin has not placed.
  */
  const vehiclePositions = spatialPositions(minecast.vehicles, minecast.site);

  const selected =
    minecast.vehicles.find((vehicle) => vehicle.canonicalVehicleId === view.selectedVehicleId) ??
    null;

  return (
    <div className="hmi minecast" data-feed-state={minecast.feedState}>
      {/* ---- TOP BAR ---- */}
      <header className="mc-topbar">
        <div className="mc-brand">
          <span className="mc-brand-product">FOG-ORCHESTRATOR</span>
          <span className="mc-brand-site">NMDC BAILADILA — DEPOSIT-5</span>
        </div>
        {/* MINECAST-03: what this deck IS, stated as identity - not as a data claim. */}
        <div className="mc-identity" aria-label="Mine-Cast Digital Twin">
          <span className="mc-identity-name">MINE-CAST</span>
          <span className="mc-identity-kind">DIGITAL TWIN · SIMULATION VIEW</span>
        </div>

        <div className="mc-topbar-slot">
          {/*
            LIVE is a claim about freshness, so it is derived from the fleet's own data
            state - never from the fact that a socket happens to be open.
          */}
          <span className="mc-feed" data-feed={minecast.feedState}>
            <span aria-hidden="true">{FEED_GLYPH[minecast.feedState]}</span> {minecast.feedState}
          </span>
          <span className="faint">{FEED_DETAIL[minecast.feedState]}</span>
        </div>

        <div className="mc-topbar-slot">
          <span className="mc-topbar-label">LAST UPDATE</span>
          <span className="mono">{minecast.observedAtIso ?? "UNAVAILABLE"}</span>
        </div>

        <div className="mc-topbar-slot">
          <span className="mc-topbar-label">CONNECTION</span>
          <StatusBadge token={providerStatusToken(state.connection.status)} />
          {minecast.connectionError ? (
            <span className="faint">{minecast.connectionError}</span>
          ) : null}
        </div>

        <div className="mc-topbar-slot">
          <span className="mc-topbar-label">PROVIDER</span>
          <span className="mono">{minecast.mode}</span>
          {minecast.scenarioName ? <span className="faint">{minecast.scenarioName}</span> : null}
        </div>

        <div className="mc-topbar-slot">
          <BackendHealth />
        </div>
      </header>

      {freshness === null ? (
        <div className="hmi-banner" role="status">
          <div className="hmi-banner-title">▲ FRESHNESS THRESHOLD NOT CONFIGURED</div>
          <p>
            Data age is still shown. Stale classification is <strong>not evaluated</strong>{" "}
            (AMB-014), so this view cannot promise that anything labelled current really is.
          </p>
          {freshnessReason ? <p className="faint">{freshnessReason}</p> : null}
        </div>
      ) : null}

      {/* ---- BODY: left operations · centre spatial · right inspector ---- */}
      <div className="mc-body">
        <aside className="mc-left">
          <FleetPanel
            minecast={minecast}
            selectedVehicleId={view.selectedVehicleId}
            onSelect={selectVehicle}
          />
          <Legend />
          {/* Secondary context, collapsed so the map keeps the column's attention. */}
          <details className="mc-collapsible" open={view.panels.miniMap}>
            <summary onClick={(event) => { event.preventDefault(); togglePanel("miniMap"); }}>
              SITE CONTEXT
            </summary>
            <MiniMap minecast={minecast} />
          </details>
        </aside>

        <section className="mc-centre" aria-label="Mine site spatial view">
          <SpatialViewport
            site={minecast.site}
            layerVisibility={view.layerVisibility}
            vehiclePositions={vehiclePositions}
            vehicles={minecast.vehicles}
            cameraRequest={view.cameraRequest}
            selectedVehicleId={view.selectedVehicleId}
            onSelectVehicle={selectVehicle}
            highlightRouteId={selected?.scenePose?.routeId ?? null}
          >
            {/*
              MINECAST-03 — rails over the map.

              Layer switches and camera buttons sit on the scene, operations-map style,
              so the map keeps the width the side columns would otherwise take. Both are
              VIEW controls: nothing here changes, filters or invents operational data.
            */}
            <div className={`mc-layer-rail${view.panels.layers ? "" : " mc-layer-rail-collapsed"}`}>
              <button
                type="button"
                className="mc-rail-toggle"
                onClick={() => togglePanel("layers")}
                aria-expanded={view.panels.layers}
              >
                {view.panels.layers ? "LAYERS ▾" : "LAYERS ▸"}
              </button>
              {view.panels.layers ? (
                <LayerPanel
                  layers={minecast.layers}
                  visibility={view.layerVisibility}
                  onToggle={toggleLayer}
                />
              ) : null}
            </div>

            <MapControlRail onCommand={requestCamera} />
          </SpatialViewport>
        </section>

        <aside className="mc-right">
          <VehiclePanel vehicle={selected} />
          <details className="mc-collapsible" open={view.panels.provenance}>
            <summary onClick={(event) => { event.preventDefault(); togglePanel("provenance"); }}>
              PROVENANCE
            </summary>
            <ProvenancePanel minecast={minecast} />
          </details>
        </aside>
      </div>

      {/* ---- BOTTOM ---- */}
      <footer className="mc-bottombar">
        <span>
          {minecast.site.operator} · {minecast.site.name}
        </span>
        <span className="faint">
          Read-only view. Commands are issued from the vehicle and control-room consoles, where the
          operator is authenticated and authorized server-side.
        </span>
      </footer>
    </div>
  );
}

export function MineCastApp() {
  return (
    <ProviderHost>
      <MineCastContent />
    </ProviderHost>
  );
}
