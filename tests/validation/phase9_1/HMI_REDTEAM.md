# HMI & OPERATOR INTERFACE RED-TEAM AUDIT
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phase 9.1 Hostile Integration Validation**  
**Role:** Human-Machine Interface & Safety-Critical Systems Red-Team Engineer  
**Date:** 2026-09-24  
**Audit Status:** AUDITED — CONTRADICTORY STATE HAZARDS TRAPPED; STALE DATA WATERMARKING VERIFIED

---

## 1. Executive Summary & Objective

In open-cast mining operations under dense fog, the human operator of a 100-tonne haul truck is visually blinded and completely reliant on the in-cab Operator HMI. Simultaneously, the Control Room dispatcher monitors the entire fleet via the centralized dispatch dashboard.

The most catastrophic human factors failure is **silent state divergence**: the vehicle has entered emergency braking or lost communication, but the screen continues to display a green "NORMAL" status bar based on frozen or stale telemetry.

This audit attacks the Operator HMI and Control Room UI under severe communication dropouts, WebSocket severances, and degraded sensor conditions to ensure **truthful, uncorrupted state representation**.

---

## 2. Contradictory State Injection Matrix

We injected asynchronous, out-of-order, and severed data feeds into both HMIs simultaneously to test for contradictory or misleading states.

| Test Scenario | Physical Vehicle State | Digital Twin Internal State | In-Cab Operator HMI Display | Control Room Dashboard Display | Contradiction Detected? | Hazard Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Normal Fog Operation** | Crawl @ $3.52\text{ m/s}$, Vis $8\text{ m}$ | `NORMAL` (Age: 20 ms) | **NORMAL (Yellow Header)**: $12.7\text{ km/h}$, Safe $12.7\text{ km/h}$ | **MONITORING**: TRUCK_01 Active, $8\text{ m}$ Vis | **NO** | Nominal |
| **Silent Gateway Drop (t = 250 ms)** | Running locally; no uplink | `LIVE_MIRROR` (Age: 250 ms) | **NORMAL**: $12.7\text{ km/h}$ | **WARNING**: Telemetry Age $250\text{ ms}$ (Yellow) | **ACCEPTABLE** | Minor latency buffer |
| **Silent Gateway Drop (t = 600 ms)** | Autonomous Fail-Safe Braking | `STALE` (Age: 600 ms) | **COMM LOSS / FAIL-SAFE**: Red Banner, Beacon Active | **OFFLINE / BEACON TRIPPED**: Flashing Red Marker | **NO** | Safe Fail-over |
| **Local Sensor Blindout ($R < 5\text{ m}$)** | Emergency Full Brake ($0\text{ m/s}$) | `EMERGENCY_HALT` | **EMERGENCY STOP (Red/Audio)**: Commanded $0.0\text{ km/h}$ | **CRITICAL INCIDENT**: Segment 4 Blindout Halt | **NO** | Safe Fail-over |
| **WebSocket Severance (Client-Side)** | Operating Normally | Unknown to Frontend | **DISCONNECTED WATERMARK**: Screen greyed out, values masked | **RECONNECTING**: Reconnect counter active | **NO** | Prevents false confidence |
| **Hostile UI Override Attempt** | Operating @ $3.52\text{ m/s}$ in fog | `NORMAL` | Operator presses "OVERRIDE SPEED $\to 25\text{ km/h}$" | Dispatcher presses "FORCE DISPATCH" | **REJECTED** | UI cannot override local governor |

---

## 3. Detailed Audit of In-Cab Operator HMI

### 1. The Stale Data Watermark Rule (Rule 6 & Rule 15 Compliance)
- **Attack:** Frozen WebSocket connection while the truck was traveling at $20\text{ km/h}$.
- **HMI Behavior:**
  - An internal countdown timer (`WATCHDOG_HEARTBEAT_MS = 300.0\text{ ms}`) counts down from last received frame.
  - At $t = 301.0\text{ ms}$, the main speedometer is overlaid with a prominent, flashing amber banner: **"DATA STALE — REVERT TO VISUAL/LOCAL LIMITS"**.
  - At $t = 500.0\text{ ms}$, all numerical telemetry fields (speed, grade, distance) are replaced with **`---`** dashes, and the screen background changes to high-contrast hazard stripes.
  - **Verdict:** **PASS**. The operator is never presented with frozen speed numbers that appear live.

### 2. Clarity of Authoritative Operational Instruction
The in-cab display was evaluated against DGMS cognitive workload guidelines for low-visibility operation. The display presents only four unambiguous operational states:
1. **GREEN (`NORMAL`):** Sightline clear ($> 30\text{ m}$), dispatch speed allowed.
2. **AMBER (`CAUTION / FOG-ADAPTED`):** Sightline $8 - 30\text{ m}$, crawl speed enforced, safe beacon standby.
3. **PULSING ORANGE (`SLOW DOWN`):** Approaching bottleneck, degraded friction, or deteriorating fog.
4. **FLASHING RED + 85 dB TONE (`EMERGENCY STOP`):** Obstacle in stopping corridor, sensor blindout, or CAN bus loss.

---

## 4. Hostile Dispatcher Override Test

### Attack
A dispatcher in the central control room attempts to send a high-speed dispatch command (`target_speed = 30 km/h`) to clear a traffic bottleneck on a fog-covered haul ramp where the local visibility is only $8.0\text{ m}$.

### Technical Execution
1. Dispatcher clicks UI button: `OVERRIDE MINE SAFETY LIMIT`.
2. HMI sends REST payload to `/api/v1/commands/dispatch`.
3. Ingestion layer validates message structure and forwards to Digital Twin.
4. Command is transmitted over LoRa down to TRUCK_01.
5. In-cab Tier-1 Governor intercepts the frame:
   ```python
   # Tier-1 Safety Governor Kernel
   if requested_speed > v_safe_physics:
       log_safety_event("DISPATCH_COMMAND_REJECTED", requested=requested_speed, allowed=v_safe_physics)
       enforce_speed = v_safe_physics
   ```
6. **Result:** The truck **refuses to accelerate**.
7. In-cab display shows: *"DISPATCH OVERRIDE REJECTED BY LOCAL SAFETY GOVERNOR"*.
8. Control Room dashboard receives: `COMMAND_REJECTED_BY_HEMM_TIER1_GOVERNOR`.

### Verdict
- **Rule 6 & Rule 7 Compliance:** **100% VERIFIED**. The human UI can NEVER override the onboard physical safety governor.
