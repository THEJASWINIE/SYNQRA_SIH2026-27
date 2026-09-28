# EXPERIMENT E9 — SAFE BEACON FALLBACK REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Distributed Peer-to-Peer Safety Fallback Architecture  
**Evidence Level:** L7 — Bench Measured / L1 — Deterministic Logic Verification  

---

## 1. Safety Hierarchy & Architectural Boundaries

> [!IMPORTANT]
> **BEACON BOUNDARY RULE**  
> A V2V beacon communicates situational awareness and presence. A peer beacon **DOES NOT DIRECTLY DRIVE THE BRAKE ACTUATOR**.
>
> The authoritative actuation path is strictly:
> $$\text{Beacon Received} \longrightarrow \text{Local Awareness Engine} \longrightarrow \text{Local Safety Governor} \longrightarrow v_{\text{safe}} \longrightarrow \text{Actuator}$$

```
Level 1 (Primary):   Central Gateway Dispatch (Haul road pacing, slot allocation)
                             │ (If gateway lost / shadowed)
                             ↓
Level 2 (Fallback):  Direct Peer Safety Beacon (V2V peer proximity, zone occupancy)
                             │ (If all RF lost or dense fog)
                             ↓
Level 3 (Ultimate):  Autonomous Local Vehicle Governor (Onboard sensors + failsafe)
```

---

## 2. Beacon Protocol Format & Payload Specification

The P2P safety beacon format follows a lightweight, parseable CSV structure:

```
BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>
```

- `vehicle_id`: Alphanumeric string identifier (e.g. `TRUCK_01`, `TRUCK_02`)
- `sequence`: Monotonically increasing 32-bit unsigned integer
- `state`: Enum in `[NORMAL, DEGRADED, STOP, EMERGENCY]`
- `timestamp`: UTC Epoch float with millisecond resolution
- `zone_id`: Spatial segment identifier (e.g. `HAUL_RD_01`, `SWITCHBACK_03`)

---

## 3. Verification of Rejection Rules

1. **Stale Beacon Rejection:**  
   Beacons with age $> 500\text{ ms}$ are marked STALE. If no beacon is received from a preceding vehicle within $1.0\text{ s}$, the trailing vehicle automatically increases its following distance from 50 m to 100 m.

2. **Duplicate & Replay Rejection:**  
   Beacons with sequence numbers $\le$ highest observed sequence are logged and discarded, preventing replay attacks.

3. **Prevention of False Actuator Tripping:**  
   Corrupted or noisy beacon packets are rejected by CRC checks and cannot trigger sudden emergency braking on trailing trucks, preventing rear-end pileups on downhill ramps.
