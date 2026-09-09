/**
 * Hardware telemetry readout tests — hardware integration of commit 83d05d3.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: the HMI states exactly what the prototype measures
 * and nothing more. A measured RPM says PHYSICAL, a speed computed from it says it was
 * derived, TRUCK_02's PWM speed is never dressed up as an encoder reading, and the
 * firmware's hard-coded 9.5 dB SNR never reaches an operator as a measurement.
 */

import { describe, expect, it } from "vitest";
import type { TwinFieldProvenance, VehicleState } from "../contracts/domain";
import { UNAVAILABLE_VALUE } from "./dataStatus";
import {
  accelReadouts,
  derivedSpeedReadout,
  gyroReadouts,
  hardwareReadouts,
  hasAnyHardwareReadout,
  pwmSpeedReadout,
  rpmReadout,
  rssiReadout,
  snrReadout,
  telemetryTransport,
} from "./hardwareTelemetry";

const T = "2026-01-01T00:00:00.000Z";

function f(partial: Partial<TwinFieldProvenance> = {}): TwinFieldProvenance {
  return {
    value: 0,
    timestamp: 1_788_681_152,
    source: "MEASURED",
    origin: "HARDWARE",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...partial,
  };
}

function vehicle(provenance: Record<string, TwinFieldProvenance>): VehicleState {
  return {
    vehicleId: "TRUCK_01",
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: null,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    provenance,
  };
}

/** A TRUCK_01 frame exactly as the Wi-Fi firmware + ingestor produce one. */
function truck01(): VehicleState {
  return vehicle({
    rpm: f({ value: 136.8 }),
    speed_mps: f({ value: 0.7163, source: "DERIVED" }),
    ax_mps2: f({ value: 0.12 }),
    ay_mps2: f({ value: -0.05 }),
    az_mps2: f({ value: 9.81 }),
    gx_rad_s: f({ value: 0.021 }),
    gy_rad_s: f({ value: 0.014 }),
    gz_rad_s: f({ value: -0.003 }),
    rssi_dbm: f({ value: -63 }),
    snr_db: f({ value: 9.5 }),
    telemetry_transport: f({ value: "DIRECT_WIFI", source: "DERIVED", origin: "DERIVED" }),
  });
}

// ---------------------------------------------------------------------------
// what the prototype genuinely measures
// ---------------------------------------------------------------------------

describe("physically measured fields", () => {
  it("wheel RPM is PHYSICAL", () => {
    const row = rpmReadout(truck01());
    expect(row.available).toBe(true);
    expect(row.value).toBe("136.8");
    expect(row.unit).toBe("rev/min");
    expect(row.provenance).toBe("PHYSICAL");
    expect(row.freshness).toBe("CURRENT");
  });

  it("speed says it was DERIVED from the wheel RPM, not measured directly", () => {
    const row = derivedSpeedReadout(truck01());
    expect(row.available).toBe(true);
    expect(row.value).toBe("0.72");
    expect(row.label).toContain("derived from wheel RPM");
    // source=DERIVED + origin=HARDWARE is physical, and says it was derived.
    expect(row.provenance).toBe("PHYSICAL (derived)");
    expect(row.provenance).not.toBe("PHYSICAL");
  });

  it("MPU6050 acceleration renders on all three axes as PHYSICAL", () => {
    const rows = accelReadouts(truck01());
    expect(rows.map((r) => r.label)).toEqual(["Accel X", "Accel Y", "Accel Z"]);
    expect(rows.map((r) => r.value)).toEqual(["0.12", "-0.05", "9.81"]);
    for (const row of rows) {
      expect(row.provenance, row.label).toBe("PHYSICAL");
      expect(row.unit, row.label).toBe("m/s²");
    }
  });

  it("MPU6050 gyroscope renders on all three axes as PHYSICAL", () => {
    const rows = gyroReadouts(truck01());
    expect(rows.map((r) => r.label)).toEqual(["Gyro X", "Gyro Y", "Gyro Z"]);
    expect(rows.map((r) => r.value)).toEqual(["0.021", "0.014", "-0.003"]);
    for (const row of rows) expect(row.provenance, row.label).toBe("PHYSICAL");
  });

  it("Wi-Fi RSSI is PHYSICAL and keeps its sign", () => {
    const row = rssiReadout(truck01());
    expect(row.value).toBe("-63");
    expect(row.unit).toBe("dBm");
    expect(row.provenance).toBe("PHYSICAL");
  });

  it("a supplied zero is kept as zero, never turned into unavailable", () => {
    // 0 rev/min is a stopped wheel. It is a measurement.
    const stopped = rpmReadout(vehicle({ rpm: f({ value: 0 }) }));
    expect(stopped.available).toBe(true);
    expect(stopped.value).toBe("0.0");
    expect(stopped.value).not.toBe(UNAVAILABLE_VALUE);
  });
});

// ---------------------------------------------------------------------------
// the SNR exception
// ---------------------------------------------------------------------------

describe("SNR on a DIRECT_WIFI frame", () => {
  it("does NOT present the firmware's 9.5 dB as a measured LoRa SNR", () => {
    const row = snrReadout(truck01());
    expect(row.available).toBe(false);
    expect(row.value).toBe(UNAVAILABLE_VALUE);
    expect(row.value).not.toContain("9.5");
    expect(row.reason).toBe("LoRa SNR is not available for DIRECT_WIFI telemetry.");
  });

  it("never labels the suppressed value PHYSICAL", () => {
    expect(snrReadout(truck01()).provenance).toBe(UNAVAILABLE_VALUE);
  });

  it("a genuine V2V frame keeps its supplied SNR", () => {
    const v2v = vehicle({
      snr_db: f({ value: 9.75 }),
      telemetry_transport: f({ value: "V2V", source: "DERIVED", origin: "DERIVED" }),
    });
    const row = snrReadout(v2v);
    expect(row.available).toBe(true);
    expect(row.value).toBe("9.8");
  });

  it("recognises the transports the ingestor defines, and nothing else", () => {
    expect(telemetryTransport(truck01())).toBe("DIRECT_WIFI");
    expect(
      telemetryTransport(vehicle({ telemetry_transport: f({ value: "SERIAL_GATEWAY" }) })),
    ).toBe("SERIAL_GATEWAY");
    expect(
      telemetryTransport(vehicle({ telemetry_transport: f({ value: "CARRIER_PIGEON" }) })),
    ).toBe(null);
    expect(telemetryTransport(vehicle({}))).toBe(null);
  });
});

// ---------------------------------------------------------------------------
// TRUCK_02 — PWM-derived, not measured
// ---------------------------------------------------------------------------

describe("TRUCK_02 PWM-derived speed", () => {
  const truck02 = vehicle({
    speed_mps_pwm_derived: f({ value: 0.42, source: "DERIVED", origin: "SIMULATION" }),
    telemetry_transport: f({ value: "V2V" }),
  });

  it("is labelled PWM-derived and never as an encoder measurement", () => {
    const row = pwmSpeedReadout(truck02);
    expect(row).not.toBeNull();
    expect(row?.label).toBe("Speed (PWM-derived)");
    expect(row?.label).not.toContain("wheel RPM");
    expect(row?.reason).toContain("NOT an encoder measurement");
  });

  it("does not claim to be physical", () => {
    expect(pwmSpeedReadout(truck02)?.provenance).toBe("SIMULATION");
  });

  it("is absent for a vehicle whose Twin carries no PWM speed", () => {
    expect(pwmSpeedReadout(truck01())).toBeNull();
  });

  it("its encoder-derived speed stays UNAVAILABLE rather than borrowing the PWM value", () => {
    const row = derivedSpeedReadout(truck02);
    expect(row.available).toBe(false);
    expect(row.value).toBe(UNAVAILABLE_VALUE);
    expect(row.reason).toContain("calibrated wheel radius");
  });
});

// ---------------------------------------------------------------------------
// absence, staleness and the fields no sensor produces
// ---------------------------------------------------------------------------

describe("unsupported and absent telemetry", () => {
  it("every readout is unavailable for a vehicle with no provenance at all", () => {
    const bare = vehicle({});
    for (const row of hardwareReadouts(bare)) {
      expect(row.available, row.label).toBe(false);
      expect(row.value, row.label).toBe(UNAVAILABLE_VALUE);
    }
    expect(hasAnyHardwareReadout(bare)).toBe(false);
  });

  it("a field the Twin marks unavailable is never rendered as a number", () => {
    const row = rpmReadout(vehicle({ rpm: f({ value: 136.8, available: false }) }));
    expect(row.available).toBe(false);
    expect(row.value).toBe(UNAVAILABLE_VALUE);
  });

  it("a non-finite value is treated as absent, not printed", () => {
    expect(rpmReadout(vehicle({ rpm: f({ value: Number.NaN }) })).available).toBe(false);
    expect(rssiReadout(vehicle({ rssi_dbm: f({ value: null }) })).available).toBe(false);
  });

  it("stale hardware keeps its last value and says STALE", () => {
    const stale = vehicle({ rpm: f({ value: 136.8, freshness: "STALE", ageS: 6.4 }) });
    const row = rpmReadout(stale);
    expect(row.available).toBe(true);
    expect(row.value).toBe("136.8"); // the value is NOT blanked
    expect(row.freshness).toBe("STALE");
    expect(row.ageS).toBe(6.4);
  });

  it("no readout is offered for a quantity this prototype cannot measure", () => {
    // position, heading, GNSS, visibility and friction are in NEVER_FROM_HARDWARE.
    // They must not appear as permanently-blank hardware rows.
    const labels = hardwareReadouts(truck01()).map((r) => r.label.toLowerCase());
    for (const missing of ["position", "heading", "gnss", "visibility", "friction", "v_safe"]) {
      expect(
        labels.some((l) => l.includes(missing)),
        missing,
      ).toBe(false);
    }
  });

  it("the full readout set for a live TRUCK_01 is exactly the measured fields", () => {
    const rows = hardwareReadouts(truck01());
    expect(rows.map((r) => r.label)).toEqual([
      "Wheel RPM",
      "Speed (derived from wheel RPM)",
      "Accel X",
      "Accel Y",
      "Accel Z",
      "Gyro X",
      "Gyro Y",
      "Gyro Z",
      "Wi-Fi RSSI",
      "SNR",
    ]);
    // Everything except the suppressed SNR carries a real supplied value.
    expect(rows.filter((r) => r.available)).toHaveLength(9);
    expect(hasAnyHardwareReadout(truck01())).toBe(true);
  });
});
