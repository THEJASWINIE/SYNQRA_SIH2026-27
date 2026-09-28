# FOG-ORCHESTRATOR 2.0 — Physical Validation Baseline Freeze

**Project:** SIH 2026–27 — Autonomous Fog/Low-Visibility Fleet Orchestrator  
**Document ID:** `DOC-PVB-2026-01`  
**Classification:** Authoritative Technical Specification & Baseline Freeze  
**Author:** Principal Software Architect & Lead Hardware Integration Engineer  
**Baseline Commit Hash:** `4a3aa47` (`ControlHM_Iwith_updated_mine_cast_map`)  
**Freeze Status:** **FROZEN — NO FEATURE MODIFICATIONS PERMITTED DURING TESTING**

---

## 1. Executive Summary & Freeze Policy

This document formally establishes and freezes the authoritative software, firmware, hardware, and configuration baseline for the **FOG-ORCHESTRATOR 2.0** physical validation campaign. 

Per Non-Negotiable Rule 1 and Rule 28 of the project charter:
1. **Zero Feature Creep:** No new features, speculative abstractions, or cosmetic modifications are permitted during the validation execution.
2. **Experiment Branching:** Any code change required to rectify a hardware fault must be recorded as a discrete sub-version with full regression test verification before re-entering physical testing.
3. **Evidence Boundary Enforcement:** Laboratory prototype measurements shall under no circumstances be conflated with OEM Heavy Earth Moving Machinery (HEMM) physical validation or NMDC Bailadila Iron Ore Mine Deposit 5 field validation.

---

## 2. Baseline Version Manifest

| Component | Repository Path / Module | Frozen Version | Hash / Checksum | Verification Status |
|:---|:---|:---|:---|:---|
| **Git Repository** | Root workspace | Commit `4a3aa47` | `4a3aa47` | Clean working tree verified |
| **Vehicle A Firmware** | `esp32_code/VEHICLE_SPEED_CALIBRATION/src/main_vehicle_a.cpp` | `v2.1.0-canonical` | `SHA256:7f49c0...` | Reconciled & compiled |
| **Vehicle B Firmware** | `esp32_code/VEHICLE_SPEED_CALIBRATION/src/main_vehicle_b.cpp` | `v2.1.0-canonical` | `SHA256:3a1b8d...` | Reconciled & compiled |
| **Backend Core** | `core/orchestrator.py`, `core/safety_governor.py` | `v2.1.0-canonical` | Invariant pass | Pytest suite: 1,189 passed |
| **Safety Governor** | `core/safety_governor.py` | `v2.1.0-canonical` | Tier-1 isolated | Clamping & timeout validated |
| **Sensor Health** | `core/sensor_health.py` | `v2.1.0-canonical` | State machine frozen | 5 degradation modes tested |
| **Safe Beacon** | `core/safe_beacon.py`, `integration_adapters/safe_beacon_adapter.py` | `v2.1.0-canonical` | 5-packet recovery frozen | Non-actuating confirmed |
| **RF / Gateway** | `integration_adapters/dsss_gateway_selector.py` | `v2.1.0-canonical` | Hysteresis 3 dB frozen | 38.5 ms airtime baseline |
| **Operator HMI** | `hmi/operator_hmi.py`, `web/operator_dashboard.html` | `v2.1.0-canonical` | Consumer-only frozen | No state invention |
| **Control Room HMI**| `hmi/technician_hmi.py`, `web/control_room.html` | `v2.1.0-canonical` | Read-only twin link | Live/Stale/Off indicators |
| **Digital Twin** | `digital_twin/twin_state.py`, `integration_adapters/digital_twin_sync.py` | `v2.1.0-canonical` | Authoritative twin | Replay isolated from actuation |
| **Test Suite** | `tests/` (110+ test files) | `v2.1.0-hostile-audited`| 1,189 PASS / 1 SKIP | 100% regression clean |

---

## 3. Physical Hardware Baseline Specifications

### 3.1 Kinematics & Wheel Dimensions (Both Vehicles)
* **Wheel Outer Diameter ($D$):** $0.060\text{ m}$ ($60.0\text{ mm}$)
* **Wheel Radius ($R$):** $0.030\text{ m}$ ($30.0\text{ mm}$)
* **Wheel Circumference ($C$):** $\pi \times 0.060 = 0.188495559\text{ m}$ ($188.50\text{ mm}$)
* **Effective Calibration Factor ($K_{\text{enc}}$):** $34.58\text{ pulses/revolution}$
  * *Physical Rationale:* Maps raw slotted-disk encoder pulses, dynamic rubber tire deflection under load, optical jitter hysteresis, and rolling slip directly to true linear displacement.
* **Effective Distance Per Pulse ($d_{\text{pulse}}$):**
  $$d_{\text{pulse}} = \frac{C}{K_{\text{enc}}} = \frac{0.188495559\text{ m}}{34.58\text{ pulses}} = 0.00545100\text{ m/pulse} \quad (5.451\text{ mm/pulse})$$

### 3.2 Vehicle A: Discrete Driver Platform
* **Chassis ID:** `TRUCK_01`
* **Controller MCU:** Espressif ESP32-WROOM-32 (240 MHz Dual Core, 520 KB SRAM)
* **Motor Driver:** STMicroelectronics L298N Dual Full-Bridge Driver (BJT H-Bridge)
  * *Forward Voltage Drop ($V_{\text{drop}}$):* $\sim 1.8\text{ V} - 2.2\text{ V}$ (integrated Darlington output)
  * *Pin Mapping:*
    * `ENA` (PWM Channel A): GPIO 27 (LEDC 5 kHz, 8-bit resolution)
    * `IN1`: GPIO 25
    * `IN2`: GPIO 26
    * `ENB` (PWM Channel B): GPIO 14 (LEDC 5 kHz, 8-bit resolution)
    * `IN3`: GPIO 32
    * `IN4`: GPIO 33
    * `STBY` / Logic Enable: GPIO 13 (Pulled high; pulled low on safety shutdown)
* **Encoder:** Single-channel optical slotted interrupter with 42 physical slots
  * *Raw Wheel Pulses Per Revolution:* $42\text{ PPR}$
  * *Interrupt Pin:* GPIO 18 (Falling edge triggered, debounced via 15 µs hardware RC)
* **Battery Power:** 2S Li-Ion 18650 Pack (7.4 V nominal, 8.4 V peak, 2600 mAh)
* **Telemetry Role:** Lead haulage vehicle (`TRUCK_01`)

### 3.3 Vehicle B: MOSFET Driver Platform
* **Chassis ID:** `TRUCK_02`
* **Controller MCU:** Espressif ESP32-WROOM-32 (240 MHz Dual Core, 520 KB SRAM)
* **Motor Driver:** Toshiba TB6612FNG Dual Dual-Channel H-Bridge (Low-$R_{\text{DS(on)}}$ DMOS)
  * *Forward Resistance ($R_{\text{DS(on)}}$):* $0.5\ \Omega$ typical (significantly higher electrical efficiency than L298N)
  * *Pin Mapping:*
    * `PWMA`: GPIO 27 (LEDC 5 kHz, 8-bit resolution)
    * `AIN1`: GPIO 25
    * `AIN2`: GPIO 26
    * `PWMB`: GPIO 14 (LEDC 5 kHz, 8-bit resolution)
    * `BIN1`: GPIO 32
    * `BIN2`: GPIO 33
    * `STBY`: GPIO 13 (Hardware gate disable; motor outputs float when LOW)
* **Encoder:** Single-channel optical slotted interrupter with 43 physical slots
  * *Raw Wheel Pulses Per Revolution:* $43\text{ PPR}$
  * *Interrupt Pin:* GPIO 19 (Falling edge triggered, debounced via 15 µs hardware RC)
* **Battery Power:** 2S Li-Ion 18650 Pack (7.4 V nominal, 8.4 V peak, 2600 mAh)
* **Telemetry Role:** Following haulage vehicle (`TRUCK_02`)

---

## 4. Communication & Latency Baseline

### 4.1 RF Physical Layer (SX1278 / SX1262 LoRa/FSK)
* **Frequency:** 868.0 MHz / 433.0 MHz ISM Band
* **Modulation:** Chirp Spread Spectrum (CSS) / Direct Sequence Spread Spectrum (DSSS) emulation
* **Bandwidth (BW):** 125 kHz
* **Spreading Factor (SF):** SF7
* **Coding Rate (CR):** 4/5
* **Preamble Length:** 8 symbols
* **Payload Size:** 32 bytes fixed binary telemetry packet
* **Measured Single-Packet Airtime:** $38.5\text{ ms}$ ($\pm 0.4\text{ ms}$)
  * *Definitive Boundary:* $38.5\text{ ms}$ represents **`RF_AIRTIME_COMPONENT` ONLY**. It is not the total end-to-end latency.

### 4.2 Local Safety Beacon Broadcast
* **Protocol:** UDP Multicast / ESP-NOW heartbeat packet (16 bytes)
* **Broadcast Frequency:** 10 Hz ($100\text{ ms}$ period)
* **Local Safety Timeout:** $300\text{ ms}$ (3 missed frames trigger autonomous crawl mode)
* **Emergency Halt Threshold:** $500\text{ ms}$ (5 missed frames trigger full motor shutdown)
* **Recovery Rule:** 5 consecutive valid packets required before clearing safe-beacon state.

---

## 5. Frozen Software Parameters & Invariants

```json
{
  "baseline_version": "v2.1.0-canonical",
  "git_commit": "4a3aa47",
  "kinematics": {
    "wheel_diameter_m": 0.060,
    "wheel_radius_m": 0.030,
    "wheel_circumference_m": 0.188495559,
    "effective_encoder_ppr": 34.58,
    "distance_per_pulse_m": 0.00545100
  },
  "chassis": {
    "TRUCK_01": {
      "driver_ic": "L298N",
      "raw_encoder_ppr": 42,
      "max_speed_mps": 1.50,
      "creep_speed_mps": 0.20
    },
    "TRUCK_02": {
      "driver_ic": "TB6612FNG",
      "raw_encoder_ppr": 43,
      "max_speed_mps": 1.50,
      "creep_speed_mps": 0.20
    }
  },
  "timing": {
    "rf_airtime_ms": 38.5,
    "dgms_safety_reaction_limit_ms": 800.0,
    "telemetry_tick_ms": 50.0,
    "gateway_hysteresis_db": 3.0,
    "recovery_packet_count": 5
  },
  "target_deployment_hemm": {
    "machine_type": "BEML BH100 Mining Dump Truck",
    "gross_vehicle_weight_kg": 165000,
    "payload_capacity_kg": 100000,
    "retarder_max_power_kw": 1200,
    "max_mine_speed_mps": 11.11,
    "hydraulic_brake_delay_status": "NOT_MEASURED"
  }
}
```

---

## 6. Pre-Run Laboratory Checklist

Before initiating any run in Section 3 to Section 11:
1. **Power Check:** Verify Li-Ion battery pack voltage $\ge 7.8\text{ V}$ using calibrated DMM. Do not run below $7.2\text{ V}$ (prevents L298N saturation shifts).
2. **Tire Inspection:** Clean rubber tires with isopropyl alcohol; inspect for flat spots or particulate adherence.
3. **Sensor Alignment:** Verify optical encoder interrupter disc does not touch photo-transistor housing during 360° free wheel rotation.
4. **Firmware Integrity:** Confirm git branch `master` or baseline tag, verify flashed binary matches `main_vehicle_a.cpp` and `main_vehicle_b.cpp`.
5. **Safety Isolation:** Confirm physical emergency toggle switch interrupts main battery $V_{\text{cc}}$ to motor driver board directly.
