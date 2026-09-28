# EXPERIMENT E12 — MINE CAPACITY & THROUGHPUT FORENSIC AUDIT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Mine Site Reference:** NMDC Bailadila Deposit-5 (Crushing & Screening Plant)  
**Classification:** Mine Haulage Capacity & Bottleneck Demarcation  
**Evidence Level:** L2 (BEML BH100 Payload) / L3 (NMDC Crusher Spec) / L6 (Industrial Engineering Calculation)  

---

## 1. Forensic Dissection of Historical Production Claims

> [!WARNING]
> **AUDIT CLASSIFICATION OF HISTORICAL METRICS**  
> Early project benchmarks reported an unsustainable throughput of **3,294 TPH**. A forensic audit reveals this was an artifact of a pre-buffered initial queue discharging rapidly at simulation start-up, not a steady-state physical operating rate.

---

## 2. Capacity Classification Hierarchy

| Metric | Historical / Derived Value | True Physical Classification | Formula / Derivation Basis | Steady-State Defensibility |
|:---|:---:|:---|:---|:---:|
| **3,294 TPH** | 3,294 TPH | **Transient Initial Queue Flush** | 6 trucks dumping in 10 minutes: $\frac{6 \times 91.5\text{ t}}{0.167\text{ hr}} = 3,294\text{ TPH}$ | **UNSUSTAINABLE (Artifact)** |
| **1,647 TPH** | 1,647 TPH | **Crusher Maximum Physical Capacity** | 18 dumps/hour at 200s slot cycle: $18 \times 91.5\text{ t} = 1,647\text{ TPH}$ | **AUTHORITATIVE UPPER BOUND** |
| **1,591 TPH** | 1,591 TPH | **FOG-Orchestrator Steady-State** | Measured across 30 seeds with fog pacing (96.6% crusher utilization) | **REALISTIC PRODUCTION RATE** |
| **700.5 VPH** | 700.5 VPH | **Haul Road Free-Flow Cap** | $\frac{3600\text{ s}}{5.14\text{ s headway}}$ at 20 km/h | **THEORETICAL ROAD SATURATION** |

---

## 3. Detailed Parameter Formulations

1. **Crusher Service Bottleneck ($C_{\text{crusher}} = 1,647\text{ TPH}$):**  
   The primary gyratory crusher pocket at Deposit-5 accepts one BH100 dumper at a time. The physical dump cycle consists of:
   - Backing & positioning: 45 s
   - Hydraulic hoist raise & rock dump: 65 s
   - Body down & pull-away: 30 s
   - Safety buffer / dust clearing: 60 s  
   **Total slot duration:** $T_{\text{slot}} = 200\text{ s}$ ($\mu_{\text{crusher}} = 18\text{ dumps/hour}$).  
   With a nominal payload of 91.5 metric tonnes (rated payload of BH100), the maximum sustainable physical feed rate is:
   $$C_{\text{crusher}} = 18\text{ dumps/hour} \times 91.5\text{ tonnes} = 1,647.0\text{ TPH}$$

2. **Why 700.5 VPH Road Capacity Does Not Dictate Production:**  
   A single haul road lane operating at 20 km/h with 28.5 m safe headway could theoretically pass 700.5 vehicles per hour ($700.5 \times 91.5 = 64,095\text{ TPH}$). However, the mine is strictly **crusher-constrained**. Dispatching dumpers at road capacity merely builds a massive, dangerous stationary queue in front of the crusher pocket. FOG-Orchestrator meters road entries to exactly match the 200 s crusher acceptance slot.
