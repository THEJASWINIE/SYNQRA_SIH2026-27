# FOG-ORCHESTRATOR 2.0 — FINAL CLAIM FREEZE (PHASE 7.3.3)
**Competition:** Smart India Hackathon (SIH 2026-27)  
**Problem Statement:** SIH26007 — Safe and Efficient Operation of Mine Vehicles in Fog and Low-Visibility Conditions in Open Cast Iron Ore Mines  
**Reference Machine:** BEML BH100 Rigid Rear Dump Truck (100-Tonne Class)  
**Reference Site:** NMDC Bailadila Iron Ore Mine, Deposit 5, Bacheli Complex, Chhattisgarh  
**Model Freeze Status:** **LOCKED & CANONICAL**  

---

## 1. Executive Authority & Classification Standard
This document establishes the definitive, legally and scientifically defensible claim boundaries for FOG-ORCHESTRATOR 2.0.  
All claims are partitioned into four strict evidence categories:
- **GREEN:** Demonstrated and verified within prototype, laboratory hardware bench, and deterministic simulation scope. Ready for evaluation and skeptical questioning.
- **YELLOW:** Supported by engineering theory, standards, and surrogate hardware testing, but dependent on uncalibrated on-chassis machine parameters.
- **OPEN:** Requires live field trials on physical BEML BH100 haul trucks at Bailadila to eliminate remaining uncertainties.
- **RED:** Disproven, mathematically invalid, or misleading claims that are permanently retracted.

---

## 2. Definitive Frozen Claims

```
========================================================================================
                                   CLAIM FREEZE MATRIX
========================================================================================

  [GREEN] DEMONSTRATED WITHIN PROTOTYPE / BENCH / SIMULATION SCOPE:
  --------------------------------------------------------------------------------------
  * Emergency Deceleration Derivation:
      Derived from first-principles longitudinal force balance on -8% ramp.
      Canonical: 2.7856 m/s² (165.5t GVW, Crr=0.025, g=9.80665 m/s²).
      Legacy Simulation: 2.7466 m/s² (165.0t GVW, Crr=0.020, g=9.81 m/s²).
      Clamped by tire-road adhesion limit (566.2 kN on wet hematite mu=0.35).
  * Brake Force Clarification:
      550,000 N is Total Gross Mechanical Rim Braking Force at the tire-road interface,
      not caliper normal clamping force.
  * Two-State Safety Model:
      State 1 (Moving v>0): S_stop(v) + S_base <= R_effective  ==>  M_travel >= 0.
      State 2 (Staged v=0): Forward S_stop == 0m, line-of-sight clearance D_sight = R_eff.
      Resolves dense fog (3-5m) margin semantics without false violation errors.
  * Dense Fog Controlled Staging:
      At visibility <= 5.0m, v_safe = 0.0000 m/s (Controlled Staging / Hold).
      Modeled road flow is strictly 0.0 TPH / 0.0 VPH during blindout.
  * Independent Safe Speed Quadratic Root:
      At 12m visibility with P99 latency (tau = 437.1 ms):
      Emergency (a = 2.7466 m/s²): v_safe = 5.1158 m/s (18.42 km/h), S_stop = 7.0004 m.
      Service (a = 1.2000 m/s²):   v_safe = 3.6078 m/s (12.99 km/h), S_stop = 7.0000 m.
  * Space Headway & Road Flow:
      Space headway at 12m = 22.5200 m (S_stop 7.0m + S_margin 5.0m + Length 10.52m).
      Theoretical kinematic road flow = 817.8 VPH (emergency) / 587.2 VPH (service).
  * Modeled Crusher Ceiling:
      Single tipping pocket bottleneck ceiling = 1,647.0 TPH (200s cycle x 91.5t).
  * Delivered Steady-State Production:
      Level 4 dynamic staging delivers 1,591.4 TPH (96.6% crusher utilization) across
      1800s, 3600s, and 7200s horizons with initial warmup discarded.
  * Baseline Throughput Comparison:
      Level 4 achieves +35.88% (+35.9%) throughput over uncoordinated Level 0 (1,171.2 TPH)
      under identical routes, fleet, weather, seeds, and crusher models.
  * Hazardous Ramp Queue Relocation:
      Ramp queue waiting reduced by -77.36% (625.4s -> 141.6s) by holding trucks in
      safe shovel staging areas (+401.0s).
  * Net Cycle Delay Reduction & Causality:
      Net round-trip cycle delay reduced by -11.60% (-82.8s, 713.6s -> 630.8s),
      causally proven by the elimination of ramp stop-start accordion waves (4.8 -> 0.9 stops).
  * Safety Invariant:
      v_command_actual <= v_safe held with zero violations across 1,200 fault injection trials.
  * V2V Hardware Bench Timing:
      Dual-ESP32 SX1278 CSS-LoRa bench achieved mean 41.2 ms, P99 48.6 ms, 99.1% PDR.
  * Gateway Relay Timing:
      ESP32 gateway serial-to-WiFi relay bench achieved mean 82.4 ms, P99 105.2 ms.
  * BEML BH100 OEM Geometry:
      Tare 74.0t, rated payload 91.5t, GVW 165.5t, length 10.52m, width 5.52m, tire 1.35m.

  [YELLOW] SUPPORTED BY LITERATURE / SURROGATE BENCH / SIMULATION:
  --------------------------------------------------------------------------------------
  * BH100 Brake Actuation Lag:
      Modeled as 250.0 ms nominal, 350.0 ms worst-case based on pneumatic fill literature.
      Supported by automotive electro-hydraulic surrogate bench (mean 200.16 ms, P99 237.1 ms).
  * Service Deceleration Limit:
      1.2000 m/s² haulage literature comfort limit to prevent rock spillage.
  * DSSS Spreading Gain:
      +12.0 dB processing gain demonstrated via mathematical simulation model.
  * Haul Road Rolling Resistance:
      Crr = 0.025 (SME Mining Engineering Handbook unpaved road baseline).

  [OPEN] REQUIRES PHYSICAL FIELD VALIDATION AT BAILADILA DEPOSIT 5:
  --------------------------------------------------------------------------------------
  * Live BEML BH100 Deceleration:
      Physical decelerometer runs on loaded BH100 descending -8% ramp at Deposit 5.
  * Live J1939 Bus Telemetry:
      Chassis harness tap on BH100 to verify actual PGN broadcast rates and latencies.
  * Pit Topographic RF Propagation:
      Field RF multipath, shadowing over iron ore benches, and hematite dust attenuation.

  [RED] PERMANENTLY RETRACTED CLAIMS:
  --------------------------------------------------------------------------------------
  * 74,828.7 TPH Headline:
      RETRACTED. Single-lane kinematic pipe flow cannot be equated to mine production.
  * 3,294.0 TPH & 2,745.0 TPH Production Bursts:
      RETRACTED. Transient initial queue flushes cannot be annualized as production.
  * "77.4% Total Waiting Reduction":
      RETRACTED. Relocation of queueing reduces ramp wait by 77.4%; net delay cut is 11.6%.
  * "100% Real-World Safety":
      RETRACTED. Clamping guarantees mathematical safety; mechanical/geotechnical edge
      cases require physical field validation.
  * "Bailadila Field Validated":
      RETRACTED. Replaced with "Bailadila Site-Calibrated Simulation & Bench Prototype".
========================================================================================
```

---

## 3. Canonical Number Sheet

| Metric | Canonical Value | Unit | Status |
|:---|:---:|:---:|:---:|
| **Gross Operating Mass (GVW)** | $165,500.0$ | $\text{kg}$ ($165.5\text{ t}$) | **GREEN** |
| **Gross Rim Braking Force** | $550,000.0$ | $\text{N}$ ($550\text{ kN}$) | **GREEN** |
| **Emergency Deceleration (Canonical)** | $2.7856$ | $\text{m/s}^2$ | **GREEN** |
| **Emergency Deceleration (Legacy)** | $2.7466$ | $\text{m/s}^2$ | **GREEN** |
| **Service Deceleration** | $1.2000$ | $\text{m/s}^2$ | **YELLOW** |
| **Local P99 Reaction Latency** | $0.4371$ | $\text{s}$ ($437.1\text{ ms}$) | **GREEN** |
| **Emergency Safe Speed @ 12m** | $5.1158$ ($18.42$) | $\text{m/s}$ ($\text{km/h}$) | **GREEN** |
| **Service Safe Speed @ 12m** | $3.6078$ ($12.99$) | $\text{m/s}$ ($\text{km/h}$) | **GREEN** |
| **Stopping Distance @ 12m (Emergency)** | $7.0004$ | $\text{m}$ | **GREEN** |
| **Stopping Distance @ 12m (Service)** | $7.0000$ | $\text{m}$ | **GREEN** |
| **Standstill Safety Margin** | $5.0000$ | $\text{m}$ | **GREEN** |
| **Safe Space Headway @ 12m** | $22.5200$ | $\text{m}$ | **GREEN** |
| **Kinematic Road Flow (Emergency)** | $817.8$ | $\text{VPH}$ | **GREEN** |
| **Kinematic Road Flow (Service)** | $587.2$ | $\text{VPH}$ | **GREEN** |
| **Modeled Crusher Ceiling** | $1,647.0$ | $\text{TPH}$ | **GREEN** |
| **Steady-State Production (L4)** | $1,591.4$ | $\text{TPH}$ | **GREEN** |
| **Baseline Production (L0)** | $1,171.2$ | $\text{TPH}$ | **GREEN** |
| **Throughput Improvement (L4 vs L0)** | **+35.88% (+35.9%)** | $\%$ | **GREEN** |
| **Hazardous Ramp Queue Reduction** | **-77.36%** | $\%$ | **GREEN** |
| **Net Round-Trip Delay Reduction** | **-11.60% (-82.8s)** | $\%$ ($\text{s}$) | **GREEN** |
| **Safety Invariant Violations** | **0 / 1,200** | count | **GREEN** |
| **Monte Carlo Safety Violations** | **0 / 10,000** | count | **GREEN** |
| **Dense Fog Speed ($\le 5\text{m}$)** | **0.0000** | $\text{m/s}$ (HOLD) | **GREEN** |
| **Dense Fog Modeled Throughput** | **0.0** | $\text{TPH}$ | **GREEN** |

---

## 4. Final Hard Truth

### The Single Most Important Remaining Physical Assumption:
> **The effective pneumatic-over-hydraulic pressure build-up latency of the BEML BH100 brake control valves under low ambient operating temperatures and extended service wear, currently assumed as $\tau_{\text{actuator}} = 250\text{ ms}$ (nominal) / $350\text{ ms}$ (worst-case).**

### The Exact Field Experiment Required to Eliminate It:
> **Instrument a production BEML BH100 dump truck at NMDC Bailadila Deposit 5 with a calibrated pressure transducer tapped directly into the wheel brake lines (or auxiliary test ports) and a high-speed CAN bus data logger. Record the precise time interval between the electronic transmission of the brake actuation command on the J1939 bus and the achievement of $90\%$ rated hydraulic pressure ($P_{\text{line}} \ge 12.5\text{ MPa}$) across 50 full-stop brake applications at $-8\%$ ramp grade.**
