# PHASE 7.3.2 — REPORT 15: FINAL J1939 EVIDENCE AUDIT
## Bench TWAI Measurements vs Physical Vehicle J1939 Scope
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. The Critical Architectural Distinction

To prevent any misleading claims regarding vehicle communication, FOG-ORCHESTRATOR 2.0 permanently maintains the distinction between bench transceiver experiments and physical machine ECU integration:

$$\mathbf{\text{ESP32 TWAI Bench Testbed}} \quad \neq \quad \mathbf{\text{BEML BH100 Chassis J1939 Network}}$$

* The bench experiments demonstrate firmware driver compatibility, message serialization, and priority arbitration under the **Two-Wire Automotive Interface (TWAI)** at $250\text{ kbps}$.
* Logging, commanding, and testing on an operational BEML BH100 dumper in the Bailadila open-cast pit is **FIELD-UNVALIDATED**.

---

### 2. Decomposition of Vehicle Command Latency

The delay between governor decision output and mechanical deceleration is decomposed into physical stages:

| Stage | Physical Process | Typical SAE J1939 Spec | Project Conservative Model | Evidence Level | Verification Status |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **1. CAN Serialization** | 128-bit frame @ 250 kbps | $0.51\text{ ms}$ | $1.0\text{ ms}$ | BENCH_MEASURED | Verified on TWAI bench |
| **2. Arbitration Latency** | Priority bus contention (PGN 0) | $1.0\text{--}5.0\text{ ms}$ | $10.0\text{ ms}$ | BENCH_MEASURED | Verified under simulated 60% bus load |
| **3. ECU Message Ingest** | Engine / Brake controller loop | $10.0\text{--}20.0\text{ ms}$| $39.0\text{ ms}$ | ENGINEERING_ASSUMPTION | Conservative buffer pending OEM access |
| **Total CAN Loop Budget**| Governor to Brake Controller | **< 25.0 ms** | **50.0 ms** | **CONSERVATIVE BOUND** | **YELLOW** |
| **4. Hydraulic Actuator** | Solenoid valve + caliper fill | $180\text{--}260\text{ ms}$| $250.0\text{ ms}$ | SURROGATE_BENCH | Verified on surrogate hydraulic bench |
| **5. Vehicle Deceleration** | Brake torque $\to$ Wheel slip $\to$ Stop | $1,500\text{--}2,500\text{ ms}$| $1,863.0\text{ ms}$ | DERIVED_MODEL | Derived from force balance on -8% ramp |

---

### 3. ESP32 TWAI Bench Results

* **Controller**: ESP32 built-in TWAI controller (SJA1000 compatible) with external SN65HVD230 $3.3\text{V}$ CAN transceiver.
* **Baud Rate**: $250\text{ kbps}$ (SAE J1939 standard).
* **Frame Format**: 29-bit extended identifier (PGN 61444 - Electronic Engine Controller 1, PGN 61441 - Electronic Brake Controller 1).
* **Measured Hardware Latency**: Mean **$1.84\text{ ms}$** transmission and acknowledgment on clean bus; **$4.12\text{ ms}$** under $60\%$ background packet injection.
* **Zero Frame Drop**: $10,000$ consecutive frames transmitted without arbitration loss or bus-off errors.

---

### 4. Permanent Claim Scope

> **CANONICAL STATUS**:  
> **"TWAI/J1939 protocol implementation and message arbitration are verified on bench hardware. Physical bus tapping, parameter monitoring, and command injection on the BEML BH100 chassis ECU remain FIELD-UNVALIDATED pending NMDC site access."**
