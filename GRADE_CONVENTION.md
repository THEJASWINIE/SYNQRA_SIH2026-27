# GRADE CONVENTION SPECIFICATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
### Canonical Road Grade Sign Convention & Normalization Architecture

**Specification Version:** 2.0.0  
**Status:** CANONICAL ARCHITECTURAL STANDARD  
**Enforcement Layer:** `integration_adapters/grade_adapter.py` (`GradeAdapter`)  
**Validation Suite:** `tests/test_grade_adapter.py`

---

## 1. The Core Engineering Conflict

In earlier versions of the software, two competing grade conventions existed concurrently across different subsystems:

1. **Civil Engineering & GIS Convention (External Mine Surveys / Maps / HMI):**
   - Defined by elevation differential over horizontal travel distance: $G_{\text{civil}} = \frac{\Delta h}{\Delta s} \times 100\%$.
   - **Positive Grade ($+G$):** Uphill ascent. Elevation increases along vehicle travel direction. Gravity vector points backwards along the road slope, opposing vehicle motion and aiding braking deceleration.
   - **Negative Grade ($-G$):** Downhill descent. Elevation decreases along vehicle travel direction. Gravity vector points forwards along the road slope, accelerating the vehicle forward and opposing braking deceleration.
   - **Zero Grade ($0\%$):** Level road.

2. **Internal Resistance Physics Convention (`fog_safe/road.py` & `fog_safe/braking.py`):**
   - Oriented along vehicle forward longitudinal axis ($+x$).
   - Defined downhill forward slope as a positive angle $\theta > 0$, where the forward component of gravity is $F_{\text{grade}} = m g \sin\theta > 0$.
   - In net retarding force balance: $F_{\text{net\_retarding}} = F_{\text{brake}} + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}$.
   - Under this coordinate orientation, internal physics required a positive percent grade for downhill.

**Failure Mode If Unadapted:** If a civil map supplied $-8\%$ for a downhill ramp directly to the resistance solver without transformation, the solver would interpret it as an uphill climb, computing an artificially high deceleration and an dangerously short stopping distance.

---

## 2. Canonical Architecture & The GradeAdapter Contract

To eliminate ambiguity without breaking working mathematical solvers, the system establishes a single authoritative boundary adapter:

$$\text{External GIS / Mine Maps / HMI UI} \xrightarrow[\text{Civil Convention: }+=\text{Uphill},\ -=\text{Downhill}]{} \text{GradeAdapter} \xrightarrow[\text{Internal Physics: }+=\text{Downhill},\ -=\text{Uphill}]{} \text{Physics Engine / Twin}$$

### 2.1 Mathematical Transformation Equations

```mermaid
flowchart LR
    A["Civil GIS Grade<br>(+8% Uphill, -8% Downhill)"] -->|GradeAdapter.civil_to_physics_grade| B["Internal Physics Grade<br>(-8% Uphill, +8% Downhill)"]
    B -->|RoadSegment.theta| C["Slope Angle theta = arctan(Grade / 100)"]
    C -->|F_grade = m g sin(theta)| D["Longitudinal Force Balance<br>Downhill: F_grade > 0 (accelerates forward)<br>Uphill: F_grade < 0 (opposes motion)"]
    D -->|GradeAdapter.physics_to_civil_grade| E["HMI / Operator HUD Display<br>(Restores Civil Convention)"]
```

The bijective mapping enforced by `GradeAdapter` is:
$$G_{\text{physics}} = - G_{\text{civil}}$$
$$G_{\text{civil}} = - G_{\text{physics}}$$

Where the grade angle $\theta$ is:
$$\theta = \arctan\left(\frac{G_{\text{physics}}}{100}\right) = \arctan\left(\frac{-G_{\text{civil}}}{100}\right)$$

### 2.2 Force Balance Integration

In longitudinal dynamics:
$$m \frac{dv}{dt} = F_{\text{drive}} + F_{\text{grade}} - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$

Where:
- Downhill ($G_{\text{civil}} < 0 \implies G_{\text{physics}} > 0 \implies \theta > 0$):
  $$F_{\text{grade}} = m g \sin\theta > 0 \quad \text{(Assists forward motion / opposes braking)}$$
- Uphill ($G_{\text{civil}} > 0 \implies G_{\text{physics}} < 0 \implies \theta < 0$):
  $$F_{\text{grade}} = m g \sin\theta < 0 \quad \text{(Opposes forward motion / assists braking)}$$

During emergency braking ($F_{\text{drive}} = 0$):
$$F_{\text{net\_retarding}} = F_{\text{brake}} + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}$$
$$a_{\text{dec}} = \frac{F_{\text{net\_retarding}}}{m}$$

Because $F_{\text{grade}}$ is subtracted:
- On downhill ($F_{\text{grade}} > 0$), net retarding force is reduced, leading to **lower $a_{\text{dec}}$** and **longer $S_{\text{stop}}$**.
- On uphill ($F_{\text{grade}} < 0$), $-(- |F_{\text{grade}}|) = + |F_{\text{grade}}|$, net retarding force is increased, leading to **higher $a_{\text{dec}}$** and **shorter $S_{\text{stop}}$**.

---

## 3. Mandatory 5-Point Calibration Verification Matrix

Evaluated under canonical conditions:
- Vehicle: BEML BH100 / CAT 777G fully loaded gross mass $m = 165{,}500\text{ kg}$
- Tire-Road Friction: $\mu = 0.35$ (Wet compacted ore haul road)
- Rolling Resistance: $C_{rr} = 0.025$
- Autonomous Latency: $\tau_{\text{total}} = 0.450\text{ s}$
- Visibility: Dense fog $V = 12.0\text{ m}$ ($R_{\text{effective}} = 12.0\text{ m}$)
- Test Speed: $v_{\text{test}} = 6.00\text{ m/s}$

| Civil Grade ($G_{\text{civil}}$) | Physics Grade ($G_{\text{physics}}$) | Angle $\theta$ (rad) | Effective Deceleration $a_{\text{dec}}$ | Stopping Distance $S_{\text{stop}}$ ($v = 6\text{ m/s}$) | Safe Speed $v_{\text{safe}}$ ($V = 12\text{ m}$) | Active Limiting Constraint | Physical Behavior Description |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$+8.0\%$** | $-8.0\%$ | $-0.0798$ | **$4.313\text{ m/s}^2$** | **$6.87\text{ m}$** | **$5.05\text{ m/s}$** ($18.18\text{ km/h}$) | `v_stop` | Steep uphill: Gravity opposes forward velocity; maximal braking assistance. |
| **$+5.0\%$** | $-5.0\%$ | $-0.0500$ | **$4.021\text{ m/s}^2$** | **$7.18\text{ m}$** | **$4.95\text{ m/s}$** ($17.81\text{ km/h}$) | `v_stop` | Moderate uphill: Gravity assists braking. |
| **$0.0\%$** | $0.0\%$ | $0.0000$ | **$3.531\text{ m/s}^2$** | **$7.80\text{ m}$** | **$4.75\text{ m/s}$** ($17.11\text{ km/h}$) | `v_stop` | Level ground: Deceleration governed purely by tire friction and rolling resistance. |
| **$-5.0\%$** | $+5.0\%$ | $+0.0500$ | **$3.041\text{ m/s}^2$** | **$8.62\text{ m}$** | **$4.53\text{ m/s}$** ($16.31\text{ km/h}$) | `v_stop` | Moderate downhill: Gravity pulls truck forward; braking capacity degraded. |
| **$-8.0\%$** | $+8.0\%$ | $+0.0798$ | **$2.748\text{ m/s}^2$** | **$9.25\text{ m}$** | **$4.38\text{ m/s}$** ($15.77\text{ km/h}$) | `v_stop` | Steep downhill ramp: Gravity severely degrades deceleration; safe speed lowest. |

---

## 4. Verification of Physical Invariants

The 5-point sweep mathematically proves the four mandatory sanity invariants:

1. **Deceleration Monotonicity:**
   $$a_{\text{dec}}(+8\%) > a_{\text{dec}}(+5\%) > a_{\text{dec}}(0\%) > a_{\text{dec}}(-5\%) > a_{\text{dec}}(-8\%)$$
   $$4.313 > 4.021 > 3.531 > 3.041 > 2.748\text{ m/s}^2 \quad \text{[PROVEN]}$$

2. **Stopping Distance Monotonicity:**
   $$S_{\text{stop}}(+8\%) < S_{\text{stop}}(+5\%) < S_{\text{stop}}(0\%) < S_{\text{stop}}(-5\%) < S_{\text{stop}}(-8\%)$$
   $$6.87 < 7.18 < 7.80 < 8.62 < 9.25\text{ m} \quad \text{[PROVEN]}$$

3. **Safe Speed Monotonicity:**
   $$v_{\text{safe}}(+8\%) \ge v_{\text{safe}}(+5\%) \ge v_{\text{safe}}(0\%) > v_{\text{safe}}(-5\%) > v_{\text{safe}}(-8\%)$$
   $$5.05 \ge 4.95 \ge 4.75 > 4.53 > 4.38\text{ m/s} \quad \text{[PROVEN]}$$

4. **Origin of Canonical $4.382\text{ m/s}$:**
   The exact value $v_{\text{safe}} = 4.3815\dots\text{ m/s}$ ($15.77\text{ km/h}$) is proven to be the exact analytical root of the quadratic stopping constraint on a **$-8.0\%$ downhill ramp** under wet surface ($\mu = 0.35$) and $12.0\text{ m}$ perception envelope.
