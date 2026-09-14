/**
 * Mine-Cast shell — render tests.
 *
 * Rendered with `react-dom/server`'s `renderToString` in the project's Node test
 * environment. NO jsdom, NO Testing Library, no change to the Vitest environment (M4D-C).
 *
 * These assert the things an operator must be able to READ off the screen: that a truck
 * with no position says so, that the coordinate extent carries its caveat, that a layer
 * with no renderer is marked NOT BUILT, and that the shell never prints a reassuring
 * number in place of a missing one.
 *
 * SOFTWARE ONLY. No hardware, no network.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { FleetPanel } from "./FleetPanel";
import { LayerPanel } from "./LayerPanel";
import { Legend } from "./Legend";
import { MineCastContent } from "./MineCastApp";
import { MiniMap } from "./MiniMap";
import { LAYERS, projectMineCast } from "./minecastProjection";
import { initialViewState } from "./minecastStore";
import { ProvenancePanel } from "./ProvenancePanel";
import { VehiclePanel } from "./VehiclePanel";

const T = "2026-09-10T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function vehicle(id: string, speedMps: number | null): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps,
    position: { x: 0, y: 0, segmentId: null, offsetM: 0 },
    accelMps2: null,
    gradeRad: null,
    commConfidence: null,
    frictionEst: null,
    routeId: null,
    timestamp: T,
  } as VehicleState;
}

/** A store seeded the way production seeds it: through `applyPatch`. */
function seededStore(vehicles?: Record<string, VehicleState>): AppStateStore {
  const store = new AppStateStore(T);
  store.applyPatch(
    {
      changes: {
        vehicles: vehicles ?? {
          TRUCK_01: vehicle("TRUCK_01", 4.2),
          TRUCK_02: vehicle("TRUCK_02", 3.8),
        },
      },
    },
    T,
  );
  return store;
}

function minecastOf(vehicles?: Record<string, VehicleState>) {
  return projectMineCast(seededStore(vehicles).getSnapshot());
}

/** Mount the real shell against a controlled store, as the screen tests do. */
function renderShell(vehicles?: Record<string, VehicleState>): string {
  const store = seededStore(vehicles);
  const value = testHmiContext({ store, freshness: CONFIG });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );
  return renderToString(wrap(<MineCastContent />));
}

// ---------------------------------------------------------------------------
// the shell
// ---------------------------------------------------------------------------

describe("Mine-Cast shell", () => {
  it("renders the product and site identity", () => {
    const html = renderShell();
    expect(html).toContain("FOG-ORCHESTRATOR");
    expect(html).toContain("NMDC BAILADILA");
    expect(html).toContain("DEPOSIT-5");
  });

  it("renders a stated loading notice rather than a blank rectangle before mount", () => {
    /*
      Pass 2 replaced the "NOT BUILT" placeholder with the real WebGL viewport. `MineCanvas`
      is lazily loaded and WebGL is detected after mount, so a server render - which is
      exactly what `renderToString` produces - shows the pre-mount notice. An operator (or
      a reader of a screenshot) must always be able to tell "loading" from "broken".
    */
    const html = renderShell();
    expect(html).toContain("LOADING SPATIAL VIEW");
    expect(html).toContain("fetched on demand");
  });

  it("captions the viewport as synthetic terrain, in the markup itself", () => {
    // A rendered landform is persuasive, so the caveat is painted over the viewport and is
    // present even in a server-rendered snapshot.
    const html = renderShell();
    expect(html).toContain("SYNTHETIC TERRAIN");
    expect(html).toContain("NOT SURVEYED");
  });

  it("discloses the synthetic corridors on the viewport and in the provenance panel", () => {
    // Pass 3B. The corridor caveat is painted over the viewport itself, so a screenshot
    // of the road network carries its own provenance.
    const html = renderShell();
    const occurrences =
      html.split("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE").length - 1;
    expect(occurrences).toBeGreaterThanOrEqual(2);
    expect(html).toContain("OPERATIONAL_CORRIDOR");
  });

  it("states in the viewport where the vehicle markers come from", () => {
    // MINECAST-01: the shell fixture carries no scene pose, so the honest statement is
    // that the Twin has placed none. The caption must say so in words either way - an
    // empty viewport must never be indistinguishable from a broken one.
    const html = renderShell();
    expect(html).toContain("NO VEHICLE DRAWN");
    expect(html).toContain("the Digital Twin has placed none");
  });

  it("loads the 3D bundle lazily, so no WebGL is required to render the shell", () => {
    // If `MineCanvas` were statically imported this very test would fail to collect.
    expect(() => renderShell()).not.toThrow();
  });

  it("renders every required panel", () => {
    const html = renderShell();
    expect(html).toContain("Fleet operations");
    expect(html).toContain("Selected vehicle");
    expect(html).toContain("Layers");
    expect(html).toContain("Legend");
    expect(html).toContain("Provenance");
    expect(html).toContain("Site context");
  });

  it("shows both display labels and both canonical ids", () => {
    const html = renderShell();
    expect(html).toContain("T01");
    expect(html).toContain("T02");
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
  });

  it("carries the extent caveat into the rendered output", () => {
    const html = renderShell();
    expect(html).toContain("PUBLISHED COORDINATE EXTENT");
    expect(html).toContain("NOT A LEASE BOUNDARY");
  });

  it("mentions a lease boundary only inside the caveat that denies it", () => {
    const html = renderShell().toUpperCase();
    const occurrences = html.split("LEASE BOUNDARY").length - 1;
    const caveats = html.split("NOT A LEASE BOUNDARY").length - 1;
    expect(occurrences).toBeGreaterThan(0);
    expect(occurrences).toBe(caveats);
  });

  it("renders no command control", () => {
    const html = renderShell();
    for (const word of ["SEND TARGET_SPEED", "CONFIRM STOP", "TARGET SPEED (m/s)"]) {
      expect(html, word).not.toContain(word);
    }
    expect(html).not.toContain('<button type="button" >SEND');
  });

  it("says where commands are issued instead", () => {
    expect(renderShell()).toContain("Read-only view");
  });
});

// ---------------------------------------------------------------------------
// fleet panel
// ---------------------------------------------------------------------------

describe("FleetPanel", () => {
  it("shows the fleet count and both vehicles", () => {
    const html = renderToString(
      <FleetPanel minecast={minecastOf()} selectedVehicleId={null} onSelect={() => {}} />,
    );
    expect(html).toContain("REPORTING");
    expect(html).toContain("T01");
    expect(html).toContain("T02");
  });

  it("keeps a silent truck listed as UNAVAILABLE", () => {
    const html = renderToString(
      <FleetPanel
        minecast={minecastOf({ TRUCK_01: vehicle("TRUCK_01", 4.2) })}
        selectedVehicleId={null}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("T02");
    expect(html).toContain("UNAVAILABLE");
  });

  it("reports safety as UNAVAILABLE rather than inventing a risk level", () => {
    const html = renderToString(
      <FleetPanel minecast={minecastOf()} selectedVehicleId={null} onSelect={() => {}} />,
    );
    expect(html).toContain("SAFETY DATA UNAVAILABLE");
    expect(html).not.toContain("NORMAL RISK");
  });

  it("states that no position can be drawn", () => {
    const html = renderToString(
      <FleetPanel minecast={minecastOf()} selectedVehicleId={null} onSelect={() => {}} />,
    );
    expect(html).toContain("0");
    expect(html).toContain("vehicles have a position that can be");
  });

  it("marks the selected row", () => {
    const html = renderToString(
      <FleetPanel minecast={minecastOf()} selectedVehicleId="TRUCK_01" onSelect={() => {}} />,
    );
    expect(html).toContain("mc-selected");
    expect(html).toContain('aria-pressed="true"');
  });
});

// ---------------------------------------------------------------------------
// vehicle panel
// ---------------------------------------------------------------------------

describe("VehiclePanel", () => {
  it("says nothing is selected when nothing is", () => {
    const html = renderToString(<VehiclePanel vehicle={null} />);
    expect(html).toContain("NO VEHICLE SELECTED");
  });

  it("renders the selected vehicle's label and canonical id", () => {
    const projected = minecastOf().vehicles[0] ?? null;
    const html = renderToString(<VehiclePanel vehicle={projected} />);
    expect(html).toContain("T01");
    expect(html).toContain("TRUCK_01");
  });

  it("renders absent safety values as UNAVAILABLE", () => {
    const projected = minecastOf().vehicles[0] ?? null;
    const html = renderToString(<VehiclePanel vehicle={projected} />);
    expect(html).toContain("V_safe");
    expect(html).toContain("H_safe");
    expect(html).toContain("SAFETY DATA UNAVAILABLE");
  });

  it("shows V2V and V2I as unavailable, with the reason", () => {
    // The seeded store's provider is MOCK, so V2I correctly reports the SIMULATED
    // wording. Either way it is UNAVAILABLE and never CONNECTED — a simulated link is
    // labelled, not promoted. The LIVE wording is asserted in the projection tests.
    const projected = minecastOf().vehicles[0] ?? null;
    const html = renderToString(<VehiclePanel vehicle={projected} />);
    expect(html).toContain("V2V");
    expect(html).toContain("V2I");
    expect(html).toContain("No LoRa frame evidence has reached the Digital Twin");
    expect(html).toContain("SIMULATED V2I");
    expect(html).not.toContain("physical roadside unit</td>");
  });

  it("labels local metres as local, never as latitude or longitude", () => {
    const projected = minecastOf().vehicles[0] ?? null;
    const html = renderToString(<VehiclePanel vehicle={projected} />);
    expect(html).toContain("X (local, m)");
    expect(html).toContain("Y (local, m)");
    expect(html).not.toContain("Latitude");
    expect(html).not.toContain("Longitude");
  });

  it("distinguishes peer presence from a communication link", () => {
    const projected = minecastOf().vehicles[0] ?? null;
    const html = renderToString(<VehiclePanel vehicle={projected} />);
    expect(html).toContain("Peer in Twin");
    expect(html).toContain("PRESENT");
  });
});

// ---------------------------------------------------------------------------
// layer panel
// ---------------------------------------------------------------------------

describe("LayerPanel", () => {
  const view = initialViewState();

  it("lists every required layer", () => {
    const html = renderToString(
      <LayerPanel layers={LAYERS} visibility={view.layerVisibility} onToggle={() => {}} />,
    );
    for (const label of [
      "Terrain",
      "Orthophoto",
      "Published Extent",
      "Pit",
      "Benches",
      "Haul Roads",
      "Ramps",
      "Mine Zones",
      "Vehicles",
      "Routes",
      "Safety",
      "V2V",
      "V2I / RSU",
    ]) {
      expect(html, label).toContain(label);
    }
  });

  it("marks unbuilt layers NOT BUILT and disables their switch", () => {
    const html = renderToString(
      <LayerPanel layers={LAYERS} visibility={view.layerVisibility} onToggle={() => {}} />,
    );
    expect(html).toContain("NOT BUILT");
    expect(html).toContain("disabled");
    expect(html).toContain("No renderer exists yet");
  });

  it("labels synthetic mine geometry SYNTHETIC_FOR_DEMO", () => {
    const html = renderToString(
      <LayerPanel layers={LAYERS} visibility={view.layerVisibility} onToggle={() => {}} />,
    );
    expect(html).toContain("SYNTHETIC_FOR_DEMO");
  });
});

// ---------------------------------------------------------------------------
// legend
// ---------------------------------------------------------------------------

describe("Legend", () => {
  it("names all five states", () => {
    const html = renderToString(<Legend />);
    for (const label of [
      "Normal",
      "Caution",
      "Degraded / restricted",
      "High risk / restricted",
      "Selected",
    ]) {
      expect(html, label).toContain(label);
    }
  });

  it("pairs each state with a non-colour cue", () => {
    const html = renderToString(<Legend />);
    expect(html).toContain("mc-legend-swatch");
    expect(html).toContain('aria-hidden="true"');
  });
});

// ---------------------------------------------------------------------------
// provenance panel
// ---------------------------------------------------------------------------

describe("ProvenancePanel", () => {
  it("distinguishes every provenance class", () => {
    const html = renderToString(<ProvenancePanel minecast={minecastOf()} />);
    for (const cls of [
      "HARDWARE",
      "DERIVED",
      "SOFTWARE_TEST",
      "SYNTHETIC_FOR_DEMO",
      "UNAVAILABLE",
    ]) {
      expect(html, cls).toContain(cls);
    }
  });

  it("cites the published source and area", () => {
    const html = renderToString(<ProvenancePanel minecast={minecastOf()} />);
    expect(html).toContain("NMDC Limited");
    // `renderToString` inserts a comment marker between text and an interpolation, so the
    // area and its unit are asserted separately rather than as one literal.
    expect(html).toContain("540.05");
    expect(html).toContain("Published M.L. area");
    expect(html).toContain("J-11015/261/2007-IA.II(M)");
  });

  it("records the datum as unverified", () => {
    const html = renderToString(<ProvenancePanel minecast={minecastOf()} />);
    expect(html).toContain("ASSUMED_WGS84_UNVERIFIED");
  });

  it("states the hardware verification boundary", () => {
    const html = renderToString(<ProvenancePanel minecast={minecastOf()} />);
    expect(html).toContain("PHYSICAL HARDWARE VERIFICATION");
    expect(html).toContain("No physical GNSS receiver is fitted");
  });

  it("carries the ODbL attribution for open geographic data", () => {
    const html = renderToString(<ProvenancePanel minecast={minecastOf()} />);
    expect(html).toContain("OpenStreetMap");
    expect(html).toContain("ODbL");
  });
});

// ---------------------------------------------------------------------------
// mini-map
// ---------------------------------------------------------------------------

describe("MiniMap", () => {
  it("is inline SVG", () => {
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).toContain("<svg");
    expect(html).not.toContain("<canvas");
  });

  it("captions the extent and its caveat inside the drawing", () => {
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).toContain("PUBLISHED COORDINATE EXTENT");
    expect(html).toContain("NOT A LEASE BOUNDARY");
  });

  it("draws the extent dashed, so it never reads as a surveyed outline", () => {
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).toContain("stroke-dasharray");
  });

  it("plots no vehicle when no geographic position exists", () => {
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).toContain("NO GEOGRAPHIC POSITION");
  });

  it("draws no invented mine geometry", () => {
    // The only shapes are the background, the extent, the north arrow and the scale bar.
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).not.toContain("<polygon");
    expect(html).not.toContain("<polyline");
  });

  it("describes itself for a screen reader", () => {
    const html = renderToString(<MiniMap minecast={minecastOf()} />);
    expect(html).toContain('role="img"');
    expect(html).toContain("aria-label");
  });
});
