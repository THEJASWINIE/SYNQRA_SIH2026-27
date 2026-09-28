# PHASE 7.3.2 — REPORT 17: FINAL PARAMETER RECONCILIATION & FREEZE
## Master Engineering Parameter Registry & Evidence Locking
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Final Canonical Parameter Registry

| Parameter Name | Historical / Old Value | Reconciled Canonical Value | SI Unit | Analytical Equation / Formulation | Evidence Level | Primary Source | Rationale for Update | Confidence | Final Status |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **`mass_empty_kg`** | 74,000.0 | **74,000.0** | $\text{kg}$ | Fixed chassis mass | OEM_REFERENCE | BEML BH100 Spec Sheet | Modern revision certified chassis weight | HIGH | **KEEP** |
| **`payload_rated_kg`** | 91,500.0 | **91,500.0** | $\text{kg}$ | Rated ore load | OEM_REFERENCE | BEML BH100 Datasheet | Official metric rating (91.5 tonnes) | HIGH | **KEEP** |
| **`mass_loaded_kg`** | 165,500.0 | **165,500.0** | $\text{kg}$ | $m = m_{\text{tare}} + m_{\text{load}}$ | OEM_REFERENCE | BEML Certified GVW | Full gross operating vehicle mass | HIGH | **KEEP** |
| **`length_m`** | 10.52 | **10.52** | $\text{m}$ | Overall length | OEM_REFERENCE | BEML GA Drawing | Bumper-to-canopy length | HIGH | **KEEP** |
| **`width_m`** | 5.52 | **5.52** | $\text{m}$ | Overall width | OEM_REFERENCE | BEML GA Drawing | Outside canopy operating width | HIGH | **KEEP** |
| **`wheelbase_m`** | 5.25 | **5.25** | $\text{m}$ | Wheelbase | OEM_REFERENCE | BEML GA Drawing | Front to rear tandem distance | HIGH | **KEEP** |
| **`hardware_brake_max_force_n`** | 550,000.0 | **550,000.0** | $\text{N}$ | Caliper force ceiling | STANDARD | ISO 3450:2011 | Air-over-hydraulic mechanical clamp limit | HIGH | **KEEP** |
| **`retarder_power_max_w`** | 1,200,000.0 | **1,200,000.0** | $\text{W}$ | Retarder curve | OEM_REFERENCE | Rear wet multi-disc | Continuous retarding thermal ceiling | HIGH | **KEEP** |
| **`a_dec_service`** | 1.20 | **1.2000** | $\text{m/s}^2$ | Operator comfort limit | ASSUMED | Haulage literature | Operational limit to prevent rock spillage | MEDIUM | **KEEP** |
| **`a_dec_emergency`** | 1.20 (misstated)| **2.7466** | $\text{m/s}^2$ | $a = [F_{\text{brk}} + F_{\text{roll}} - F_{\text{grd}}]/m$ | DERIVED_MODEL | Dynamics Force Balance | True net retarding on -8% ramp at 12m | HIGH | **UPDATE** |
| **`tau_sensor_s`** | 0.025 | **0.0250** | $\text{s}$ | Sensor window | ASSUMED | Perception model | 40 Hz transmissometer update delay | MEDIUM | **KEEP** |
| **`tau_decision_s`** | 0.050 | **0.0500** | $\text{s}$ | Safety loop execution | MEASURED | Benchmark profiling | 20 Hz fixed discrete safety governor loop | HIGH | **KEEP** |
| **`tau_can_s`** | 0.050 | **0.0500** | $\text{s}$ | CAN bus budget | ASSUMED | Conservative model | 5-10x higher than SAE J1939 benchmark | LOW | **KEEP** |
| **`tau_actuator_bench_mean_s`** | 0.20016 | **0.20016** | $\text{s}$ | Empirical mean | SURROGATE_BENCH | Hydraulic bench testbed | Measured mean on surrogate hydraulic bench | HIGH | **KEEP** |
| **`tau_actuator_model_s`** | 0.250 | **0.2500** | $\text{s}$ | Model parameter | ASSUMED | Engineering buffer | Incorporates BH100 pneumatic line fill lag | MEDIUM | **KEEP** |
| **`tau_local_nominal_s`** | 0.375 | **0.3750** | $\text{s}$ | $\sum \tau_{\text{nominal}}$ | DERIVED_MODEL | Sum of components | Nominal autonomous perception-to-brake | MEDIUM | **KEEP** |
| **`tau_local_p99_s`** | 0.4371 | **0.4371** | $\text{s}$ | Statistical P99 bound | DERIVED_MODEL | Component convolution | P99 conservative local safety loop budget | HIGH | **KEEP** |
| **`v_safe_12m_emergency_mps`** | 5.12 | **5.1158** | $\text{m/s}$ | Quadratic positive root | DERIVED_MODEL | Analytical solver | Solved with a=2.7466, tau=0.4371, 5m buffer | HIGH | **UPDATE** |
| **`v_safe_12m_service_mps`** | Unmodeled | **3.6078** | $\text{m/s}$ | Quadratic positive root | DERIVED_MODEL | Analytical solver | Solved with a=1.2000, tau=0.4371, 5m buffer | HIGH | **UPDATE** |
| **`stopping_distance_12m_m`** | 7.0 (with a=1.2) | **7.0004** | $\text{m}$ | $S = v\tau + v^2/(2a)$ | DERIVED_MODEL | Analytical kinematic | Corrected with true emergency a=2.7466 | HIGH | **UPDATE** |
| **`s_base_m`** | 5.0 | **5.0000** | $\text{m}$ | Standstill buffer | STANDARD | DGMS Regulation | Mandatory standoff margin | HIGH | **KEEP** |
| **`headway_safe_m`** | 17.52 (buffer-less)| **22.5200** | $\text{m}$ | $H = S_{\text{stop}} + S_{\text{base}} + L$ | DERIVED_MODEL | Geometry formulation | Corrected to include mandatory 5.0m buffer | HIGH | **UPDATE** |
| **`theoretical_road_flow_vph`** | 700.5 (legacy) | **817.8** | $\text{VPH}$ | $C = 3600 v / H_{\text{space}}$ | DERIVED_MODEL | Kinematic pipe flow | Evaluated at canonical v=5.1158, H=22.52 | HIGH | **UPDATE** |
| **`crusher_cycle_time_s`** | 200.0 | **200.0** | $\text{s}$ | Single pocket dump slot | STANDARD | Mine engineering standard | Gyratory crusher clearance cycle | HIGH | **KEEP** |
| **`crusher_capacity_tph`** | 1,647.0 | **1,647.0** | $\text{TPH}$ | $C = (3600/200) \times 91.5$ | DERIVED_MODEL | Physical Bottleneck Model| Hard upper ceiling on mine production | HIGH | **KEEP** |
| **`throughput_transient_tph`**| 3,294 / 2,745 | **RETRACTED** | $\text{TPH}$ | Short-burst surge rate | TRANSIENT_ARTIFACT | Finite horizon flush | Permanently retracted as sustained metric | HIGH | **REMOVE** |
| **`throughput_steady_state_tph`**| 1,591.4 | **1,591.4** | $\text{TPH}$ | Shift production rate | SIMULATION_BENCHMARK | Multi-window 2-hr sim | Sustained steady-state (96.6% utilization)| HIGH | **KEEP** |
| **`ramp_waiting_reduction_pct`**| 77.4% (total wait)| **77.36% (relocation)**| $\%$ | $(W_0 - W_1)/W_0$ | SIMULATION_BENCHMARK | Event log forensics | Clarified as ramp hazard relocation | HIGH | **UPDATE** |
| **`net_cycle_delay_reduction`**| Unreported | **-11.60% (-82.8s)** | $\%$ | Net trip delay delta | SIMULATION_BENCHMARK | Energy shockwave audit | Genuine delay reduction via shockwave cut | HIGH | **UPDATE** |
