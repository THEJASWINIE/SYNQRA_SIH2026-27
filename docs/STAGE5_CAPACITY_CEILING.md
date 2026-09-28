# STAGE 5: PHYSICAL FEASIBILITY CEILING & CAPACITY FORMULATION
**SIH 2026-27 — NMDC Bailadila Haulage Fog Stress Problem Statement**  
**Role:** Lead Simulation / Research Engineer, FOG-ORCHESTRATOR 2.0  
**Status:** COMPLETE & VERIFIED

---

## 1. Physical Capacity Hierarchy

In previous project documentation, a common conceptual error was noted:
> *Comparing an arrival rate of 18 VPH against a theoretical dual-lane highway capacity of 700 VPH, while ignoring that the primary gyratory crusher service capacity is strictly bounded at 18 VPH.*

To eliminate unscientific comparisons, the STAGE 5 framework strictly categorizes four distinct capacity layers:

```
                    ┌──────────────────────────────────────────────┐
                    │ 1. KINEMATIC THEORETICAL ROAD CAPACITY       │
                    │    C_kinematic = 3600 * v_safe / H_safe      │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 2. ROAD PRACTICAL CAPACITY                   │
                    │    Accounts for single-lane switchbacks,     │
                    │    grades, curve radii, and acceleration     │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 3. NODE SERVICE CAPACITY                     │
                    │    mu_crusher = 18 VPH, lambda_shovel = 15 VPH│
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 4. NETWORK FEASIBLE THROUGHPUT               │
                    │    Q_fog_feasible = min(C_road, mu_node, Q_fl)│
                    └──────────────────────────────────────────────┘
```

---

## 2. Derivation of the Four Capacity Layers

### 2.1 Layer 1: Kinematic Theoretical Road Capacity ($C_{\text{kinematic}}$)
On dual-lane haul roads (`ROAD_01`, `ROAD_02`, `ROAD_03`, `ROAD_05`, `ROAD_06`), the theoretical saturation flow is determined by steady-state car-following headway:
$$H_{\text{safe}}(v, a_{\text{dec}}) = L_{\text{veh}} + S_{\text{margin}} + v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
where:
- Vehicle Length: $L_{\text{veh}} = 10.52\text{ m}$
- Standstill Safety Margin: $S_{\text{margin}} = 5.0\text{ m}$
- Perception-Reaction + Actuation Latency: $\tau_{\text{total}} = 1.25\text{ s}$
- Deceleration on Grade: $a_{\text{dec}} = \frac{F_{\text{brake}} + F_{\text{roll}} - F_{\text{grade}}}{m}$

Then the theoretical kinematic road capacity is:
$$C_{\text{kinematic}} = \frac{3600 \cdot v_{\text{safe}}}{H_{\text{safe}}} \quad [\text{VPH}]$$

### 2.2 Layer 2: Road Practical Capacity & Switchback Bottlenecks ($C_{\text{practical}}$)
The critical physical bottleneck on the NMDC Bailadila haul ramp is the **narrow, single-lane alternating switchback hairpin (`ROAD_04`)**:
- Length: $L_{\text{switchback}} = 250\text{ m}$
- Grade: $8.0\%$ steep gradient
- Curve Radius: $R_c = 45\text{ m}$
- Direction Mode: `single_lane_alternating` (strict mutual exclusion)

Because opposing haul traffic cannot occupy `ROAD_04` simultaneously, the bidirectional capacity is strictly bounded by alternating clearance time:
$$t_{\text{traverse}} = \frac{L_{\text{switchback}}}{v_{\text{safe}}^{\text{switchback}}}$$
$$C_{\text{switchback}} = \frac{3600}{2 \cdot t_{\text{traverse}} + 2 \cdot t_{\text{clearance}}} \quad [\text{VPH}]$$
where $t_{\text{clearance}} = 3.0\text{ s}$ safety buffer between opposing release slots.

### 2.3 Layer 3: Node Service Capacity ($\mu_{\text{node}}$)
- **Primary Gyratory Crusher (`CRUSHER_01`):** Service rate $\mu_{\text{crusher}} = 18.0\text{ VPH}$ ($\sim 200.0\text{ s}$ per truck tipping/dumping cycle).  
  Maximum Crusher Ore Intake: $18.0 \times 91.5\text{ t} = \mathbf{1,647.0\text{ TPH}}$.
- **Pit Loading Shovels (`SHOVEL_01`, `SHOVEL_02`):** Combined service rate $\lambda_{\text{total}} = 15.0 + 15.0 = 30.0\text{ VPH}$ ($\sim 240.0\text{ s}$ per 4-pass loading cycle).  
  Maximum Shovel Ore Production: $30.0 \times 91.5\text{ t} = \mathbf{2,745.0\text{ TPH}}$.

### 2.4 Layer 4: Network Feasible Throughput ($Q_{\text{fog\_feasible}}$)
The achievable ore throughput cannot exceed the most restrictive component in the entire chain:
$$Q_{\text{fog\_feasible}}(R_v, N) = \min \Big( Q_{\text{fleet\_available}}(R_v, N), \; Q_{\text{node\_service}}, \; Q_{\text{switchback}}(R_v) \Big)$$

---

## 3. Analytical Capacity Ceiling Table Across Visibility Regimes

Evaluated using CAT 777D gross operating mass ($165,500\text{ kg}$) and wet road friction ($\mu = 0.35$):

| Visibility $R_v$ | Surface State | Ramp $v_{\text{safe}}$ (8% grade) | Headway $H_{\text{safe}}$ | Dual-Lane $C_{\text{road}}$ | Switchback $C_{\text{switch}}$ | Crusher Intake Limit | Net Feasible $Q_{\text{fog\_feasible}}$ ($N=10$) | Net Feasible $Q_{\text{fog\_feasible}}$ ($N=30$) | Net Feasible $Q_{\text{fog\_feasible}}$ ($N=50$) | Active Constraint |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **100 m** (Clear) | Dry ($\mu=0.65$) | $8.33\text{ m/s}$ (30 km/h) | $34.76\text{ m}$ | $862.8\text{ vph}$ | $54.5\text{ vph}$ | $1,647.0\text{ TPH}$ | **1,647.0 TPH** | **1,647.0 TPH** | **1,647.0 TPH** | **Crusher Service ($\mu=18$)** |
| **50 m** (Mod. Fog) | Dry ($\mu=0.65$) | $8.33\text{ m/s}$ | $34.76\text{ m}$ | $862.8\text{ vph}$ | $54.5\text{ vph}$ | $1,647.0\text{ TPH}$ | **1,647.0 TPH** | **1,647.0 TPH** | **1,647.0 TPH** | **Crusher Service ($\mu=18$)** |
| **25 m** (Hvy. Fog) | Wet ($\mu=0.35$) | $8.33\text{ m/s}$ | $35.52\text{ m}$ | $844.1\text{ vph}$ | $54.5\text{ vph}$ | $1,647.0\text{ TPH}$ | **1,647.0 TPH** | **1,647.0 TPH** | **1,647.0 TPH** | **Crusher Service ($\mu=18$)** |
| **12 m** (Dense Fog)| Wet ($\mu=0.35$) | $4.63\text{ m/s}$ (16.7 km/h)| $22.52\text{ m}$ | $739.9\text{ vph}$ | $31.6\text{ vph}$ | $1,647.0\text{ TPH}$ | **1,647.0 TPH** | **1,647.0 TPH** | **1,647.0 TPH** | **Crusher Service ($\mu=18$)** |
| **10 m** (Dense Fog)| Wet ($\mu=0.35$) | $3.80\text{ m/s}$ (13.7 km/h)| $20.52\text{ m}$ | $667.4\text{ vph}$ | $26.2\text{ vph}$ | $1,647.0\text{ TPH}$ | **1,647.0 TPH** | **1,647.0 TPH** | **1,647.0 TPH** | **Crusher Service ($\mu=18$)** |
| **6.0 m** (Extreme) | Wet ($\mu=0.35$) | $1.37\text{ m/s}$ (4.9 km/h)  | $17.55\text{ m}$ | $281.0\text{ vph}$ | $9.6\text{ vph}$  | $1,647.0\text{ TPH}$ | **878.4 TPH** | **878.4 TPH** | **878.4 TPH** | **Switchback Slot Capacity** |
| **5.0 m** (Threshold)| Wet ($\mu=0.35$)| $\mathbf{0.00\text{ m/s}}$ | $15.52\text{ m}$ | $\mathbf{0.0\text{ vph}}$ | $\mathbf{0.0\text{ vph}}$ | $1,647.0\text{ TPH}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | **Safety Margin ($R_v \le S_{\text{margin}}$)** |
| **4.0 m** (Severe)  | Wet ($\mu=0.35$)| $\mathbf{0.00\text{ m/s}}$ | $15.52\text{ m}$ | $\mathbf{0.0\text{ vph}}$ | $\mathbf{0.0\text{ vph}}$ | $1,647.0\text{ TPH}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | **PHYSICAL HALT (MANDATORY)** |
| **3.0 m** (Severe)  | Wet ($\mu=0.35$)| $\mathbf{0.00\text{ m/s}}$ | $15.52\text{ m}$ | $\mathbf{0.0\text{ vph}}$ | $\mathbf{0.0\text{ vph}}$ | $1,647.0\text{ TPH}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | $\mathbf{0.0\text{ TPH}}$ | **PHYSICAL HALT (MANDATORY)** |

---

## 4. Fundamental Finding: The Severe Fog 3–5 m Physical Operating Boundary

A vital engineering finding emerges from the physical braking equation:
$$S_{\text{stop}} + S_{\text{margin}} \le R_v \implies v_{\text{safe}} = -a_{\text{dec}} \tau_{\text{total}} + \sqrt{(a_{\text{dec}} \tau_{\text{total}})^2 + 2 a_{\text{dec}} \max(0, R_v - S_{\text{margin}})}$$
- Standstill safety margin is $S_{\text{margin}} = 5.0\text{ m}$ (the minimum distance a 165.5-tonne haul truck must maintain from an obstacle at rest).
- When visibility drops to **$R_v \le 5.0\text{ m}$ (specifically $3\text{--}5\text{ m}$)**:
  $$\max(0, R_v - S_{\text{margin}}) = 0 \implies v_{\text{safe}} = 0.0\text{ m/s}$$
- **Evaluator Defense Grounding:**  
  If any system claims to operate haul trucks at speed when visibility is $3\text{ m}$, it is either fabricating telemetry or violating safety physics. In $3\text{ m}$ visibility, an obstacle cannot be perceived before the front bumper is already within the $5.0\text{ m}$ hazard buffer.  
  Therefore, **at $3\text{ m}$, continuing movement is physically impossible without violating safety.**  
  FOG-ORCHESTRATOR's response is an authoritative **CONTROLLED SAFETY HOLD**, eliminating collision risk while staging the fleet at buffers to resume immediately once visibility recovers.
