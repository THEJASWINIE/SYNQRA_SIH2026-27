# FOG-ORCHESTRATOR 2.0 — LoRa Gateway Architecture & Data Audit
**Document ID:** `AUDIT-GW-LORA-2026-09-27`  
**Classification:** Engineering Specification & Audit  
**Author:** Principal Software Architect & Lead Engineer  
**Status:** VERIFIED & AUTHORITATIVE  

---

## 1. Gateway Purpose & Scope Boundary

The **LoRa Gateway** is an independent hardware appliance positioned along the haul road infrastructure. Its sole architectural responsibility is:

```
[ PHYSICAL VEHICLES A & B (433 MHz LoRa) ]
                     ↓ (RF Broadcast)
           [ LORA GATEWAY APPLIANCE ]
                     ↓ (HTTP POST / Wi-Fi)
[ FOG-ORCHESTRATOR 2.0 INGESTION API (/api/hardware/telemetry) ]
```

### Architectural Invariant (PAD-A/B/E & Rule 5):
The LoRa Gateway is **STRICTLY A TRANSPORT ADAPTER**.
- **NO Physics Computation:** Gateway never calculates stopping distance or safe speed.
- **NO Digital Twin State:** Gateway does not store an authoritative world model.
- **NO Telemetry Modification:** Sensor numbers are forwarded untouched.
- **NO Fabricated Radio Metrics:** RSSI and SNR values are physical RF front-end measurements sampled by the SX1278 hardware registers at packet arrival.

---

## 2. Hardware Architecture & Pin Configuration

| Component | Specification | Gateway Assignment | Function |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32D | Dual Core 240 MHz | Real-time RF packet processing & Wi-Fi HTTP transport |
| **LoRa Transceiver** | SX1278 (Ra-02) | 433.0 MHz SPI | Long-range low-power RF reception |
| **LoRa SCK** | SPI Clock | GPIO 18 | High-speed bus |
| **LoRa MISO** | SPI Data In | GPIO 19 | Hardware register reading |
| **LoRa MOSI** | SPI Data Out | GPIO 23 | Configuration commands |
| **LoRa NSS / CS** | Chip Select | GPIO 5 | Bus select |
| **LoRa RST** | Hardware Reset | GPIO 4 | Radio power-on reset |
| **LoRa DIO0** | Rx Done Interrupt | GPIO 34 | Edge-triggered packet arrival interrupt |
| **Network Link** | 802.11b/g/n Wi-Fi | Station (STA) Mode | HTTP REST uplink to Supervisory Backend |

---

## 3. Radio Frequency Ingress Parameters

```
Frequency:       433.000 MHz
Bandwidth (BW):  125 kHz
Spreading Factor:SF7 (High throughput, low latency for moving haulers)
Coding Rate:     4/5
Preamble Length: 8 symbols
Sync Word:       0x12 (Private Haulage Network)
CRC:             Hardware CRC Enabled
```

---

## 4. Ingress Frame Decoders & Backend Uplink Contracts

### 4.1 Ingress V2V State Frame
Vehicles broadcast ASCII comma-delimited state frames:
```
STATE,<vehicle_id>,<seq>,<rpm>,<speed>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>
```
**Transformation to Canonical HTTP POST Payload:**  
Endpoint: `POST /api/hardware/telemetry`
```json
{
  "vehicle_id": "TRUCK_01",
  "sequence": 142,
  "rpm": 450.2,
  "speed": 1.40,
  "ax": 102.0,
  "ay": -54.0,
  "az": 16384.0,
  "gx": 12.0,
  "gy": -4.0,
  "gz": 8.0,
  "rssi": -78,
  "snr": 9.2,
  "source": "LORA_GATEWAY",
  "boot_id": 4
}
```

### 4.2 Ingress Safe Beacon Frame
Under radio-shadow or emergency situations, vehicles emit priority beacon frames:
```
BEACON,<vehicle_id>,<beacon_seq>,<state>,<zone_id>
```
**Transformation to Canonical HTTP POST Payload:**  
Endpoint: `POST /api/hardware/safe-beacon`
```json
{
  "vehicle_id": "TRUCK_01",
  "beacon_sequence": 28,
  "state": "DEGRADED",
  "zone_id": "ZONE_HAUL_NORTH",
  "rssi": -82,
  "snr": 8.1,
  "source": "LORA_GATEWAY",
  "boot_id": 4
}
```

---

## 5. Gateway Robustness & Exception Handling

1. **Non-Blocking Network Timeout:**  
   The HTTP client uses a bounded timeout ($\le 1000\text{ ms}$). If the backend or Wi-Fi AP is momentarily congested, the request aborts and the gateway immediately returns to listening for RF packets on the SX1278 FIFO.
2. **Duplicate & Stale Frame Resilience (HTTP 409):**  
   If a vehicle packet arrives via Wi-Fi Direct *before* the LoRa relay frame reaches the backend, the backend deduplication engine responds with `HTTP 409 Conflict ("status": "DUPLICATE_IGNORED")`. The Gateway gracefully consumes the 409, logs the event, and continues execution without rebooting.
3. **Session Reset (Reboot) Transparency:**  
   When an ESP32 vehicle reboots and re-anchors sequence counting with a new `boot_id`, the Gateway transmits `boot_id` directly in the JSON body, allowing the backend to accept the re-anchored stream seamlessly.
4. **Physical Radio Quality Metrics:**  
   Every payload carries physical RSSI (dBm) and SNR (dB) measured by the SX1278 receiver. If a frame has no valid RF metadata, the fields remain `null` rather than inserting arbitrary constants.

---

## 6. Audit Conclusion & Compliance Status

| Audit Item | Status | Verified Source Reference |
| :--- | :--- | :--- |
| Strict Transport Relay Boundary | PASS | `esp32_code/LORA_GATEWAY/LORA_GATEWAY.ino` |
| SX1278 433 MHz Pinout & Config | PASS | Pin definitions: SCK 18, MISO 19, MOSI 23, SS 5, RST 4, DIO0 34 |
| Canonical Telemetry JSON Formatting | PASS | Matches `HardwareTelemetryPayload` schema in `main.py` |
| Safe Beacon Forwarding Support | PASS | Matches `SafeBeaconPayload` schema in `main.py` |
| Non-blocking $\le 1\text{s}$ HTTP Timeout | PASS | Implemented in HTTP client request configuration |
| Zero Fabrication of RSSI/SNR | PASS | Directly captures `LoRa.packetRssi()` and `LoRa.packetSnr()` |
