# COMPLETE CASCADE FAILURE & END-TO-END CRASH ATTACK
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phase 9.1 Hostile Integration Validation**  
**Role:** Lead Safety-Critical Systems Red-Team Engineer / Principal Systems Architect  
**Date:** 2026-09-24  
**Audit Status:** AUDITED — SYSTEM SURVIVES PHYSICALLY; TIMING VIOLATION EXPOSED UNDER COMM LOSS

---

## 1. Executive Summary & Attack Conditions

The ultimate benchmark of an autonomous or assisted mining safety system is whether it survives a **simultaneous catastrophic collapse of every peripheral, network, and environmental subsystem**.

We constructed the most hostile conceivable operating scenario at NMDC Bailadila Iron Ore Mine:

### The 12-Factor Nightmare Invariant Matrix
1. **Vehicle:** Fully loaded 100-tonne HEMM (Total gross mass: $165,000\text{ kg}$).
2. **Topography:** **$-8\%$ downhill haul ramp** entering the deep pit.
3. **Atmospheric Environment:** Zero-visibility dense fog envelope ($R_{\text{eff\_true}} = 4.0\text{ m}$).
4. **Surface Condition:** Water-saturated crushed iron ore fines ($\mu = 0.35$).
5. **Primary Sensor:** Optical scatter sensor suffering sudden dropout ($R_{\text{eff}} \to \text{null}$).
6. **Primary Uplink:** 433 MHz LoRa transceiver experiences sudden deep shadowing (0 pkts received).
7. **Infrastructure Gateway:** Pit Gateway 2 suffers power outage / lightning strike (OFFLINE).
8. **DSSS Handover:** Candidate Gateway 3 in deep cut has correlation $\rho = 0.45 < 0.65$ (HANDOVER REJECTED).
9. **CAN Bus:** High-priority logging creates bus load of $95\%$ ($T_{\text{CAN}} = 45.0\text{ ms}$).
10. **Digital Twin:** Telemetry age exceeds 500 ms $\implies$ Cloud mirror enters `DISCONNECTED`.
11. **Control Room:** Backhaul fiber severed $\implies$ Dispatcher sees vehicle OFFLINE.
12. **Safe Beacon:** Emergency 433 MHz broadcast activated at 2 Hz.

---

## 2. Millisecond-by-Millisecond Execution Trace

```
Time (ms)  Subsystem                  Event / State Machine Action
-----------------------------------------------------------------------------------------------------------------
  0.0 ms   Haul Road Environment      Vehicle enters 4m dense fog bank on -8% ramp at v = 3.52 m/s.
  0.0 ms   Sensor Ingestion           Optical sensor reading drops to null (wire break / lens occlusion).
  2.5 ms   Sensor Health Engine       Stale timer starts; health transitions to DEGRADED.
 12.0 ms   Primary LoRa Gateway       Gateway 2 power failure; uplink ACK missing.
 50.0 ms   DSSS Handover Engine       Candidate Gateway 3 correlation rho = 0.45 < 0.65 (REJECTED).
150.0 ms   CAN Bus Ingestion          Bus load spikes to 95% due to high-rate engine telemetry logging.
250.0 ms   Sensor Health Engine       Sensor timeout expired (250 ms) -> Transitions to MISSING.
                                      Fail-safe default applied: Floor R_eff = 8.0 m.
300.0 ms   In-Cab Operator HMI        Data age exceeds 300 ms -> Yellow "DATA STALE" watermark appears.
500.0 ms   Gateway Heartbeat Timer    COMMUNICATION LOSS DECLARED (Heartbeat timeout 500.0 ms reached).
502.0 ms   Safe Beacon Controller     Safe Beacon activated on 433 MHz @ 2 Hz broadcast.
505.0 ms   Central Digital Twin       Server-side heartbeat timeout -> Vehicle marked OFFLINE on dashboard.
520.0 ms   Local Safety Governor      Remote dispatch rejected; autonomous local authority takes over.
540.0 ms   Local Safety Governor      Calculates v_safe = 0.0 m/s (Emergency Halt due to blindout + comm loss).
541.0 ms   Chassis Gateway (TWAI)     Emergency Stop Frame 0x0C000003 queued on CAN bus.
586.0 ms   Chassis Brake Controller   Frame delivered to Brake ECU (45.0 ms delivery delay due to 95% bus load).
936.0 ms   Hydraulic Calipers         Full 18.5 MPa hydraulic brake pressure achieved (350 ms caliper lag).
2150.0 ms   Haul Truck Kinematics      Vehicle comes to a complete standstill on -8% ramp.
-----------------------------------------------------------------------------------------------------------------
```

---

## 3. Hostile Questions & Answers

### Q1: Did the local governor still act when every external system failed?
**YES.** The Tier-1 governor runs locally inside FreeRTOS on the ESP32-S3 chassis microcontroller. It requires zero cloud connectivity, zero gateway handshakes, and zero control-room authorizations. When the remote heartbeat died at $t = 500\text{ ms}$, the local state machine clamped commanded speed to $0.0\text{ m/s}$ within **$40\text{ ms}$**.

### Q2: What was the worst-case reaction delay?
**$935.0\text{ ms}$.**
- $500.0\text{ ms}$ (Communication heartbeat loss timeout)
- $+ 40.0\text{ ms}$ (Local governor solve and task scheduling)
- $+ 45.0\text{ ms}$ (CAN bus arbitration queue delay under 95% load)
- $+ 350.0\text{ ms}$ (Worst-case hydraulic caliper pressure rise time)
- **Total: $935.0\text{ ms}$**.

### Q3: Did this violate the DGMS 800 ms safety criterion?
**YES.** Under normal local sensing, reaction time is $243.8\text{ ms} < 800\text{ ms}$. But under **cascade communication failure where the truck relies on gateway downlinks before realizing it is disconnected**, the $500\text{ ms}$ timeout pushes the total reaction time to **$935.0\text{ ms}$**, exceeding the DGMS standard by **$135.0\text{ ms}$**.

### Q4: Did the truck physically crash?
- Initial speed: $v_0 = 3.52\text{ m/s}$ ($12.67\text{ km/h}$).
- Distance traveled during $0.935\text{ s}$ delay: $S_{\text{react}} = 3.52 \cdot 0.935 = 3.291\text{ m}$.
- Braking distance on $-8\%$ slope ($a_{\text{dec}} = 2.641\text{ m/s}^2$): $S_{\text{brake}} = \frac{3.52^2}{2 \cdot 2.641} = 2.346\text{ m}$.
- **Total Distance to Halt:** $S_{\text{total}} = 3.291 + 2.346 = \mathbf{5.637\text{ m}}$.
- If an obstacle was placed at $R_{\text{eff}} = 8.0\text{ m}$, the vehicle halted **$2.363\text{ m}$ before impact**.
- **No physical collision occurred.** However, the required $5.0\text{ m}$ DGMS standstill buffer was eroded down to $2.36\text{ m}$.

---

## 4. Architectural Vulnerabilities Exposed

1. **The 500 ms Communication Timeout Is Too Slow for Dense Fog:**
   Waiting half a second just to realize the gateway is dead consumes **53.5%** of the entire reaction budget.
2. **CAN Bus Queue Delay Under Heavy Telemetry:**
   Allowing 95% bus load added $45\text{ ms}$ to brake delivery. Low-priority periodic telemetry must be suppressed immediately during emergency deceleration.
3. **Unmeasured Hydraulic Lag:**
   The $350\text{ ms}$ hydraulic buildup assumption accounts for **37.4%** of the total time.

---

## 5. Mandatory Engineering Action

### Parameter Revision: `CONFIG_REV_9_1_04`
```yaml
# Cascade Hardening Parameters
failsafe:
  comm_loss_timeout_dense_fog_ms: 200.0  # Reduced from 500.0 ms
  can_emergency_priority: 0x0            # Preempts all background traffic
  suppress_telemetry_on_ebrake: true     # Instantly drops bus load to <10%
```

With `comm_loss_timeout = 200.0 ms` and `can_delay = 5.0 ms`:
$$\tau_{\text{cascade\_new}} = 200 + 40 + 5 + 350 = \mathbf{595.0\text{ ms}} < 800.0\text{ ms} \quad \text{\textbf{(FULLY DGMS COMPLIANT)}}$$
