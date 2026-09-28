# PHASE 8 — CAN / TWAI VALIDATION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH26007
### 250 kbps Heavy-Duty Bus Emulation, J1939 PGN Mapping & Invariant Integrity

---

## 1. Provenance & Engineering Boundary

> **MANDATORY DISCLAIMER:**  
> The CAN frame IDs and bit encodings defined herein represent **project-defined HIL frames** formatted to adhere to SAE J1939 standard PGN conventions. Under NO circumstances do these represent reverse-engineered or tapped OEM proprietary wiring from a BEML BH100 haul truck at NMDC Bailadila. Direct OEM ECU integration remains **UNVALIDATED** and is classified as a field-validation gap.

---

## 2. J1939-Compatible Frame Specifications

All frames utilize **29-bit Extended CAN Identifiers** operating at **250 kbps** on a Two-Wire Automotive Interface (TWAI / ISO 11898-1).

| Signal Name | CAN ID (Hex) | SAE PGN | Source | Target | Update Period | Timeout | Scaling & Resolution | Range / Units |
|---|---|---|---|---|---|---|---|---|
| **ENGINE_SPEED** | `0x0CF00400` | 61444 (EEC1) | Powertrain ECU | Safety ECU | 20 ms | 100 ms | 0.125 RPM/bit, offset 0 | 0.0 – 8031.875 RPM |
| **VEHICLE_SPEED** | `0x18FEF100` | 65265 (CCVS) | Transmission ECU | Safety ECU | 50 ms | 150 ms | 1/256 km/h per bit | 0.0 – 250.0 km/h (m/s converted) |
| **BRAKE_STATUS** | `0x18F0010B` | 61441 (EBC1) | Brake Actuator | Safety ECU | 50 ms | 200 ms | Pedal: 0.4%/bit; Press: 1 kPa/bit | 0 – 100% / 0 – 2000 kPa |
| **RETARDER_STAT**| `0x18F0000F` | 61440 (ERC1) | Retarder Controller | Safety ECU | 50 ms | 200 ms | Torque: 0.4%/bit | 0 – 100% torque capacity |
| **SAFETY_COMMAND**| `0x0CFF0101`| 65281 (PropB) | Safety ECU (ESP32) | Chassis ECU | 50 ms | 150 ms | Speed: 0.01 m/s/bit; Act: 1 byte | 0 – 655.35 m/s, Action Enum |
| **VEHICLE_STATE** | `0x18FF0201` | 65282 (PropB) | Vehicle IMU/ECU | Safety ECU | 100 ms | 300 ms | Grade: 1 %/bit (int8); Payload: 1 t | -128% to +127% / 0 – 250 t |

---

## 3. Payload Bit Layout & Protocol Decoding

### 3.1 PGN 61444 (EEC1) — Engine Speed
- **Byte 0–2:** Miscellaneous engine status indicators (`0xFF` padding).
- **Bytes 3–4:** Engine speed in RPM:
  $$\text{RPM} = \left(\text{Byte}_3 \mid (\text{Byte}_4 \ll 8)\right) \times 0.125$$
- **Defensive Clamp:** Any raw value $\ge \text{0xFAFF}$ indicates sensor fault or unmeasured condition $\implies$ local governor sets $v_{\text{safe}} = 0.0\text{ m/s}$.

### 3.2 PGN 65265 (CCVS) — Wheel-Based Vehicle Speed
- **Byte 0:** Cruise control state (`0xFF`).
- **Bytes 1–2:** Wheel-based vehicle speed:
  $$v_{\text{km/h}} = \frac{\text{Byte}_1 \mid (\text{Byte}_2 \ll 8)}{256.0}, \quad v_{\text{m/s}} = \frac{v_{\text{km/h}}}{3.6}$$
- **Defensive Clamp:** Out-of-bounds check ($v > 60\text{ m/s}$ or negative) triggers fail-safe stop.

### 3.3 PGN 65281 (Proprietary B) — Authoritative Safety Command
- **Bytes 0–1:** Commanded speed ceiling $v_{\text{command}}$:
  $$v_{\text{command}} = \frac{\text{Byte}_0 \mid (\text{Byte}_1 \ll 8)}{100.0}\quad (\text{m/s})$$
- **Byte 2:** Command Action Code ($0 = \text{ACCEPT}, 1 = \text{CLAMP}, 2 = \text{REJECT}$).
- **Bytes 3–4:** Monotonic 16-bit sequence number for replay defense.

---

## 4. Bus Emulation Timing & Failure Injection Results

Empirical verification from [`tests/test_phase8_hil.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/test_phase8_hil.py):

| Test Condition | Injected Fault | Expected Result | Measured Result | Status |
|---|---|---|---|---|
| **Wire Transmission Time** | DLC = 8 bytes @ 250 kbps | $T_{\text{wire}} = 0.512\text{ ms}$ | $0.512\text{ ms}$ lower bound | **PASS** |
| **Arbitration Latency** | High-priority vs low-priority PGNs | Higher priority (`0x0C...`) wins arbitration | Mean $5.79\text{ ms}$, P95 $19.17\text{ ms}$ | **PASS** |
| **Stochastic Packet Loss** | 20% random packet drop | Safety ECU maintains last valid ceiling | $v_{\text{applied}} \le v_{\text{safe}}$ preserved | **PASS** |
| **Burst Packet Loss** | 5 consecutive frames dropped | Governor maintains safe speed | Zero runaway observed | **PASS** |
| **Speed Frame Timeout** | 300 ms silence ($> 150\text{ ms}$ timeout) | Detects stale frame $\implies v_{\text{safe}} = 0.0$ | $v_{\text{applied}} \to 0.0\text{ m/s}$ | **PASS** |
| **Bit Corruption** | Byte 0 inverted (`XOR 0xFF`) | Payload rejected by parser | Defensively handled | **PASS** |
| **Bus-Off Transition** | Forced TEC $> 255$ / bus-off | Bus transmission rejected | Bus state = `BUS_OFF` | **PASS** |

---

## 5. Conclusion & Invariant Confirmation

The CAN/TWAI layer successfully isolates physical communication transport from the safety core. Under no circumstance did corrupted CAN payloads, lost frames, or timeouts allow the vehicle speed to exceed $v_{\text{safe}}$.
