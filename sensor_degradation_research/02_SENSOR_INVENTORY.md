# 02 — SENSOR INVENTORY
## FOG-ORCHESTRATOR 2.0 — Sensor / Data Source Inventory
**Scope:** What data is actually available, at what rate, from what source, with what confidence.  
**Date:** 2026-09-21  
**Classification Rule:** Never merge separate evidence categories.

---

## Category 1 — PROTOTYPE SENSORS (OUR HARDWARE — MEASURED)

These are sensors physically present on the SIH26007 ESP32 prototype vehicles.

| Sensor | Vehicle | Interface | Measurement | Update Rate | Notes |
|---|---|---|---|---|---|
| LM393 Slot Encoder | TRUCK_01 | GPIO ISR | Wheel RPM, derived speed_mps | ~5–20 Hz (motion-dependent) | MEASURED. Encoder-derived. Evidence: VEHICLE_A_HMI_FIRMWARE.ino:128-129 |
| MPU6050 IMU | TRUCK_01, TRUCK_02 | I2C | ax, ay, az (m/s²), gx, gy, gz (rad/s) | ~10–50 Hz (configurable) | MEASURED. Raw LSB converted by existing parsers. |
| LoRa SX1276 RF RSSI/SNR | TRUCK_01, TRUCK_02, Gateway | SPI | Link quality metric | Per-packet | MEASURED. Used for communication health. |

### TRUCK_02 Special Case

| Parameter | Source | Classification |
|---|---|---|
| speed_mps (V2V SPEED field) | PWM-derived (appliedSpeedMs = PWM/MAX_PWM * MAX_PROTO_SPEED) | SYNTHETIC / NOT ENCODER-MEASURED. Firmware comment explicitly states this. |

### NOT ON THIS PROTOTYPE

| Parameter | Classification |
|---|---|
| position_lat, position_lon | NOT MEASURED. No GNSS receiver fitted. GNSS_EQUIPPED_VEHICLES = frozenset() |
| visibility_m | NOT MEASURED. No visibility sensor on ESP32 prototype. |
| friction_mu | NOT MEASURED. Model prior only (mu = 0.35 engineering assumption). |
| road_id, heading_rad | NOT MEASURED. Never populated from hardware. |

---

## Category 2 — BEML BH100 DOCUMENTED SENSOR/ECU INTERFACES

Source: BEML BH100 Parts Catalogue references, J1939 documentation.  
Evidence Level: L1 (partial) — OEM documentation; specific PGN/SPN lists require serial-number-specific manual.

| System | Interface | Data Available | Evidence Level |
|---|---|---|---|
| Cummins QSK60 Engine ECU | J1939 CAN 250 kbps, 29-bit ext. frame | Engine RPM, Engine Load, Coolant Temp, Fuel Rate | L1 partial — J1939 PGN EEC1 (0x0CF00400) confirmed generically |
| Allison H8610A Transmission | J1939 CAN via CEC2 | Gear, Output RPM, Transmission Temp | L1 partial — Allison CEC2 J1939 compliance documented |
| Service Brake System | Electro-pneumatic, J1939 EBC1 (PGN 61441) | Brake pedal %, line pressure (kPa) | L1 generic — specific BH100 brake ECU PGN mapping NOT VERIFIED |
| Retarder System | J1939 ERC1 (PGN 61440) | Retarder torque % | L1 generic — specific BH100 retarder ECU NOT VERIFIED |
| Wheel Speed | Wheel-mounted speed sensor or ABS ECU, J1939 CCVS (PGN 65265) | Wheel speed km/h | L1 generic — BH100 specific SPN NOT VERIFIED |
| Payload Monitor | Proprietary system (often Loadrite or equivalent strut pressure) | Payload kg | L2 — general HEMM practice; BH100 specific system UNKNOWN |
| GNSS | Optional fitment — not standard on all BH100 variants | Position, heading | UNKNOWN / NOT VERIFIED. Depends on FMS integration package. |

**CRITICAL NOTE:** The BH100 is a human-operated dumper. It is NOT equipped with autonomous perception
sensors (LiDAR, radar, front camera for visibility detection). Visibility sensing is an infrastructure
function, not a vehicle-local function for this vehicle class.

---

## Category 3 — NMDC / FMS DOCUMENTED DATA

Source: NMDC public documentation, ICCC reports, SIH PS SIH26007 background material.  
Evidence Level: L2.

| Data Type | Source | Coverage | Update Rate | Notes |
|---|---|---|---|---|
| Weather station data | NMDC meteorological stations (mine-site, not national) | Mine-site level — single point or few points | 1–10 min typical | Documented: NMDC Bailadila complex uses on-site stations |
| Fog / visibility alerts | Manual reporting + weather station | Mine-wide (not zone-specific) | As-reported | Not a continuous sensor stream in documented form |
| HEMM tracking (FMS) | NMDC FMS GPS tracking modules | Vehicle position on haul road | 30–60 s typical (FMS standard) | Under implementation at Bailadila (ICCC project) |
| Road condition / grade | Survey data / engineering maps | Per-segment static | Updated periodically | Not a real-time sensor stream |
| Haul road visibility (zone-level) | NOT DOCUMENTED | NOT AVAILABLE | N/A | SIGNIFICANT GAP |

---

## Category 4 — RESEARCH LITERATURE SENSOR CONFIGURATIONS

Source: Mining safety literature, autonomous HEMM research papers (L5).  
These are NOT present on NMDC BH100 vehicles unless separately documented.

| Sensor | Common Use | Notes |
|---|---|---|
| Forward scatter visibility meter | Surface mine weather stations | Measures optical extinction path (~10 m sampling volume). Does NOT represent entire haul road. |
| Thermal camera | Vision-enhancement prototypes | NMDC research: demonstrated 30–40 m effective range in fog. Prototype only. |
| Proximity radar | Collision avoidance systems | Caterpillar, Komatsu AHS trucks. NOT BH100 standard. |
| LiDAR | Autonomous haulage (Komatsu FrontRunner, Caterpillar CAT Command) | NOT present on BH100 (human-operated) |
| IMU (vehicle-grade) | VIMS, Caterpillar onboard monitoring | BH100 equivalent UNKNOWN / NOT VERIFIED |

---

## Category 5 — ENGINEERING ASSUMPTIONS (USED IN THIS PROTOTYPE)

| Parameter | Value | Classification | Justification |
|---|---|---|---|
| mu (friction) | 0.35 | ENGINEERING ASSUMPTION | Conservative low-friction compacted haul road; not measured on BH100 |
| visibility_m | Scenario-set (12 m, 8 m, etc.) | SIMULATION INPUT | No physical sensor; set by benchmark scenarios |
| r_effective | = visibility_m (direct substitution) | MODEL SIMPLIFICATION | Assumes perception range equals meteorological visibility; conservative |
| grade | ±8% | ENGINEERING REFERENCE | Bailadila Deposit-5 topographic data; modeled only |

---

## Summary: Availability vs. Accessibility

| Data Type | Available in Principle | Accessible by Prototype Architecture | Evidence Level |
|---|---|---|---|
| Vehicle speed (encoder) | YES — TRUCK_01 | YES | MEASURED |
| IMU data | YES — both trucks | YES | MEASURED |
| Engine RPM | YES — J1939 (BH100) | NOT CONNECTED (HIL only) | L1 partial |
| Brake status | YES — J1939 (BH100) | NOT CONNECTED (HIL only) | L1 generic |
| Visibility (mine-site) | PARTIAL — weather station | NO — not on prototype | L2 |
| Visibility (zone-level) | NO — not documented | NO | NOT VERIFIED |
| Road grade (real-time) | NO | NO | NOT VERIFIED |
| Payload (real-time) | POSSIBLE via FMS | NO | L2 generic |
