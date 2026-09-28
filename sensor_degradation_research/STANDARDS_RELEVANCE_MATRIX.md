# STANDARDS RELEVANCE MATRIX
## FOG-ORCHESTRATOR 2.0 — Safety Standards Alignment Audit
**Project:** SIH26007 — Fog / Low-Visibility Mine Fleet Orchestrator  
**Date:** 2026-09-21  
**Auditor:** Safety Systems Verification Lead  
**Audit Policy:** Strict anti-overclaiming. Never claim certification or full compliance without full third-party test execution and clause verification.

---

## 1. Standards Alignment Matrix

| Standard | Relevant Concept | Exact Verified Clause? | Applicability Verified? | Evidence | Status | Open Verification Task |
|---|---|---|---|---|---|---|
| **ISO 17757:2019** *(Autonomous and semi-autonomous machine systems for earth-moving machinery)* | Supervisory system boundaries, operational domain constraints, fail-safe degradation on perception loss | Clause 4.3 (Perception system integrity), Clause 5.6 (Emergency stop & fail-safe fallback) | CONCEPTUAL ALIGNMENT ONLY (Mining haulage in restricted visibility) | Architectural design principles; fail-safe governor clamping ($v_{\text{applied}} \le v_{\text{safe}}$) | **INFORMED BY STANDARD (NOT CERTIFIED)** | Physical machine physical emergency brake test; functional testing of all ASAMS state transitions on physical machine. |
| **ISO 19014:2018 (Parts 1–4)** *(Earth-moving machinery — Functional safety)* | Machine Performance Level (MPL) specification, systematic failure prevention, diagnostic coverage | Part 2 Clause 5.2 (Diagnostic coverage for sensors), Part 4 (Software design requirements) | CONCEPTUAL ALIGNMENT ONLY (Safety-related parts of control systems) | Deterministic failure injection test suite (`tests/`); bounded execution time; defensive type checking | **INFORMED BY STANDARD (NOT CERTIFIED)** | Formal FMEA/FMECA analysis; MTBF calculation for physical hardware; independent software tool qualification. |
| **IEC 61508:2010 (Parts 1–7)** *(Functional safety of electrical/electronic/programmable electronic safety-related systems)* | Fail-safe principles, Safe Failure Fraction (SFF), $\lambda_{\text{DU}}$ (Dangerous Undetected failures) | Part 2 Table A.1 (Diagnostic coverage techniques), Part 3 (Software architecture) | CONCEPTUAL ALIGNMENT ONLY (Risk reduction via independent safety layer) | Class C (plausible-but-wrong) analyzed as $\lambda_{\text{DU}}$; fail-closed exception boundaries | **ARCHITECTURAL REFERENCE ONLY** | Full SIL determination; rigorous verification of software lifecycle documentation according to IEC 61508-3. |
| **SAE J1939-71 / J1939-21** *(Surface Vehicle Recommended Practice / CAN Application Layer)* | Parameter Group Numbers (PGN) for vehicle speed (PGN 65265), engine RPM (PGN 61444), brake status | PGN 65265 (Cruise Control / Vehicle Speed), PGN 61444 (Electronic Engine Controller 1) | CANDIDATE INTERFACE ONLY (BH100 deployment path) | Synthetic HIL payload parsing in `integration_adapters/can_twai_hil.py` | **CANDIDATE INTERFACE (NOT OEM VALIDATED)** | Connect physical CAN bus analyzer to active BEML BH100 dump truck; verify PGN broadcast rates and presence of unencrypted speed/RPM. |
| **DGMS Tech. Circular No. 06 of 2020** *(Directorate General of Mines Safety — Safety in Opencast Mines)* | Provision of operator assistance devices in HEMM, proximity warning, low-visibility alarms | Section 3 (Fatigue & visibility aids), Section 4 (Safe traffic management) | HIGH RELEVANCE (Indian coal/iron ore regulatory context) | Local operator HMI safe speed alert; audio-visual warning; staging at hazardous bottlenecks | **REGULATORY TARGET ALIGNED** | Formal demonstration before DGMS inspection authority; trial deployment in NMDC/Coal India open-cast pit. |
| **NMDC Open-Cast Haulage Safety Guidelines** | Mine traffic dispatch rules, speed limits in fog ($10\text{--}15\text{ km/h}$), dumper-crusher flow control | General mine standing orders (speed restriction under fog/dust) | DIRECT RELEVANCE (Hackathon benchmark context) | Staging queue logic, mine speed limit limiter ($v_{\text{mine}}$ in physics solver) | **OPERATIONAL GOAL ALIGNED** | Review against specific mine standing orders of NMDC Bailadila or Donimalai iron ore projects. |

---

## 2. Definitive Non-Compliance Statement

> [!IMPORTANT]
> FOG-ORCHESTRATOR 2.0 has **NOT** undergone formal laboratory or site certification under ISO 17757, ISO 19014, or IEC 61508.
> The standards above serve exclusively as **engineering reference frameworks** for diagnostic coverage classification, fault taxonomy structuring, and fail-safe state machine design.
> Any claim that the current software is "ISO certified" or "IEC 61508 compliant" is false, mathematically unproven, and strictly prohibited.
