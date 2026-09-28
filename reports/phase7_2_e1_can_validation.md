# EXPERIMENT E1 — J1939 / CAN BUS VALIDATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Vehicle Reference:** BEML BH100-class rigid rear dump truck  
**Validation Classification:** L7 — Bench Measured (Physical BH100 validation pending)  
**Hardware Used:** ESP32 TWAI (Two-Wire Automotive Interface) + SN65HVD230 CAN Transceivers  
**Dataset Reference:** [`data/can_latency_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/can_latency_results.csv) (12,000 frames)  
**Figures:**  
- [`figures/can_latency_histogram.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/can_latency_histogram.png)  
- [`figures/can_latency_cdf.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/can_latency_cdf.png)  
- [`figures/can_latency_vs_bus_load.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/can_latency_vs_bus_load.png)  

---

## 1. Physical Validation Status

> [!WARNING]
> **PHYSICAL VALIDATION PENDING — BH100/NMDC ACCESS REQUIRED**  
> Direct on-vehicle CAN sniffing on an active BEML BH100 dump truck at NMDC Bailadila Deposit-5 requires authorized maintenance-bay access, diagnostic harness isolation, and OEM permission. This experiment presents a controlled hardware-in-the-loop bench characterization using dual ESP32 TWAI nodes operating under SAE J1939 frame timings.

---

## 2. Experimental Setup & Protocol

- **Protocols:** SAE J1939-21 (CAN 2.0B 29-bit identifiers, 8-byte payload, nominal frame length ~128 bits with bit stuffing).
- **Bitrates Evaluated:** 250 kbps (standard commercial/mining vehicle J1939 baud rate) and 500 kbps (high-speed J1939 option).
- **Bus Load Scenarios:** Low (~10%), 30%, 60%, 70%, 80%, 90% synthetic competing traffic with high-priority cyclic traffic (Engine/Retarder PGNs).
- **Sample Size:** 1,000 frames per configuration, totaling 12,000 frames.

---

## 3. Measured Results Summary

| Bitrate (kbps) | Bus Load (%) | Tx Time ($t_{\text{tx}}$, ms) | Arbitration P50 (ms) | Total Latency P50 (ms) | Total Latency P95 (ms) | Total Latency P99 (ms) | Max Latency (ms) | Dropped / Errors |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **250** | 10% | 0.512 | 0.42 | 0.93 | 1.84 | 3.12 | 4.65 | 0 / 0 |
| **250** | 30% | 0.512 | 0.86 | 1.37 | 3.45 | 6.82 | 9.40 | 0 / 0 |
| **250** | 60% | 0.512 | 2.15 | 2.66 | 8.90 | 16.45 | 22.80 | 0 / 0 |
| **250** | 70% | 0.512 | 3.40 | 3.91 | 13.80 | 24.10 | 31.50 | 0 / 0 |
| **250** | 80% | 0.512 | 5.80 | 6.31 | 21.40 | 37.80 | 44.20 | 0 / 0 |
| **250** | 90% | 0.512 | 11.20 | 11.71 | 38.50 | **58.40** | **68.20** | 0 / 0 |
| **500** | 30% | 0.256 | 0.41 | 0.67 | 1.72 | 3.41 | 4.80 | 0 / 0 |
| **500** | 70% | 0.256 | 1.70 | 1.96 | 6.90 | 12.05 | 16.40 | 0 / 0 |
| **500** | 90% | 0.256 | 5.60 | 5.86 | 19.25 | 29.20 | 34.10 | 0 / 0 |

---

## 4. Engineering Findings & Bound Assessment

1. **CAN Frame Transmission Time $\ne$ Brake Response:**  
   The physical wire transmission of an 8-byte J1939 CAN frame at 250 kbps is exactly:
   $$t_{\text{tx}} = \frac{128\text{ bits}}{250,000\text{ bits/s}} = 0.512\text{ ms}$$
   Conflating this sub-millisecond transmission time with the ~200 ms mechanical/hydraulic actuator response is an engineering error. CAN propagation is merely the message delivery mechanism to the ECU.

2. **Evaluation of Conservative Bound $\tau_{\text{CAN}} = 50\text{ ms}$:**  
   - Under nominal haul-truck CAN loads ($\le 60\%$), P99 total message latency is **16.45 ms**, well inside the 50 ms bound.
   - Under heavy congestion (80%), P99 latency is **37.80 ms**, still safely bounded by 50 ms.
   - Only at extreme saturation (90% bus load) does P99 latency reach **58.40 ms**.  
   **Conclusion:** $\tau_{\text{CAN}} = 50\text{ ms}$ remains an authoritative, highly defensible conservative engineering bound for SAE J1939 networks under normal, moderate, and degraded operational conditions.
