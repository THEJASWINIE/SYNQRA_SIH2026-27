# PHASE 7.3.4 — ATTACK #16: SX1278 RF BENCH MEASUREMENT & BAILADILA GAP AUDIT
**Module:** Wireless Telemetry & Physical Communications  
**Dataset:** `data/phase7_3_4_rf_bench_protocol.csv`  
**Classification:** **BENCH MEASURED (GREEN) / BAILADILA FIELD GAP (OPEN)**  

---

## 1. Physical Bench Test Protocol & Experimental Parameters

The project cites a packet delivery ratio (PDR) of **$99.1\%$** and a direct V2V latency of **$41.2\text{ ms}$** (mean) / **$48.6\text{ ms}$** (P99).  
The hostile audit examined the laboratory test protocol to determine exact physical operating conditions:

| Parameter | Laboratory Bench Setting | Verification Status | Scrutiny Assessment |
|:---|:---|:---:|:---|
| **Transceiver Chipset** | Semtech SX1278 (AI-Thinker Ra-02 module) | **BENCH_MEASURED** | Commercial off-the-shelf SPI transceiver |
| **Host Microcontroller** | Espressif ESP32-WROOM-32 (240 MHz dual-core) | **BENCH_MEASURED** | Standard embedded controller |
| **Carrier Center Frequency**| $433.000\text{ MHz}$ (Sub-GHz ISM Band) | **BENCH_MEASURED** | Free license ISM frequency in India |
| **Modulation** | Chirp Spread Spectrum (CSS-LoRa) | **BENCH_MEASURED** | Native SX1278 modulation |
| **Spreading Factor** | **SF7** (128 chips / symbol) | **BENCH_MEASURED** | Low-latency configuration |
| **Modulation Bandwidth** | **125 kHz** | **BENCH_MEASURED** | Standard LoRa channel bandwidth |
| **Coding Rate** | **4/5** (1 redundancy bit per 4 data bits) | **BENCH_MEASURED** | Minimal FEC overhead |
| **Transmitter Output Power**| **+20 dBm** ($100\text{ mW}$) | **BENCH_MEASURED** | Maximum legal output power |
| **Antenna Architecture** | $3\text{ dBi}$ omnidirectional quarter-wave whip | **BENCH_MEASURED** | Directly attached SMA terminal |
| **RF Channel Environment** | Open park / sports ground (Clear Line-of-Sight) | **BENCH_MEASURED** | Non-industrial test environment |
| **Test Distance** | $150.0\text{ metres}$ | **BENCH_MEASURED** | Flat suburban open-space field |
| **Packet Payload Size** | $36\text{ bytes}$ (`STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz`) | **BENCH_MEASURED** | Canonical V2V ASCII packet string |
| **Total Packet Count ($N$)**| $1,000\text{ packets}$ continuously transmitted | **BENCH_MEASURED** | Statistically sufficient for bench test |
| **Measured Packets Received**| $991\text{ packets}$ ($9\text{ packets lost}$) | **BENCH_MEASURED** | **PDR = 99.1%** |
| **Received Signal Strength**| Mean $\text{RSSI} = -84.2\text{ dBm}$ (Margin: $+35\text{ dB}$ above sensitivity)| **BENCH_MEASURED** | High signal-to-noise ratio |
| **Signal-to-Noise Ratio** | Mean $\text{SNR} = +7.8\text{ dB}$ | **BENCH_MEASURED** | Clean suburban RF environment |

---

## 2. The Bailadila Physical Extrapolation Gap

The audit evaluated whether $99.1\%$ PDR can be extrapolated to real mining operations at NMDC Bailadila Deposit 5:

```
[LABORATORY BENCH TEST]                         [NMDC BAILADILA DEPOSIT 5]
  Flat open field                                 Deep spiral open pit (200m depth)
  Zero electromagnetic interference               High-voltage electric shovels (6.6 kV)
  Clean, dry air                                  Dense hematite airborne dust & rain
  Clear optical Line-of-Sight                     Steep iron ore benches, switchbacks
  PDR = 99.1% at 150m                             Multipath reflections, shadowing, diffraction
```

### Critical Field Gaps Identified:
1. **Airborne Hematite Dust Attenuation:** Dense clouds of dry or wet iron ore dust cause dielectric scattering and RF absorption, particularly when wet. Unvalidated on site.
2. **Pit Bench Knife-Edge Shadowing:** Vehicles navigating hairpin switchbacks lose optical LOS. Signal propagation around iron ore rock faces requires diffraction, drastically reducing RSSI.
3. **Electromagnetic Noise Floor:** Operating within $50\text{ m}$ of a $10\text{--}15\text{ m}^3$ electric mining shovel or DC haulage substation creates severe impulse noise.
4. **DSSS Gold Code Architectural Status:** The proposed $+12\text{ dB}$ processing gain from Gold-code DSSS is a **MATHEMATICAL SIMULATION MODEL**. The physical ESP32 bench uses native commercial LoRa chirp spread spectrum (CSS).

---

## 3. Mandatory Presentation Language Rule

The project presentation must strictly adhere to the following language constraint:

> **Allowed Statement:**  
> *"Physical laboratory bench trials of dual-ESP32 SX1278 transceivers at 433 MHz achieved 99.1% packet delivery ratio and 41.2 ms mean latency across 150 m line-of-sight in suburban testing."*

> **Prohibited Statement:**  
> *"Radio communication is 99.1% reliable inside the Bailadila iron ore mine." (FALSE)*
