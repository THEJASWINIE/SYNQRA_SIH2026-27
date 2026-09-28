# PHASE 8 — HARDWARE-IN-THE-LOOP (HIL) ARCHITECTURE
## FOG-ORCHESTRATOR 2.0 — SIH26007
### Autonomous Safety Validation & CAN/TWAI Integration Report

---

## 1. Executive Summary & Objective

Phase 8 moves FOG-ORCHESTRATOR 2.0 one critical layer closer to physical mining vehicle integration by implementing an authoritative, closed-loop **Hardware-in-the-Loop (HIL)** safety validation architecture. This layer integrates:
1. **A Simulated Vehicle ECU** modeling longitudinal haul truck dynamics, powertrain RPM, service brake hydraulic pressure, retarder torque, and wheel odometry.
2. **An Isolated CAN 2.0B / TWAI 250 kbps Bus Emulator** implementing 29-bit extended frame transport adhering to SAE J1939 parameter group number (PGN) conventions.
3. **An Onboard ESP32 Safety Controller (Local Safety ECU)** hosting the canonical Tier-1 physics solver (`fog_safe.safety.solve_safe_speed`), the local safety governor (`LocalVehicleSafetyGovernor`), and peer safety beacon processing (`SafeBeaconAdapter`).
4. **An Actuator Response Model** simulating electro-pneumatic brake valve delays ($\tau \in [200, 350]\text{ ms}$) while enforcing the absolute physical constraint that the actuator cannot accelerate beyond the commanded speed ceiling ($v_{\text{actuator}} \le v_{\text{command}}$).
5. **Operator HMI Cab HUD Presentation Bridge** supplying situational awareness telemetry and explicit restriction reasons directly from authoritative Twin/ECU state.

```
       ┌────────────────────────────────────────────────────────┐
       │             SIMULATED VEHICLE POWERTRAIN / ECU         │
       │                                                        │
       │  Mass: 165.5 t | Grade: ±8% | Rolling Resistance: 0.02 │
       │  Wheel Speed | Engine RPM | Hydraulic Brake Pressure   │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                       CAN 2.0B / TWAI (250 kbps)
               [ENGINE_SPEED, VEHICLE_SPEED, BRAKE_STATUS]
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │             ONBOARD LOCAL SAFETY ECU (ESP32)           │
       │                                                        │
       │  Canonical Physics Solver: solve_safe_speed()          │
       │  Tier-1 Local Safety Governor: evaluate_command()      │
       │  Peer Safe Beacon Adapter: 868 MHz LoRa                │
       └──────────────┬──────────────────────────┬──────────────┘
                      │                          │
                      │ CAN Dispatch             │ HUD Bridge Telemetry
                      │ [SAFETY_COMMAND]         │
                      ▼                          ▼
       ┌──────────────────────────────┐   ┌───────────────────────────┐
       │        ACTUATOR MODEL        │   │        OPERATOR HMI       │
       │                              │   │                           │
       │  tau: 200 ms nominal         │   │  Live Speed / Safe Speed  │
       │  tau: 300 ms delayed         │   │  Command / Visibility     │
       │  tau: 350 ms maximum         │   │  Grade / Action / Reason  │
       │  Invariant I11: v_act <= v_cmd│  │  Communication Status     │
       └──────────────┬───────────────┘   └───────────────────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │     VEHICLE LONGITUDINAL     │
       │          DYNAMICS            │
       └──────────────┬───────────────┘
                      │
                      └────── Closed-Loop Dynamics Feedback ↺
```

---

## 2. Evidence Boundary & Provenance Classification

To preserve scientific and industrial integrity (in accordance with Master Prompt Section 2 and Non-Negotiable Rule 3):

| Subsystem Component | Engineering Classification | Provenance & Evidence Boundary | What is NOT Claimed |
|---|---|---|---|
| **ESP32 CAN/TWAI Controller** | `L7_BENCH_MEASURED` | Validated on bench microcontroller registers; 250 kbps bit timing, 0.512 ms wire propagation, and queue arbitration. | **NOT** an OEM Cummins CM2350 or Allison transmission proprietary ECU tap. |
| **CAN Frame Definitions** | `SIMULATED_J1939_COMPATIBLE` | Uses standard 29-bit extended IDs and standard PGN bit layouts (EEC1, CCVS, EBC1, ERC1, PropB). | **NOT** an OEM BEML BH100 proprietary factory CAN bus database. |
| **Haul Truck Dynamics** | `L6_MODELED` | Longitudinal mass-balance kinematics ($M = 165.5\text{ t}$, $C_{rr} = 0.02$, grade $\pm 8\%$). | **NOT** an empirical instrumented field run on a physical 165-tonne truck at Bailadila. |
| **Brake Deceleration** | `MODEL_DERIVED / ASSUMPTION` | Emergency decel $2.7856\text{ m/s}^2$ (model-derived); service decel $1.20\text{ m/s}^2$ (engineering assumption). | **NOT** physical BH100 brake drum/disc dynamometer test data. |
| **Actuator Delay** | `L6_MODELED` | Modeled first-order lag with pure time delay $\tau \in [200, 350]\text{ ms}$. | **NOT** physical pneumatic valve pressure transducer measurement on a BH100. |
| **Operator HMI Bridge** | `DEMONSTRATED` | Integrated software projection feeding in-cab HTML/React HUD with live reason disclosure. | **NOT** an MSHA-certified physical in-cab rugged display. |

---

## 3. Communication Hierarchy & Safety Authority

The communication fail-safe hierarchy established in Phase 7.4 remains strictly frozen:

$$\text{PRIMARY: DSSS / Gateway Coordination} \longrightarrow \text{FALLBACK: Local Safe Beacon} \longrightarrow \text{ULTIMATE: Local Vehicle Safety Governor}$$

### Invariable Safety Ordering:
$$\text{LOCAL SAFETY GOVERNOR} > \text{LOCAL SAFETY AWARENESS} > \text{CENTRAL FLEET ORCHESTRATION}$$

### Fundamental Physical Invariant:
$$v_{\text{applied}} \le v_{\text{safe}}$$

Under no circumstance can a central fleet dispatch optimizer, network packet, or corrupt telemetry frame increase the applied vehicle speed beyond the local physical safe ceiling $v_{\text{safe}}$ determined by onboard sensors.

---

## 4. Subsystem Interfaces & Protocols

### 4.1 CAN/TWAI Physical & Transport Layer
- **Bitrate:** 250 kbps (standard heavy-duty commercial vehicle bus).
- **Identifier Type:** 29-bit Extended Identifiers (CAN 2.0B / ISO 11898-1).
- **Nominal Bit Time:** $4.0\ \mu\text{s}$.
- **Nominal Frame Size (DLC=8):** 128 bit times = $0.512\text{ ms}$ raw transmission time.
- **Mean Bench Arbitration Latency:** $5.79\text{ ms}$ (P95: $19.17\text{ ms}$).

### 4.2 Local Safety ECU Execution Cycle
The onboard ESP32 execution cycle runs deterministically on a 50 ms loop:
1. **Sensor Ingestion (1.26 ms):** Receive wheel speed, engine RPM, brake status from CAN bus.
2. **Physics Envelope Solver (2.20 ms):** Call canonical solver $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$.
3. **Local Governor Evaluation (0.15 ms):** Verify command timestamp freshness, sequence monotonicity, and apply local ceiling clamp.
4. **CAN Dispatch (0.512 ms):** Transmit `CAN_ID_SAFETY_COMMAND` (`0x0CFF0101`) to chassis actuator.
5. **Actuator Modulation (200.0 ms nominal):** Modulate service brakes and retarder toward target speed.
6. **Telemetry & HMI (0.93 ms):** Dispatch vehicle HUD status packet to Operator HMI.

---

## 5. Summary of Phase 8 Deliverables

1. **CAN/TWAI HIL Driver:** [`integration_adapters/can_twai_hil.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/can_twai_hil.py)
2. **Closed-Loop HIL Simulator:** [`integration_adapters/hil_simulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/hil_simulator.py)
3. **Automated HIL Test Suite (60 tests):** [`tests/test_phase8_hil.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/test_phase8_hil.py)
4. **Benchmark & Parametric Sweep:** [`experiments/run_phase8_hil_validation.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_phase8_hil_validation.py)
5. **Empirical CSV Dataset (105 scenarios):** [`data/phase8_hil_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase8_hil_results.csv)
6. **Evaluator Demonstration:** [`experiments/run_phase8_evaluator_demo.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_phase8_evaluator_demo.py)
7. **Canonical Configuration:** [`config/PHASE8_HIL_CONFIG.yaml`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/config/PHASE8_HIL_CONFIG.yaml)
