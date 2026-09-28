# FINAL AUTHORITATIVE PRESENTATION NUMBERS & DEFENSE CHEATSHEET
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Single Source of Truth for Evaluator Presentations, Slides, Research Papers & Viva

---

## 1. Core Heavy Vehicle & Ramp Geometry Numbers

| Parameter | Authoritative Value | Physical Unit | Provenance / Evidence Level | Presentation Usage & Defense Notes |
|---|---|---|---|---|
| **Gross Vehicle Weight (Loaded)** | **165,500** | kg (165.5 t) | `CLASS_D` (OEM Documented) | BEML BH100 datasheet: 74.0 t tare mass + 91.5 t rated nominal payload. |
| **Tare Mass (Empty)** | **74,000** | kg (74.0 t) | `CLASS_D` (OEM Documented) | Unladen rock body with standard ROPS/FOPS cabin. |
| **Rated Ore Payload** | **91,500** | kg (91.5 t) | `CLASS_D` (OEM Documented) | Standard volumetric hopper capacity per hauling cycle. |
| **Haul Truck Length** | **10.525** | m | `CLASS_D` (OEM Documented) | Overall bumper-to-bumper vehicle length used in headway calculations. |
| **Haul Truck Width** | **5.920** | m | `CLASS_D` (OEM Documented) | Overall operating width across dual rear drive tires. |
| **Drive Tire Rolling Radius** | **1.450** | m | `CLASS_D` (OEM Documented) | 27.00-R49 mining haulage radial tire static loaded radius. |
| **Canonical Ramp Gradient** | **-0.08** | (-8.0% slope) | `CLASS_D` (NMDC Survey) | NMDC Bailadila Deposit-5 main haul ramp civil survey. (Negative = Downhill). |
| **Rolling Resistance ($C_{\text{rr}}$)** | **0.025** | dimensionless | `CLASS_D` (Literature) | Compacted hematite gravel/crushed rock haul road standard. |
| **Nominal Friction ($\mu$)** | **0.35** | dimensionless | `CLASS_D` (Assumption) | Conservative low-friction engineering assumption for compacted haul roads. |
| **Wet Slurry Friction ($\mu_{\text{wet}}$)**| **0.30** | dimensionless | `CLASS_D` (Literature) | Degraded wet haul road surface with fine hematite slurry. |
| **Severe Mud Friction ($\mu_{\text{mud}}$)** | **0.25** | dimensionless | `CLASS_D` (Assumption) | Worst-case monsoon mud slick sensitivity test point. |
| **Rated Brake Mechanical Force** | **550,000** | N (550 kN) | `CLASS_D` (Derivation) | Reverse-derived from ISO 3450 stopping criteria on 165.5 t GVM. |

---

## 2. Deceleration & Stopping Kinematics (Reconciled Values)

| Parameter | Authoritative Value | Physical Unit | Provenance | Presentation Usage & Defense Notes |
|---|---|---|---|---|
| **Canonical Emergency Decel** | **2.7856** | $\text{m/s}^2$ | `CLASS_D` (Analytical) | Net deceleration on -8% ramp under 550 kN braking force ($165.5\text{ t}$, $C_{\text{rr}}=0.025$). |
| **Legacy Emergency Decel** | **2.7466** | $\text{m/s}^2$ | `CLASS_D` (Analytical) | Legacy derived value ($165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81$) retained in baseline tests. |
| **Service Deceleration Ceiling**| **1.2000** | $\text{m/s}^2$ | `CLASS_D` (Assumption) | Operator comfort and ore spillage prevention limit during non-emergency braking. |
| **Defensive Standstill Buffer** | **5.0** | m | `CLASS_D` (Assumption) | $S_{\text{base}} = 5.0\text{ m}$ (half truck length clear safety margin to obstacle). |
| **Dense Fog Safe Speed (12m vis)**| **5.12** (18.4) | $\text{m/s}$ (km/h) | `CLASS_D` (Analytical) | Analytical root of stopping envelope at $R_v = 12.0\text{ m}$ with $\tau = 0.4371\text{ s}$. |
| **Stopping Distance at 5.12 m/s**| **6.94** | m | `CLASS_D` (Analytical) | Reaction distance: $2.24\text{ m}$ + Mechanical braking distance: $4.70\text{ m}$. |
| **Dense Fog Space Headway** | **22.52** | m | `CLASS_D` (Analytical) | $H = S_{\text{stop}} (6.94\text{m}) + S_{\text{base}} (5.00\text{m}) + L_{\text{truck}} (10.53\text{m}) = 22.52\text{ m}$. |
| **Blindout Halting Boundary** | **5.0** | m | `CLASS_D` (Analytical) | At $R_v \le 5.0\text{ m}$, $v_{\text{safe}} = 0.00\text{ m/s}$ (Mandatory controlled vehicle halt). |

---

## 3. Crusher Intake & Mining Capacity Barriers

| Parameter | Authoritative Value | Physical Unit | Provenance | Presentation Usage & Defense Notes |
|---|---|---|---|---|
| **Primary Crusher Dump Cycle** | **200.0** | s/truck | `CLASS_D` (Operational) | Single gyratory pocket positioning, tipping, and clearing cycle. |
| **Crusher Modeled Service Ceiling**| **1,647.0** | TPH | `CLASS_D` (Analytical) | $(3600\text{ s} / 200\text{ s}) \times 91.5\text{ t} = 18\text{ dumps/hr} \times 91.5\text{ t} = 1647.0\text{ TPH}$. Upper physical intake barrier. |
| **Theoretical Emergency Road Flow** | **817.8** | VPH | `CLASS_D` (Analytical) | Kinematic pipe flow ($3600 \times 5.12 / 22.52$). ROAD FLOW ONLY. NOT mine production TPH! |
| **Theoretical Service Road Flow** | **587.2** | VPH | `CLASS_D` (Analytical) | Kinematic pipe flow under $1.2\text{ m/s}^2$ service decel ceiling. ROAD FLOW ONLY. NOT mine TPH! |
| **Transient Flush Rate (Retracted)**| **3,294.0** | TPH | `CLASS_C` (Artifact) | 6 pre-buffered trucks dumped in 10 min. Retracted as an unsustainable transient! |

---

## 4. 20-Seed Master Benchmark Statistical Results (L0 vs L1 vs L4)

Evaluated across **20 matched seeds** over a 2-hour shift (7,200 s) in 12m fog on a -8% ramp with 6 x BEML BH100 trucks:

| Evaluated Metric | Baseline A (L0)<br>*(Unmanaged)* | Baseline B (L1)<br>*(Safety Only)* | System C (L4)<br>*(FOG-Orchestrator)* | Delta vs L1<br>*(Orchestration Gain)* | Statistical Significance |
|---|---|---|---|---|---|
| **Safety Invariant Violations** | 12.4 ± 1.1 | **0.0 ± 0.0** | **0.0 ± 0.0** | 0.0 (Zero Modeled Violations) | Defined safety invariant maintained |
| **Hazardous Ramp Waiting (s)** | 860.2 s | 625.4 s | **141.6 s** | **-483.8 s (-77.36%)** | $t = 58.02$, $p = 1.50 \times 10^{-31}$, $d = 10.59$ |
| **Safe Staging Bay Waiting (s)** | 42.0 s | 88.2 s | **489.2 s** | +401.0 s (Relocated) | Waiting shifted from slope to flat bench |
| **Net Total Trip Delay (s)** | 902.2 s | 713.6 s | **630.8 s** | **-82.8 s (-11.60%)** | $t = 5.82$, $p = 1.42 \times 10^{-5}$, $d = 1.30$ |
| **Modeled Throughput (TPH)** | 1171.2 TPH | 1248.5 TPH | **1591.4 TPH** | **+342.9 TPH (+27.46%)** | vs L0 Baseline: **+420.2 TPH (+35.88%)** |
| **Crusher Pocket Utilization** | 71.1% | 75.8% | **96.6%** | **+20.8% Utilization** | Paces haulers to 1647 TPH ceiling |
| **Peak Queue on Ramp (trucks)** | 7.8 trucks | 5.8 trucks | **1.2 trucks** | **-4.6 trucks (-79.3%)** | Reduces hazardous queue on slope by 79.3% |
| **Post-Fog Recovery Time (s)** | 1200.0 s | 950.0 s | **180.0 s** | **-770.0 s (5.3x Faster)** | Rapid fleet flow resynchronization |

---

## 5. Hardware Timing & Communication Benchmarks

| Metric / Parameter | Authoritative Value | Classification | Evidence Class | Defense Statement |
|---|---|---|---|---|
| **SX1278 LoRa Packet Delivery** | **99.1%** | Measured | `CLASS_A` (Physical Bench) | 1,000 packets over 150m outdoor LOS bench testbed at 433 MHz. Does NOT imply pit-wide reliability. |
| **LoRa Roundtrip Ping-Pong** | **41.2 ms** | Measured | `CLASS_A` (Physical Bench) | Over-the-air RF roundtrip transmission and acknowledgment on bench. |
| **CAN / TWAI Bus Wire Delay** | **0.512 ms** | Measured | `CLASS_A` (Physical Bench) | ESP32 TWAI peripheral at 250 kbps with 29-bit extended frames. |
| **Electronic Command Path** | **13.81 ms** | Measured | `CLASS_A` (Physical Bench) | $1.26\text{ ms (Sensor)} + 2.20\text{ ms (Governor)} + 10.35\text{ ms (CAN wire/process)}$. |
| **HIL Command-Path Latency** | **216.05 ms** (P50) | Characterized | `CLASS_B` (HIL) | $13.81\text{ ms}$ physical bench electronics + $202.24\text{ ms}$ modeled actuator lag. NOT physical brake response. |
| **Worst-Case Safety Budget ($\tau$)**| **437.1 ms** (0.437 s) | Budgeted | `CLASS_D` (Analytical) | P99 conservative latency ceiling used in stopping distance quadratic root. |
