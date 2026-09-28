/**
 * HMI-COMMS-01 — communication truth contract (brief tests 1-30).
 *
 *     WI-FI CONNECTIVITY ≠ V2V.   NO VERIFIED PHYSICAL V2I ENDPOINT = V2I UNAVAILABLE.
 *
 * SOFTWARE ONLY. Twin frames are fixtures shaped like the backend projection; radio
 * numbers are TEST-ONLY. `renderToString`, node environment.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VehicleCard } from "../components/VehicleCard";
import { freshnessConfig } from "../config/freshness";
import type { VehicleState } from "../contracts/domain";
import type { RawTwinVehicle } from "../contracts/raw";
import { normalizeTwinVehicle } from "../data/normalize";
import { OperationsOverview } from "../screens/OperationsOverview";
import { viewFreshness } from "../state/freshness";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import {
  backendLink,
  communicationLinks,
  GATEWAY_NOT_V2V_REASON,
  LORA_GATEWAY_RECEIVER,
  v2iLink,
  v2vLink,
} from "./communication";
import { DriverScreen } from "./DriverScreen";
import { vehicleConfig } from "./vehicleConfig";
import { projectVehicle } from "./vehicleProjection";

const NOW_S = 1_788_000_000;
const T = new Date(NOW_S * 1000).toISOString();
const CONFIG = freshnessConfig(5000);

type Over = Partial<{
  source: string;
  origin: string;
  freshness: string;
  available: boolean;
  age_s: number | null;
}>;
function field(value: unknown, over: Over = {}) {
  return {
    value,
    timestamp: NOW_S,
    source: "HARDWARE",
    origin: "HARDWARE",
    quality: "GOOD",
    age_s: 0.3,
    available: true,
    clock_domain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...over,
  };
}

/** TRUCK_01 posting over DIRECT_WIFI: Wi-Fi RSSI, nothing LoRa. */
function wifiFrame(
  id = "TRUCK_01",
  extra: Record<string, ReturnType<typeof field>> = {},
): RawTwinVehicle {
  return {
    vehicle_id: id,
    static: {},
    has_hardware_data: true,
    dynamic: {
      rpm: field(1450),
      speed_mps: field(7.59, { source: "DERIVED" }),
      received_at: field(NOW_S, { source: "DERIVED" }),
      wifi_rssi_dbm: field(-45),
      rssi_dbm: field(-45),
      telemetry_transport: field("DIRECT_WIFI", { source: "DERIVED" }),
      ...extra,
    },
  } as RawTwinVehicle;
}

/** TRUCK_01's LoRa frame as relayed by TRUCK_02 (V2V_VIA_TRUCK_02): measured at TRUCK_02. */
function relayFrame(
  over: Record<string, ReturnType<typeof field> | undefined> = {},
  prov: Over = {},
): RawTwinVehicle {
  const dynamic: Record<string, ReturnType<typeof field>> = {
    rpm: field(1450, prov),
    speed_mps: field(7.59, { source: "DERIVED", ...prov }),
    received_at: field(NOW_S, { source: "DERIVED" }),
    lora_rssi_dbm: field(-72, prov),
    lora_snr_db: field(8.5, prov),
    v2v_sequence: field(41, prov),
    lora_receiver_id: field("TRUCK_02", { source: "DERIVED", ...prov }),
    telemetry_transport: field("V2V", { source: "DERIVED" }),
  };
  for (const [k, v] of Object.entries(over)) {
    if (v === undefined) delete dynamic[k];
    else dynamic[k] = v;
  }
  return { vehicle_id: "TRUCK_01", static: {}, has_hardware_data: true, dynamic } as RawTwinVehicle;
}

const V = (raw: RawTwinVehicle): VehicleState => normalizeTwinVehicle(raw);

function storeFrom(
  frames: RawTwinVehicle[],
  provider: "LIVE" | "MOCK" | "REPLAY" = "LIVE",
): AppStateStore {
  const store = new AppStateStore(T, provider);
  const vehicles: Record<string, VehicleState> = {};
  for (const f of frames) vehicles[f.vehicle_id] = V(f);
  store.applyPatch({ changes: { vehicles } }, T);
  store.setStatus("CONNECTED", null);
  return store;
}
const text = (html: string) => html.replace(/<!-- -->/g, "");
function render(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: CONFIG });
  return text(renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>));
}
function driver(store: AppStateStore, id: "TRUCK_01" | "TRUCK_02"): string {
  return render(
    store,
    <DriverScreen
      projection={projectVehicle(store.getSnapshot(), id)}
      config={vehicleConfig(id)}
    />,
  );
}
const cell = (html: string, label: string) =>
  html.match(
    new RegExp(
      `${label}</div><div class="drv-cell-value">([^<]*)</div>(?:<div class="drv-cell-sub">([^<]*)<)?`,
    ),
  );
const src = (rel: string) =>
  readFileSync(join(__dirname, "..", rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
const sourcesIn = (dir: string) =>
  readdirSync(join(__dirname, "..", dir))
    .filter((f) => /\.(ts|tsx)$/.test(f) && !/\.test\./.test(f))
    .map((f) => ({ name: `${dir}/${f}`, text: src(`${dir}/${f}`) }));

// ===========================================================================
// 1-4. connectivity is not V2V
// ===========================================================================

describe("connectivity is not V2V (1-4)", () => {
  it("1/2/3. Wi-Fi, backend and WebSocket connectivity give V2V UNAVAILABLE", () => {
    const v = V(wifiFrame());
    const links = communicationLinks(v, "CONNECTED", "LIVE");
    const backend = links.find((l) => l.label === "Backend");
    const v2v = links.find((l) => l.label === "V2V");
    expect(backend?.state).toBe("CONNECTED");
    expect(backend?.bearer).toContain("Wi-Fi");
    expect(v2v?.state).toBe("UNAVAILABLE");
    expect(v2v?.peerId).toBeUndefined();
    // A bare vehicle with no telemetry at all: also UNAVAILABLE, never DISCONNECTED.
    expect(v2vLink(null).state).toBe("UNAVAILABLE");
    expect(
      v2vLink(V({ vehicle_id: "TRUCK_02", static: {}, dynamic: {} } as RawTwinVehicle)).state,
    ).toBe("UNAVAILABLE");
  });

  it("4. telemetry freshness is distinct from V2V freshness", () => {
    // Telemetry CURRENT, V2V STALE.
    const a = V(
      relayFrame({
        lora_rssi_dbm: field(-72, { freshness: "STALE", age_s: 9 }),
        lora_snr_db: field(8.5, { freshness: "STALE", age_s: 9 }),
      }),
    );
    expect(backendLink(a, "CONNECTED").state).toBe("CONNECTED");
    expect(v2vLink(a).state).toBe("STALE");
    // Telemetry STALE, V2V CURRENT.
    const b = V(
      relayFrame({
        received_at: field(NOW_S, { source: "DERIVED", freshness: "STALE", age_s: 9 }),
      }),
    );
    expect(backendLink(b, "CONNECTED").state).toBe("STALE");
    expect(v2vLink(b).state).toBe("CONNECTED");
  });
});

// ===========================================================================
// 5-13. peer, RSSI, SNR, sequence
// ===========================================================================

describe("evidence fields (5-13)", () => {
  it("5/6/11. peer id comes from the LoRa receiver evidence; none is fabricated", () => {
    expect(v2vLink(V(relayFrame())).peerId).toBe("TRUCK_02");
    expect(v2vLink(V(wifiFrame())).peerId).toBeUndefined();
    // LoRa metrics without a receiver identity: no peer is guessed, no link claimed.
    const noReceiver = v2vLink(V(relayFrame({ lora_receiver_id: undefined })));
    expect(noReceiver.state).toBe("UNAVAILABLE");
    expect(noReceiver.peerId).toBeUndefined();
    // The configured "other truck" is not consulted: v2vLink takes no peer argument.
    expect(v2vLink.length).toBe(1);
    expect(src("vehicle/communication.ts")).not.toMatch(/peerOf|VEHICLE_IDS/);
  });

  it("7/8. V2V RSSI comes only from the LoRa path; Wi-Fi RSSI cannot populate it", () => {
    const both = V(relayFrame({ wifi_rssi_dbm: field(-45) }));
    const v2v = v2vLink(both);
    expect(v2v.metrics[0]?.label).toContain("LoRa RSSI");
    expect(v2v.metrics[0]?.value).toBe("-72");
    const wifiOnly = v2vLink(V(wifiFrame()));
    expect(wifiOnly.metrics[0]?.available).toBe(false);
    expect(wifiOnly.metrics[0]?.value).toBe("--");
    expect(backendLink(V(wifiFrame()), "CONNECTED").metrics[0]).toMatchObject({
      label: "Wi-Fi RSSI",
      value: "-45",
    });
  });

  it("9/10. V2V SNR only from LoRa; missing SNR is UNAVAILABLE, not a constant", () => {
    expect(v2vLink(V(relayFrame())).metrics[1]).toMatchObject({
      label: "LoRa SNR (at TRUCK_02)",
      value: "8.5",
    });
    const noSnr = v2vLink(V(relayFrame({ lora_snr_db: undefined })));
    expect(noSnr.state).toBe("CONNECTED"); // RSSI evidence alone still proves the frame
    expect(noSnr.metrics[1]?.available).toBe(false);
    expect(noSnr.metrics[1]?.value).toBe("--");
    // A Wi-Fi frame's firmware fallback (snr_db 9.5) is never a V2V SNR.
    const wifiWithFallback = v2vLink(V(wifiFrame("TRUCK_01", { snr_db: field(9.5) })));
    expect(wifiWithFallback.metrics[1]?.value).toBe("--");
    expect(JSON.stringify(wifiWithFallback)).not.toContain("9.5");
  });

  it("12/13. V2V sequence is preserved from the LoRa frame and never made up for Wi-Fi", () => {
    expect(v2vLink(V(relayFrame())).sequence).toBe(41);
    expect(v2vLink(V(wifiFrame("TRUCK_01", { sequence: field(7) }))).sequence).toBeNull();
  });
});

// ===========================================================================
// 14-20. states, V2I, simulation, replay
// ===========================================================================

describe("V2V state machine, V2I, provenance (14-20)", () => {
  it("14/15/16. CURRENT needs real evidence; STALE only after it ages; UNAVAILABLE without it", () => {
    expect(v2vLink(V(relayFrame())).state).toBe("CONNECTED");
    expect(
      v2vLink(
        V(
          relayFrame({
            lora_rssi_dbm: field(-72, { freshness: "STALE", age_s: 12 }),
            lora_snr_db: field(8.5, { freshness: "STALE", age_s: 12 }),
          }),
        ),
      ).state,
    ).toBe("STALE");
    expect(v2vLink(V(wifiFrame())).state).toBe("UNAVAILABLE");
    // A frame heard by the bench gateway proves LoRa TX, not truck-to-truck.
    const gw = v2vLink(
      V(relayFrame({ lora_receiver_id: field(LORA_GATEWAY_RECEIVER, { source: "DERIVED" }) })),
    );
    expect(gw.state).toBe("UNAVAILABLE");
    expect(gw.reason).toBe(GATEWAY_NOT_V2V_REASON);
    expect(gw.peerId).toBeUndefined();
    expect(gw.metrics[0]?.label).toBe("LoRa RSSI (at gateway)");
  });

  it("17/18. V2I is UNAVAILABLE in LIVE; simulated V2I says SIMULATED and is still not CONNECTED", () => {
    expect(v2iLink("LIVE")).toMatchObject({ state: "UNAVAILABLE", bearer: "LoRa 433 MHz" });
    expect(v2iLink("MOCK").bearer).toContain("SIMULATED");
    expect(v2iLink("MOCK").state).toBe("UNAVAILABLE");
    expect(v2iLink("REPLAY").bearer).toContain("REPLAY");
    expect(src("vehicle/communication.ts")).not.toMatch(/intersection_rsu.*CONNECTED/);
  });

  it("19/20. simulated V2V is labelled SIMULATION; replay is not labelled LIVE", () => {
    const sim = v2vLink(V(relayFrame({}, { source: "SIMULATION", origin: "SIMULATION" })));
    expect(sim.state).toBe("CONNECTED");
    expect(sim.reason).toContain("SIMULATION");
    expect(sim.metrics[0]?.provenance).toBe("SIMULATION");
    const store = storeFrom(
      [relayFrame({}, { source: "SIMULATION", origin: "SIMULATION" }), wifiFrame("TRUCK_02")],
      "REPLAY",
    );
    const html = driver(store, "TRUCK_01");
    expect(cell(html, "V2V")?.[2]).toContain("SIMULATION");
    expect(cell(html, "V2I")?.[2]).toContain("REPLAY");
    expect(cell(html, "V2V")?.[2]).not.toMatch(/\bLIVE\b|HARDWARE|PHYSICAL/);
  });
});

// ===========================================================================
// 21-24. identity and projections
// ===========================================================================

describe("identity and projections (21-24)", () => {
  const store = () => storeFrom([relayFrame(), wifiFrame("TRUCK_02")]);

  it("21/22/23. own identity fixed; peer communication is the peer's canonical state", () => {
    const t01 = driver(store(), "TRUCK_01");
    expect(t01).toContain("TRUCK_01 driver display");
    expect(cell(t01, "V2V")?.[1]).toContain("CONNECTED");
    expect(cell(t01, "V2V")?.[2]).toContain("PEER TRUCK_02");
    expect(cell(t01, "V2V")?.[2]).toContain("LoRa RSSI (at TRUCK_02) -72 dBm");
    expect(cell(t01, "V2V")?.[2]).toContain("SEQ 41");
    // TRUCK_02 itself has only Wi-Fi telemetry: its OWN V2V is UNAVAILABLE even though its
    // modem heard TRUCK_01. Peer telemetry existing is not V2V.
    const t02 = driver(store(), "TRUCK_02");
    expect(t02).toContain("TRUCK_02 driver display");
    expect(cell(t02, "V2V")?.[1]).toContain("UNAVAILABLE");
    expect(cell(t02, "V2V")?.[2]).toContain("PEER UNAVAILABLE");
    expect(cell(t02, "V2I")?.[1]).toContain("UNAVAILABLE");
  });

  it("24. Control Room shows fleet communication per vehicle, never one merged state", () => {
    const html = render(store(), <OperationsOverview onSelectVehicle={() => {}} />);
    const card = (id: string) =>
      html.match(new RegExp(`aria-label="[^"]*${id}[^"]*">[\\s\\S]*?</article>`))?.[0] ?? "";
    expect(card("TRUCK_01")).toContain(
      "V2V = CONNECTED · PEER TRUCK_02 · LoRa RSSI (at TRUCK_02) -72 dBm · LoRa SNR (at TRUCK_02) 8.5 dB",
    );
    expect(card("TRUCK_01")).toContain("V2I ? UNAVAILABLE");
    expect(card("TRUCK_02")).toContain("BACKEND = CONNECTED · WI-FI RSSI -45 dBm");
    expect(card("TRUCK_02")).toContain("V2V ? UNAVAILABLE");
    expect(card("TRUCK_02")).not.toContain("V2V RSSI");
    // Stand-alone card without a mode still says V2I UNAVAILABLE.
    const bare = text(
      renderToString(
        <VehicleCard
          vehicle={V(wifiFrame())}
          safety={undefined}
          freshness={viewFreshness(T, CONFIG, NOW_S * 1000)}
        />,
      ),
    );
    expect(bare).toContain("V2I ? UNAVAILABLE");
  });
});

// ===========================================================================
// 25-30. architecture
// ===========================================================================

describe("architecture (25-30)", () => {
  const HMI = () => [...sourcesIn("vehicle"), ...sourcesIn("screens"), ...sourcesIn("components")];

  it("25. no frontend V2V algorithm: no link is derived from connectivity or vehicle presence", () => {
    for (const f of HMI()) {
      expect(f.text, f.name).not.toMatch(/state:\s*"CONNECTED"\s*,?\s*\/\/\s*default/);
      expect(f.text, f.name).not.toMatch(/WiFi\.RSSI|wifi_rssi_dbm[^\n]*lora_rssi_dbm[^\n]*\?\?/);
      expect(f.text, f.name).not.toMatch(/nearestVehicle|calculateV2V|inferPeer/i);
    }
    const comm = src("vehicle/communication.ts");
    // Every CONNECTED originates from evidence freshness, never from a literal default.
    expect(comm.match(/return "CONNECTED"/g)?.length).toBe(2); // CURRENT and UNKNOWN in stateFromEvidence
    expect(comm).not.toMatch(/state:\s*"CONNECTED"/);
  });

  it("26/27. no second communication store; ProviderHost remains the boundary", () => {
    for (const f of HMI()) {
      expect(f.text, f.name).not.toMatch(/new AppStateStore\(|new WebSocket|fetch\(|EventSource/);
    }
  });

  it("28. Mine-Cast remains separate", () => {
    for (const f of HMI()) expect(f.text, f.name).not.toMatch(/from "\.\.?\/minecast|from "three"/);
  });

  it("29/30. command and safety architecture unchanged", () => {
    expect(src("api/commandClient.ts")).toMatch(/\/api\/commands/);
    expect(src("api/commandClient.ts")).toMatch(/Authorization/);
    for (const rel of [
      "state/speedContract.ts",
      "state/operatorAction.ts",
      "vehicle/driverState.ts",
    ]) {
      expect(src(rel), rel).not.toMatch(/lora_|wifi_|v2v_|rssi|snr/i);
    }
    expect(src("vehicle/communication.ts")).not.toMatch(/vSafe|riskLevel|targetSpeed|applyPatch/);
  });
});
