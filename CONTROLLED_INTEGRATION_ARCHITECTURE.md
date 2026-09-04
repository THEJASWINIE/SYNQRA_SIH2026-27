# FOG-ORCHESTRATOR 2.0 — CONTROLLED INTEGRATION ARCHITECTURE SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Non-Invasive Adapter Layer Architecture Specification

---

## 1. System Integration Block Diagram

```text
                    PHASE 1 (FROZEN ARCHITECTURE)
        ┌───────────────────────────────────────────────┐
        │ Physical Vehicles (TRUCK_01, TRUCK_02)        │
        │ ESP32 + TB6612 / L298N + LM393 + MPU6050      │
        └───────────────────────┬───────────────────────┘
                                │ LoRa 433 MHz
                                ▼
                         LoRa Gateway ESP32
                                │ USB Serial 115200
                                ▼
                         HMI Backend Store
                                │
                                │ Canonical Telemetry Payload
                                ▼
        ┌───────────────────────────────────────────────┐
        │ INTEGRATION ADAPTER LAYER (NEW MODULE)        │
        │                                               │
        │ 1. Vehicle ID Mapper Adapter                  │
        │ 2. Unit Converter Adapter                     │
        │ 3. Kinematic Scale Adapter                    │
        │ 4. IMU Processor Adapter                      │
        │ 5. Time Synchronization Adapter               │
        │ 6. Coordinate Mapper Adapter                  │
        │ 7. Telemetry Quality Filter Adapter           │
        │ 8. Command Adapter                            │
        └───────────────────────┬───────────────────────┘
                                │
                                │ Adapted State / Advisory Commands
                                ▼
                    PHASE 2 (INDEPENDENT TWIN)
        ┌───────────────────────────────────────────────┐
        │ Digital Twin Simulator & Mine Graph           │
        │ Fog Physics & Visibility Model (50m -> 15m)   │
        │ Queue & Bottleneck Detector (rho = lambda/mu) │
        │ Chance-Constrained MPC Central Orchestrator   │
        └───────────────────────────────────────────────┘
```

---

## 2. Fundamental Architectural Rule

$$\text{LOCAL SAFETY AUTHORITY } (v_{\text{local\_safe}}) > \text{CENTRAL OPTIMIZATION } (v_{\text{rec}})$$

No integration path allows the Digital Twin or Central Orchestrator to directly control physical motor drivers. All advisories pass through `CommandAdapter` and are evaluated by the physical vehicle ESP32 local safety governor before actuation.
