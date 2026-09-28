# FINAL EXECUTIVE SUMMARY & SYSTEM VALIDATION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Safe and Efficient Operation of Mine Vehicles in Fog / Low Visibility

---

FOG-ORCHESTRATOR 2.0 is a prototype decision-and-safety architecture for managing open-pit haulage under fog and low-visibility conditions.

The core engineering mechanism resolves the operational conflict between local collision safety and fleet-scale congestion through a continuous, closed-loop causal chain:

1. **Visibility Changes Vehicle Safe Envelope:** When seasonal fog descends upon an open-pit mine (reducing sightline visibility from $100\text{ m}$ to $12\text{ m}$), Newtonian stopping kinematics dictate that a loaded 165.5-tonne hauler on a steep -8% downhill ramp must drastically reduce its speed ($11.11 \to 5.12\text{ m/s}$ / $40 \to 18.4\text{ km/h}$) to maintain $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$.
2. **Safe Envelope Changes Road Capacity:** Slower travel speeds expand the required space headway ($14.5 \to 22.52\text{ m}$), causing the road corridor's kinematic throughput capacity to collapse ($817.8 \to 450\text{ VPH}$).
3. **Capacity Change Creates Queue / Bottleneck Effects:** When the unregulated arrival demand from loading shovels (e.g., $18.0\text{ trucks/hr}$) exceeds the degraded downhill ramp capacity, multi-truck queues form on the steep incline, exposing haulers to rear-end collision hazards, brake thermal runaway, and primary crusher feed starvation.
4. **Predictor Identifies Emerging Congestion:** The Digital Twin what-if prediction engine continuously projects queue growth 5 minutes ahead, detecting when the Bottleneck Severity Index exceeds $0.3$ before vehicles reach the ramp.
5. **Orchestrator Changes Truck Release / Staging:** Central orchestration intervenes proactively by holding trailing haulers at flat, safe shovel staging bays and issuing metered virtual entry slots ($200\text{ s}$ pacing) matching the primary crusher service cycle.
6. **Local Governor Remains Highest Motion Authority:** An onboard Tier-1 safety governor executing locally on an ESP32 microcontroller continuously computes the analytical stopping quadratic root and clamps all speed commands ($v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$). Central dispatch can NEVER override vehicle safety constraints.

---

## Authoritative Benchmark Findings across 20 Matched Seeds

Evaluated across **20 canonical matched seeds** (101 to 197) over a 2-hour shift simulation (7,200 s) under sustained $12.0\text{ m}$ dense fog with a 6-truck BEML BH100 fleet on a -8% haul ramp:

```
+-----------------------------------------------------------------------------------------------+
| METRIC                       | BASELINE A (L0)  | BASELINE B (L1)  | SYSTEM C (L4 ORCHESTRATED)|
|                              | (Unmanaged)      | (Safety Only)    | (Full FOG-Orchestrator)   |
+-----------------------------------------------------------------------------------------------+
| Safety Invariant Violations  | 12.4 ± 1.1       | 0.0 ± 0.0        | 0.0 ± 0.0 (Zero Modeled)  |
| Completed Loads (2-hr shift) | 25.6 ± 0.5       | 27.3 ± 0.5       | 34.8 ± 0.4 (+35.9% vs L0) |
| Delivered Tonnage (t)        | 2342.4 ± 45.7    | 2498.0 ± 45.7    | 3184.2 ± 36.6 t           |
| Steady Modeled Throughput    | 1171.2 TPH       | 1248.5 TPH       | 1591.4 TPH                |
| Modeled Crusher Utilization  | 71.1%            | 75.8%            | 96.6% of 1647 TPH ceiling |
| Hazardous Ramp Waiting Time  | 860.2 s          | 625.4 s          | 141.6 s (-77.36% vs L1!)  |
| Safe Staging Bay Waiting     | 42.0 s           | 88.2 s           | 489.2 s (Relocated Wait)  |
| Net Total Trip Delay         | 902.2 s          | 713.6 s          | 630.8 s (-11.60% vs L1)   |
| Peak Queue on Slope (trucks) | 7.8 trucks       | 5.8 trucks       | 1.2 trucks                |
| Post-Fog Recovery Time       | 1200.0 s         | 950.0 s          | 180.0 s (5.3x Faster)     |
+-----------------------------------------------------------------------------------------------+
```

### Strict Baseline-Specific Comparisons:

- **Baseline B (L1 Safety Only) $\longrightarrow$ System C (L4 Orchestration):**
  - **Hazardous Ramp Waiting:** Reduced from **$625.4\text{ s}$ to $141.6\text{ s}$** (**77.36% reduction**, $t = 58.02$, $p = 1.50 \times 10^{-31}$, Cohen's $d = 10.59$).
  - **Modeled Delivered Throughput:** Increased from **$1248.5\text{ TPH}$ to $1591.4\text{ TPH}$** (**+27.46% increase relative to L1**).
  - **Net Total Trip Delay:** Reduced from **$713.6\text{ s}$ to $630.8\text{ s}$** (**11.60% net reduction**, $t = 5.82$, $p = 1.42 \times 10^{-5}$).
- **Baseline A (L0 Unmanaged) $\longrightarrow$ System C (L4 Orchestration):**
  - **Modeled Delivered Throughput:** Increased from **$1171.2\text{ TPH}$ to $1591.4\text{ TPH}$** (**+35.88% increase relative to L0**).
  - **Crusher Pocket Utilization:** Increased from **71.1% to 96.6%** of the $1647.0\text{ TPH}$ physical crusher service ceiling.
- **Safety Stress Testing:**
  - **10,000 Monte Carlo Trials:** Zero violations of the defined safety invariant were observed across the 10,000 modeled scenarios ($v_{\text{command}} \le v_{\text{safe}}$ and $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$).

---

## Hardware-in-the-Loop (HIL) & Physical Evidence Separation

The project explicitly maintains transparency regarding physical bench vs HIL vs simulated evidence:

1. **Class A — Physical Bench Evidence:**
   - **ESP32 Firmware Execution:** Dual-core FreeRTOS deterministic task timing ($T_{\text{governor}} = 2.20\text{ ms}$, $T_{\text{sensor}} = 1.26\text{ ms}$).
   - **SX1278 LoRa Link:** 99.1% packet delivery ratio (PDR) measured over $150\text{ m}$ outdoor line-of-sight bench testbed; $41.2\text{ ms}$ roundtrip ping-pong latency. (Valid in outdoor LOS bench; does not imply mine-wide pit coverage).
   - **TWAI / CAN 2.0B Controller:** 250 kbps ISO 11898-1 framing with 29-bit extended IDs; $0.512\text{ ms}$ wire propagation time.
2. **Class B — Hardware-in-the-Loop (HIL) Evidence:**
   - **Command-Path Latency:** Characterized at **216.05 ms median** under the configured actuator model ($13.81\text{ ms}$ physical bench electronics + $202.24\text{ ms}$ modeled electro-pneumatic actuator build-up lag).
   - **Operator In-Cab HUD Bridge:** Headless bridge serializing live safety envelopes, alarms, and communication states in $0.93\text{ ms}$.
   - **J1939-Style Protocol:** 6 project-defined J1939-compatible PGNs decoded over TWAI.
3. **Class C — Simulation Evidence:**
   - 20-seed haulage benchmark, queue redistribution, what-if prediction, and Monte Carlo safety evaluations.
4. **Class D — Analytical Derivations:**
   - First-principles longitudinal force balance, quadratic safe speed derivation, and $1647.0\text{ TPH}$ crusher service ceiling.

---

## Formal System Verdict

$$\mathbf{FINAL\ SYSTEM\ VERDICT:}\quad \mathbf{CLOSED\ WITH\ LIMITATIONS}$$

FOG-ORCHESTRATOR 2.0 demonstrates an integrated, physics-constrained orchestration architecture for open-pit haulage under fog/low-visibility conditions. The architecture couples vehicle physics, safe speed envelopes, road capacity, queue propagation, prediction, and proactive fleet staging while preserving local vehicle safety authority.

**Physical Field Boundary:** Brake dynamics were represented through analytical and HIL models; physical brake actuation on a production mining truck and factory OEM ECU integration remain future validation work.
