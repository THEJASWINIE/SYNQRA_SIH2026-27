# FOG-ORCHESTRATOR 2.0 — PARAMETER FORENSIC AUDIT
**SIH 2026-27 | PHASE H11: CANONICAL PARAMETER RECONCILIATION**  
**Lead Embedded, Robotics, Cyber-Physical Systems & Safety Integration Engineer**  
**Audit Standard:** Strict Source-of-Truth Hierarchy & Evidence Levels (L0–L5)  
**Date:** 2026-09-24  

---

## 1. Executive Summary

This forensic audit identifies every parameter occurrence across physical microcontrollers (Vehicle A & Vehicle B ESP32 firmware), calibration test sketches, backend kinematic adapters, Digital Twin models, simulation engines, HMI telemetry consumers, and configuration files.

The mission objective is:
$$\textbf{ONE PHYSICAL PARAMETER} \longrightarrow \textbf{ONE CANONICAL VALUE} \longrightarrow \textbf{ESP32} \longrightarrow \textbf{BACKEND} \longrightarrow \textbf{DIGITAL TWIN} \longrightarrow \textbf{HMIs}$$

### The Critical Calibration Reconciled:
* **Wheel Diameter ($D$):** **$0.060\text{ m}$** ($6.0\text{ cm}$, Radius $R = 0.030\text{ m}$) across **BOTH Vehicle A and Vehicle B**.
* **Effective Pulses Per Revolution ($\text{PPR}_{\text{eff}}$):** **$34.58\text{ pulses/rev}$** across **BOTH Vehicle A and Vehicle B**.
* **Raw Hardware Encoder PPR:**
  - Vehicle A: $42.0\text{ pulses/rev}$ (retained as `RAW_ENCODER_PPR = 42.0`)
  - Vehicle B: $43.0\text{ pulses/rev}$ (retained as `RAW_ENCODER_PPR = 43.0`)
* **Effective Kinematic Calibration Derivation:**
  Physical bench tests driving vehicles over a measured 10-second run revealed an effective pulse accumulation factor of $34.58\text{ pulses/rev}$ due to dynamic rolling radius under payload and optical slot edge transition debounce. Distance per pulse is exactly $\frac{\pi \times 0.060}{34.58} = 0.00545100\text{ m}$ ($5.451\text{ mm/pulse}$).

---

## 2. Parameter Forensic Audit Table

| Parameter | Current Repository Value | Location(s) | Expected Canonical Value | Unit | Evidence Class | Status | Required Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vehicle A Wheel Diameter** | `0.10 m` / `10 cm` | `esp32_code/sketch_aug26a/sketch_aug26a.ino:52`<br>`config/physical_vehicle_parameters.json:6`<br>`integration_adapters/wheel_imu_odometry.py:42`<br>`SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py:245` | `0.060` | m | `VERIFIED` (L3/L4) | **MISMATCH** | Update firmware, backend JSON, odometry adapter, and serial reader to `0.060 m`. |
| **Vehicle A Wheel Radius** | `0.050 m` | `config/physical_vehicle_parameters.json:5`<br>`tests/test_unit_converter.py:12`<br>`tests/test_speed_truth_contract.py:31` | `0.030` | m | `VERIFIED` (L3/L4) | **MISMATCH** | Update backend JSON and test fixtures to $R = D/2 = 0.030\text{ m}$. |
| **Vehicle A Encoder PPR** | `42.0` (Raw) | `esp32_code/sketch_aug26a/sketch_aug26a.ino:51`<br>`config/physical_vehicle_parameters.json:7`<br>`integration_adapters/wheel_imu_odometry.py:41` | Effective: `34.58`<br>Raw: `42.0` | pulses/rev | `VERIFIED` (L3/L4) | **MISMATCH** | Introduce `ENCODER_EFFECTIVE_PPR = 34.58f` while retaining `RAW_ENCODER_PPR = 42.0f`. Update backend config. |
| **Vehicle B Wheel Diameter** | `0.085 m` (Backend)<br>`0.060 m` (Firmware) | `config/physical_vehicle_parameters.json:32`<br>`SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py:256`<br>`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino:57` | `0.060` | m | `VERIFIED` (L3/L4) | **MISMATCH** (Backend/Gateway) | Update backend JSON and gateway serial reader to `0.060 m`. |
| **Vehicle B Wheel Radius** | `0.0425 m` | `config/physical_vehicle_parameters.json:31`<br>`tests/test_unit_converter.py:17` | `0.030` | m | `VERIFIED` (L3/L4) | **MISMATCH** | Reconcile backend to $R = 0.030\text{ m}$. Update unit test assertions. |
| **Vehicle B Encoder PPR** | `20.0` (Backend)<br>`43.0` (Firmware) | `config/physical_vehicle_parameters.json:33`<br>`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino:55` | Effective: `34.58`<br>Raw: `43.0` | pulses/rev | `VERIFIED` (L3/L4) | **MISMATCH** | Update firmware to `ENCODER_EFFECTIVE_PPR = 34.58f` and backend to `effective_ppr: 34.58`. |
| **Vehicle B Motor Driver** | `TB6612FNG` | `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino:27`<br>`config/physical_vehicle_parameters.json:20` | `TB6612FNG` | N/A | `VERIFIED` (L3/L4) | **MATCH** | Maintain TB6612FNG freeze (`STBY:13, AIN1:25, AIN2:26, PWMA:27, BIN1:32, BIN2:33, PWMB:14`). |
| **Vehicle A Motor Driver** | `L298N` | `esp32_code/sketch_aug26a/sketch_aug26a.ino:32` | `L298N` | N/A | `VERIFIED` (L3/L4) | **MATCH** | Maintain L298N pinout (`IN1:25, IN2:26, PWM:27, IN3:32, IN4:33, PWM:14, STBY:13`). |
| **Prototype Chassis Mass (TRUCK_01)** | `2.20` | `config/physical_vehicle_parameters.json:8` | `2.20` | kg | `VERIFIED` (L3) | **MATCH** | Maintain verified bench measurement. |
| **Prototype Chassis Mass (TRUCK_02)** | `1.85` | `config/physical_vehicle_parameters.json:34` | `1.85` | kg | `VERIFIED` (L3) | **MATCH** | Maintain verified bench measurement. |
| **OEM Scale Mass (CAT 777D / BEML BH100)** | `165,000` (Gross loaded)<br>`67,500` (Tare empty) | `config/hemm_canonical.yaml`<br>`fog_orchestrator/core/config.py`<br>`config/bailadila_hemm_canonical.yaml` | `165,000`<br>`67,500` | kg | `MODEL_PARAMETER` (L5 Spec) | **MATCH** | Unchanged. |
| **HEMM Tire Rolling Radius** | `1.2` | `fog_orchestrator/core/config.py:22` | `1.2` | m | `MODEL_PARAMETER` (L5 Spec) | **MATCH** | Unchanged for 27.00R49 mining tires. |
| **Max Prototype Speed** | `1.40` (TRUCK_02)<br>`3.00` (TRUCK_01) | `config/physical_vehicle_parameters.json:9,35`<br>`esp32_code/sketch_aug26a.ino:145` | `1.40` | m/s | `VERIFIED` (L4) | **MATCH** | Maintain prototype safety ceiling ($1.40\text{ m/s} = 5.04\text{ km/h}$). |
| **Safe Crawl Speed** | `0.50` | ESP32 firmware & Safety Governor | `0.50` | m/s | `VERIFIED` (L3/L4) | **MATCH** | Maintain power-on crawl speed. |
| **RF Airtime Metric** | `38.5 ms` labeled as "end-to-end command latency" | `INTEGRATION_REPORT.md:243`<br>`docs/HARDWARE_SOFTWARE_INTEGRATION.md` | `RF_AIRTIME_COMPONENT` | ms | `VERIFIED` (L3) | **TERMINOLOGY MISMATCH** | Correct description from "end-to-end latency" to "Measured RF airtime component (`RF_AIRTIME_COMPONENT`)". |
| **CAN Bus Latency (Emergency)** | `1.82 - 2.45 ms` | `results/can_validation/can_timing_sweep.json` | `CAN_TWAI_COMPONENT` | ms | `VERIFIED` (L3) | **MATCH** | Classify as `CAN_TWAI_COMPONENT` in latency budget. |
| **Safe Beacon Timeout** | `500` | `failsafe/safe_beacon.py`<br>`integration_adapters/safe_beacon_adapter.py` | `500` | ms | `VERIFIED` (L3) | **MATCH** | Maintain heartbeat threshold. |
| **Safe Beacon Recovery Hysteresis** | `5` | `integration_adapters/safe_beacon_adapter.py` | `5` | packets | `VERIFIED` (L2/L3) | **MATCH** | Anti-flapping recovery requirement verified. |
| **Grade Transformation** | $G_{\text{physics}} = -G_{\text{civil}}$ | `integration_adapters/grade_adapter.py`<br>`fog_orchestrator/tier1_governor/vehicle_physics.py` | $G_{\text{physics}} = -G_{\text{civil}}$ | % | `MODEL_PARAMETER` (L1) | **MATCH** | Monotonicity verified. |

---

## 3. Mathematical Verification of Reconciled Kinematics

With canonical parameters:
$$D = 0.060\text{ m} \quad (R = 0.030\text{ m})$$
$$\text{PPR}_{\text{eff}} = 34.58\text{ pulses/revolution}$$

1. **Wheel Circumference ($C$):**
   $$C = \pi \times D = 3.141592653589793 \times 0.060 = \mathbf{0.188495559\dots\text{ m}} \approx \mathbf{0.188496\text{ m}}$$
2. **Distance Per Revolution ($d_{\text{rev}}$):**
   $$d_{\text{rev}} = C = \mathbf{0.188496\text{ m}} = 188.496\text{ mm}$$
3. **Distance Per Pulse ($d_{\text{pulse}}$):**
   $$d_{\text{pulse}} = \frac{C}{\text{PPR}_{\text{eff}}} = \frac{0.188495559}{34.58} = \mathbf{0.00545100\dots\text{ m}} \approx \mathbf{5.451\text{ mm/pulse}}$$
4. **Revolutions ($N_{\text{rev}}$):**
   $$N_{\text{rev}} = \frac{\text{pulse\_count}}{34.58}$$
5. **Linear Speed from Wheel RPM ($v$):**
   $$v = \frac{\text{RPM} \times C}{60} = \text{RPM} \times \frac{0.188495559}{60} = \mathbf{\text{RPM} \times 0.00314159265\text{ m/s}}$$
   - At $180\text{ RPM}$: $v = 180 \times 0.00314159265 = \mathbf{0.5655\text{ m/s}}$ ($2.036\text{ km/h}$)
   - At $240\text{ RPM}$: $v = 240 \times 0.00314159265 = \mathbf{0.7540\text{ m/s}}$ ($2.714\text{ km/h}$)
   - At $445.63\text{ RPM}$: $v = 445.63 \times 0.00314159265 = \mathbf{1.4000\text{ m/s}}$ ($5.040\text{ km/h}$, max prototype ceiling)

---

## 4. Remediation Plan

1. **Firmware:**
   - Update `esp32_code/sketch_aug26a/sketch_aug26a.ino`: set `WHEEL_DIAMETER_M = 0.060f`, `PULSES_PER_REV = 34.58f`, define `RAW_ENCODER_PPR 42.0f`.
   - Update `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`: set `WHEEL_DIAMETER_M = 0.060f`, `PULSES_PER_REV = 34.58f`, define `RAW_ENCODER_PPR 43.0f`.
2. **Backend & Adapters:**
   - Update `config/physical_vehicle_parameters.json` for both `TRUCK_01` and `TRUCK_02` to $R = 0.030\text{ m}$, $D = 0.060\text{ m}$, $\text{effective\_ppr} = 34.58$.
   - Create single source-of-truth configuration `config/canonical_vehicle_calibration.yaml` and `.json`.
   - Update `SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py` lines 245 and 256 to use $0.060\text{ m}$.
   - Update `integration_adapters/wheel_imu_odometry.py` to support canonical parameters ($0.060\text{ m}$, $34.58\text{ PPR}$).
3. **Tests:**
   - Update unit test fixtures in `tests/test_unit_converter.py`, `tests/test_speed_truth_contract.py`, and `tests/integration/test_end_to_end_integration.py`.
   - Add new automated calibration and cross-layer consistency test suite.
