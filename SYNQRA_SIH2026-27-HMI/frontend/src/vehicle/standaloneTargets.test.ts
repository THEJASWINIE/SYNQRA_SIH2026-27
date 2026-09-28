import { describe, expect, it } from "vitest";
import type { AppState } from "../contracts/appState";
import { vehicleConfig } from "./vehicleConfig";
import { projectVehicle } from "./vehicleProjection";

describe("Three-HMI Standalone Target Specifications", () => {
  it("binds TRUCK_01 target to fixed vehicle identity and port 3001", () => {
    const config = vehicleConfig("TRUCK_01");
    expect(config.vehicleId).toBe("TRUCK_01");
    expect(config.displayName).toBe("TRUCK_01");
    expect(config.devPort).toBe(3001);
  });

  it("binds TRUCK_02 target to fixed vehicle identity and port 3002", () => {
    const config = vehicleConfig("TRUCK_02");
    expect(config.vehicleId).toBe("TRUCK_02");
    expect(config.displayName).toBe("TRUCK_02");
    expect(config.devPort).toBe(3002);
  });

  it("strictly isolates projected vehicle state per target", () => {
    const mockState: AppState = {
      connection: {
        status: "CONNECTED",
        provider: "MOCK",
        scenarioName: "DEFAULT",
        lastMessageAt: "2026-09-09T12:00:00Z",
        error: null,
      },
      clock: { now: "2026-09-09T12:00:00Z", replayPosition: null },
      vehicles: {
        TRUCK_01: {
          vehicleId: "TRUCK_01",
          mode: "NORMAL",
          vehicleKind: "DUMPER",
          speedMps: 12.5,
          position: { x: 10, y: 20, segmentId: "SEG_1", offsetM: 100 },
          accelMps2: 0,
          gradeRad: 0,
          commConfidence: 1.0,
          frictionEst: null,
          routeId: null,
          timestamp: "2026-09-09T12:00:00Z",
        },
        TRUCK_02: {
          vehicleId: "TRUCK_02",
          mode: "NORMAL",
          vehicleKind: "DUMPER",
          speedMps: 8.0,
          position: { x: 30, y: 40, segmentId: "SEG_2", offsetM: 200 },
          accelMps2: 0,
          gradeRad: 0,
          commConfidence: 1.0,
          frictionEst: null,
          routeId: null,
          timestamp: "2026-09-09T12:00:00Z",
        },
      },
      safety: {},
      road: {},
      forecasts: {},
      bottlenecks: {},
      arrivals: {},
      slots: {},
      dispatch: {},
      alerts: [],
      events: [],
      health: null,
      kpis: null,
      cv: null,
      commands: [],
      observability: {
        status: "CURRENT",
        data: null,
        fetchedAt: "2026-09-09T12:00:00Z",
        error: null,
      },
      topology: null,
    };

    const proj1 = projectVehicle(mockState, "TRUCK_01");
    expect(proj1.vehicleId).toBe("TRUCK_01");
    expect(proj1.vehicle?.speedMps).toBe(12.5);
    expect(proj1.peerVehicleId).toBe("TRUCK_02");
    expect(proj1.peer?.speedMps).toBe(8.0);

    const proj2 = projectVehicle(mockState, "TRUCK_02");
    expect(proj2.vehicleId).toBe("TRUCK_02");
    expect(proj2.vehicle?.speedMps).toBe(8.0);
    expect(proj2.peerVehicleId).toBe("TRUCK_01");
    expect(proj2.peer?.speedMps).toBe(12.5);
  });
});
