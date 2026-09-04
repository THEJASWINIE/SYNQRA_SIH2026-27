# FOG-ORCHESTRATOR 2.0 — HARDWARE MODE RUN GUIDE

This guide provides step-by-step instructions to run physical **Vehicle A (`TRUCK_01`)** and **Vehicle B (`TRUCK_02`)** hardware telemetry through the **LoRa Gateway** into the **HMI Supervisory Dashboard**.

---

## Hardware Integration Architecture

```
        VEHICLE A (`TRUCK_01`)       VEHICLE B (`TRUCK_02`)
        ESP32 + TB6612               ESP32 + L298N
          │                             │
          │ LoRa (433 MHz)              │ LoRa (433 MHz)
          └──────────────┬──────────────┘
                         │
                         ▼
                 LORA GATEWAY ESP32
                         │
                         │ USB Serial (115200 baud)
                         ▼
                    HMI BACKEND
                         │
                         │ WebSocket / REST API
                         ▼
                    HMI FRONTEND
```

---

## Step-by-Step Hardware Execution Protocol

### Step 1 — Upload Vehicle A Firmware
1. Open [`esp32_code/VEHICLE_A_HMI_FIRMWARE.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/VEHICLE_A_HMI_FIRMWARE.ino) in Arduino IDE.
2. Connect Vehicle A ESP32 via USB.
3. Select Board: `ESP32 Dev Module`, set Port, and click **Upload**.
4. Verify Serial Monitor (115200 baud): `[VEHICLE_A] Sent Telemetry: V=TRUCK_01`.

---

### Step 2 — Upload Vehicle B Firmware
1. Open [`esp32_code/VEHICLE_B_HMI_FIRMWARE.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/VEHICLE_B_HMI_FIRMWARE.ino) in Arduino IDE.
2. Connect Vehicle B ESP32 via USB.
3. Select Board: `ESP32 Dev Module`, set Port, and click **Upload**.
4. Verify Serial Monitor (115200 baud): `[VEHICLE_B] Sent Telemetry: V=TRUCK_02`.

---

### Step 3 — Start LoRa Gateway
1. Open [`esp32_code/LORA_GATEWAY_RECEIVER.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/LORA_GATEWAY_RECEIVER.ino) in Arduino IDE.
2. Connect Gateway ESP32 (with Ra-02 module) via USB to the host computer.
3. Select Board: `ESP32 Dev Module`, set Port, and click **Upload**.

---

### Step 4 — Connect Gateway USB
Keep the Gateway ESP32 plugged into the USB port (e.g. `COM3` on Windows or `/dev/ttyUSB0` on Linux).

---

### Step 5 — Configure Backend Serial Port
Open [`SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/backend/app/gateway_serial_reader.py) and set the COM port matching your Gateway USB device:
```python
gateway_reader = GatewaySerialReader(port="COM3", baudrate=115200)
```

---

### Step 6 — Start HMI Backend in HARDWARE Mode
Open Terminal 1 and execute:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\backend"
$env:HMI_MODE="HARDWARE"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### Step 7 — Start HMI Frontend
Open Terminal 2 and execute:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\frontend"
npm run dev
```

---

### Step 8 — Verify TRUCK_01 (`Vehicle A`)
- Open browser to `http://localhost:5173`.
- Confirm `TRUCK_01` status indicator displays **ONLINE** (green).
- Verify real-time wheel RPM, speed, acceleration ($AX, AY, AZ$), and gyroscope values.

---

### Step 9 — Verify TRUCK_02 (`Vehicle B`)
- Confirm `TRUCK_02` status indicator displays **ONLINE** (green).
- Power off Vehicle B or disconnect LoRa antenna.
- Verify status indicator transitions from **ONLINE** $\rightarrow$ **STALE** (yellow) after 3s $\rightarrow$ **OFFLINE** (red) after 10s.

---

## Run Verification Suite

To run automated integration tests:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python verify_vehicle_hmi_integration.py
```
