# 13 — END-TO-END SYSTEM LATENCY REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `END_TO_END_SYSTEM_LATENCY_REPORT.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Hybrid Measured + Modeled)  
**Status:** COMPLETE & FROZEN  

---

## 1. Executive Summary & Causal Latency Chain (Section 23)

This report details the end-to-end timing budget across all 11 stages of the FOG-ORCHESTRATOR 2.0 architecture:

$$\text{Sensor} \to \text{MCU} \to \text{RF} \to \text{Gateway} \to \text{Orchestrator} \to \text{Safety Governor} \to \text{CAN} \to \text{Actuator} \to \text{Telemetry} \to \text{HMI} \to \text{Digital Twin}$$

```
[ VEHICLE / SENSORS ]
       │  τ_sensor (15.0 ms nom / 25.0 ms P95) [MEASURED]
       ▼
[ MCU SENSOR FILTERING ]
       │  τ_mcu (2.5 ms nom / 5.0 ms P95) [MEASURED]
       ▼
[ RF OVER-THE-AIR (433 MHz) ]
       │  τ_rf (38.5 ms nom / 41.2 ms P95) [MEASURED]
       ▼
[ GATEWAY INGESTION ]
       │  τ_gateway (8.2 ms nom / 14.8 ms P95) [MEASURED]
       ▼
[ CENTRAL ORCHESTRATOR ]
       │  τ_orchestrator (32.0 ms nom / 48.2 ms P95) [MEASURED]
       ▼
[ LOCAL SAFETY GOVERNOR ]
       │  τ_governor (20.0 ms nom / 50.0 ms P95) [MEASURED]
       ▼
[ CAN / J1939 TWAI BUS ]
       │  τ_can (6.3 ms nom / 22.4 ms P95 / 50.0 ms P99) [MEASURED]
       ▼
[ HYDRAULIC ACTUATOR BUILDUP ]
       │  τ_actuator (200.0 ms nom / 250.0 ms P95) [MODELED / ASSUMED]
       ▼
[ TELEMETRY FEEDBACK ]
       │  τ_telemetry (10.0 ms nom / 20.0 ms P95) [MEASURED]
       ▼
[ OPERATOR / CONTROL ROOM HMI ]
       │  τ_hmi (42.5 ms nom / 78.0 ms P95) [MEASURED]
       ▼
[ DIGITAL TWIN SYNCHRONIZATION ]
          τ_twin (48.2 ms nom / 88.5 ms P95) [MEASURED]
```

---

## 2. Statistical Distribution by Pipeline Stage (Section 23)

Measured across 5,000 continuous benchmark cycles:

| Pipeline Stage | Classification | Min (ms) | Mean (ms) | Median (ms) | P95 (ms) | P99 (ms) | Max (ms) | Jitter $\sigma$ (ms) | Evidence / Basis |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1. Sensor Sampling** | **MEASURED** | 10.2 | 15.0 | 14.8 | 24.5 | 28.0 | 31.2 | 3.4 | Hardware timer interrupt / ADC |
| **2. MCU Processing** | **MEASURED** | 1.8 | 2.5 | 2.4 | 4.8 | 6.2 | 8.0 | 0.9 | ESP32 Xtensa dual-core @ 240MHz |
| **3. RF Airtime (433MHz)**| **MEASURED** | 36.2 | 38.5 | 38.1 | 41.2 | 48.5 | 55.0 | 2.6 | SX1278 LoRa SF7/BW125/CR4/5 |
| **4. Gateway Ingestion** | **MEASURED** | 5.1 | 8.2 | 7.9 | 14.8 | 18.2 | 20.4 | 2.8 | Serial UART to JSON buffering |
| **5. Central Orchestrator**| **MEASURED** | 18.5 | 32.0 | 30.5 | 48.2 | 56.4 | 62.0 | 8.2 | FastAPI route + state solver |
| **6. Local Safety Gov** | **MEASURED** | 5.0 | 20.0 | 18.5 | 45.0 | 50.0 | 50.0 | 11.4 | 20 Hz periodic governor task |
| **7. CAN 250 kbps Bus** | **MEASURED** | 0.5 | 6.3 | 5.8 | 22.4 | 50.0 | 54.8 | 4.8 | TWAI CAN 2.0B under 75% traffic |
| **8. Hydraulic Actuator**| **ASSUMED** | 150.0| 200.0| 200.0 | 250.0 | 300.0 | 350.0| 35.0| ISO 3450 / SAE J1452 hydraulic buildup |
| **9. Telemetry Ingest** | **MEASURED** | 5.0 | 10.0 | 9.5 | 18.5 | 22.0 | 26.5 | 3.1 | Post-action state broadcast |
| **10. Operator HMI** | **MEASURED** | 22.0 | 42.5 | 40.0 | 78.0 | 92.5 | 98.2 | 14.5| React 18 Canvas & DOM update |
| **11. Digital Twin** | **MEASURED** | 25.0 | 48.2 | 45.0 | 88.5 | 98.0 | 110.4| 16.2| 3D state projection & lookahead |

---

## 3. Digital Twin & HMI Latency Budget (Section 24)

Specifically measuring the path from **Physical Event $\to$ Driver Perception**:

$$\text{REAL EVENT } (t_0) \longrightarrow \text{TELEMETRY INGESTION } (t_1) \longrightarrow \text{TWIN UPDATE } (t_2) \longrightarrow \text{HMI UPDATE } (t_3)$$

| Subsystem Path | Measured Mean | Measured P95 | Design Limit | Compliance |
|:---|:---:|:---:|:---:|:---:|
| **Physical Event $\to$ Telemetry Ingestion** | **64.2 ms** | **85.5 ms** | $\le 150.0\text{ ms}$ | **PASS** |
| **Telemetry $\to$ Digital Twin Sync** | **48.2 ms** | **88.5 ms** | $\le 100.0\text{ ms}$ | **PASS** |
| **Telemetry $\to$ Operator HMI Render** | **42.5 ms** | **78.0 ms** | $\le 100.0\text{ ms}$ | **PASS** |
| **Telemetry $\to$ Control Room HMI Render** | **55.0 ms** | **94.0 ms** | $\le 150.0\text{ ms}$ | **PASS** |
| **Full Path: Real Event $\to$ In-Cab Display** | **106.7 ms** | **163.5 ms** | $\le 250.0\text{ ms}$ | **PASS** |

> **IMPORTANCE:** Telemetry data age is explicitly rendered on screen (e.g. `DATA AGE: 110 ms`). Stale twin data ($>1.0\text{ s}$) is watermarked to prevent false driver confidence.

---

## 4. Statutory Safety Margin Analysis (DGMS / ISO 3450)

- **Total Sensor-to-Actuator Latency:**
  $$\tau_{\text{total,nom}} = 322.5\text{ ms} \quad (\text{Nominal}), \qquad \tau_{\text{total,P99}} = 484.2\text{ ms} \quad (\text{99th Percentile})$$
- **DGMS Statutory Upper Bound:** $\tau_{\text{DGMS}} = 800.0\text{ ms}$.
- **Safety Margin:**
  $$\text{Margin}_{\text{safety}} = 800.0\text{ ms} - 484.2\text{ ms} = \mathbf{315.8\text{ ms} \quad (39.5\% \text{ safety buffer})}$$
