# STAGE 5: PRODUCTIVITY RETENTION METRIC DEFINITION
**SIH 2026-27 — NMDC Bailadila Haulage Fog Stress Problem Statement**  
**Role:** Lead Simulation / Research Engineer, FOG-ORCHESTRATOR 2.0  
**Status:** FROZEN REFERENCE DEFINITION

---

## 1. The Core Scientific Problem

In open-cast mining during severe monsoons (e.g. NMDC Bailadila Complex, Kirandul / Bacheli), thick fog regularly reduces visibility to $3\text{--}5\text{ m}$. Under these conditions, standard mine operations either:
1. **Shut Down Completely (Level -1):** Resulting in zero ore delivery ($0.0\text{ TPH}$), massive financial loss, and disrupted processing plant feed; or
2. **Operate with Ad-Hoc Human Driving / Safety-Only (Level 1):** Drivers slow down reactively. Because haul roads have differing grades, curve radii, and single-lane bottlenecks (such as hairpin switchbacks), deceleration causes localized headway expansions and severe arrival bunching. Massive uncontrolled queues form at the primary crusher pocket and switchback approaches, causing trucks to idle in dense fog, burn fuel, cycle their retarders, and waste operating capacity.

The goal of FOG-ORCHESTRATOR is **not** to magically drive at clear-weather speeds through thick fog. That would violate basic physics and safety.  
The true scientific objective is:
$$\text{MAXIMIZE ACHIEVED PRODUCTION SUBJECT TO PHYSICAL SAFETY AND CAPACITY CONSTRAINTS}$$

---

## 2. Formal Mathematical Definition of Productivity Retention (PR)

We define the primary figure of merit:

$$\mathbf{PR} = \frac{Q_{\text{actual}}}{Q_{\text{fog\_feasible}}} \times 100 \quad [\%]$$

where:
- $Q_{\text{actual}}$: The actual delivered ore production (in tonnes per hour, TPH) achieved by the evaluated operating policy over simulation horizon $T$.
- $Q_{\text{fog\_feasible}}$: The **maximum production physically feasible** under the exact same operational and environmental constraints:
  - Same visibility profile $R_v(t)$
  - Same road surface friction $\mu(t)$
  - Same haul road geometry (grades $\theta_e$, lengths $L_e$, widths $W_e$, curve radii $R_c$)
  - Same vehicle physical dynamics (CAT 777D gross mass $165.5\text{ t}$, retarder absorption limit $1193\text{ kW}$)
  - Same destination node service capacities ($\mu_{\text{crusher}} = 18\text{ VPH}$, $\lambda_{\text{shovel}} = 15\text{ VPH}$)
  - Same available fleet size $N \in \{10, 20, 30, 40, 50\}$
  - Same discrete time horizon $T$
  - **Strict adherence to the Tier-1 local safety envelope ($v \le v_{\text{safe}}$ and zero collisions).**

---

## 3. Derivation of the Physical Feasibility Ceiling $Q_{\text{fog\_feasible}}$

$Q_{\text{fog\_feasible}}$ is **never an arbitrary number** or an unconstrained clear-sky throughput. It is the analytical upper-bound established by the **min-cut capacity** of the network:

$$Q_{\text{fog\_feasible}}(R_v, N) = \min \Big( Q_{\text{fleet\_available}}(R_v, N), \; Q_{\text{node\_service}}, \; Q_{\text{road\_capacity}}(R_v) \Big)$$

### 3.1 Fleet Availability Bound ($Q_{\text{fleet\_available}}$)
Each truck requires a minimum round-trip cycle time consisting of loading, loaded haul, dumping, and empty return:
$$T_{\text{cycle}}^{\text{min}}(R_v) = t_{\text{load}} + \sum_{e \in \text{Haul}} \frac{L_e}{v_{\text{safe}}(e, R_v)} + t_{\text{dump}} + \sum_{e \in \text{Return}} \frac{L_e}{v_{\text{safe}}(e, R_v)}$$
Under unconstrained zero-queue conditions:
$$Q_{\text{fleet\_available}}(R_v, N) = \frac{N \times \text{Payload}}{T_{\text{cycle}}^{\text{min}}(R_v) / 3600} \quad [\text{TPH}]$$
where $\text{Payload} = 91.5\text{ tonnes}$.

### 3.2 Node Service Bound ($Q_{\text{node\_service}}$)
The crusher cannot receive more trucks than its physical tipping and dumping mechanism permits:
$$Q_{\text{crusher\_max}} = \mu_{\text{crusher}} \times \text{Payload} = 18.0 \times 91.5 = 1,647.0\text{ TPH}$$
The loading shovels cannot dispatch more than their combined loading rate:
$$Q_{\text{shovel\_max}} = \sum_{s \in \text{Shovels}} \lambda_s \times \text{Payload} = (15.0 + 15.0) \times 91.5 = 2,745.0\text{ TPH}$$
Hence:
$$Q_{\text{node\_service}} = \min(Q_{\text{crusher\_max}}, Q_{\text{shovel\_max}}) = 1,647.0\text{ TPH}$$

### 3.3 Road Segment Kinematic & Switchback Bound ($Q_{\text{road\_capacity}}$)
On dual-lane segments, road capacity is governed by safe stopping headway:
$$C_e(R_v) = \frac{3600 \cdot v_{\text{safe}}(e, R_v)}{H_{\text{safe}}(e, R_v)} \quad [\text{VPH}]$$
On single-lane alternating segments (e.g. `ROAD_04` hairpin switchback), mutual exclusion dictates:
$$C_{\text{switchback}}(R_v) = \frac{3600}{2 \cdot \left(\frac{L_{\text{switchback}}}{v_{\text{safe}}^{\text{switchback}}(R_v)}\right) + 2 \cdot t_{\text{clearance}}} \quad [\text{VPH}]$$
The road network capacity ceiling is:
$$Q_{\text{road\_capacity}}(R_v) = \min_{e \in \text{Critical Path}} C_e(R_v) \times 91.5 \quad [\text{TPH}]$$

---

## 4. Complete Suite of Evaluated Performance Metrics

In addition to $PR$, every simulation run records:
1. **Absolute Production (TPH):** $\frac{\text{Total Tonnes Delivered}}{T_{\text{hours}}}$.
2. **Production Loss Relative to Clear Weather ($\Delta Q_{\text{loss}}$):**
   $$\Delta Q_{\text{loss}} = Q_{\text{clear}} - Q_{\text{actual}} \quad [\text{TPH}]$$
3. **Production Retention Percent:** $\frac{Q_{\text{actual}}}{Q_{\text{clear}}} \times 100\ [\%]$.
4. **Productivity Retention Percent ($PR$):** $\frac{Q_{\text{actual}}}{Q_{\text{fog\_feasible}}} \times 100\ [\%]$.
5. **Fleet Idle Percent ($\%$):** Percentage of total vehicle-seconds where speed $v < 0.1\text{ m/s}$ while not actively loading or dumping.
6. **Fleet Waiting Time ($s$):** Average accumulated standstill waiting time per vehicle.
7. **Mean Cycle Time ($s$):** Average elapsed time per completed haul cycle.
8. **Peak Queue (vehicles):** Maximum queue length observed across all service and conflict nodes.
9. **Queue Duration ($s$):** Total duration during which any node queue $Q(t) \ge 3$ vehicles.
10. **Bottleneck Duration ($s$):** Total continuous duration where any element utilization $\rho > 0.85$.
11. **Recovery Time ($s$):** Time required after fog clears for fleet speeds and cycle throughput to return within $5\%$ of nominal clear-weather steady state.
12. **Safety Violations (count):** Any instance where $v_{\text{actual}} > v_{\text{safe}} + 10^{-3}\text{ m/s}$ or gap $g < H_{\text{safe}}^{\text{min}}$. Must be strictly **$0$**.

---

## 5. Decision Thresholds & Success Criteria

| Metric | Target / Benchmark Requirement | Evaluator Defense Criteria |
|:---|:---:|:---|
| **Safety Violations** | **Strictly 0.0 across all seeds** | Non-negotiable Tier-1 invariant. |
| **Productivity Retention ($PR$)** | **$PR_{\text{Level 4}} > PR_{\text{Level 1}}$** | Proves orchestration prevents queuing loss. |
| **Fleet Idle Reduction** | **$\ge 25\%$ reduction vs Level 1** | Prevents bunching in fog. |
| **Queue Peak Mitigation** | **Lower peak queue vs Level 1** | Meters arrivals to prevent crusher gridlock. |
| **Recovery Speed** | **Faster or equal to Level 1** | Proactive slot clearing prevents post-fog logjam. |
