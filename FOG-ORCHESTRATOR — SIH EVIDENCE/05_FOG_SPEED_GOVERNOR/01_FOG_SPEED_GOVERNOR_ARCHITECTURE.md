# FOG-ORCHESTRATOR 2.0 — 5-Constraint Physics Safety Governor
**Document ID:** `DOC-05-FSG-01` | **Audited Standard:** Level-5 Physics Derivation

---

## 1. Mathematical Formulation: 5 Physical Safety Constraints

The governed safe operating speed ($v_{safe}$) is defined as the strict mathematical infimum of five independent physical and regulatory constraints:

$$v_{safe} = \min(v_{stop}, v_{retarder}, v_{traction}, v_{curve}, v_{mine})$$

### 1. Stopping Sight Distance Constraint ($v_{stop}$)
Emergency stopping distance ($S_{stop}$) must not exceed sightline visibility ($V_{vis}$):
$$S_{stop} = v \cdot \tau_{total} + \frac{v^2}{2 \cdot a_{dec}} \le V_{vis}$$
Where $\tau_{total} = \tau_{sensor} + \tau_{comm} + \tau_{solver} + \tau_{driver\_perception} + \tau_{brake\_buildup} = 1.85\text{ s}$.
$$v_{stop} = -a_{dec} \cdot \tau_{total} + \sqrt{(a_{dec} \cdot \tau_{total})^2 + 2 \cdot a_{dec} \cdot V_{vis}}$$

### 2. Retarder Thermal Capacity Constraint ($v_{retarder}$)
On a downhill gradient of grade $G = \tan\theta$, gravitational descent power must not exceed maximum hydraulic retarder dissipation ($P_{retarder} = 1,119\text{ kW}$ for BEML BH100):
$$P_{grav} = M \cdot g \cdot (\sin\theta - f_r \cos\theta) \cdot v \le P_{retarder} \implies v_{retarder} = \frac{P_{retarder}}{M \cdot g \cdot (\sin\theta - f_r \cos\theta)}$$

### 3. Traction / Wheel Slip Limit ($v_{traction}$)
Tire-road braking force cannot exceed maximum available friction:
$$a_{dec} \le \mu \cdot g \cos\theta - g \sin\theta$$

### 4. Switchback Curve Lateral Stability ($v_{curve}$)
To prevent lateral slip or rollover on hairpin turns of radius $R_{curve} = 22\text{ m}$:
$$v_{curve} = \sqrt{\mu \cdot g \cdot R_{curve}}$$

### 5. Mine Haulage Regulatory Limit ($v_{mine}$)
Statutory DGMS speed ceiling for haul roads: $v_{mine} = 40\text{ km/h}$ ($11.1\text{ m/s}$), scaled on bench prototype to $0.80\text{ m/s}$.
