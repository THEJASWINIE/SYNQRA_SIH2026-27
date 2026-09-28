# THROUGHPUT SEMANTICS & CRUSHER BOTTLENECK RECONCILIATION
## FOG-ORCHESTRATOR 2.0 / SIH26007 — Scientific Closure

**Document Status:** FINAL AUTHORITATIVE RECONCILIATION  
**Audit Date:** 2026-09-21  
**Author:** Principal Safety-Critical Systems Auditor & Lead Scientific Validator  

---

### 1. Executive Definition: "Modeled Completed Haulage Tonnage"

In all Sensor Degradation benchmark publications, reports, and tables, the headline metric:
$$\mathbf{5,796.0\text{ Tonnes (over 2 hours)}} \quad (\approx 2,898.0\text{ TPH})$$
is defined strictly and authoritatively as:

> **MODELED COMPLETED HAULAGE TONNAGE**  
> *The cumulative payload delivered from the open-pit shovel face to the pit dumping perimeter by the 6-truck BEML BH100 fleet over a 7,200-second (2-hour) simulation horizon under unconstrained multi-bay tipping conditions.*

It is **NOT** "mine production", **NOT** "crusher throughput", and **NOT** "crusher receipts".

---

### 2. Executable Code Provenance & Implementation

In `experiments/run_sensor_degradation_benchmark.py`:
- **Haulage Cycle Logic (Lines 328–335):**
  ```python
  elif st == "DUMPING":
      trk["wait_time"] += dt
      if trk["wait_time"] >= 90.0:  # 90-second unconstrained multi-bay tip
          trk["state"] = "RETURNING"
          trk["progress_m"] = 0.0
          trk["wait_time"] = 0.0
          trips_completed += 1
  ```
- **Tonnage Scalar Multiplication (Line 353):**
  ```python
  throughput_tonnes = trips_completed * PAYLOAD_TONNES  # 72 * 80.5 = 5796.0 tonnes
  ```

Every completed trip registers exactly **$80.5\text{ tonnes}$** of ore delivered to the dump apron upon elapsed 90-second tipping cycle.

---

### 3. Reconciling 2,898 TPH with the 1,647 TPH Crusher Bottleneck

A critical architectural finding in the FOG-ORCHESTRATOR master research is the physical bottleneck of the **Bailadila Deposit-5 Primary Gyratory Crusher**:
- **Crusher Type:** Single-tipping-pocket primary gyratory crusher.
- **Physical Gross Dump Cycle ($T_{\text{dump}}$):** $200.0\text{ seconds}$ per haul truck (backing, positioning, bed hoist, discharge, bed lowering, departure).
- **Maximum Steady-State Intake Frequency:**
  $$f_{\text{max}} = \frac{3,600\text{ s/hr}}{200.0\text{ s/truck}} = 18.0\text{ trucks/hour}$$

#### The Mathematical Comparison:

| Parameter | Single-Pocket Primary Gyratory Crusher | Sensor Benchmark Haulage Model | Reconciliation / Mechanism |
|---|---|---|---|
| **Dump Cycle Time ($T_{\text{dump}}$)** | $200.0\text{ s}$ per truck | $90.0\text{ s}$ per truck | Benchmark models fast multi-bay open tipping (e.g. waste dump or multi-chute ROM stockpile). |
| **Pocket Availability** | 1 dedicated single pocket | Unconstrained parallel bays (no queuing bottleneck at dump) | Benchmark measures haul road transit capacity, not downstream crushing capacity. |
| **Max Dumps per Hour** | $18.0\text{ trucks/hr}$ | $36.0\text{ trucks/hr}$ ($72\text{ dumps / 2 hr}$) | Exactly $2.0\times$ the single-pocket rate (equivalent to a dual-pocket dumping station). |
| **Tonnage at $91.5\text{ t}$** | $\mathbf{1,647.0\text{ TPH}}$ ($3,294.0\text{ t / 2hr}$) | $\mathbf{3,294.0\text{ TPH}}$ ($6,588.0\text{ t / 2hr}$) | $2.0\times$ single-pocket capacity. |
| **Tonnage at $80.5\text{ t}$** | $\mathbf{1,449.0\text{ TPH}}$ ($2,898.0\text{ t / 2hr}$) | $\mathbf{2,898.0\text{ TPH}}$ ($5,796.0\text{ t / 2hr}$) | Exactly $2.0\times$ single-pocket capacity ($2 \times 1,449 = 2,898\text{ TPH}$). |

---

### 4. Forensic Causal Reconciliation

1. **Why the discrepancy exists:**  
   The Sensor Degradation benchmark specifically investigated **haul road traffic flow, fog speed governor compliance, and vehicle headway safety** across the $-8\%$ gradient ramp. It intentionally isolated road performance from stationary crusher queuing by assuming an unconstrained multi-bay dump apron with a nominal 90-second tipping cycle.

2. **Why 2,898 TPH cannot be dumped into a single-pocket crusher:**  
   If all 36 trucks per hour arrived at a single 200s pocket, the arrival rate ($36\text{ VPH}$) would exceed the service rate ($18\text{ VPH}$) by $2.0\times$. Within 2 hours, a catastrophic queue of 36 haul dumpers ($>378\text{ meters}$ of heavy trucks) would accumulate on the crusher approach ramp.

3. **System Behavior under Canonical FOG-ORCHESTRATOR Integration:**  
   When the Data-Health layer is integrated with the central FOG-ORCHESTRATOR Level-4 Slot Scheduler, the central orchestrator enforces the statutory 200-second crusher spacing rule, metering dispatches so that haul road throughput does not exceed **$1,647.0\text{ TPH}$ (at $91.5\text{ t}$)** or **$1,449.0\text{ TPH}$ (at $80.5\text{ t}$)**.

---

### 5. Mandatory Reporting Standard

In all future documentation, presentations, and publications:
- The term **"Mine Production"** is **FORBIDDEN** when referring to the 5,796t figure.
- The term **"Crusher Throughput"** is **FORBIDDEN** when referring to the 5,796t figure.
- The only permissible term is: **"Modeled Completed Haulage Tonnage (Multi-Bay Unconstrained)"**.
- Any comparison to mine capacity must explicitly note:
  > *"The 2,898 TPH haulage discharge rate reflects multi-bay unconstrained tipping upstream of the 1,647 TPH single-pocket crusher bottleneck."*
