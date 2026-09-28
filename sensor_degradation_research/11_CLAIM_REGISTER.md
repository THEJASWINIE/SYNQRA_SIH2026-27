# 11 — CLAIM REGISTER
## FOG-ORCHESTRATOR 2.0 — Sensor Degradation Research Claims
**Date:** 2026-09-21  
**Epistemic Classification:** FACT / MEASURED / MODELLED / ASSUMED / SIMULATED / UNKNOWN

---

| Claim ID | Claim | Classification | Evidence | Confidence |
|---|---|---|---|---|
| C01 | visibility_m → r_effective path has NO freshness check in the existing architecture | FACT | Code inspection: fog_safe/environment.py, telemetry_ingest.py, telemetry_quality_filter.py | HIGH |
| C02 | TelemetryQualityFilter covers vehicle telemetry freshness (LIVE/STALE/OFFLINE) | FACT | Code inspection: integration_adapters/telemetry_quality_filter.py | HIGH |
| C03 | solve_safe_speed fails closed on mu <= 0 (v_safe = 0) | FACT | Code inspection: fog_safe/safety.py:114-116 | HIGH |
| C04 | solve_safe_speed does NOT check r_effective for staleness or plausibility | FACT | Code inspection: fog_safe/safety.py — no freshness parameter in signature | HIGH |
| C05 | TRUCK_02 speed field is PWM-derived, not encoder-measured | FACT | Code comment: telemetry_ingest.py:66-73, firmware comment cited | HIGH |
| C06 | No GNSS receiver is fitted on the ESP32 prototype vehicles | FACT | GNSS_EQUIPPED_VEHICLES = frozenset() in telemetry_ingest.py:118 | HIGH |
| C07 | No visibility sensor exists on the ESP32 prototype vehicles | FACT | NEVER_FROM_HARDWARE frozenset includes visibility_m; no firmware produces it | HIGH |
| C08 | v_safe at r_effective=12 m, -8% grade, 165.5 t, mu=0.35 ≈ 2.70 m/s | MODELLED | fog_safe.safety.solve_safe_speed with canonical parameters | HIGH |
| C09 | v_safe at r_effective=50 m (same conditions) ≈ 8.52 m/s | MODELLED | fog_safe.safety.solve_safe_speed with canonical parameters | HIGH |
| C10 | Over-permission of ~5.82 m/s when bias sensor reports 50 m with true vis = 12 m | MODELLED | Derived from C08, C09 | HIGH |
| C11 | BEML BH100 uses J1939 at 250 kbps for engine/transmission ECUs | FACT PARTIAL | BEML documentation references (web-verified), J1939 standard; specific PGN list for BH100 NOT verified | MEDIUM |
| C12 | NMDC Bailadila uses on-site meteorological stations | FACT | NMDC ICCC documentation (public) | MEDIUM |
| C13 | Zone-level visibility data is NOT documented as available from NMDC FMS | FACT | No documentation found; confirmed absence | HIGH |
| C14 | Open-pit mines exhibit significant spatial visibility variation due to microclimate effects | FACT | Mining meteorology research literature (L5) | HIGH |
| C15 | A single weather station is insufficient to represent visibility across all haul road zones | FACT | Research literature consensus (L5) | HIGH |
| C16 | ISO 17757 applies to autonomous machines, not FMS orchestration layers | FACT | ISO 17757:2019 scope clause (verified) | HIGH |
| C17 | IEC 61508 lambda_DU concept applies to Class C (plausible-but-wrong) sensor failures | FACT | IEC 61508 Part 1 (verified concept); not a mandate for FOG-ORCHESTRATOR | HIGH |
| C18 | The proposed EnvironmentalDataHealth module requires ~200 LOC | ASSUMED | Architecture design estimate | LOW |
| C19 | Phase 8 HIL verified Invariant I3 (local safety operates independently of comms loss) | FACT | Phase 8 test suite: 60 passed, 0 failed; 105/105 benchmark scenarios passed I1 | HIGH |
| C20 | D7 (bias scenario) will produce unsafe commands due to Class C undetectability | MODELLED | Expected from gap analysis; not yet experimentally confirmed | MEDIUM |
| C21 | Rule-based data health is more appropriate than ML for this context | ARGUED | Based on: explainability requirement, single sensor source, no training data, safety-critical context | MEDIUM |
| C22 | Adding the data health layer does not bypass or weaken the local safety governor | DESIGNED | Architecture design: health layer modifies r_effective only; governor unchanged | HIGH (design intent) |

---

## Forbidden Claims (Not to be made in any project document)

| Forbidden Claim | Reason |
|---|---|
| "Sensor degradation is solved" | Class C (plausible-but-wrong) cannot be detected |
| "The system handles all sensor failures" | F05 has 300 s detection latency; F14, F15 are unresolved |
| "Weather station is always accurate" | Forward-scatter sensors are known to exhibit bias and drift |
| "HEMM has redundant sensors" | Not documented for BH100 in standard configuration |
| "BH100 has visibility sensor X" | No authoritative documentation found |
| "Physical validation in mine conditions" | This is a simulation prototype only |
| "ISO 17757 certified" | Not undergone ASAMS certification process |
| "IEC 61508 SIL-rated" | Not undergone SIL determination process |
