# EVIDENCE BOUNDARY & TRUTHFULNESS CHARTER
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phases H1–H10**  
**Lead Safety-Critical Systems & CPS Integration Engineer**  
**Document Revision:** 1.0  
**Date:** 2026-09-24  

---

## 1. Non-Negotiable Evidence Hierarchy (Section 19 Standard)

Every performance figure, latency benchmark, safety margin, and capability claim in FOG-ORCHESTRATOR 2.0 is classified under an immutable 6-tier evidence hierarchy:

| Level | Evidence Category | Definition | Allowed Claim Scope |
| :---: | :--- | :--- | :--- |
| **L0** | **UNTESTED** | Conceptual proposal with no executable tests or prototypes. | Must be stated as *"Proposed concept"*. |
| **L1** | **STATIC / CODE VERIFIED** | Static analysis, type checking, architectural boundary reviews, and code inspection. | May claim syntax and structural integrity. |
| **L2** | **SOFTWARE SIMULATION** | Numerical simulation, kinematic solvers, synthetic packet generators, and software unit tests. | May claim algorithm validity in simulated environments. |
| **L3** | **HIL / BENCH** | Real microcontrollers (ESP32), physical RF transceivers (SX1278), logic analyzers, and hardware CAN/TWAI transceivers on a laboratory bench. | May claim hardware-in-the-loop and benchtop embedded performance. |
| **L4** | **CONTROLLED VEHICLE** | Small-scale physical wheeled robotic prototypes (Vehicle A / Vehicle B) running in a controlled lab or indoor environment. | May claim small-scale physical robotic validation. |
| **L5** | **ACTUAL MINE FIELD** | Real 100-tonne haul trucks (Caterpillar 777D, BEML BH85/BH100) operating inside an active open-cast mine (NMDC Bailadila Deposit 5). | May claim full industrial mining operational validation. |

---

## 2. Subsystem-by-Subsystem Evidence Classification

| Subsystem | Specific Metric / Assertion | Evidence Level | Verification Source / Test Script | Permitted Claim Wording |
| :--- | :--- | :---: | :--- | :--- |
| **Microcontroller Scheduling** | ESP32 FreeRTOS loop latency: $2.5\text{ ms}$ | **L3** | Hardware DWT cycle counter trace | *"Measured on physical ESP32 benchtop hardware."* |
| **LoRa RF Airtime** | 433 MHz SX1278 airtime: $38.5\text{ ms}$ (SF7/BW125) | **L3** | Saleae logic analyzer on DIO0 pin | *"Physically measured on Semtech SX1278 transceiver."* |
| **Motor Drive & Encoders** | Vehicle B TB6612FNG PWM & 43 PPR odometry | **L4** | Physical Vehicle B benchtop run | *"Validated on physical small-scale prototype Vehicle B."* |
| **CAN / TWAI Framing** | J1939 29-bit framing & preemption @ 250 kbps | **L3** | ESP32 TWAI controller with VP230 | *"Validated on physical TWAI CAN bench at 250 kbps."* |
| **OEM Haul Truck CAN** | J1939 interface on physical BEML / CAT chassis | **L0** | None (Lab bench only) | *"PROHIBITED: Cannot claim OEM HEMM J1939 validation."* |
| **Hydraulic Caliper Lag** | Brake pressure buildup time: $250.0\text{ ms}$ | **L2** | Caterpillar 777D literature baseline | *"Modeled in simulation based on OEM technical literature."* |
| **Local Safety Governor** | Invariant $v_{\text{applied}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$ | **L3** | ESP32-S3 HIL execution | *"Validated in embedded HIL loop."* |
| **DSSS PN Gateway Model** | PN sequence correlation & multipath rejection | **L2** | `tests/test_dsss_gateway_selection.py` | *"Algorithm mathematically validated in software simulation."* |
| **Physical RF Coexistence** | Dual-channel isolation for Safe Beacon | **L0** | Single SX1278 prototype only | *"OPEN SAFETY DEPENDENCY: Dual radio required in production."* |
| **Single-Channel Sensor Bias** | Detectability of positive additive visibility bias | **L2** | `test_environmental_data_health.py` | *"Exposed as mathematically unobservable on single channel."* |
| **Bailadila Mine Validation** | Operational deployment at Deposit 5 pit | **L0** | Geodata imported into twin | *"PROHIBITED: Physical mine field deployment is pending."* |

---

## 3. Strict Truthfulness Rules (Section 20 Compliance)

1. **Rule of No Manufactured Field Data:**  
   Under no circumstances shall simulation logs, HIL traces, or indoor vehicle runs be labeled as *"Tested at Bailadila"* or *"Field Validated"*.
2. **Rule of Architectural Demarcation:**  
   Physical LoRa Chirp Spread Spectrum (CSS) hardware must never be described as *"Hardware DSSS ASIC"*.
3. **Rule of No Unmeasured Actuation Claims:**  
   The $250\text{ ms}$ hydraulic caliper delay must never be labeled as *"Measured vehicle braking response"*. It must always carry the label `ENGINEERING_ASSUMPTION (L2/L3)`.
4. **Rule of Failed Invariant Transparency:**  
   If an invariant fails under stress (such as the downhill buffer erosion on $-8\%$ slope), the failure must be formally documented as a failure before issuing a parameter revision.
