# FOG-ORCHESTRATOR 2.0 — Dual-Vehicle Firmware Parity Matrix
**Document ID:** `DOC-03-HW-02` | **Audited Standard:** Codebase Parity Audit

---

## 1. Summary Comparison: Common Contract vs Chassis Differences

Vehicle A (`sketch_aug26a.ino`) and Vehicle B (`VEHICLE_B_TRUCK_02_...ino`) share an identical software protocol contract while preserving physical hardware distinctions:

| Firmware Subsystem | Common Fleet Contract | Vehicle A Implementation | Vehicle B Implementation | Parity Status |
| :--- | :--- | :--- | :--- | :---: |
| **Telemetry Transport** | Dual Wi-Fi REST + LoRa V2V | Dual-link enabled | Dual-link enabled | **PARITY** |
| **JSON Telemetry Schema** | `HardwareTelemetryPayload` | Canonical schema | Canonical schema | **PARITY** |
| **Sequence Counter** | Unified `globalSequence` | Monotonic across transports | Monotonic across transports | **PARITY** |
| **Session Identification** | NVS Flash `bootId` | Flash increment on reboot | Flash increment on reboot | **PARITY** |
| **LoRa Radio Settings** | 433.0 MHz, SF7, BW 125 kHz | SX1278 SPI configuration | SX1278 SPI configuration | **PARITY** |
| **V2V Wire Format** | `STATE,ID,seq,rpm,spd,a,g` | Frozen 11-field format | Frozen 11-field format | **PARITY** |
| **V2V TDM Schedule** | Non-interfering slotting | **500 ms** in 2000 ms cycle | **1000 ms** in 2000 ms cycle | **PARITY** |
| **Emergency Safe Beacon** | 1.0 Hz LoRa beacon on Wi-Fi loss | Autonomous fallback | Autonomous fallback | **PARITY** |
| **Physical Disc Slots** | Hardware specific | **42 slots** | **43 slots** | **HARDWARE** |
| **Calibration Divisor** | $K_{cal} = 34.58\text{ pulses/rev}$ | Identical kinematic scale | Identical kinematic scale | **PARITY** |
| **Motor H-Bridge Driver** | Driver-specific truth table | **L298N Bipolar** | **TB6612FNG MOSFET + STBY** | **HARDWARE** |
| **Startup Safety Lock** | Zero PWM at boot / STBY LOW | `PWM = 0` | `STBY = LOW`, `PWM = 0` | **PARITY** |
