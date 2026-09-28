# FAIL-SAFE ARCHITECTURE & LOCAL SAFETY GOVERNOR SPECIFICATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Target Standard:** ISO 3450:2011, DGMS Metalliferous Open Cast Safety Regulations, SAE J1939  
**Status:** CANONICAL ARCHITECTURAL SPECIFICATION  
**Module Reference:** `integration_adapters/fail_safe_controller.py`  
**Date:** 2026-09-18  

---

## 1. THE SUPREMACY PRINCIPLE (PART 16)

> [!IMPORTANT]
> **The Local Vehicle Safety Governor is the Highest Authority**:
> - The wireless gateway is NOT the safety authority.
> - The central dispatch / optimization engine is NOT the safety authority.
> - The predictive 3D Digital Twin is NOT the safety authority.
> - **THE ONBOARD LOCAL VEHICLE SAFETY GOVERNOR IS THE SOLE AND HIGHEST OPERATIONAL SAFETY AUTHORITY.**
>
> The central intelligence engine may recommend speed, headway, or slot allocation. The local governor, running directly on the vehicle microcontroller/ECU, evaluates the recommendation against real-time local physical constraints and **ACCEPTS**, **CLAMPS**, or **REJECTS** it. Under no circumstances may an upstream network message override a local safety constraint.

---

## 2. CANONICAL AUTHORITY HIERARCHY (PART 19)

```
LEVEL 0: EMERGENCY / LOCAL PHYSICAL SAFETY
         (Firmware Watchdog, E-Stop Button, Loss-of-Air Emergency Valves)
         ▲
         │ (Can override Level 1 by forcing 0.0 m/s)
LEVEL 1: LOCAL HEMM SAFETY GOVERNOR
         (Onboard ECU Quadratic Solver, v_safe Envelope, Force Balance)
         ▲
         │ (Can CLAMP or REJECT Levels 2-5)
LEVEL 2: VEHICLE COMMAND VALIDATION & INGESTION GATEWAY
         (Freshness, Sequence Order, Deduplication, Schema Verification)
         ▲
         │ (Can filter and reject Levels 3-5)
LEVEL 3: CENTRAL FOG-ORCHESTRATOR INTELLIGENCE
         (Deterministic Safe Speed, Headway Solver, Junction Coordinator)
         ▲
         │ (Recommends dispatch actions to Level 2)
LEVEL 4: FLEET OPTIMIZATION & RESOURCE SCHEDULING
         (MILP Slot Reservation, Crusher Arrival Shaping)
         ▲
         │ (Feeds candidate flow targets to Level 3)
LEVEL 5: PREDICTIVE 3D DIGITAL TWIN
         (Geospatial Projection, Future Horizon What-If Prediction)
         (STRICTLY OBSERVES: NO DIRECT CONTROL PATH TO ACTUATOR)
```

**Rule:** Higher levels recommend. Lower levels govern and reject. Never the reverse.

---

## 3. FAIL-SAFE STATE MACHINE (PART 17)

```
                       ┌──────────────────────┐
                       │        NORMAL        │
                       └──────────┬───────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ Loss >= 25%            │ Invalid/Over-speed     │ Stale age > 1.0s
         ▼                        ▼                        ▼
 ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
 │   DEGRADED    │        │    UNSAFE/    │        │ STALE_COMMAND │
 │ COMMUNICATION │        │ INVALID_CMD   │        └───────────────┘
 └───────┬───────┘        └───────┬───────┘                │
         │                        │                        │
         │ Gateway lost           │ E-Stop / Watchdog      │ Watchdog > 1.0s
         ▼                        ▼                        ▼
 ┌───────────────┐        ┌────────────────────────────────────────┐
 │   NO_GATEWAY  │        │             EMERGENCY_STOP             │
 └───────┬───────┘        │         (Forced 0.0 m/s Command)       │
         │                └───────────────────┬────────────────────┘
         │ Link restored                      │ Reset & Sync (N >= 2)
         ▼                                    ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                            RECOVERY                             │
 └─────────────────────────────────────────────────────────────────┘
```

### State Definitions & Operational Rules:
1. **`NORMAL`**:
   - Central commands validated; requested speed $\le v_{\text{safe}}$. Command is **ACCEPTED**.
2. **`DEGRADED_COMMUNICATION`**:
   - RF link experiencing elevated packet loss ($\ge 25\%$) or marginal correlation ($\rho < 0.60$).
   - Local governor increases safety margin: $S_{\text{margin}} = S_{\text{base}} + k_{\text{comm}}(1 - C_{\text{comm}})v$.
   - Vehicle continues operation under local safety limits; central coordination bandwidth reduced.
3. **`STALE_COMMAND`**:
   - Received command has age $(t_{\text{now}} - t_{\text{created}}) > 1.0\text{ s}$.
   - Command is **REJECTED**; vehicle retains previous safe velocity or decelerates.
4. **`NO_GATEWAY`**:
   - Wireless gateway disconnected or out of range.
   - All central commands are **REJECTED**. Vehicle transitions to autonomous standoff state governed strictly by local sensors / sight distance.
5. **`UNSAFE_COMMAND`**:
   - Requested speed exceeds local safe speed ($v_{\text{requested}} > v_{\text{safe}}$).
   - Command is **CLAMPED** to $v_{\text{safe}}$ or rejected. Actuator velocity never exceeds $v_{\text{safe}}$.
6. **`INVALID_COMMAND`**:
   - Malformed packet, duplicate sequence, out-of-order sequence, negative speed, or NaN/Inf.
   - Command is **REJECTED**.
7. **`EMERGENCY_STOP`**:
   - Triggered by manual E-stop, loss of pneumatic brake pressure, or firmware watchdog timeout ($>1.0\text{ s}$ during low visibility).
   - Commanded velocity is latched to **$0.0\text{ m/s}$**. Service and emergency brakes fully applied.
8. **`RECOVERY`**:
   - Transition state following communication restoration or E-stop reset.
   - Vehicle requires at least 2 consecutive valid, in-sequence command frames before re-engaging central dispatch commands.

---

## 4. COMMAND VALIDATION CONTRACT (PART 18)

Every dispatch command ingested by the vehicle must provide:
```json
{
  "vehicle_id": "TRUCK_01",
  "sequence": 1042,
  "timestamp": 1726650420.150,
  "requested_speed_mps": 4.50,
  "action": "TARGET_SPEED",
  "command_source": "CENTRAL",
  "reason": "Clear sector advance"
}
```

### Validation Invariants:
- **Vehicle Match:** `cmd.vehicle_id == local.vehicle_id`.
- **Sequence Freshness:** `cmd.sequence > local.last_valid_sequence`. Duplicates and out-of-order frames are rejected.
- **Timestamp Freshness:** $(t_{\text{now}} - \text{timestamp}) \le 1.0\text{ s}$.
- **Numerical Sanity:** `requested_speed_mps` must be finite, non-negative, and $\le 20\text{ km/h}$.
- **Enforcement:**
  $$v_{\text{applied}} = \min(v_{\text{requested}}, v_{\text{safe}})$$

---

## 5. QUALIFICATION OF THE 75% PACKET LOSS CLAIM (PART 21)

Prior documents noted that the system survives up to $75\%$ wireless packet loss. To ensure absolute scientific honesty and avoid misleading presentation:

> [!CAUTION]
> **Communication Delivery vs Local Safety Robustness**:
> - **What is NOT true:** We DO NOT claim that a 433 MHz LoRa link with 75% packet loss is a reliable communication channel. An RF link dropping 3 out of 4 packets is severely degraded.
> - **What IS true:** We prove that under a 75% packet loss condition, **LOCAL SAFETY INVARIANTS REMAIN FULLY ENFORCED**.
>   1. Valid packets that arrive have their target speeds clamped to $v_{\text{safe}}$.
>   2. Stale packets ($>1.0\text{ s}$) are rejected.
>   3. If packet loss persists beyond the watchdog threshold ($1.0\text{ s}$ fast / $15.0\text{ s}$ firmware), the vehicle halts safely.
>   4. Communication failure NEVER causes an over-speed, runaway, or collision.
