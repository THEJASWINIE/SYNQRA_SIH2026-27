# 03 — LATENCY MODEL RECONCILIATION & AUDIT REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Real-Time Control Loop & Safety Reaction Timing Audit  
**Dataset Reference:** [`data/phase7_3_latency.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_latency.csv)  
**Date of Audit:** 2026-09-18  

---

## 1. The Dual-Loop Latency Architecture

A critical architectural flaw in early project models was bundling the central cloud/gateway transmission delay into the vehicle's emergency stopping distance equation. 

FOG-ORCHESTRATOR 2.0 enforces a **strict dual-loop separation**:

```
========================================================================================
LOOP A: TIER-1 LOCAL AUTONOMOUS SAFETY LOOP (tau_local_nominal = 375 ms)
Relevant to emergency braking, stopping distance, and collision avoidance.
Runs entirely onboard the vehicle on local ECU / ESP32.

  [Obstacle / Fog Sensor] (10 Hz)
         │  tau_sensor = 100.0 ms (Sampling / perception window)
         ▼
  [Local Safety Governor] (20 Hz)
         │  tau_decision = 50.0 ms (Evaluation + quadratic solver clamp)
         ▼
  [SAE J1939 CAN Bus] (250 kbps)
         │  tau_CAN = 25.0 ms nom / 50.0 ms bound (Arbitration + frame tx)
         ▼
  [Brake Actuator (Air-Over-Hydraulic)]
         │  tau_actuator = 200.16 ms mean / 237.1 ms P99 (Pilot + air + hyd + clamp)
         ▼
  [Wheel Deceleration Onset (a_dec)]
========================================================================================

========================================================================================
LOOP B: TIER-2 CENTRAL FLEET COMMAND LOOP (tau_fleet_command = 685 ms nominal)
Relevant to haul road entry metering, slot pacing, and bottleneck avoidance.
Routes across wireless links to central cloud optimizer.

  [Truck 01 ESP32]
         │  tau_lora_uplink = 150.0 ms (LoRa CSS Time-on-Air + serial out)
         ▼
  [LoRa Gateway ESP32]
         │  tau_gateway_wifi = 30.0 ms (Wi-Fi TCP/IP socket relay)
         ▼
  [FastAPI Backend / TwinStateStore]
         │  tau_backend = 50.0 ms (Validation, normalization, Twin update)
         ▼
  [Linear Programming Fleet Optimizer]
         │  tau_optimizer = 80.0 ms (Arrival shaping & slot assignment)
         ▼
  [Gateway Downlink Broadcast]
         │  tau_lora_downlink = 150.0 ms (LoRa CSS command transmission)
         ▼
  [Truck 01 Onboard Governor]
         │  tau_CAN = 25.0 ms (Internal dispatch to actuator)
         ▼
  [Actuator Target Speed Adjustment]
========================================================================================
```

---

## 2. Canonical Latency Reconciliation Table

| Parameter Name | Nominal Value | Statistical P50 | Statistical P95 | Statistical P99 | Worst-Case Scenario | Unit | Evidence Level | Measurement Type | Used In Model | Confidence |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| `tau_sensor` | 100.0 | 66.8 | 95.2 | 98.9 | 99.9 | ms | L6 | Engineering Model | Perception Delay | HIGH |
| `tau_decision` | 50.0 | 25.1 | 47.6 | 49.5 | 49.9 | ms | L7 | Bench Measured | Governor Task Period | VERY HIGH |
| `tau_CAN` | 25.0 | 3.9 | 13.8 | 24.1 | 50.0 | ms | L7 | Bench Measured | Bus Arbitration & Tx | VERY HIGH |
| `tau_actuator` | 200.16 | 199.85 | 226.40 | 237.10 | 350.0 | ms | L7_Surrogate | Surrogate Bench | Pressure Rise & Pad Clamp | HIGH_SURROGATE |
| `tau_local_total` | **375.0** | **324.1** | **399.0** | **436.9** | **550.0** | **ms** | **L6/L7 Synthesized** | **Synthesized Calibrated** | **Authoritative $S_{\text{stop}}$ & $v_{\text{safe}}$** | **VERY HIGH** |
| `tau_lora_uplink` | 150.0 | 62.2 | 85.0 | 114.0 | 250.0 | ms | L7 | Bench Measured | Telemetry Ingestion | HIGH |
| `tau_gateway_wifi`| 30.0 | 15.0 | 28.0 | 45.0 | 80.0 | ms | L7 | Bench Measured | Gateway TCP/IP Relay | HIGH |
| `tau_backend` | 50.0 | 12.0 | 35.0 | 48.0 | 100.0 | ms | L7 | Bench Measured | Twin State Synchronization | HIGH |
| `tau_optimizer` | 80.0 | 45.0 | 78.0 | 95.0 | 150.0 | ms | L7 | Bench Measured | Dispatch Optimization | HIGH |
| `tau_lora_downlink`| 150.0 | 62.2 | 85.0 | 114.0 | 250.0 | ms | L7 | Bench Measured | Command Delivery | HIGH |
| `tau_fleet_total` | **685.0** | **420.0** | **610.0** | **710.0** | **1050.0** | **ms** | **L6/L7 Synthesized** | **Synthesized Bench** | **Fleet Orchestration Only** | **VERY HIGH** |

---

## 3. Mathematical Proof: Why Gateway Latency is Excluded from $S_{\text{stop}}$

Let $d_{\text{react}}$ denote the longitudinal reaction distance traveled by a haul truck before physical braking begins:

$$d_{\text{react}} = v \cdot \tau_{\text{reaction}}$$

1. **If local emergency braking is autonomous:**  
   Obstacle detection occurs via onboard radar or V2V direct peer beacon. The governor issues an emergency brake command directly to the service brake pneumatic valve over the local CAN bus:
   $$\tau_{\text{reaction}} = \tau_{\text{local\_total}} = \tau_{\text{sensor}} + \tau_{\text{decision}} + \tau_{\text{CAN}} + \tau_{\text{actuator}} = 0.375\text{ s (Nominal)}$$
   At $v = 20\text{ km/h}$ ($5.56\text{ m/s}$):
   $$d_{\text{react}} = 5.56 \times 0.375 = \mathbf{2.08\text{ m}}$$

2. **If gateway latency is erroneously included:**  
   Assuming braking requires central cloud round-trip dispatch ($\tau_{\text{fleet}} \approx 0.685\text{ s}$):
   $$\tau_{\text{reaction\_erroneous}} = \tau_{\text{fleet\_total}} = 0.685\text{ s}$$
   At $v = 20\text{ km/h}$ ($5.56\text{ m/s}$):
   $$d_{\text{react\_erroneous}} = 5.56 \times 0.685 = \mathbf{3.81\text{ m}}$$
   $$\Delta d_{\text{react}} = +1.73\text{ meters}$$

**Safety & Operational Implication:**  
Artificially inflating reaction distance by $+1.73\text{ m}$ would force vehicles to travel unnecessarily slowly under fog without providing any physical safety benefit, because the physical vehicle **does not wait for cloud permission to avoid a collision**. The autonomous local governor remains the sole authority for vehicle stopping distance.
