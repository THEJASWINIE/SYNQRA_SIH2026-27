/**
 * S4 Dispatch & Slots tests — M7.
 *
 * `react-dom/server`, mounted against a real `AppStateStore` via `HmiContext` (M5D-B).
 * No jsdom, no Testing Library (M4D-C).
 *
 * ASSERTIONS ARE AGAINST TEXT. Colour is stripped before every safety-relevant assertion,
 * so nothing passes on a colour attribute alone (NFR-008).
 *
 * FIXTURES ARE TEST-LOCAL (M7D-D). `slot-conflict` is the authored happy path and supplies
 * RESERVED + CONFLICT slots and one RECOMMENDED command. Everything the authored data does
 * not carry — ISSUED, the other slot statuses, missing reason codes, null ETA/route/target
 * speed, multi-row ordering — is fixtured here. NO M3 SCENARIO FILE IS MODIFIED.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import type { DispatchCommand, SafetyState, SlotState, VehicleState } from "../contracts/domain";
import { SLOT_STATUSES } from "../contracts/enums";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { DispatchSlots } from "./DispatchSlots";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function slot(partial: Partial<SlotState> = {}): SlotState {
  return {
    slotId: "SL-1",
    resourceId: "N-SW-1",
    vehicleId: "V-1",
    startTime: "2026-01-01T00:00:30.000Z",
    endTime: "2026-01-01T00:01:30.000Z",
    status: "RESERVED",
    eta: "2026-01-01T00:00:28.000Z",
    conflictWith: null,
    ...partial,
  };
}

function command(partial: Partial<DispatchCommand> = {}): DispatchCommand {
  return {
    commandId: "C-1",
    vehicleId: "V-2",
    routeId: "R-2",
    departureTime: "2026-01-01T00:00:45.000Z",
    targetSpeed: 6,
    slotId: "SL-1",
    reasonCode: "SWITCHBACK_CONTENTION",
    timestamp: T,
    state: "RECOMMENDED",
    limitingVariables: ["slot_overlap", "switchback_capacity"],
    routeNodeIds: ["N-INT-1", "N-SW-1", "N-WP-6"],
    ...partial,
  };
}

interface MountOptions {
  slots?: Record<string, SlotState>;
  dispatch?: Record<string, DispatchCommand>;
  status?: ConnectionStatus;
  error?: string | null;
  config?: FreshnessConfig | null;
  nowIso?: string;
  /** Phase 2 — S4 command panel. Optional, so every existing call is unaffected. */
  vehicles?: Record<string, VehicleState>;
  safety?: Record<string, SafetyState>;
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        slots: options.slots ?? { "SL-1": slot() },
        dispatch: options.dispatch ?? { "C-1": command() },
        ...(options.vehicles ? { vehicles: options.vehicles } : {}),
        ...(options.safety ? { safety: options.safety } : {}),
      },
    },
    T,
  );

  if (options.status) store.setStatus(options.status, options.error ?? null);
  store.setScenarioName("Slot conflict");
  if (options.nowIso) store.tick(options.nowIso);

  const value = testHmiContext({
    store,
    freshness: options.config === undefined ? CONFIG : options.config,
  });

  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );

  return renderToString(wrap(<DispatchSlots />));
}

/** The authored `slot-conflict` pair, reproduced from the scenario file, not modified. */
const CONFLICT_PAIR: Record<string, SlotState> = {
  "SL-1": slot(),
  "SL-2": slot({
    slotId: "SL-2",
    vehicleId: "V-2",
    startTime: "2026-01-01T00:01:00.000Z",
    endTime: "2026-01-01T00:02:00.000Z",
    status: "CONFLICT",
    eta: "2026-01-01T00:00:58.000Z",
    conflictWith: ["SL-1"],
  }),
};

// ---------------------------------------------------------------------------

describe("conflicts (FR-009 AC3)", () => {
  it("flags a supplied conflict in TEXT, not colour alone", () => {
    const html = greyscale(render({ slots: CONFLICT_PAIR }));
    expect(html).toContain("SLOT CONFLICT");
    expect(html).toContain("CONFLICTS WITH");
  });

  it("names the conflicting slot ids", () => {
    const html = greyscale(render({ slots: CONFLICT_PAIR }));
    expect(html).toContain("SL-2");
    expect(html).toContain("SL-1");
  });

  it("states the holder of a conflicting slot", () => {
    expect(render({ slots: CONFLICT_PAIR })).toContain("held by");
  });

  it("renders an honest empty state when no conflict is supplied", () => {
    const html = render({ slots: { "SL-1": slot() } });
    expect(html).toContain("NO ACTIVE SLOT CONFLICT");
    expect(html).toContain("runs no conflict detection");
  });

  it("treats a supplied conflictWith list as a conflict even without CONFLICT status", () => {
    const html = greyscale(
      render({
        slots: { "SL-9": slot({ slotId: "SL-9", status: "RESERVED", conflictWith: ["SL-1"] }) },
      }),
    );
    expect(html).toContain("SLOT CONFLICT");
  });

  it("says so when a conflict is reported without the conflicting ids", () => {
    const html = render({
      slots: { "SL-9": slot({ slotId: "SL-9", status: "CONFLICT", conflictWith: null }) },
    });
    expect(html).toContain("CONFLICTING SLOT IDS NOT SUPPLIED");
  });
});

describe("slot timeline (FR-009 AC1, AC2, AC4)", () => {
  it("renders a timeline and a real time axis from supplied times", () => {
    const html = render({ slots: CONFLICT_PAIR });
    expect(html).toContain('class="timeline"');
    expect(html).toContain("00:00:30");
    expect(html).toContain("00:02:00");
  });

  it("keeps overlapping slots individually readable, in separate lanes", () => {
    const html = render({ slots: CONFLICT_PAIR });
    // Two bands, stacked: one at lane 0, one at lane 2.4rem.
    expect(html).toContain("top:0rem");
    expect(html).toContain("top:2.4rem");
  });

  it("shows the holder and status on every band", () => {
    const html = greyscale(render({ slots: CONFLICT_PAIR }));
    expect(html).toContain("V-1");
    expect(html).toContain("V-2");
    expect(html).toContain("RESERVED");
    expect(html).toContain("CONFLICT");
  });

  it("also renders every slot as a table row, readable without the chart", () => {
    const html = render({ slots: CONFLICT_PAIR });
    expect(html).toContain("Supplied slot reservations");
    expect(html).toContain("Conflicts with");
  });

  it.each(SLOT_STATUSES)("renders supplied status %s distinctly", (status) => {
    const html = greyscale(render({ slots: { "SL-1": slot({ status }) } }));
    expect(html).toContain(status);
  });

  it("renders UNKNOWN status as unknown, never as RESERVED", () => {
    const html = greyscale(render({ slots: { "SL-1": slot({ status: "UNKNOWN" }) } }));
    expect(html).toContain("UNKNOWN");
    expect(html).not.toContain("RESERVED");
  });

  it("shows a supplied ETA, and says so when none was supplied", () => {
    expect(render({ slots: { "SL-1": slot({ eta: "2026-01-01T00:00:28.000Z" }) } })).toContain(
      "00:00:28",
    );
    expect(render({ slots: { "SL-1": slot({ eta: null }) } })).toContain("NOT SUPPLIED");
  });

  it("renders no holder explicitly rather than blank", () => {
    expect(render({ slots: { "SL-1": slot({ vehicleId: null }) } })).toContain("UNAVAILABLE");
  });

  it("groups by supplied resource and offers a selector when there are several", () => {
    const html = render({
      slots: {
        "SL-1": slot(),
        "SL-9": slot({ slotId: "SL-9", resourceId: "N-INT-2" }),
      },
    });
    expect(html).toContain("N-SW-1");
    expect(html).toContain("N-INT-2");
  });
});

describe("unusable time axis is never guessed", () => {
  it("an unparseable supplied time yields TIMELINE UNAVAILABLE and names the cause", () => {
    const html = render({ slots: { "SL-1": slot({ startTime: "not-a-time" }) } });
    expect(html).toContain("TIMELINE UNAVAILABLE");
    expect(html).toContain("could not be read");
    expect(html).toContain("No time is guessed");
  });

  it("a zero-duration window yields TIMELINE UNAVAILABLE", () => {
    const html = render({
      slots: { "SL-1": slot({ startTime: T, endTime: T }) },
    });
    expect(html).toContain("TIMELINE UNAVAILABLE");
    expect(html).toContain("span no duration");
  });

  it("still lists the slots in the table when the axis fails", () => {
    const html = render({ slots: { "SL-1": slot({ startTime: "nope" }) } });
    expect(html).toContain("SL-1");
    expect(html).toContain("Supplied slot reservations");
  });
});

describe("dispatch assignments (FR-010)", () => {
  it("renders every required field from the supplied command", () => {
    const html = render();
    expect(html).toContain("C-1");
    expect(html).toContain("V-2");
    expect(html).toContain("R-2");
    expect(html).toContain("00:00:45");
    expect(html).toContain("SL-1");
    expect(html).toContain("SWITCHBACK_CONTENTION");
  });

  it("renders the supplied route node chain, not a computed route", () => {
    const html = render();
    expect(html).toContain("N-INT-1 → N-SW-1 → N-WP-6");
  });

  it("renders supplied limiting variables", () => {
    expect(render()).toContain("slot overlap");
  });

  it("converts target speed for display and shows the supplied m/s alongside", () => {
    // 6 m/s = 21.6 km/h. Both appear; the supplied value is not replaced.
    const html = render();
    expect(html).toContain("21.6");
    expect(html).toContain("6.00 m/s");
  });

  it("says NOT SUPPLIED for a null target speed rather than showing zero", () => {
    const html = render({ dispatch: { "C-1": command({ targetSpeed: null }) } });
    expect(html).toContain("NOT SUPPLIED");
    expect(html).not.toContain("0.0<span");
  });

  it("says NOT SUPPLIED for a null route", () => {
    const html = render({
      dispatch: { "C-1": command({ routeId: null, routeNodeIds: null }) },
    });
    expect(html).toContain("NOT SUPPLIED");
    expect(html).toContain("route node chain not supplied");
  });

  it("says NOT SUPPLIED for a null departure time", () => {
    expect(render({ dispatch: { "C-1": command({ departureTime: null }) } })).toContain(
      "NOT SUPPLIED",
    );
  });
});

describe("dispatch state (FR-010 AC2)", () => {
  it("renders RECOMMENDED, as the authored scenario supplies", () => {
    expect(greyscale(render())).toContain("RECOMMENDED");
  });

  it("renders ISSUED distinctly from RECOMMENDED", () => {
    // Test-local fixture: no authored scenario supplies ISSUED (M7D-D).
    const issued = greyscale(render({ dispatch: { "C-1": command({ state: "ISSUED" }) } }));
    const recommended = greyscale(render());
    expect(issued).toContain("ISSUED");
    expect(recommended).toContain("RECOMMENDED");
    expect(issued).not.toBe(recommended);
  });

  it("renders every supplied dispatch state as text", () => {
    for (const state of [
      "RECOMMENDED",
      "ISSUED",
      "ACKNOWLEDGED",
      "SUPERSEDED",
      "REJECTED",
    ] as const) {
      expect(greyscale(render({ dispatch: { "C-1": command({ state }) } }))).toContain(state);
    }
  });

  it("ISSUED is producer-reported and grants the HMI no control", () => {
    const html = render({ dispatch: { "C-1": command({ state: "ISSUED" }) } });
    expect(html).toContain("reported by the producer");
    expect(html).not.toMatch(/>\s*(Issue|Send|Execute|Approve|Apply|Dispatch Now)\s*</i);
  });
});

describe("reason code (FR-010 AC1, NFR-006)", () => {
  it("renders a supplied non-empty reason code", () => {
    expect(render()).toContain("SWITCHBACK_CONTENTION");
  });

  it("an empty reason code renders an explicit data-defect marker, never blank", () => {
    const html = greyscale(render({ dispatch: { "C-1": command({ reasonCode: "" }) } }));
    expect(html).toContain("REASON CODE MISSING (DATA DEFECT)");
  });

  it("a whitespace-only reason code is treated as missing", () => {
    const html = greyscale(render({ dispatch: { "C-1": command({ reasonCode: "   " }) } }));
    expect(html).toContain("REASON CODE MISSING (DATA DEFECT)");
  });
});

describe("deterministic ordering", () => {
  it("orders commands newest supplied timestamp first", () => {
    const html = render({
      dispatch: {
        "C-1": command({ commandId: "C-1", timestamp: "2026-01-01T00:00:00.000Z" }),
        "C-2": command({ commandId: "C-2", timestamp: "2026-01-01T00:00:09.000Z" }),
      },
    });
    expect(html.indexOf("C-2")).toBeLessThan(html.indexOf("C-1"));
  });

  it("breaks equal timestamps by command id, so order never drifts between renders", () => {
    const dispatch = {
      "C-B": command({ commandId: "C-B" }),
      "C-A": command({ commandId: "C-A" }),
    };
    const first = render({ dispatch });
    const second = render({ dispatch });
    expect(first).toBe(second);
    expect(first.indexOf("C-A")).toBeLessThan(first.indexOf("C-B"));
  });
});

describe("degraded states", () => {
  it("no supplied dispatch data", () => {
    const html = render({ dispatch: {} });
    expect(html).toContain("DISPATCH DATA UNAVAILABLE");
    expect(html).toContain("neither selects nor optimizes");
  });

  it("no supplied slot data", () => {
    const html = render({ slots: {} });
    expect(html).toContain("SLOT DATA UNAVAILABLE");
    expect(html).toContain("does not generate slots");
  });

  it("neither supplied", () => {
    const html = render({ slots: {}, dispatch: {} });
    expect(html).toContain("SLOT DATA UNAVAILABLE");
    expect(html).toContain("DISPATCH DATA UNAVAILABLE");
    expect(html).toContain("NO ACTIVE SLOT CONFLICT");
  });

  it("a command naming a slot that was not supplied says so", () => {
    const html = render({ slots: {}, dispatch: { "C-1": command({ slotId: "SL-404" }) } });
    expect(html).toContain("SLOT NOT SUPPLIED");
  });

  it("disconnected", () => {
    expect(greyscale(render({ status: "DISCONNECTED" }))).toContain("Disconnected");
  });

  it("reconnecting", () => {
    expect(greyscale(render({ status: "RECONNECTING" }))).toContain("Reconnecting");
  });

  it("provider error, with its message", () => {
    const html = greyscale(render({ status: "ERROR", error: "dispatch feed lost" }));
    expect(html).toContain("Provider error");
    expect(html).toContain("dispatch feed lost");
  });

  it("keeps supplied values visible while disconnected", () => {
    const html = render({ status: "DISCONNECTED" });
    expect(html).toContain("C-1");
    expect(html).toContain("SWITCHBACK_CONTENTION");
  });
});

describe("freshness", () => {
  it("classifies as CURRENT when a threshold is configured and data is recent", () => {
    expect(render()).toContain("CURRENT");
  });

  it("classifies as STALE past the configured threshold, keeping the values", () => {
    const html = render({ nowIso: "2026-01-01T00:01:00.000Z" });
    expect(html).toContain("STALE");
    expect(html).toContain("C-1");
  });

  it("with no configured threshold, shows age but does NOT classify", () => {
    const html = render({ config: null });
    expect(html).toContain("AGE ONLY — NOT CLASSIFIED");
  });

  it("never invents OK or STALE from an unconfigured threshold", () => {
    const html = render({ config: null, nowIso: "2026-01-01T02:00:00.000Z" });
    expect(html).toContain("AGE ONLY — NOT CLASSIFIED");
    expect(html).not.toContain(">STALE<");
  });

  it("shows provider and scenario provenance", () => {
    const html = render();
    expect(html).toContain("Slot conflict");
    expect(html).toContain("MOCK");
  });
});

describe("scope — display only (M7D-A)", () => {
  it("renders no form and no submit path", () => {
    const html = render({ slots: CONFLICT_PAIR });
    expect(html).not.toContain("<form");
    expect(html).not.toContain('type="submit"');
    expect(html).not.toContain("<input");
  });

  it("renders no operational control of any kind", () => {
    const html = render({ slots: CONFLICT_PAIR }).toLowerCase();
    for (const forbidden of [
      "dispatch now",
      "approve",
      "apply slot",
      "override",
      "release vehicle",
      "hold vehicle",
      "send command",
      "execute",
      "apply change",
      "modify route",
      "modify target speed",
    ]) {
      expect(html, `forbidden control: ${forbidden}`).not.toContain(forbidden);
    }
  });

  it("the only buttons are resource selectors, which change display and nothing else", () => {
    const html = render({
      slots: { "SL-1": slot(), "SL-9": slot({ slotId: "SL-9", resourceId: "N-INT-2" }) },
    });
    const buttons = html.match(/<button[^>]*>/g) ?? [];
    expect(buttons.length).toBe(2);
    for (const button of buttons) expect(button).toContain("resource-tab");
  });

  it("a single resource needs no selector at all", () => {
    expect(render({ slots: { "SL-1": slot() } }).match(/<button/g)).toBeNull();
  });

  it("does not mutate the supplied values it renders", () => {
    const supplied = command();
    const before = JSON.parse(JSON.stringify(supplied));
    render({ dispatch: { "C-1": supplied } });
    expect(supplied).toEqual(before);
  });

  it("does not mutate supplied slots", () => {
    const supplied = slot();
    const before = JSON.parse(JSON.stringify(supplied));
    render({ slots: { "SL-1": supplied } });
    expect(supplied).toEqual(before);
  });
});

describe("FR-010 AC3 — declared partial non-conformance (M7D-C)", () => {
  it("states on screen that the event-log criterion is not verified in M7", () => {
    const html = render();
    expect(html).toContain("FR-010 AC3");
    expect(html).toContain("NOT verified in this milestone");
    expect(html).toContain("M9");
  });

  it("manufactures no event records to close the gap", () => {
    const html = render();
    expect(html).not.toContain("Event log");
    expect(html).not.toContain("EventRecord");
  });
});

// =========================================================================
// Phase 2 — S4 dispatch command panel (render level).
//
// Interaction (clicking SEND / CONFIRM STOP, the busy state) cannot be driven here: the
// suite renders with `react-dom/server` and there is no DOM (M4D-C). The behaviour behind
// those clicks is covered as pure logic in `state/dispatchCommand.test.ts` and
// `api/commandClient.test.ts`.
// =========================================================================

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_01",
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: 2.5,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "TRAVELING",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    ...partial,
  } as VehicleState;
}

const TWO_TRUCKS: Record<string, VehicleState> = {
  TRUCK_01: vehicle(),
  TRUCK_02: vehicle({ vehicleId: "TRUCK_02", speedMps: 1.0 }),
};

describe("S4 dispatch command panel", () => {
  it("A — renders the command panel", () => {
    const html = render({ vehicles: TWO_TRUCKS });
    expect(html).toContain("Dispatch command");
    expect(html).toContain("POST /api/commands");
  });

  it("B — offers every supplied vehicle for selection", () => {
    const html = render({ vehicles: TWO_TRUCKS });
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
    expect(html).toContain("dispatch-vehicle");
  });

  it("C — offers all four backend actions and the target-speed field", () => {
    const html = render({ vehicles: TWO_TRUCKS });
    for (const action of ["TARGET SPEED", "HOLD", "STOP", "RELEASE"]) {
      expect(html, `missing action: ${action}`).toContain(action);
    }
    // TARGET_SPEED is the default action, so the speed input is present.
    expect(html).toContain("dispatch-target-speed");
    expect(html).toContain("Target speed (m/s)");
  });

  it("labels the speed unit as m/s, matching the wire contract", () => {
    const html = render({ vehicles: TWO_TRUCKS });
    expect(html).toContain("m/s");
    expect(html).toContain("exactly as typed");
  });

  it("does not show a stop confirmation until STOP is chosen and sent", () => {
    // Default action is TARGET_SPEED; the confirmation must not be pre-rendered.
    const html = render({ vehicles: TWO_TRUCKS });
    expect(html).not.toContain("CONFIRM STOP");
  });

  it("shows an empty state when no vehicle has been supplied", () => {
    const html = render({ vehicles: {} });
    expect(html).toContain("NO VEHICLE SUPPLIED");
  });

  it("shows -- for a safe speed the authoritative state does not supply", () => {
    // No SafetyState is supplied, which is the current LIVE-mode condition.
    const html = greyscale(render({ vehicles: TWO_TRUCKS }));
    expect(html).toContain("Safe speed");
    expect(html).toContain("--");
    // It must not invent a number from the vehicle's speed.
    expect(html).not.toContain("SAFE SPEED CALCULATED");
  });

  it("shows a supplied safe speed when the authoritative state has one", () => {
    const html = render({
      vehicles: TWO_TRUCKS,
      safety: {
        TRUCK_01: {
          vehicleId: "TRUCK_01",
          timestamp: T,
          vSafe: 10,
          hSafe: null,
          actualSpeed: 2.5,
          headwayCurrent: null,
          leadVehicleId: null,
          activeConstraint: "VISIBILITY",
          riskLevel: "LOW",
          headwayViolation: null,
          envelopeViolation: null,
        } as SafetyState,
      },
    });
    expect(html).toContain("36.0"); // 10 m/s supplied -> 36.0 km/h
  });

  it("distinguishes SIMULATION from PHYSICAL provenance", () => {
    const simulated = render({
      vehicles: {
        TRUCK_01: vehicle({
          provenance: {
            speed_mps: {
              value: 2.5,
              timestamp: 1788000000,
              source: "SIMULATION",
              origin: "SIMULATION",
              quality: "GOOD",
              ageS: 0.1,
              available: true,
              clockDomain: "WALL_CLOCK",
              freshness: "CURRENT",
            },
          },
        }),
      },
    });
    expect(simulated).toContain("SIMULATION");

    const physical = render({
      vehicles: {
        TRUCK_01: vehicle({
          provenance: {
            speed_mps: {
              value: 2.5,
              timestamp: 1788000000,
              source: "DERIVED",
              origin: "HARDWARE",
              quality: "GOOD",
              ageS: 0.1,
              available: true,
              clockDomain: "WALL_CLOCK",
              freshness: "CURRENT",
            },
          },
        }),
      },
    });
    expect(physical).toContain("PHYSICAL");
  });

  it("S — renders the session history region, empty before any command", () => {
    const html = render({ vehicles: TWO_TRUCKS });
    expect(html).toContain("Session command history");
    expect(html).toContain("NO COMMANDS THIS SESSION");
  });

  it("never claims a vehicle executed anything", () => {
    const html = greyscale(render({ vehicles: TWO_TRUCKS })).toLowerCase();
    expect(html).not.toContain("vehicle stopped");
    expect(html).not.toContain("executed successfully");
  });
});
