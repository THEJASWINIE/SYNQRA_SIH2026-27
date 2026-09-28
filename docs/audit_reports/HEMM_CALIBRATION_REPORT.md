# HEMM CALIBRATION & OPERATING-ENVELOPE REPORT
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
### Phase 1: Heavy Earth Moving Machinery (HEMM) Physics Calibration

**Document Version:** 1.0.0  
**Date:** September 17, 2026  
**Primary Vehicle Reference:** BEML BH100 / Caterpillar 777G (100-tonne class rigid mining haul truck)  
**Governing Site Reference:** NMDC Bailadila Deposit 5 Open-Cast Iron Ore Mine  
**Evidence Principle:** Physical Evidence > Derived Model > Engineering Assumption > Simulation Output > Presentation Claim  

---

## Executive Summary

In accordance with the Phase 1 project directive, all RF/DSSS validation, CAN-delay physical calibration, and final system validation were **PAUSED**. The sole objective of Phase 1 is to establish a scientifically defensible, mathematically closed, and physically grounded Heavy Earth Moving Machinery (HEMM) vehicle model and operating envelope.

This report establishes the verified parameter baseline connecting:
$$\text{ENVIRONMENT} \to \text{VEHICLE PARAMETERS} \to \text{VEHICLE DYNAMICS} \to \text{BRAKING / RETARDING} \to \text{STOPPING DISTANCE} \to \text{SAFE SPEED} \to \text{SAFE HEADWAY} \to \text{ROAD CAPACITY}$$

---

## A. What Was Calibrated

1. **Vehicle Inertia & Payload Baseline:**
   - Unladen Tare Weight: $74{,}000.0\text{ kg}$ ($74.0\text{ t}$)
   - Rated Ore Payload: $91{,}500.0\text{ kg}$ ($91.5\text{ t}$)
   - Gross Operating Weight: $165{,}500.0\text{ kg}$ ($165.5\text{ t}$)
2. **Service Braking & Deceleration Limit:**
   - Unified mechanical braking actuator ceiling to $F_{\text{hardware\_max}} = 550{,}000.0\text{ N}$ (550 kN), resolving previous contradictions ($450\text{ kN}$ vs $550\text{ kN}$ vs $600\text{ kN}$).
   - Validated that $550\text{ kN}$ yields $a_{\text{dec,max}} = 3.323\text{ m/s}^2$ ($0.339\text{ g}$) loaded, strictly matching ISO 3450 criteria ($2.8\text{--}3.5\text{ m/s}^2$).
3. **Continuous Retarding Power Ceiling:**
   - Hydrodynamic / oil-cooled multi-disc continuous retarding absorption ceiling calibrated at $P_{\text{retarder,max}} = 1{,}200{,}000.0\text{ W}$ ($1.2\text{ MW}$).
4. **Road Rolling Resistance & Aerodynamics:**
   - Rolling resistance coefficient calibrated to $C_{rr} = 0.025$ for compacted unpaved haul roads (USBM / SME Handbook).
   - Aerodynamic drag contribution quantified at haul speeds ($v \le 11.11\text{ m/s}$): $F_{\text{aero}} \le 3.27\%$ of $F_{\text{roll}}$, proving that aerodynamic forces are minor compared to tire-road rolling and grade resistance.
5. **Grade Convention & GradeAdapter:**
   - Formalized two-way bijective adapter between Civil/GIS convention ($+8\%$ uphill, $-8\%$ downhill) and Internal Resistance Physics ($\theta > 0$ downhill, $\theta < 0$ uphill).
   - Proved strict monotonicity across the mandatory 5-point test matrix: $+8\%, +5\%, 0\%, -5\%, -8\%$.
6. **Simulation Timestep Authority & Invariant:**
   - Proved that vehicle state integration is strictly singular per timestep $\Delta t$. Eliminated potential double-stepping defects between outer simulation loops and inner digital twin state updates.
7. **Operating Envelopes & Capacities:**
   - Mapped full 4,860-point deterministic calibration matrix across 9 visibilities, 5 grades, 4 friction states, 3 loading states, 3 latencies, and 3 speeds.
   - De-conflated theoretical kinematic saturation ($700.5\text{ vph}$), convoy headway limits ($180\text{ vph}$), and crusher dumping bottleneck ($18\text{ vph}$ / $1{,}647\text{ TPH}$).

---

## B. What Was Measured

1. **Desktop Scale Prototype Parameters (Physical Caliper & Balance Measurements):**
   - TRUCK_01 Wheel Radius: $0.050\text{ m}$ (Diameter $0.100\text{ m}$)
   - TRUCK_01 Chassis Mass: $2.20\text{ kg}$
   - TRUCK_02 Wheel Radius: $0.0425\text{ m}$ (Diameter $0.085\text{ m}$)
   - TRUCK_02 Chassis Mass: $1.85\text{ kg}$
2. **Microcontroller Bench Latencies:**
   - ESP32 hardware UART telemetry packet serialization and parsing latency: $8.4\text{ ms} \pm 1.2\text{ ms}$.
   - Tier-1 local governor control loop execution time on ESP32: $14.2\text{ ms}$.

*Important Note:* No physical sensor or telemetry measurements were conducted on full-scale 165-tonne haul trucks inside NMDC Bailadila Deposit 5.

---

## C. What Was Derived

1. **BEML BH100 / Caterpillar 777G Dimensions & Inertia:**
   - Length: $10.52\text{ m}$, Width: $5.52\text{ m}$, Height: $5.25\text{ m}$, Wheelbase: $5.25\text{ m}$. Derived from manufacturer engineering specification sheets.
   - Frontal Area: $A = 22.0\text{ m}^2$, calculated as Width ($5.52\text{ m}$) $\times$ Height ($5.25\text{ m}$) $\times$ form fill factor ($0.76$).
2. **Kinematic Stopping Distance & Safe Speed:**
   - Analytical quadratic closed-form root of ISO 3450 stopping constraint:
     $$v_{\text{safe}} = -a_{\text{dec}} \tau_{\text{eff}} + \sqrt{a_{\text{dec}}^2 \tau_{\text{eff}}^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$
   - Canonical dense fog safe speed on $-8.0\%$ downhill wet ramp: $v_{\text{safe}} = 4.3815\text{ m/s}$ ($15.77\text{ km/h}$).
3. **Primary Gyratory Crusher Ceiling:**
   - Derived from $200\text{ s}$ dumper tipping/hopper clearance cycle:
     $$\mu_{\text{crusher}} = \frac{3600\text{ s}}{200\text{ s}} = 18\text{ trucks/hr} \implies C_{\text{crusher}} = 18 \times 91.5\text{ t} = 1{,}647.0\text{ TPH}$$
4. **Autonomous Reaction Time Budget:**
   - Derived as linear sum of component delays:
     $$\tau_{\text{total}} = 0.100\text{s} (\text{sensor}) + 0.050\text{s} (\text{comm}) + 0.050\text{s} (\text{decision}) + 0.200\text{s} (\text{actuator}) + 0.050\text{s} (\text{CAN}) = 0.450\text{ s}$$

---

## D. What Remains Assumed

1. **CAN Bus Arbitration & Transmission Delay:**
   - $\tau_{\text{CAN\_assumed}} = 0.050\text{ s}$ (nominal, swept $0.010\text{--}0.250\text{ s}$). Tagged explicitly as `ASSUMED` pending physical CANoe / oscilloscope bus logger measurements on the vehicle J1939 network.
2. **Hydraulic Brake Pressure Buildup Latency:**
   - $\tau_{\text{actuator\_buildup}} = 0.200\text{ s}$. Tagged as `ASSUMED` based on commercial heavy vehicle pneumatic-over-hydraulic spool response curves.
3. **Sensor Perception Processing Latency:**
   - $\tau_{\text{sensor}} = 0.100\text{ s}$. Tagged as `ASSUMED` for camera/LiDAR transmission and temporal filtering window.
4. **Tire-Road Friction Prior Distribution:**
   - Friction values ($\mu_{\text{dry}} = 0.65$, $\mu_{\text{wet}} = 0.35$, $\mu_{\text{slick}} = 0.20$) are based on USBM RI 8757 literature, but have not been measured with a skid trailer or decelerometer on Bailadila iron ore haul roads.
5. **Center of Gravity (CG) Height:**
   - $h_{\text{cg}} = 2.50\text{ m}$ for fully laden truck.
6. **Aerodynamic Drag Coefficient:**
   - $C_d = 0.80$ (blunt body assumption).

---

## E. What Remains Unverified

1. **In-Pit Haul Road Friction on Iron Ore Clay Slurry:**
   - Dynamic tire slip curves ($F_x$ vs slip ratio $\kappa$) on wet Bailadila lateritic iron ore clay under 165-tonne axle loads have not been experimentally measured.
2. **High-Temperature Retarder Brake Thermal Fade:**
   - Thermal cooling rates of the continuous oil-cooled disc brakes during repetitive downhill cycles without auxiliary retarder cooling remain unmodeled.
3. **Physical CAN Bus Jitter Under Heavy Bus Load:**
   - True CAN message jitter and queue latency under $80\%$ bus saturation with broadcast telemetry packets.
4. **Full-Scale Autonomous Actuation Dynamics:**
   - Physical electronic-to-hydraulic proportional valve transfer function on full-scale mining equipment.

---

## F. Equations Used

1. **Longitudinal Force Balance:**
   $$m \frac{dv}{dt} = F_{\text{drive}} + F_{\text{grade}} - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$
2. **Rolling Resistance Force:**
   $$F_{\text{roll}} = C_{rr} \cdot m \cdot g \cdot \cos\theta$$
3. **Aerodynamic Drag Force:**
   $$F_{\text{aero}} = \frac{1}{2} \rho C_d A v^2$$
4. **Grade Force:**
   $$F_{\text{grade}} = m \cdot g \cdot \sin\theta \quad (\theta > 0 \text{ for downhill, } \theta < 0 \text{ for uphill})$$
5. **Effective Deceleration:**
   $$a_{\text{dec}} = \frac{\min(F_{\text{hardware\_max}}, \mu m g \cos\theta) + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}}{m}$$
6. **Stopping Distance:**
   $$S_{\text{stop}}(v) = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
7. **Dynamic Safety Margin:**
   $$S_{\text{margin}}(v) = S_{\text{base}} + k_{\text{comm}} (1 - C_{\text{comm}}) v$$
8. **Stopping-Limited Safe Speed ($v_{\text{stop}}$):**
   $$v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{eff}} + \sqrt{a_{\text{dec}}^2 \tau_{\text{eff}}^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$
   $$\text{where } \tau_{\text{eff}} = \tau_{\text{total}} + k_{\text{comm}} (1 - C_{\text{comm}})$$
9. **Multi-Constraint Safe Speed Solver:**
   $$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$
10. **Dynamic Safe Headway:**
    $$H_{\text{safe}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}} + L_{\text{vehicle}} + S_{\text{base}}$$
11. **Theoretical Kinematic Carrying Capacity:**
    $$C_{\text{kinematic}} = 3600 \cdot \frac{v_{\text{safe}}}{H_{\text{safe}}} \quad [\text{vehicles/hour}]$$

---

## G. Canonical Values & Operating Ranges

| Parameter | Canonical Value | Valid Range | Unit | Classification |
| :--- | :---: | :---: | :---: | :---: |
| Gross Machine Mass ($m$) | 165,500.0 | [150000, 180000] | kg | DERIVED |
| Unladen Tare Mass ($m_{\text{empty}}$) | 74,000.0 | [65000, 80000] | kg | DERIVED |
| Rated Payload ($m_{\text{payload}}$) | 91,500.0 | [85000, 100000] | kg | DERIVED |
| Maximum Mechanical Brake Force ($F_{\text{brake}}$) | 550,000.0 | [450000, 650000] | N | DERIVED |
| Continuous Retarder Power ($P_{\text{retarder}}$) | 1,200,000.0 | [900000, 1500000] | W | DERIVED |
| Rolling Resistance Coefficient ($C_{rr}$) | 0.025 | [0.015, 0.060] | - | DERIVED |
| Drag Coefficient ($C_d$) | 0.80 | [0.60, 1.10] | - | ASSUMED |
| Frontal Projection Area ($A$) | 22.0 | [18.0, 26.0] | m² | DERIVED |
| Standard Gravitational Constant ($g$) | 9.80665 | [9.78, 9.83] | m/s² | VERIFIED |
| Total Autonomous Latency ($\tau_{\text{total}}$) | 0.450 | [0.250, 0.800] | s | DERIVED |
| Assumed CAN Bus Delay ($\tau_{\text{CAN\_assumed}}$) | 0.050 | [0.010, 0.250] | s | ASSUMED |
| Human Driver Reaction Time ($\tau_{\text{human}}$) | 1.200 | [1.000, 2.500] | s | DERIVED |
| Base Standstill Margin ($S_{\text{base}}$) | 5.0 | [3.0, 10.0] | m | DERIVED |
| Site Speed Limit ($v_{\text{mine}}$) | 20.0 (5.56 m/s) | [15.0, 40.0] | km/h | VERIFIED |
| Maximum Ramp Grade ($G_{\text{civil}}$) | $\pm 8.0$ | [-15.0, +15.0] | % | VERIFIED |
| Crusher Service Cycle Time ($t_{\text{crusher}}$) | 200.0 | [150.0, 300.0] | s | VERIFIED |

---

## H. Sensitivity Analysis Results

From `HEMM_SENSITIVITY_ANALYSIS.csv` (evaluated around nominal baseline: $V = 12\text{ m}$, $G_{\text{civil}} = -8\%$, $\mu = 0.35$, $m = 165.5\text{ t}$, $\tau = 0.450\text{ s}$):

| Input Parameter ($X$) | Nominal Value | Elasticity w.r.t $v_{\text{safe}}$ | Elasticity w.r.t $S_{\text{stop}}$ | Elasticity w.r.t $a_{\text{dec}}$ | Key Physical Takeaway |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Reaction Time ($\tau_{\text{total}}$)** | $0.450\text{ s}$ | **$-0.1968$** | **$+0.3109$** | $0.0000$ | $10\%$ increase in reaction time increases stopping distance by $3.11\%$ and reduces safe speed by $1.97\%$. |
| **CAN Delay ($\tau_{\text{CAN\_assumed}}$)** | $0.050\text{ s}$ | **$-0.0219$** | **$+0.0345$** | $0.0000$ | CAN delay accounts for approx. $11\%$ of total latency sensitivity. |
| **Perception Visibility ($V$)** | $12.0\text{ m}$ | **$+1.0283$** | $0.0000$ | $0.0000$ | Safe speed scales directly with perception envelope ($1:1$ sensitivity). |
| **Tire Friction ($\mu$)** | $0.350$ | **$+0.2073$** | **$-0.3920$** | **$+0.4896$** | Friction degradation directly degrades deceleration ($\sim 0.49\%$ per $1\%$ drop in $\mu$). |
| **Civil Grade ($G_{\text{civil}}$)** | $-8.0\%$ | **$-0.1123$** | **$+0.1928$** | **$-0.2796$** | Downhill grade reduces braking deceleration by $0.28\%$ per percentage point. |
| **Gross Vehicle Mass ($m$)** | $165{,}500\text{ kg}$ | **$-0.4695$** | **$+0.8060$** | **$-1.1691$** | Inertia increases stopping distance with an elasticity of $+0.81$. |
| **Rolling Resistance ($C_{rr}$)** | $0.025$ | $+0.0352$ | $-0.0605$ | $+0.0878$ | Rolling resistance provides modest passive braking assistance. |
| **Hardware Brake Force ($F_{\text{brake}}$)** | $550{,}000\text{ N}$ | $+0.3999$ | $-0.6952$ | $+0.9887$ | On high friction surfaces, mechanical brake clamp governs deceleration. |

---

## I. Contradictions Resolved

1. **Grade Sign Ambiguity:** Completely reconciled via bijective `GradeAdapter` ($G_{\text{physics}} = -G_{\text{civil}}$). Tested and verified on $+8\%, +5\%, 0\%, -5\%, -8\%$.
2. **Safe Speed Divergence ($4.382\text{ m/s}$ vs $4.109\text{ m/s}$):** Proven to be the exact analytical root ($4.3815\dots\text{ m/s}$) for a $-8\%$ downhill ramp at $12\text{ m}$ visibility.
3. **Retarder Speed Mistranscription ($92.4\text{ vph}$ vs $92.41\text{ km/h}$):** Traced to Column 10 of `results/monte_carlo_results.csv`; confirmed as a velocity in km/h, not a fleet capacity in vph.
4. **Theoretical Saturation ($700.5\text{ vph}$):** Clearly separated from practical convoy spacing ($180\text{ vph}$) and crusher dumping limit ($18\text{ vph}$).
5. **Transient Queue Flush ($3{,}294\text{ TPH}$):** Identified as an initial condition artifact; steady-state throughput is strictly bound by the crusher ceiling ($1{,}647\text{ TPH}$).
6. **Crusher Ceiling ($1{,}647\text{ TPH}$):** Formalized as an unbreakable physical ceiling for NMDC Deposit 5.
7. **HOLD Policy Delay Conservation:** Reconciled with Little's Law; delay is conserved ($\approx 125\text{ s}$), but relocated spatially away from downhill ramps.
8. **Extreme Fog ($V \le 5\text{ m}$):** Formally enforced as mandatory emergency halt ($v_{\text{safe}} = 0.0\text{ m/s}$, $0\text{ TPH}$).
9. **CAN Latency Classification:** Explicitly relabeled as `ASSUMED` ($\tau_{\text{CAN\_assumed}} = 0.050\text{ s}$).
10. **Double-Stepping in Simulation:** Fully audited and verified with automated invariant tests (`tests/test_simulation_single_timestep.py`).

---

## J. Contradictions Remaining

None within the software and mathematical models.  
*Physical reality gap remains:* Field validation in a live mine is unperformed; assumptions regarding tire friction and CAN bus latency remain pending physical instrumented measurement.

---

## K. Tests Passed

- Full Regression Suite: **769 passed, 1 skipped** (`python -m pytest tests/ -q` in 10.41s).
- 5-Point Grade Monotonicity Suite: **5 passed** (`tests/test_grade_adapter.py`).
- Single Timestep Authority Suite: **4 passed** (`tests/test_simulation_single_timestep.py`).
- Sanity Invariants Suite: **8 passed** (`tests/test_hemm_sanity_invariants.py`).

---

## L. Tests Failed

**0 tests failed.**

---

## M. Physics Limitations

1. **Longitudinal 1-DOF Limitation:**
   - Lateral tire slip, roll angle, load transfer between axles, and yaw stability during emergency braking in curves are simplified to point-mass centrifugal limits ($v_{\text{curve}} = \sqrt{\mu g R}$).
2. **Deterministic Friction Assumption:**
   - Road surface friction is modeled as a constant or Gaussian variable ($\mu \pm \sigma$); localized patches of standing water, loose rocks, or black ice are not captured micro-topographically.
3. **Brake Fade & Thermal Limitations:**
   - The retarder is modeled with a continuous power limit ($1200\text{ kW}$), but thermal buildup over long downhill runs ($> 3\text{ km}$) and hydraulic fade are not dynamically simulated.
4. **Sensor Perception Simplification:**
   - Visibility $V$ is treated as an isotropic scalar perception boundary $R_{\text{effective}}$; non-uniform fog plumes, headlight glare, and dust scattering are abstracted.

---

## N. Field-Validation Requirements

Before this system can be deployed onto physical production dumpers at NMDC Bailadila Deposit 5, the following field validations must be executed:

1. **Instrumented Braking Deceleration Trials (ISO 3450 Annex B):**
   - Measure stopping distance and deceleration of fully laden BEML BH100 dumpers on actual Bailadila haul ramps at $0\%, -5\%$, and $-8\%$ grades using high-precision RTK-GNSS and tri-axial accelerometers.
2. **Tire-Road Skid Resistance Measurement:**
   - Perform continuous friction logging on dry compacted ore, wet ore, and muddy switchback surfaces using an in-situ pendulum tester or dynamic friction trailer.
3. **J1939 CAN Bus Physical Latency Profiling:**
   - Connect a hardware CAN analyzer (CANoe / PEAK-System) to the haul truck CAN bus to measure transmission latency, arbitration delay, and ECU response times under operating engine loads.
4. **Environmental Visibility Sensor Benchmark:**
   - Validate forward perception sensors (optical camera, 77 GHz radar, thermal camera) in actual high-altitude Bailadila monsoon fog banks to ground-truth visibility estimation.

---

# DECISION GATE

### **RESULT: YELLOW**

**Formal Justification:**
The HEMM physics model is mathematically rigorous, fully calibrated across its operating envelope, and free from internal contradictions. Every equation is physically traceable, units are unified to SI, and the simulator timestep authority is strictly singular (no double-stepping).

However, in strict compliance with the **Final Principle** (*Physical Evidence > Derived Model > Engineering Assumption > Simulation Output > Presentation Claim*) and Rule 3/Rule 23 of `AGENTS.md`:
- Important latency parameters ($\tau_{\text{CAN\_assumed}}$, $\tau_{\text{actuator\_buildup}}$) remain engineering assumptions rather than measured values.
- Friction coefficients on Bailadila iron ore clay remain literature-derived.
- Field testing on physical 165-tonne haul trucks has not been executed.

Therefore, declaring **GREEN** at this stage would be scientifically dishonest and would reward test-pass counts over physical evidence. **YELLOW** certifies that the model is mathematically sound and sufficiently defensible to proceed with architecture finalization, while explicitly demarcating the boundary of unmeasured physical assumptions.
