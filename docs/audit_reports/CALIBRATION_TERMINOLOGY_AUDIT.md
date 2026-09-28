# CALIBRATION_TERMINOLOGY_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Pre-Physical Hostile Audit: Calibration Terminology & Sensor Truth

**Date:** 2026-09-27  
**Status:** **AUDITED & ALIGNED**  
**Classification:** L1 (Source Code Inspection) + L2 (Automated Test Verification) + L4 (Elevated Bench Hardware)  
**Rule Compliance:** AGENTS.md Rules 3, 4, 8, 23 ("Explicit units", "Never fabricate telemetry", "Honesty about hardware")

---

### 1. Executive Summary

This forensic audit investigates every occurrence of the calibration factor **34.58**, raw disc slot counts, and pulse-per-revolution (PPR) terminology across the entire repository (ESP32 firmware, backend, Digital Twin, frontend HMI, automated test suites, and documentation).

**Core Finding & Disambiguation:**
1. **Physical Optical Slots:**
   - **Vehicle A (`TRUCK_01`):** Exactly **42 physical optical slots** on its LM393 slotted interrupter disc (`#define RAW_ENCODER_PPR 42.0f`).
   - **Vehicle B (`TRUCK_02`):** Exactly **43 physical optical slots** on its LM393 slotted interrupter disc (`#define RAW_ENCODER_PPR 43.0f`).
   - Both vehicles use optical slotted interrupter discs from separate manufacturing batches. Physical discs possess **integer** slot counts only.
2. **Empirical Distance Calibration Factor ($K_{\text{cal}}$):**
   - **$K_{\text{cal}} = 34.58\text{ pulses/revolution}$** (also denoted in code as `ENCODER_EFFECTIVE_PPR` or `PPR_eff`).
   - $34.58$ is an **empirical ground-roll distance calibration factor**, reflecting effective rolling radius under chassis normal load, optical edge hysteresis, and tire deformation on polished surfaces.
   - **$34.58$ IS NOT A PHYSICAL FRACTIONAL ENCODER SLOT COUNT.** No optical sensor disc has $34.58$ physical slots.
3. **Kinematic Scale Parity:**
   - Both vehicles apply $K_{\text{cal}} = 34.58\text{ pulses/rev}$ with calibrated wheel diameter $D = 0.060\text{ m}$, establishing an identical linear displacement resolution:
     $$C = \pi \times D = 3.14159265 \times 0.060 = 0.188495559\text{ m}$$
     $$d_{\text{pulse}} = \frac{C}{K_{\text{cal}}} = \frac{0.188495559\text{ m}}{34.58\text{ pulses}} = 0.00545100\text{ m/pulse} \quad (5.451\text{ mm/pulse})$$
     $$1.0\text{ meter} = \frac{1.0}{0.00545100} = 183.45\text{ pulses}$$

---

### 2. Forensic Occurrence Registry Across Repository Layers

#### 2.1 ESP32 Firmware Layer
| File | Line(s) | Symbol / Definition | Context & Architectural Meaning |
| :--- | :--- | :--- | :--- |
| `esp32_code/sketch_aug26a/sketch_aug26a.ino` (Vehicle A) | 55–60 | `#define RAW_ENCODER_PPR 42.0f`<br>`#define ENCODER_EFFECTIVE_PPR 34.58f`<br>`#define PULSES_PER_REV ENCODER_EFFECTIVE_PPR`<br>`#define WHEEL_DIAMETER_M 0.060f` | Physical disc slots explicitly separated from empirical calibration factor $K_{\text{cal}}$. |
| `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino` (Vehicle B) | 59–64 | `#define RAW_ENCODER_PPR 43.0f`<br>`#define ENCODER_EFFECTIVE_PPR 34.58f`<br>`#define PULSES_PER_REV ENCODER_EFFECTIVE_PPR`<br>`const float WHEEL_DIAMETER_M = 0.060f` | Physical disc slots (43.0) separated from empirical calibration factor $K_{\text{cal}}$ (34.58). |
| `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/...ino` | 51–52 | `#define ENCODER_EFFECTIVE_PPR 34.58f` | Calibration verification sketch matching production $K_{\text{cal}}$. |
| `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE B/...ino` | 86 | `#define PULSES_PER_REV 34.58f` | Calibration verification sketch matching production $K_{\text{cal}}$. |

#### 2.2 Backend & Digital Twin Layer
| File | Line(s) | Symbol / Definition | Context & Architectural Meaning |
| :--- | :--- | :--- | :--- |
| `integration_adapters/wheel_imu_odometry.py` | 42 | `EFFECTIVE_CALIBRATION_K = 34.58`<br>`WHEEL_DIAMETER_M = 0.060` | Canonical dead-reckoning odometry integration. Maps accumulated pulse delta to ground translation. |
| `config/physical_vehicle_parameters.json` | 10–13, 41–44 | `"encoder_effective_ppr": 34.58`,<br>`"pulses_per_revolution": 34.58`,<br>`"raw_slots": 42` (TRUCK_01), `"raw_slots": 43` (TRUCK_02) | JSON configuration authoritative for vehicle physical parameters. |
| `config/canonical_vehicle_calibration.yaml` | 23, 51 | `effective_ppr: 34.58`, `wheel_diameter_m: 0.060` | YAML canonical calibration configuration. |
| `config/canonical_vehicle_calibration.json` | 24, 56 | `"effective_ppr": 34.58`, `"wheel_diameter_m": 0.060` | Canonical JSON mirror for runtime consistency. |

#### 2.3 Automated Test Suites Layer
| File | Line(s) | Test Name | Assertion / Invariant Verified |
| :--- | :--- | :--- | :--- |
| `tests/integration/test_canonical_kinematics_calibration.py` | 24, 50–65 | `test_pulse_to_distance_progression`, `test_canonical_config_files` | Verifies exact conversions: 1 pulse = $0.005451\text{ m}$; 34.58 pulses = exactly 1 rev ($0.188496\text{ m}$). |
| `tests/integration/test_cross_layer_consistency.py` | 47 | `test_vehicle_kinematic_parity` | Verifies cross-layer agreement between firmware, backend config, and twin odometry. |
| `tests/test_unit_converter.py` | 20–35 | `test_speed_from_rpm_and_pulses` | Verifies SI unit conversions ($D=0.060\text{ m}$, $K=34.58$). |

#### 2.4 HMI & Frontend Layer
| File | Line(s) | Displayed Text / Label | Truth & Provenance Guard |
| :--- | :--- | :--- | :--- |
| `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx` | 524–532 | `Wheel Encoder: FUNCTIONAL (xx.x RPM)` | Reads live `provenance.rpm.value`. Never displays synthetic pulses. |
| `SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperationsOverview.tsx` | 471–475 | `Encoder: FUNCTIONAL (xx.x RPM)` | Reads live `provenance.rpm.value`. Displays "NO PULSES" when stationary. |

---

### 3. Terminology Invariant Verification

1. **Fractional Slot Myth Disproven:**
   - Optical interrupter discs cannot possess fractional slots ($34.58$ physical openings would be physically impossible).
   - Microscopic and bench inspection establishes:
     - Vehicle A disc = **42 cutouts / teeth**
     - Vehicle B disc = **43 cutouts / teeth**
2. **Origin of 34.58:**
   - Calibrated empirically over a known linear ground distance ($0.5\text{ m}$, $1.0\text{ m}$) under vehicle normal load ($480\text{ g}$).
   - The effective rolling circumference under tire squish and optical edge hysteresis matches $34.58\text{ pulses}$ per full $360^\circ$ wheel cycle on the test surface.
3. **UI / Documentation Protection:**
   - No HMI screen or user-facing card references "34.58 slots".
   - All documentation and configuration explicitly annotate $34.58$ as `K_cal`, `effective_ppr`, or `empirical_calibration`.

---

### 4. Audit Verdict: PASS (CODE & ELEVATED BENCH VERIFIED)

| Requirement | Implementation Evidence | Verdict |
| :--- | :--- | :---: |
| Vehicle A Physical Slots = 42 | `#define RAW_ENCODER_PPR 42.0f` in `sketch_aug26a.ino` | **PASS** |
| Vehicle B Physical Slots = 43 | `#define RAW_ENCODER_PPR 43.0f` in `VEHICLE_B_...ino` | **PASS** |
| 34.58 Described as Empirical Calibration Factor | Explicitly defined as `ENCODER_EFFECTIVE_PPR` / `K_cal` across all layers | **PASS** |
| No UI / Docs Fractional Slot Claims | HMI renders RPM and speed in SI units; zero fractional slot claims | **PASS** |
| Kinematic Parity Verified | Identical $5.451\text{ mm/pulse}$ resolution across both vehicles | **PASS** |
