# REPORT 17 — LIVE DEMONSTRATION & HARDWARE RUNBOOK
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 FINAL EVALUATION DEMO RUNBOOK

| Document ID | Canonical File Path | Date | Audit Status | Version |
| :--- | :--- | :--- | :--- | :--- |
| **REP-17-DEMORUN** | `reports/17_DEMO_EVIDENCE_SHEET.md` | 2026-09-18 | **FROZEN / AUDITED** | 2.1.0 |

---

### Demonstration Purpose & Core Proof Chain

The primary objective of the SIH 2026-27 live demonstration is NOT to showcase visual animation. The objective is to rigorously demonstrate the **Closed-Loop Cyber-Physical Safety and Orchestration Chain**:

```
DYNAMIC FOG CHANGE
       ↓
DIGITAL TWIN ENVIRONMENT UPDATE
       ↓
PHYSICS SAFETY SOLVER RECALCULATION
       ↓
v_safe BOUNDING & LOCAL GOVERNOR INTERVENTION
       ↓
COMMAND GATEWAY DISPATCH & TELEMETRY
       ↓
VEHICLE SPEED / QUEUE STATE CHANGE
       ↓
TWIN STATE SYNCHRONIZATION
       ↓
HMI / PYGAME AUTHORITATIVE VISUALIZATION
```

---

### Live System Architecture Setup

```
[ ESP32 Node 1: TRUCK_01 ] ──── Direct CSS-LoRa V2V ──── [ ESP32 Node 2: TRUCK_02 ]
         │ (433 MHz)                                               │ (433 MHz)
         └─────────────────────────┬───────────────────────────────┘
                                   │ LoRa Uplink
                                   ▼
                       [ ESP32 LoRa Gateway ]
                                   │ USB Serial / Wi-Fi (JSON Telemetry)
                                   ▼
                     [ FastAPI Backend Engine ]
                                   │ Python In-Memory Shared Store
                                   ▼
                        [ Authoritative Digital Twin ]
                                   │ WebSocket / REST API
                       ┌───────────┴───────────┐
                       ▼                       ▼
            [ Technician / Operator HMI ]   [ Pygame Visualization (game_ui.py) ]
```

---

### Phase-by-Phase Live Demonstration Script (5-Act Grand Finale)

#### Act 1: Baseline Clear Operation (Nominal Haulage)
* **Initial State**: Visibility $V_{\text{fog}} = 100\text{ m}$. Dry haul road ($\mu = 0.35$).
* **System Action**:
  - Twin initializes 6 haul dumpers operating along the Bailadila South Ramp route.
  - Safe speed solver sets $v_{\text{safe}} = 11.11\text{ m/s}$ ($40.0\text{ km/h}$, mine speed limit).
  - Crushers operating at nominal steady-state service rate ($200\text{ s}$ per dump).
* **Expected Display**:
  - HMI Dashboard: All vehicle status indicators **GREEN (NORMAL)**.
  - Pygame: Smooth continuous circulation; zero queue formation at switchbacks.

#### Act 2: Fog Incursion & Safety Solver Adaptation (Kinematic Invariant Proof)
* **Trigger**: Operator injects dynamic fog event via HMI Control Panel: Visibility drops $100\text{ m} \to 25\text{ m} \to 12\text{ m}$.
* **System Action**:
  - Backend `TwinStateStore` updates road environment within $<10\text{ ms}$.
  - Kinematic solver recomputes safe stopping envelope:
    - At $12\text{ m}$: $v_{\text{safe}}$ drops automatically to **$5.12\text{ m/s}$ ($18.4\text{ km/h}$)**.
  - Command Gateway clamps speed target ($v_{\text{command}} \le v_{\text{safe}}$).
  - ESP32 local governor receives telemetry and enforces deceleration ($a = -1.2\text{ m/s}^2$).
* **Evaluator Proof Point**:
  - Demonstrate that $v_{\text{command}}$ never exceeds $v_{\text{safe}}$ under any condition.
  - Show telemetry log: Local governor throttles speed before vehicle enters the fog bank.

#### Act 3: Extreme Fog (3–5 Metre Visibility) & Controlled Staging
* **Trigger**: Visibility collapses to $4.0\text{ m}$ (Severe Bailadila Monsoon Fog).
* **System Action**:
  - Kinematic solver computes stopping distance ($S_{\text{stop}} \ge 5.8\text{ m}$ at any moving speed), which violates sightline ($R_{\text{eff}} = 4.0\text{ m}$).
  - Safety solver outputs **$v_{\text{safe}} = 0.00\text{ m/s}$**.
  - Central Orchestrator issues **HOLD / STAGE** commands to approaching vehicles.
  - Rather than stopping abruptly on the dangerous $-8\%$ downhill ramp, vehicles are intercepted and staged in the flat, safe Shovel Bay and Crusher Bypass loop.
* **Evaluator Proof Point**:
  - Zero fabricated throughput: System honestly reports $0\text{ TPH}$ flow on the fog-blind ramp.
  - Zero collisions: Pygame and HMI show vehicles holding safe $25\text{ m}$ headways in designated staging zones.

#### Act 4: Hardware Fault Injection & Communication Loss Invariant
* **Trigger**: Unplug LoRa Gateway antenna or disconnect USB cable during active motion (100% packet loss).
* **System Action**:
  - Vehicle ESP32 heartbeat watchdog trips at $T_{\text{timeout}} = 1,000\text{ ms}$.
  - Onboard local safety governor trips in **$52.4\text{ ms}$** after timeout.
  - Firmware forces autonomous transition to **FAIL-SAFE RETARDING**: clamps commanded speed to $v_{\text{safe}}$ or brings vehicle to a controlled halt on ramp.
* **Evaluator Proof Point**:
  - Evaluator observes serial output from TRUCK_01 ESP32:
    `[FAIL-SAFE ACTIVE] Heartbeat lost. Override fleet command. Enforcing local safe governor.`
  - Prove that communication loss does NOT cause runaway, overspeed, or crashing.

#### Act 5: Fog Clearing & Coordinated Staggered Recovery
* **Trigger**: Visibility recovers $4\text{ m} \to 25\text{ m} \to 100\text{ m}$.
* **System Action**:
  - Orchestrator initiates Level 4 dynamic slot allocation.
  - Staged trucks are released with **$60.0\text{ s}$ staggered headways** to prevent crushing the primary gyratory crusher pocket.
  - Production smoothly returns to **$1,591.4\text{ TPH}$** (96.6% crusher ceiling) without transient pile-ups.
* **Evaluator Proof Point**:
  - Show queue graph: Queue empties predictably without secondary stop-and-go shockwaves.

---

### Command Execution Runbook

#### 1. Start FastAPI Backend & Authoritative Digital Twin
```powershell
# Terminal 1: Launch Backend Server
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Launch Pygame Authoritative Visualizer
```powershell
# Terminal 2: Launch Pygame Display
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python game_ui.py
```

#### 3. Run Automated Closed-Loop Verification Test
```powershell
# Terminal 3: Run Full Regression Test Suite
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python -m pytest tests/ -v
```

#### 4. Monitor Physical ESP32 Hardware Telemetry
```powershell
# Terminal 4: Serial Monitor for Gateway / Truck Node (adjust COM port as required)
python -m serial.tools.miniterm COM3 115200
```
*Expected Serial Output*:
```
[CAN] Rx PGN: 0xF004 | Speed: 5.12 m/s | Safe: 5.12 m/s | Gov: NOMINAL
[LoRa V2V] TRUCK_01 -> TRUCK_02 | RSSI: -68 dBm | SNR: +9.2 dB | PDR: 99.4%
[GATEWAY] Uplink sequence: 1048 | Latency: 42 ms | CRC: OK
```

---

### Evaluator Verification Checklist

- [x] **Authoritative Twin**: Confirm Pygame and HMI consume state from `TwinStateStore`, not internal models.
- [x] **Decoupled Latencies**: Verify emergency stopping distance uses local latency ($375\text{ ms}$), not cloud latency ($685\text{ ms}$).
- [x] **Honest Capacity**: Verify sustained production is capped at $1,647.0\text{ TPH}$ (crusher bottleneck limit).
- [x] **Queue Redistribution**: Verify $77.4\%$ haul ramp waiting reduction is accompanied by safe staging bay holding.
- [x] **Fail-Safe Invariant**: Verify that killing communication immediately triggers safe vehicle governing.
