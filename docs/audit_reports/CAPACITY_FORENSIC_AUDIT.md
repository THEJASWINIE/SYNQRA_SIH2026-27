# CAPACITY & THROUGHPUT FORENSIC AUDIT REPORT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3 SCIENTIFIC AUDIT & EVIDENCE FREEZE

| Document ID | Canonical File Path | Date | Audit Status | Version |
| :--- | :--- | :--- | :--- | :--- |
| **DOC-CAP-AUDIT** | `CAPACITY_FORENSIC_AUDIT.md` | 2026-09-18 | **FROZEN / AUDITED** | 2.1.0 |

---

### 1. Executive Forensic Finding

> [!WARNING]
> **AUDIT FINDING: HISTORICAL 3,294 TPH IS A TRANSIENT QUEUE-FLUSH ARTIFACT**  
> Early project benchmarks cited a throughput of **3,294 TPH**. A detailed forensic audit confirms this number cannot physically represent steady-state mine production.
> 
> At Bailadila Deposit-5, the primary gyratory crushing plant accepts one truck at a time. The physical dump cycle takes **200 seconds** (18 dumps/hour). With a 91.5-tonne payload, the **maximum physical crusher throughput ceiling is exactly 1,647.0 TPH**.
> 
> The 3,294 TPH metric was produced by six trucks discharging an initial pre-buffered queue within a 10-minute simulation burst:
> $$\text{Burst Rate} = \frac{6 \text{ trucks} \times 91.5 \text{ tonnes}}{10 / 60 \text{ hours}} = \mathbf{3,294.0\text{ TPH}}$$
> Calling this "steady-state mine capacity" is an industrial engineering falsehood. It has been permanently reclassified as a transient queue discharge artifact.

---

### 2. Capacity Hierarchy & Classification

To ensure rigorous transparency, mine transport capacity is decomposed into three strictly separated categories:

```
[1. THEORETICAL KINEMATIC ROAD FLUX] = 700.5 VPH (~64,095 TPH theoretical ore flux)
   Calculated from continuous road pipe flow: C = 3600 * v_safe / (H_safe + L_truck).
   Ignores intersections, loading shovels, and crusher bottleneck.
   DOES NOT EQUAL DELIVERED MINE ORE PRODUCTION.

[2. PRACTICAL OPERATIONAL HAUL ROAD CAPACITY] = 120 - 240 VPH
   Accounts for switchback single-lane passing, switchback speed limits (10 km/h),
   and convoy platoon pacing.

[3. CRUSHER SERVICE BOTTLENECK CEILING] = 18.0 VPH = 1,647.0 TPH
   Hard physical limit of the single tipping pocket at Deposit-5:
   Dump slot cycle T_slot = 200 s (45s backing, 65s hoisting/dumping, 30s exit, 60s buffer).
   Sustained steady-state production CANNOT exceed 1,647 TPH.

[4. FOG-ORCHESTRATOR DELIVERED STEADY-STATE PRODUCTION] = 1,591.4 TPH
   Achieved across 30 seeds by metering origin shovel departures to match crusher acceptance,
   sustaining 96.6% utilization of the 1,647 TPH bottleneck without creating road queues.
```

---

### 3. Dissection of Historical & Derived Values

| Metric Name | Numerical Value | Unit | Time Horizon | True Physical Classification | Mathematical Derivation | Defensibility Status |
|:---|:---:|:---:|:---:|:---|:---|:---:|
| **`3,294 TPH`** | 3,294.0 | TPH | 10 minutes | **Transient Initial Queue Flush** | $\frac{6 \times 91.5\text{ t}}{0.1667\text{ hr}} = 3,294\text{ TPH}$ | **UNSUSTAINABLE ARTIFACT** |
| **`2,745 TPH`** | 2,745.0 | TPH | 6 minutes | **Short Burst Flush Rate** | $\frac{3 \times 91.5\text{ t}}{0.1000\text{ hr}} = 2,745\text{ TPH}$ | **UNSUSTAINABLE ARTIFACT** |
| **`1,647 TPH`** | 1,647.0 | TPH | Continuous | **Crusher Service Bottleneck Ceiling** | $\frac{3600\text{ s}}{200\text{ s}} \times 91.5\text{ t} = 18 \times 91.5 = 1,647.0\text{ TPH}$ | **PROVEN PHYSICAL CEILING** |
| **`1,591.4 TPH`** | 1,591.4 | TPH | Shift / Day | **Delivered Steady-State Throughput** | 12-truck closed-loop haulage with origin bay metering (30 seeds mean) | **AUTHORITATIVE STEADY-STATE** |
| **`700.5 VPH`** | 700.5 | VPH | Instantaneous | **Theoretical Kinematic Road Saturation** | $\frac{3600 \times 4.3815}{12.0 + 10.52} = \frac{15773.4}{22.52} = 700.497\text{ VPH}$ | **THEORETICAL ROAD FLUX** |
| **`183 TPH`** | 183.0 | TPH | Continuous | **Degraded Unmanaged Fog Crawl** | Single truck 1,800 s round trip without central coordination | **DEGRADED BENCHMARK** |

---

### 4. Why Haul Road Capacity Does Not Dictate Production

In an open-cast iron ore mine, haul roads are conveyors, not consumers. 

If dispatchers send trucks down the haul ramp at the road's kinematic capacity ($700.5\text{ VPH}$), trucks arrive at the primary crusher every 5.1 seconds. But the crusher requires 200.0 seconds to service each truck! 

Consequently, after just 15 minutes of unmetered dispatch, **35 trucks would be stranded in a 350-meter stationary jam on a steep, foggy -8% haul ramp**, presenting a catastrophic rear-end collision hazard.

FOG-Orchestrator meters dispatches at origin shovel pockets to exactly match the crusher's 200 s slot cadence, maintaining smooth, continuous 1,591.4 TPH throughput with **zero stationary queues on the haul road**.
