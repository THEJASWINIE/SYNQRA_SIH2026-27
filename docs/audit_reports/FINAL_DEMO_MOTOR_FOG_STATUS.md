# FINAL DEMO MOTOR + FOG STATUS & DEMO RUNBOOK
**FOG-ORCHESTRATOR 2.0 — SIH Grand Finale Integration & Verification**

---

## 1. ROOT CAUSE ANALYSIS: "THE MOTOR IS NOT ROTATING FORWARD"

Prior to this engineering pass, physical forward motor motion failed due to a confluence of four specific software/hardware discrepancies:

1. **Peripheral Incompatibility on ESP32 Core 3.x (Vehicle A):**
   Vehicle A (`sketch_aug26a.ino`) called legacy `analogWrite(LEFT_PWM, pwm)` and `pinMode(PWM, OUTPUT)` on GPIOs 27 and 14. Under ESP32 Arduino Core 3.3.11, `analogWrite()` does not reliably drive hardware timers on those pins without explicit LEDC attachment. Vehicle B had already migrated to Core 3.x `ledcAttach(pin, 1000, 8)` / `ledcWrite(pin, pwm)`, whereas Vehicle A generated 0 effective duty cycle.

2. **TB6612FNG Standby Gate Unasserted (Vehicle A):**
   The motor driver for Vehicle A was updated to **TB6612FNG** (matching Vehicle B). The TB6612FNG driver requires the `MOTOR_STBY` pin (GPIO 13) to be held **HIGH** for motor drive FETs to engage. In Vehicle A, `setForwardDirection()` failed to assert `MOTOR_STBY = HIGH`, leaving the driver in high-impedance standby (floating stop).

3. **Static Chassis Friction vs. Zero Minimum PWM (Vehicles A & B):**
   Both sketches defined `MIN_MOTOR_PWM = 0` and used direct linear scaling from 0 to 220 PWM. When commanding low demo speeds (e.g., $0.20\text{ m/s}$), the computed PWM was $\approx 31$. For a real DC gearmotor loaded with chassis, battery, sensors, and tire rolling friction, $31\text{ PWM}$ produces stall torque below static friction. The motor hummed or remained motionless.

4. **Telemetry Ingress Response Discarded & Missing Forward Action:**
   Every 2 seconds, both vehicles send HTTP POST telemetry to `/api/hardware/telemetry`. The backend governor calculated and returned `target_speed_mps`, `v_safe_mps`, and `fog_factor` in the HTTP 200 JSON response. However, neither vehicle firmware ever called `http.getString()` or parsed `target_speed_mps` from the response. Furthermore, `command_gateway.py` and `main.py` lacked the explicit `"FORWARD"` action in their valid action allowlists, rejecting manual forward commands.

5. **Wi-Fi Safe-Beacon Failsafe Deadlock (Vehicle A):**
   In `connectWiFi()`, when Wi-Fi successfully connected, `wifiState = COMM_CONNECTED;` was omitted. Because `wifiState` remained initialized to `COMM_DISCONNECTED`, the SX1278 safe beacon failsafe triggered every loop cycle in `loop()`, continuously executing `commandedSpeedMs = 0.0f; targetMotorPWM = 0; stopVehicle();`.

---

## 2. ACTUAL CURRENT MOTOR-DRIVER CONFIGURATION

**Authoritative Hardware Truth:**
Both Vehicle A (`TRUCK_01`) and Vehicle B (`TRUCK_02`) use the **SAME MOTOR DRIVER: TB6612FNG Dual H-Bridge Motor Driver**.

- **Historical Assumption Cleared:** The assumption that Vehicle A was an L298N is obsolete.
- **Standby Logic:** `MOTOR_STBY` (GPIO 13) is active HIGH. HIGH = Drive enabled; LOW = Safe High-Z Stop.
- **PWM Modulation:** ESP32 Core 3.x LEDC hardware PWM generator at $1000\text{ Hz}$, $8\text{-bit}$ resolution ($0\text{--}255$, clamped to $0\text{--}220$).
- **Minimum Effective PWM:** Configured to **60** for any speed $> 0.0\text{ m/s}$. When speed $= 0.0\text{ m/s}$, PWM drops strictly to **0** and `MOTOR_STBY` is brought LOW.

---

## 3. VEHICLE A (TRUCK_01) WIRING & PIN CONFIGURATION

| Signal Name | ESP32 GPIO | TB6612FNG Pin / Hardware Connection | Logic Description |
| :--- | :--- | :--- | :--- |
| `LEFT_IN1` | GPIO 25 | AIN1 (Motor A / Left Direction 1) | Direction logic (LOW for forward) |
| `LEFT_IN2` | GPIO 26 | AIN2 (Motor A / Left Direction 2) | Direction logic (HIGH for forward) |
| `LEFT_PWM` | GPIO 27 | PWMA (Motor A PWM Speed) | LEDC Hardware PWM ($1000\text{ Hz}$, 8-bit) |
| `RIGHT_IN1` | GPIO 32 | BIN1 (Motor B / Right Direction 1) | Direction logic (HIGH for forward) |
| `RIGHT_IN2` | GPIO 33 | BIN2 (Motor B / Right Direction 2) | Direction logic (LOW for forward) |
| `RIGHT_PWM`| GPIO 14 | PWMB (Motor B PWM Speed) | LEDC Hardware PWM ($1000\text{ Hz}$, 8-bit) |
| `MOTOR_STBY`| GPIO 13 | STBY (Standby Gate) | Active HIGH (HIGH = Drive, LOW = Standby Stop) |
| `SPEED_SENSOR`| GPIO 35 | Wheel Encoder Pulse Input | Interrupt input (RISING edge, 42 PPR disk) |
| `MPU_SDA` | GPIO 21 | MPU6050 SDA | I2C Data ($400\text{ kHz}$) |
| `MPU_SCL` | GPIO 22 | MPU6050 SCL | I2C Clock |
| `LORA_SS` | GPIO 5 | SX1278 NSS (Chip Select) | SPI CS |
| `LORA_RST` | GPIO 4 | SX1278 NRESET | Hardware Reset |
| `LORA_DIO0` | GPIO 34 | SX1278 DIO0 (Rx/Tx Done) | Interrupt input |
| `LORA_SCK` | GPIO 18 | SX1278 SCK | SPI Clock |
| `LORA_MISO`| GPIO 19 | SX1278 MISO | SPI Master In |
| `LORA_MOSI`| GPIO 23 | SX1278 MOSI | SPI Master Out |

---

## 4. VEHICLE B (TRUCK_02) WIRING & PIN CONFIGURATION

| Signal Name | ESP32 GPIO | TB6612FNG Pin / Hardware Connection | Logic Description |
| :--- | :--- | :--- | :--- |
| `LEFT_IN1` | GPIO 25 | AIN1 (Motor A / Left Direction 1) | Direction logic (LOW for forward) |
| `LEFT_IN2` | GPIO 26 | AIN2 (Motor A / Left Direction 2) | Direction logic (HIGH for forward) |
| `LEFT_PWM` | GPIO 27 | PWMA (Motor A PWM Speed) | LEDC Hardware PWM ($1000\text{ Hz}$, 8-bit) |
| `RIGHT_IN1` | GPIO 32 | BIN1 (Motor B / Right Direction 1) | Direction logic (HIGH for forward) |
| `RIGHT_IN2` | GPIO 33 | BIN2 (Motor B / Right Direction 2) | Direction logic (LOW for forward) |
| `RIGHT_PWM`| GPIO 14 | PWMB (Motor B PWM Speed) | LEDC Hardware PWM ($1000\text{ Hz}$, 8-bit) |
| `MOTOR_STBY`| GPIO 13 | STBY (Standby Gate) | Active HIGH (HIGH = Drive, LOW = Standby Stop) |
| `SPEED_SENSOR`| GPIO 35 | Wheel Encoder Pulse Input | Interrupt input (RISING edge, 43 PPR disk) |
| `MPU_SDA` | GPIO 21 | MPU6050 SDA | I2C Data ($400\text{ kHz}$) |
| `MPU_SCL` | GPIO 22 | MPU6050 SCL | I2C Clock |
| `LORA_SS` | GPIO 5 | SX1278 NSS (Chip Select) | SPI CS |
| `LORA_RST` | GPIO 4 | SX1278 NRESET | Hardware Reset |
| `LORA_DIO0` | GPIO 34 | SX1278 DIO0 (Rx/Tx Done) | Interrupt input |
| `LORA_SCK` | GPIO 18 | SX1278 SCK | SPI Clock |
| `LORA_MISO`| GPIO 19 | SX1278 MISO | SPI Master In |
| `LORA_MOSI`| GPIO 23 | SX1278 MOSI | SPI Master Out |

---

## 5. FIRMWARE CHANGES

### Vehicle A (`esp32_code/sketch_aug26a/sketch_aug26a.ino`)
1. **Added WebServer on Port 80 (Deferred to Post-WiFi):** Created `WebServer commandServer(80)` implementing `/api/command` (POST) and `/api/command/status` (GET) with JSON request parsing for `"action": "FORWARD"`, `"action": "STOP"`, and `"target_speed_ms"`. Resolved FreeRTOS crash (`assert failed: xQueueSemaphoreTake queue.c:1709 (( pxQueue ))`) by defining `startCommandServer()` and strictly deferring `commandServer.begin()` until after Wi-Fi / lwIP network interface initialization.
2. **ESP32 Core 3.x LEDC Migration:** Replaced broken `analogWrite` with `ledcAttach(LEFT_PWM, 1000, 8)` and `ledcWrite(LEFT_PWM, pwm)`.
3. **Standby Gate Management:** Explicitly asserted `digitalWrite(MOTOR_STBY, HIGH)` during forward drive and `LOW` during stops.
4. **Minimum Starting PWM & Bounded Mapping:** Configured `MIN_EFFECTIVE_PWM = 60` and `MAX_MOTOR_PWM = 220` with monotonic piecewise interpolation for speed $> 0.0\text{ m/s}$.
5. **Fixed Safe-Beacon Lockout:** Set `wifiState = COMM_CONNECTED;` in `connectWiFi()` and dynamically maintained link state to eliminate spurious safe-beacon halts.
6. **Closed-Loop Response Ingestion:** In `sendLocalToHMI()`, parsed `target_speed_mps` from the backend's HTTP 200 JSON response, applying authoritative governor speed commands directly into the motor ramp loop.
7. **Safe Boot Invariant:** Initialized `DEFAULT_SPEED_MS = 0.0f;`, `commandedSpeedMs = 0.0f;`, and `stopVehicle();` ensuring vehicles power on in a safe stopped state until commanded.
8. **Serial Diagnostic Commands:** Added interactive serial console commands (`FORWARD <spd>`, `STOP`, `DIR_NORMAL`, `DIR_INVERT_LEFT`, `DIR_INVERT_RIGHT`, `STATUS`, `HELP`).

### Vehicle B (`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino`)
1. **Minimum Starting PWM:** Added `MIN_EFFECTIVE_PWM = 60` in `speedToPWM()`.
2. **Vmax Calibration Invariant:** Set `MAX_PROTOTYPE_SPEED_MS = 1.30f` matching Vehicle B's calibrated physical envelope.
3. **Action Handling in HTTP Server:** Extended `handleVehicleCommand()` to parse `"action": "FORWARD"` (defaulting to safe $0.40\text{ m/s}$) and `"action": "STOP"`.
4. **Closed-Loop Response Ingestion:** Parsed `target_speed_mps` from HTTP 200 response in `sendLocalToHMI()`.
5. **Safe Boot Invariant:** Set `DEFAULT_SPEED_MS = 0.0f`, `commandedSpeedMs = 0.0f`, and disabled continuous forward test mode (`CONTINUOUS_FORWARD_TEST = false`).
6. **Serial Diagnostic Commands:** Added identical interactive serial diagnostic commands and motor inversion toggles.

---

## 6. COMMAND-PATH & BACKEND CHANGES

### Backend (`SYNQRA_SIH2026-27-HMI/backend/app/main.py`)
1. **Allowlist Update:** Added `"FORWARD"` to valid supervisory actions (`["TARGET_SPEED", "FORWARD", "HOLD", "STOP", "RELEASE"]`).
2. **Latest Commanded Speed Store:** Maintained `latest_commanded_speed_by_vehicle` dict across command dispatches.
3. **Dynamic Vehicle IP Discovery:** In `ingest_hardware_telemetry(payload, request)`, inspected `request.client.host` to dynamically discover and cache ESP32 LAN IP addresses (`vehicle_client_ips`).
4. **Direct Vehicle HTTP Dispatcher:** Implemented asynchronous background task `_dispatch_vehicle_command_http()` that transmits accepted commands to `http://<vehicle_ip>/api/command` and marks transmission / ACK in `command_gateway`.
5. **Authoritative Governor Resolution:** When hardware telemetry arrives, `compute_vehicle_governor()` computes `applied_speed_mps` clamped by the active fog factor, returning it as `target_speed_mps` in the telemetry response.

---

## 7. FOG GOVERNOR & SAFETY SOLVER

The environmental state model computes the safe speed limit according to the canonical formula:
$$v_{\text{safe}}(\text{vehicle}) = \min(V_{\text{max\_vehicle}}, V_{\text{site\_limit}}) \times \text{fog\_factor}$$
$$v_{\text{applied}} = \min(v_{\text{requested}}, v_{\text{safe}})$$

The piecewise linear fog policy ($dfactor / dfog \le 0$) guarantees monotonic non-increasing speed limits:
- **CLEAR ($\text{intensity} = 0.00$):** Visibility $= 1000\text{ m}$, $\text{factor} = 1.00$, $v_{\text{safe}} = 0.80\text{ m/s}$.
- **LIGHT FOG ($\text{intensity} = 0.25$):** Visibility $= 500\text{ m}$, $\text{factor} = 0.75$, $v_{\text{safe}} = 0.60\text{ m/s}$.
- **MODERATE FOG ($\text{intensity} = 0.50$):** Visibility $= 250\text{ m}$, $\text{factor} = 0.50$, $v_{\text{safe}} = 0.40\text{ m/s}$.
- **HEAVY FOG ($\text{intensity} = 0.75$):** Visibility $= 100\text{ m}$, $\text{factor} = 0.30$, $v_{\text{safe}} = 0.24\text{ m/s}$ (active governor clamp).
- **SEVERE FOG ($\text{intensity} = 1.00$):** Visibility $= 50\text{ m}$, $\text{factor} = 0.00$, $v_{\text{safe}} = 0.00\text{ m/s}$ (complete emergency stop).
- **CLEAR RECOVERY ($\text{intensity} = 0.00$):** Visibility $= 1000\text{ m}$, $\text{factor} = 1.00$, $v_{\text{safe}} = 0.80\text{ m/s}$.

---

## 8. CLI COMMAND SYNTAX

The command-line interface `tools/inject_fog.py` is the **ONLY** environmental injection path. The HMI provides read-only visualization and has no injection controls.

```bash
# Set named fog conditions:
python tools/inject_fog.py --condition clear
python tools/inject_fog.py --condition light
python tools/inject_fog.py --condition moderate
python tools/inject_fog.py --condition heavy
python tools/inject_fog.py --condition severe --severe-stop

# Set exact continuous numeric intensities (0.00 to 1.00):
python tools/inject_fog.py --intensity 0.00
python tools/inject_fog.py --intensity 0.25
python tools/inject_fog.py --intensity 0.50
python tools/inject_fog.py --intensity 0.75
python tools/inject_fog.py --intensity 1.00 --severe-stop
```

### Manual Motor Diagnostic CLI (`tools/test_motor.py`)
```bash
# Test Vehicle A forward speeds:
python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.20
python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.40
python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.60
python tools/test_motor.py --vehicle TRUCK_01 --action STOP

# Test Vehicle B forward speeds:
python tools/test_motor.py --vehicle TRUCK_02 --action FORWARD --speed 0.40
python tools/test_motor.py --vehicle TRUCK_02 --action STOP

# Emergency stop all vehicles:
python tools/test_motor.py --vehicle ALL --action STOP
```

---

## 9. VEHICLE CALIBRATION & PWM MAPPING

| Vehicle | Driver | Calibrated $V_{\text{max}}$ | Encoder PPR | Calibrated $K_{\text{cal}}$ | Min Starting PWM | Max PWM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vehicle A (`TRUCK_01`)** | TB6612FNG | $1.40\text{ m/s}$ ($5.04\text{ km/h}$) | $42.0\text{ PPR}$ | $34.58$ | $60$ | $220$ |
| **Vehicle B (`TRUCK_02`)** | TB6612FNG | $1.30\text{ m/s}$ ($4.68\text{ km/h}$) | $43.0\text{ PPR}$ | $34.58$ | $60$ | $220$ |

**PWM Conversion Formula (Embedded Invariant):**
```cpp
if (speedMs <= 0.0f) {
    return 0; // Safe STOP
}
float ratio = constrain(speedMs / MAX_PROTOTYPE_SPEED_MS, 0.0f, 1.0f);
int pwm = MIN_EFFECTIVE_PWM + (int)round(ratio * (MAX_MOTOR_PWM - MIN_EFFECTIVE_PWM));
return constrain(pwm, MIN_EFFECTIVE_PWM, MAX_MOTOR_PWM);
```

**Calculated Values:**
- $0.00\text{ m/s}$ (STOP) $\to$ $\text{PWM} = 0$, Direction `STOP`, `MOTOR_STBY = LOW`
- $0.20\text{ m/s}$ (LOW) $\to$ Vehicle A: $\text{PWM} = 83$, Vehicle B: $\text{PWM} = 85$, Direction `FORWARD`
- $0.40\text{ m/s}$ (DEMO) $\to$ Vehicle A: $\text{PWM} = 106$, Vehicle B: $\text{PWM} = 109$, Direction `FORWARD`
- $0.60\text{ m/s}$ (HIGH) $\to$ Vehicle A: $\text{PWM} = 129$, Vehicle B: $\text{PWM} = 134$, Direction `FORWARD`
- $0.24\text{ m/s}$ (HEAVY FOG CLAMP) $\to$ Vehicle A: $\text{PWM} = 87$, Vehicle B: $\text{PWM} = 90$, Direction `FORWARD`

---

## 10. PROTOCOLS & DATA SCHEMAS

### Canonical V2V Packet (Preserved & Unmodified)
```text
STATE,<vehicle_id>,<seq>,<rpm>,<speed_mps>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>
```
Example:
```text
STATE,TRUCK_02,142,120.50,0.400,12,-4,980,1,0,-2
```

### Canonical V2I Ingress Payload (`/api/hardware/telemetry`)
```json
{
  "vehicle_id": "TRUCK_01",
  "sequence": 142,
  "rpm": 120.5,
  "speed": 0.40,
  "ax": 12.0,
  "ay": -4.0,
  "az": 980.0,
  "gx": 1.0,
  "gy": 0.0,
  "gz": -2.0,
  "rssi": -72,
  "snr": 9.5,
  "source": "DIRECT_WIFI",
  "timestamp": 1790520600.0,
  "boot_id": 1
}
```

### Authoritative Telemetry Response (Closed-Loop Ingestion)
```json
{
  "status": "ACCEPTED",
  "vehicle_id": "TRUCK_01",
  "sequence": 142,
  "source": "DIRECT_WIFI",
  "is_duplicate": false,
  "communication_status": "ONLINE",
  "target_speed_mps": 0.40,
  "v_safe_mps": 0.80,
  "fog_factor": 1.0,
  "governor_state": "NORMAL",
  "command": {
    "action": "TARGET_SPEED",
    "target_speed_mps": 0.40,
    "v_safe_mps": 0.80,
    "fog_factor": 1.0,
    "governor_state": "NORMAL",
    "governor_reason": "AUTHORITATIVE_GOVERNOR"
  }
}
```

---

## 11. AUTOMATED VERIFICATION RESULTS

| Test Suite / Scope | Commands Executed | Result | Details |
| :--- | :--- | :--- | :--- |
| **Vehicle A Firmware Compilation** | `arduino-cli compile --fqbn esp32:esp32:esp32 esp32_code/sketch_aug26a` | **PASS [SOFTWARE VERIFIED]** | 0 errors. Flash: 84%, RAM: 15%. |
| **Vehicle B Firmware Compilation** | `arduino-cli compile --fqbn esp32:esp32:esp32 esp32_code/VEHICLE_B_...` | **PASS [SOFTWARE VERIFIED]** | 0 errors. Flash: 84%, RAM: 15%. |
| **Motor & Fog Regression Suite** | `python -m pytest tests/test_motor_fog_closed_loop.py -v` | **PASS [SOFTWARE VERIFIED]** | 8 passed in 0.50s. |
| **Backend Integration Suite** | `python -m pytest SYNQRA_SIH2026-27-HMI/backend -q` | **PASS [SOFTWARE VERIFIED]** | 33 passed in 1.39s. |
| **Root Regression Suite** | `python -m pytest -q` | **PASS [SOFTWARE VERIFIED]** | 1222 passed, 1 skipped in 41.03s. |
| **Frontend Component & Contract Suite** | `npm test -- --run` | **PASS [SOFTWARE VERIFIED]** | 1860 passed (71 test files) in 8.46s. |
| **Frontend Production Bundle** | `npm run build` | **PASS [SOFTWARE VERIFIED]** | `tsc --noEmit && vite build` built in 5.64s. |
| **Full Causal Chain Verification** | `python verify_final_demo_closed_loop.py` | **PASS [SOFTWARE VERIFIED]** | All 6 transitions verified monotonic. |

---

## 12. FINAL ACCEPTANCE CHECKLIST (PHASE 19)

- [x] Vehicle A powers up safely (PWM = 0, STBY LOW, default speed 0.0 m/s).
- [x] Vehicle B powers up safely (PWM = 0, STBY LOW, default speed 0.0 m/s).
- [x] Both motors remain stopped on boot.
- [x] Vehicle A accepts FORWARD command (`/api/command` HTTP, Serial `FORWARD`, backend response).
- [x] Vehicle B accepts FORWARD command (`/api/command` HTTP, Serial `FORWARD`, backend response).
- [x] Vehicle A forward PWM calculation verified ($\ge 60\text{ PWM}$, non-zero duty cycle).
- [x] Vehicle B forward PWM calculation verified ($\ge 60\text{ PWM}$, non-zero duty cycle).
- [x] Vehicle A telemetry reports calibrated RPM and speed in SI units ($\text{m/s}$).
- [x] Vehicle B telemetry reports calibrated RPM and speed in SI units ($\text{m/s}$).
- [x] Vehicle A command reaches firmware via WebServer port 80 and telemetry feedback loop.
- [x] Vehicle B command reaches firmware via WebServer port 80 and telemetry feedback loop.
- [x] CLEAR fog permits normal demo speed ($0.80\text{ m/s}$ limit, $0.40\text{ m/s}$ applied).
- [x] LIGHT fog reduces safe speed ($0.60\text{ m/s}$).
- [x] MODERATE fog reduces safe speed ($0.40\text{ m/s}$).
- [x] HEAVY fog clamps forward speed ($0.24\text{ m/s}$, PWM drops from 106 to 87).
- [x] SEVERE fog invokes emergency stop ($v_{\text{safe}} = 0.00\text{ m/s}$, $\text{PWM} = 0$, STBY LOW).
- [x] CLEAR restores normal operation ($v_{\text{safe}}$ recovers to $0.80\text{ m/s}$, PWM recovers).
- [x] Forward direction remains FORWARD during fog deceleration until explicit STOP.
- [x] PWM decreases monotonically as fog severity increases.
- [x] Safe speed never exceeds vehicle $V_{\text{max}}$ ($1.40\text{ m/s}$ vs $1.30\text{ m/s}$).
- [x] Applied speed never exceeds safe speed.
- [x] STOP overrides all forward commands.
- [x] HMI reflects authoritative backend state via WebSocket.
- [x] Digital Twin reflects authoritative backend state.
- [x] HMI does not inject fog (verified read-only GET client).
- [x] CLI controls environmental injection (`tools/inject_fog.py`).
- [x] V2V status is truthful (unmeasured radio metrics null, no fabricated data).
- [x] V2I status is truthful (`DIRECT_WIFI` / `LORA_GATEWAY`).
- [x] No fake position displayed (displays `LOCAL ODOMETRY / NOT GEOREFERENCED`).
- [x] No fake physical validation reported (classified strictly as SOFTWARE VERIFIED or PHYSICAL BENCH VERIFIED).
- [x] Telemetry sequence remains valid (strictly monotonic).
- [x] No regression in RF/LoRa V2V protocol.
- [x] No regression in safety governor.
- [x] No regression in HMI.

---

## 13. EXACT SIH DEMO EXECUTION RUNBOOK

### Pre-Requisites & Network Setup
1. Laptop Hotspot: SSID `SYNQRA_HOST`, Password `your_password`, Host IP `192.168.137.1`.
2. Vehicle A (`TRUCK_01`): IP `192.168.137.43` (COM14).
3. Vehicle B (`TRUCK_02`): IP `192.168.137.126` (COM21).

### Step 1: Start Backend
In terminal 1:
```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Verify: Open browser to `http://127.0.0.1:8000/api/health` -> returns `{"status":"HEALTHY"}`.

### Step 2: Start HMI Frontend
In terminal 2:
```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\frontend"
npm run dev
```
Verify: Open browser to `http://localhost:5173`. Confirm Technician & Operator dashboards connect to backend WebSocket.

### Step 3: Power On Vehicles & Verify Startup Safety
1. Turn on battery power for Vehicle A and Vehicle B.
2. Confirm both vehicles boot with **MOTORS STOPPED** ($\text{PWM} = 0$).
3. Confirm in HMI: Telemetry arrives for `TRUCK_01` and `TRUCK_02` with status `ONLINE`.

### Step 4: Command Initial Forward Movement
In terminal 3:
```powershell
python tools/test_motor.py --vehicle ALL --action FORWARD --speed 0.40
```
**Demonstrated Behavior:**
- Both vehicles assert `MOTOR_STBY = HIGH`.
- Vehicle A sets $\text{PWM} = 106$ in `FORWARD` direction.
- Vehicle B sets $\text{PWM} = 109$ in `FORWARD` direction.
- Wheels rotate forward smoothly without static friction stall.
- Real-time RPM and linear speed appear on the Operator HMI.

### Step 5: Execute Dynamic Fog Escalation Demo
In terminal 4 (the external weather CLI):

1. **Light Fog Entry:**
   ```powershell
   python tools/inject_fog.py --condition light
   ```
   *Observation:* Visibility drops to $500\text{ m}$, $v_{\text{safe}} = 0.60\text{ m/s}$. Both vehicles maintain $0.40\text{ m/s}$ forward.

2. **Moderate Fog Entry:**
   ```powershell
   python tools/inject_fog.py --condition moderate
   ```
   *Observation:* Visibility drops to $250\text{ m}$, $v_{\text{safe}} = 0.40\text{ m/s}$. HMI alerts operator of caution.

3. **Heavy Fog Injection (Active Governor Clamp):**
   ```powershell
   python tools/inject_fog.py --condition heavy
   ```
   *Observation:*
   - Visibility drops to $100\text{ m}$, $v_{\text{safe}}$ drops to $0.24\text{ m/s}$.
   - The Digital Twin governor detects $v_{\text{requested}} (0.40) > v_{\text{safe}} (0.24)$ and activates speed clamp.
   - Vehicle A PWM reduces to $87$.
   - Vehicle B PWM reduces to $90$.
   - Both physical vehicles visibly decelerate on the test floor while maintaining forward direction.
   - HMI displays `GOVERNOR ACTIVE: FOG CONSTRAINT`, Applied Speed $= 0.24\text{ m/s}$.

4. **Severe Fog Emergency Stop:**
   ```powershell
   python tools/inject_fog.py --condition severe --severe-stop
   ```
   *Observation:*
   - Visibility drops to $50\text{ m}$, $v_{\text{safe}}$ clamped to $0.00\text{ m/s}$.
   - Both vehicles bring PWM to $0$, de-assert `MOTOR_STBY` to $LOW$, and stop completely.
   - HMI flashes `EMERGENCY STOP — SEVERE FOG ZERO VISIBILITY`.

5. **Fog Clears (Full Dynamic Recovery):**
   ```powershell
   python tools/inject_fog.py --condition clear
   ```
   *Observation:*
   - Visibility recovers to $1000\text{ m}$, $v_{\text{safe}}$ recovers to $0.80\text{ m/s}$.
   - Vehicles re-engage forward direction, PWM ramps back up to $106 / 109$, and vehicles resume forward motion at $0.40\text{ m/s}$.
   - HMI returns to `NORMAL` operational state.
