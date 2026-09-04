# digitalTwin_FOG — V0.1 BASELINE FROZEN ARCHIVE

This document records the **frozen validation baseline** for Demo V0.1 of the FOG-ORCHESTRATOR 2.0 Task 2 Digital Twin.
All core algorithms, physical equations, safety governors, and capacity models are verified and locked.

---

## 1. Implementation Status
*   **Physics Engine**: Fully frozen and validated.
*   **Safety Governor**: Fully frozen and validated. Enforces $v_{\rm command} \le v_{\rm safe}$ at every step.
*   **Capacity Model**: Fully frozen and validated. Matches $C_r = 3600 \cdot v_{\rm safe} / H_{\rm safe\_meters}$ analytically.
*   **Queue Model**: Discrete-time queue logic ($Q(t+dt) = \max(0, Q(t) + A(t) - D(t))$) frozen and verified.
*   **Bottleneck Detector**: Score-based priority index frozen and validated.
*   **Arrival Shaping**: Closed-loop feedback release controller frozen and validated.
*   **Environments**: Smooth spatiotemporal linear transitions for fog visibility and road friction coefficient frozen and validated.
*   **Deferred Features (V0.2+)**: MILP/MPC scheduling solvers, dynamic slot allocations for switchbacks, LoRa packet loss emulations, hardware in-the-loop (HIL) ingestion, and HMI Web UI dashboards are deferred. No future code has been added to V0.1.

---

## 2. Test Results Summary
*   **Unified Testing Framework**: 17 tests executed.
*   **Status**: **17 / 17 PASS**
*   **Execution Time**: 0.558 seconds
*   **Test suite command**:
    ```powershell
    python -m unittest discover -s tests -p "test_*.py"
    ```

---

## 3. Physical & Safety Governor Verification
The longitudinal force balance and stopping envelopes are implemented in `models/vehicle_physics.py` and `models/braking.py`:
$$a_{\rm dec} = \frac{F_{\rm brake} + F_{\rm roll}}{m} + g \sin(\theta)$$
$$v_{\rm stop} = a_{\rm dec} \left( -\tau_{\text{total}} + \sqrt{\tau_{\text{total}}^2 + \frac{2}{a_{\rm dec}} (Visibility - S_{\rm margin})} \right)$$

*   **Safety Audit**: Enforced $v_{\rm command} \le v_{\rm safe}$ across all vehicle states.
    *   Total checks: **7,200** (4 vehicles * 1800 steps).
    *   Violations: **0**.
    *   Safety override governor works flawlessly.

---

## 4. Road Capacity Verification
Verified on downhill segment `ROAD_2` (representative loaded mass = $165,000\text{ kg}$, slope = $-8\%$):
*   **Clear Condition ($t = 100$s)**:
    *   $v_{\rm safe\_mps} = 11.11\text{ m/s}$ (speed limit)
    *   $H_{\rm safe\_meters} = 28.01\text{ m}$ ($H_{\rm safe\_seconds} = 2.52\text{ s}$)
    *   $C_r = 3600 \cdot v / H = \mathbf{1427.68\text{ vph}}$
*   **Dense Fog Condition ($t = 700$s)**:
    *   $v_{\rm safe\_mps} = 5.78\text{ m/s}$
    *   $H_{\rm safe\_meters} = 15.50\text{ m}$ (clamped by physical static buffer $15.5\text{ m}$) ($H_{\rm safe\_seconds} = 2.68\text{ s}$)
    *   $C_r = 3600 \cdot v / H = \mathbf{1343.46\text{ vph}}$
*   **Recovery/Damp Condition ($t = 1500$s)**:
    *   $v_{\rm safe\_mps} = 11.11\text{ m/s}$
    *   $H_{\rm safe\_meters} = 27.63\text{ m}$ ($H_{\rm safe\_seconds} = 2.49\text{ s}$)
    *   $C_r = 3600 \cdot v / H = \mathbf{1447.42\text{ vph}}$
*   **Recovery/Clear Condition ($t = 1700$s)**:
    *   $v_{\rm safe\_mps} = 11.11\text{ m/s}$
    *   $H_{\rm safe\_meters} = 28.01\text{ m}$ ($H_{\rm safe\_seconds} = 2.52\text{ s}$)
    *   $C_r = 3600 \cdot v / H = \mathbf{1427.68\text{ vph}}$

Dimensional analysis is fully verified, and both distance-based ($C_r = 3600 \cdot v / H_{\text{meters}}$) and time-based ($C_r = 3600 / H_{\text{seconds}}$) capacity equations yield identical values.

---

## 5. Queue & Bottleneck Verification
*   **Queue Conservation**: Verified by step transitions satisfying $Q(t + dt) = \max(0, Q(t) + A(t) - D(t))$.
*   **Bottleneck Score**: Dynamic calculation of priority index:
    $$B_j = \rho_j \cdot (1 + Q_j) \cdot \text{Criticality}_j$$
    Correctly identified the Crusher as the dominant bottleneck segment when fog reduced safety throughput (Crusher score = 9.00 vs Shovel score = 0.00 at t = 400s).

---

## 6. Arrival Shaping Verification
*   **Throttling Action**: Closed-loop feedback controller dynamically adjusts shovel release delay based on crusher queue accumulation.
*   **Performance**: Stabilized Crusher queue size at a maximum of **1 vehicle** compared to a runaway queue of **3 vehicles** when shaping is inactive.

---

## 7. Model Assumptions & Limitations
*   **OEM Reference Values**: BEML BH100 tare/payload/power are reference parameters. No field measurement claims are made.
*   **Synthetic Baseline Rates**: Shovel (15 vph) and Crusher (10 vph in DEMO_06) are baseline simulation values.
*   **Deterministic Weather**: Weather and visibility follow a predefined profile for validation sweeps.
*   **Aero Drag**: Aero drag is conservatively omitted in safety stopping distance calculations.
*   **Network Layout**: Static graph loop without branch routing alternatives.

---

## 8. Deferred Task 2 Features
*   **Active Switchback Coordinators (MILP/MPC)**: Block slot reservation scheduling.
*   **Probabilistic Optimization**: Robust MPC chance-constrained models.
*   **Network Multipath Routing**: Graph pathfinding alternatives.
*   **ESP32 Telemetry & Packet Loss Emulator**: Hardware integration layers.
*   **FastAPI WebSocket HMI Server**: Web UI bindings.
