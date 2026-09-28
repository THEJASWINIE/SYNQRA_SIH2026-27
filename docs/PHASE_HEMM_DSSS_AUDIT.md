# PHASE HEMM DSSS & FAIL-SAFE FORENSIC AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Problem:** Safe and Efficient Operation of Mine Vehicles in Fog and Low-Visibility Conditions in Open Cast Iron Ore Mines  
**Target Mine Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Chhattisgarh  
**Audit Date:** 2026-09-18  
**Audit Classification:** FORENSIC EVIDENCE & ARCHITECTURAL BASELINE AUDIT (Zero Modification Phase)

---

## 1. EXECUTIVE SUMMARY & AUDIT SCOPE

In accordance with PART 1 of the Phase Specification, a complete forensic audit of the `FOG-ORCHESTRATOR 2.0` codebase was conducted prior to making any code modifications. 

The audit evaluated 21 architectural and physical dimensions across all modules, configurations, tests, and documentation to identify:
1. Current HEMM physics, vehicle models, safe speed solvers, stopping distance implementations, and headway/capacity representations.
2. The exact degree of consistency between the authoritative physics engine (`fog_safe`), the Digital Twin (`SYNQRA_SIH2026-27-main` / `twin`), the central orchestrator (`fog_orchestrator`), and the command/telemetry gateway boundaries.
3. The current state of wireless communications, confirming the physical status of the SX1278 transceivers (CSS-LoRa) versus the conceptual/research DSSS/PN multi-gateway architecture.
4. All hardcoded parameters, legacy values, sign convention conflicts, and test fixtures needing canonical harmonization.

---

## 2. DETAILED FORENSIC FINDINGS BY SYSTEM COMPONENT

### 2.1 Current HEMM Physics Implementation
- **Authoritative Engine:** `fog_safe` (`fog_safe/dynamics.py`, `fog_safe/braking.py`, `fog_safe/retarder.py`, `fog_safe/safety.py`).
  - Canonical longitudinal force balance:
    $$m \frac{dv}{dt} = F_{\text{drive}} + F_{\text{grade}} - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$
  - Deceleration during emergency stop ($F_{\text{drive}} = 0$):
    $$a_{\text{dec}} = \frac{F_{\text{brake\_max}} + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}}{m}$$
  - Rolling resistance: $F_{\text{roll}} = C_{\text{rr}} \cdot m \cdot g \cdot \cos\theta$.
  - Aerodynamic drag: $F_{\text{aero}} = 0.5 \cdot \rho \cdot C_d \cdot A \cdot v^2$.
  - Downhill gravity force: $F_{\text{grade}} = m \cdot g \cdot \sin\theta$ (where $\theta > 0$ represents downhill forward pull).
- **Compatibility Adapter:** `SYNQRA_SIH2026-27-main/models/vehicle_physics.py`.
  - Implements the P2 Architectural Ruling: it does NOT compute independent physics formulas; it maps legacy positional arguments to `fog_safe.safety.solve_safe_speed()`.
- **Duplicate Implementation Detected:** `fog_orchestrator/tier1_governor/vehicle_physics.py` and `safety_governor.py`.
  - An earlier independent implementation of vehicle deceleration and retarder limits exists in `fog_orchestrator/tier1_governor/`. While mathematically similar, it creates a potential competing source of truth if invoked directly rather than through `fog_safe`.

### 2.2 Current Vehicle Model
- **Dataclass:** `fog_safe/vehicle.py::MiningVehicle`.
  - Properties: `mass`, `power`, `hardware_brake_max`, `c_rr`, `Cd`, `frontal_area`, `wheel_radius`.
- **Target Reference Model:** BEML BH100 (100-tonne class rigid rear dump truck).
  - Unladen tare mass: $74{,}000\text{ kg}$ (OEM documented).
  - Rated payload: $91{,}500\text{ kg}$ (OEM documented).
  - Gross operating machine weight: $165{,}500\text{ kg}$ (OEM documented).
- **Discrepancy Audit:**
  - `fog_safe/config.py`: specifies `mass_loaded = 165000.0 kg` and `payload_rated = 91000.0 kg` (rounded legacy numbers).
  - `SYNQRA_SIH2026-27-main/config/vehicle.yaml`: specifies `mass_loaded_kg = 165000.0 kg` and `max_service_brake_force_n = 600000.0 N` (legacy).
  - Canonical specification (`config/bailadila_hemm_canonical.yaml` / Phase 7): establishes exact OEM values $165{,}500\text{ kg}$ and $550{,}000\text{ N}$.

### 2.3 Current Safe-Speed Solver
- **Authoritative Solver:** `fog_safe.safety.solve_safe_speed()`.
  - Evaluates multi-constraint envelope:
    $$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$
  - Optional traction ceiling: $v_{\text{traction\_ceiling}} = \text{factor} \cdot \mu$.
  - Fail-Closed Behavior: if $\mu_{\text{effective}} \le 0$ or non-finite, returns $v_{\text{safe}} = 0.0\text{ m/s}$ with `primary_constraint = "INVALID_FRICTION"`.
  - Curve Lateral Limit: $v_{\text{curve}} = \sqrt{\mu \cdot g \cdot R_{\text{curve}}}$; straight road ($R = \infty$) yields $v_{\text{curve}} = \infty$. Zero/negative/NaN radius fails closed ($v_{\text{curve}} = 0.0$).

### 2.4 Current Stopping-Distance Implementation
- **Analytical Formulation:**
  $$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
  $$\tau_{\text{total}} = \tau_{\text{sensor}} + \tau_{\text{comm}} + \tau_{\text{decision}} + \tau_{\text{can}} + \tau_{\text{actuator}}$$
- **Analytical Solver for $v_{\text{stop}}$:**
  Solves quadratic constraint $S_{\text{stop}}(v) + S_{\text{margin}}(v) \le R_{\text{effective}}$:
  $$\frac{1}{2 a_{\text{dec}}} v^2 + [\tau_{\text{total}} + k_{\text{comm}}(1 - C_{\text{comm}})] v + (S_{\text{base}} - R_{\text{effective}}) = 0$$
- **Latency Budget Status:**
  - Prior baseline: $\tau_{\text{total}} = 0.450\text{ s}$ (sensor $100\text{ ms}$ + comm $50\text{ ms}$ + decision $50\text{ ms}$ + actuator $200\text{ ms}$ + CAN $50\text{ ms}$).
  - Phase 7 Deep Research Update: separates V2V ($\tau_{\text{v2v}} = 50\text{ ms}$) from gateway upstream ($\tau_{\text{gw}} = 80\text{ ms}$), yielding $\tau_{\text{total}} = 0.530\text{ s}$ autonomous end-to-end.
  - CAN latency status: $50\text{ ms}$ assumed baseline is conservative vs TWAI/CAN bench characterized P95 ($19.17\text{ ms}$) and literature ($<10\text{ ms}$). Remains tagged `ASSUMED` pending physical vehicle logging.

### 2.5 Current Headway Model
- **Implementation:** `fog_safe/headway.py::calculate_safe_headway()`.
  - Distance Headway: $H_{\text{safe}} = S_{\text{stop}}(v_{\text{lead}}) + S_{\text{margin}} + L_{\text{veh}}$ (in meters).
  - Time Headway: $T_{\text{headway}} = H_{\text{safe}} / v_{\text{follower}}$ (in seconds).
  - Physical Invariant: strictly distinguishes spatial distance (m) from temporal gap (s). Verified that lower visibility $\to$ lower safe speed $\to$ increased headway spacing.

### 2.6 Current Road-Capacity Model
- **Implementation:** `fog_safe/metrics.py` and `docs/STAGE5_2_CAPACITY_HIERARCHY.md`.
- **Classification Hierarchy:**
  1. `THEORETICAL_KINEMATIC`: $C_{\text{kin}} = \frac{3600 \cdot v_{\text{safe}}}{H_{\text{safe}}}$ (vehicles per hour per lane). Peak theoretical value ~700.5 vph.
  2. `PRACTICAL_ROAD`: Accounts for platoon turbulence, lane merging, and passing restrictions (~600 vph).
  3. `SERVICE_RESOURCE`: Governed by crusher tipping/hopper cycle ($T_{\text{service}} = 200\text{ s} \to 18\text{ trucks/hr} \times 91.5\text{ t} = 1647\text{ TPH}$).
- **Contradiction Audit:** Completely eliminates historical confusion between theoretical road flux (700.5 vph), fleet dispatch (92.4 vph / 92.41 km/h), and crusher sustainable capacity (18 vph / 1647 TPH).

### 2.7 Current Queue / Bottleneck Engine
- **Implementation:** `fog_orchestrator/tier3_central/bottleneck_analyzer.py` and `optimizer.py`.
  - Analyzes segment density vs critical density, identifies bottleneck junctions, and calculates slot reservations to prevent switchback starvation and crusher spillback.

### 2.8 Current Digital Twin
- **Authoritative State Store:** `TwinStateStore` in `fog_orchestrator/tier3_central/digital_twin.py`.
- **Projection Layer:** `twin_projection.py` (projects authoritative state to HMI and 3D visualization clients).
- **Client Adapters:** `integration_adapters/canonical_twin_client.py`.
- **Architectural Rule:** Digital Twin is authoritative; visualization tools (`game_ui.py`, Pygame, web HMI) are pure consumers.

### 2.9 Current Vehicle Simulator
- **Simulation Implementations:**
  1. `fog_safe/simulator.py`: Single-vehicle closed-loop dynamics simulator.
  2. `SYNQRA_SIH2026-27-main/twin/simulator.py`: Multi-vehicle network haulage simulator.
  3. `hardware_emulator.py`: Emulates physical ESP32 telemetry generation and command ingestion for automated testing.
- **Double-Stepping Audit:** Verified that motion integration updates vehicle position exactly once per simulation timestep $dt$.

### 2.10 Current Command Gateway
- **Implementation:** `command_gateway.py`.
  - Validates `vehicle_id`, sequence monotonic increase, command freshness (`max_recommendation_age_seconds = 5.0 s`), action legality (`TARGET_SPEED`, `HOLD`, `STOP`, `RELEASE`), and safety state dependency.
  - ACK tracking with `command_ack_timeout_seconds = 3.0 s`.
  - Enforces authority: reads `v_safe` from Digital Twin; fails closed if safety state is stale or contradictory.

### 2.11 Current Telemetry Ingestion Path
- **Implementation:** `telemetry_ingest.py` (`NormalizedTelemetry`, `TelemetryIngestService`).
  - Wire formats parsed:
    - V2V format: `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz` (via `v2v_packet_parser.py`).
    - Gateway serial format: `V=TRUCK_01,SEQ=..,RPM=..`.
    - HMI HTTP JSON: `POST /api/hardware/telemetry`.
  - Atomic writes to `TwinStateStore`.
  - Refuses to fabricate GNSS coordinates, heading, visibility, or road association as hardware measurements.

### 2.12 Current Vehicle Firmware
- **Firmware Artifacts:**
  - `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino` (TRUCK_02 motor control, optical RPM sensor, MPU6050 IMU, LoRa transceiver).
  - `esp32_code/LORA_GATEWAY_RECEIVER/LORA_GATEWAY_RECEIVER.ino` (Gateway receiver, SX1278 LoRa to Wi-Fi UDP/HTTP).

### 2.13 Current Watchdog & Timeout Logic
- **Three Separate Timeouts (Deliberately Not Merged):**
  1. Gateway Command Freshness Window: `max_recommendation_age_seconds = 5.0 s` (`integration_config.json`).
  2. Command ACK Timeout: `command_ack_timeout_seconds = 3.0 s` (`integration_config.json`).
  3. Physical Firmware Watchdog: `COMMAND_TIMEOUT_MS = 15000 ms` in ESP32 firmware. If no valid command arrives within 15 seconds, motor output halts ($0\text{ PWM}$).
  4. Local Governor Fast Watchdog: $1.0\text{ s}$ timeout for loss of active communications in degraded visibility.

### 2.14 Current Communication Abstraction
- **Implementation:** `fog_safe/communication.py::CommunicationModel`.
  - Models communication confidence $C_{\text{comm}} \in [0.0, 1.0]$.
  - Dynamic safety margin penalty: $S_{\text{margin}} = S_{\text{base}} + k_{\text{comm}} \cdot (1 - C_{\text{comm}}) \cdot v$.

### 2.15 Existing LoRa Implementation
- **Hardware:** HopeRF RFM95W / AI-Thinker Ra-02 with Semtech SX1278 transceiver.
- **Modulation:** Chirp Spread Spectrum (CSS) LoRa at $433\text{ MHz}$, Spreading Factor 7 (SF7), Bandwidth $125\text{ kHz}$, Coding Rate 4/5.
- **Physical Dataset:** `data/phase6_rf_packets.csv` ($N = 1{,}050$ bench transmissions).

### 2.16 Existing Gateway-Selection Code
- **Status:** **NOT IMPLEMENTED IN CODE.**
- The existing hardware setup features a single physical LoRa Gateway. Multi-gateway selection, beacon tracking, and handover logic exist only in concept and requirements.
- **Action Required:** Create `integration_adapters/dsss_gateway_selector.py` to model PN beacon correlation, candidate gateway evaluation, and anti-flapping handover.

### 2.17 Existing PN / Correlation / DSSS Code
- **Status:** **NOT IMPLEMENTED IN PHY HARDWARE.**
- The SX1278 Ra-02 is a proprietary CSS-LoRa modem; it does not execute arbitrary direct-sequence pseudo-noise (PN) chipping sequences.
- **Action Required:** Explicitly document the distinction between the physical LoRa prototype and the research DSSS/PN architectural model.

### 2.18 Hardcoded HEMM Values Audit
| Parameter | Location | Hardcoded Value | Canonical Value | Status |
|-----------|----------|-----------------|-----------------|--------|
| `mass_loaded` | `SYNQRA_SIH2026-27-main/config/vehicle.yaml` | $165{,}000\text{ kg}$ | $165{,}500\text{ kg}$ | Superseded |
| `mass_loaded` | `fog_safe/config.py` | $165{,}000\text{ kg}$ | $165{,}500\text{ kg}$ | Superseded |
| `mass_loaded` | `fog_orchestrator/core/config.py` | $165{,}000\text{ kg}$ | $165{,}500\text{ kg}$ | Superseded |
| `hardware_brake_max` | `SYNQRA_SIH2026-27-main/config/vehicle.yaml` | $600{,}000\text{ N}$ | $550{,}000\text{ N}$ | Superseded |
| `drag_coefficient` | `fog_safe/config.py` | $0.70$ | $0.80$ | Superseded |
| `frontal_area` | `fog_safe/config.py` | $20.0\text{ m}^2$ | $22.0\text{ m}^2$ | Superseded |
| `tau_total_autonomous` | `SYNQRA_SIH2026-27-main/models/vehicle_physics.py` | $0.25\text{ s}$ / $0.45\text{ s}$ | $0.530\text{ s}$ | Superseded |
| `tau_human` | `fog_safe/config.py` | $0.50\text{ s}$ | $1.200\text{ s}$ | Superseded |

### 2.19 Grade Sign Convention Audit
- **Mine / Civil Engineering / GIS Standard:**
  - $+8\%$ is UPHILL ($\Delta h > 0$, gravity opposes vehicle motion, increases braking deceleration).
  - $-8\%$ is DOWNHILL ($\Delta h < 0$, gravity pulls vehicle forward, decreases braking deceleration).
- **Internal `fog_safe` Physics Convention:**
  - $\theta > 0$ defines a forward downhill slope ($F_{\text{grade}} = m g \sin\theta > 0$).
  - $a_{\text{dec}} = [F_{\text{brake}} + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}] / m$.
- **Harmonization Status:**
  - Handled cleanly by `GradeAdapter` (`integration_adapters/grade_adapter.py`). All external interfaces pass civil grades, which are inverted at the system boundary for internal force calculations.

### 2.20 Test Fixtures & Legacy Assumptions
- `tests/test_physics_unification.py` uses legacy test base with $m = 165{,}000\text{ kg}$, $F_{\text{brake}} = 600{,}000\text{ N}$, $\tau = 0.25\text{ s}$.
- `tests/test_phase6_timing_and_rf.py` references `integration_adapters/fail_safe_controller.py` and `config/bailadila_hemm_canonical.yaml`.
- Missing modules must be provided cleanly without breaking legacy compatibility tests.

---

## 3. AUDIT CONCLUSION & ACTION MATRIX

The audit confirms that the architecture is solid and coherent, but requires:
1. Publishing `config/bailadila_hemm_canonical.yaml` with strict provenance tags.
2. Formalizing `docs/GRADE_CONVENTION_FINAL.md`.
3. Creating `docs/HEMM_PARAMETER_MIGRATION.md` to catalog all superseded parameters.
4. Implementing `integration_adapters/fail_safe_controller.py` and `integration_adapters/dsss_gateway_selector.py`.
5. Delivering automated test matrices FS-01 to FS-16, verifying invariants I1 to I12.
6. Producing the comprehensive final report `docs/PHASE_HEMM_DSSS_FAILSAFE_FINAL.md`.
