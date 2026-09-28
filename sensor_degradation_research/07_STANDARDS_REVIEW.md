# 07 — STANDARDS REVIEW
## FOG-ORCHESTRATOR 2.0 — Applicable Standards Assessment
**Date:** 2026-09-21  
**Rule:** Verify exact scope before citing. Do not cite a standard merely because it contains the word safety.

---

## Standard 1 — ISO 17757 (ASAMS)

**Full Title:** Autonomous and semi-autonomous machine systems — Safety requirements  
**Publication:** ISO 17757:2019  
**Verified Scope:** Earth-moving machinery (ISO 6165) and mobile mining machines with autonomous/semi-autonomous function.

**Relevance to FOG-ORCHESTRATOR:**
- APPLICABLE CONCEPTUALLY: The standard defines "perception system" as the sensor set used for
  detection, localization, and object recognition. It requires that perception data quality be maintained.
- NOT MANDATORY: FOG-ORCHESTRATOR is orchestration software interfacing with HUMAN-OPERATED vehicles.
  The BH100 in its standard configuration is not an ASAMS. ISO 17757 applies to autonomous machines,
  not to FMS-level orchestration layers.
- USEFUL GUIDANCE: The standard's requirements for sensor error handling (dust/obscurant degradation,
  sensor misalignment) directly inform our failure taxonomy (F01, F02, F04, F14).
- CITATION DISCIPLINE: "FOG-ORCHESTRATOR follows principles consistent with ISO 17757 perception
  system integrity requirements." NOT "FOG-ORCHESTRATOR is ISO 17757 compliant."

---

## Standard 2 — IEC 61508

**Full Title:** Functional Safety of Electrical/Electronic/Programmable Electronic Safety-related Systems  
**Publication:** IEC 61508:2010 (Parts 1–7)  
**Verified Scope:** Safety-related E/E/PE systems across all industries. Provides the SIL framework.

**Relevance to FOG-ORCHESTRATOR:**
- NOT MANDATORY: Full IEC 61508 compliance requires a complete safety lifecycle, formal FMEDA,
  probabilistic hardware failure rate calculations, and SIL determination. The prototype has not
  undergone this process.
- USEFUL CONCEPTS:
  - lambda_DU (Dangerous Undetected failure rate) — directly relevant to Class C sensor failures.
  - Diagnostic Coverage — motivates the data health checks H1–H5.
  - Systematic Capability — motivates the rule-based (deterministic) approach over ML approaches.
  - Safe Reaction Logic — validates our fail-closed behaviour for invalid environmental inputs.
- CITATION DISCIPLINE: "The architecture applies fail-closed principles consistent with IEC 61508
  safe reaction logic." NOT "The architecture is IEC 61508 SIL-2 rated."

---

## Standard 3 — SAE J1939

**Full Title:** Serial Control and Communications Heavy Duty Vehicle Network  
**Publication:** SAE J1939 (series of related documents)  
**Verified Scope:** CAN-based vehicle network for heavy-duty vehicles. Defines PGNs, SPNs, 250 kbps.

**Relevance to FOG-ORCHESTRATOR:**
- ALREADY APPLIED: Phase 8 HIL implemented J1939-compatible frame formats (EEC1, CCVS, EBC1, ERC1,
  PropB) in can_twai_hil.py.
- FOR THIS RESEARCH: J1939 does NOT define visibility measurement PGNs. Environmental data
  (meteorological visibility) is NOT part of J1939 vehicle ECU communication. This standard
  therefore does not cover the environmental data health gap.
- CITATION DISCIPLINE: "Vehicle ECU data (engine speed, brake status) follows SAE J1939 PGN
  conventions in the HIL simulation."

---

## Standard 4 — ISO 19014

**Full Title:** Earth-moving machinery — Functional safety  
**Publication:** ISO 19014:2020  
**Verified Scope:** Functional safety requirements for safety-related parts of control systems of 
earth-moving machinery (SRPCS). Performance-based standard for earth-moving machine controls.

**Relevance to FOG-ORCHESTRATOR:**
- RELEVANT DOMAIN: Applies to BEML BH100-class earth-moving machinery control systems.
- LIMITED APPLICABILITY: ISO 19014 focuses on MACHINE CONTROL SYSTEMS (braking, steering,
  powertrain controls), not on fleet management software or orchestration layers.
- USEFUL PRINCIPLE: Performance level requirements for safety functions — our local safety governor
  function (v_applied ≤ v_safe) aligns with the concept of a safety-related control function.
- CITATION DISCIPLINE: "The local safety governor implements a safety function conceptually consistent
  with ISO 19014 SRPCS principles." NOT "ISO 19014 certified."

---

## Standard 5 — ISO 20474-1

**Full Title:** Earth-moving machinery — Safety — Part 1: General requirements  
**Verified Scope:** General safety requirements for earth-moving machinery.

**Relevance to FOG-ORCHESTRATOR:**
- Provides the baseline safety requirements context for the machine class.
- Does not specify sensor data quality checking or FMS integration requirements.
- CITATION DISCIPLINE: Background context only.

---

## Standards Coverage Matrix

| Gap | Most Relevant Standard | Guidance Level | Mandate Level |
|---|---|---|---|
| Sensor/data quality checking | IEC 61508 (lambda_DU concept) | HIGH | NONE |
| Perception system integrity | ISO 17757 | HIGH | NOT MANDATORY (non-ASAMS) |
| Fail-closed behaviour | IEC 61508, ISO 19014 | HIGH | NOT MANDATORY (FMS layer) |
| Vehicle ECU data protocol | SAE J1939 | DIRECT (HIL) | PARTIAL |
| Safety function architecture | ISO 19014 | MEDIUM | NOT MANDATORY (FMS layer) |
| Environmental data quality | NONE found | N/A | N/A |

**Finding:** No standard directly mandates environmental data health checking for FMS orchestration
layers interfacing with human-operated mining vehicles. This confirms the partial gap in the
regulatory/standards landscape and supports the research contribution claim.
