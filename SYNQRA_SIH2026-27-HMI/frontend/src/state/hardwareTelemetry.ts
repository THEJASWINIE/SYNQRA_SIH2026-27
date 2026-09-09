/**
 * Hardware telemetry readouts — for the hardware integration of commit 83d05d3.
 *
 * ==========================================================================
 *  READS THE TWIN. COMPUTES NOTHING.
 *
 *  Every value here was already measured, already derived and already stamped with a
 *  provenance by `telemetry_ingest.py`. This module selects fields out of the Twin's
 *  per-field provenance map and labels them. It converts no units, derives no speed and
 *  infers no provenance.
 * ==========================================================================
 *
 * WHY IT EXISTS
 *
 * `VehicleState` carries `speedMps`, `accelMps2` and friends, but the physical fields the
 * ESP32 actually sends - wheel RPM, the IMU axes, Wi-Fi RSSI - have no named slot on that
 * contract. They ARE carried, verbatim, in `VehicleState.provenance`, because
 * `normalizeTwinVehicle` copies every dynamic Twin field into it. So the hardware can be
 * displayed truthfully without widening a frozen contract.
 *
 * WHAT THE PROTOTYPE ACTUALLY MEASURES (telemetry_ingest.py:52-85, the hardware truth table)
 *
 *   rpm                    MEASURED. LM393 slot sensor + ISR pulse count.
 *   speed_mps              DERIVED from that measured RPM by the existing UnitConverter.
 *                          Absent - not zero - when the vehicle has no calibrated radius.
 *   ax/ay/az, gx/gy/gz     MEASURED. MPU6050.
 *   rssi_dbm               MEASURED. WiFi.RSSI().
 *   speed_mps_pwm_derived  NOT a measurement. TRUCK_02's commanded prototype velocity,
 *                          stored under its own name so nothing can mistake it for an
 *                          encoder reading.
 *
 * THE SNR EXCEPTION
 *
 * `snr_db` is stamped `observed` by the ingestor, but the Vehicle A firmware sends a
 * hard-coded 9.5 dB when it has no valid LoRa packet
 * (`sketch_aug26a.ino`: `remoteDataValid ? remoteSNR : 9.5f`), and a LoRa SNR is not a
 * meaningful quantity for a frame that arrived over Wi-Fi at all. So on a DIRECT_WIFI
 * frame this module reports SNR as UNAVAILABLE with that reason. It does not relabel the
 * number, and it does not silently show it. See `snrReadout`.
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
} from "./dataStatus";

/** One hardware value, ready to render. */
export interface HardwareReadout {
  label: string;
  /** Already formatted, or the unavailable marker. Never a fabricated number. */
  value: string;
  unit?: string | undefined;
  available: boolean;
  /** PHYSICAL / PHYSICAL (derived) / SIMULATION / -- , from the supplied provenance. */
  provenance: string;
  /** CURRENT / STALE / UNKNOWN / UNAVAILABLE. */
  freshness: string;
  /** Age in seconds as the Twin reported it, when it reported one. */
  ageS: number | null;
  /** Why a value is absent, when there is a specific reason worth stating. */
  reason?: string | undefined;
}

/** The transport a frame arrived on. Distinct from provenance (telemetry_ingest.py:135). */
export type TelemetryTransport = "V2V" | "DIRECT_WIFI" | "SERIAL_GATEWAY" | "EMULATOR" | null;

export function telemetryTransport(vehicle: VehicleState | null | undefined): TelemetryTransport {
  const raw = vehicle?.provenance?.telemetry_transport?.value;
  if (typeof raw !== "string") return null;
  const upper = raw.toUpperCase();
  return upper === "V2V" ||
    upper === "DIRECT_WIFI" ||
    upper === "SERIAL_GATEWAY" ||
    upper === "EMULATOR"
    ? (upper as TelemetryTransport)
    : null;
}

function field(
  vehicle: VehicleState | null | undefined,
  name: string,
): TwinFieldProvenance | undefined {
  return vehicle?.provenance?.[name];
}

/** An absent readout. Never 0, never a placeholder number. */
function absent(label: string, reason?: string): HardwareReadout {
  return {
    label,
    value: UNAVAILABLE_VALUE,
    available: false,
    provenance: UNAVAILABLE_VALUE,
    freshness: DATA_STATE_TEXT.UNAVAILABLE,
    ageS: null,
    reason,
  };
}

/**
 * Build one readout from a supplied Twin field.
 *
 * A field the Twin marked unavailable, or one carrying a non-finite value, becomes
 * `absent` - it is never rendered as a number.
 */
export function readout(
  vehicle: VehicleState | null | undefined,
  name: string,
  label: string,
  unit: string,
  digits = 2,
  reasonWhenAbsent?: string,
): HardwareReadout {
  const f = field(vehicle, name);
  const state: DataState = fieldDataState(f);
  if (!f || state === "UNAVAILABLE") return absent(label, reasonWhenAbsent);

  const raw = f.value;
  if (typeof raw !== "number" || !Number.isFinite(raw)) return absent(label, reasonWhenAbsent);

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

// ---------------------------------------------------------------------------
// the physical fields
// ---------------------------------------------------------------------------

/** Wheel RPM — the one directly measured quantity on this prototype. */
export function rpmReadout(vehicle: VehicleState | null | undefined): HardwareReadout {
  return readout(vehicle, "rpm", "Wheel RPM", "rev/min", 1, "No encoder reading supplied.");
}

/**
 * Encoder-derived speed.
 *
 * Present only when a measured RPM AND a calibrated wheel radius exist. The ingestor
 * leaves it absent rather than guessing, and so does this.
 */
export function derivedSpeedReadout(vehicle: VehicleState | null | undefined): HardwareReadout {
  return readout(
    vehicle,
    "speed_mps",
    "Speed (derived from wheel RPM)",
    "m/s",
    2,
    "No encoder-derived speed supplied. Requires a measured RPM and a calibrated wheel radius.",
  );
}

/**
 * TRUCK_02's PWM-derived speed, when the Twin carries one.
 *
 * Labelled for what it is. This is NOT an encoder measurement and the label says so on
 * the readout itself, not only in a tooltip.
 */
export function pwmSpeedReadout(vehicle: VehicleState | null | undefined): HardwareReadout | null {
  const f = field(vehicle, "speed_mps_pwm_derived");
  if (!f) return null;
  const built = readout(vehicle, "speed_mps_pwm_derived", "Speed (PWM-derived)", "m/s", 2);
  return {
    ...built,
    reason: "Commanded prototype velocity, NOT an encoder measurement.",
  };
}

/** MPU6050 acceleration, all three axes. */
export function accelReadouts(vehicle: VehicleState | null | undefined): HardwareReadout[] {
  return [
    readout(vehicle, "ax_mps2", "Accel X", "m/s²", 2, "No IMU reading supplied."),
    readout(vehicle, "ay_mps2", "Accel Y", "m/s²", 2, "No IMU reading supplied."),
    readout(vehicle, "az_mps2", "Accel Z", "m/s²", 2, "No IMU reading supplied."),
  ];
}

/** MPU6050 gyroscope, all three axes. */
export function gyroReadouts(vehicle: VehicleState | null | undefined): HardwareReadout[] {
  return [
    readout(vehicle, "gx_rad_s", "Gyro X", "rad/s", 3, "No IMU reading supplied."),
    readout(vehicle, "gy_rad_s", "Gyro Y", "rad/s", 3, "No IMU reading supplied."),
    readout(vehicle, "gz_rad_s", "Gyro Z", "rad/s", 3, "No IMU reading supplied."),
  ];
}

/** Wi-Fi signal strength, as measured by the ESP32. */
export function rssiReadout(vehicle: VehicleState | null | undefined): HardwareReadout {
  return readout(vehicle, "rssi_dbm", "Wi-Fi RSSI", "dBm", 0, "No RSSI supplied.");
}

/**
 * SNR — suppressed on a DIRECT_WIFI frame.
 *
 * The firmware substitutes a hard-coded 9.5 dB whenever it holds no valid LoRa packet,
 * and the backend's own default is also 9.5, so the two are indistinguishable downstream.
 * On a frame that arrived over Wi-Fi there is no LoRa link to have measured, so the only
 * honest rendering is UNAVAILABLE with the reason stated.
 *
 * A genuine V2V or SERIAL_GATEWAY frame keeps its supplied value.
 */
export function snrReadout(vehicle: VehicleState | null | undefined): HardwareReadout {
  if (telemetryTransport(vehicle) === "DIRECT_WIFI") {
    return absent("SNR", "LoRa SNR is not available for DIRECT_WIFI telemetry.");
  }
  return readout(vehicle, "snr_db", "SNR", "dB", 1, "No SNR supplied.");
}

/**
 * Everything the physical vehicle actually reports, in display order.
 *
 * Fields with no producer are simply not in this list. Nothing here stands in for
 * position, heading, GNSS, visibility, friction or a safety value - those have no sensor
 * on this prototype, and the screens state that separately rather than showing a row that
 * is permanently blank.
 */
export function hardwareReadouts(vehicle: VehicleState | null | undefined): HardwareReadout[] {
  const rows: HardwareReadout[] = [rpmReadout(vehicle), derivedSpeedReadout(vehicle)];
  const pwm = pwmSpeedReadout(vehicle);
  if (pwm) rows.push(pwm);
  rows.push(
    ...accelReadouts(vehicle),
    ...gyroReadouts(vehicle),
    rssiReadout(vehicle),
    snrReadout(vehicle),
  );
  return rows;
}

/** True when at least one hardware field carries a supplied value. */
export function hasAnyHardwareReadout(vehicle: VehicleState | null | undefined): boolean {
  return hardwareReadouts(vehicle).some((row) => row.available);
}
