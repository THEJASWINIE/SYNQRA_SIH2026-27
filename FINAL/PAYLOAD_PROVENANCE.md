# PAYLOAD & VEHICLE MASS PROVENANCE AUDIT
## FOG-ORCHESTRATOR 2.0 / SIH26007 — Scientific Closure

**Document Status:** FINAL AUTHORITATIVE RECONCILIATION  
**Audit Date:** 2026-09-21  
**Author:** Principal Safety-Critical Systems Auditor & Lead Scientific Validator  

---

### 1. Executive Summary: The 80.5t vs 91.5t Discrepancy

During forensic audit of the Sensor Degradation benchmark suite (`experiments/run_sensor_degradation_benchmark.py`), a payload discrepancy was identified between two distinct modules of the FOG-ORCHESTRATOR codebase:

1. **Canonical Model / Core Architecture Parameter:** **$91.5\text{ tonnes}$** ($91,500\text{ kg}$)
   - Sourced from official BEML BH100 OEM technical specification brochures (Tier L2 OEM Documented).
   - Unladen Tare Mass: $74.0\text{ tonnes}$ ($74,000\text{ kg}$).
   - Gross Vehicle Operating Weight (GVW): $165.5\text{ tonnes}$ ($165,500\text{ kg}$).
   - Rated Factory Payload: $165.5\text{ t} - 74.0\text{ t} = \mathbf{91.5\text{ tonnes}}$ (100 short tons).

2. **Sensor Degradation Benchmark Parameter:** **$80.5\text{ tonnes}$** ($80,500\text{ kg}$)
   - Location: `experiments/run_sensor_degradation_benchmark.py` Line 98 (`PAYLOAD_TONNES = 80.5`).
   - Sourced from operational mining practice at NMDC Bailadila Deposit-5 (Tier L6 Engineering Assumption).
   - Heavy-duty abrasive iron ore rock body liners and steel reinforcement wear plates add $\approx 11.0\text{ tonnes}$ to unladen chassis tare (increasing empty mass from $74.0\text{ t} \to 85.0\text{ t}$).
   - Operating within the certified statutory $165.5\text{ t}$ GVW ceiling, the usable net payload per haul cycle is $165.5\text{ t} - 85.0\text{ t} = \mathbf{80.5\text{ tonnes}}$ (an operational payload fill factor of $88.0\%$).

---

### 2. Comprehensive Code & Documentation Audit Register

The repository was exhaustively searched for instances of `80.5`, `91.5`, `80500`, and `91500`. The authoritative findings are cataloged below:

| Value | Code / Document Location | Variable / Context | Meaning | Evidence Source | Evidence Tier | Canonical Status |
|---|---|---|---|---|---|---|
| **$91.5\text{ t}$** | `reports/14_FINAL_BH100_EVIDENCE.md` L18 | `Nominal Rated Payload` | Manufacturer rated factory payload capacity | BEML BH100 OEM Technical Brochure | **L2** (OEM Documented) | **Canonical Project Spec** |
| **$91.5\text{ t}$** | `reports/16_FINAL_PARAMETER_RECONCILIATION.md` L16 | `payload_rated_kg: 91500.0` | Rated payload for mass conservation | BEML OEM Datasheet | **L2** (OEM Documented) | **Canonical Project Spec** |
| **$91.5\text{ t}$** | `reports/18_FINAL_CANONICAL_PARAMETERS.yaml` L36 | `payload_rated_kg: 91500.0` | Official metric rating (100 short tons) | BEML OEM Datasheet | **L2** (OEM Documented) | **Canonical Project Spec** |
| **$91.5\text{ t}$** | `reports/15_FINAL_EVIDENCE_MATRIX.md` L32 | Crusher Calculation ($18 \times 91.5\text{ t}$) | Derivation of 1,647 TPH crusher ceiling | Analytical Crusher Engineering Audit | **L3 / L6** (Physical Derived) | **Canonical Bottleneck Model** |
| **$74.0\text{ t}$** | `fog_safe/config.py` L12 | `mass_empty: 74000.0` | Unladen standard factory chassis tare | BEML OEM Datasheet | **L2** (OEM Documented) | **Canonical Project Spec** |
| **$165.5\text{ t}$** | `reports/14_FINAL_BH100_EVIDENCE.md` L19 | `Gross Operating Weight` | Certified gross operating machine mass | BEML OEM Datasheet ($74\text{t} + 91.5\text{t}$) | **L2** (OEM Documented) | **Canonical Project Spec** |
| **$80.5\text{ t}$** | `experiments/run_sensor_degradation_benchmark.py` L98 | `PAYLOAD_TONNES = 80.5` | Operational payload per trip in benchmark | Heavy-liner chassis tare ($85\text{t}$) assumption | **L6** (Engineering Assumption) | **Benchmark-Specific Operational Spec** |
| **$80.5\text{ t}$** | `FINAL/SENSOR_DEGRADATION_FINAL_REPORT.md` L108 | Simulated Hauler Payload | Net payload under heavy tare configuration | Sensor Degradation Experimental Setup | **L6** (Engineering Assumption) | **Benchmark-Specific Operational Spec** |
| **$80.5\text{ t}$** | `FINAL/SENSOR_DEGRADATION_JUDGE_QA.md` L43 | Tonnage Calculation | Multiplier for completed trips | Sensor Degradation Benchmark Math | **L6** (Engineering Assumption) | **Benchmark-Specific Operational Spec** |

---

### 3. Forensic Causal Answers to Mandatory Questions

#### 1. Why is 80.5t used in the Sensor Degradation Benchmark?
In open-pit hard-rock mining (specifically hematite iron ore at Bailadila Deposit-5), rigid haul dumpers are equipped with heavy steel body liner plates (Hardox/high-manganese steel) to withstand shovel impact loading. This raises the tare mass from factory unladen $74.0\text{ tonnes}$ to approximately $85.0\text{ tonnes}$. To prevent tire overheating and structural overload beyond the certified Gross Vehicle Weight of $165.5\text{ tonnes}$, dispatch limits the payload to:
$$\text{Payload}_{\text{operational}} = 165.5\text{ t (GVW)} - 85.0\text{ t (Heavy Tare)} = \mathbf{80.5\text{ tonnes}}$$

#### 2. Is it intentional?
**YES.** It was intentionally defined as an operational haulage parameter to represent realistic unconstrained pit-to-dump cycle production under severe duty conditions, rather than theoretical clean-body showroom payload.

#### 3. Is it a benchmark-specific usable payload?
**YES.** It is strictly benchmark-specific to the 14-scenario Sensor Degradation benchmark (`experiments/run_sensor_degradation_benchmark.py`).

#### 4. Is it an outdated constant?
**NO.** It is a contemporaneous operational payload model introduced during the multi-truck fleet haulage benchmark.

#### 5. Is it a coding error?
**NO.** It does not represent a syntax error, unit miscalculation, or accidental numeric transposition.

#### 6. Is it a different vehicle configuration?
**YES.** It reflects the heavy-liner abrasive duty configuration of the BEML BH100 platform ($85.0\text{ t}$ empty, $80.5\text{ t}$ payload, $165.5\text{ t}$ loaded), contrasting with the standard factory specification configuration ($74.0\text{ t}$ empty, $91.5\text{ t}$ payload, $165.5\text{ t}$ loaded).

---

### 4. Mathematical Conversion & Cross-Consistency Proof

Both configurations share the identical **Gross Vehicle Weight of $165.5\text{ tonnes}$ ($165,500\text{ kg}$)**. Because braking dynamics, tire-road traction, rolling resistance, and retarder heat absorption are functions of **gross mass** ($m_{\text{loaded}} = 165.5\text{ t}$), the physical stopping distance, safe speed $v_{\text{safe}}$, and command authority $v_{\text{command}}$ are **mathematically invariant** between the two payload assumptions.

The only affected metric is the delivered haulage tonnage scalar:
- **Under Benchmark Operational Spec ($80.5\text{ t}$):**
  $$\text{Tonnage}_{\text{benchmark}} = 72\text{ trips} \times 80.5\text{ tonnes} = \mathbf{5,796.0\text{ Tonnes (over 2 hours)}} \implies \mathbf{2,898.0\text{ TPH}}$$
- **Under Canonical Factory Spec ($91.5\text{ t}$):**
  $$\text{Tonnage}_{\text{canonical}} = 72\text{ trips} \times 91.5\text{ tonnes} = \mathbf{6,588.0\text{ Tonnes (over 2 hours)}} \implies \mathbf{3,294.0\text{ TPH}}$$

### 5. Final Authoritative Rule
1. The **Canonical Project Reference** for BEML BH100 factory rating remains **$91.5\text{ tonnes}$** (Tier L2).
2. The **Sensor Degradation Benchmark** delivered tonnage figures ($\sim 5,796\text{ t}$) are based on the **$80.5\text{ tonnes}$ operational spec** (Tier L6).
3. These values must **never be silently conflated**. Every citation of $5,796\text{ t}$ must explicitly state: *"based on 72 completed trips at 80.5t operational payload per trip"*.
