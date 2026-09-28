# 13_CONFIGURATION_CONSISTENCY.md
## FOG-ORCHESTRATOR 2.0 — Cross-Layer Parameter & Calibration Consistency Audit
**Date / Timestamp:** 2026-09-27T09:43:00+05:30  
**Evaluator Role:** Senior Systems Architect, Embedded Systems Engineer  
**Absolute Principle:** NO FABRICATION — Full Repository Parameter Extraction

---

### 1. CANONICAL PARAMETER VERIFICATION

The codebase was searched comprehensively across firmware sketches, backend configuration, frontend components, Digital Twin modules, and unit test suites to determine parameter consistency:

| Parameter | Nominal Specification | Firmware A | Firmware B | Backend | Frontends (HMIs) | Digital Twin | Status / Reconciliation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Wheel Diameter ($D$)** | `0.060 m` (60 mm) | `0.060f` | `0.060f` | `0.060` | Consumes backend $m/s$ | `0.060` | **CONSISTENT** |
| **Raw Encoder PPR A** | `42.0` | `42.0f` | N/A | `42.0` | N/A | `42.0` | **CONSISTENT** |
| **Raw Encoder PPR B** | `43.0` | N/A | `43.0f` | `43.0` | N/A | `43.0` | **CONSISTENT** |
| **Effective Calibration ($K$)** | `34.58` | `34.58f` | `34.58f` | `34.58` | N/A | `34.58` | **CONSISTENT (PROD)**; Divergent in calibration sketches |
| **RF Airtime Component** | `38.5 ms` | Assumed | Assumed | $38.5\text{ ms}$ budget | N/A | $38.5\text{ ms}$ | **CONFIGURED ONLY** |
| **Stale Threshold** | `3.0 s` | N/A | N/A | `3.0 s` | `3.0 s` | `3.0 s` | **CONSISTENT** |
| **Offline Threshold** | `10.0 s` | N/A | N/A | `10.0 s` | `10.0 s` | `10.0 s` | **CONSISTENT** |
| **Command Timeout** | `15.0 s` | N/A | `15000 ms` | `15.0 s` | N/A | `15.0 s` | **CONSISTENT** |
| **Max Safe Speed** | `1.40 m/s` | N/A | `1.40f` | `1.40` | `1.40` | `1.40` | **CONSISTENT** |
| **Default Cruise Speed** | `0.50 m/s` | N/A | `0.50f` | `0.50` | `0.50` | `0.50` | **CONSISTENT** |

---

### 2. FORENSIC DISCREPANCIES IDENTIFIED

#### [DISCREPANCY CFG-001] Standalone Speed Calibration Sketches Omit $K=34.58$
- **Files:**
  - `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/VEHICLE_SPEED_CALIBRATION/VEHICLE_SPEED_CALIBRATION.ino`
  - `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE B/sketch_sep17a_copy_20260917203801/...`
- **Finding:** Both standalone calibration sketches compute speed using:
  ```cpp
  #define PULSES_PER_REV 42.0f // (or 43.0f for Vehicle B)
  ```
  Neither sketch includes `ENCODER_EFFECTIVE_PPR 34.58f`.
- **Impact:** An engineer running the standalone calibration test will observe a calculated speed that is $17.67\%$ (Vehicle A) or $19.58\%$ (Vehicle B) **lower** than what the live production firmware reports for the exact same physical pulse frequency.
- **Required Fix:** Update both calibration sketches to define:
  ```cpp
  #define ENCODER_EFFECTIVE_PPR 34.58f
  #define PULSES_PER_REV ENCODER_EFFECTIVE_PPR
  ```

#### [DISCREPANCY CFG-002] Misattribution of 38.5 ms RF Airtime as End-to-End Latency
- **Finding:** Several past reports and documentation strings referred to $38.5\text{ ms}$ as the "end-to-end latency".
- **Physical Reality:** $38.5\text{ ms}$ is solely the **RF PHY packet airtime component** ($T_4$) calculated from LoRa spreading factor $\text{SF}=7$, bandwidth $\text{BW}=125\text{ kHz}$, coding rate $4/5$, and payload length $32\text{ bytes}$.
- **Complete Budget:** Total reaction latency includes sensor acquisition ($10\text{ ms}$), ESP32 processing ($5\text{ ms}$), RF airtime ($38.5\text{ ms}$), Gateway forwarding ($15\text{ ms}$), Backend ingestion ($5\text{ ms}$), Safety Governor evaluation ($2\text{ ms}$), Command downlink ($38.5\text{ ms}$), and Motor driver ramp ($10\text{ ms}$), totaling approximately $124.0\text{ ms}$.
- **Status:** Correctly classified as **CONFIGURED / PARTIAL**; never claim $38.5\text{ ms}$ is total system latency.
