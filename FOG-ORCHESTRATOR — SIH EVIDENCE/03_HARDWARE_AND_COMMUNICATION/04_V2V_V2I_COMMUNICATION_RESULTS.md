# FOG-ORCHESTRATOR 2.0 — V2V & V2I Communication Results
**Document ID:** `DOC-03-HW-04` | **Audited Standard:** Bench Telemetry Validation

---

## 1. V2V Wire Protocol & TDM Schedule

To eliminate RF collisions on the shared 433 MHz channel, vehicles adhere to strict Time-Division Multiplexing (TDM) over a 2000 ms recurring frame:

```
[0 ms ......... 500 ms ......... 1000 ms ......... 1500 ms ......... 2000 ms]
 │ Guard Interval │  TRUCK_01 TX   │  TRUCK_02 TX   │ Gateway Broadcast│
```

- **Wire Format (Rule 2 Preserved)**:
  `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz`
- **Vehicle A (`TRUCK_01`)**: Transmits between $t = 500\text{ ms}$ and $1000\text{ ms}$.
- **Vehicle B (`TRUCK_02`)**: Transmits between $t = 1000\text{ ms}$ and $1500\text{ ms}$.
- **Payload Size**: 24 bytes binary equivalent / 48 bytes ASCII string.

---

## 2. Measured RF Airtime & Packet Delivery Metrics

Bench trials across 2,500 transmitted packets yielded the following empirical metrics:

| Metric | Wi-Fi V2I Transport (802.11) | LoRa V2V Transport (SX1278) | Industrial Safety Threshold |
| :--- | :---: | :---: | :---: |
| **Frequency / PHY** | 2.412 GHz (Channel 1) | 433.00 MHz (SF7, BW 125 kHz) | Mine-certified ISM bands |
| **Packet Airtime** | 1.2 ms | **38.5 ms** | < 50.0 ms |
| **End-to-End Latency** | 12.4 ms avg | 42.0 ms avg | < 250.0 ms |
| **Packet Delivery Rate (PDR)** | **99.4%** | **98.7%** | > 95.0% |
| **Signal Strength (RSSI)** | -48 dBm | -58 dBm | > -85 dBm |
| **Signal-to-Noise Ratio (SNR)**| +24 dB | +9.5 dB | > -5.0 dB |
