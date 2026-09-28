# PHASE 7.3.4 — ATTACK #9: CRUSHER 200-SECOND SERVICE TIME AUDIT & SENSITIVITY
**Module:** Pit Bottleneck & Crushing Plant Service Channel  
**Dataset:** `data/phase7_3_4_crusher_sensitivity.csv`  
**Classification:** **MODELED CRUSHER SERVICE TIME (YELLOW / NOT FIELD SCADA)**  

---

## 1. Provenance Investigation of the 200-Second Dump Cycle

The project bases its primary physical ceiling on a $200.0\text{ s}$ truck dump cycle at the primary gyratory crusher pocket:
$$C_{\text{crusher}} = \left(\frac{3,600\text{ s/hr}}{200.0\text{ s/truck}}\right) \times 91.5\text{ tonnes} = 18.0\text{ trucks/hr} \times 91.5\text{ t} = \mathbf{1,647.0\text{ TPH}}$$
The hostile audit investigated whether $200.0\text{ s}$ is a measured NMDC field value:
1. **Is it derived from NMDC SCADA pit weight-scale telemetry?** **NO.** Live weighbridge and dumping timestamps from NMDC Deposit 5 were not accessible.
2. **Is it an OEM equipment specification?** **PARTIALLY.** Heavy primary gyratory crushers (e.g., FLSmidth / Metso 54-75 or 60-89 classes commonly installed in Indian iron ore mines) have rated mechanical capacities of $2,000\text{--}3,000\text{ TPH}$ when continuously fed. However, single-truck dumping slots are limited by maneuvering, tipping, and hopper drawdown.
3. **What is the exact origin?**  
   It is an **ENGINEERING TIME-MOTION MODEL**:
   - Backing into tipping pocket: $35\text{ s}$
   - Hydraulic body hoist raise and ore discharge: $65\text{ s}$
   - Body down, weighment, and exit clearance: $40\text{ s}$
   - Grizzly feeder clearing and pocket reset buffer: $60\text{ s}$
   - Total: $35 + 65 + 40 + 60 = \mathbf{200.0\text{ seconds}}$.

**Formal Renaming:**  
$$\mathbf{MODELED\;CRUSHER\;SERVICE\;TIME = 200.0\;s\;(NOT\;FIELD\;SCADA)}$$

---

## 2. Sensitivity of Crusher Ceiling and Relative Throughput Gain

The audit evaluated whether the project's headline $+35.88\%$ ($+35.9\%$) throughput improvement over baseline Level 0 is fragile or sensitive to the chosen $200\text{ s}$ cycle time. Dump cycle time was swept across $[120, 300]\text{ seconds}$:

| Dump Cycle ($T_{\text{dump}}$) | Crusher Ceiling (VPH) | Crusher Ceiling (TPH) | Baseline Level 0 (TPH) | Coordinated Level 4 (TPH) | Absolute Gain (TPH) | Relative Gain (%) | Gain Survives? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **120.0 s** (Rapid Twin Slot) | $30.00\text{ VPH}$ | **2,745.0 TPH** | $1,951.7\text{ TPH}$ | **2,651.7 TPH** | $+700.0\text{ TPH}$ | **+35.87%** | **YES** |
| **150.0 s** (High-Speed Dump) | $24.00\text{ VPH}$ | **2,196.0 TPH** | $1,561.4\text{ TPH}$ | **2,121.3 TPH** | $+560.0\text{ TPH}$ | **+35.87%** | **YES** |
| **180.0 s** (Bailadila Benchmark) | $20.00\text{ VPH}$ | **1,830.0 TPH** | $1,301.1\text{ TPH}$ | **1,767.8 TPH** | $+466.7\text{ TPH}$ | **+35.87%** | **YES** |
| **200.0 s** (Canonical Baseline) | $18.00\text{ VPH}$ | **1,647.0 TPH** | $1,171.2\text{ TPH}$ | **1,591.4 TPH** | $+420.2\text{ TPH}$ | **+35.88%** | **YES** |
| **220.0 s** (Slight Delay) | $16.36\text{ VPH}$ | **1,497.3 TPH** | $1,064.6\text{ TPH}$ | **1,446.4 TPH** | $+381.8\text{ TPH}$ | **+35.87%** | **YES** |
| **250.0 s** (Congested Pocket) | $14.40\text{ VPH}$ | **1,317.6 TPH** | $936.8\text{ TPH}$ | **1,272.8 TPH** | $+336.0\text{ TPH}$ | **+35.87%** | **YES** |
| **300.0 s** (Severe Hopper Choke) | $12.00\text{ VPH}$ | **1,098.0 TPH** | $780.7\text{ TPH}$ | **1,060.7 TPH** | $+280.0\text{ TPH}$ | **+35.87%** | **YES** |

---

## 3. Hostile Audit Conclusion

1. **Why Does the +35.88% Gain Survive Identically Across All Dump Times?**  
   Because the throughput improvement is driven by the **UTILIZATION EFFICIENCY** of the bottleneck, not the absolute magnitude of the bottleneck:
   - In uncoordinated manual operations (Level 0), random arrival gaps and stop-and-go ramp shockwaves cause the crusher to sit starved and idle for an average of $1,040.2\text{ s/hr}$, capping utilization at **$71.1\%$**.
   - In Level 4, origin-staged dispatch spaces truck arrivals at the exact service cadence, reducing crusher idle starvation to $122.4\text{ s/hr}$ and raising utilization to **$96.6\%$**.
   - The ratio of delivered production is:
     $$\frac{\text{Throughput}_{\text{L4}}}{\text{Throughput}_{\text{L0}}} = \frac{0.966 \times C_{\text{crusher}}}{0.711 \times C_{\text{crusher}}} = \frac{0.966}{0.711} = \mathbf{1.3587} \implies \mathbf{+35.87\%}$$
   - The $+35.88\%$ relative productivity gain is mathematically invariant to the absolute dump time.
2. **Provenance Mandate:**  
   The $1,647.0\text{ TPH}$ ceiling must be clearly presented as a **MODELLED SERVICE CEILING**, not a certified field sensor measurement.
