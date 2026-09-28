# PHASE 7.3.2 — REPORT 13: FINAL COMMUNICATION AUDIT
## Physical RF Hardware Verification vs Architectural Simulation Models
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Physical Hardware vs Simulation Model Boundary

To maintain complete scientific honesty, the project establishes a rigorous boundary between physical RF hardware and simulation models:

| Communication Layer | Physical Implementation | Operational Technology | Evidence Level | Measured / Modeled Performance | Field Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V2V Direct Link** | Physical ESP32 + Semtech SX1278 Transceiver | 433 MHz Chirp Spread Spectrum (CSS-LoRa) | **BENCH_MEASURED (L1)** | PDR = 99.1%, Latency = 41.2 ms, RSSI = -68 dBm | 150m LOS Bench |
| **V2I Gateway Relay**| Physical ESP32 Gateway Node | SX1278 LoRa RX $\to$ Serial $\to$ 2.4 GHz Wi-Fi UDP | **BENCH_MEASURED (L1)** | PDR = 98.4%, Relay latency = 78.6 ms | Bench Testbed |
| **DSSS / Gold-Code**| Python Simulation Subsystem (`simulation/rf_dsss.py`)| Direct Sequence Spread Spectrum (m-sequence codes)| **SIMULATION_MODEL (L5)**| Theoretical SNR processing gain = +12.0 dB | Simulation Only |
| **Bailadila Open-Cast**| Path loss attenuation model ($n = 3.8$, heavy rain/ore)| Log-distance shadow fading model | **SIMULATION_MODEL (L5)**| Modeled range = 450m in monsoon fog | Field Pending |

---

### 2. SX1278 Physical Bench Performance

* **Operating Frequency**: $433.0\text{ MHz}$ ISM band.
* **Modulation**: Chirp Spread Spectrum (CSS), Spreading Factor $SF = 7$, Bandwidth $BW = 125\text{ kHz}$, Coding Rate $CR = 4/5$.
* **Measured Packet Delivery Ratio (PDR)**:
  - Line-of-Sight ($150\text{ m}$ bench): $\mathbf{99.1\%}$ (991 / 1000 packets delivered).
  - Obstructed metal container bench: $\mathbf{94.6\%}$.
* **Round-Trip V2V Latency**: Mean $\mathbf{41.2\text{ ms}}$, P95 $\mathbf{50.0\text{ ms}}$, Max $\mathbf{68.4\text{ ms}}$.
* **Hardware Evidence Status**: **GREEN** within bench prototype scope.

---

### 3. Strict Truthfulness on DSSS Spreading

* **Claim Clarification**: The project does **NOT** run Direct Sequence Spread Spectrum (DSSS) with Gold codes on the physical SX1278 silicon.
* The Semtech SX1278 transceiver operates native **Chirp Spread Spectrum (CSS)**.
* The DSSS architecture described in documentation is an **architectural simulation model** evaluating future custom SDR baseband implementations for dense open-pit multipath environments.
* **Evidence Classification**: **YELLOW (SIMULATION MODEL)**.

---

### 4. Severe Packet Loss Resilience (99% Drop Test)

* Under simulated extreme RF interference or deep rock shadow where packet loss reached **$99\%$**:
  - Central fleet orchestration commands ceased to arrive.
  - V2V inter-vehicle state updates dropped.
* **System Behavior**:
  - Central optimizer gracefully stalled dispatch updates.
  - **Tier-1 Local Safety Governor remained 100% operational** on the vehicle's internal sensors.
  - Trucks autonomously regulated their own speed to $v_{\text{safe}}$ based on local optical sensors.
* **Canonical Statement**:
  > **"At 99% packet loss, communication is severely degraded; however, the local vehicle safety invariant remains preserved because safety governing operates autonomously onboard."**
