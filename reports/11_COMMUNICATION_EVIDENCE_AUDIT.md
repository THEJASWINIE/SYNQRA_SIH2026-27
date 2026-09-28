# 11 — COMMUNICATION EVIDENCE & MODULATION AUDIT REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**RF Transceiver:** Semtech SX1278 (Ra-02 Module, 433 MHz, Chirp Spread Spectrum - CSS)  
**Microcontroller:** Espressif ESP32-WROOM-32  
**Dataset References:**  
- [`data/packet_loss_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/packet_loss_results.csv)  
- [`data/rf_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/rf_results.csv)  
**Date of Audit:** 2026-09-18  

---

## 1. Modulation Truthfulness: CSS-LoRa vs. DSSS

> [!IMPORTANT]
> **HARDWARE MODULATION TRUTHFULNESS STATEMENT**  
> 1. **Physical Hardware:** The physical prototype transceivers are Semtech SX1278 modules operating on **Chirp Spread Spectrum (CSS)** LoRa modulation at $433.0\text{ MHz}$ (BW = 125 kHz, SF = 7, CR = 4/5).
> 2. **DSSS Modeling:** Direct Sequence Spread Spectrum (DSSS) with pseudo-noise (PN) Gold codes is a **theoretical research and simulation architecture model** evaluated for future mine-wide ASIC integration. The prototype hardware does **NOT** run a physical DSSS baseband.
> 3. **Audit Directive:** Any claim that "the physical prototype implements custom DSSS radio hardware" is classified as **RED / FORBIDDEN**.

---

## 2. Packet Loss: Invariant Preservation vs. Network Reliability

A core source of confusion in early presentations was the claim:
*"The system works normally with 75% packet loss."*

The forensic audit establishes the proper scientific boundary:

$$\text{Communication Reliability (PDR)} \ne \text{Safety Invariant Preservation}$$

| Packet Loss Rate | Delivered Commands | Link Delivery Ratio (PDR) | Network Communication Status | Governor Fallback Mode | Safety Invariant Violations ($v > v_{\text{safe}}$) | True Scientific Meaning |
|:---:|:---:|:---:|:---:|:---|:---:|:---|
| **0%** | 500 / 500 | **100.0%** | Full Nominal Link | `NORMAL` | **0** | Optimal central dispatch & tracking |
| **25%** | 378 / 500 | **75.6%** | Mild Degradation | `DEGRADED_COMMUNICATION` | **0** | Re-transmissions; speed clamped |
| **50%** | 244 / 500 | **48.8%** | Heavy Loss | `DEGRADED_COMMUNICATION` | **0** | Sparse commands; local safety active |
| **75%** | 129 / 500 | **25.8%** | Severe Impairment | `DEGRADED_COMMUNICATION` | **0** | Dispatch degraded; 100% safe clamping |
| **90%** | 52 / 500 | **10.4%** | Near Blackout | `DEGRADED_COMMUNICATION` | **0** | Intermittent reception; safe envelope |
| **99%** | 4 / 500 | **0.8%** | Radio Blackout | `EMERGENCY_STOP` (Watchdog) | **0** | Watchdog expires; vehicle halted |

### Rigorous Audit Finding:
- **Communication Reliability:** Under 75% packet loss, communication reliability is **poor (only 25.8% of packets arrive)**. Central fleet optimization cannot function at peak responsiveness.
- **Safety Invariant Preservation:** Safety is **100% maintained**, because the vehicle local governor evaluates incoming commands against onboard sensor limits and trips the $1.0\text{ s}$ watchdog into an emergency stop during sustained blackout.

---

## 3. Link Budget & Range Characterization

- **Proximity V2V Zone ($\le 150\text{ m}$):** Direct peer-to-peer LoRa CSS achieves **$99.1\%$ PDR** with mean $\text{RSSI} = -74.8\text{ dBm}$ and $\text{SNR} = +7.4\text{ dB}$, providing reliable inter-truck platooning awareness.
- **Mid-Range Haul Road ($150\text{--}500\text{ m}$):** $\text{PDR} \ge 94.2\%$, suitable for upstream gateway slot requests.
- **Pit Shadow Zones ($> 750\text{ m}$):** Due to steep bench cuts, PDR drops below $86.4\%$, validating the need for decentralized local safety rather than centralized command dependence.
