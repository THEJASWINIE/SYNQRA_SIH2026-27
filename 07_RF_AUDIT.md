# 07_RF_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — RF / LoRa 433 MHz Communication Subsystem Audit
**Date / Timestamp:** 2026-09-27T09:45:30+05:30  
**Evaluator Role:** RF/Communication Systems Engineer, Embedded Systems Engineer  
**Absolute Principle:** NO FABRICATION — Live RF Parameters & Physical Link Truth

---

### 1. PHYSICAL RF ARCHITECTURE & SPECIFICATIONS

| Parameter | Configured Value | Hardware Implementation | Theoretical Bounds |
| :--- | :--- | :--- | :--- |
| **Radio Transceiver** | Semtech SX1278 | SPI interface on ESP32 | High-sensitivity sub-GHz LoRa modem |
| **Center Frequency** | $433.0\text{ MHz}$ (`#define LORA_FREQUENCY 433E6`) | Helical spring / SMA whip antenna | ISM band (sub-GHz license exempt) |
| **Spreading Factor** | $\text{SF} = 7$ | Configured in firmware | 128 chips/symbol |
| **Bandwidth** | $\text{BW} = 125\text{ kHz}$ | Standard narrow-band channel | Symbol rate $R_s = \frac{125000}{128} \approx 976.56\text{ symbols/s}$ |
| **Coding Rate** | $\text{CR} = 4/5$ | Error correction enabled | 25% forward error overhead |
| **Preamble Length** | $8\text{ symbols}$ | Standard LoRa sync header | $T_{\text{preamble}} \approx 12.55\text{ ms}$ |
| **Payload Length** | $32\text{ bytes}$ (V2V state string) | Canonical ASCII CSV string | $T_{\text{payload}} \approx 25.95\text{ ms}$ |
| **Packet Airtime** | $\mathbf{38.50\text{ ms}}$ | Mathematically calculated from SX1278 formula | **RF PHY Airtime Only** |
| **CRC Checking** | ENABLED | Enforced in receiver | Corrupt packets automatically discarded by silicon |

---

### 2. V2V PAYLOAD PROTOCOL INTEGRITY (RULE 2)

$$\text{Canonical Format: } \texttt{STATE,TRUCK\_01,seq,rpm,speed,ax,ay,az,gx,gy,gz}$$

- **Verification:** Both Vehicle A and Vehicle B firmware preserve the canonical comma-separated V2V protocol.
- **Backward Compatibility:** Maintained. Gateway regex parses the CSV string, validates sequence monotonicity, and maps to JSON for backend ingestion.

---

### 3. LIVE RF OBSERVATIONS & BENCH REALITY

1. **LoRa Gateway Receiver (`COM11` / `192.168.137.185`):**
   - **Boot State:** Initialized SX1278 on 433 MHz successfully.
   - **Mode:** Continuous RX mode.
   - **Packet Reception During Audit Window:** `RX packets: 0 | Forwarded: 0 | Failed: 0`.
   - **Reason:** Vehicle A was routing telemetry directly via HTTP Wi-Fi (`ENABLE_DIRECT_WIFI_TELEMETRY`), and Vehicle B mobile transmitter was in bench idle state without RF transmit pulses received.
2. **Mine Coverage & Path Loss Claims:**
   - **Audit Verdict:** **NOT TESTED IN MINE ENVIRONMENT**.
   - Tests were conducted in a room/bench environment.
   - Any claim of "tested across deep open-pit benches" or "validated through Bailadila pit walls" is **UNSUBSTANTIATED / FALSE** until field propagation measurements are gathered.
