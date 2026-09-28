# 08_SAFETY_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Safety Governor, Safe Beacon & Failsafe Audit
**Date / Timestamp:** 2026-09-27T09:44:00+05:30  
**Evaluator Role:** Safety-Critical Systems Engineer, Embedded Systems Engineer  
**Absolute Principle:** NO FABRICATION — Formal Invariant Verification & Fault Response

---

### 1. AUTHORITATIVE SAFETY ARCHITECTURE

The FOG-ORCHESTRATOR architecture enforces non-negotiable Tier-1 local safety:
$$\text{Safety Rule: The Central Orchestrator must NEVER override the vehicle's Tier-1 safety constraint.}$$

```text
       [Central Fleet Dispatch] (v_dispatch)
                  │
                  ▼
         [Authoritative Twin]
                  │
                  ▼
       [Safety Governor Solver] (v_safe)
                  │
                  ▼
      v_command = min(v_dispatch, v_safe)
                  │
                  ▼
         [Command Gateway]
                  │
                  ▼ (Downlink)
     [Local Vehicle Safety Governor] (ESP32)
                  │
                  ▼
       [Hardware Motor Actuator]
```

#### Deterministic Safety Limit Formulation:
$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$
$$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
Where:
- $\tau_{\text{total}} = \tau_{\text{sensor}} + \tau_{\text{comm}} + \tau_{\text{solver}} + \tau_{\text{actuation}} \approx 0.124\text{ s}$
- $a_{\text{dec}} = 1.80\text{ m/s}^2$ (conservative prototype braking limit)

---

### 2. SAFETY GOVERNOR STATE TRANSITIONS

| Operational Condition | Input Visibility ($V$) / Link State | Target Safe Speed ($v_{\text{safe}}$) | Local System State | Safe Beacon Mode | Actuator Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CLEAR** | $V \ge 100\text{ m}$, Link Active | $1.40\text{ m/s}$ (Max Safe) | `NORMAL` | OFF / STEADY GREEN | Full dispatch speed permitted |
| **FOG ENTRY** | $40\text{ m} \le V < 100\text{ m}$ | $0.80\text{ m/s}$ | `CAUTION` | SLOW AMBER (1 Hz) | Smooth deceleration ramp |
| **DENSE FOG** | $10\text{ m} \le V < 40\text{ m}$ | $0.35\text{ m/s}$ | `RESTRICTED` | RAPID AMBER (3 Hz) | Crawl speed clamped |
| **ZERO VISIBILITY** | $V < 10\text{ m}$ | $0.00\text{ m/s}$ | `EMERGENCY_STOP` | FLASHING RED (5 Hz) | Immediate controlled stop |
| **COMM DEGRADATION** | Age $> 3.0\text{ s}$ | $0.50\text{ m/s}$ | `COMM_DEGRADED` | AMBER FLASH | Speed clamp, warning triggered |
| **COMM LOSS (OFFLINE)**| Age $> 10.0\text{ s}$ | $0.00\text{ m/s}$ | `SAFE_STOP` | SOLID RED | Motor STBY pulled LOW, H-bridge coast |

---

### 3. LIVE COMMUNICATION LOSS & TIMEOUT TIMESTAMPS

In accordance with Phase 11:
- $t_0 = 1790481339.465\text{ s}$ (Last valid telemetry frame received from TRUCK_01, sequence 15)
- $t_1 = t_0 + 3.00\text{ s}$ (Stale threshold tripped -> Backend transitioned `data_quality` from `LIVE` to `STALE`, status `COMMUNICATION_DEGRADED`)
- $t_2 = t_0 + 10.00\text{ s}$ (Offline threshold tripped -> Backend transitioned status to `OFFLINE`)
- $t_3 = t_0 + 15.00\text{ s}$ (Command gateway validity window expired -> all outgoing commands invalidated)
- $t_4 = \text{Hardware Timeout}$ (ESP32 local watchdog `COMMAND_TIMEOUT_MS = 15000` tripped -> `targetMotorPWM = 0`, `STBY = LOW`)
- $t_5 = \text{Restoration}$ (Awaiting physical telemetry packet reception)
- $t_6 = \text{Recovery Authorization}$ (Requires sequence synchronization and explicit clear)

---

### 4. SAFE BEACON PHYSICAL & LOGICAL AUDIT

- **Vehicle A Implementation:**
  - Logic in `sketch_aug26a.ino` sets Beacon status based on remote telemetry validity and local safety state.
  - Safe Beacon pins: GPIO 2 (Built-in Blue/Red LED) and designated external warning pin.
- **Vehicle B Implementation:**
  - Logic in `VEHICLE_B_...ino` monitors V2V link age. When link age $> 5000\text{ ms}$, Safe Beacon triggers `BEACON_ALERT` state.
- **Observed Live State:**
  - When TRUCK_01 was stationary with no active command, backend correctly reported `safety_state: COMMUNICATION_DEGRADED`.
  - Frontend Operator HMI correctly displayed Yellow Warning Banner (`COMMUNICATION DEGRADED`).
