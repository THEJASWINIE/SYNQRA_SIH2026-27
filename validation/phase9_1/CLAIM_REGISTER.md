# RED-TEAM CLAIM REGISTER: FOG-ORCHESTRATOR 2.0
**Phase 9.1 — Full Integration Hostile Validation & Claim Breaking**  
**SIH 2026-27 | Problem Statement: SIH26007**  
**Document ID:** `validation/phase9_1/CLAIM_REGISTER.md`  
**Status:** HOSTILE AUDIT LOCKED  

---

## 1. Evidence Level Classification Key (Section 0)

Every claim in the register is classified into exactly one of the seven standardized evidence tiers:
- **A:** Physically measured on live mining vehicle or production quarry equipment.
- **B:** Hardware-in-the-loop (HIL) or laboratory electronics bench measured (e.g. ESP32 testbed).
- **C:** Simulation validated (kinematic, Monte Carlo, multi-agent closed-loop).
- **D:** Software unit / integration test validated (Pytest, Vitest).
- **E:** Literature-derived from peer-reviewed publications, OEM brochures, or ISO standards.
- **F:** Engineering assumption / design rule of thumb.
- **G:** Proposed / future validation experiment (unvalidated).

---

## 2. Master System Claim Register

| Claim ID | Exact Technical Claim | Subsystem | Evidence Level | Source Document | Test Reference | Numerical Result Claimed | Required Evidence for Level A | Known Critical Limitation | Audit Status |
|:---|:---|:---|:---:|:---|:---|:---|:---|:---|:---:|
| **CLM-01** | "Total sensor-to-actuator reaction latency is $484.2\text{ ms}$ (P99), within DGMS $800\text{ ms}$ limit." | Controls / Timers | **Mixed (B + F)** | `13_END_TO_END_LATENCY_REPORT.md` | `test_hil_17_actuator_delay` | $484.2\text{ ms}$ P99 | Pressure transducer on BEML BH100 brake lines | Actuator component ($250\text{ ms}$) is an ASSUMPTION (F). In cascade failure, total reaches $935\text{ ms}$. | **PARTIALLY_SUPPORTED** |
| **CLM-02** | "BEML BH100 hydraulic brake pressure build-up lag is $250.0\text{ ms}$ nominal / $350.0\text{ ms}$ worst-case." | Chassis Braking | **E / F** | `config/integration_canonical.yaml` | `test_hil_17` | $250.0\text{ ms}$ | High-speed hydraulic line telemetry | UNMEASURED on physical haul truck chassis. Modeled from ISO 3450 standard. | **PARTIALLY_SUPPORTED** |
| **CLM-03** | "Vehicle maintains a $5.0\text{ m}$ standstill safety buffer ($S_{\text{stop}} + 5.0\text{ m} \le R_{\text{vis}}$) on $-8\%$ grade in $8.0\text{ m}$ fog." | Safety Governor | **C / D** | `config/integration_canonical.yaml` | `test_hil_02_dense_fog` | $v_{\text{safe}} = 3.52\text{ m/s}$ | Stopping distance trial on live Bailadila ramp | On $-8\%$ downhill grade, $3.52\text{ m/s}$ requires $3.885\text{ m}$ stopping distance. Residual margin is $4.115\text{ m}$, partially eroding the $5.0\text{ m}$ buffer! | **CONTRADICTED** |
| **CLM-04** | "CAN / TWAI 250 kbps bus latency is bounded by $50.0\text{ ms}$ P99 with 0 dropped frames." | Vehicle CAN Bus | **B** | `07_CAN_TIMING_REPORT.md` | `test_hil_12_can_latency` | $\mu = 6.302\text{ ms}$, $P_{99} = 50.0\text{ ms}$ | Vector CANoe tap on live BH100 J1939 harness | Measured on ESP32 SN65HVD230 bench rig under 75% load. At $>95\%$ bus load, queue delay causes frame drops ($12.5\%$). | **SUPPORTED (under $\le 75\%$ load)** |
| **CLM-05** | "CAN timeout of $150\text{ ms}$ reliably triggers autonomous failsafe brake deceleration." | Safety Watchdog | **B / D** | `07_CAN_TIMING_REPORT.md` | `test_hil_16_can_timeout` | Timeout at $150\text{ ms}$ | Instrumented brake ECU line test on vehicle | Verified on TWAI emulator. True vehicle ECU reaction depends on unverified OEM hydraulic valve response. | **SUPPORTED** |
| **CLM-06** | "Direct-Sequence Spread Spectrum (DSSS) PN gateway selection provides seamless cell handover." | RF Communications| **C / D** | `06_GATEWAY_INTEGRATION_REPORT.md` | `test_hil_12_gateway_handover` | Handover in $300\text{ ms}$ | SDR baseband despreading trial in open pit | Physical hardware is Semtech SX1278 Chirp Spread Spectrum (CSS). DSSS is a software simulation model. | **PARTIALLY_SUPPORTED** |
| **CLM-07** | "Safe Beacon autonomously activates within $550\text{ ms}$ upon communication timeout." | Failsafe / RF | **B / D** | `08_SAFE_BEACON_VALIDATION.md` | `test_hil_14_safe_beacon` | Activation in $550.0\text{ ms}$ | Dual-radio bench trial under RF fading | Activates locally on vehicle. But single SX1278 transceiver creates half-duplex blocking (cannot listen while transmitting). | **SUPPORTED (locally)** |
| **CLM-08** | "Safe Beacon alerts Control Room when primary communication link is severed." | Failsafe / Comms | **D** | `08_SAFE_BEACON_VALIDATION.md` | `test_invariant_i4` | Alerts Control Room | Multi-hop V2V mesh testbed | CIRCULAR DEPENDENCY: A dead gateway cannot forward the vehicle's beacon to the Control Room. Control Room only knows via timeout! | **CONTRADICTED** |
| **CLM-09** | "Sensor health engine detects $100\%$ of sensor degradation and failure modes." | Sensor Intelligence | **D** | `05_SENSOR_HEALTH_INTEGRATION_REPORT.md` | `test_hil_06, 07, 08` | 8-State classification | Multi-sensor monsoon field trials | FUNDAMENTAL LIMITATION: Single-channel systematic additive calibration bias within $[0.5, 2000]\text{ m}$ is mathematically unobservable. | **PARTIALLY_SUPPORTED** |
| **CLM-010**| "Digital Twin synchronization latency is $48.2\text{ ms}$ with Position RMSE of $0.342\text{ m}$." | Digital Twin | **C / D** | `12_DIGITAL_TWIN_SYNC_REPORT.md` | `test_hil_18, test_hil_19` | $\text{RMSE} = 0.342\text{ m}$ | High-precision RTK GNSS truth tracking on dumper | Validated against simulated vehicle odometry. Physical wheel slip in deep mud will cause larger dead-reckoning drift. | **SUPPORTED (in simulation)** |
| **CLM-011**| "Digital Twin failure leaves physical vehicle operating safely under Local Safety Governor." | Safety Authority | **B / D** | `11_DIGITAL_TWIN_VALIDATION.md` | `test_hil_27_twin_restart` | Local Gov holds $v_{\text{safe}}$ | Physical disconnect of Twin server | Verified in HIL. Local governor code is completely decoupled from Twin network socket. | **SUPPORTED** |
| **CLM-012**| "Control Room dispatch cannot override the onboard Local Vehicle Safety Governor." | Safety Invariant | **B / D** | `10_CONTROL_ROOM_HMI_VALIDATION.md` | `test_invariant_i7` | $v_{\text{applied}} = \min(v_{\text{cmd}}, v_{\text{safe}})$ | Hardware injection of oversized dispatch speed | Enforced in firmware/software governor math. Hardware override impossible through network path. | **SUPPORTED** |
| **CLM-013**| "Operator HMI renders speed and fog warnings within $100\text{ ms}$ without displaying stale state." | Operator Cab HMI | **D** | `09_OPERATOR_HMI_VALIDATION.md` | `test_hil_20_hmi_stale` | Update in $42.5\text{ ms}$; stale at $1.0\text{ s}$| In-cab vibration & optical render measurement | Vitest UI suite verified. Stale data explicitly watermarked `STALE: x.x s`. | **SUPPORTED** |
| **CLM-014**| "System increases dense fog ore haulage throughput by $43.4\%$ at NMDC Bailadila Deposit-5." | Mine Logistics | **C** | `17_FINAL_SYSTEM_BENCHMARK.md` | `fog_orchestrator/simulation` | Throughput $448.2\text{ t/h}$ vs $312.5\text{ t/h}$ | Multi-shift production weighbridge records | SIMULATION ONLY. Bailadila haul cycle dispatch and staging wait times are derived from Monte Carlo simulator. | **PARTIALLY_SUPPORTED** |
| **CLM-015**| "Full system recovery occurs deterministically after comm restoration via 2 sync frames." | Network Recovery | **B / D** | `20_PHASE9_CLOSURE_REPORT.md` | `test_hil_24_vehicle_restart` | 2 frames ($200\text{ ms}$) resync | Live vehicle reboot on haul ramp | Verified in HIL state machine. Intentionally introduces $200\text{ ms}$ delay to prevent flapping. | **SUPPORTED** |
