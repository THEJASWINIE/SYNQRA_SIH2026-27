# 06 — PRIOR ART REVIEW
## FOG-ORCHESTRATOR 2.0 — Literature and Prior Art Assessment
**Date:** 2026-09-21

---

## 1. Search Scope

Searched for:
- Sensor degradation in mining HEMM
- Mining vehicle sensor health monitoring
- Visibility sensor fault detection
- Fog sensor fusion in mining
- Mining FMS sensor confidence
- Degraded perception in mining vehicles
- Safety envelopes under uncertain environmental state
- Uncertainty-aware haulage orchestration
- Fleet management under sensor uncertainty

---

## 2. Relevant Prior Art Found

### 2.1 Vehicle Sensor Health Monitoring in Mining

**Finding:** Monitoring of vehicle-mounted sensors (GPS/IMU, onboard telematics) is COMMON PRACTICE
in mining HEMM fleets. Caterpillar VIMS (Vital Information Management System) performs onboard health
monitoring. Komatsu JXCE01 provides similar monitoring for their AHS trucks.

**Evidence Level:** L5 (research literature), L1 partial (commercial documentation)

**Relevance to FOG-ORCHESTRATOR:** The vehicle telemetry quality monitoring (TelemetryQualityFilter)
already captures this class of monitoring for the prototype's sensor signals. No gap here.

### 2.2 Autonomous Haulage System (AHS) Sensor Degradation

**Finding:** Komatsu FrontRunner, Caterpillar Command for Hauling, and similar AHS platforms implement
multi-modal sensor fusion (GPS/INS + LiDAR + radar) with explicit degraded-mode protocols. When
perception confidence falls below a threshold, the AHS vehicle decelerates to a safe-hold speed.

**Evidence Level:** L1 partial (commercial documentation, patent literature)  
**Key Limitation:** These systems apply to LiDAR/radar-equipped autonomous platforms, NOT to 
human-operated vehicles like BH100 with FMS-only environmental data.

**Relevance to FOG-ORCHESTRATOR:** The concept of degraded-mode safe speed is validated prior art.
Our proposed R_UNAVAILABLE_MIN fallback follows this pattern. However, the sensor mix is entirely
different — we rely on meteorological station visibility data, not onboard perception sensors.

### 2.3 Visibility Sensor Fault Detection

**Finding:** Forward-scatter visibility meters are known to exhibit:
- Fouling (dust/condensate on optical surfaces) → under-reading visibility
- Power supply variation → erratic readings
- Calibration drift over months → systematic bias

These failure modes are documented in meteorological literature and mine weather station operator manuals.

**Evidence Level:** L5 (meteorological standards, mine weather guides)

**Relevance:** Directly motivates F06 (Bias), F07 (Drift), F05 (Stuck-at) entries in the taxonomy.

### 2.4 Spatial Variation of Visibility in Open-Pit Mines

**Finding:** Multiple studies confirm that open-pit mines create microclimatic effects due to:
- Varying pit depth and topography
- Different radiation loading on pit faces
- Localised dust from active haul roads
- Cold air pooling in pit floors at night/dawn

A single weather station at the pit rim significantly misrepresents visibility in active haul zones.

**Evidence Level:** L5 (mining meteorology literature), L2 (NMDC ICCC documentation)

**Relevance:** Directly supports F14 (Spatially Stale Environmental Data) and the spatial zone
experiment in Section 12 of the research prompt. Single-point visibility is a demonstrated limitation,
not a theoretical one.

### 2.5 Uncertainty-Aware Haulage Orchestration

**Finding:** THIS IS A PARTIAL GAP. Most mining FMS literature focuses on vehicle dispatching
and queue optimization under deterministic or stochastic demand. The specific problem of orchestrating
haul trucks under explicitly degraded environmental sensor confidence (not just speed uncertainty) is
NOT well-covered in the published literature found.

FMS uncertainty handling found: scheduling under machine breakdown uncertainty, stochastic travel time.
FMS uncertainty handling NOT found: environmental data health states feeding speed envelope decisions.

**Evidence Level:** L5/L8 — partial gap confirmed  
**Novelty Assessment:** PARTIAL CONTRIBUTION — the integration of a formal environmental data health
state into the safety speed envelope calculation is novel in the FMS orchestration context.

### 2.6 Plausible-But-Wrong Sensor Data

**Finding:** IEC 61508 terminology: Dangerous Undetected failure (lambda_DU). This failure class is
well-known in functional safety. Mitigation requires either:
(a) Redundant independent sensors
(b) Process-model-based virtual sensors (Kalman, ML observer)
(c) Physical calibration verification

None of these options are available on the current prototype without hardware addition.

**Evidence Level:** L4 (IEC 61508 as guidance), L5 (functional safety literature)

**Relevance:** Confirms that the prototype's inability to detect Class C (plausible-but-wrong) is not
a design oversight — it is a fundamental limitation that can only be resolved with additional hardware
or infrastructure. This is properly classified as LIMITATION in Report 12.

---

## 3. Novelty Assessment

| Capability | Classification |
|---|---|
| Vehicle sensor health monitoring | COMMON PRACTICE |
| AHS degraded-mode safe speed | KNOWN PRACTICE (different sensor class) |
| Visibility sensor fault detection | KNOWN RESEARCH (meteorological domain) |
| Environmental data health state in safety speed solver | PARTIAL GAP — potential contribution |
| Zone-differentiated visibility in FMS orchestration | PARTIAL GAP |
| Formal DATA STATE / COMM STATE / SAFETY STATE separation | DESIGN CONTRIBUTION |
| Plausible-but-wrong detection (Class C) | KNOWN LIMITATION — not solved here |

---

## 4. Conclusion

The proposed degradation layer is:
- Grounded in established functional safety principles (IEC 61508 lambda_DU concept)
- Consistent with AHS industry practice for degraded-mode operation
- Addressing a genuine partial gap in the mine FMS / environmental data health integration literature
- Not overclaiming novelty in sensor fusion or AI-based approaches

The prototype does NOT claim to solve:
- Class C (plausible-but-wrong) detection
- Zone-level visibility estimation
- ML-based sensor fusion
These remain documented limitations and future research directions.
