# PHASE FINAL REPORT: BAILADILA HEMM CALIBRATION + DSSS GATEWAY + FAIL-SAFE INTEGRATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Problem:** Safe and Efficient Operation of Mine Vehicles in Fog and Low-Visibility Conditions in Open Cast Iron Ore Mines  
**Target Mine Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Dantewada District, Chhattisgarh  
**Vehicle Class:** BEML BH100 100-Tonne Rigid Rear Dump Truck  
**Date:** 2026-09-18  
**Authoritative Status:** ARCHITECTURAL FREEZE BASELINE REPORT  

---

## 1. EXECUTIVE SUMMARY

This report synthesizes the integration of three foundational pillars for the **FOG-ORCHESTRATOR 2.0** safety and orchestration engine:
1. **Research-Derived Bailadila HEMM Parameters**: Rigorously sourced from official BEML specifications, DGMS regulatory circulars, and Phase 7 deep engineering research for the BEML BH100 heavy mining dumper.
2. **Canonical Intelligence & Physics Engine**: Grounded in authoritative multi-constraint longitudinal dynamics (`fog_safe.safety`), establishing analytical stopping distance, deterministic safe speeds ($v_{\text{safe}}$), dynamic headways ($H_{\text{safe}}$), and unambiguous capacity classifications.
3. **DSSS/PN Gateway Communication Architecture & Local Fail-Safe Integration**: A multi-gateway correlation and handover state machine coupled with an onboard Local Vehicle Safety Governor that enforces the non-negotiable invariant $v_{\text{command}} \le v_{\text{safe}}$ under all operating conditions.

All 53 automated regression and fail-safe tests pass with $100\%$ compliance. All 15 known systemic contradictions have been formally audited and resolved.

---

## 2. RESEARCH-DERIVED BAILADILA HEMM PARAMETERS

The canonical vehicle specification models the **BEML BH100**, the primary 100-tonne haul truck operating at NMDC Bailadila Deposit 5:

| Parameter Category | Canonical Parameter | Numerical Value | Units | Provenance Level & Type | Reference / Source |
|--------------------|---------------------|-----------------|-------|-------------------------|--------------------|
| **Mass & Payload** | `mass_empty_kg` | $74{,}000.0$ | $\text{kg}$ | OEM_REFERENCE | BEML BH100 Specification Sheet |
| | `payload_rated_kg` | $91{,}500.0$ | $\text{kg}$ | OEM_REFERENCE | BEML BH100 Technical Datasheet |
| | `mass_loaded_kg` (GVW) | $165{,}500.0$ | $\text{kg}$ | OEM_REFERENCE | Certified Maximum Machine Weight |
| **Geometry** | `length_m` | $10.52$ | $\text{m}$ | OEM_REFERENCE | BEML BH100 Overall Length |
| | `width_m` | $5.52$ | $\text{m}$ | OEM_REFERENCE | BEML BH100 Overall Width |
| | `height_m` | $5.25$ | $\text{m}$ | OEM_REFERENCE | Canopy ROPS Top Height |
| | `wheelbase_m` | $5.25$ | $\text{m}$ | OEM_REFERENCE | Axle Center-to-Center Distance |
| | `wheel_radius_m` | $1.35$ | $\text{m}$ | OEM_REFERENCE | Bridgestone 27.00R49 E-4 Radial |
| | `cg_height_m` | $2.50$ | $\text{m}$ | ASSUMED | Loaded Haul Truck Dynamics Ref. |
| **Powertrain** | `max_engine_power_kw` | $770.0$ ($1{,}032\text{ HP}$) | $\text{kW}$ | OEM_REFERENCE | Cummins KTA38-C Flywheel Power |
| | `max_retarder_power_w` | $1{,}200{,}000.0$ ($1.2\text{ MW}$) | $\text{W}$ | OEM_REFERENCE | Oil-Cooled Wet Disc Retarder |
| **Braking & Drag** | `hardware_brake_max_force_n` | $550{,}000.0$ | $\text{N}$ | STANDARD | ISO 3450:2011 Braking Limit |
| | `rolling_resistance_crr` | $0.025$ (Dry) / $0.035$ (Wet) | -- | RESEARCH_DERIVED | SME Mining Engineering Handbook |
| | `drag_coefficient_cd` | $0.80$ | -- | ASSUMED | Heavy Blunt Mining Vehicle Ref. |
| | `frontal_area_m2` | $22.0$ | $\text{m}^2$ | DERIVED | $5.52\text{m} \times 5.25\text{m} \times 0.76$ blockage |
| **Site Limits** | `v_mine_speed_limit_kmh` | $20.0$ ($5.556\text{ m/s}$) | $\text{km/h}$ | STANDARD | DGMS Tech Circular 09/2008 |
| | `max_ramp_grade_pct` | $8.0$ ($1:12.5$) | $\%$ | STANDARD | DGMS Metalliferous Haul Standard |
| | `crusher_service_time_s` | $200.0$ ($18\text{ VPH}$) | $\text{s}$ | STANDARD | Bailadila Primary Crusher Cycle |
| | `fog_hazard_season` | `MONSOON_JUN_OCT` | range | STANDARD | Problem Statement SIH26007 |
| | `visibility_minimum_m` | $3.0$ | $\text{m}$ | STANDARD | Problem Statement SIH26007 |

---

## 3. PARAMETER PROVENANCE

Every parameter is tagged according to the non-negotiable schema defined in `config/bailadila_hemm_canonical.yaml`:
- **`OEM_REFERENCE`**: BEML official technical specification sheets for BH100; Cummins engine datasheets.
- **`STANDARD`**: DGMS Technical Circulars (09/2008, 03/2024, 07/2025), ISO 3450:2011, SAE J1939-11, Mines Act 1952.
- **`RESEARCH_DERIVED`**: SME Mining Engineering Handbook haul road parameters; peer-reviewed air-over-hydraulic actuator latency literature ($\tau_{\text{actuator}} = 200\text{ ms}$ nominal, $350\text{ ms}$ worst-case).
- **`MEASURED`**: Phase 6 hardware bench measurements on CSS-LoRa 433 MHz RF link ($\tau_{\text{v2v}} = 50\text{ ms}$, $\tau_{\text{gw}} = 80\text{ ms}$) and Tier-1 governor execution latency ($<5\text{ ms}$).
- **`ASSUMED`**: CAN bus latency ($\tau_{\text{can}} = 50\text{ ms}$) intentionally modeled 5-10x conservative compared to SAE J1939 literature ($<10\text{ ms}$) pending in-pit instrumented logging.

---

## 4. CANONICAL PHYSICS

The authoritative longitudinal vehicle model is governed by:
$$m \frac{dv}{dt} = F_{\text{drive}} + F_{\text{grade}} - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$

Where:
- Rolling resistance: $F_{\text{roll}} = C_{\text{rr}} \cdot m \cdot g \cdot \cos\theta$.
- Aerodynamic drag: $F_{\text{aero}} = 0.5 \cdot \rho \cdot C_d \cdot A \cdot v^2$. At the $20\text{ km/h}$ mine limit, $F_{\text{aero}} \approx 333\text{ N}$, which represents $<1.5\%$ of rolling resistance ($40{,}525\text{ N}$). It is retained for completeness but correctly modeled as non-dominant.
- Downhill gravity force: $F_{\text{grade}} = m \cdot g \cdot \sin\theta$.

### Grade Sign Convention:
- External GIS / Mine surveying: **$+8\%$ is Uphill**, **$-8\%$ is Downhill**.
- Internal physics: $\theta > 0$ accelerates the vehicle forward downhill.
- Boundary mapping: Managed exclusively through `GradeAdapter` (`integration_adapters/grade_adapter.py`).

---

## 5. SAFE OPERATING ENVELOPE

The safe operating envelope guarantees that stopping distance plus dynamic safety margin never exceeds usable sight distance:
$$S_{\text{stop}}(v) + S_{\text{margin}}(v) \le R_{\text{effective}}$$

Where:
$$S_{\text{stop}}(v) = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
$$S_{\text{margin}}(v) = S_{\text{base}} + k_{\text{comm}} \cdot (1 - C_{\text{comm}}) \cdot v$$

### Reaction Time Decomposition:
$$\tau_{\text{total}} = \tau_{\text{sensor}} (0.100\text{s}) + \tau_{\text{v2v}} (0.050\text{s}) + \tau_{\text{gw}} (0.080\text{s}) + \tau_{\text{decision}} (0.050\text{s}) + \tau_{\text{can}} (0.050\text{s}) + \tau_{\text{actuator}} (0.200\text{s}) = 0.530\text{ s}$$

---

## 6. SAFE-SPEED RESULTS

Safe speed is calculated analytically by the multi-constraint solver (`fog_safe.safety.solve_safe_speed`):
$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$

### Representative Envelope Solutions ($m = 165.5\text{ t}, \mu = 0.35$):
- **Clear Weather ($R = 100\text{ m}$, Flat):** $v_{\text{safe}} = 5.56\text{ m/s}$ ($20.0\text{ km/h}$) — Limited by `v_mine`.
- **Moderate Fog ($R = 12\text{ m}$, Downhill $-8\%$):** $v_{\text{safe}} = 4.38\text{ m/s}$ ($15.8\text{ km/h}$) — Limited by `v_stop`.
- **Severe Fog ($R = 8\text{ m}$, Downhill $-8\%$):** $v_{\text{safe}} = 3.22\text{ m/s}$ ($11.6\text{ km/h}$) — Limited by `v_stop`.
- **Extreme Fog ($R \le 5\text{ m}$):** $v_{\text{safe}} = 0.0\text{ m/s}$ — Limited by `TIER_1_SAFETY_ZERO_SPEED_HALT`.

---

## 7. HEADWAY RESULTS

Headway strictly separates spatial distance from temporal gap:
- **Safe Distance Headway:**
  $$H_{\text{safe}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{follower}}} - \frac{v^2}{2 a_{\text{leader}}} + S_{\text{margin}} + L_{\text{veh}}$$
  Under conservative brick-wall assumption ($d_{\text{brake\_leader}} = 0$):
  At $v = 4.38\text{ m/s}$, $H_{\text{safe}} \approx 22.5\text{ m}$.
- **Safe Time Headway:**
  $$T_{\text{headway}} = \frac{H_{\text{safe}}}{v} \approx \frac{22.5}{4.38} \approx 5.14\text{ seconds}$$
  Metres and seconds are never conflated.

---

## 8. CAPACITY DEFINITIONS

To eliminate historical contradictions, capacity is strictly typed into three distinct categories:
1. **`THEORETICAL_KINEMATIC` ($700.5\text{ vph}$):** Theoretical single-lane pipe flux ($3600 \cdot v / H$). It reflects traffic flow physics under infinite supply and demand; it is never the active bottleneck.
2. **`PRACTICAL_ROAD` ($180\text{--}600\text{ vph}$):** Haul road capacity accounting for platoon stability, passing restrictions, and junction interference.
3. **`SERVICE_RESOURCE` ($18\text{ vph} = 1{,}647\text{ TPH}$):** The active physical bottleneck governed by the primary crusher tipping cycle ($200\text{ s}$ per dumper). Sustainable mine production can never exceed $1{,}647\text{ TPH}$.

---

## 9. DSSS GATEWAY ARCHITECTURE

The communication topology links vehicles to central orchestration through a multi-gateway PN correlation layer:
- **GW-01 (PN-A):** Pit Rim North Mast ($1{,}245\text{ m}$)
- **GW-02 (PN-B):** Crusher Hopper Overlook ($1{,}280\text{ m}$)
- **GW-03 (PN-C):** Haul Ramp Switchback 3 Tower ($1{,}210\text{ m}$)
- **GW-04 (PN-D):** Pit Bottom Shovel Sector ($1{,}175\text{ m}$)

Each vehicle correlates received RF signals against gateway Gold code signatures ($L=127$) to compute normalized correlation score $\rho \in [0.0, 1.0]$. Proximity is based on link correlation and SNR, not geographic distance.

---

## 10. GATEWAY-SELECTION LOGIC

The selection state machine enforces anti-flapping hysteresis:
$$\rho_{\text{candidate}} > \rho_{\text{current}} + \text{SWITCH\_MARGIN} \quad (\text{SWITCH\_MARGIN} = 0.15)$$
- Candidate must maintain advantage for $N \ge 3$ consecutive observations (`PERSISTENCE_COUNT`).
- If primary gateway beacon is missing for $>1.50\text{ s}$ (`FAIL_TIMEOUT`), the system fails over immediately to a viable candidate or transitions to `NO_GATEWAY` / `DISCONNECTED`.

---

## 11. FAIL-SAFE ARCHITECTURE

The Local Vehicle Safety Governor is the highest operational authority:
$$\text{CENTRAL INTELLIGENCE} \to \text{RECOMMENDED COMMAND} \to \text{LOCAL GOVERNOR} \to \text{ACCEPT / CLAMP / REJECT} \to \text{ACTUATOR}$$

### Monotonic Hierarchy:
- **Level 0:** Emergency / Local Physical Safety (E-Stop button, loss-of-air valve)
- **Level 1:** Local HEMM Safety Governor (`integration_adapters/fail_safe_controller.py`)
- **Level 2:** Vehicle Command Validation Gateway
- **Level 3:** Central FOG-Orchestrator Intelligence Engine
- **Level 4:** Fleet Optimization & Slot Reservation
- **Level 5:** Predictive 3D Digital Twin (Observation only; no direct actuator path)

---

## 12. COMMUNICATION FAILURE BEHAVIOR

| Failure Mode | Governor Action | Resulting Vehicle State | Speed Actuation |
|--------------|-----------------|-------------------------|-----------------|
| **Normal Packet** | ACCEPT | `NORMAL` | Applied as requested ($\le v_{\text{safe}}$) |
| **Over-Speed Command** | CLAMP | `UNSAFE_COMMAND` | Clamped to $v_{\text{safe}}$ |
| **Stale Command ($>1.0\text{s}$)** | REJECT | `STALE_COMMAND` | Retains previous safe speed |
| **Duplicate Sequence** | REJECT | `INVALID_COMMAND` | Command dropped |
| **Out-of-Order Sequence** | REJECT | `INVALID_COMMAND` | Command dropped |
| **No Gateway Link** | REJECT | `NO_GATEWAY` | Governed strictly by local sensors |
| **Complete RF Outage ($>1.0\text{s}$)**| REJECT | `EMERGENCY_STOP` | Forced to $0.0\text{ m/s}$ |
| **Manual E-Stop** | REJECT | `EMERGENCY_STOP` | Forced to $0.0\text{ m/s}$ (Latched) |
| **Post-Fault Recovery** | REJECT (Frame 1) | `RECOVERY` | Re-syncs sequence before resume |

### Qualification of 75% Packet Loss:
Under $75\%$ packet loss, **local safety invariants remain fully enforced** ($v_{\text{applied}} \le v_{\text{safe}}$, stale packets rejected, vehicle halts safely if silence persists). The wireless link itself degrades; safety robustness ensures zero loss of vehicle control.

---

## 13. CONTRADICTION RESOLUTION

All 15 systemic contradictions documented in `docs/CONTRADICTION_REGISTER.md` have been resolved:
1. Grade sign convention unified via `GradeAdapter`.
2. Safe speed discrepancies resolved through canonical analytical quadratic solving ($4.3815\text{ m/s}$).
3. Capacity conflation ($700.5\text{ vph}$ vs $18\text{ vph}$) resolved via explicit type tagging.
4. $92.4\text{ vph}$ expunged and identified as a misread $92.41\text{ km/h}$ retarder velocity limit.
5. $3{,}294\text{ TPH}$ transient queue flush clamped to $1{,}647\text{ TPH}$ physical crusher ceiling.
6. HOLD policy delay conservation recognized under Little's Law.
7. $\le 5\text{ m}$ visibility classified as zero-speed emergency halt ($0\text{ TPH}$).
8. CAN latency ($50\text{ ms}$) classified as conservative assumption.
9. 75% packet loss qualified as governor robustness, not RF link reliability.
10. Test pass counts qualified as regression assertions, not physical field validity.
11. Modeled non-collision separated from unmodeled open-pit obstacles.
12. Software scalability separated from physical RF bandwidth scalability.
13. Simulation/bench testing separated from real-world mine field validation.
14. Research DSSS model separated from physical CSS-LoRa 433 MHz prototype.
15. Gateway communication transport separated from local vehicle safety authority.

---

## 14. AUTOMATED TEST RESULTS

Comprehensive automated test execution proves system-wide compliance:
- **`tests/test_hemm_canonical_regression.py`**: 7 passed in 1.23s (Schema, force balance, grade monotonicity, stopping distance decomposition, headway separation, capacity distinction).
- **`tests/test_dsss_gateway_selection.py`**: 6 passed in 0.37s (Cold start, rejection, handover margin, persistence count, anti-flapping, timeout failover).
- **`tests/test_failsafe_execution.py`**: 28 passed in 1.34s (FS-01 to FS-16, Invariants I1 to I12).
- **`tests/test_phase6_timing_and_rf.py`**: 7 passed in 3.40s (CAN bench stats, RF dataset, packet loss invariant, Safe Beacon hierarchy).
- **`tests/test_grade_adapter.py`**: 5 passed in 0.50s (Grade conversion, clamping, 5-point physical monotonicity).
- **TOTAL SUITE:** **53 PASSED, 0 FAILED** ($100\%$ pass rate).

---

## 15. REMAINING ASSUMPTIONS

The following engineering assumptions remain documented in `config/bailadila_hemm_canonical.yaml`:
1. `tau_can_assumed_s = 0.050 s`: Assumed conservative baseline pending physical J1939 CAN bus logging on BEML chassis.
2. `tau_actuator_s = 0.200 s` (Nominal) / `0.350 s` (Worst-Case): Sourced from heavy vehicle air-over-hydraulic literature pending direct pressure transducer logging on BEML BH100 brake packs.
3. `cg_height_m = 2.50 m`: Assumed loaded center of gravity height.
4. `drag_coefficient_cd = 0.80`: Assumed aerodynamic form drag coefficient.

---

## 16. REMAINING FIELD-VALIDATION REQUIREMENTS

To transition from software readiness to full commercial deployment at NMDC Bailadila Deposit 5, the following 5 field trials must be conducted in subsequent phases:
- **G1 (RF Propagation Survey):** Site RF drive-test inside Deposit 5 pit to measure true path loss, bench diffraction, and fog attenuation.
- **G2 (J1939 CAN Bus Logging):** CAN bus logging on an operational BEML BH100 dumper to measure P95/P99 frame arbitration delays.
- **G3 (Brake Actuator Response Logging):** Pressure transducer logging on brake relay valves to measure physical pressure build-up latency.
- **G4 (Haul Route Geometry Survey):** Integration of actual surveyed switchback radii and profiles from Bailadila Deposit 5 Detailed Project Reports (DPR).
- **G5 (Monsoon Fog Time-Series Logging):** Deployment of optical transmissometers on Deposit 5 haul roads to log visibility time-series during the June–October monsoon.

---

## 17. ARCHITECTURE FREEZE RECOMMENDATIONS

The software architecture of FOG-ORCHESTRATOR 2.0 is complete, modular, and internally consistent:
1. **Freeze Core Interfaces:** Freeze `fog_safe.safety.solve_safe_speed`, `GradeAdapter`, `DSSSGatewaySelector`, and `LocalVehicleSafetyGovernor`.
2. **Preserve Authority Monotonicity:** Reject any future proposal that grants central intelligence or predictive Digital Twin instances the authority to override local vehicle safety limits.
3. **Advance to Physical Baseband Prototyping:** Transition from the current architectural DSSS simulation layer to FPGA-based DSSS chipping transceivers in post-SIH hardware trials.

---

## FINAL DECISION GATE

$$\mathbf{STATUS: GREEN}$$

### Rationale:
- Research-derived Bailadila HEMM parameters are fully integrated into canonical configuration with complete provenance metadata.
- Longitudinal vehicle physics, GradeAdapter sign handling, stopping distance decomposition, and headway calculations are internally consistent and mathematically proved.
- The DSSS multi-gateway selection architecture and anti-flapping state machine are fully specified and tested.
- Local Vehicle Safety Governor fail-safe behavior is verified across all 16 test matrix conditions (FS-01 to FS-16) and all 12 critical safety invariants (I1 to I12).
- All 15 systemic contradictions are formally resolved with complete traceability.
- The system is **100% READY FOR ARCHITECTURE FREEZE** and progression to physical system validation.
