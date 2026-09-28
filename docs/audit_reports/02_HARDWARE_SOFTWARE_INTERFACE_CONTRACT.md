# 02 — HARDWARE-SOFTWARE INTERFACE CONTRACT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**

*(The full specification is maintained in [docs/HARDWARE_SOFTWARE_INTERFACE_CONTRACT.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/HARDWARE_SOFTWARE_INTERFACE_CONTRACT.md))*

### Authoritative Interface Matrix
| ID | Interface Name | Protocol | Physical Medium | Direction | Update Rate | Timeout |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IF-01** | HEMM Raw Telemetry | Custom CSV / V2V | 433 MHz LoRa / UART | ESP32 $\to$ Gateway | 10 Hz (100 ms) | 500 ms |
| **IF-02** | Gateway Telemetry Uplink | HTTP POST JSON | Wi-Fi 802.11 b/g/n | Gateway $\to$ Backend | 10 Hz (100 ms) | 1000 ms |
| **IF-03** | Environmental Visibility | Modbus RTU / JSON | RS485 / Ethernet | Weather Station $\to$ Backend | 1 Hz (1000 ms) | 3000 ms |
| **IF-04** | Vehicle Wheel Speed | Pulse / CAN J1939 | Hall Effect / TWAI | Sensor $\to$ Local ECU | 20 Hz (50 ms) | 200 ms |
| **IF-05** | Haul Road Grade | DEM / Inclinometer | CAN J1939 / Memory | GIS / Sensor $\to$ Twin | 1 Hz (1000 ms) | 2000 ms |
| **IF-06** | Service & Retarder Brake | J1939 EBC1/ERC1 | CAN 250 kbps TWAI | Brake ECU $\leftrightarrow$ Local Gov | 20 Hz (50 ms) | 150 ms |
| **IF-07** | Speed Command Dispatch | J1939 Prop-B / JSON | Central Wi-Fi / CAN | Backend $\to$ Local Gov | 10 Hz (100 ms) | 500 ms |
| **IF-08** | GNSS / Local Positioning | NMEA 0183 / JSON | UART / Ethernet | GNSS Receiver $\to$ Twin | 5 Hz (200 ms) | 1000 ms |
| **IF-09** | RF Link Metrics | LoRa Packet Metadata | SX1278 Internal Reg | LoRa PHY $\to$ Gateway | 10 Hz (100 ms) | 500 ms |
| **IF-10** | DSSS / Gateway State | Internal Adapter | Software Pipe | Selector $\to$ Orchestrator | 10 Hz (100 ms) | 300 ms |
| **IF-11** | Sensor Health & Quality | Internal Typed Record| Software Pipe | Health Filter $\to$ Gov | 10 Hz (100 ms) | 200 ms |
| **IF-12** | Local Safety Governor State| CAN J1939 / WebSocket| CAN / TCP | Local Gov $\to$ HMI / Twin | 10 Hz (100 ms) | 500 ms |
| **IF-13** | Safe Beacon Broadcast | Custom ASCII Broadcast| 433 MHz LoRa PHY | Vehicle $\to$ Broadcast | 2 Hz – 5 Hz | 1000 ms |
