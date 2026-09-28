# FULL SYSTEM INVENTORY: FOG-ORCHESTRATOR 2.0 (PHASE 9)
**NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System**  
**Document ID:** `01_FULL_SYSTEM_INVENTORY.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026  
**Status:** FROZEN & VERIFIED  

---

## 1. Executive Summary & Inventory Purpose

This document provides a comprehensive, rigorous inventory of all physical hardware, microcontroller firmware, sensor systems, communication interfaces, control software, human-machine interfaces (HMIs), Digital Twin engines, and testing frameworks comprising the FOG-ORCHESTRATOR 2.0 system.

In strict adherence to **Rule 1 (Do not rewrite working systems)**, **Rule 3 (Never fabricate telemetry)**, and the **System-of-Systems Authority Hierarchy**, every subsystem is inventoried with its file location, implementation language, protocols, update frequencies, data owners, safety relevance, and verification status.

---

## 2. Comprehensive Subsystem Registry (A through Q)

| ID | Subsystem Name | Physical / Code Location | Language / Tech Stack | Input Protocol / Source | Output Protocol / Destination | Update Rate | Safety Class | Validation Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **A** | **Vehicle Hardware (HEMM Chassis)** | Physical BEML BH100 chassis & motor testbench (`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR`) | Mechanical / Electrical / PWM | PWM Throttle, CAN brake request | Wheel torque, hydraulic braking, chassis motion | Continuous | Tier-1 Safety Critical | L4 Bench Hardware Verified |
| **B** | **MCU Firmware** | `esp32_code/LORA_GATEWAY_RECEIVER/`<br>`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/` | C++ / Arduino ESP32 core | SPI, I2C, UART, GPIO | CAN (TWAI 250 kbps), LoRa 433 MHz, USB Serial | 10 Hz (100 ms) | Tier-1 Safety Critical | L4 Bench Hardware Verified |
| **C** | **Sensors** | MPU6050 IMU, Optical Tachometer, Analog Lux/Fog sensor, GNSS receiver | Embedded C++ / Python emulators | Physical optical/inertial stimuli | I2C (0x68), ADC (0-3.3V), NMEA UART | 10 Hz - 50 Hz | Tier-1 Safety Critical | L4 Bench Hardware Verified |
| **D** | **CAN / J1939 Bus** | `integration_adapters/can_twai_hil.py`<br>ESP32 TWAI Peripheral | Python / C++ | CAN Rx buffer (250 kbps) | CAN Tx buffer (J1939 PGNs) | 10 Hz - 50 Hz | Tier-1 Safety Critical | L3 HIL / L4 Bench Verified |
| **E** | **RF Hardware** | Semtech SX1278 Ra-02 (433 MHz)<br>`integration_adapters/dsss_gateway_selector.py` | C++ / Python adapter | SPI from ESP32 | 433 MHz Chirp Spread Spectrum (CSS) | 10 Hz | Tier-2 Infrastructure | L4 Bench Hardware (CSS) / L2 Research (DSSS) |
| **F** | **Gateway Software** | `SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py`<br>`integration_adapters/dsss_gateway_selector.py` | Python / FastAPI | USB Serial (115200 baud) from ESP32 | WebSocket `/ws/telemetry`, REST API | 10 Hz | Tier-2 Monitoring / Dispatch | L2 Software-in-Loop Verified |
| **G** | **Safety Governor** | `integration_adapters/fail_safe_controller.py`<br>`fog_orchestrator/tier1_governor/safety_governor.py`<br>`failsafe/safe_beacon.py` | Python (Pydantic, NumPy) | Canonical VehicleState, RoadState, CAN | Local vehicle brake/throttle command | 10 Hz | **Tier-1 Final Safety Authority** | L2/L3 Verified (100% Pass) |
| **H** | **Sensor-Health Engine** | `integration_adapters/environmental_data_health.py`<br>`sensor_degradation_research/` | Python | Raw telemetry sequences, visibility | 8-State SensorQuality, Confidence, r_effective | 10 Hz | Tier-1 Safety Critical | L2/L3 Verified (100% Pass) |
| **I** | **Operator HMI** | `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx`<br>`VehicleHmiApp.tsx` | React 18, TypeScript, CSS | WebSocket `/ws/telemetry`, CAN state | Visual display, audible tones, driver action alerts | 10 Hz (<= 100 ms) | Advisory / Situational Awareness | L2 Verified (Vitest & Playwright) |
| **J** | **Control-Room HMI** | `SYNQRA_SIH2026-27-HMI/frontend/src/`<br>`fog-orchester-3d-digital-twin/dashboard` | React, TypeScript, Three.js / WebGL | WebSocket `/ws/fleet`, REST API | Dispatch requests, fleet monitoring, incident alerts | 2 Hz - 10 Hz | Monitoring & Decision Support | L2 Verified |
| **K** | **Digital Twin Core** | `fog-orchester-3d-digital-twin/twin/`<br>`fog_orchestrator/simulation/`<br>`integration_adapters/canonical_twin_client.py` | Python (NumPy, SciPy) | Real vehicle telemetry, road geometry, weather | Predicted state, what-if stopping envelope, risk | 10 Hz | Predictive / Non-authoritative | L2 Verified |
| **L** | **Database & Event Logger** | `SYNQRA_SIH2026-27-HMI/frontend/src/state/eventLog.ts`<br>`SYNQRA_SIH2026-27-HMI/frontend/src/state/recorder.ts` | SQLite / CSV / JSONL | Incident triggers, telemetry stream | Append-only audit records, CSV export | Event-driven / 10 Hz | Audit & Diagnostics | L2 Verified |
| **M** | **APIs (FastAPI Backend)** | `SYNQRA_SIH2026-27-HMI/backend/app/main.py` | Python (FastAPI, Uvicorn) | HTTP POST `/api/telemetry`, `/api/commands` | HTTP 200/400/422 responses, WebSocket broadcasts | Real-time | Integration & Ingestion | L2 Verified |
| **N** | **Message Buses** | Physical CAN 250 kbps, WebSocket, P2P V2V | CAN 2.0B / WebSocket RFC 6455 | Ingestion adapters | Distributed HMI and Digital Twin clients | 10 Hz - 50 Hz | Communication Transport | L3/L4 Verified |
| **O** | **Configuration** | `config/integration_canonical.yaml`<br>`fog_orchestrator/core/config.py` | YAML / Pydantic | Static config files | Canonical parameters with provenance classification | On boot | System Configuration | L2 Verified |
| **P** | **Automated Tests** | `tests/` (1082 tests)<br>`SYNQRA_SIH2026-27-HMI/frontend/src/**/*.test.ts*` | Pytest, Vitest | Unit, integration, HIL, adversarial suites | Test reports, assertion validations | CI/CD on demand | Verification Framework | 1082 Passed, 1 Skipped |
| **Q** | **HIL Infrastructure** | `integration_adapters/can_twai_hil.py`<br>`integration_adapters/hil_simulator.py`<br>`run_physical_hil_test.py` | Python / Hardware loop | Physical/emulated sensor and CAN buses | End-to-end timing, jitter, fault injection | 100 Hz simulation step | Verification Infrastructure | L3 HIL Verified |

---

## 3. Subsystem Interconnection & Authority Flow

```
                      +---------------------------------------+
                      |           CONTROL ROOM HMI            |
                      |   Fleet Map | Incident Alerts | View  |
                      +-------------------+-------------------+
                                          |
                                          | (WebSocket / REST - Advisory Only)
                                          v
                      +---------------------------------------+
                      |         CENTRAL ORCHESTRATOR          |
                      |   Fleet Optimization | Staging Plan   |
                      +-------------------+-------------------+
                                          |
                                          | (Dispatch Speed Request)
                                          v
                      +---------------------------------------+
                      |            DIGITAL TWIN               |
                      |  What-If Simulation | Safe Prediction |
                      +-------------------+-------------------+
                                          |
                                          | (Advisory Speed Recommendation)
                                          v
                      +=======================================+
                      |        LOCAL SAFETY GOVERNOR          |
                      |    *** FINAL VEHICLE AUTHORITY ***     |
                      |   v_command = min(v_dispatch, v_safe) |
                      +===================+===================+
                                          |
                                          | (CAN / TWAI 250 kbps)
                                          v
                      +---------------------------------------+
                      |             HEMM CHASSIS              |
                      |   BEML BH100 Actuators & Sensors      |
                      +-------------------+-------------------+
                                          |
                                          | (Visual / Audible Warnings)
                                          v
                      +---------------------------------------+
                      |             OPERATOR HMI              |
                      |   Speed | Safe Speed | Fog Alert      |
                      +---------------------------------------+
```

### Strict Authority Rules:
1. **Rule of Local Sovereign:** The Local Safety Governor running on the vehicle ECU has the sole and final authority to actuate brakes. Remote commands from the Control Room or Digital Twin are strictly advisory proposals capped by `v_safe`.
2. **Rule of Failsafe Decoupling:** Complete failure or disconnection of the Control Room HMI, Operator HMI, or Digital Twin leaves the Local Safety Governor fully autonomous and operating in SAFE MODE.
3. **RF Modulation Truthfulness:** Semtech SX1278 Ra-02 hardware operates via CSS (LoRa). DSSS/PN code processing is an evaluated software research model.
