# PHASE 7.3.3 — FINAL PARAMETER EVIDENCE MATRIX
**Module:** Evidence Classification & Provenance Tracking  
**Dataset:** `data/final_evidence_matrix.csv`  
**Standard:** PART 3 Provenance Architecture  
**Status:** FROZEN & TRACEABLE

---

## 1. Classification Methodology (Section 18 & 19)
Under the non-negotiable rules of Phase 7.3.3:
- **GREEN:** Equations are internally consistent, parameters are backed by traceable evidence (OEM, standard, or bench measurement), results are reproducible, and claim wording strictly matches the verified scope.
- **YELLOW:** Supported by credible engineering assumptions, literature, or surrogate bench hardware, but lacks on-chassis mining validation.
- **OPEN:** Requires physical field trials on a live BEML BH100 haul truck inside NMDC Bailadila Deposit 5 to eliminate remaining uncertainties.
- **RED:** Retracted, disproven, or mathematically invalid claims.

---

## 2. Complete 25-Parameter Master Evidence Matrix

| Domain | Parameter Name | Canonical Value | Status | Evidence Category | Empirical Source / Justification |
|:---|:---|:---:|:---:|:---|:---|
| **VEHICLE** | Tare Machine Mass | $74,000\text{ kg}$ | **GREEN** | OEM_REFERENCE | BEML BH100 Technical Specification Sheet |
| **VEHICLE** | Nominal Payload | $91,500\text{ kg}$ | **GREEN** | OEM_REFERENCE | BEML BH100 100-Tonne Class Rated Payload |
| **VEHICLE** | Gross Vehicle Weight | $165,500\text{ kg}$ | **GREEN** | OEM_REFERENCE | Sum of tare ($74.0\text{ t}$) and payload ($91.5\text{ t}$) |
| **VEHICLE** | Vehicle Length | $10.52\text{ m}$ | **GREEN** | OEM_REFERENCE | BEML BH100 Dimensional Drawing |
| **VEHICLE** | Vehicle Width | $5.52\text{ m}$ | **GREEN** | OEM_REFERENCE | BEML BH100 Dimensional Drawing |
| **VEHICLE** | Tire Rolling Radius | $1.35\text{ m}$ | **GREEN** | OEM_REFERENCE | Bridgestone 27.00R49 E-4 Mining Radial Catalog |
| **PHYSICS** | Gross Rim Braking Force | $550,000\text{ N}$ | **GREEN** | DERIVED_MODEL | Rated longitudinal braking force clamped by tire adhesion ($566.2\text{ kN}$) |
| **PHYSICS** | Emergency Deceleration | $2.7856\text{ m/s}^2$ | **GREEN** | DERIVED_MODEL | First-principles longitudinal force balance on $-8\%$ ramp ($165.5\text{ t}$) |
| **PHYSICS** | Legacy Model Decel | $2.7466\text{ m/s}^2$ | **GREEN** | DERIVED_MODEL | Exact derivation for legacy parameters ($165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81$) |
| **PHYSICS** | Measured BH100 Decel | **UNAVAILABLE** | **OPEN** | FIELD_UNVALIDATED | On-truck decelerometer trials at Bailadila not yet conducted |
| **PHYSICS** | Service Deceleration | $1.2000\text{ m/s}^2$ | **YELLOW** | ASSUMED | Haulage literature comfort standard to prevent rock spillage |
| **SAFETY** | Standstill Safety Margin | $5.0000\text{ m}$ | **GREEN** | STANDARD | DGMS Metalliferous Mines Standoff Standard |
| **SAFETY** | Emergency Safe Speed @ 12m | $5.1158\text{ m/s}$ | **GREEN** | DERIVED_MODEL | Quadratic closed-form root under P99 latency and $a_{\text{emerg}}$ |
| **SAFETY** | Service Safe Speed @ 12m | $3.6078\text{ m/s}$ | **GREEN** | DERIVED_MODEL | Quadratic closed-form root under P99 latency and $a_{\text{service}}$ |
| **SAFETY** | Dense Fog Speed ($\le 5\text{m}$) | **0.0000 m/s** | **GREEN** | DERIVED_MODEL | Two-State Safety Model: Controlled Staging / Hold |
| **TIMING** | SX1278 CSS-LoRa V2V Latency| Mean $41.2\text{ ms}$, P99 $48.6\text{ ms}$ | **GREEN** | BENCH_MEASURED | Direct physical dual-ESP32 SX1278 hardware bench trials |
| **TIMING** | Gateway Serial-to-WiFi | Mean $82.4\text{ ms}$, P99 $105.2\text{ ms}$ | **GREEN** | BENCH_MEASURED | Physical hardware ESP32 gateway to FastAPI relay bench |
| **TIMING** | Controller Decision Loop | $< 5.0\text{ ms}$ (at 20 Hz loop) | **GREEN** | BENCH_MEASURED | CPU profiling of Tier-1 safety solver |
| **TIMING** | Surrogate Actuator Bench | Mean $200.16\text{ ms}$, P99 $237.1\text{ ms}$ | **YELLOW** | SURROGATE_BENCH | Automotive electro-hydraulic surrogate test rig |
| **TIMING** | BH100 Actuator Model | $250.0\text{ ms}$ (nominal) / $350.0\text{ ms}$ (worst) | **YELLOW** | ASSUMED | Heavy dumper pneumatic fill lag model |
| **COMM** | DSSS / Gold Code Gateway | $+12.0\text{ dB}$ processing gain | **YELLOW** | SIMULATION_MODEL | Mathematical spreading simulation model (no FPGA hardware) |
| **COMM** | Real Bailadila RF Topo | Topographic shadowing | **OPEN** | FIELD_UNVALIDATED | Real pit multipath and shadowing at Bailadila unmeasured |
| **CHASSIS** | Real BH100 CAN / J1939 | PGN 61444, 65265 | **OPEN** | FIELD_UNVALIDATED | Chassis bus tap on BEML BH100 pending NMDC pit clearance |
| **FLEET** | Sustained Steady-State TPH | $1,591.4\text{ TPH}$ | **GREEN** | SIMULATION_BENCHMARK | Continuous multi-horizon simulation with warmup discarded |
| **FLEET** | Modeled Crusher Ceiling | $1,647.0\text{ TPH}$ | **GREEN** | DERIVED_MODEL | Single pocket $200\text{ s}$ dump cycle ceiling ($18\text{ VPH} \times 91.5\text{ t}$) |

---

## 3. Explicit Retraction of Unjustified Claims
1. **No Real-World Claims:** Never claim "field validated at Bailadila" — all Bailadila figures are simulation models or literature calibrations.
2. **No Real BH100 Brake Telemetry:** Measured brake pressures are labeled **FIELD_UNVALIDATED / OPEN**.
3. **No Hardware DSSS:** DSSS is an architectural simulation model; physical radio bench testing used commercial Semtech SX1278 CSS-LoRa modules.
