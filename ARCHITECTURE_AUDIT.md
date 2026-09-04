# ARCHITECTURE AUDIT REPORT
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**DATE**: 2026-08-28  
**SYSTEM**: Mining Fleet Fog-Orchestrator Digital Twin & Supervisory HMI  

---

## 1. EXECUTIVE SUMMARY & AUDIT PURPOSE

This system audit was conducted to evaluate the entire existing software codebase across all sub-projects (`SYNQRA_SIH2026-27-main`, `SYNQRA_SIH2026-27-HMI`, `fog_orchestrator`, `fog_safe`, and `esp32_code`). The goal is to establish a rigorous, evidence-based module inventory and architecture gap analysis prior to physical hardware integration (ESP32/LoRa).

---

## 2. MODULE INVENTORY

| Module Name | File Location | Purpose | Input | Output | Data Format | Update Rate | Dependencies | Status | Executable | Integrated | Dead Code | Duplication Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **HMI Backend Main** | `SYNQRA_SIH2026-27-HMI/backend/app/main.py` | FastApi entrypoint for HMI backend | HTTP GET | Health status | JSON | On demand | `fastapi`, `pydantic` | PARTIAL | Yes | No (Lacks WS `/ws/live`) | No | None |
| **HMI Frontend Shell** | `SYNQRA_SIH2026-27-HMI/frontend/src/App.tsx` | React UI Application | DataProvider patch stream | React DOM | TSX/React State | 60 Hz UI refresh | React, Lucide, Tailwind/CSS | COMPLETE | Yes | Mock only | No | None |
| **HMI Data Normalizer** | `SYNQRA_SIH2026-27-HMI/frontend/src/data/normalize.ts` | Schema validation & camelCase normalization | Raw JSON WebSocket msg | Normalized Domain Objects | TypeScript Objects | Streamed | Zod | COMPLETE | Yes | Yes (in Mock) | No | None |
| **Digital Twin Simulator** | `SYNQRA_SIH2026-27-main/twin/simulator.py` | Main Digital Twin discrete time simulator | Weather, Graph, Fleet Cfg | Vehicle & Road States | Python Dicts / Dataclasses | 1.0 s step | `numpy`, `network` | COMPLETE | Yes | Partial | No | Paralleled by `fog_orchestrator/simulation` |
| **Mine Network Graph** | `SYNQRA_SIH2026-27-main/twin/network.py` | Road graph topology & node queues | Node & Edge definitions | Network graph & states | Python Objects | Static / Dynamic | None | COMPLETE | Yes | Yes | No | Paralleled by `fog_orchestrator/core/graph_network.py` |
| **Physics Braking Model** | `SYNQRA_SIH2026-27-main/models/braking.py` | Deceleration & safe speed calculation | Grade, friction, mass | `a_dec`, `v_stop` | Float values | Per step | `numpy` | COMPLETE | Yes | Yes | No | Duplicated in `fog_safe` and `fog_orchestrator` |
| **Bottleneck Score Model** | `SYNQRA_SIH2026-27-main/models/bottleneck.py` | Queue arrival/service bottleneck scoring | $\lambda, \mu$, queue, criticality | Bottleneck score | Float | Per step | None | COMPLETE | Yes | Yes | No | Duplicated in `fog_orchestrator` |
| **Road Capacity Model** | `SYNQRA_SIH2026-27-main/models/road_capacity.py` | Calculates road capacity $C_r(v, h)$ | $v_{\rm safe}$, safe headway | $C_r$ (vph) | Float | Per step | None | COMPLETE | Yes | Yes | No | None |
| **Arrival Shaping Controller** | `SYNQRA_SIH2026-27-main/control/arrival_shaping.py` | Downstream queue rate throttling | Crusher queue, service rate | Release delay (s) | Float | Per step | None | COMPLETE | Yes | Yes | No | None |
| **MILP / MPC Dispatch Optimizer** | `SYNQRA_SIH2026-27-main/optimizer/milp_dispatch.py` | Receding horizon fleet dispatch optimization | Twin state, horizon | Target speed & release commands | Dict / Command list | Per step | `scipy`, `numpy` | COMPLETE | Yes | Partial | No | Paralleled by `fog_orchestrator/tier3_central/optimizer.py` |
| **Task 1 HMI Interface Package** | `SYNQRA_SIH2026-27-main/interfaces/task1_hmi.py` | Serializes twin state for HMI | Twin objects | HMI State Vector | JSON Dict (Schema valid) | 1.0 s | `jsonschema` | COMPLETE | Yes | No (Not connected to FastAPI WS) | No | None |
| **Task 3 Vehicle Telemetry Adapter** | `SYNQRA_SIH2026-27-main/interfaces/task3_vehicle_io.py` | Ingests ESP32 telemetry JSON | Inbound Telemetry JSON | Updated Twin Vehicle | Python Dict / Objects | 0.1 s | `jsonschema` | COMPLETE | Yes | No (No live socket listener) | No | None |
| **Fog Safety Physics Solver** | `fog_safe/safety.py` | Multi-constraint safe speed solver | Vehicle, Road, Env, Comm | `SafeSpeedResult` | Dataclass | Analytical / Per step | `numpy` | COMPLETE | Yes | Standalone | No | Complete physics formulation |
| **RLS Friction Estimator** | `fog_safe/rls.py` & `fog_orchestrator/tier1_governor/safety_governor.py` | Recursive Least Squares friction estimation | $a_{\rm meas}$, grade, retarder force | $\hat{\mu}, \sigma_{\mu}, \mu_{\rm safe}$ | Tuple of floats | Per step | `math`/`numpy` | COMPLETE | Yes | Standalone | No | Duplicate algorithms |
| **Multi-Tier Fog Orchestrator** | `fog_orchestrator/simulation/simulator.py` | Multi-tier simulation engine | Scenarios | Metrics & Logs | Python Dicts | 1.0 s | Internal modules | COMPLETE | Yes | Standalone | No | Parallels `SYNQRA_SIH2026-27-main` |
| **ESP32 Vehicle A Sketch** | `esp32_code/sketch_aug26a/sketch_aug26a.ino` | Firmware for Vehicle A hardware | IMU, Wheel speed, LoRa | Telemetry JSON | C++ / Serial / LoRa | 100 ms | Arduino / ESP32 | COMPLETE | Hardware | Pending HIL | No | Firmware code |
| **ESP32 Vehicle B Sketch** | `esp32_code/vehicle_B/vehicle_B.ino` | Firmware for Vehicle B hardware | IMU, Wheel speed, LoRa | Telemetry JSON | C++ / Serial / LoRa | 100 ms | Arduino / ESP32 | COMPLETE | Hardware | Pending HIL | No | Firmware code |

---

## 3. ARCHITECTURE GAP ANALYSIS

### 3.1 CRITICAL SEVERITY GAPS

#### GAP-CRIT-01: Disconnected HMI Live Data Pipeline (Fake WebSocket Integration)
* **Description**: `SYNQRA_SIH2026-27-HMI/backend/app/main.py` only implements a static `/api/health` endpoint. It contains no WebSocket route (`/ws/live`), no connection manager, and no integration with the Digital Twin simulation running in `SYNQRA_SIH2026-27-main` or `fog_orchestrator`.
* **Impact**: The React HMI frontend is forced to operate in `mock` mode (`VITE_PROVIDER=mock`). Live simulation states, fog events, and vehicle telemetry do not reach the HMI backend or frontend in real time.
* **Remediation**: Implement a live WebSocket endpoint (`/ws/live`) in `SYNQRA_SIH2026-27-HMI/backend/app/main.py` that streams valid JSON state vectors formatted according to `HMI_STATE_SCHEMA` and accepts user commands.

#### GAP-CRIT-02: Fragmented & Duplicate Physics Safety Governors
* **Description**: The codebase contains three independent implementations of the safety governor:
  1. `SYNQRA_SIH2026-27-main/models/braking.py`
  2. `fog_orchestrator/tier1_governor/safety_governor.py`
  3. `fog_safe/safety.py`
* **Impact**: Inconsistent physical stopping calculations, latency penalty rules, and curve speed constraints across modules. Risk of safety violations if different components compute conflicting $v_{\rm safe}$ values.
* **Remediation**: Unify the safety governor into a single reference engine using the validated formulation from `fog_safe/safety.py` and `fog_orchestrator/tier1_governor/safety_governor.py`, enforcing $v_{\rm command} \le v_{\rm safe}$ and $\text{applied\_speed} = \min(v_{\rm command}, v_{\rm safe})$ globally.

---

### 3.2 HIGH SEVERITY GAPS

#### GAP-HIGH-01: Missing Hardware Interface Emulator (HIL Bridge)
* **Description**: No dedicated software emulator exists to model Vehicle A and Vehicle B hardware interfaces prior to physical ESP32/LoRa connection.
* **Impact**: Testing central optimizer commands and telemetry ingestion relies on internal simulation objects rather than realistic network interfaces with latency, packet drops, and stale data flags.
* **Remediation**: Create a dedicated Hardware Interface Emulator module (`hardware_emulator.py`) implementing Vehicle A and Vehicle B emulators with configurable transport impairments (delay, loss, stale telemetry, local safety governor clamp, and ACK generation).

#### GAP-HIGH-02: Disconnected Central Optimizer Command Flow
* **Description**: Optimizer recommendations generated by `optimizer/milp_dispatch.py` or `control/arrival_shaping.py` are applied directly as internal variable edits within scenario runs rather than passing through formal `DispatchCommand` structures with command IDs, timestamps, reason codes, and vehicle acknowledgements.
* **Impact**: The HMI and vehicle emulators cannot track command origin, reason codes, or execution status.
* **Remediation**: Wrap all central optimizer decisions in formal `DispatchCommand` message objects, route them through the vehicle interface emulator, and record command ACKs.

#### GAP-HIGH-03: Fragmented Test Suites & Pytest Import Collisions
* **Description**: Test files in `SYNQRA_SIH2026-27-main/tests` and `SYNQRA_SIH2026-27-main/V0_1_BASELINE/tests` share identical filenames (`test_bottleneck.py`, `test_capacity.py`, etc.), causing `pytest` import errors. Furthermore, required test categories specified in Section 14 are split across different directories.
* **Impact**: Automated continuous verification cannot be executed using a single standard `pytest` command.
* **Remediation**: Structure a unified root test directory (`tests/`) containing all 11 required test modules (`test_data_contract.py`, `test_physics.py`, `test_safety_governor.py`, `test_fog_propagation.py`, `test_queue_model.py`, `test_bottleneck_detection.py`, `test_optimizer.py`, `test_command_flow.py`, `test_stale_data.py`, `test_failure_modes.py`, `test_end_to_end.py`).

---

### 3.3 MEDIUM SEVERITY GAPS

#### GAP-MED-01: Unit Mismatches and Field Name Differences in Schemas
* **Description**: Slight field naming variations exist between contracts:
  - `speed_v` (m/s) in `task2_state_schema.py` vs `speed_mps` in `VEHICLE_TELEMETRY_SCHEMA` and Section 4 `VehicleState`.
  - Grade represented in percent (`grade_pct`) vs radians (`grade_rad`).
* **Impact**: Potential serialization errors or misinterpretation of units between components.
* **Remediation**: Enforce canonical unit conversions in data adapters (always m/s for speed, m for distance, m/s² for acceleration, rad for angles, vph for flow rates).

#### GAP-MED-02: Missing Baseline vs Orchestrator Formal Results CSV & Report Exporter
* **Description**: Baseline and Fog-Orchestrator comparative runs are computed in `main.py`, but the specific structured outputs `BASELINE_VS_ORCHESTRATOR_RESULTS.csv` and `BASELINE_VS_ORCHESTRATOR_REPORT.md` requested in Section 9 are not generated as distinct standalone artifacts.
* **Impact**: Harder for external stakeholders to inspect side-by-side performance metrics.
* **Remediation**: Implement a dedicated comparison script (`run_baseline_vs_orchestrator.py`) that executes both runs under identical fog profiles and writes both deliverables.

---

### 3.4 LOW SEVERITY GAPS

#### GAP-LOW-01: Standalone Game UI UI Disconnection
* **Description**: `game_ui.py` in `SYNQRA_SIH2026-27-main` uses Pygame for desktop visualization. It is standalone and does not consume data from the FastAPI HMI backend.
* **Impact**: Purely cosmetic; does not affect core orchestration or web HMI.
* **Remediation**: Document `game_ui.py` as a legacy local visualizer; focus primary supervisory monitoring on the React web HMI.

---

## 4. AUDIT SUMMARY & VERDICT

The underlying physics models, queue dynamics, RLS friction estimation, and optimizer algorithms are sound and mathematically validated. However, **the sub-projects operate in isolation**. The Digital Twin simulation is decoupled from the HMI FastAPI backend, and vehicle telemetry integration lacks a dedicated software-HIL emulator. 

Executing the remediation plan outlined above will bridge all components into one coherent, fully validated end-to-end system ready for physical ESP32/LoRa hardware integration.
