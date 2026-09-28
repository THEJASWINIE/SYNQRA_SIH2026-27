# 02 — PARAMETER RECONCILIATION & AUDIT REPORT
*(Fulfills `PARAMETER_RECONCILIATION_TABLE.md` Requirement)*

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Canonical Parameter Reconciliation & Traceability Matrix  
**Date of Audit:** 2026-09-18  

---

## 1. Parameter Reconciliation Rule

Parameters in FOG-ORCHESTRATOR 2.0 are governed by a strict hierarchy:
1. **L1 / L2 / L4 (Standards & OEM Documentation):** Overrides all assumptions.
2. **L7 / L8 (Physical & Bench Measurements):** Calibrates dynamics and delays.
3. **L6 (Engineering Assumptions / Scenarios):** Maintained only where physical measurement is pending; must be explicitly labeled.
4. **L10 (Untraceable / Unsupported):** Permanently **REMOVED**.

---

## 2. Comprehensive Reconciliation Table

| Parameter Name | Old Value | Reconciled Value | Unit | Action | Evidence Level | Primary Source & Experiment Reference | Reason for Action |
|:---|:---:|:---:|:---:|:---:|:---:|:---|:---|
| `mass_loaded_kg` | 165,500.0 | **165,500.0** | kg | **KEEP** | L2 | BEML BH100 Technical Specification Sheet | Official Gross Operating Weight (GVW) under rated payload. |
| `mass_empty_kg` | 74,000.0 | **74,000.0** | kg | **KEEP** | L2 | BEML BH100 Technical Specification Sheet | Certified unladen tare mass with standard chassis and ROPS cab. |
| `payload_rated_kg` | 91,500.0 | **91,500.0** | kg | **KEEP** | L2 | BEML BH100 Technical Brochure (100 short tons) | Nominal iron ore payload capacity. |
| `tau_sensor_s` | 0.100 | **0.100** | s | **KEEP** | L6 | 10 Hz Radar / Perception Filter Window | Conservative upper bound on obstacle & visibility estimation refresh. |
| `tau_decision_s` | 0.050 | **0.050** | s | **KEEP** | L7 | 20 Hz Onboard Governor Task on ESP32/ECU | Bench measured execution loop (< 5 ms execution + 50 ms task period). |
| `tau_CAN_s` | 0.050 (Assumed) | **0.025 (Nom) / 0.050 (Bound)** | s | **UPDATE** | L7 | ESP32 TWAI J1939 Bench ([`phase7_2_e1`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/reports/phase7_2_e1_can_validation.md)) | Frame wire time is 0.512 ms; P99 at 70% load is 24.1 ms; 50 ms confirmed as conservative bound. |
| `tau_actuator_s` | 0.200 (Assumed) | **0.20016 (Mean)** | s | **UPDATE** | L7_Surrogate | Surrogate Pneumatic-Hydraulic Bench ([`phase7_2_e2`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/reports/phase7_2_e2_actuator_validation.md)) | Calibrated: Pilot 25ms + Air fill 60ms + Hydraulic rise 85ms + Clamp 30ms = 200.2 ms mean (P99: 237.1 ms). |
| `tau_actuator_worst_case_s`| 0.350 | **0.350** | s | **KEEP** | L6_Scenario | Degraded cold-oil/worn-pad sensitivity model | Maintained as conservative engineering scenario. Removed false "ISO limit" label. |
| `actuator_delay_260ms` | 0.260 | **REMOVED** | s | **REMOVE** | L10 | Untraceable legacy claim | Not found in any OEM documentation or test standard. Expunged. |
| `tau_local_safety_nom_s` | 0.450 | **0.375** | s | **UPDATE** | L6/L7 Synthesized| Sum: $\tau_{\text{sensor}}(100) + \tau_{\text{dec}}(50) + \tau_{\text{CAN}}(25) + \tau_{\text{act}}(200)$ | Recomputed local autonomous reaction budget without gateway hops. |
| `tau_fleet_command_total_s`| 0.530 | **0.685** | s | **UPDATE** | L7 Synthesized | Sum of LoRa uplink, Wi-Fi, backend, optimizer, LoRa downlink | Formally separated from local stopping path. |
| `crusher_service_tph` | 1,647.0 | **1,647.0** | TPH | **KEEP** | L3/L4 Physical | 200 s dump cycle at single gyratory crusher (18 VPH $\times$ 91.5 t) | Certified physical mine bottleneck capacity ceiling. |
| `historical_3294_tph` | 3,294.0 | **REMOVED (from steady state)** | TPH | **REMOVE** | L9_Artifact | 6-truck initial queue flush in 10 minutes | Dissected as transient discharge artifact. Cannot be sustained continuously. |
| `v_safe_dense_fog_mps` | Unspecified | **0.00** | m/s | **UPDATE** | L6/L1 Formulated| Strict physical cutoff for visibility $\le 5.0\text{ m}$ | Prevents vehicle motion when sight distance is less than vehicle length + margin. |
| `v_safe_canonical_12m_mps` | 4.3815 | **5.256 (Nom) / 4.3815 (Buffered)**| m/s | **UPDATE** | L6 Derived | Inversion of quadratic stopping equation on $-8\%$ grade | Reconciled: 5.256 m/s is pure autonomous; 4.3815 m/s retains legacy 0.50 s human buffer. |
| `max_ramp_grade_pct` | 8.0 | **8.0 (Civil $-8\%$ Downhill)** | % | **UPDATE** | L4 Standard | DGMS Circular 09/2008 & `GradeAdapter` | Explicitly unified under civil sign convention ($-8\%$ downhill, $+8\%$ uphill). |
