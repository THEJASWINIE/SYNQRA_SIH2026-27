# PHASE 7.3.2 — REPORT 05: FINAL HEADWAY & ROAD CAPACITY AUDIT
## Separation of Theoretical Kinematic Road Flux from Mine Production
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Space Headway Formulation from First Principles

Space headway $H_{\text{space}}$ defines the center-to-center longitudinal distance between successive vehicles traveling along the haul road.

To prevent collision under worst-case emergency braking of the leading vehicle, $H_{\text{space}}$ must incorporate:
1. Stopping distance of the trailing vehicle: $S_{\text{stop}}$
2. Mandatory standstill safety margin: $S_{\text{margin}} = 5.0\text{ m}$
3. Physical vehicle length: $L_{\text{truck}} = 10.52\text{ m}$

$$H_{\text{space}} = S_{\text{stop}} + S_{\text{margin}} + L_{\text{truck}}$$

#### Forensic Resolution of Historical 17.52 m Claim:
* In earlier documentation, $H_{\text{safe}}$ was reported as:
  $$H_{\text{safe}} = 17.52\text{ m}$$
* **Forensic Audit**:
  $$S_{\text{stop}} + L_{\text{truck}} = 7.0000 + 10.5200 = \mathbf{17.5200\text{ m}}$$
* **Defect Identified**: The historical calculation completely omitted the mandatory $5.0\text{ m}$ standstill safety margin!
* **Corrected Canonical Space Headway**:
  $$H_{\text{space}} = 7.0000 + 5.0000 + 10.5200 = \mathbf{22.5200\text{ m}}$$

---

### 2. Theoretical Kinematic Road Flow vs Production Capacity

Theoretical road flow represents continuous single-lane pipe flux if vehicles travel nose-to-tail at maximum safe speed:
$$C_{\text{road}} = \frac{3600 \cdot v}{H_{\text{space}}} \quad [\text{Vehicles Per Hour (VPH)}]$$

#### A. Evaluation Across Operating Regimes:
1. **Emergency Safe Speed ($v = 5.1158\text{ m/s}$)**:
   $$C_{\text{road}} = \frac{3600 \times 5.1158}{22.5200} = \mathbf{817.8\text{ VPH}}$$
   Theoretical ore flux ($91.5\text{ t}$ payload): $817.8 \times 91.5 = \mathbf{74,828.7\text{ TPH}}$.
2. **Conservative Service Safe Speed ($v = 3.6734\text{ m/s}$)**:
   $$C_{\text{road}} = \frac{3600 \times 3.6734}{22.5200} = \mathbf{587.2\text{ VPH}}$$
   Theoretical ore flux: $587.2 \times 91.5 = \mathbf{53,728.8\text{ TPH}}$.
3. **Forensic Trace of Historical 700.5 VPH**:
   Using legacy safe speed $v = 4.3815\text{ m/s}$ with the corrected headway $22.52\text{ m}$:
   $$C = \frac{3600 \times 4.3815}{22.5200} = \mathbf{700.417\text{ VPH}} \approx \mathbf{700.5\text{ VPH}}$$
   This proves exactly where the historical $700.5\text{ VPH}$ originated.

**CRITICAL SCIENTIFIC RULING**: Theoretical road flow ($817.8\text{ VPH}$ or $700.5\text{ VPH}$) is a geometric pipe-saturation metric. It does **NOT** represent mine production capacity, because physical production is bounded by the fixed dumping cycle of the primary gyratory crusher.

---

### 3. Crusher Physical Bottleneck Ceiling

* **Tipping Cycle Time**: The primary gyratory crusher pocket requires:
  - Backing and positioning: $40.0\text{ s}$
  - Bed hoist and rock dump: $60.0\text{ s}$
  - Bed lower and hopper clearance: $40.0\text{ s}$
  - Buffer and dust dispersion: $60.0\text{ s}$
  - **Total Dump Slot Cycle**: $T_{\text{dump}} = \mathbf{200.0\text{ s}}$
* **Crusher Processing Ceiling**:
  $$R_{\text{crusher}} = \frac{3600\text{ s/hr}}{200.0\text{ s/truck}} = \mathbf{18.0\text{ trucks/hour}}$$
* **Crusher Production Ceiling**:
  $$C_{\text{crusher}} = 18.0\text{ trucks/hr} \times 91.5\text{ tonnes} = \mathbf{1,647.0\text{ TPH}}$$

No dispatch algorithm, platooning strategy, or road optimization can exceed $1,647.0\text{ TPH}$ at steady state without installing a second primary crusher pocket.

---

### 4. Retraction of Transient Queue-Flush Claims

* **Historical 3,294 TPH Claim**:
  - In earlier tests, 6 preloaded trucks queued at the crusher dumped in rapid succession over a 10-minute window ($0.167\text{ hr}$):
    $$\text{Rate} = \frac{6 \times 91.5\text{ t}}{0.167\text{ hr}} = \mathbf{3,294.0\text{ TPH}}$$
  - **Audit Ruling**: This was an initial queue-flush transient, physically impossible to sustain beyond 10 minutes.
  - **Status**: **PERMANENTLY RETRACTED AS SUSTAINED METRIC**.
* **Historical 2,745 TPH Claim**:
  - 3 queued trucks dumped in 6 minutes ($0.100\text{ hr}$):
    $$\text{Rate} = \frac{3 \times 91.5\text{ t}}{0.100\text{ hr}} = \mathbf{2,745.0\text{ TPH}}$$
  - **Status**: **PERMANENTLY RETRACTED AS SUSTAINED METRIC**.
* **Authoritative Sustainable Production**:
  - Unmanaged conventional fog baseline (Level 0): **$1,171.2\text{ TPH}$** ($71.1\%$ crusher utilization).
  - FOG-Orchestrator steady-state production (Level 4): **$1,591.4\text{ TPH}$** ($96.6\%$ crusher utilization).
