# 06 — GATEWAY & DSSS/LORA INTEGRATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `06_GATEWAY_INTEGRATION_REPORT.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Hybrid Architecture)  
**Status:** COMPLETE & FROZEN  

---

## 1. Architectural Demarcation & Carrier Truthfulness (Section 19)

In strict adherence to **Rule 3 (Never fabricate telemetry)** and **Rule 23 (Honesty about hardware)**:
1. **Physical Bench Hardware:** Semtech SX1278 (Ra-02) 433 MHz LoRa transceiver.
   - Operating Modulation: **Chirp Spread Spectrum (CSS)**.
   - Channel Parameters: $433.0\text{ MHz}$, $\text{BW} = 125\text{ kHz}$, $\text{SF} = 7$, $\text{CR} = 4/5$.
2. **Research / Production Architecture:** Direct-Sequence Spread Spectrum (DSSS) with pseudo-noise (PN) code spreading.
   - Status: Evaluated **research and software simulation model**.
   - Under no circumstances is physical SX1278 hardware claimed as executing physical DSSS chipping.
3. **Unified Abstraction Layer:**
   - Both physical CSS/LoRa frames and simulated DSSS/PN frames interface through `integration_adapters/dsss_gateway_selector.py`.
   - The central orchestrator and safety governor consume a standardized `CommunicationLink` object.

---

## 2. 5-Layer Gateway Selection Architecture

```
  ┌────────────────────────────────────────────────────────┐
  │                 1. RFHardwareAdapter                   │
  │  (Bridges SX1278 LoRa SPI packets & DSSS frame models) │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                 2. CommunicationLink                   │
  │     (Standardized carrier metrics: RSSI, SNR, Loss)    │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │              3. GatewayCorrelationEngine               │
  │    (Computes normalized PN / link correlation score)   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │           4. GatewaySelectionStateMachine              │
  │    (Anti-flapping hysteresis, persistence counter,      │
  │     handover arbitrations, transition audit logging)   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │               5. SafetyOrchestratorLink                │
  │     (Presents chosen gateway & degradation state)      │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Gateway Selection & Handover Parameters

| Parameter | Canonical Value | Unit | Rationale / Provenance |
|:---|:---:|:---:|:---|
| `switch_margin` | $0.15$ | Normalized | Prevents ping-pong handover at overlapping cell boundary |
| `persistence_count` | $3$ | Samples ($300\text{ ms}$) | Filters transient multipath fading dips |
| `fail_timeout_s` | $1.0$ | Seconds | Grace period before switching away from fading gateway |
| `loss_window_size` | $10$ | Packets | Rolling window for packet error rate calculation |
| `rssi_degraded_threshold` | $-105.0$ | dBm | Signal level triggering degraded communication state |
| `snr_degraded_threshold` | $-5.0$ | dB | Noise floor triggering forward error correction alert |

---

## 4. Gateway Visualization Rules (Section 20)

### A. Control Room HMI Visualization
The Control Room requires comprehensive infrastructure observability:
- **Gateway Locations:** Displayed on the interactive mine map (GW-01 Crusher, GW-02 Ramp R1, GW-03 Pit Bench).
- **Per-Gateway Telemetry Card:**
  - Gateway ID & Health State (`CONNECTED`, `DEGRADED`, `OFFLINE`).
  - Active vehicle associations.
  - Correlation score ($0.0$ to $1.0$).
  - Measured RSSI (dBm) and SNR (dB).
  - Sliding window packet loss percentage.
  - Timestamp of last beacon received.
  - Estimated RF coverage radius.

### B. Operator HMI (Driver Cab)
The driver must not be overwhelmed with complex radio metrics:
- **Displayed Fields:**
  - `Gateway: GW-02`
  - `RF: NORMAL` (or `DEGRADED` / `DISCONNECTED`)
- **Suppressed Fields:** Raw RSSI, SNR, PN code sequences, and CRC error counts are hidden from the operator cab.
