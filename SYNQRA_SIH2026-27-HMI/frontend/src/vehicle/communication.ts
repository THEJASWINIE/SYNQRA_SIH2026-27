/**
 * Communication state — three separate links, three separate answers.
 *
 * ==========================================================================
 *  A LINK IS CONNECTED WHEN SOMETHING ARRIVED OVER IT. NOT WHEN A MODEM EXISTS.
 *
 *  Both trucks carry an SX1278 LoRa modem. That fact is worth exactly nothing as
 *  evidence: the question a V2V panel answers is "did a frame arrive, and how long ago",
 *  and only measured fields can answer it. Every state below is derived from a supplied
 *  Twin field or is UNAVAILABLE. Nothing here defaults to CONNECTED.
 * ==========================================================================
 *
 * THE THREE LINKS ARE NOT INTERCHANGEABLE
 *
 *   BACKEND / Wi-Fi   this browser's data feed, plus the vehicle's own Wi-Fi RSSI
 *   V2V     / LoRa    truck to truck, 433 MHz
 *   V2I     / LoRa    truck to roadside infrastructure
 *
 * A healthy browser socket says nothing about whether two trucks can hear each other.
 * They are computed independently and rendered separately, because conflating them is how
 * an operator ends up trusting a V2V link that has been down for ten minutes.
 *
 * RADIO METRICS NEVER CROSS
 *
 * `wifi_rssi_dbm` comes from the vehicle's `WiFi.RSSI()`. `lora_rssi_dbm` and
 * `lora_snr_db` come from the receiving LoRa modem's `packetRssi()` / `packetSnr()`.
 * The ingestor writes them by TRANSPORT (telemetry_ingest.py) and this module reads them
 * under their own names. A Wi-Fi number is never shown under a LoRa heading, and an
 * absent LoRa metric stays absent rather than borrowing the Wi-Fi one.
 *
 * PHYSICAL TRUTH AT THE TIME OF WRITING
 *
 *   * TRUCK_01 and TRUCK_02 post telemetry over DIRECT_WIFI. A DIRECT_WIFI frame crossed
 *     no LoRa radio, so it carries no LoRa metrics and no V2V evidence.
 *   * The only path that delivers measured LoRa RSSI/SNR to the backend is the serial
 *     LoRa gateway (`esp32_code/LORA_GATEWAY_RECEIVER`), whose frames arrive as
 *     SERIAL_GATEWAY / V2V.
 *   * NO physical roadside V2I unit exists. `intersection_rsu.py` is a Python simulation
 *     with no device behind it, so V2I is UNAVAILABLE in LIVE mode - never CONNECTED.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { TwinFieldProvenance, VehicleState } from "../contracts/domain";
import {
  DATA_STATE_TEXT,
  type DataState,
  fieldDataState,
  provenanceLabel,
  UNAVAILABLE_VALUE,
} from "../state/dataStatus";
import { type HardwareReadout, telemetryTransport } from "../state/hardwareTelemetry";

/** What a link can be. Four states, and no fifth that means "probably fine". */
export type LinkState = "CONNECTED" | "STALE" | "DISCONNECTED" | "UNAVAILABLE";

export const LINK_STATE_TEXT: Record<LinkState, string> = {
  CONNECTED: "CONNECTED",
  STALE: "STALE",
  DISCONNECTED: "DISCONNECTED",
  UNAVAILABLE: "UNAVAILABLE",
};

/** Non-colour cue, so link state is never carried by colour alone (accessibility). */
export const LINK_STATE_GLYPH: Record<LinkState, string> = {
  CONNECTED: "=",
  STALE: "~",
  DISCONNECTED: "x",
  UNAVAILABLE: "?",
};

export interface LinkStatus {
  /** Which link this is, for the panel heading. */
  readonly label: string;
  /** The radio or transport that carries it. Named so the metric cannot be misattributed. */
  readonly bearer: string;
  readonly state: LinkState;
  /** Freshness of the evidence, when there is evidence. */
  readonly dataState: DataState;
  /** Why the state is what it is. A state without a reason is a guess. */
  readonly reason: string;
  /** The peer at the other end, when the link has a named one. */
  readonly peerId?: string | undefined;
  /** Age of the newest evidence, in seconds, as the Twin reported it. */
  readonly ageS?: number | null | undefined;
  /** Radio metrics belonging to THIS link. Never borrowed from another. */
  readonly metrics: readonly HardwareReadout[];
}

function field(
  vehicle: VehicleState | null | undefined,
  name: string,
): TwinFieldProvenance | undefined {
  return vehicle?.provenance?.[name];
}

/** A metric row from a supplied field, or an explicit absent row. Never a fabricated number. */
function metric(
  vehicle: VehicleState | null | undefined,
  name: string,
  label: string,
  unit: string,
  digits: number,
  absentReason: string,
): HardwareReadout {
  const f = field(vehicle, name);
  const state = fieldDataState(f);
  const raw = f?.value;

  if (!f || state === "UNAVAILABLE" || typeof raw !== "number" || !Number.isFinite(raw)) {
    return {
      label,
      value: UNAVAILABLE_VALUE,
      available: false,
      provenance: UNAVAILABLE_VALUE,
      freshness: DATA_STATE_TEXT.UNAVAILABLE,
      ageS: null,
      reason: absentReason,
    };
  }

  return {
    label,
    value: raw.toFixed(digits),
    unit,
    available: true,
    provenance: provenanceLabel(f),
    freshness: DATA_STATE_TEXT[state],
    ageS: f.ageS ?? null,
  };
}

/**
 * Turn the freshness of the newest piece of evidence into a link state.
 *
 * UNKNOWN means the staleness threshold is unconfigured (AMB-014), so freshness is not
 * evaluated at all. The link is reported CONNECTED - something did arrive - with the
 * UNKNOWN data state carried alongside, exactly as the rest of the HMI reports it. It is
 * never silently upgraded to a freshness claim nobody can make.
 */
function stateFromEvidence(dataState: DataState): LinkState {
  switch (dataState) {
    case "CURRENT":
      return "CONNECTED";
    case "UNKNOWN":
      return "CONNECTED";
    case "STALE":
      return "STALE";
    case "UNAVAILABLE":
      return "UNAVAILABLE";
  }
}

// ---------------------------------------------------------------------------
// BACKEND / Wi-Fi
// ---------------------------------------------------------------------------

/** The HMI's own connection status, as `AppState.connection.status` reports it. */
export type BrowserConnectionStatus = string;

/**
 * The vehicle's link to the backend.
 *
 * TWO different facts share this panel and are kept apart on purpose:
 *   * whether THIS BROWSER is receiving the feed  (`connectionStatus`)
 *   * whether the VEHICLE's telemetry is arriving  (freshness of its own fields)
 *
 * A browser that lost its socket does not mean the truck went quiet, and a truck that
 * went quiet does not mean the browser is broken. The state below reports the vehicle's
 * telemetry; the browser's own status is carried alongside it in the reason.
 */
export function backendLink(
  vehicle: VehicleState | null | undefined,
  connectionStatus: BrowserConnectionStatus,
): LinkStatus {
  const transport = telemetryTransport(vehicle);
  const wifi = metric(
    vehicle,
    "wifi_rssi_dbm",
    "Wi-Fi RSSI",
    "dBm",
    0,
    "No Wi-Fi RSSI measured by this vehicle.",
  );

  if (!vehicle) {
    return {
      label: "Backend",
      bearer: "Wi-Fi",
      state: "UNAVAILABLE",
      dataState: "UNAVAILABLE",
      reason: `The Digital Twin has supplied no state for this vehicle. Browser feed: ${connectionStatus}.`,
      metrics: [wifi],
    };
  }

  // The Twin's own receipt stamp decides freshness; RPM is the fallback measured field.
  const stamped = field(vehicle, "received_at") ?? field(vehicle, "rpm");
  const dataState = fieldDataState(stamped);
  const state = stateFromEvidence(dataState);

  const reason =
    state === "UNAVAILABLE"
      ? "No telemetry timestamp supplied for this vehicle."
      : state === "STALE"
        ? "Telemetry has stopped arriving from this vehicle."
        : `Telemetry arriving${transport ? ` over ${transport}` : ""}.`;

  return {
    label: "Backend",
    bearer: transport === "DIRECT_WIFI" ? "Wi-Fi (DIRECT_WIFI)" : (transport ?? "Wi-Fi"),
    state,
    dataState,
    reason: `${reason} Browser feed: ${connectionStatus}.`,
    ageS: stamped?.ageS ?? null,
    metrics: [wifi],
  };
}

// ---------------------------------------------------------------------------
// V2V / LoRa
// ---------------------------------------------------------------------------

export const NO_V2V_EVIDENCE_REASON =
  "No LoRa frame evidence has reached the Digital Twin for this vehicle. " +
  "Telemetry arriving over DIRECT_WIFI crossed no LoRa radio, so it carries no V2V metrics. " +
  "V2V status requires measured LoRa RSSI/SNR, which reach the backend only through the LoRa gateway.";

/**
 * Truck-to-truck link.
 *
 * Evidence is the per-radio LoRa fields. Their PRESENCE is the proof a LoRa frame was
 * received and measured; their freshness is how recently. With neither field supplied the
 * answer is UNAVAILABLE - not DISCONNECTED, because "we have no way to tell" and "we
 * checked and it is down" are different statements and only one of them is true here.
 */
export function v2vLink(
  vehicle: VehicleState | null | undefined,
  peerId: string | null,
): LinkStatus {
  const rssi = metric(
    vehicle,
    "lora_rssi_dbm",
    "LoRa RSSI",
    "dBm",
    0,
    "No LoRa RSSI measured. Not substituted from Wi-Fi.",
  );
  const snr = metric(
    vehicle,
    "lora_snr_db",
    "LoRa SNR",
    "dB",
    1,
    "No LoRa SNR measured. Not substituted from Wi-Fi.",
  );

  const rssiField = field(vehicle, "lora_rssi_dbm");
  const snrField = field(vehicle, "lora_snr_db");

  const states: DataState[] = [];
  if (rssiField) states.push(fieldDataState(rssiField));
  if (snrField) states.push(fieldDataState(snrField));
  const evidence = states.filter((s) => s !== "UNAVAILABLE");

  if (evidence.length === 0) {
    return {
      label: "V2V",
      bearer: "LoRa 433 MHz",
      state: "UNAVAILABLE",
      dataState: "UNAVAILABLE",
      reason: NO_V2V_EVIDENCE_REASON,
      peerId: peerId ?? undefined,
      metrics: [rssi, snr],
    };
  }

  // Worst evidence wins: one stale metric makes the link stale, never the other way round.
  const dataState: DataState = evidence.includes("STALE")
    ? "STALE"
    : evidence.includes("UNKNOWN")
      ? "UNKNOWN"
      : "CURRENT";

  const state = stateFromEvidence(dataState);
  const ageS = [rssiField?.ageS, snrField?.ageS]
    .filter((age): age is number => typeof age === "number")
    .sort((a, b) => a - b)[0];

  return {
    label: "V2V",
    bearer: "LoRa 433 MHz",
    state,
    dataState,
    reason:
      state === "STALE"
        ? `No recent LoRa frame${peerId ? ` from ${peerId}` : ""}.`
        : `Measured LoRa frame metrics supplied${peerId ? ` for the ${peerId} link` : ""}.`,
    peerId: peerId ?? undefined,
    ageS: ageS ?? null,
    metrics: [rssi, snr],
  };
}

// ---------------------------------------------------------------------------
// V2I / LoRa
// ---------------------------------------------------------------------------

export const NO_PHYSICAL_V2I_REASON =
  "No physical roadside infrastructure unit exists on this prototype. " +
  "intersection_rsu.py is a Python simulation with no device behind it and no ingestion path, " +
  "so there is no infrastructure link to report.";

export const SIMULATED_V2I_REASON =
  "SIMULATED V2I. Produced by the RSU simulation, not by any physical roadside unit.";

/**
 * Truck-to-infrastructure link.
 *
 * UNAVAILABLE in LIVE mode, unconditionally, because no infrastructure device exists to
 * be connected to. In MOCK/SIMULATION the panel says SIMULATED V2I, which is a label and
 * not a promotion: a simulated link is still never reported as CONNECTED, because there
 * is nothing physical at the far end of it.
 *
 * When a real roadside unit is built, this function gains an evidence branch exactly like
 * `v2vLink` - and not before.
 */
export function v2iLink(mode: string): LinkStatus {
  const simulated = mode === "MOCK" || mode === "SIMULATION";
  return {
    label: "V2I",
    bearer: simulated ? "LoRa 433 MHz (SIMULATED)" : "LoRa 433 MHz",
    state: "UNAVAILABLE",
    dataState: "UNAVAILABLE",
    reason: simulated ? SIMULATED_V2I_REASON : NO_PHYSICAL_V2I_REASON,
    metrics: [],
  };
}

/** The three links, in the order the panel renders them. */
export function communicationLinks(
  vehicle: VehicleState | null | undefined,
  peerId: string | null,
  connectionStatus: BrowserConnectionStatus,
  mode: string,
): LinkStatus[] {
  return [v2vLink(vehicle, peerId), v2iLink(mode), backendLink(vehicle, connectionStatus)];
}
