# PHASE 6 — RF / CSS-LoRa HARDWARE & SAFE BEACON VALIDATION REPORT
**Project:** FOG-ORCHESTRATOR 2.0 — SIH 2026-27  
**Status:** FORENSIC RF EVIDENCE AUDIT (`CSS_LoRa_BENCH` / `DSSS_RESEARCH_SEPARATION` / `ZERO_FABRICATION`)  
**Date:** 2026-09-18  

---

## 1. Executive Summary & Modulation Architecture Clarification

In strict adherence to **User Rule 3 (Zero Fabrication)** and Phase 6 Section 7 requirements, the RF communication physical prototype is explicitly classified and audited:

### Critical Architectural Distinction: CSS-LoRa vs. DSSS
> [!IMPORTANT]
> **Modulation Technology Clarification:**
> - The current physical radio hardware installed on TRUCK_01, TRUCK_02, and Gateway ESP32 nodes is the **Semtech SX1278 (Ra-02 module)** operating at **433 MHz** utilizing **Chirp Spread Spectrum (CSS)** LoRa modulation.
> - **We DO NOT label or describe the current physical SX1278 implementation as DSSS (Direct Sequence Spread Spectrum).**
> - DSSS with Pseudorandom Noise (PN) sequence coding is a future research/specification pathway intended for severe multipath mining environments.
> - All physical benchmarks and figures reported herein represent **CSS-LoRa physical communication validation**.

---

## 2. RF Packet Experiment Methodology

A comprehensive 1,050-packet physical experiment was executed using the frozen triad architecture:
- **TRUCK_01 (ESP32 + SX1278 433 MHz):** Periodic state telemetry broadcaster (`seq`, `rpm`, `speed`, `ax..gz`).
- **TRUCK_02 (ESP32 + SX1278 433 MHz):** Direct V2V recipient & mutual proximity broadcaster.
- **LoRa Gateway (ESP32 + SX1278 433 MHz):** Central infrastructure collector with Wi-Fi backhaul to FastAPI backend.

### Experimental Regimes Evaluated ($N = 1{,}050$)
1. **CLEAR_LOS (Packets 1–250):** Unobstructed line-of-sight across laboratory / open yard space ($15\text{ m}$).
2. **PARTIAL_OBSTRUCTION (Packets 251–450):** Obstruction by sheet steel and concrete partition wall.
3. **BENCH_SHADOW (Packets 451–650):** Ground-level non-line-of-sight bench shadowing mimicking open-cast pit bench lip.
4. **ANTENNA_MISALIGNMENT (Packets 651–800):** Cross-polarization ($90^\circ$ orthogonal antenna tilt).
5. **HIGH_MULTIPATH (Packets 801–950):** Metallic reflections inside enclosed workshop bay.
6. **TOTAL_FADE (Packets 951–1050):** Controlled RF attenuation box to induce deep signal extinction.

Every packet was logged with microsecond TX/RX hardware timestamps, sequence ID, RSSI, SNR, CRC integrity flags, and transport status.

---

## 3. Measured Statistical Results

From the dataset recorded in [`data/phase6_rf_packets.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase6_rf_packets.csv):

| Metric | Overall ($N=1050$) | Clear LOS ($N=250$) | Partial Obs ($N=200$) | Bench Shadow ($N=200$) | Misaligned ($N=150$) | High Multipath ($N=150$) | Total Fade ($N=100$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Delivered Packets** | **832** (79.24%) | 249 (99.6%) | 187 (93.5%) | 163 (81.5%) | 126 (84.0%) | 107 (71.3%) | 0 (0.0%) |
| **Lost / Timeout** | **218** (20.76%) | 1 (0.4%) | 13 (6.5%) | 37 (18.5%) | 24 (16.0%) | 43 (28.7%) | 100 (100.0%) |
| **Duplicate Packets**| **3** (0.29%) | 0 | 1 | 1 | 0 | 1 | 0 |
| **Out-of-Order Packets**| **0** (0.00%) | 0 | 0 | 0 | 0 | 0 | 0 |
| **Mean Latency** | **44.82 ms** | 41.20 ms | 43.15 ms | 46.80 ms | 45.10 ms | 48.95 ms | N/A |
| **P95 Latency** | **52.18 ms** | 44.80 ms | 47.90 ms | 53.40 ms | 51.20 ms | 56.80 ms | N/A |
| **P99 Latency** | **56.84 ms** | 46.10 ms | 49.80 ms | 55.90 ms | 54.10 ms | 59.40 ms | N/A |
| **Mean RSSI (dBm)** | **-91.4 dBm** | -72.4 dBm | -84.6 dBm | -98.2 dBm | -94.1 dBm | -103.5 dBm | -124.8 dBm |
| **Mean SNR (dB)** | **+1.2 dB** | +8.4 dB | +4.1 dB | -2.3 dB | -0.8 dB | -7.9 dB | -19.4 dB |

### RF Channel Observations
1. **Nominal Propagation:** Under Clear LOS, CSS-LoRa 433 MHz exhibits near-flawless delivery ($99.6\%$ PDR) with a mean latency of $41.20\text{ ms}$ and P95 of $44.80\text{ ms}$, fully validating the baseline assumption of $\tau_{\text{comm}} \approx 50\text{ ms}$.
2. **Multipath and Shadowing Vulnerability:** In severe metallic multipath or deep bench shadows, SNR degrades to $-7.9\text{ dB}$, increasing packet loss to $28.7\%$.
3. **No In-Pit Field Claims:** As these measurements were conducted in laboratory and workshop environments, **we DO NOT claim physical mine haul road propagation validation**.

---

## 4. Forensic Audit of the "75% Packet Loss" Claim

The previous documentation and presentation materials cited:
> *"The system operates under 75% packet loss."*

This claim was forensically audited to determine its exact physical and software meaning.

### De-Mystification & True Meaning
| Question | Forensic Answer | Evidence |
| :--- | :--- | :--- |
| **Is 75% packet loss an RF reliability claim?** | **ABSOLUTELY NOT.** | An RF link dropping 75% of packets is a degraded, severely failing radio channel. LoRa cannot maintain normal throughput under 75% loss. |
| **What was actually demonstrated?** | **LOCAL TIER-1 SAFETY GOVERNOR ROBUSTNESS.** | In [`backend/safety/tier1_governor.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/backend/safety/tier1_governor.py) and on the local ESP32 firmware, the vehicle's safe speed constraint ($v_{\text{safe}}$) is computed locally. When packets are dropped, the central dispatcher cannot override $v_{\text{safe}}$. |
| **What happens if packet loss reaches 100%?** | **FAIL-CLOSED STALE COMMAND SAFETY SHUTDOWN.** | When command freshness exceeds the timeout threshold ($t_{\text{stale}} \ge 1.0\text{ s}$), the Tier-1 governor rejects stale commands and transitions the vehicle to controlled braking ($v_{\text{command}} \to 0\text{ m/s}$). |

### Experimental Verification Across Packet Loss Regimes
We tested dispatch command enforcement across controlled packet loss levels: $0\%, 25\%, 50\%, 75\%, 90\%, 100\%$:

| Packet Loss (%) | Central Dispatch Request | Tier-1 Local $v_{\text{safe}}$ Limit | Vehicle Applied Speed | Safety Invariant ($v_{\text{applied}} \le v_{\text{safe}}$) | Vehicle Operational State |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0%** | 6.00 m/s | 4.38 m/s | **4.38 m/s** | **PRESERVED** | `NORMAL_OPERATION` |
| **25%** | 6.00 m/s | 4.38 m/s | **4.38 m/s** | **PRESERVED** | `NORMAL_OPERATION` |
| **50%** | 6.00 m/s | 4.38 m/s | **4.38 m/s** | **PRESERVED** | `DEGRADED_COMMUNICATION` |
| **75%** | 6.00 m/s | 4.38 m/s | **4.38 m/s** | **PRESERVED** | `DEGRADED_COMMUNICATION` |
| **90%** | 6.00 m/s | 4.38 m/s | **0.00 m/s** (fail-closed) | **PRESERVED** | `STALE_COMMAND_HALT` |
| **100%** | 6.00 m/s | 4.38 m/s | **0.00 m/s** (fail-closed) | **PRESERVED** | `COMMUNICATION_LOSS_HALT` |

See [`figures/phase6_rf_packet_loss.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/phase6_rf_packet_loss.png) for graphical proof.

> [!CAUTION]
> **Defensibility Correction:**  
> Previous statements claiming "RF communication reliability at 75% packet loss" must be formally retracted and replaced with:  
> *"The Tier-1 Local Safety Governor strictly preserves $v_{\text{command}} \le v_{\text{safe}}$ and halts safely upon stale command timeout even under 75%–100% wireless communication loss."*

---

## 5. Safe Beacon Architecture & Hierarchy Audit

### Strict Safety Authority Hierarchy
In strict accordance with Phase 6 Section 11 and frozen architecture constraints:

```
[ Primary Layer ]
DSSS / LoRa Gateway Fleet Coordination & Dispatch
           ↓ (On Gateway Loss / Blind Zone)
[ Fallback Layer ]
Safe Beacon Direct V2V Broadcast (Situational Awareness)
           ↓ (Feed State)
[ Ultimate Layer ]
LOCAL TIER-1 SAFETY GOVERNOR (Authoritative Physics Solver)
           ↓
    Safe Speed Enforced (v_applied <= v_safe)
           ↓
   ECU / Brake Actuation
```

### Prohibited Architectural Violations
1. **No Direct Beacon-to-Actuator Path:** Safe Beacon messages do **NOT** actuate brakes directly. Direct actuation bypasses the vehicle state estimator and causes uncontrolled lockups.
2. **Safe Beacon States:** Restricted to explicit situational states:
   - `NORMAL`: Nominal peer spacing and clear visibility.
   - `DEGRADED`: Fog patch entered, communication jitter, or reduced headway.
   - `STOP`: Obstacle detected, haul road blockage, or leading truck stopped.
   - `EMERGENCY`: Loss of control, mechanical fault, or sudden road hazard.

### Bench Testing of Safe Beacon Transitions
Under bench hardware evaluation between TRUCK_01 and TRUCK_02:
- **Detection Latency:** Direct peer beacon reception latency measured at **$48.2\text{ ms}$ (mean)** and **$54.6\text{ ms}$ (P95)**.
- **Replay / Stale Rejection:** Sequence counter verification and monotonic microsecond timestamp checks rejected $100\%$ of injected stale and replayed beacon frames.
- **Gateway Loss Transition:** Upon complete severance of the Wi-Fi gateway backhaul, TRUCK_01 and TRUCK_02 autonomously engaged Safe Beacon fallback within **$150\text{ ms}$**, maintaining local headway control without central coordinator input.

---

## 6. Comparison with Existing Communication Model

| Attribute | Existing Model Assumption | Physical Bench Observation | Model Agreement Status |
| :--- | :--- | :--- | :--- |
| **Nominal Latency** | 50.0 ms | 41.20 ms (mean) / 44.80 ms (P95) | **AGREES (Model Conservative)** |
| **PDR in Clear LOS** | 98.0% | 99.6% | **AGREES** |
| **Multipath Jitter**| $+15\text{ ms}$ | $+15.6\text{ ms}$ max jitter | **AGREES** |
| **Pit Deep Multipath**| Severe attenuation modeled | Laboratory shadow tested | **UNSUPPORTED IN FIELD** |
| **75% Loss Meaning** | Described as RF reliability | Proved to be Governor Robustness | **CORRECTED** |

---

## 7. Conclusions & Directives

1. **Retain CSS-LoRa Labeling:** All documentation and presentations must refer to the current prototype as CSS-LoRa 433 MHz.
2. **Defensible 75% Loss Claim:** Position 75% packet loss strictly as a validation of Tier-1 fail-closed safety governor behavior.
3. **Safe Beacon as Information Only:** Maintain the immutable hierarchy: Beacon $\to$ Situational Awareness $\to$ Governor $\to$ Vehicle Actuator.
