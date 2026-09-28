# STAGE 5 PRE-AUDIT: ARCHITECTURAL BASELINE & BENCHMARK INTEGRITY AUDIT
**SIH 2026-27 — NMDC Bailadila Haulage Fog Stress Problem Statement**  
**Role:** Lead Simulation / Research Engineer, FOG-ORCHESTRATOR 2.0  
**Date:** September 2026  
**Status:** COMPLETE (Pre-Audit Sign-Off)

---

## 1. Executive Context & Objective

In STAGE 4, the root cause of the $2.0 \pm 0.0$ safety violations reported in Stage 3 was forensically isolated and resolved:
- **Root Cause Identified:** Segment boundary transitions from `ROAD_06` ($v_{\text{safe}} = 4.731\text{ m/s}$) to `ROAD_05` ($v_{\text{safe}} = 4.134\text{ m/s}$) where `speed_v` was clamped to the target segment's limit, but `target_speed` remained un-clamped for one simulation tick.
- **Resolution:** Clamped `vehicle.state.target_speed = min(vehicle.state.target_speed, next_spd_limit)` upon edge transitions and in benchmark control loops.
- **Stage 4 Verification:** Over 140 simulation runs across 20 seeds and 4 discrete timesteps ($\Delta t \in \{1.0, 0.5, 0.1, 0.05\}\text{ s}$), **$0.0$ safety violations** were recorded across all 7 levels (except Level 0 unconstrained baseline).

**The STAGE 5 Mandate:**
STAGE 5 is strictly a **productivity retention and fog stress validation sprint**. It is not a feature-development sprint, not an AI-addition sprint, and not a UI redesign sprint. The frozen architecture must be evaluated under the severe low-visibility conditions of NMDC Bailadila (specifically the $3\text{--}5\text{ m}$ severe monsoon visibility regime) to answer the fundamental operational question:
> *"When visibility reduces the safe operating envelope, does FOG-ORCHESTRATOR preserve the maximum physically feasible ore flow instead of unnecessarily stopping or creating uncontrolled queues?"*

---

## 2. Current Implementation Audit

### 2.1 Current Simulator Entry Point
- **Primary Simulator Class:** `MineDigitalTwinSimulator` located in [`fog-orchester-3d-digital-twin/twin/simulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/twin/simulator.py).
- **Core Update Loop Order (Strict Invariant):**
  1. Environment (`set_environmental_conditions`, friction prior, visibility)
  2. Vehicle Dynamics (`vehicle_physics.py`, numerical Euler integration, wheel resistance, retarder, brakes)
  3. Safety Governor (`braking_model.py`, multi-constraint envelope $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$, car-following headway $H_{\text{safe}}$)
  4. Road Capacity (`road_capacity.py`, Greenshields/Pipes kinematic capacity $C_e = \frac{3600 \cdot v_{\text{safe}}}{H_{\text{safe}}}$)
  5. Queue Models (`queue_model.py`, discrete Lindley/M/M/1 node queue update)
  6. Bottleneck Detection (`bottleneck.py`, multi-criteria scoring $S = w_1 \rho + w_2 Q + w_3 C$)
  7. Arrival Rate Shaping (`ArrivalRateShaper`, release interval calculation $\Delta t_{\text{release}} = \frac{3600}{\mu - \delta}$)
  8. Switchback Coordination (`switchback.py`, mutual exclusion slot reservations)
- **Synchronized State Container:** `TwinState` in [`fog-orchester-3d-digital-twin/twin/state.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/twin/state.py).

### 2.2 Current Benchmark Entry Points
- **Stage 4 Entry Point:** [`experiments/run_stage4_benchmark.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_stage4_benchmark.py).
- **Historical Benchmark Scripts:**
  - `experiments/run_stage2_ablation.py`: Evaluated marginal contributions of architectural layers.
  - `experiments/run_stage3_robustness_and_sensitivity.py`: Evaluated 20 seeds across 7 levels with parameter variations.
  - `experiments/run_queue_and_capacity_audit.py`: Verified queue dynamics and road capacity calculations.
- **Stage 5 Master Entry Point:** To be created as [`experiments/run_stage5_productivity_benchmark.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_stage5_productivity_benchmark.py).

### 2.3 Fleet Model
- **Fleet Scale:** Parameterized from $N = 10$ to $N = 50$ haul trucks (`spawn_fleet(num_vehicles)`).
  - *Constraint Notice:* 50-truck operation is strictly **SIMULATION ONLY**. The physical hardware demonstration is explicitly bounded to the two ESP32 prototype units (`TRUCK_01`, `TRUCK_02`) and the LoRa Gateway.
- **Truck Specifications:** CAT 777D equivalent heavy mining truck:
  - Tare Weight: $74,000\text{ kg}$ ($74.0\text{ t}$)
  - Payload: $91,500\text{ kg}$ ($91.5\text{ t}$)
  - Gross Operating Weight: $165,500\text{ kg}$ ($165.5\text{ t}$)
  - Vehicle Length: $10.52\text{ m}$, Width: $6.10\text{ m}$, Height: $5.11\text{ m}$
  - Engine Power: $746\text{ kW}$ ($1000\text{ hp}$)
  - Continuous Retarder Capacity: $1,193\text{ kW}$

### 2.4 Production Calculation
- **Haul Cycle Accounting:** Total tonnes delivered to primary destination nodes (`CRUSHER_01` or `DUMP_01`):
  $$Q_{\text{tonnes}} = \sum_{k=1}^{M} \text{Payload}_k = M \times 91.5\text{ t}$$
- **Hourly Production Rate (TPH):**
  $$\text{Production (TPH)} = \frac{Q_{\text{tonnes}}}{T_{\text{hours}}} = \frac{M \times 91.5}{T_{\text{seconds}} / 3600}$$
- **Throughput in Vehicles per Hour (VPH):**
  $$\text{Throughput (VPH)} = \frac{M}{T_{\text{hours}}}$$

### 2.5 Queue & Capacity Models
- **Queue Model (`QueueModel` in `models/queue_model.py`):**
  - Discrete service mechanism based on node service rate $\mu_{\text{node}}$ (vehicles/hour).
  - Capacitated buffer: $Q(t) \le Q_{\text{max}}$.
  - Departure equation: $D(t) = \min(Q(t) + A(t), \mu \cdot \Delta t)$.
  - Spillback condition: When $Q(t) = Q_{\text{max}}$, incoming vehicles are blocked or held upstream.
- **Road Capacity Model (`RoadCapacityModel` in `models/road_capacity.py`):**
  - Safe stopping distance:
    $$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
    where $\tau_{\text{total}} = \tau_{\text{sensor}} + \tau_{\text{comm}} + \tau_{\text{decision}} + \tau_{\text{act}} = 1.25\text{ s}$.
  - Safe car-following headway:
    $$H_{\text{safe}} = L_{\text{veh}} + S_{\text{margin}} + v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
  - Road Kinematic Capacity:
    $$C_{\text{road}} = \frac{3600 \cdot v_{\text{safe}}}{H_{\text{safe}}}$$

### 2.6 Dispatch & Orchestration Logic
- **Layer 1 (Local Safety Governor):** Autonomous vehicle controller enforcing $v_{\text{command}} \le v_{\text{safe}}$.
- **Layer 2 (Road Capacity Awareness):** Speed advisory constrained by road segment safe speeds.
- **Layer 3 (Local Queue Awareness):** Heuristic queue throttling (e.g. slowing trucks if crusher queue $\ge 3$).
- **Layer 4 (Deterministic MILP Dispatcher - FOG-ORCHESTRATOR):** Receding-horizon deterministic mixed-integer program solving route selection and departure metering ($x_{i, r, k} \in \{0, 1\}$) subject to road capacity and crusher arrival rate limits ($\lambda \le \mu - \delta$), generating **HOLD**, **RELEASE**, **SLOT**, and **DISPATCH** commands.
- **Layer 5 (Chance-Constrained RH-MPC):** Robust stochastic dispatch accounting for friction uncertainty ($\mu \pm 2\sigma$).

### 2.7 Environmental Fog Model
- Configured in `fog-orchester-3d-digital-twin/config/weather.yaml`.
- Modes: `CLEAR` ($R_v = 100\text{ m}$), `MODERATE_FOG` ($R_v = 50\text{ m}$), `HEAVY_FOG` ($R_v = 25\text{ m}$), `DENSE_FOG` ($R_v = 12\text{ m}$), and extreme low-visibility regimes ($R_v = 10\text{ m}, 5\text{ m}, 3\text{ m}$).
- Surface friction degradation: $\mu_{\text{dry}} = 0.65 \to \mu_{\text{wet}} = 0.35 \to \mu_{\text{saturated}} = 0.20$.

### 2.8 Identified Limitations of Previous Stages
1. **Constant Visibility Horizon:** Previous benchmarks ran at fixed visibility ($R_v = 12\text{ m}$) for 300 seconds; dynamic fog transitions (entry, persistence, clearance) were not evaluated in the 20-seed multi-seed suite.
2. **Artificial TPH Saturation at Small Fleet Size:** With $N = 10$ trucks and 300 s horizon, only 2 deliveries occurred during the window, yielding identical $183.0\text{ TPH}$ across L1, L2, L3, L4. True productivity retention divergence occurs when fleet density stresses network capacity ($N = 20, 30, 40, 50$) or during longer dynamic transitions ($1500\text{ s}$).
3. **Flawed Capacity Comparison in Historical Notes:** Comparing 18 VPH arrival rate against 700 VPH road capacity neglected the fact that the crusher service capacity ($\mu = 18\text{ VPH}$) is the binding bottleneck!
4. **Lack of Severe Low-Visibility Evaluation:** $3\text{--}5\text{ m}$ fog conditions were not systematically evaluated for physical feasibility.

---

## 3. Component Boundary & File Modification Plan

### 3.1 Files That Will Remain Untouched (Frozen Architecture)
- [`fog-orchester-3d-digital-twin/twin/network.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/twin/network.py): Network graph topology.
- [`fog-orchester-3d-digital-twin/models/vehicle_physics.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/models/vehicle_physics.py): Core vehicle dynamics.
- [`fog-orchester-3d-digital-twin/models/braking.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/models/braking.py): Safety braking equations and governor.
- [`fog-orchester-3d-digital-twin/models/retarder.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/models/retarder.py): Retarder thermal dissipation model.
- [`fog-orchester-3d-digital-twin/models/switchback.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/models/switchback.py): Switchback mutual exclusion coordinator.
- [`esp32_code/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/): All ESP32 LoRa V2V firmware and protocol definitions.
- [`server/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/server/): Gateway and telemetry ingestion routes.

### 3.2 Files That Will Be Modified / Adapted
- [`fog-orchester-3d-digital-twin/twin/simulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/twin/simulator.py): Only if non-intrusive logging or dynamic weather trajectory support requires extending hooks; preserving all existing invariants.
- [`optimizer/milp_dispatch.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog-orchester-3d-digital-twin/optimizer/milp_dispatch.py): Instrument explicit tracking of HOLD, RELEASE, SLOT, DISPATCH actions.

### 3.3 New Experiment & Deliverable Files to be Created
1. `docs/STAGE5_PRE_AUDIT.md` (This document)
2. `docs/STAGE5_PRODUCTIVITY_METRIC.md`: Formal definition of $PR$ and upper-bound $Q_{\text{fog\_feasible}}$.
3. `docs/STAGE5_CAPACITY_CEILING.md`: Analytical calculation of physical feasibility ceilings.
4. `experiments/run_stage5_productivity_benchmark.py`: Reproducible multi-seed benchmark harness.
5. `docs/STAGE5_PRODUCTIVITY_BENCHMARK.csv`: Aggregated benchmark across fleet sizes and fog conditions.
6. `docs/STAGE5_MULTI_RUN_RESULTS.csv`: Full raw runs across 20 seeds.
7. `docs/STAGE5_STATISTICAL_ANALYSIS.md`: Statistical significance, paired t-tests, confidence intervals.
8. `docs/STAGE5_ABLATION_ANALYSIS.md`: Marginal gain analysis ($L_1 \to L_2 \to L_3 \to L_4$).
9. `docs/STAGE5_ORCHESTRATION_TRACE.csv`: Trace of HOLD/RELEASE/SLOT/DISPATCH commands.
10. `docs/STAGE5_COUNTERFACTUAL_ANALYSIS.md`: Counterfactual evaluation (with vs without HOLD/SLOT).
11. `docs/STAGE5_RECOVERY_ANALYSIS.md`: Post-fog clearance recovery dynamics.
12. `docs/STAGE5_SCIENTIFIC_CONCLUSION.md`: Comprehensive answers to 20 evaluator defense questions.
13. `docs/STAGE5_EVALUATOR_DEFENSE.md`: Hostile evaluator defense scripts.
14. `docs/STAGE5_EXECUTIVE_SUMMARY.md`: Final verdict (GREEN / YELLOW / RED).
15. `docs/STAGE5_TRUTH_TABLE.md`: Final audit of claims.
16. `docs/stage5_figures/`: High-resolution figures illustrating visibility vs speed, capacity, queue, and productivity.

---

## 4. Pre-Audit Sign-Off

The existing codebase is structurally sound. The Stage-4 fix for segment boundary speed clamping holds. All models conform to SI units and the frozen architecture. We proceed immediately to Phase 2: Definition of the Productivity Retention metric and analytical physical capacity ceilings.
