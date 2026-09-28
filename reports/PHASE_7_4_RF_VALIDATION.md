# PHASE 7.4 — RF BENCH VALIDATION & COMMUNICATION DEGRADATION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH26007
**Hardware Identification:** Semtech SX1278 (Ra-02) Chirp Spread Spectrum (CSS-LoRa) Transceiver  
**Operating Frequency:** 433.0 MHz | Bandwidth: 125 kHz | Spreading Factor: SF7 | Coding Rate: 4/5  
**Evidence Standard:** L7 (Bench Measured Physical RF) / L9 (Simulated DSSS Model)  
**Dataset Source:** `data/phase7_4_rf_results.csv` ($N = 6{,}000$ packets, $N \ge 1{,}000$ per test condition)  

---

## 1. Mandatory Physical RF Hardware Disclaimer

> [!IMPORTANT]
> **CSS-LoRa $\ne$ DSSS Physical Validation Rule**
> - The physical prototype hardware uses **Semtech SX1278 (Ra-02) CSS-LoRa** transceivers.
> - The multi-gateway Direct Sequence Spread Spectrum (DSSS) Gold code correlation architecture described in system documentation is an **architectural research model evaluated in simulation (L9)**.
> - The physical SX1278 Ra-02 hardware does **NOT** execute physical DSSS chipping sequences.
> - Physical RF experimental results in this report represent **"CSS-LoRa SX1278 bench validation"** and must **NEVER** be described as *"DSSS hardware validation"* or *"Mine deployment validation"*.

---

## 2. Experimental Test Matrix & Physical Bench Results

A total of 6,000 physical and channel-emulated RF frames were logged across 6 canonical test conditions ($N = 1{,}000$ packets per condition):

| Test Condition | Transmitted ($N$) | Delivered ($N$) | Packet Delivery Ratio (PDR) | Mean RSSI ($\text{dBm}$) | Mean SNR ($\text{dB}$) | Latency P50 ($\text{ms}$) | Latency P95 ($\text{ms}$) | Fallback State Triggered | Evidence Classification |
|---|---|---|---|---|---|---|---|---|---|
| **A. V2V Direct Link** | 1,000 | 1,000 | **100.0%** | $-63.2\text{ dBm}$ | $+10.7\text{ dB}$ | $24.78\text{ ms}$ | $27.24\text{ ms}$ | `NORMAL` | **L7 Physical Bench Link** |
| **B. Truck $\to$ Gateway** | 1,000 | 981 | **98.1%** | $-73.5\text{ dBm}$ | $+8.2\text{ dB}$ | $24.81\text{ ms}$ | $27.35\text{ ms}$ | `NORMAL` | **L7 Physical Bench Link** |
| **C. Gateway Failure** | 1,000 | 0 | **0.0%** | $-125.0\text{ dBm}$ | $-22.0\text{ dB}$ | N/A | N/A | `NO_GATEWAY` | **Controlled Software Injection** |
| **D. 75% Loss Sweep** | 1,000 | 254 | **25.4%** | $-86.4\text{ dBm}$ | $+4.5\text{ dB}$ | $24.80\text{ ms}$ | $27.18\text{ ms}$ | `DEGRADED_COMMUNICATION` | **Controlled Software Injection** |
| **E. Burst Shadow Loss**| 1,000 | 52 | **5.2%** | $-92.1\text{ dBm}$ | $+2.0\text{ dB}$ | $24.75\text{ ms}$ | $27.40\text{ ms}$ | `COMM_LOSS` | **Controlled Software Injection** |
| **F. Post-Fade Recovery**| 1,000 | 991 | **99.1%** | $-67.4\text{ dBm}$ | $+9.5\text{ dB}$ | $24.82\text{ ms}$ | $27.29\text{ ms}$ | `RECOVERY` $\to$ `NORMAL` | **Controlled Software Injection** |

---

## 3. Detailed Failure Mode Analysis

### Condition A & B: Clear Channel Normal Operation
- Under line-of-sight bench conditions (distances $10\text{ m} - 50\text{ m}$), SX1278 packet delivery exceeds $98\%$.
- Round-trip airtime and SPI buffer transfer consistently measures $24.8\text{ ms}$ (P50) and $27.3\text{ ms}$ (P95).

### Condition C: Gateway Severance & Power Cut
- When the gateway link drops, PDR falls to $0.0\%$.
- Within $1.050\text{ s}$ of silence, the onboard local governor detects watchdog expiry and enters `NO_GATEWAY`.
- **Safety Result:** The vehicle does not accelerate or stall uncommanded; it operates under autonomous local safe speed constraints.

### Condition D & E: Severe Channel Degradation & 100-Packet Burst Loss
- Under severe attenuation (75% to 95% injected drop rate), packet gaps occur.
- **Clarification on "Survives 75% Packet Loss":**
  - This claim means that **the local safety governor invariant ($v_{\text{command}} \le v_{\text{safe}}$) is preserved 100% of the time**, because the vehicle clamps to local sensor envelopes and rejects stale commands.
  - It does **NOT** mean the wireless network itself is reliable or delivering telemetry during a blackout.

### Condition F: Re-synchronization & Recovery
- When RF flow resumes post-fade, the `LocalVehicleSafetyGovernor` and `SafeBeaconAdapter` require multiple valid sequential frames (minimum 2 consecutive observations) before exiting recovery.
- Unrestricted speed is never instantly restored without valid state confirmation.

---

## 4. Scientific Bounds & Field Disclaimer

1. **RF Propagation Context:** Bench testing was conducted indoors with antenna attenuators and line-of-sight laboratory links.
2. **Mine Shadowing Caveat:** Open-pit iron ore haul roads in Bailadila feature deep bench benches, high-grade magnetite walls, and multipath reflections from 100-tonne steel truck bodies that will introduce significantly more severe diffraction and path loss than bench testing.
3. **Evidence Level Classification:**
   - Bench SX1278 PDR/RSSI/SNR/Airtime = **L7 (Bench Measured)**.
   - 750m deep pit RF modeling = **L6 (Empirical Assumption / Model)**.
   - Multi-gateway DSSS Gold code correlation = **L9 (Simulation Model)**.
