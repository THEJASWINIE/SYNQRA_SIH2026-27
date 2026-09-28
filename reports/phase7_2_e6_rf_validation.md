# EXPERIMENT E6 — RF / LORA BENCH CHARACTERIZATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**RF Transceiver:** Semtech SX1278 (Ra-02 Module, 433 MHz, Chirp Spread Spectrum - CSS)  
**Host Microcontroller:** Espressif ESP32-WROOM-32  
**Validation Classification:** L7 — Bench Measured (Field Bailadila Deposit-5 validation pending)  
**Dataset Reference:** [`data/rf_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/rf_results.csv) (10,000 packets)  
**Figures:**  
- [`figures/rf_pdr_vs_distance.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/rf_pdr_vs_distance.png)  
- [`figures/rf_rssi_vs_distance.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/rf_rssi_vs_distance.png)  

---

## 1. Physical Validation Status & Hardware Modulation Truthfulness

> [!WARNING]
> **PHYSICAL VALIDATION PENDING — BAILADILA DEPOSIT-5 RF PROPAGATION SURVEY REQUIRED**  
> RF propagation in an open-cast iron ore mine involves extreme multipath scattering off hematite/banded-iron-formation (BIF) rock benches, high dielectric absorption, and deep pit shadow zones. The results presented herein represent laboratory bench measurements with controlled RF variable attenuators and line-of-sight surrogate field testing.
>
> **MODULATION TRUTHFULNESS:**  
> The physical hardware utilizes Semtech SX1278 transceivers operating in Chirp Spread Spectrum (CSS) LoRa mode. The system does **NOT** currently utilize a custom Direct Sequence Spread Spectrum (DSSS) PHY layer on hardware; DSSS is an evaluated architectural protocol model.

---

## 2. RF Configuration & Physical Parameters

- **Carrier Frequency:** 433.0 MHz (ISM band)
- **Modulation:** LoRa CSS (Spreading Factor SF = 7, Bandwidth BW = 125 kHz, Coding Rate CR = 4/5)
- **Tx Power:** +20 dBm (100 mW, with PA_BOOST enabled)
- **Preamble Length:** 8 symbols; Fixed payload: 32 bytes (Standard V2V state packet)
- **Time-on-Air (ToA):** Calculated $\approx 61.7\text{ ms}$

---

## 3. Measured Link Quality Breakdown (10,000 Packets)

| Distance Equivalent (m) | Path Attenuation / Condition | Mean RSSI (dBm) | Mean SNR (dB) | Packet Delivery Ratio (PDR, %) | P50 One-Way ToA (ms) | P99 Latency (ms) |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **50** | Clear Line-of-Sight (LOS) | -62.4 | +9.8 | **99.8%** | 62.1 | 68.4 |
| **150** | Clear Line-of-Sight (LOS) | -74.8 | +7.4 | **99.1%** | 62.2 | 69.1 |
| **300** | Clear Line-of-Sight (LOS) | -86.2 | +4.1 | **97.6%** | 62.4 | 72.8 |
| **500** | Mild Bench Edge Shadowing | -96.5 | +0.8 | **94.2%** | 63.1 | 79.5 |
| **750** | Non-Line-of-Sight (NLOS Rock Face)| -108.4 | -5.2 | **86.4%** | 64.8 | 89.2 |
| **1,000** | Heavy Pit Obstruction / Bench Cut | -118.2 | -11.4 | **68.5%** | 67.2 | 114.0 |
| **1,200** | Deep Pit Shadow Zone | -124.6 | -16.2 | **42.1%** | 71.0 | 145.0 |

---

## 4. Key Engineering Conclusions

1. **V2V Inter-Truck Proximity ($\le 150\text{ m}$):**  
   At normal platooning and emergency convoy distances ($\le 150\text{ m}$), V2V packet delivery exceeds **99.1%** with high link margins (SNR $> +7\text{ dB}$). Direct vehicle-to-vehicle awareness packets remain highly reliable.

2. **Long-Range Haul Road Shadowing:**  
   As haulage distances approach 1 km through multi-bench switchbacks, terrain attenuation causes packet delivery to degrade toward 68%. This justifies the dual-path architecture: local V2V direct safety beacons handle immediate collision avoidance, while central dispatch handles strategic arrival shaping.
