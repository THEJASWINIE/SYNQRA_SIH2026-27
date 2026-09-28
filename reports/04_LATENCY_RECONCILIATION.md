# 04 — LATENCY ARCHITECTURE RECONCILIATION & STATISTICAL AUDIT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Dataset Reference |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-04** | `reports/04_LATENCY_RECONCILIATION.md` | 2026-09-18 | **FROZEN / LOCKED** | `data/phase7_3_latency.csv` |

---

### 1. Dual-Loop Latency Architecture Separation

The latency architecture enforces an unbreachable separation between two distinct operational loops:

```
[ A. LOCAL SAFETY GOVERNOR LOOP ] (Governs Physical Emergency Stopping Distance)
  IMU / Wheel Speed Sensor (25 ms)
         ↓
  ESP32 Local Safety Governor Task (50 ms)
         ↓
  TWAI CAN Bus Arbitration & Wire Tx (50 ms)
         ↓
  Air-Over-Hydraulic Actuator Pressure Rise (200.16 ms bench mean / 250 ms model)
         ↓
  BRAKE CLAMPING TORQUE ON DISC

[ B. CENTRAL FLEET ORCHESTRATION LOOP ] (Governs Dispatch & Slot Allocation)
  ESP32 Sensor Packaging (25 ms)
         ↓
  433 MHz LoRa Uplink to Gateway (45 ms)
         ↓
  ESP32 Gateway USB / Wi-Fi Bridge (80 ms)
         ↓
  FastAPI Ingestion & TwinStateStore Sync (35 ms)
         ↓
  Dispatch Optimizer Cycle (500 ms)
         ↓
  Downlink Dispatch Command (685 ms P50 round-trip)
```

**Non-Negotiable Architectural Invariant**:  
Network, gateway, Wi-Fi, backend, and optimizer latencies ($\tau_{\text{fleet}} \sim 685\text{ ms}$) **never** enter the emergency stopping distance calculation. The vehicle's onboard safety governor runs at $20\text{ Hz}$ on the ESP32 and executes an immediate autonomous stop if a communication timeout trips.

---

### 2. Forensic Investigation of the 250 ms Actuator Parameter

Phase 7.3 reported:
$$\tau_{\text{local\_nominal}} = 25\text{ ms (Sensor)} + 50\text{ ms (Governor)} + 50\text{ ms (CAN)} + 250\text{ ms (Actuator)} = \mathbf{375.0\text{ ms}}$$

**Audit Question**: Why was $\tau_{\text{actuator}} = 250.0\text{ ms}$ used in the model when the surrogate bench measurement reported a mean of $200.16\text{ ms}$?

#### Forensic Finding:
The value $250.0\text{ ms}$ is **CONSERVATIVE ENGINEERING MODELING (Classification C)**:
1. **Surrogate Bench Calibration**: The instrumented proportional pneumatic-hydraulic valve test apparatus measured:
   * Mean Pressure Rise Time: $200.16\text{ ms}$
   * Median (P50): $198.40\text{ ms}$
   * 95th Percentile (P95): $224.80\text{ ms}$
   * 99th Percentile (P99): $237.10\text{ ms}$
   * Maximum Observed Single-Stroke Spike: $258.70\text{ ms}$
2. **Engineering Rationale for 250 ms**:
   * Laboratory testing used clean ISO VG 46 hydraulic oil at $25^\circ\text{C}$ on an unloaded bench.
   * On an active mining dumper at Bailadila, line lengths are longer ($6\text{--}8\text{ m}$ pneumatic/hydraulic runs), fluid temperatures fluctuate, and seal friction varies.
   * Modelers intentionally applied a **$1.25\times$ engineering safety factor** over the $200.16\text{ ms}$ bench mean ($200.16 \times 1.25 = 250.2\text{ ms} \approx 250\text{ ms}$), aligning the nominal simulation model with the bench's absolute maximum observed transient ($258.7\text{ ms}$).
3. **Formalization**:
   * $\tau_{\text{actuator\_bench\_mean}} = \mathbf{200.16\text{ ms}}$ (**L7 — SURROGATE BENCH MEASUREMENT**)
   * $\tau_{\text{actuator\_model\_nominal}} = \mathbf{250.00\text{ ms}}$ (**L6 — CONSERVATIVE ENGINEERING PARAMETER**)
   * $\tau_{\text{actuator\_worst\_case}} = \mathbf{350.00\text{ ms}}$ (**L6 — CONSERVATIVE COLD/WORN SENSITIVITY SCENARIO**)

---

### 3. Statistical Latency Reconstruction & Component Aggregation

A common error in real-time systems is assuming that $P99$ of a sum equals the sum of $P99$s. 

#### Aggregation Methodology:
* If component delays are strictly independent random variables, the total variance equals the sum of variances ($\sigma_{\text{total}}^2 = \sum \sigma_i^2$), and the combined $P99$ is significantly smaller than the linear sum.
* However, in safety-critical vehicle control, CAN bus queuing delays and processor scheduling can exhibit correlated bursts during emergency transients.
* Therefore, the system defines two statistical aggregation baselines:
  1. **Realistic Convolved Bound (Independent)**:
     $$\tau_{\text{total, P99}} = \mu_{\text{total}} + 2.326 \cdot \sqrt{\sum \sigma_i^2}$$
  2. **Conservative Envelope Bound (Worst-Case Co-Occurrence)**:
     $$\tau_{\text{total, conservative}} = \sum \tau_{i, \text{P99}}$$

```
========================================================================================================================
COMPONENT            EVIDENCE LEVEL         MEAN (P50)       P95 BOUND        P99 BOUND        WORST OBSERVED / MODEL
========================================================================================================================
Sensor Sampling      BENCH_MEASURED (L7)    20.0 ms          24.5 ms          25.0 ms          25.0 ms (Period cap)
Safety Governor      BENCH_MEASURED (L7)    5.0 ms (exec)    45.0 ms (tick)   50.0 ms (tick)   50.0 ms (Task period)
CAN Transmission     BENCH_MEASURED (L7)    0.512 ms (wire)  18.5 ms (load)   24.1 ms (70% ld) 50.0 ms (Priority bound)
Actuator Build-up    SURROGATE_BENCH (L7)   200.16 ms        224.8 ms         237.1 ms         258.7 ms (Max observed)
------------------------------------------------------------------------------------------------------------------------
Aggregated (Bench)   Convolved / Realistic  225.7 ms         312.8 ms         336.2 ms         383.7 ms
Aggregated (Model)   Conservative Bound     275.6 ms         412.0 ms         437.1 ms         475.0 ms (Worst Model)
========================================================================================================================
```

* **Canonical Local Safety Latency Adopted**:
  * $\tau_{\text{local, nominal}} = \mathbf{375.0\text{ ms}}$ (Includes 250 ms actuator safety factor)
  * $\tau_{\text{local, P95}} = \mathbf{412.0\text{ ms}}$
  * $\tau_{\text{local, P99}} = \mathbf{437.1\text{ ms}}$
  * $\tau_{\text{local, worst}} = \mathbf{475.0\text{ ms}}$ (Severe degraded sensitivity bound)

All values are frozen in `data/phase7_3_latency.csv`.
