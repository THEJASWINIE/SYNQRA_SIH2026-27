# ARCHITECTURE DIAGRAM
## FOG-ORCHESTRATOR 2.0 — Data Health Layer Integration
Date: 2026-09-21

## Layered Architecture

  TELEMETRY SOURCES
  Mine Weather Station (visibility_m) | FMS Environmental (grade) | V2V LoRa Packets (speed, RPM, IMU)
           |                                    |                              |
           v                                    |                              v
  EnvironmentalDataHealth (NEW)                 |         telemetry_ingest.py + TelemetryQualityFilter
    H1: Freshness timeout                       |         BoundedSequenceTracker
    H2: Range check                             |         Provenance enforcement
    H3: Stuck-at detection                      |
    H4: Noise check                             |
    H5: Conflict (future)                       |
    Outputs: DataState, r_effective_health      |
           |                                    |
           v                                    v
  EnvironmentState(r_effective=r_effective_health)     TwinStateStore
           |                                               + env_data_state (NEW)
           v                                               + r_effective_applied (NEW)
  fog_safe.safety.solve_safe_speed()
    v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
           |
           v
  LocalVehicleSafetyGovernor [FINAL AUTHORITY - UNCHANGED]
    v_applied <= v_safe (INVARIANT I1)
    Invariants I1-I12
           |
           v
  VEHICLE ACTUATOR (CAN/TWAI command)

## State Enums (SEPARATE - do not merge)

DataState             CommunicationState          VehicleSafetyState
HEALTHY               NORMAL                      NORMAL
DEGRADED              DEGRADED_COMMUNICATION      RESTRICTED
STALE                 STALE_COMMAND               STAGED
CONFLICTING           NO_GATEWAY                  STOP
UNAVAILABLE           INVALID_COMMAND             EMERGENCY_STOP
                      UNSAFE_COMMAND              RECOVERY
                      STOP
                      EMERGENCY_STOP
                      RECOVERY

## Authority Hierarchy (Unchanged)
LEVEL 0: Firmware Watchdog / E-Stop (Physical)
LEVEL 1: LocalVehicleSafetyGovernor (FINAL)
LEVEL 2: Safe Beacon / V2V awareness
LEVEL 3: Central Fleet Orchestration
LEVEL 4: Fleet Optimization
LEVEL 5: Predictive Digital Twin

DATA HEALTH LAYER inserts BEFORE LEVEL 3 inputs reach the physics solver.
It does NOT insert between LEVEL 1 and the actuator.
