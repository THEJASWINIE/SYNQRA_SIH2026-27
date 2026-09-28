# HEMM PARAMETER MIGRATION & PROVENANCE AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Target Machine Reference:** BEML BH100 100-Tonne Rear Dump Truck  
**Mine Site Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Chhattisgarh  
**Status:** COMPLETE MIGRATION CATALOGUE  
**Date:** 2026-09-18  

---

## 1. MIGRATION POLICY & INTEGRITY RULES

In accordance with PART 10 of the Phase Specification:
1. **No Blind Deletion:** Historical values and models in archived test suites or compatibility adapters are explicitly tracked rather than silently wiped.
2. **Traceability:** Every migrated parameter carries its old value, new canonical value, physical/engineering rationale, authoritative source, and list of files updated.
3. **Hierarchy of Truth:** Physical Evidence / OEM Specification > Derived Kinematic Model > Engineering Assumption > Simulation Output.

---

## 2. CANONICAL PARAMETER MIGRATION TABLE

| Parameter Identifier | Old Value | New Canonical Value | Engineering Rationale | Authoritative Source | Files Updated / Referenced |
|----------------------|-----------|---------------------|-----------------------|----------------------|----------------------------|
| `mass_loaded_kg` (GVW) | $165{,}000.0\text{ kg}$ | $165{,}500.0\text{ kg}$ | Accurate unladen tare ($74.0\text{ t}$) + rated payload ($91.5\text{ t}$) per OEM datasheet replaces rounded approximation. | BEML BH100 Specification Sheet | `config/bailadila_hemm_canonical.yaml`, `docs/STAGE2_PARAMETER_PROVENANCE.md` |
| `payload_rated_kg` | $91{,}000.0\text{ kg}$ | $91{,}500.0\text{ kg}$ | Correct nominal payload capacity for 100-tonne class ($91.5\text{ metric tonnes}$). | BEML BH100 Datasheet | `config/bailadila_hemm_canonical.yaml`, `fog_safe/config.py` |
| `mass_empty_kg` | $74{,}000.0\text{ kg}$ | $74{,}000.0\text{ kg}$ | Confirmed exact tare weight including ROPS/FOPS cabin and standard body. | BEML BH100 Datasheet | `config/bailadila_hemm_canonical.yaml` |
| `hardware_brake_max_force_n` | $600{,}000.0\text{ N}$ | $550{,}000.0\text{ N}$ | Certified service brake clamping limit under ISO 3450:2011 corresponds to $550\text{ kN}$ ($\sim 3.32\text{ m/s}^2$ fully laden). | ISO 3450:2011 / BEML Technical Data | `config/bailadila_hemm_canonical.yaml`, `fog_safe/config.py` |
| `max_retarder_power_w` | $1{,}200{,}000.0\text{ W}$ ($1.2\text{ MW}$) | $1{,}200{,}000.0\text{ W}$ ($1.2\text{ MW}$) | Continuous thermal absorption rating of oil-cooled rear disc retarder confirmed. | BEML BH100 Technical Specification | `config/bailadila_hemm_canonical.yaml`, `fog_safe/retarder.py` |
| `max_engine_power_kw` | $895.0\text{ kW}$ | $770.0\text{ kW}$ ($1{,}032\text{ HP}$) | OEM Cummins KTA38-C engine rating at $2{,}100\text{ rpm}$ is $770\text{ kW}$ ($1{,}032\text{ HP}$). $895\text{ kW}$ ($1{,}200\text{ HP}$) was QST30 optional rating. | Cummins KTA38-C Spec Sheet | `config/bailadila_hemm_canonical.yaml` |
| `drag_coefficient_cd` | $0.70$ | $0.80$ | Blunt, square cab and rock body geometry of heavy mining dumpers exhibits higher form drag ($C_d \approx 0.80$). | Mining Truck Aerodynamics Literature | `config/bailadila_hemm_canonical.yaml` |
| `frontal_area_m2` | $20.0\text{ m}^2$ | $22.0\text{ m}^2$ | Recomputed from actual dimensions ($W=5.52\text{ m}, H=5.25\text{ m}$) with $0.76$ frontal shape blockage factor. | BEML BH100 Geometric Envelope | `config/bailadila_hemm_canonical.yaml` |
| `rolling_resistance_crr` | $0.020$ | $0.025$ (Dry) / $0.035$ (Wet) | Unpaved compacted haul roads at Bailadila exhibit higher hysteresis and rutting than smooth asphalt ($0.020$). | SME Mining Engineering Handbook | `config/bailadila_hemm_canonical.yaml`, `experiments/generate_hemm_calibration.py` |
| `tau_sensor_s` | $0.100\text{ s}$ | $0.100\text{ s}$ | Perception filter window and visibility estimation update cycle. | Engineering Assumption | `config/bailadila_hemm_canonical.yaml` |
| `tau_comm_s` (aggregate) | $0.050\text{ s}$ / $0.100\text{ s}$ | $0.050\text{ s}$ (V2V) + $0.080\text{ s}$ (Gateway) | Phase 7 research decomposed aggregate communication into separate peer-to-peer V2V hop and gateway relay hop. | Phase 6 Bench Benchmarks | `config/bailadila_hemm_canonical.yaml`, `reports/phase7_deep_research_master.md` |
| `tau_decision_s` | $0.100\text{ s}$ | $0.050\text{ s}$ | Tier-1 Safety Governor runs at $20\text{ Hz}$ ($50\text{ ms}$ execution cycle; inner computation $<5\text{ ms}$). | Bench Profiling / Code Invariant | `config/bailadila_hemm_canonical.yaml` |
| `tau_actuator_s` | $0.200\text{ s}$ (Assumed) | $0.200\text{ s}$ Nominal / $0.350\text{ s}$ Worst-Case | Confirmed BEML BH100 utilizes air-over-hydraulic brakes. Literature establishes nominal $200\text{ ms}$, worst-case $350\text{ ms}$. | Experimental Literature on Air-Over-Hydraulic Actuators | `config/bailadila_hemm_canonical.yaml`, `reports/phase7_deep_research_master.md` |
| `tau_can_assumed_s` | $0.050\text{ s}$ (Assumed) | $0.050\text{ s}$ (Assumed Conservative) | J1939 CAN bus latency characterized on bench ($19.17\text{ ms}$ P95) and literature ($<10\text{ ms}$). Retained as $50\text{ ms}$ conservative assumption. | SAE J1939-11 Standard / Bench Logs | `config/bailadila_hemm_canonical.yaml`, `reports/phase6_can_latency_validation.md` |
| `tau_total_autonomous_s` | $0.250\text{ s}$ / $0.450\text{ s}$ | $0.450\text{ s}$ (Baseline) / $0.530\text{ s}$ (Decomposed) | Complete latency budget accounting for sensor, comm, governor, CAN bus, and actuator build-up. | Derived Synthesis | `config/bailadila_hemm_canonical.yaml`, `tests/test_phase6_timing_and_rf.py` |
| `tau_human_s` | $0.500\text{ s}$ | $1.200\text{ s}$ | $0.500\text{ s}$ was an unrealistic human reaction time. Standard AASHTO Green Book / DGMS baseline is $1.200\text{ s}$ ($1.0\text{--}2.5\text{ s}$). | AASHTO / DGMS Standards | `config/bailadila_hemm_canonical.yaml` |
| `grade_sign` convention | Inconsistent sign ($\pm$) | External Civil $+8\%$ Uphill / $-8\%$ Downhill; Internal $\theta > 0$ Downhill | Fixed through `GradeAdapter` boundary. Physical monotonicity verified. | DGMS Standards & Physics Force Balance | `integration_adapters/grade_adapter.py`, `docs/GRADE_CONVENTION_FINAL.md` |
| `v_mine_speed_limit_kmh` | $50.0\text{ km/h}$ / $30.0\text{ km/h}$ | $20.0\text{ km/h}$ ($5.556\text{ m/s}$) | Regulatory speed limit on unpaved haul roads at Bailadila per DGMS Tech Circular 09/2008. | DGMS Circular 09/2008 & NMDC Site Rules | `config/bailadila_hemm_canonical.yaml`, `fog_safe/safety.py` |
| `fog_hazard_season` | Winter Fog (Nov–Jan) | Monsoon (Jun–Oct) | Problem Statement SIH26007 explicitly identifies dense monsoon fog as the principal operating hazard. | SIH26007 Problem Statement | `config/bailadila_hemm_canonical.yaml`, `reports/phase7_deep_research_master.md` |
| `visibility_minimum_m` | $5.0\text{ m}$ / $10.0\text{ m}$ | $3.0\text{ m}$ | SIH26007 official problem description states visibility drops to $3\text{--}5\text{ metres}$ during severe monsoon fog. | SIH26007 Problem Statement | `config/bailadila_hemm_canonical.yaml` |
| `crusher_service_time_s` | $18.0\text{ s}$ (misinterpreted) | $200.0\text{ s}$ ($18\text{ trucks/hr}$) | Gyratory crusher tipping and hopper clear cycle requires $200\text{ s}$ per dumper, delivering $18\text{ VPH} \times 91.5\text{ t} = 1647\text{ TPH}$. | NMDC Primary Crushing Plant Data | `config/bailadila_hemm_canonical.yaml`, `docs/STAGE5_2_CAPACITY_HIERARCHY.md` |

---

## 3. AUDIT OF SUPERSEDED & LEGACY FILES

The following files retain legacy signatures or test fixtures for backward compatibility:
1. `SYNQRA_SIH2026-27-main/models/vehicle_physics.py`:
   - Acts as a backward-compatibility translation layer. It accepts legacy positional arguments (e.g. `mass_kg=165000.0`, `hardware_max_brake_n=600000.0`) and routes them to `fog_safe.safety.solve_safe_speed()`.
2. `tests/test_physics_unification.py`:
   - Retains `BASE` fixture with $165{,}000\text{ kg}$ and $600{,}000\text{ N}$ to prove that the public API signature of the compatibility adapter remains stable.
3. `config/physical_vehicle_parameters.json`:
   - Explicitly tagged as **SCALE-MODEL HARDWARE PROTOTYPE PARAMETERS** ($2.85\text{ kg}$ bench truck, $0.043\text{ m}$ wheel radius). This file governs bench motor scaling and must NEVER be confused with full-scale HEMM parameters.

---

## 4. VERIFICATION OF COMPLETE HARMONIZATION

With the publication of `config/bailadila_hemm_canonical.yaml` and this migration catalog:
- No parameter exists without an explicit provenance tag (`OEM_REFERENCE`, `STANDARD`, `RESEARCH_DERIVED`, `MEASURED`, `ASSUMED`, `DERIVED`).
- No assumption is disguised as measured data.
- The intelligence engine, Digital Twin, and regression suites now share a single, traceable source of truth.
