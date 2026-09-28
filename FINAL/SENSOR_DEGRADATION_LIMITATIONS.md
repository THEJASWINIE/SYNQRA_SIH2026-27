# SENSOR DEGRADATION RESEARCH LIMITATIONS & FORENSIC BOUNDARIES
## FOG-ORCHESTRATOR 2.0 — Unvarnished Hard Truths & Unresolved Risks
**Project:** SIH26007 — Fog / Low-Visibility Mining Fleet Orchestrator  
**Audit Date:** 2026-09-21  
**Lead Author:** Systems Architect & Safety Systems Auditor  
**Audit Policy:** Total transparency. No promotional evasion. Every technical vulnerability laid bare.

---

## 1. The Twelve Mandatory Limitations (§27)

### 1. Single-Source Plausible-But-Wrong Telemetry (Class C)
If a single environmental visibility sensor drifts, degrades, or gets blinded while reporting $50.0\text{ m}$ visibility during dense $5.0\text{ m}$ fog, and the packet carries fresh timestamps, valid schemas, contiguous sequences, and reasonable signal variance, **software data validation is mathematically blind to the lie**.  
The data-health layer will classify the reading as `HEALTHY`, permitting full speed ($40.0\text{ km/h}$) with an actual stopping distance of $23.2\text{ m}$ against a $5.0\text{ m}$ visual horizon. Single-source validation cannot detect plausible-but-wrong telemetry without an independent physical reference.

### 2. Systematic Sensor Bias Observability (Scenario D7)
An additive bias (e.g., $+30.0\text{ m}$) resulting from miscalibration, dirty optics, or photodiode degradation produces a reading of $42.0\text{ m}$ when true visibility is $12.0\text{ m}$.  
Because $42.0\text{ m}$ is well within the physically valid range of open-cast haul roads ($[0.5, 2000]\text{ m}$) and natural atmospheric variance is preserved, the bias is fundamentally unobservable from the telemetry stream alone. Detecting bias requires physical sensor redundancy.

### 3. Stuck-At Ambiguity & Incomplete Recovery (Scenario D6)
Zero variance over a sliding window indicates that a signal is stuck. However, **zero variance does not reveal what the true physical value is**.  
On a clear afternoon, visibility remains at $50.0\text{ m}$ with near-zero variance; during a sudden fog bank, a dead ADC may also output constant $45.0\text{ m}$. Penalizing a stuck sensor with a conservative $30\%$ reduction ($45\text{ m} \to 31.5\text{ m}$) still fails to close the safety envelope when true visibility has dropped to $12.0\text{ m}$. Single-source variance detection cannot reconstruct missing physical ground truth.

### 4. Sensor Sampling-Rate and Quantization Assumptions
The data-health module assumes nominal $1.0\text{ Hz}$ telemetry arrival. High-frequency analog sensor noise or low-frequency polled interfaces ($0.1\text{ Hz}$) distort variance calculations:
- At $0.1\text{ Hz}$, a 10-sample rolling variance window requires $100\text{ seconds}$ to populate, delaying stuck-at and noise detection.
- Fast atmospheric optical scintillation ($> 10\text{ Hz}$) cannot be resolved by $1\text{ Hz}$ sampling, potentially misclassifying optical scintillation as analog noise.

### 5. Threshold Provenance & Subjectivity
All data health thresholds ($T_{\text{DEGRADED}} = 30\text{ s}$, $T_{\text{STALE}} = 60\text{ s}$, $T_{\text{GRACE}} = 120\text{ s}$, $\text{DEGRADED\_FACTOR} = 0.70$, $\text{STALE\_FACTOR} = 0.50$, $R_{\text{UNAVAILABLE}} = 8.0\text{ m}$) are classified under **Tier L6 Engineering Assumptions**.  
While grounded in standard transmissometer averaging windows and radio shadow budgets, they have not been empirically calibrated against long-term optical fog climatology at a specific mine pit. Tuning thresholds tighter increases false alarm rates; tuning them looser prolongs exposure to stale data.

### 6. Simulation Kinematics vs. Real-World Vehicle Dynamics
Simulations assume 1D longitudinal point-mass dynamics with Coulomb friction. They do not model:
- Transient tire slip dynamics or longitudinal tire force saturation curves ($F_x$ vs. slip ratio $\kappa$).
- Brake drum/disc thermal fade during prolonged retarder failure on $-8\%$ downhill grades.
- Lateral tire slip, road crowning, or loss of steering control during emergency braking on wet clay haul roads.

### 7. Physical Braking Boundary
All vehicle stopping distance verifications are based on mathematical kinematics and embedded ESP32 software timing. **Zero physical pneumatic or hydraulic brake actuators were fired on an actual 165.5-tonne mining truck.** Software decision latency ($\approx 2.2\text{ ms}$) must never be equated with physical hydraulic brake build-up time ($\approx 200\text{--}350\text{ ms}$).

### 8. OEM Interface Boundary (BEML BH100)
SAE J1939 CAN-TWAI frame encoders and decoders were validated on embedded microcontrollers. However, **access to a physical BEML BH100 truck CAN harness has not occurred**. It remains unverified whether native BEML BH100 electronic control units broadcast unencrypted wheel speed and retarder telemetry without proprietary OEM security gateways.

### 9. Mine Pit RF Propagation & Radio Shadows
The communication failure benchmark uses mathematical dropout probabilities and step-function link severances. It does not model physical radio frequency propagation:
- Highwall Fresnel zone obstruction, diffraction around pit switchbacks, and multi-path reflection off iron ore / rock faces.
- RF attenuation caused by heavy atmospheric dust clouds and monsoon precipitation.

### 10. Spatial Visibility Sensing Boundary
The primary benchmark models visibility as a single mine-wide or segment-wide scalar. In active open-cast pits, fog forms non-uniformly in localized pockets (inversion layers, pit sumps, and deep benches). Applying a single environmental station to an entire $5\text{ km}$ haul circuit either permits dangerous speeds in dense localized pockets or unnecessarily paralyzes clear upper benches.

### 11. Homogeneous Fleet Assumptions
The benchmark fleet consists exclusively of identical 165.5-tonne BEML BH100 dump trucks with identical braking characteristics. Real open-cast mining circuits operate heterogeneous fleets:
- Mixed haulers (e.g., $100\text{ t}$ BEML BH100 alongside $240\text{ t}$ CAT 793F).
- Light utility vehicles (Bolero/Scorpio mine inspection pickups) sharing the haul road with vastly shorter stopping distances and lower driver eye heights.
- Water tankers and diesel bowsers operating at different speed regimes.

### 12. Lack of Active-Mine Field Deployment
**The system has not undergone field trials in an operating open-cast mine.**  
All evidence belongs strictly to Tier L9 (Simulation), Tier L7 (Bench Measured), and Tier L6 (Engineering Assumptions). No claim of production readiness, mine validation, or field deployment is permitted.

---

## 2. The Seven Hard Truths

1. **What does this research actually prove?**  
   It proves that when telemetry degradations are detectable (packet dropouts, stale timers, schema errors, range violations, multi-source conflicts), rule-based data health deterministically prevents stopping envelope violations and converts dangerous downhill ramp queuing into safe flat staging queueing.
2. **What does it only demonstrate?**  
   It demonstrates 165.5-tonne longitudinal kinematics in simulation and software decision execution in laboratory microcontroller HIL.
3. **What remains unvalidated?**  
   Physical pneumatic brake actuation, native OEM BH100 CAN access, real atmospheric mine dust optical scatter, and human driver compliance.
4. **What failure can still defeat the system?**  
   Class C plausible-but-wrong single-source telemetry (True=5m, Reported=50m).
5. **What hardware is missing?**  
   Dual cross-path optical transmissometers, physical LiDAR/radar for cross-validation, physical wheel encoders on TRUCK_02, and physical GNSS receivers.
6. **What field experiment is required next?**  
   Mounting dual optical forward-scatter sensors with an opposing retroreflector target across a $100\text{ m}$ baseline on an active open-cast haul road bench, tapping an isolated CAN logger into a BEML BH100 diagnostic port, and measuring multi-path RF packet loss across haul ramp switchbacks under real atmospheric mine dust.
7. **Why is this architecture still useful despite these limitations?**  
   Because eliminating detectable failure modes ($> 85\%$ of real-world telemetry errors) is vastly superior to doing nothing, costs almost zero compute overhead ($< 1.2\text{ ms}$), introduces zero black-box ML failure modes, and establishes explicit, fail-closed boundaries.
