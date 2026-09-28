# EXPERIMENT E15 — ARCHITECTURAL TIMING SEPARATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Dual-Loop Real-Time Control & Safety Boundary Analysis  
**Evidence Level:** L1 — Formal Architecture Proof / L6 — Control Timing Formulation  

---

## 1. Architectural Timing Invariant

> [!IMPORTANT]
> **THEOREM OF TIMING SEPARATION**  
> Gateway propagation delay ($\tau_{\text{gateway}}$) and central cloud optimization latency ($\tau_{\text{fleet}}$) **DO NOT ENTER** the vehicle physical emergency stopping distance equation ($S_{\text{stop}}$).
>
> Emergency stopping is governed entirely by the **Tier-1 Local Autonomous Safety Loop**.

---

## 2. Dual-Loop Timing Budget Comparison

```
+-----------------------------------------------------------------------------------------+
| LOOP 1: TIER-1 LOCAL SAFETY GOVERNOR LOOP (tau_local_safety = 375 ms nominal)           |
|                                                                                         |
|  [Onboard Sensors] --(100ms)--> [Local Governor] --(50ms)--> [CAN Bus] --(25ms)-->     |
|                                [Brake Actuator] --(200ms)--> [Wheel Deceleration Onset] |
+-----------------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------------+
| LOOP 2: TIER-2 CENTRAL FLEET ORCHESTRATION LOOP (tau_fleet_command = 610-710 ms nom)    |
|                                                                                         |
|  [Truck Telemetry] --(LoRa 150ms)--> [Gateway ESP32] --(Wi-Fi 30ms)-->                  |
|  [FastAPI Backend] --(Processing 50ms)--> [LP Optimizer] --(Solving 80ms)-->           |
|  [Gateway Downlink] --(LoRa 150ms)--> [Truck Receiver] --(CAN 50ms)-->                  |
|  [Local Governor Clamp Validation]                                                      |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Mathematical Proof: Why Gateway Latency Is Excluded from $S_{\text{stop}}$

Let $S_{\text{stop}}$ denote the distance required to bring a haul truck to a complete halt from initial speed $v$ upon detection of an obstacle at distance $d_{\text{obs}}$.

1. **Local Path:**  
   The obstacle is detected by onboard radar/cameras or communicated directly over V2V peer beacon:
   $$t_{\text{detect}} = t_0 + \tau_{\text{sensor}}$$
   The onboard governor issues the brake command across the vehicle's internal CAN bus:
   $$t_{\text{brake\_cmd}} = t_{\text{detect}} + \tau_{\text{decision}} + \tau_{\text{CAN}}$$
   The air-over-hydraulic actuator develops retarding torque:
   $$t_{\text{decel\_start}} = t_{\text{brake\_cmd}} + \tau_{\text{actuator}} = t_0 + \tau_{\text{local\_total}}$$
   Therefore, reaction distance is:
   $$d_{\text{react}} = v \cdot \tau_{\text{local\_total}}$$
   where $\tau_{\text{local\_total}} \in [0.324\text{ s}, 0.437\text{ s}]$.

2. **Central Path Independence:**  
   At no point in this sequence does the vehicle transmit telemetry to the gateway, wait for cloud optimization, or await a downlink command to initiate emergency braking.
   
   If central dispatch transmits an unsafe speed command ($v_{\text{cmd}} > v_{\text{safe}}$), the onboard governor clamps it to $v_{\text{safe}}$ before actuation.  
   If the central gateway is completely destroyed, the vehicle continues operating safely under local sensor governance.

3. **Consequence of Conflation:**  
   If an engineer erroneously included the full two-way gateway dispatch loop ($\tau_{\text{fleet}} \approx 0.710\text{ s}$) into $S_{\text{stop}}$, the calculated reaction distance at 20 km/h would inflate by:
   $$\Delta d = 5.56\text{ m/s} \times (0.710\text{ s} - 0.375\text{ s}) = +1.86\text{ meters}$$
   This would force an unnecessarily low speed limit without any improvement in safety. The architectural separation is both scientifically rigorous and operationally essential.
