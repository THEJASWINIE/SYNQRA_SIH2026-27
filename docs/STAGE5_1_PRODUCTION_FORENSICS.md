# STAGE 5.1: PRODUCTION BENCHMARK FORENSIC AUDIT
**Authoritative Architectural & Mathematical Dissection of Stage 5 Throughput Claims**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Haulage)  
**Status:** FORENSIC AUDIT COMPLETE — ROOT CAUSES IDENTIFIED

---

## 1. Executive Forensic Summary

The Stage-5 benchmark report presented four claims that appear physically contradictory:
1. At $3\text{--}5\text{ m}$ visibility, safe speed $v_{\text{safe}} = 0\text{ m/s}$ under Tier-1 braking constraints.
2. Under dynamic fog stress ($100\text{ m} \to 3\text{ m}$), FOG-Orchestrator reported $1,647.0\text{ TPH}$.
3. Fog-feasible capacity was reported as exactly $1,647.0\text{ TPH}$.
4. Productivity retention ($\text{PR}$) was reported as $100.0\%$.
5. Baseline methods (Safety-Only, Safety-Capacity, Safety-Capacity-Queue, FOG-Orchestrator, Chance-MPC) all reported identical throughput of $1,647.0\text{ TPH}$.

**Forensic Finding:**  
The reported $1,647.0\text{ TPH}$ is **NOT** a steady-state measurement of mine haulage throughput under severe fog. It is the mathematical artifact of a **three-fold simulation and modeling coupling**:
1. **The Spawning Location & Pre-Loading Artifact:** In `twin/simulator.py`, vehicles were initialized across `["SHOVEL_01", "SHOVEL_02", "BUFFER_01"]` with interleaved loading status. Two trucks (`TRUCK_003` and `TRUCK_009`) were spawned **already loaded at `BUFFER_01`**, merely $240\text{--}260\text{ m}$ from `CRUSHER_01`. These trucks dumped within the first $50\text{ s}$ of the run ($2 \times 91.5\text{ t} = 183.0\text{ t}$).
2. **The 3,150 m Physical Haul Window vs Short Horizon:** A genuine haul from `SHOVEL_01` to `CRUSHER_01` spans $3,150\text{ m}$. At fog-constrained speeds ($v \approx 4.8\text{ m/s}$ at $12\text{ m}$ visibility), one-way travel alone requires $658\text{ s}$, plus $240\text{ s}$ loading. Over the $600\text{ s}$ benchmark window, only one truck (`TRUCK_005` from `SHOVEL_02`, which started empty/loading during the initial clear weather $t < 300\text{ s}$) ever reached the crusher before dense fog halted or drastically slowed the remaining fleet ($1 \times 91.5\text{ t} = 91.5\text{ t}$).
3. **The Numerical Coincidence:** $183.0\text{ t} + 91.5\text{ t} = 274.5\text{ t}$. Over $600\text{ s}$ ($1/6\text{ hour}$), $274.5\text{ t} / (1/6\text{ h}) = \mathbf{1,647.0\text{ TPH}}$. Simultaneously, the primary crusher service rate in the code was modeled as $18.0\text{ VPH} \times 91.5\text{ t} = \mathbf{1,647.0\text{ TPH}}$ (note that $18\text{ VPH} = 3\text{ dumps} / 10\text{ min}$).
4. **The Zero-Division Edge Case:** In static runs at $3\text{ m}$ and $5\text{ m}$ visibility, actual production was $0.0\text{ TPH}$ and feasible capacity was $0.0\text{ TPH}$. An edge-case condition `pr_pct = 100.0 if prod_tph == 0.0 else 0.0` converted $0/0$ into $100.0\%$ retention.

Every level (1, 2, 3, 4, 5) received the exact same initial burst dumps, creating the illusion that orchestration achieved 100% capacity retention under zero-visibility fog.

---

## 2. Parameter-by-Parameter Code Trace

### 2.1 `production_total_tonnes`
- **Source File:** `fog-orchester-3d-digital-twin/twin/simulator.py`
- **Line Numbers:** Line 591, Line 616
- **Function:** `MineDigitalTwinSimulator.step()` (specifically under destination arrival handling)
- **Input Parameters:**
  - `v_state.payload_tonnes`: Float ($91.5\text{ t}$ for loaded Caterpillar 777G, $0.0\text{ t}$ for empty).
  - `dest_type`: String (`"CRUSHER"`).
  - `v_state.is_loaded`: Boolean.
- **Equation:**
  $$\text{total\_tonnage\_delivered}(t) = \sum_{k=1}^{M(t)} m_{\text{payload}, k}$$
  where $M(t)$ is the cumulative count of dump events completed at the crusher node up to time $t$.
- **Physical Meaning:** Realized cumulative payload delivered to the primary crusher pocket.
- **Forensic Execution Record (Seed 101, 10 trucks, 600s dynamic):**
  - $t = 44\text{ s}$: `TRUCK_009` dumps $91.5\text{ t}$ (spawned at `BUFFER_01`, pos $60\text{ m}$, distance to crusher $240\text{ m}$).
  - $t = 49\text{ s}$: `TRUCK_003` dumps $91.5\text{ t}$ (spawned at `BUFFER_01`, pos $40\text{ m}$, distance to crusher $260\text{ m}$).
  - $t = 370\text{ s}$: `TRUCK_005` dumps $91.5\text{ t}$ (spawned at `SHOVEL_02`, departed in clear weather at $t < 300\text{ s}$).
  - $t = 371\text{--}600\text{ s}$: Zero additional dumps occur as severe fog ($v_{\text{safe}} \le 4.8\text{ m/s} \to 0\text{ m/s}$) halts downstream progression.
  - Cumulative delivered: **$274.5\text{ tonnes}$** (exactly 3 dumps).

---

### 2.2 `production_tph`
- **Source File:** `experiments/run_stage5_productivity_benchmark.py`
- **Line Numbers:** Line 464–466
- **Function:** `run_simulation_instance()`
- **Input Parameters:**
  - `sim.state.total_tonnage_delivered`: $274.5\text{ tonnes}$.
  - `duration_s`: $600.0\text{ s}$ (or $300.0\text{ s}$ in fleet scaling).
- **Equation:**
  $$Q_{\text{actual}} = \frac{\text{total\_tonnage\_delivered}}{\text{duration\_s} / 3600.0} = \frac{274.5}{600.0 / 3600.0} = 274.5 \times 6.0 = 1,647.0\text{ TPH}$$
- **Physical Meaning:** Extrapolated hourly production rate based on discrete haul completions over the observation window.
- **Forensic Defect:**
  In a $600\text{ s}$ run, multiplying by $6.0$ extrapolates an initial transient burst (trucks spawned $250\text{ m}$ from the crusher) into an annualized hourly rate. In fleet scaling ($300\text{ s}$ window), the multiplier was $12.0$, producing $274.5 \times 12 = 3,294.0\text{ TPH}$ (20 trucks), $457.5 \times 12 = 5,490.0\text{ TPH}$ (30 trucks), etc. None of these represented closed-loop steady-state haul cycles.

---

### 2.3 `feasible_capacity_tph`
- **Source File:** `experiments/run_stage5_productivity_benchmark.py`
- **Line Numbers:** Lines 126–183, Lines 469–470
- **Function:** `calculate_analytical_feasible_capacity()`
- **Input Parameters:**
  - `network`: MineNetwork (geometry, grades, lengths).
  - `vehicle_cfg`: Mass, power, retarder, dimensions.
  - `visibility_m`: Static visibility or fixed $25.0\text{ m}$ surrogate for dynamic fog.
  - `num_vehicles`: Fleet size ($N \in \{10, 20, 30, 40, 50\}$).
- **Equation:**
  $$C_{\text{feasible}} = \min(Q_{\text{fleet}}, Q_{\text{crusher}}, Q_{\text{switchback}})$$
  where:
  - $Q_{\text{crusher}} = 18.0\text{ VPH} \times 91.5\text{ t} = \mathbf{1,647.0\text{ TPH}}$ (Line 172).
  - $Q_{\text{fleet}} = \frac{N \times 91.5}{T_{\text{cycle}} / 3600.0}$.
  - $Q_{\text{switchback}} = \frac{3600}{2 \times (L_{\text{sb}} / v_{\text{sb}}) + t_{\text{clearance}}} \times 91.5$.
- **Physical Meaning:** Intended to represent the upper bound min-cut bottleneck capacity of the haulage system under given environmental visibility.
- **Forensic Defect:**
  For $N \ge 10$ at $25\text{ m}$ visibility, $Q_{\text{fleet}} = 1,732\text{ TPH}$ and $Q_{\text{switchback}} = 1,840\text{ TPH}$. Thus $\min(Q_{\text{fleet}}, Q_{\text{crusher}}, Q_{\text{switchback}})$ was bounded by $Q_{\text{crusher}} = 1,647.0\text{ TPH}$.
  In dynamic fog, `avg_vis` was set to an arbitrary constant $25.0\text{ m}$ regardless of the actual fog progression down to $3\text{ m}$. Hence `feasible_capacity_tph` remained frozen at $1,647.0\text{ TPH}$.

---

### 2.4 `productivity_retention_percent`
- **Source File:** `experiments/run_stage5_productivity_benchmark.py`
- **Line Numbers:** Lines 472–476
- **Function:** `run_simulation_instance()`
- **Input Parameters:**
  - `prod_tph`: Actual production rate.
  - `feasible_cap_tph`: Calculated feasible capacity.
- **Equation:**
  $$\text{PR} = \begin{cases}
  \min\left(100.0, \frac{Q_{\text{actual}}}{C_{\text{feasible}}} \times 100.0\right) & \text{if } C_{\text{feasible}} > 0 \\
  100.0 & \text{if } C_{\text{feasible}} = 0 \text{ and } Q_{\text{actual}} = 0 \\
  0.0 & \text{otherwise}
  \end{cases}$$
- **Physical Meaning:** Ratio of realized mine throughput to the maximum physically achievable throughput under the active safety envelope.
- **Forensic Defect:**
  1. Under dynamic fog: $Q_{\text{actual}} = 1,647.0\text{ TPH}$ and $C_{\text{feasible}} = 1,647.0\text{ TPH} \implies \text{PR} = 100.0\%$.
  2. Under $3\text{ m}$ and $5\text{ m}$ static fog: $C_{\text{feasible}} = 0.0$ and $Q_{\text{actual}} = 0.0 \implies \text{PR} = 100.0\%$.
  This mathematical convention concealed the physical paralysis of the mine under the claim of "100% productivity retention."

---

## 3. Summary of Forensic Findings

| Metric | Reported Value | Source Mechanism | True Physical Value | Root Flaw |
|:---|:---:|:---|:---:|:---|
| Dynamic Fog Throughput | $1,647.0\text{ TPH}$ | 3 discrete dumps in $600\text{ s}$ ($274.5\text{ t} \times 6$) | $0\text{ TPH}$ steady-state during severe fog ($3\text{--}5\text{ m}$) | Extrapolated initial buffer spawn transient |
| Fog Feasible Capacity | $1,647.0\text{ TPH}$ | Hardcoded crusher limit $18.0 \times 91.5$ at assumed $25\text{ m}$ vis | Collapses to $0\text{ TPH}$ when $v_{\text{safe}} = 0$ | Static parameter substitution in dynamic scenario |
| Productivity Retention | $100.0\%$ | $1647 / 1647 = 1.0$ and $0 / 0 \to 1.0$ | $0.0\%$ when stalled; uncoupled in transient | Circular definition against crusher ceiling |
| Level Differentiation | All levels $= 1647.0$ | All levels dumped same 3 initial trucks | Throughput identical because bottleneck is safety speed | Evaluator cannot see orchestration benefits from throughput |

---

## 4. Remediation Requirements for Stage 5.1

To make the benchmark scientifically rigorous, physically honest, and immune to evaluator challenge:
1. **Cold Start Elimination / True Cycle Accounting:** Production must be measured either:
   - Over a sufficiently long window ($T \ge 3,600\text{ s}$) where full round-trip cycles ($> 1,500\text{ s}$) settle into genuine steady-state.
   - Or by tracking **completed shovel-to-crusher haul cycles** initialized exclusively at shovels with explicit load timestamps.
2. **Dynamic Capacity Ceiling:** $C_{\text{network}}(t)$ must dynamically track the instantaneous minimum physical capacity across road headway, switchback clearance, shovel cycle, and crusher pocket as visibility changes.
3. **Honest Retention:** When $C_{\text{network}} = 0\text{ TPH}$ (at $v_{\text{safe}} = 0\text{ m/s}$), productivity retention is defined as **$0.0\%$**, explicitly reflecting mine closure.
4. **Valid Operational Metrics:** Because Level 1 (Safety Only) and Level 4 (FOG-Orchestrator) both strictly obey Tier-1 safety speed limits, neither can physically move trucks faster than $v_{\text{safe}}$. Orchestration's value lies in **eliminating avoidable queuing on ramps, preventing switchback gridlock, reducing idle fuel burn, and orchestrating rapid recovery when visibility lifts**.
