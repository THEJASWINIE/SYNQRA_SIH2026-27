# 03_HARDWARE_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Comprehensive Physical Hardware & Serial Interface Audit
**Date / Timestamp:** 2026-09-27T09:41:00+05:30  
**Evaluator Role:** Senior Embedded Systems Engineer, Robotics Hardware Test Engineer  
**Absolute Principle:** NO FABRICATION — Physical Detection, Serial States, and Hardware Reality

---

### 1. PHYSICAL HARNESS & SERIAL PORT INSPECTION

An exhaustive probe of the Windows Plug-and-Play (`Win32_PnPEntity`) device subsystem and COM ports revealed three physical USB-to-UART bridge controllers connected to the workstation:

```text
COM11: Silicon Labs CP210x USB to UART Bridge (VID: 10C4, PID: EA60, Rev 0001)
COM14: USB-Enhanced-SERIAL CH9102 (VID: 1A86, PID: 55D4, Rev 5B53023552)
COM21: Silicon Labs CP210x USB to UART Bridge (VID: 10C4, PID: EA60, Location: 5&274D72C6&0&6)
```

#### Detailed Findings per Interface:

1. **COM11 — LoRa Gateway Node (SX1278 433 MHz + ESP32):**
   - **Hardware State:** Fully operational.
   - **Network Link:** Associated with hotspot SSID `SYNQRA_HOST` at IP `192.168.137.185`.
   - **Application Status:** Running `LORA_GATEWAY_RECEIVER.ino`. Actively polling the backend health endpoint `http://192.168.137.1:8000/api/health` at 1–2 Hz, receiving HTTP 200 OK responses.
   - **Serial Port Access:** Port is locked by active Arduino IDE process (PID 34944), confirming real-time developer serial monitoring.

2. **COM14 — Auxiliary ESP32-WROOM-32E (CH9102):**
   - **Hardware State:** Hardware powered, but firmware corrupted.
   - **Direct Serial Interception:**
     ```text
     E (338) esp_image: Image hash failed - image is corrupt
     E (338) boot: OTA app partition slot 0 is not bootable
     E (338) esp_image: image at 0x150000 has invalid magic byte (nothing flashed here?)
     E (344) boot: OTA app partition slot 1 is not bootable
     E (349) boot: No bootable app partitions in the partition table
     rst:0x3 (SW_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
     ```
   - **Finding:** The flash memory contains a broken image hash. The chip is stuck in an infinite reboot loop. Marked as **BLOCKED / FAIL** until reflashed.

3. **COM21 — Auxiliary / Vehicle ESP32 (CP210x):**
   - **Hardware State:** Connected, but port currently held open (`PermissionError: Access is denied`) by an active background session or Arduino IDE instance.

4. **Vehicle A Mobile Node (TRUCK_01):**
   - **Connection Mode:** Wireless via Mobile Hotspot `SYNQRA_HOST`.
   - **Assigned IP:** `192.168.137.43` (MAC `70-4b-ca-49-bd-b4`, Espressif).
   - **Ping Round-Trip:** 140–221 ms (Active).
   - **Telemetry Streaming:** Sent frames 1 through 15 via direct HTTP POST to `/api/hardware/telemetry`.

5. **Vehicle B Mobile Node (TRUCK_02):**
   - **Connection Mode:** Wireless via Mobile Hotspot `SYNQRA_HOST`.
   - **Assigned IP:** `192.168.137.126` (MAC `8c-94-df-8f-44-7c`, Espressif).
   - **Ping Round-Trip:** 80–94 ms (Active).
   - **Direct HTTP Telemetry:** Inactive by design (`ENABLE_DIRECT_WIFI_TELEMETRY = false` in firmware). Communicates via 433 MHz LoRa V2V.

---

### 2. MOTOR DRIVER ELECTRICAL & LOGICAL PINOUT AUDIT

#### Vehicle A: L298N Dual Full-Bridge Driver
```text
LEFT_IN1:   GPIO 25 (ESP32 Output) -> L298N IN1
LEFT_IN2:   GPIO 26 (ESP32 Output) -> L298N IN2
LEFT_PWM:   GPIO 27 (ESP32 Output / LEDC) -> L298N ENA
RIGHT_IN1:  GPIO 32 (ESP32 Output) -> L298N IN3
RIGHT_IN2:  GPIO 33 (ESP32 Output) -> L298N IN4
RIGHT_PWM:  GPIO 14 (ESP32 Output / LEDC) -> L298N ENB
MOTOR_STBY: GPIO 13 (ESP32 Output) -> L298N Enable / Standby line
```
- **Driver Logic Check:** Direction controlled by differential logic on `IN1`/`IN2` and `IN3`/`IN4`. Forward: `IN1=HIGH, IN2=LOW`. Speed modulated via 1 kHz 8-bit PWM on `ENA`/`ENB`.
- **Finding:** No pin conflicts. GPIO 35 is properly used for optical encoder input (GPIO 34-39 are input-only on ESP32, preventing drive conflict).

#### Vehicle B: TB6612FNG Dual H-Bridge Driver
```text
PWMA:       GPIO 27 (LEDC Channel 0, 1 kHz, 8-bit)
AIN1:       GPIO 25 (Direction A)
AIN2:       GPIO 26 (Direction A)
PWMB:       GPIO 14 (LEDC Channel 1, 1 kHz, 8-bit)
BIN1:       GPIO 32 (Direction B)
BIN2:       GPIO 33 (Direction B)
STBY:       GPIO 13 (Hardware Standby Control)
```
- **Critical TB6612FNG Invariant:** The `STBY` (Standby) pin **MUST** be pulled HIGH to take the H-bridges out of high-impedance mode. When `STBY` is LOW or floating, both motor outputs are disconnected (coasting/high-Z).
- **Firmware Verification:** Firmware correctly sets `pinMode(MOTOR_STBY, OUTPUT)` and executes `digitalWrite(MOTOR_STBY, HIGH)` on driver enable.
- **Fail-safe Logic:** When safety limits trip or command timeout expires (>15,000 ms), the firmware executes `digitalWrite(MOTOR_STBY, LOW)` and pulls PWM to 0, providing hardware-level motor cutoff.

---

### 3. LIVE MOTOR & ENCODER BEHAVIOR AUDIT

In accordance with **Absolute Rule #1 (NO FABRICATION)**:
- **Motor Movement:** During the live audit window, both vehicles were stationary on the bench. Telemetry logged from Vehicle A confirmed `rpm: 0.00`, `speed: 0.00 m/s`. No synthetic encoder pulses were generated.
- **Physical Displacement:** Since track rolling across measured intervals (0.5m, 1m, 2m, 3m, 5m) was not physically executed during this terminal session, these tests are recorded as **NOT TESTED (BENCH ONLY)** rather than fabricated PASS.
- **Sensor Telemetry:** Live MPU6050 gravity vectors ($z \approx 8.62\text{ m/s}^2$ indicating slight chassis tilt) and Wi-Fi RSSI ($-44\text{ dBm}$) confirm physical sensor presence.
