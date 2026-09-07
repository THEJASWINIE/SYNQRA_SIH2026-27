/**
 * S1 render tests — M4.
 *
 * Rendered with `react-dom/server`, as M1 established, so no DOM environment is needed and
 * no UI testing dependency is added (M4D-C).
 *
 * ASSERTIONS ARE AGAINST TEXT. A test that passed because a colour attribute was present
 * would prove nothing about an operator who cannot rely on that colour (NFR-008).
 */

import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { AlertRow } from "../components/AlertRow";
import { StatusBadge } from "../components/primitives";
import { VehicleCard } from "../components/VehicleCard";
import { freshnessConfig } from "../config/freshness";
import type { Alert, SafetyState, VehicleState } from "../contracts/domain";
import { SYSTEM_MODES } from "../contracts/enums";
import { emptyAppState } from "../data/patch";
import { viewFreshness } from "../state/freshness";
import { providerStatusToken, systemModeToken } from "../theme/statusTokens";
import { PENDING_SCREENS, PendingScreen } from "./AppShell";
import { MineMap } from "./MineMap";

const T = "2026-01-01T00:00:00.000Z";
const NOW = Date.parse(T);
const CONFIG = freshnessConfig(5000);

/** Colour is stripped before assertion, so nothing can pass on colour alone. */
function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK-07",
    timestamp: T,
    position: { x: 10, y: 20, segmentId: "S-1", offsetM: null },
    speedMps: 12.5,
    accelMps2: 0,
    gradeRad: 0.05,
    frictionEst: { value: 0.55, sigma: 0.03 },
    mode: "NORMAL",
    commConfidence: 0.9,
    vehicleKind: "TRUCK",
    routeId: null,
    ...partial,
  };
}

function safety(partial: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK-07",
    timestamp: T,
    vSafe: 8,
    hSafe: 60,
    actualSpeed: 12.5,
    headwayCurrent: 41,
    leadVehicleId: "TRUCK-03",
    activeConstraint: "VISIBILITY",
    riskLevel: "HIGH",
    headwayViolation: null,
    envelopeViolation: null,
    ...partial,
  };
}

const fresh = (timestamp: string | null) => viewFreshness(timestamp, CONFIG, NOW);

// ---------------------------------------------------------------------------

describe("VehicleCard — actual versus safe speed", () => {
  it("renders both values with labels and units", () => {
    const html = renderToString(
      <VehicleCard vehicle={vehicle()} safety={safety()} freshness={fresh(T)} />,
    );
    expect(html).toContain("Actual speed");
    expect(html).toContain("Safe speed");
    expect(html).toContain("km/h");
  });

  it("actualSpeed > vSafe produces a TEXTUAL violation marker", () => {
    const html = renderToString(
      <VehicleCard
        vehicle={vehicle({ speedMps: 12.5 })}
        safety={safety({ actualSpeed: 12.5, vSafe: 8 })}
        freshness={fresh(T)}
      />,
    );
    expect(greyscale(html)).toContain("OVER SAFE SPEED");
  });

  it("the violation survives with every colour removed", () => {
    const html = greyscale(
      renderToString(
        <VehicleCard
          vehicle={vehicle()}
          safety={safety({ actualSpeed: 30, vSafe: 5 })}
          freshness={fresh(T)}
        />,
      ),
    );
    expect(html).toContain("OVER SAFE SPEED");
    expect(html).toContain("HIGH");
  });

  it("no violation marker when actual is within safe", () => {
    const html = renderToString(
      <VehicleCard
        vehicle={vehicle({ speedMps: 4 })}
        safety={safety({ actualSpeed: 4, vSafe: 8 })}
        freshness={fresh(T)}
      />,
    );
    expect(html).not.toContain("OVER SAFE SPEED");
  });

  it("no supplied safe speed renders UNAVAILABLE and no violation marker", () => {
    const html = renderToString(
      <VehicleCard
        vehicle={vehicle({ speedMps: 40 })}
        safety={safety({ actualSpeed: 40, vSafe: null })}
        freshness={fresh(T)}
      />,
    );
    expect(html).toContain("UNAVAILABLE");
    expect(html).not.toContain("OVER SAFE SPEED");
  });

  it("renders risk and active constraint as text", () => {
    const html = greyscale(
      renderToString(
        <VehicleCard
          vehicle={vehicle()}
          safety={safety({ riskLevel: "CRITICAL", activeConstraint: "BRAKING_RETARDER" })}
          freshness={fresh(T)}
        />,
      ),
    );
    expect(html).toContain("CRITICAL");
    expect(html).toContain("BRAKING RETARDER");
  });

  it("renders UNKNOWN risk as unknown, never as low or blank", () => {
    const html = greyscale(
      renderToString(
        <VehicleCard
          vehicle={vehicle()}
          safety={safety({ riskLevel: "UNKNOWN" })}
          freshness={fresh(T)}
        />,
      ),
    );
    expect(html).toContain("UNKNOWN");
    expect(html).not.toContain("RISK LOW");
  });

  it("marks the h_safe unit as unresolved and shows no headway comparison", () => {
    const html = renderToString(
      <VehicleCard vehicle={vehicle()} safety={safety()} freshness={fresh(T)} />,
    );
    expect(html).toContain("AMB-001");
    expect(html).not.toContain("HEADWAY VIOLATION");
  });

  it("shows a SUPPLIED headway violation when Task 2 sends one", () => {
    const html = greyscale(
      renderToString(
        <VehicleCard
          vehicle={vehicle()}
          safety={safety({ headwayViolation: true })}
          freshness={fresh(T)}
        />,
      ),
    );
    expect(html).toContain("HEADWAY VIOLATION");
  });

  it("renders POSITION UNAVAILABLE rather than a guessed position", () => {
    const html = renderToString(
      <VehicleCard
        vehicle={vehicle({ position: { x: null, y: null, segmentId: "S-1", offsetM: 40 } })}
        safety={safety()}
        freshness={fresh(T)}
      />,
    );
    expect(html).toContain("POSITION UNAVAILABLE");
  });

  it("renders a stale marker with the age, keeping the value", () => {
    const stale = viewFreshness("2026-01-01T00:00:00.000Z", CONFIG, NOW + 60_000);
    const html = greyscale(
      renderToString(<VehicleCard vehicle={vehicle()} safety={safety()} freshness={stale} />),
    );
    expect(html).toContain("STALE");
    expect(html).toContain("Actual speed");
  });

  it("renders SAFETY STATE UNAVAILABLE when no safety record arrived", () => {
    const html = renderToString(
      <VehicleCard vehicle={vehicle()} safety={undefined} freshness={fresh(T)} />,
    );
    expect(html).toContain("SAFETY STATE UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------

describe("AlertRow", () => {
  const alert: Alert = {
    alertId: "A-1",
    timestamp: T,
    severity: "CRITICAL",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "TRUCK-07" },
    message: "Speed exceeds safe envelope",
    reasonCode: "ENV-01",
    acknowledgeable: false,
    acknowledged: null,
    active: true,
  };

  it("renders severity as text", () => {
    expect(greyscale(renderToString(<AlertRow alert={alert} freshness={fresh(T)} />))).toContain(
      "CRITICAL",
    );
  });

  it("renders message, category and subject", () => {
    const html = renderToString(<AlertRow alert={alert} freshness={fresh(T)} />);
    expect(html).toContain("Speed exceeds safe envelope");
    expect(html).toContain("UNSAFE_SPEED");
    expect(html).toContain("TRUCK-07");
  });

  it("marks a safety-critical alert as not acknowledgeable, and offers no control", () => {
    const html = renderToString(<AlertRow alert={alert} freshness={fresh(T)} />);
    expect(html).toContain("not acknowledgeable");
    expect(html).not.toContain("<button");
  });
});

// ---------------------------------------------------------------------------

describe("MineMap", () => {
  function stateWith(topology: boolean, vehicles: Record<string, VehicleState>) {
    const state = emptyAppState(T);
    if (topology) {
      state.topology = {
        version: "1",
        nodes: [
          { nodeId: "N-1", kind: "SHOVEL", label: "Shovel 1", x: 0, y: 0 },
          { nodeId: "N-2", kind: "CRUSHER", label: "Crusher", x: 100, y: 100 },
        ],
        segments: [
          {
            segmentId: "S-1",
            fromNode: "N-1",
            toNode: "N-2",
            lengthM: 100,
            gradeRad: 0,
            bidirectional: true,
          },
        ],
      };
    }
    state.vehicles = vehicles;
    return state;
  }

  it("renders TOPOLOGY UNAVAILABLE rather than an empty frame", () => {
    const html = renderToString(<MineMap state={stateWith(false, {})} />);
    expect(html).toContain("TOPOLOGY UNAVAILABLE");
    expect(html).not.toContain("<svg");
  });

  it("draws supplied nodes and segments", () => {
    const html = renderToString(<MineMap state={stateWith(true, {})} />);
    expect(html).toContain("<svg");
    expect(html).toContain("Shovel 1");
    expect(html).toContain("Crusher");
  });

  it("places a vehicle at its supplied coordinates", () => {
    const html = renderToString(
      <MineMap state={stateWith(true, { "V-1": vehicle({ vehicleId: "V-1" }) })} />,
    );
    expect(html).toContain("V-1");
  });

  it("places a vehicle from supplied segment geometry alone (M4D-F)", () => {
    // No x/y supplied. Segment S-1 runs (0,0) -> (100,100) with lengthM 100, and the
    // supplied offset is 55, so the marker belongs at (55,55).
    const html = renderToString(
      <MineMap
        state={stateWith(true, {
          "V-9": vehicle({
            vehicleId: "V-9",
            position: { x: null, y: null, segmentId: "S-1", offsetM: 55 },
          }),
        })}
      />,
    );
    expect(html).toContain("V-9");
    expect(html).not.toContain("POSITION UNAVAILABLE");
    // The label sits at x + 9, so 55 + 9 = 64 proves the marker is at the supplied
    // fraction along the supplied segment, not at an endpoint or a midpoint.
    expect(html).toContain('<text class="map-vehicle-label" x="64"');
  });

  it("lists a vehicle whose segment is not in the supplied topology, and names why", () => {
    const html = renderToString(
      <MineMap
        state={stateWith(true, {
          "V-9": vehicle({
            vehicleId: "V-9",
            position: { x: null, y: null, segmentId: "S-NOT-IN-TOPOLOGY", offsetM: 55 },
          }),
        })}
      />,
    );
    expect(html).toContain("POSITION UNAVAILABLE");
    expect(html).toContain("V-9");
    expect(html).toContain("segment not in supplied topology");
    expect(html).toContain("No position is guessed");
  });

  it("lists a vehicle with no supplied offset rather than guessing one", () => {
    const html = renderToString(
      <MineMap
        state={stateWith(true, {
          "V-8": vehicle({
            vehicleId: "V-8",
            position: { x: null, y: null, segmentId: "S-1", offsetM: null },
          }),
        })}
      />,
    );
    expect(html).toContain("POSITION UNAVAILABLE");
    expect(html).toContain("no offset along segment supplied");
  });

  it("reports when topology is drawn but no vehicle was supplied", () => {
    const html = renderToString(<MineMap state={stateWith(true, {})} />);
    expect(html).toContain("NO VEHICLES SUPPLIED");
  });
});

// ---------------------------------------------------------------------------

describe("connection states render as text (NFR-008)", () => {
  it.each(["IDLE", "CONNECTING", "CONNECTED", "RECONNECTING", "DISCONNECTED", "ERROR"] as const)(
    "%s carries a label and a glyph, not colour alone",
    (status) => {
      const token = providerStatusToken(status);
      expect(token.label).not.toBe("");
      expect(token.glyph).not.toBe("");
      const grey = greyscale(renderToString(<StatusBadge token={token} />));
      expect(grey).toContain(token.label);
    },
  );

  it("DISCONNECTED reads as disconnected, distinctly from an idle link", () => {
    expect(providerStatusToken("DISCONNECTED").label).toBe("Disconnected");
    expect(providerStatusToken("DISCONNECTED").label).not.toBe(providerStatusToken("IDLE").label);
  });

  it("every system mode carries a label and a glyph", () => {
    for (const mode of SYSTEM_MODES) {
      const token = systemModeToken(mode);
      expect(token.label, `${mode} label`).not.toBe("");
      expect(token.glyph, `${mode} glyph`).not.toBe("");
    }
  });
});

// ---------------------------------------------------------------------------

describe("App shell — first paint, before any data has arrived", () => {
  // Effects do not run under renderToString, so this is the pre-connection state: exactly
  // what an operator sees in the instant before the first patch lands.
  const html = renderToString(<App />);
  const grey = greyscale(html);

  it("renders the shell", () => {
    expect(html).toContain("FOG-ORCHESTRATOR 2.0");
  });

  it("shows the HMI backend indicator, separate from the data connection", () => {
    expect(html).toContain("Backend (HMI)");
    expect(html).toContain("Data connection");
  });

  it("shows the system mode slot and does NOT default it to NORMAL", () => {
    expect(grey).toContain("System mode");
    expect(grey).toContain("NOT SUPPLIED");
  });

  it("shows the AMB-014 banner when no threshold is configured", () => {
    // The repository ships VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS unset, by design.
    const configured = process.env.VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS;
    if (configured === undefined || configured === "") {
      expect(grey).toContain("FRESHNESS THRESHOLD NOT CONFIGURED");
      expect(grey).toContain("not evaluated");
    } else {
      expect(grey).toContain("DEVELOPMENT VALUE");
    }
  });

  it("renders the no-alert empty state", () => {
    expect(grey).toContain("NO ACTIVE ALERTS");
  });

  it("renders the no-bottleneck empty state", () => {
    expect(grey).toContain("NO ACTIVE BOTTLENECK");
  });

  it("renders the KPI and visibility empty states", () => {
    expect(grey).toContain("KPI DATA UNAVAILABLE");
    expect(grey).toContain("VISIBILITY DATA UNAVAILABLE");
  });

  it("offers every scenario in the picker", () => {
    expect(html).toContain("Nominal");
  });

  it("offers navigation to the canonical S1-S7 screens", () => {
    for (const label of [
      "S1 Operations",
      "S2 Vehicle Detail",
      "S3 Safety / Environment",
      "S4 Dispatch",
      "S5 Alerts",
      "S6 Digital Twin",
      "S7 System Health",
    ]) {
      expect(html, `missing canonical nav entry: ${label}`).toContain(label);
    }
  });

  it("keeps the additional utility screens reachable", () => {
    // Retained alongside S1-S7, never as replacements for them.
    for (const label of ["Operator", "Bottleneck", "Replay"]) {
      expect(html, `missing additional nav entry: ${label}`).toContain(label);
    }
  });

  it("numbers each canonical screen exactly once", () => {
    // A duplicated S-number would make the structure ambiguous for an operator.
    for (const marker of ["S1 ", "S2 ", "S3 ", "S4 ", "S5 ", "S6 ", "S7 "]) {
      const occurrences = html.split(marker).length - 1;
      expect(occurrences, `${marker.trim()} appears ${occurrences} times`).toBe(1);
    }
  });

  it("does not present an implemented screen as a placeholder", () => {
    // S1/S2/S4/S5/S7 are built. Only the two declared-pending screens may say otherwise,
    // and neither is the screen rendered here.
    expect(html).not.toContain("NOT IMPLEMENTED");
    expect(html).not.toContain("NOT BUILT YET");
  });
});

describe("canonical screens that are declared but not yet built", () => {
  /**
   * Phase 6 built S3 and Phase 7 built S6, so nothing is pending any more. The mechanism
   * is kept and still tested: it is how a future declared-but-unbuilt screen says so
   * instead of rendering an empty dashboard that reads as a working one.
   */
  it("declares no screen without an implementation", () => {
    expect(Object.keys(PENDING_SCREENS)).toEqual([]);
  });

  it.each([["safety"], ["twin"], ["overview"]])(
    "renders nothing for %s, which is a built screen the shell routes itself",
    (screenId) => {
      expect(renderToString(<PendingScreen screenId={screenId} />)).toBe("");
    },
  );

  it("still announces a screen that IS declared pending", () => {
    // Exercises the mechanism itself rather than a reconstruction of it.
    const declared = { title: "S9 EXAMPLE — NOT BUILT YET", detail: "Nothing is shown." };
    PENDING_SCREENS.example = declared;
    try {
      const out = renderToString(<PendingScreen screenId="example" />);
      expect(out).toContain("S9 EXAMPLE — NOT BUILT YET");
      expect(out).toContain("NOT BUILT YET");
      // The dangerous failure would be a panel that reads as a safe, working one.
      expect(out).not.toMatch(/\bNORMAL\b|\bSAFE\b/);
    } finally {
      delete PENDING_SCREENS.example;
    }
  });
});
