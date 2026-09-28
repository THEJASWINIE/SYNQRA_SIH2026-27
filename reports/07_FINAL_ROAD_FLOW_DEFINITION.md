# PHASE 7.3.3 — FINAL ROAD FLOW DEFINITION & CRUSHER BOTTLENECK AUDIT
**Module:** Capacity & Flow Hierarchy  
**Dataset:** `data/final_road_flow.csv`  
**Status:** RECONCILED & REFOCUSED (GREEN)

---

## 1. Audit of the 74,828.7 TPH Metric
In earlier versions of the project, single-lane pipe flow was multiplied by truck payload to yield:
$$C_{\text{flow\_legacy}} = 817.8\text{ VPH} \times 91.5\text{ tonnes} = \mathbf{74,828.7\text{ TPH}}$$
The Phase 7.3.3 audit mandates:
> *"Audit whether the TPH conversion should exist at all. Retain theoretical road flow = 817.8 VPH, but avoid headline 74,828.7 TPH because crusher capacity is only 1,647 TPH. If retained in a dataset, label THEORETICAL PIPE-FLOW EQUIVALENT. NEVER mine production, mine capacity, or expected throughput."*

---

## 2. Rigorous Separation of Kinematic Road Flow vs Production

To prevent confusion among evaluators and mining engineers, FOG-ORCHESTRATOR 2.0 establishes a strict three-tier capacity hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: THEORETICAL KINEMATIC ROAD PIPE-FLOW (ROAD LEVEL)   │
│ Single-lane continuous bumper-to-bumper vehicle flux        │
│ Capacity: 817.8 VPH (Emergency) / 587.2 VPH (Service)       │
│ Unit: Vehicles Per Hour (VPH) ONLY                          │
└──────────────────────────────┬──────────────────────────────┘
                               │ Feeds into
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: PRIMARY GYRATORY CRUSHER CEILING (BOTTLENECK LEVEL) │
│ Single tipping pocket, 200s dump cycle = 18 trucks/hr       │
│ Capacity: 1,647.0 TPH (MODELED CRUSHER SERVICE CEILING)     │
│ Unit: Tonnes Per Hour (TPH)                                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ Delivers
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: SUSTAINED STEADY-STATE PRODUCTION (FLEET LEVEL)     │
│ Level 4 dynamic staging achieves 96.6% crusher utilization  │
│ Delivered Throughput: 1,591.4 TPH (17.4 trips/hr)           │
│ Unit: Tonnes Per Hour (TPH)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Audited Flow Metrics Across Visibility Levels

| Regime / Metric | Velocity ($v$) | Headway ($h_{\text{space}}$) | Theoretical Road Flow | Production Role | Formal Label | Status |
|:---|:---:|:---:|:---:|:---|:---|:---:|
| **Emergency Kinematic Flow @ 12m** | $5.1158\text{ m/s}$ ($18.42\text{ km/h}$) | $22.5200\text{ m}$ | **817.8 VPH** | Theoretical Road Limit | THEORETICAL PIPE-FLOW (VPH) | **GREEN** |
| **Service Kinematic Flow @ 12m** | $3.6734\text{ m/s}$ ($13.22\text{ km/h}$) | $22.5200\text{ m}$ | **587.2 VPH** | Routine Operating Limit | THEORETICAL PIPE-FLOW (VPH) | **GREEN** |
| **Legacy Kinematic Flow @ 12m** | $4.3815\text{ m/s}$ ($15.77\text{ km/h}$) | $22.5200\text{ m}$ | **700.4 VPH** | Midpoint Benchmark | THEORETICAL PIPE-FLOW (VPH) | **GREEN** |
| **Crusher Single Pocket Ceiling** | — | — | **18.0 VPH** | Physical Mine Bottleneck | MODELED CRUSHER SERVICE CEILING | **GREEN** |
| **Crusher Production Ceiling** | — | — | **1,647.0 TPH** | Physical Mine Bottleneck | MODELED CRUSHER SERVICE CEILING | **GREEN** |
| **Delivered Steady-State (L4)** | Variable ($0\text{--}5.56\text{ m/s}$) | Dynamic | **17.4 VPH** | Sustained Mine Production | DELIVERED STEADY-STATE TPH | **GREEN** |
| **Delivered Steady-State (L4 TPH)**| Variable | Dynamic | **1,591.4 TPH** | Sustained Mine Production | DELIVERED STEADY-STATE TPH | **GREEN** |
| **Legacy 74,828.7 TPH Headline** | — | — | — | Invalid Headline | **RETRACTED FROM CLAIMS** | **RED** |

---

## 4. Crusher Service Ceiling Derivation
The primary gyratory crusher at Deposit 5 has a single tipping pocket. The complete service cycle per truck comprises:
1. Backing into tipping pocket: $35.0\text{ s}$
2. Hydraulic hoist raise and ore discharge: $65.0\text{ s}$
3. Bed lower, weighment, and egress clearance: $40.0\text{ s}$
4. Grizzly feeder clearing and pocket reset buffer: $60.0\text{ s}$
$$\text{Total Service Time } (T_{\text{dump}}) = 35 + 65 + 40 + 60 = \mathbf{200.0\text{ s/truck}}$$

The maximum theoretical capacity of this service channel is:
$$\text{Service Frequency } = \frac{3,600\text{ s/hr}}{200.0\text{ s/truck}} = \mathbf{18.0\text{ trucks/hr}} \quad (18\text{ VPH})$$
With nominal payload $P = 91.5\text{ tonnes}$:
$$\text{Crusher Bottleneck Ceiling} = 18.0 \times 91.5\text{ t} = \mathbf{1,647.0\text{ TPH}}$$

**Classification:**  
This value is formally designated as **MODELED CRUSHER SERVICE CEILING**, based on standardized equipment time-motion cycles, rather than measured pit sensor telemetry.

---

## 5. Audit Conclusion
1. $74,828.7\text{ TPH}$ is **permanently retracted** as a headline or production number.
2. Road flow is strictly quoted as **$817.8\text{ VPH}$** (emergency kinematic flow) and **$587.2\text{ VPH}$** (routine service flow).
3. The true mine production capacity is bounded by the crusher at **$1,647.0\text{ TPH}$**.
4. Level 4 orchestration achieves **$1,591.4\text{ TPH}$**, representing **$96.6\%$** of the crusher ceiling.
