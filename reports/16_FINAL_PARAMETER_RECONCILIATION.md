# 16 — FINAL PARAMETER RECONCILIATION & MASTER PROVENANCE REGISTER
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Governing Standard |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-16** | `reports/16_FINAL_PARAMETER_RECONCILIATION.md` | 2026-09-18 | **FROZEN / LOCKED** | ISO 3450 / DGMS 09/2008 |

---

### Master Parameter Provenance & Reconciliation Register

```markdown
| Parameter | Old Value | Reconciled Canonical Value | Unit | Governing Equation / Physical Basis | Evidence Level | Source Reference | Audit Reason / Justification | Confidence | Status |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **`mass_empty_kg`** | 74,000.0 | 74,000.0 | kg | Tare weight with standard body & cab | OEM_DOCUMENTED (L2) | BEML BH100 Technical Spec | Certified unladen chassis mass | VERY_HIGH | **KEEP** |
| **`payload_rated_kg`** | 91,500.0 | 91,500.0 | kg | Rated payload capacity (91.5 tonnes) | OEM_DOCUMENTED (L2) | BEML BH100 Datasheet | Certified nominal iron ore payload | VERY_HIGH | **KEEP** |
| **`mass_loaded_kg`** | 165,000.0 | 165,500.0 | kg | $m_{\text{empty}} + m_{\text{payload}} = 74.0\text{t} + 91.5\text{t}$ | OEM_DOCUMENTED (L2) | Exact sum of certified weights | Reconciled 165.0t marketing round to exact sum | VERY_HIGH | **UPDATE** |
| **`length_m`** | 10.52 | 10.52 | m | Overall bumper-to-canopy length | OEM_DOCUMENTED (L2) | BEML BH100 Dimensional Layout | Physical vehicle bounding length | HIGH | **KEEP** |
| **`width_m`** | 5.52 | 5.52 | m | Outside tire-to-tire width | OEM_DOCUMENTED (L2) | BEML BH100 Dimensional Layout | Physical vehicle operating width | HIGH | **KEEP** |
| **`max_ramp_grade_pct`** | 8.0 | 8.0 | % | Civil grade: $\Delta h / \Delta s$ ($1\text{-in-}12.5$) | STANDARD_REGULATION (L4) | DGMS (Tech) Circular 09/2008 | Statutory maximum mine ramp gradient | VERY_HIGH | **KEEP** |
| **`grade_sign_convention`**| Inconsistent | Unified Civil/GIS | Sign | Uphill $= +8.0\%$, Downhill $= -8.0\%$ | STANDARD_REGULATION (L4) | Civil / GIS Engineering Standard | Unified across all kinematics via GradeAdapter | VERY_HIGH | **UPDATE** |
| **`friction_dry`** | 0.35 | 0.35 | - | Compacted crushed hematite road surface | LITERATURE_SUPPORTED (L5) | SME Mining Engineering Handbook | Standard dry unpaved haulage friction | HIGH | **KEEP** |
| **`friction_wet`** | 0.35 | 0.30 | - | Saturated hematite clay slurry road surface | LITERATURE_SUPPORTED (L5) | Bailadila Pit Surface Studies | Degraded wet haul road friction boundary | MEDIUM_HIGH | **UPDATE** |
| **`friction_worst`** | 0.25 | 0.25 | - | Monsoon slick liquid mud sensitivity point | ENGINEERING_SCENARIO (L6) | Severe Monsoon Sensitivity Model | Conservative emergency stopping lower bound | MEDIUM | **KEEP** |
| **`tau_sensor`** | 25.0 | 25.0 | ms | IMU and wheel speed filter window | BENCH_MEASURED (L7) | ESP32 Hardware Timer Test | Verified perception acquisition latency | HIGH | **KEEP** |
| **`tau_decision`** | 50.0 | 50.0 | ms | Tier-1 Local Safety Governor tick period | BENCH_MEASURED (L7) | ESP32 FreeRTOS Task Period (20 Hz) | Verified governor execution loop | HIGH | **KEEP** |
| **`tau_CAN_bound`** | 50.0 | 50.0 | ms | High-priority brake PGN arbitration ceiling | BENCH_MEASURED (L7) | ESP32 TWAI 250 kbps testbed @ 70% load | P99 = 24.1 ms; bounded <= 50.0 ms | HIGH | **KEEP** |
| **`tau_actuator_nominal`**| 250.0 | 200.16 (Bench) / 250 (Model) | ms | Air-over-hydraulic pressure rise time | SURROGATE_BENCH (L7) | Instrumented Proportional Valve | Bench measured 200.16 ms; 250 ms model (1.25x) | HIGH_SURROGATE | **UPDATE** |
| **`tau_actuator_P99`** | 237.1 | 237.1 | ms | Surrogate bench P99 pressure rise | SURROGATE_BENCH (L7) | Proportional Valve Apparatus | Empirical 99th percentile build-up | HIGH_SURROGATE | **KEEP** |
| **`tau_actuator_worst`** | 350.0 | 350.0 | ms | Cold oil / worn lining upper bound | ENGINEERING_SCENARIO (L6) | Analytical Sensitivity Model | Conservative bound (NOT an ISO statutory clause) | MEDIUM | **KEEP** |
| **`tau_local_nominal`** | 375.0 | 375.0 | ms | $\sum (25 + 50 + 50 + 250\text{ ms})$ | BENCH_DERIVED (L7) | Nominal Local Loop Aggregation | Decomposed local reaction time baseline | HIGH | **KEEP** |
| **`tau_local_P99`** | 437.1 | 437.1 | ms | Statistical P99 non-overlapping bound | BENCH_DERIVED (L7) | P99 Aggregated Latency Decomposition | Conservative P99 local reaction ceiling | HIGH | **KEEP** |
| **`tau_fleet_command`** | 685.0 | 685.0 | ms | ESP32 $\to$ LoRa $\to$ Gateway $\to$ Cloud $\to$ Cmd | BENCH_MEASURED (L7) | End-to-End Testbed Ping-Pong Trace | P50 cloud dispatch round trip (Excluded from S_stop) | HIGH | **KEEP** |
| **`a_dec_emergency`** | 1.20 | 2.7466 | $\text{m/s}^2$ | $a_{\text{net}} = [F_{\text{brake}} + F_{\text{roll}} - F_{\text{grade}}] / m$ | DERIVED_MODEL (L3) | Vehicle Dynamics Force Balance | True net retarding on -8% ramp at 12m (Yields 5.12 m/s) | HIGH | **UPDATE** |
| **`a_dec_service`** | -- | 1.20 | $\text{m/s}^2$ | Gentle service brake / comfort assumption | ENGINEERING_ASSUMPTION (L6) | Heavy Vehicle Braking Comfort Lit | Downgraded: Conservative service retarding (Yields 3.67 m/s) | MEDIUM | **UPDATE** |
| **`s_base_margin`** | 5.0 | 5.0 | m | Standstill standoff clearance gap | STANDARD_REGULATION (L4) | DGMS Circular 09/2008 & ISO 3450 | Mandatory obstacle clearance margin | VERY_HIGH | **KEEP** |
| **`v_safe` (@ 12m, Emerg)** | 4.3815 | 5.1158 (18.4 km/h) | m/s | Quadratic analytical root ($S_{\text{stop}} \le 7.0\text{m}$) | DERIVED_MODEL (L3) | Newtonian Kinematic Solution | Supersedes legacy 4.3815 m/s under autonomous timing | VERY_HIGH | **UPDATE** |
| **`v_safe` (@ 12m, Serv)** | -- | 3.6734 (13.2 km/h) | m/s | Quadratic analytical root ($a_{\text{dec}} = 1.20\text{m/s}^2$) | DERIVED_MODEL (L3) | Newtonian Kinematic Solution | Safe speed under conservative service deceleration | VERY_HIGH | **UPDATE** |
| **`v_safe` (@ 3–5m, Dense)**| -- | 0.0000 (0.0 km/h) | m/s | Kinematic collapse ($R_{\text{effective}} \le 5.0\text{m}$) | DERIVED_MODEL (L3) | Analytical Boundary Condition | Controlled staging enforced; zero throughput fabricated | VERY_HIGH | **UPDATE** |
| **`H_safe_space`** | 17.52 | 22.52 | m | $H_{\text{space}} = S_{\text{stop}}(7.0) + S_{\text{base}}(5.0) + L(10.52)$ | DERIVED_MODEL (L3) | Center-to-Center Space Headway | Reconciled: Historical 17.52 omitted 5.0m buffer | VERY_HIGH | **UPDATE** |
| **`road_capacity_pipe`** | 700.5 | 817.8 (Emerg) / 587.2 (Serv) | VPH | $C = 3600 \cdot v / H_{\text{space}}$ | DERIVED_APPROXIMATION (L3) | Kinematic Pipe Flux Formulation | Reconciled: 700.5 used legacy 4.3815 m/s | HIGH | **UPDATE** |
| **`crusher_capacity`** | 1,647.0 | 1,647.0 | TPH | $18\text{ dumps/hr} \times 91.5\text{ tonnes}$ ($200\text{s}$ cycle) | PHYSICAL_CALCULATED (L3) | Deposit-5 Gyratory Crusher Specs | Hard physical bottleneck steady-state ceiling | VERY_HIGH | **KEEP** |
| **`transient_flush_tph`**| 3,294.0 | RETRACTED (0.0) | TPH | 6 trucks dumped in 10-minute burst | DISPROVEN_ARTIFACT (RED) | 10-min Initial Queue Burst Trace | Disproven as steady-state mine capacity | DISPROVEN | **REMOVE** |
| **`steady_state_tph`** | 1,591.4 | 1,591.4 | TPH | Coordinated Level 4 dispatch across 30 seeds | SIMULATION_AUDITED (L9) | Closed-Loop Discrete Event Engine | Sustained steady-state (96.6% crusher utilization) | HIGH_SIMULATION | **KEEP** |
| **`ramp_waiting_reduction`**| -77.1% | -77.36% (-483.8 s) | % | $625.4\text{s} \to 141.6\text{s}$ on haul ramp | SIMULATION_AUDITED (L9) | Multi-Seed Queue Tracking (30 seeds) | Relocation of hazardous downhill ramp queue | HIGH_SIMULATION | **KEEP** |
| **`origin_waiting_increase`**| -- | +454.65% (+401.0 s) | % | $88.2\text{s} \to 489.2\text{s}$ in shovel bays | SIMULATION_AUDITED (L9) | Multi-Seed Queue Tracking (30 seeds) | Quantifies Little's Law queue relocation | HIGH_SIMULATION | **UPDATE** |
| **`net_cycle_delay_change`**| -11.6% | -11.60% (-82.8 s) | % | $713.6\text{s} \to 630.8\text{s}$ total cycle wait | SIMULATION_AUDITED (L9) | Multi-Seed Queue Tracking (30 seeds) | Net cycle efficiency gain from smooth rolling | HIGH_SIMULATION | **KEEP** |
```
