# STAGE 3 — Authoritative Capacity Model & Boundary Definitions

## 1. Executive Summary

A core finding of the STAGE 3 Forensic Audit is that previous reports conflated three distinct operational concepts under the single ambiguous word "capacity":
1. **Theoretical Single-Lane Kinematic Saturation Flow Rate ($C_{kinematic}$)**
2. **Practical Haul Road Carrying Capacity ($C_{practical}$)**
3. **Bottleneck Node Service Rate ($\mu_{node}$)**

This document establishes the canonical mathematical definitions, governing equations, operational constraints, and hand calculations for each concept.

---

## 2. Canonical Hierarchy of Capacities

```
+-------------------------------------------------------------------------+
|                  1. Theoretical Kinematic Saturation Flow               |
|                  C_kinematic = 3600 * v_safe / (H_safe + L_veh)         |
|                  Result: 700.5 vph (Bumper-to-bumper convoy at 5.14s)   |
+-------------------------------------------------------------------------+
                                    |
                                    v (Restricted by DGMS mine headway rules)
+-------------------------------------------------------------------------+
|                  2. Practical Haul Road Capacity                         |
|                  C_practical = 3600 / T_headway_min                     |
|                  Result: 180.0 vph (Min headway 30m / time headway 20s) |
+-------------------------------------------------------------------------+
                                    |
                                    v (Restricted by single-lane conflict zones)
+-------------------------------------------------------------------------+
|                  3. Alternating Switchback Passing Rate                 |
|                  mu_switchback = 3600 / (2 * T_traverse + T_clear)      |
|                  Result: 15.0 - 25.0 vph                                |
+-------------------------------------------------------------------------+
                                    |
                                    v (Restricted by physical dumping cycle)
+-------------------------------------------------------------------------+
|                  4. Primary Crusher Dumping Pocket Service Rate          |
|                  mu_crusher = 3600 / T_dumping                          |
|                  Result: 10.0 - 18.0 vph (Service time 200s - 360s)     |
+-------------------------------------------------------------------------+
```

---

## 3. Detailed Mathematical Models

### Model 1: Theoretical Kinematic Saturation Flow Rate ($C_{kinematic}$)

The maximum theoretical number of vehicles that can pass an ideal cross-section of a single uninterrupted lane per hour when vehicles are spaced at the absolute minimum legal dynamic headway:

$$C_{kinematic} = rac{3600 \cdot v_{safe}}{H_{safe} + L_{veh}} \quad [	ext{vehicles/hour}]$$

Where:
- $v_{safe}$: Multi-constraint Tier-1 safe speed ($m/s$).
- $H_{safe} = S_{stop}(v_{safe}) + S_{margin}(v_{safe})$: Dynamic safe headway ($m$).
- $L_{veh}$: Vehicle overall length ($10.52	ext{ m}$ for BEML BH100).

#### Worked Hand Calculation (Dense Fog on Downhill Haul Ramp)
- **Inputs**:
  - $R_{effective} = 12.0	ext{ m}$
  - Civil grade $= -8.0\%$ (Downhill, $	heta_{phys} = +0.0798	ext{ rad}$)
  - Tire-road friction $\mu = 0.35$ (Wet compacted iron ore road)
  - Gross mass $m = 165,500	ext{ kg}$
  - Total reaction time $	au_{total} = 0.80	ext{ s}$
  - Standstill safety margin $S_{base} = 5.0	ext{ m}$
- **Braking Deceleration**:
  $$a_{dec} = rac{\min(F_{hw}, \mu m g \cos	heta) + F_{roll} - m g \sin	heta}{m} = 2.7466	ext{ m/s}^2$$
- **Analytical Safe Speed**:
  $$v_{safe} = -a_{dec} 	au + \sqrt{a_{dec}^2 	au^2 + 2 a_{dec} (R_{eff} - S_{base})}$$
  $$v_{safe} = -2.1973 + \sqrt{4.8281 + 38.4525} = 4.3815	ext{ m/s} \quad (15.77	ext{ km/h})$$
- **Stopping Distance and Headway**:
  $$S_{stop} = 4.3815 	imes 0.80 + rac{4.3815^2}{2 	imes 2.7466} = 3.5052 + 3.4948 = 7.0000	ext{ m}$$
  $$S_{margin} = 5.0000	ext{ m}$$
  $$H_{safe} = 7.0000 + 5.0000 = 12.0000	ext{ m}$$
- **Gross Space Headway (Center-to-Center)**:
  $$D_{center} = H_{safe} + L_{veh} = 12.00 + 10.52 = 22.52	ext{ m}$$
- **Time Headway**:
  $$T_{headway} = rac{D_{center}}{v_{safe}} = rac{22.52	ext{ m}}{4.3815	ext{ m/s}} = 5.1398	ext{ seconds}$$
- **Resulting Capacity**:
  $$C_{kinematic} = rac{3600}{5.1398} = 700.41 pprox 700.5	ext{ vph}$$

> [!IMPORTANT]
> $700.5	ext{ vph}$ is a **saturation flow limit**, NOT an open-cast mine dispatch target. A haul road operating at $700.5	ext{ vph}$ would mean 165.5-tonne dumpers hurtling down an 8% grade bumper-to-bumper with only $12	ext{ m}$ separation between rear bumper and front radiator.

---

### Model 2: Practical Haul Road Carrying Capacity ($C_{practical}$)

Open-cast mine safety regulations (DGMS Circulars / MSHA regulations) mandate safe operational spacing that accounts for dust, spray, and driver comfort:
- Minimum following distance: $D_{min} \ge 30	ext{ m}$ to $50	ext{ m}$.
- Minimum dispatch interval: $T_{dispatch\_min} \ge 20.0	ext{ s}$.

$$C_{practical} = rac{3600}{\max\left(T_{dispatch\_min}, rac{H_{safe} + L_{veh}}{v_{safe}}ight)} = rac{3600}{20.0	ext{ s}} = 180.0	ext{ vph}$$

Under dense fog where $v_{safe} = 4.382	ext{ m/s}$, the practical capacity remains bound by safe convoy spacing at $180.0	ext{ vph}$.

---

### Model 3: Bottleneck Service Rates ($\mu_{node}$)

In a mine network, the true throughput bottlenecks are discrete service facilities:

1. **Primary Crusher Dumping Pocket (Node `C1`)**:
   - Single-stall gyratory crusher dumping pocket.
   - Cycle steps: Reversing into pocket ($60	ext{ s}$), raising dump body ($90	ext{ s}$), discharging ore ($120	ext{ s}$), lowering body and departure ($90	ext{ s}$).
   - Total cycle time $T_{dumping} = 360	ext{ s}$ ($6	ext{ minutes}$).
   - Nominal service capacity:
     $$\mu_{crusher} = rac{3600	ext{ s}}{360	ext{ s}} = 10.0	ext{ vph}$$
   - (High-speed multi-hopper pocket: $T_{dumping} = 200	ext{ s} \implies \mu_{crusher} = 18.0	ext{ vph}$).

2. **Single-Lane Alternating Switchback (Node `SW1`)**:
   - Length $L_{sw} = 500	ext{ m}$.
   - One-way traverse time under fog ($v_{safe} = 4.38	ext{ m/s}$):
     $$T_{traverse} = rac{500	ext{ m}}{4.3815	ext{ m/s}} = 114.1	ext{ s}$$
   - Round-trip clearance interval with safety buffer:
     $$T_{cycle} = 2 	imes 114.1 + 15	ext{ s} = 243.2	ext{ s}$$
   - Alternating bidirectional service rate:
     $$\mu_{switchback} = rac{3600}{243.2} = 14.8 pprox 15.0	ext{ vph}$$

---

## 4. Resolution of the Apparent Contradiction

| Metric | Stage 2 Formulation | Stage 3 Authoritative Specification | Reconciled Interpretation |
|:---|:---|:---|:---|
| **Road Flow** | `dynamic_capacity_vph = 700.5` | `theoretical_kinematic_capacity_vph = 700.5` | Platoon saturation limit |
| **Operational Road** | Mentioned as "600 nominal" | `practical_road_capacity_vph = 180.0` | Regulation-constrained haul road limit |
| **Crusher Capacity** | Omitted from JSON (`10.0` hardcoded in script) | `crusher_service_capacity_vph = 10.0` | Discrete physical dumping bottleneck |
| **Shovel Arrival** | `shovel_arrival_rate_vph = 18.0` | `shovel_arrival_rate_vph = 18.0` | Fleet feed demand rate |
| **Bottleneck Status** | "18 exceeded 700.5" (erroneous) | $\lambda = 18.0	ext{ vph} > \mu_{crusher} = 10.0	ext{ vph}$ | Crusher queue saturates ($+1.33	ext{ veh}/600	ext{ s}$) |

The apparent paradox is completely resolved. The road segment has plenty of kinematic flow capability ($700.5	ext{ vph}$), but the **Crusher dumping pocket** can only process $10.0	ext{ vph}$. Therefore, arrivals at $18.0	ext{ vph}$ cause queue saturation at the Crusher, demanding upstream HOLD commands.
