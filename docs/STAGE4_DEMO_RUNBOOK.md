# STAGE 4 — LIVE DEMONSTRATION RUNBOOK & DETERMINISTIC PROTOCOL

This document specifies the exact 3–5 minute live demonstration protocol for the Smart India Hackathon (SIH) Grand Finale jury, including deterministic scenes, HMI visual checkpoints, physical truck actions, and three-tier failure fallback plans.

---

## 1. Master 3–5 Minute Demonstration Script (Scenes 1 – 7)

```
[0:00 - 0:45] SCENE 1: Normal Steady-State Mine Haulage
[0:45 - 1:30] SCENE 2: Fog Onset & Dynamic Safe Operating Envelope
[1:30 - 2:15] SCENE 3: Bottleneck Accumulation & Queue Prediction
[2:15 - 3:00] SCENE 4: Origin HOLD & Dynamic Slot Deconfliction
[3:00 - 3:45] SCENE 5: Unsafe / Adversarial Command Clamping (Test H7)
[3:45 - 4:15] SCENE 6: Communication Severance & Safe Failsafe (Test H8)
[4:15 - 4:45] SCENE 7: Fog Dissipation, RELEASE & Autonomous Recovery
```

---

### Scene-by-Scene Protocol

| Scene | Duration | Trigger / Physical Event | Visual Display (Control Room & Operator HMI) | Physical Vehicle Behavior (TRUCK_01 & TRUCK_02) | Evaluator Talking Point |
|:---|:---:|:---|:---|:---|:---|
| **SCENE 1: Normal Operations** | 45s | Clear weather ($R_v = 100\text{ m}$, $\mu = 0.65$). | All haul roads displayed in **Green**. Fleet production rate nominal ($183\text{ TPH}$). In-cab speedometer at $11.1\text{ m/s}$ ($40\text{ km/h}$). | TRUCK_01 cruises forward at nominal lab setpoint ($0.50\text{ m/s}$). Motor PWM = 140. | *"Under clear visibility, the haul fleet operates at full nominal DGMS speed limits with standard headway."* |
| **SCENE 2: Fog Onset** | 45s | Fog bank enters Ramp R1 ($R_v \downarrow 12.0\text{ m}$, $\mu \downarrow 0.35$). | Ramp R1 turns **Red**. Safe speed drops to **$4.382\text{ m/s}$** ($15.8\text{ km/h}$). Operator HMI flashes: `"DENSE FOG — CLAMP 15.8 KM/H"`. | TRUCK_02 onboard Tier-1 governor ramps motor PWM down from 140 to 95 ($0.35\text{ m/s}$). Smooth service deceleration. | *"Tier-1 physics solver recalculates stopping distance in real time. Stopping headway increases from 15m to 25m."* |
| **SCENE 3: Bottleneck Prediction** | 45s | Shovels dispatch 3 consecutive haulers to Crusher C1 ($\lambda = 18 > \mu = 10$). | Crusher C1 node pulses yellow. Predictive Twin displays: `"CRUSHER SATURATION PREDICTED IN 8 MIN (Q = 3.5)"`. | Trucks en route continue at $v_{\text{safe}}$. Crusher apron buffer occupancy reaches 2 trucks. | *"Rather than allowing blind queue pile-ups inside the fog bank, the digital twin predicts queue growth 600s ahead."* |
| **SCENE 4: Origin HOLD & Slot** | 45s | Central orchestrator triggers origin holding policy for TRUCK_01. | TRUCK_01 icon pulses orange: `"HELD AT SHOVEL_01 BENCH"`. Operator HMI: `"HOLD — DISPATCH PAUSED TO PREVENT BOTTLENECK"`. | TRUCK_01 remains stationary with brakes applied at loading bench. TRUCK_02 clears switchback under allocated slot. | *"Instead of idling in fog with engines running, trucks are held at origin. Fleet idle delay drops by 33.3%."* |
| **SCENE 5: Unsafe Command Injection** | 45s | Dispatcher injects adversarial command requesting $2.50\text{ m/s}$ ($> 1.40\text{ m/s}$ max). | Control room logs audit alert: `"CENTRAL COMMAND CLAMPED BY VEHICLE GOVERNOR"`. Operator HMI: `"UNSAFE COMMAND REJECTED"`. | TRUCK_02 local firmware overrules central command. Speed remains strictly clamped at $1.40\text{ m/s}$ (or $0.50\text{ m/s}$). | *"Rule 7 verified: The central orchestrator has zero authority to violate the vehicle's Tier-1 safety envelope."* |
| **SCENE 6: Comm Loss Failsafe** | 30s | Cut Wi-Fi / LoRa downlink to TRUCK_02. | Control Room flashes red banner: `"TRUCK_02 COMM LOSS — AUTONOMOUS V2V MODE ACTIVE"`. | TRUCK_02 continues under local safety for watchdog interval, then initiates fail-safe motor stop. | *"If communication drops, onboard autonomous radar/LiDAR and peer-to-peer V2V protect the vehicle."* |
| **SCENE 7: Recovery & RELEASE** | 30s | Environmental sensor reports fog clearing ($R_v \uparrow 100\text{ m}$). | Roads return to green. Safe speed envelope expands back to $11.1\text{ m/s}$. TRUCK_01 status: `"RELEASED — ROUTE AUTHORIZED"`. | TRUCK_01 ramps motor smoothly forward. Fleet throughput returns to 100% capacity. | *"As sight distance clears, the envelope expands dynamically, releasing held vehicles without manual intervention."* |

---

## 2. Multi-Tier Demo Fallback Plan

| Fallback Tier | Operational Infrastructure | Execution Condition | Evaluator Statement |
|:---:|:---|:---|:---|
| **PLAN A** (Primary) | **Live Hardware + Real-Time Simulation** | Physical ESP32 prototypes, LoRa Gateway, and FastAPI server running on local Wi-Fi router. | *"Demonstrating live closed-loop cyber-physical execution across hardware and 3D digital twin."* |
| **PLAN B** (Intermediate) | **Replayed Hardware Telemetry + Live Orchestrator** | Pre-recorded 433 MHz packet logs streamed into FastAPI via local replay script. | *"Demonstrating real hardware telemetry trace replayed through live central optimizer and HMI."* |
| **PLAN C** (Contingency) | **Fully Deterministic Offline Twin Simulation** | Pure Python/Three.js simulation with fixed seed ($100$) running entirely on localhost. | *"Demonstrating fully deterministic offline multi-agent simulation mode (Simulation only)."* |

> [!IMPORTANT]
> **Strict Truthfulness Rule**: Under no circumstances will Plan C be represented as live hardware. If RF interference disrupts the venue, switch transparently to Plan B or C and state the mode explicitly to the jury.
