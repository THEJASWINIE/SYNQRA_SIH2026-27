# 00 — RESEARCH AUDIT: SENSOR & DATA DEGRADATION
## FOG-ORCHESTRATOR 2.0 — Forensic & Architectural Audit
**Project:** SIH26007 — Fog & Low-Visibility Autonomous/Connected Fleet Orchestrator  
**Audit Date:** 2026-09-21  
**Auditor:** Systems Architect & Safety-Critical Verification Lead  
**Audit Objective:** Rigorously partition established fact, simulation evidence, engineering assumption, unverified interface, and forbidden claims prior to code execution.

---

## 1. What Has Already Been Established (Fact & Code Reality)

1. **Frozen Architectural Authority:**  
   The project has an inviolable safety authority hierarchy:
   $$\text{Local Physical E-Stop (L0)} \to \text{Local Vehicle Safety Governor (L1)} \to \text{Command Gateway (L2)} \to \text{Central Orchestrator (L3)} \to \text{Optimization / Digital Twin (L4/L5)}$$
   The local safety governor (`LocalVehicleSafetyGovernor` in `integration_adapters/fail_safe_controller.py`) is the ultimate operational authority. Invariant $v_{\text{applied}} \le v_{\text{safe}}$ is strictly enforced.

2. **Vehicle Telemetry Quality Filtering Exists:**  
   `integration_adapters/telemetry_quality_filter.py` actively classifies vehicle telemetry into `LIVE`, `DELAYED`, `STALE`, `OFFLINE`, and `RECOVERING`. It detects packet drops, calculates sequence loss, and protects the Digital Twin from vehicle telemetry dropouts.

3. **Deterministic Multi-Constraint Physics Engine:**  
   `fog_safe/safety.py` implements the closed-form quadratic stopping distance equation:
   $$v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{eff}} + \sqrt{a_{\text{dec}}^2 \tau_{\text{eff}}^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$
   Multi-constraint safe speed is solved as:
   $$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$
   Friction $\mu \le 0$ fails closed ($v_{\text{safe}} = 0$, `INVALID_FRICTION`). Invalid curve radius fails closed ($v_{\text{curve}} = 0$).

4. **Identified Primary Safety Vulnerability:**  
   The environmental telemetry path (`visibility_m \to R_{\text{effective}}`) has **no health, freshness, range, or plausibility filter**.
   A stale or biased visibility measurement directly corrupts $v_{\text{stop}}$ without detection by `TelemetryQualityFilter`, representing a primary safety gap in low-visibility operations.

5. **Hardware Footprint Boundaries:**  
   - Prototype hardware consists of ESP32 microcontrollers communicating via LoRa / Wi-Fi / Serial.
   - TRUCK_01 has physical wheel encoder odometry and MPU6050 IMU.
   - TRUCK_02 has PWM-derived speed (not encoder-measured, never treated as confirmed speed).
   - `GNSS_EQUIPPED_VEHICLES = frozenset()` — zero GNSS receivers exist on the physical prototype; synthetic GNSS is strictly for testing.
   - Visibility is injected from central/weather station telemetry, never from on-vehicle hardware sensors.

---

## 2. What Is Experimentally Demonstrated (Bench / HIL Tested)

1. **Local Governor Clamping ($v_{\text{applied}} \le v_{\text{safe}}$):**  
   Tested across 1,009 canonical cases in `FINAL/FINAL_SAFETY_VALIDATION.csv` with zero violations. Over-speed commands from central dispatch are clamped or rejected.
2. **Phase 8 HIL Communication & Failsafe Execution:**  
   60 out of 60 test cases passed in `tests/test_phase8_hil.py`. Verified that watchdog timeouts ($1.0\text{ s}$), communication link failures, and corrupt packets trigger fallback states (`DEGRADED_COMMUNICATION`, `NO_GATEWAY`, `STOP`).
3. **Telemetry Ingestion Invariants:**  
   `tests/test_telemetry_ingest.py` (32 KB) confirms that malformed packets, negative speeds, non-finite values, and payload bounds do not crash the ingestion pipeline.
4. **V2V Protocol Compatibility:**  
   Existing state packet format `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz` runs without schema modification across the HIL simulator.

---

## 3. What Is Only Simulated

1. **165.5-Tonne BEML BH100 Dump Truck Dynamics:**  
   The vehicle mass ($165,500\text{ kg}$ loaded, $85,000\text{ kg}$ empty), hydraulic retarder thermal curve, pneumatic brake lag, and tire-road friction are modeled via differential equations in `fog_safe/`. No physical 165-tonne truck was actuated.
2. **Mine-Scale Road Network & Queue Model:**  
   The 3-zone road topology (Loading Point, Haul Road with $-8\%$ grade, Dumping Crusher) and queue bottleneck progression are evaluated in discrete-event / agent simulation.
3. **Fog Field Propagation:**  
   Spatial fog zones (Zone A: $50\text{ m}$, Zone B: $20\text{ m}$, Zone C: $8\text{ m}$) are simulated synthetic inputs, not physical meteorological optical scatter measurements.
4. **Fleet Orchestration Benefits:**  
   Throughput metrics, cycle time shifts, and staging vs. hazardous road waiting numbers are derived entirely from Python simulation benchmarks.

---

## 4. What Is Only Analytically Derived

1. **Analytical Stopping Envelope ($v_{\text{stop}}$):**  
   Derived from classical Newtonian kinematics:
   $$S_{\text{stop}}(v) = v \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
   Equating $S_{\text{stop}}(v) + S_{\text{margin}}(v) = R_{\text{effective}}$ yields the analytical quadratic solution.
2. **Deceleration Envelope on Grade:**  
   $$a_{\text{dec}} = g (\mu_{\text{effective}} \cos\theta + \sin\theta - c_{\text{rr}} \cos\theta)$$
   Derived analytically from rigid-body tire friction balance.
3. **Stale Visibility Safety Gap:**  
   The proof that holding stale $50\text{ m}$ visibility while true visibility drops to $12\text{ m}$ causes an over-speed allowance of $+5.82\text{ m/s}$ ($20.9\text{ km/h}$) at $-8\%$ grade is analytically derived from the quadratic solution.

---

## 5. What Is an Engineering Assumption

| Parameter / Feature | Value / Assumption | Classification | Rationale |
|---|---|---|---|
| $T_{\text{DEGRADED\_ENV}}$ | $30.0\text{ s}$ | Engineering Parameter | Optical scatter sensors typically average over $10\text{--}30\text{ s}$ intervals. |
| $T_{\text{STALE\_ENV}}$ | $60.0\text{ s}$ | Engineering Parameter | Beyond 1 minute, advection fog can drop visibility rapidly. |
| $T_{\text{GRACE\_PERIOD}}$ | $120.0\text{ s}$ | Engineering Parameter | Grace holding period before dropping to absolute floor. |
| $\text{DEGRADED\_FACTOR}$ | $0.70$ (30% penalty) | Engineering Parameter | Conservative margin for degraded confidence. |
| $\text{STALE\_FACTOR}$ | $0.50$ (50% penalty) | Engineering Parameter | Severe conservative margin under unrefreshed state. |
| $R_{\text{MIN}}$ | $5.0\text{ m}$ | Engineering Parameter | Physical vehicle bumper-to-sensor offset limit. |
| $R_{\text{UNAVAILABLE\_MIN}}$ | $8.0\text{ m}$ | Engineering Parameter | Standard crawl / dense fog headway requirement. |
| Recovery Hysteresis | 2 frames (STALE), 3 (UNAVAIL) | Engineering Parameter | Prevents flapping across state boundaries. |
| $S_{\text{base}}$ | $5.0\text{ m}$ | Engineering Parameter | Static buffer distance to obstacle. |
| $\tau_{\text{total}}$ | $0.80\text{ s}$ (HIL) to $1.50\text{ s}$ (human) | Engineering Parameter | Sensor + compute + hydraulic build-up latency. |

---

## 6. What Is Unknown

1. **True BH100 CAN/J1939 Bus Availability:**  
   It is unknown whether BEML BH100 dump trucks in open-cast mines expose open J1939 PGNs for wheel speed, retarder oil temperature, and brake chamber pressure without proprietary OEM gateway encryption.
2. **Mine Atmospheric Scatter Spectral Characteristics:**  
   Whether coal dust / iron ore dust in pit air creates backscatter that causes commercial optical visibility sensors to read falsely high or falsely low.
3. **Wireless Packet Error Distribution in Deep Open-Cast Pits:**  
   The exact Rayleigh/Rician fading and multipath profile of $868/433\text{ MHz}$ LoRa vs. $2.4\text{ GHz}$ Wi-Fi across highwall benches.
4. **Human Operator Reaction Time Under Auditory Safe-Speed Advisories:**  
   Whether truck operators in low visibility respond within $1.2\text{ s}$ or experience cognitive overload when speed advisory commands change dynamically.

---

## 7. What Is Proposed But Not Yet Implemented (At Start of Phase 9 Execution)

1. `integration_adapters/environmental_data_health.py` — The concrete module executing H1–H5 rules.
2. `tests/test_environmental_data_health.py` — Formal unit and integration tests.
3. `experiments/run_sensor_degradation_benchmark.py` — Deterministic matched-seed benchmark runner across D0–D13.
4. Monte Carlo safety validation harness ($N \ge 10,000$).
5. Final synthesis reports and publication figures.

---

## 8. What Is Implemented But Not Validated in Field

1. **Dual-Truck Coexistence over Radio:** Validated on bench HIL; never deployed on active haul roads with haul truck engine RF noise.
2. **Safe Beacon RSSI Proximity Detection:** Validated in laboratory RF tests; not field-validated against pit highwall reflection.
3. **BEML BH100 Kinematic Scaling:** Implemented in `integration_adapters/kinematic_scale.py`; calibrated analytically, not measured on physical dynamometer.

---

## 9. Claims That Must NOT Be Made (Forbidden Claims)

The following claims are strictly forbidden across all artifacts, reports, and code comments:

❌ **FORBIDDEN:** "Guaranteed collision-free operation"  
*Correction:* "Demonstrated deterministic stopping-distance envelope preservation under modeled simulation and HIL conditions."

❌ **FORBIDDEN:** "Field-validated on BEML BH100 trucks"  
*Correction:* "Modeled using published BEML BH100 physical and dimensional parameters; validated in simulation and laboratory HIL."

❌ **FORBIDDEN:** "Eliminates all sensor failure risks"  
*Correction:* "Mitigates detectable freshness, range, rate-of-change, and sequence failures; explicitly cannot detect Class C plausible-but-wrong single-source failures without an independent reference."

❌ **FORBIDDEN:** "Compliant with ISO 19014 / ISO 17757 / IEC 61508 / SAE J1939"  
*Correction:* "Designed with reference to principles in ISO 17757 and IEC 61508; full formal standards compliance requires physical certification not performed."

❌ **FORBIDDEN:** "Eliminates haul road waiting time"  
*Correction:* "Orchestrates traffic by converting uncontrolled, hazardous road stopping into controlled staging queue delays."

❌ **FORBIDDEN:** "Novel AI/ML sensor fusion"  
*Correction:* "Rule-based, deterministic, auditable data-health validation layer coupling telemetry validity to physics-constrained safety limits."

---

## 10. Audit Conclusion

The research trajectory is sound if and only if:
1. The bounded, auditable, rule-based approach (Decision C) is maintained.
2. Class C plausible-but-wrong data is explicitly recorded as an unresolvable fundamental limitation for single-source architectures.
3. Local vehicle safety authority ($v_{\text{applied}} \le v_{\text{safe}}$) remains inviolable.
4. Evidence boundaries (Simulation vs. Bench HIL vs. Field) are uncompromised.
