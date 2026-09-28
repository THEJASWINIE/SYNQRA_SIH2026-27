# 12 — LIMITATIONS
## FOG-ORCHESTRATOR 2.0 — Sensor Degradation Research Limitations
**Date:** 2026-09-21  
**Classification:** These are honest limitations, not implementation failures.

---

## L01 — CLASS C (PLAUSIBLE-BUT-WRONG) IS UNDETECTABLE

**Category:** Architecture Limitation  
**Severity:** CRITICAL  
**Description:**  
If a visibility sensor continuously reports 50 m while actual visibility is 5 m, the proposed
data health layer cannot detect this failure. The value passes all checks:
- Range check: 50 m is within [0.5, 2000] m — PASS
- Freshness check: fresh timestamp — PASS
- Noise check: stable reading — PASS
- Stuck-at check: value changes slightly — PASS

**Impact:**
v_safe computed at 50 m = ~8.52 m/s; true safe speed at 5 m = ~0.97 m/s.
Over-permission of ~7.55 m/s.

**Resolution Requirement:**
Requires at least one independent source of visibility: a second weather station in the
same zone, a vehicle-mounted proximity sensor, or cross-referenced V2V vehicle shadow detection.

**Mitigation (Partial, Not a Solution):**
Apply a conservative r_effective = visibility_m * 0.8 even in HEALTHY state as a standing
uncertainty buffer. This reduces over-permission but does not eliminate it.

**Classification:** DEPLOYMENT REQUIREMENT — resolved only with additional infrastructure.

---

## L02 — STUCK-AT DETECTION HAS 300 S LATENCY

**Category:** Performance Limitation  
**Severity:** HIGH  
**Description:**  
The stuck-at check (H3) requires T_STUCK_MIN = 300 s of constant readings before flagging.
During this 300 s window, if true visibility has declined below the stuck value, the system
operates with an over-estimated r_effective.

**Worst Case Calculation:**
Stuck sensor at 12 m while true visibility drops to 5 m over 300 s.
At 300 s mark: system transitions to DEGRADED → conservative r_effective applied.
But during the 300 s window: over-permission exists.

**Resolution:** Shorten T_STUCK_MIN. Risk: false positives in genuinely stable fog conditions.
This is a tuneable trade-off, not a solvable limitation without a second source.

**Classification:** TUNEABLE TRADE-OFF — documented as a design parameter.

---

## L03 — NO ZONE-LEVEL VISIBILITY

**Category:** Architecture Limitation  
**Severity:** HIGH (safety) / MEDIUM (throughput)  
**Description:**  
The current architecture applies a single mine-wide visibility value to all road segments.
Open-pit mines exhibit significant zone-to-zone visibility variation (documented in literature).
Zone D (pit floor) may have 5 m visibility while Zone A (rim) has 50 m.

**Impact:**  
Trucks in high-fog zones are permitted higher speed than their local conditions allow.

**Resolution Requirement:**  
Zone-differentiated visibility requires:
1. Multiple weather stations (one per major zone) OR
2. Vehicle-mounted proximity sensing (not available on BH100) OR
3. GPS-keyed zone assignment with per-zone visibility from FMS

**Classification:** FUTURE INTEGRATION REQUIREMENT — not solvable within prototype scope.

---

## L04 — NO SECOND VISIBILITY SOURCE FOR CONFLICT DETECTION

**Category:** Prototype Limitation  
**Severity:** MEDIUM  
**Description:**  
The CONFLICTING data state (H5 rule) requires at least two independent visibility sources.
The current prototype has zero physical visibility sources.
The benchmark simulation injects visibility as a scenario parameter.

In D9 (conflict scenario), the second source is also simulated.
No physical cross-validation is possible.

**Classification:** PROTOTYPE BOUNDARY — cannot be validated on physical hardware without infrastructure.

---

## L05 — VISIBILITY IS NOT MEASURED ON THE ESP32 PROTOTYPE

**Category:** Prototype Boundary (Pre-existing)  
**Severity:** HIGH (for hardware validation claim)  
**Description:**  
visibility_m is set by benchmark parameters or simulation scenarios.
No physical sensor on the ESP32 prototype produces a visibility measurement.
NEVER_FROM_HARDWARE frozenset explicitly excludes it.

**Impact:**  
All sensor degradation experiments are SIMULATION only.
No physical hardware validation of the degradation detection is possible on this prototype.

**Classification:** PRE-EXISTING PROTOTYPE BOUNDARY — documented in telemetry_ingest.py.

---

## L06 — BH100 J1939 PGN LIST NOT VERIFIED

**Category:** Documentation Gap  
**Severity:** MEDIUM (for BH100 integration planning)  
**Description:**  
Generic J1939 compliance of BH100's Cummins engine and Allison transmission is confirmed.
The specific PGN/SPN mapping for the BH100's brake, retarder, and speed reporting is NOT
verified from authoritative BEML documentation.

**Impact:**  
Any claims about specific BH100 J1939 signal availability must remain UNKNOWN / NOT VERIFIED.
The HIL simulation uses generic J1939 PGNs, not BH100-specific ones.

**Classification:** DOCUMENTATION GAP — requires BEML Parts Catalogue access.

---

## L07 — BIAS AND DRIFT CANNOT BE DETECTED WITHOUT CALIBRATION RECORD

**Category:** Architecture Limitation  
**Severity:** HIGH  
**Description:**  
F06 (Bias) and F07 (Drift) require either:
- A calibration reference value, OR
- An independent source for comparison, OR
- Long-term trend analysis (hours to days)

None of these are available in real-time with a single visibility source.

**Classification:** KNOWN LIMITATION OF SINGLE-SOURCE SENSING — consistent with IEC 61508 lambda_DU.

---

## L08 — SPATIAL REPRESENTATIVENESS OF WEATHER STATION DATA IS UNKNOWN

**Category:** Data Provenance Limitation  
**Severity:** HIGH  
**Description:**  
NMDC Bailadila uses on-site weather stations. The exact placement, number, zone coverage,
and update rate of these stations is NOT documented in publicly available sources.
The assumption that one station represents the entire haul network is used in the prototype
but is likely incorrect in reality (confirmed by spatial meteorology literature).

**Classification:** DATA PROVENANCE GAP — requires direct access to NMDC FMS documentation.

---

## L09 — BENCHMARK IS SIMULATION ONLY

**Category:** Evidence Boundary  
**Severity:** MEDIUM  
**Description:**  
All results from the sensor degradation benchmark (D0–D12) are produced by simulation.
Degradation scenarios are injected programmatically, not from physical sensor failures.
Results demonstrate algorithmic behaviour, not physical-world validation.

**Classification:** SIMULATION EVIDENCE — not physical mine validation.

---

## Summary of Limitations

| ID | Limitation | Severity | Resolvable in Prototype? |
|---|---|---|---|
| L01 | Class C (plausible-but-wrong) undetectable | CRITICAL | NO — needs 2nd source |
| L02 | Stuck-at detection latency 300 s | HIGH | PARTIAL — tuneable |
| L03 | No zone-level visibility | HIGH | NO — needs infrastructure |
| L04 | No second source for conflict detection | MEDIUM | NO — needs infrastructure |
| L05 | No physical visibility sensor on prototype | HIGH | NO — prototype boundary |
| L06 | BH100 J1939 PGN list not verified | MEDIUM | Needs BEML docs access |
| L07 | Bias/drift undetectable without calibration | HIGH | NO — needs 2nd source |
| L08 | Weather station spatial representativeness unknown | HIGH | Needs NMDC FMS access |
| L09 | Benchmark is simulation only | MEDIUM | Pre-existing boundary |
