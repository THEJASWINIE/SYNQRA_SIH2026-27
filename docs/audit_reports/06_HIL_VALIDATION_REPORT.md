# 06 — HARDWARE-IN-THE-LOOP (HIL) VALIDATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Evidence Classification:** LEVEL 3 (Hardware-in-the-Loop Simulation)

---

## 1. HIL VALIDATION METHODOLOGY & TEST HARNESS

The HIL test harness combines:
1. **Virtual Chassis ECU (`SimulatedVehicleECU`):** Simulates BEML BH100 longitudinal dynamics, wheel speed, engine RPM, retarder torque, and 250 kbps CAN J1939 transmission.
2. **ESP32 TWAI Bus Emulator (`CanTwaiBusEmulator`):** Models physical wire delay (0.512 ms), arbitration queueing, frame timeouts, burst loss, and bit corruption.
3. **Local Safety ECU (`HilLocalSafetyECU`):** Executes the Level 1 Local Vehicle Safety Governor and multi-constraint physics envelope solver at 20 Hz.
4. **Hydraulic Actuator Model (`ActuatorModel`):** Injects nominal (200 ms), delayed (300 ms), and worst-case (350 ms) brake pressure buildup delays.
5. **Operator HMI Bridge (`OperatorHmiBridge`):** Packages situational awareness telemetry for the in-cab display.

---

## 2. COMPREHENSIVE HIL TEST EXECUTION MATRIX (TEST 01 TO 18)

| Test ID | Test Scenario Name | Primary Condition / Injected Fault | Expected System Reaction | Measured Applied Speed | Invariant I1 Respected? | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST 01** | Normal Operation | Clear visibility ($50\text{ m}$), $0\%$ grade, request $5.0\text{ m/s}$ | Normal speed regulation under fleet pacing | $5.000\text{ m/s}$ | **YES** ($v_{\text{app}} \le v_{\text{safe}}$) | **PASS** |
| **TEST 02** | Dense Fog | Dense fog ($8.0\text{ m}$), $-8\%$ grade, request $10.0\text{ m/s}$ | Governor clamps speed to crawl ceiling ($3.52\text{ m/s}$) | $3.520\text{ m/s}$ | **YES** ($v_{\text{app}} \le v_{\text{safe}}$) | **PASS** |
| **TEST 03** | Visibility Degradation | Visibility ramps $50\text{m} \to 25\text{m} \to 12\text{m} \to 8\text{m} \to 5\text{m} \to 3\text{m}$ | Monotonic speed reduction; complete halt at $\le 5\text{m}$ | $0.000\text{ m/s}$ @ $\le 5\text{m}$ | **YES** | **PASS** |
| **TEST 04** | Sensor Dropout | Environmental visibility stream drops to `None` | Fails closed: assigns conservative $R_{\text{eff}} = 8.0\text{ m}$ | $3.520\text{ m/s}$ | **YES** | **PASS** |
| **TEST 05** | Sensor Stuck-At | Frozen reading across $11$ samples ($>300\text{ s}$) | Flags `STUCK_AT`; penalizes confidence to $0.60$ | Clamped with 30% penalty | **YES** | **PASS** |
| **TEST 06** | Sensor Bias / Spike | Impossible reading ($5000\text{ m}$) injected | Plausibility range check rejects reading as invalid | Clamped to conservative baseline | **YES** | **PASS** |
| **TEST 07** | RF Packet Loss | $50\%$ stochastic packet drop on LoRa channel | Link state transitions to `DEGRADED`; clamps speed | Clamped to safe envelope | **YES** | **PASS** |
| **TEST 08** | Gateway Loss | Primary gateway times out after $1.0\text{ s}$ | Smooth failover to candidate gateway GW-02 | Uninterrupted safe travel | **YES** | **PASS** |
| **TEST 09** | Gateway Handover | Candidate beats current by switch margin ($+0.20$) | Handover executed after $3$ persistent observations | Smooth transition, no jump | **YES** | **PASS** |
| **TEST 10** | Total RF Comm Loss | Both LoRa gateway and peer V2V links severed | Remote commands rejected; Local Governor authoritative | $v_{\text{app}} = v_{\text{safe, local}}$ | **YES** | **PASS** |
| **TEST 11** | Safe Beacon Activation| Comm timeout exceeds $500\text{ ms}$ threshold | Autonomous Safe Beacon broadcasts at $2\text{ Hz}$ | Autonomous crawl | **YES** | **PASS** |
| **TEST 12** | CAN Latency Spike | CAN arbitration latency increases to $45\text{ ms}$ | Frame delivered within $150\text{ ms}$ timeout; no drop | Normal regulation | **YES** | **PASS** |
| **TEST 13** | CAN Timeout | Vehicle speed CAN frame delayed $>150\text{ ms}$ | Frame flagged stale; speed held safely at ceiling | Clamped defensively | **YES** | **PASS** |
| **TEST 14** | Delayed Actuator | Actuator lag increased to maximum $350\text{ ms}$ | Stopping envelope maintained; no overshoot | $v_{\text{app}} \le v_{\text{safe}}$ | **YES** | **PASS** |
| **TEST 15** | Invalid Command | Injected negative speed ($-5.0$) & `NaN` values | Local Governor rejects frame with error code | $0.000\text{ m/s}$ (Halt) | **YES** | **PASS** |
| **TEST 16** | Emergency Stop | Latched E-Stop button / critical fault trigger | Priority 1 overrides all; forces actuator to $0.0$ | $0.000\text{ m/s}$ | **YES** | **PASS** |
| **TEST 17** | Recovery Resync | Central gateway restored after outage | Mandates $2$ valid consecutive frames before resuming | Re-synchronized safely | **YES** | **PASS** |
| **TEST 18** | Simultaneous Degradation| Dense fog ($8\text{m}$) + Sensor Missing + Comm Lost | Conservative fail-closed compounding; safe crawl | $3.520\text{ m/s}$ crawl | **YES** | **PASS** |

---

## 3. SAFETY INVARIANTS AUDIT VERIFICATION

- **Invariant I1 ($v_{\text{applied}} \le v_{\text{safe}}$):** Verified across **100% of test steps** (0 violations across 10,000 steps).
- **Invariant I2 (No remote command during comm loss):** Verified in TEST 10 & TEST 18.
- **Invariant I3 (Safe Beacon timing):** Verified activation within $0.55\text{ s} \le 1.0\text{ s}$ window.
- **Invariant I4 (Local safety authority survives):** Verified in TEST 10.
- **Invariant I5 (Stale sensor handling):** Verified in TEST 04 & TEST 05.
- **Invariant I6 (Handover continuity):** Verified in TEST 09; acceleration bounded $\le 1.5\text{ m/s}^2$.
- **Invariant I7 (CAN timeout failsafe):** Verified in TEST 13.
- **Invariant I8 (Emergency stop priority):** Verified in TEST 16.
- **Invariant I9 (Bijective grade convention):** Verified downhill vs flat stopping envelopes.
- **Invariant I10 (No double integration):** Verified single-timestep kinematic dynamics.
- **Invariant I11 (Auditable decisions):** 100% of safety decisions carry UTC timestamps and logged rationale.

---

## 4. VERDICT & STATUS

- **Total HIL Test Cases Executed:** 18
- **Passed:** 18 (100.0%)
- **Failed:** 0
- **Regression Count:** 0
- **Status:** **PASS — HIL SAFETY VALIDATION COMPLETE**
