# 12 — HARDWARE EVIDENCE LEVEL MATRIX REPORT
*(Corresponds to `EVIDENCE_LEVEL_MATRIX.csv`)*

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Complete Metric Traceability & Evidence Classification  
**Dataset Reference:** [`data/phase7_3_evidence_matrix.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_evidence_matrix.csv) & [`EVIDENCE_LEVEL_MATRIX.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/EVIDENCE_LEVEL_MATRIX.csv)  
**Date of Audit:** 2026-09-18  

---

## 1. Evidence Hierarchy Definitions

| Code | Evidence Level | Operational Definition |
|:---:|:---|:---|
| **L1** | **Publicly Verified / Formal Logic** | Deterministic mathematical proofs, reproducible public algorithms, automated pytest assertions. |
| **L2** | **OEM Documented** | Primary technical specifications, brochures, or manuals published directly by BEML, Cummins, or Allison. |
| **L3** | **NMDC Documented** | Official site documents, crusher parameters, or mining data from NMDC Bailadila Deposit-5. |
| **L4** | **Standard / Regulation** | Statutory standards published by DGMS, ISO, SAE, or AASHTO. |
| **L5** | **Peer-Reviewed Literature** | Published academic journal papers or mining engineering treatises (e.g. SME Mining Engineering Handbook). |
| **L6** | **Engineering Model / Scenario** | Calibrated analytical models, worst-case sensitivity scenarios, or documented engineering assumptions. |
| **L7** | **Bench Measured / Surrogate** | Physical empirical measurements on hardware testbeds (ESP32, TWAI transceivers, surrogate hydraulic rigs). |
| **L8** | **Field Measured** | Empirical data collected on active vehicles operating in a production mine (requires Deposit-5 access). |
| **L9** | **Simulation** | Discrete-event multi-agent simulation results from calibrated software engines. |
| **L10** | **Unknown / Unsupported** | Untraceable claims without verifiable primary sources (must be permanently expunged). |

---

## 2. Complete Evidence Classification Matrix

| Claim Description | Parameter | Value | Level | Primary Source | Location | Sample Size | Reproducibility | Allowed Claim | Forbidden Claim |
|:---|:---|:---:|:---:|:---|:---|:---:|:---:|:---|:---|
| **BH100 Gross Operating Weight** | `mass_loaded_kg` | 165,500 kg | **L2** | BEML BH100 Technical Spec | OEM Documentation | Spec Doc | Deterministic | "Certified OEM GVW under rated payload" | "Weighbridge measured at Bailadila" |
| **BH100 Unladen Tare Mass** | `mass_empty_kg` | 74,000 kg | **L2** | BEML BH100 Technical Spec | OEM Documentation | Spec Doc | Deterministic | "Certified tare weight with standard body" | "Individual axle weight distribution proven" |
| **DGMS Haul Road Slope Limit** | `max_ramp_grade_pct` | 8.0% | **L4** | DGMS Tech Circular 09/2008 | Statutory Regulation | Standard | Deterministic | "Statutory maximum haul road ramp slope" | "Ramp is exactly 8.0% everywhere" |
| **J1939 CAN Frame Wire Time** | `t_can_tx` | 0.512 ms | **L7** | ESP32 TWAI testbed (250 kbps) | Electronics Lab Bench | 12,000 frames | Deterministic | "Hardware J1939 wire tx time at 250 kbps" | "Calling CAN wire time brake response" |
| **Conservative CAN Bus Delay** | `tau_CAN_bound` | 50.0 ms | **L7** | ESP32 TWAI testbed (80% load) | Electronics Lab Bench | 12,000 frames | Statistical | "Conservative bound for high-priority PGNs"| "Logged on active BH100 chassis" |
| **Actuator Pressure Buildup** | `tau_actuator_nom` | 200.16 ms | **L7_Surr**| Laboratory surrogate bench | Hydraulics Lab Bench | 5,000 runs | Statistical | "Surrogate bench air-over-hydraulic delay" | "BH100 measured brake response" |
| **Actuator Worst-Case Cold** | `tau_actuator_worst`| 350.0 ms | **L6** | Degraded fluid viscosity model | Sensitivity Model | Scenario | Deterministic | "Conservative engineering scenario" | "ISO 3450 regulatory upper limit" |
| **Crusher Bottleneck Ceiling** | `crusher_capacity` | 1,647.0 TPH | **L3/L4**| 200s slot cycle (18 VPH * 91.5t) | Deposit-5 Spec | Engineering | Deterministic | "Maximum steady-state crusher ceiling" | "3,294 TPH is steady-state production" |
| **Orchestrator Production** | `steady_state_tph` | 1,591.4 TPH | **L9** | Closed-loop discrete simulation| Simulation Engine | 30 seeds | Statistical | "Achieves 96.6% utilization of crusher" | "Measured on live mine scales" |
| **Haul Road Queue Reduction** | `road_wait_reduc` | -77.1% | **L9** | Multi-seed queue simulation | Simulation Engine | 30 seeds | Statistical | "Relocates queues to safe shovel bays" | "Total cycle delay eliminated by 77.1%" |
| **Packet Loss Invariance** | `safety_invariance` | 100.0% | **L1/L7**| Firmware watchdog HIL test | Firmware Testbed | 3,000 cmds | Deterministic | "Local governor prevents overspeed" | "Communication reliable at 99% loss" |
| **SX1278 V2V Proximity PDR** | `rf_v2v_pdr` | 99.1% | **L7** | SX1278 433 MHz CSS-LoRa bench | RF Lab Bench | 10,000 pkts | Statistical | "Bench-characterized CSS-LoRa link" | "Tested in deep open pit at Bailadila" |
| **Monte Carlo Robustness** | `mc_violations` | 0 Violations | **L9** | 10,000 stochastic draws | Numerical Suite | 10,000 runs | Statistical | "Zero violations in tested space" | "100% real-world safety certification" |
| **Deposit-5 Pit Multipath** | `pit_multipath` | UNKNOWN | **L10** | Requires on-site pit survey | Deposit-5 (Pending) | 0 surveys | PENDING | "Identified future field validation test" | "Bailadila pit RF propagation validated" |
| **BH100 In-Situ Brake Logging**| `bh100_in_situ` | UNKNOWN | **L10** | Requires instrumented chassis | Bailadila Depot (Pending)| 0 test runs | PENDING | "Identified future physical test" | "BH100 brake pressure was measured" |
