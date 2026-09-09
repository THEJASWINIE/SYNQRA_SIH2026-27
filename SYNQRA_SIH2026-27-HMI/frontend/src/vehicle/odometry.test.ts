import { describe, expect, it } from "vitest";
import { normalizeTwinVehicle } from "../data/normalize";
import type { RawTwinVehicle } from "../contracts/raw";

describe("Frontend TRUCK_01 Local Odometry Normalization & Isolation", () => {
  it("normalizes position_odom correctly for TRUCK_01", () => {
    const raw: RawTwinVehicle = {
      vehicle_id: "TRUCK_01",
      static: { vehicle_id: "TRUCK_01", kind: "TRUCK" },
      dynamic: {
        position_odom: {
          value: {
            x_m: 1.25,
            y_m: 0.5,
            heading_rad: 0.15,
            distance_m: 1.35,
            timestamp: 100.0,
            source: "DERIVED",
            origin: "HARDWARE",
            provenance_label: "PHYSICAL_DERIVED",
            method: "WHEEL_IMU_ODOMETRY",
            status: "VALID",
            origin_type: "LOCAL ODOMETRY ORIGIN",
            verification_label: "ALGORITHM VERIFIED",
          },
          timestamp: 100.0,
          source: "DERIVED",
          origin: "HARDWARE",
          quality: "GOOD",
          age_s: 0.1,
          available: true,
          clock_domain: "WALL_CLOCK",
          freshness: "LIVE",
        },
      },
    };

    const state = normalizeTwinVehicle(raw);
    expect(state.positionOdom).not.toBeNull();
    expect(state.positionOdom?.xM).toBe(1.25);
    expect(state.positionOdom?.yM).toBe(0.5);
    expect(state.positionOdom?.headingRad).toBe(0.15);
    expect(state.positionOdom?.distanceM).toBe(1.35);
    expect(state.positionOdom?.status).toBe("VALID");
    expect(state.positionOdom?.provenanceLabel).toBe("PHYSICAL_DERIVED");
    expect(state.positionOdom?.method).toBe("WHEEL_IMU_ODOMETRY");
  });

  it("handles TRUCK_02 odometry isolation (UNAVAILABLE state)", () => {
    const raw: RawTwinVehicle = {
      vehicle_id: "TRUCK_02",
      static: { vehicle_id: "TRUCK_02", kind: "TRUCK" },
      dynamic: {
        position_odom: {
          value: {
            x_m: null,
            y_m: null,
            heading_rad: null,
            distance_m: null,
            timestamp: 100.0,
            source: "UNKNOWN",
            origin: "UNKNOWN",
            provenance_label: "UNAVAILABLE",
            method: "NONE",
            status: "UNAVAILABLE",
            origin_type: "NONE",
            reason: "TRUCK_02 odometry is not supported in Pass 2",
            verification_label: "CONTRACT VERIFIED",
          },
          timestamp: 100.0,
          source: "UNKNOWN",
          origin: "UNKNOWN",
          quality: "UNKNOWN",
          age_s: null,
          available: false,
          clock_domain: "WALL_CLOCK",
          freshness: "UNAVAILABLE",
        },
      },
    };

    const state = normalizeTwinVehicle(raw);
    expect(state.positionOdom).not.toBeNull();
    expect(state.positionOdom?.status).toBe("UNAVAILABLE");
    expect(state.positionOdom?.provenanceLabel).toBe("UNAVAILABLE");
    expect(state.positionOdom?.xM).toBeNull();
  });
});
