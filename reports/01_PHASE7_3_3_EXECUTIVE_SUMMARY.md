# PHASE 7.3.3 — EXECUTIVE SUMMARY: FINAL PHYSICAL DERIVATION & SAFETY-MARGIN CLOSURE
**Project:** FOG-ORCHESTRATOR 2.0 — SIH 2026-27 / SIH26007  
**Mine Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Chhattisgarh  
**Vehicle Reference:** BEML BH100 (100-Tonne Class Rigid Rear Dump Truck)  
**Status:** COMPLETE & FROZEN  

---

## 1. Purpose of Phase 7.3.3
Phase 7.3.3 executes the final forensic reconciliation and parameter freeze for FOG-ORCHESTRATOR 2.0. Following the numerical verification in Phase 7.3.2, this phase addresses the remaining physical and semantic questions before the final model lock:
1. **Physical Derivation of Emergency Deceleration:** First-principles longitudinal force balance deriving $2.7856\text{ m/s}^2$ (canonical $165.5\text{ t}$, $C_{\text{rr}}=0.025$, $g=9.80665\text{ m/s}^2$) and reconciling legacy $2.7466\text{ m/s}^2$ ($165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81\text{ m/s}^2$).
2. **Brake Force Forensic Distinction:** Explicitly distinguishing total gross mechanical rim braking force ($550\text{ kN}$ at the tire-road interface) from caliper normal clamping force.
3. **Two-State Safety Model Formulation:** Resolving the apparent dense-fog Monte Carlo contradiction by separating **State 1 (Moving, $v>0$)** where $S_{\text{stop}}(v) + S_{\text{margin}} \le R_{\text{effective}}$ from **State 2 (Staged/Stopped, $v=0$)** where $S_{\text{stop}} \equiv 0\text{ m}$ and line-of-sight clearance is $D_{\text{sight}} = R_{\text{effective}}$.
4. **10,000-Sample Monte Carlo Stress Test:** Executing 10,000 randomized iterations under the Two-State Model, proving zero margin violations.
5. **Reframing Road Flow & Crusher Bottleneck:** Retracting $74,828.7\text{ TPH}$ headline from road flow (stating $817.8\text{ VPH}$ emergency / $587.2\text{ VPH}$ service) and affirming that mine haulage is strictly bounded by the modeled crusher ceiling ($1,647.0\text{ TPH}$).
6. **Causal Shockwave Delay Validation:** Confirming that Level 4 dynamic staging eliminates ramp accordion shockwaves ($4.8 \to 0.9$ stops/trip), saving $82.8\text{ s}$ net trip delay ($-11.60\%$).

---

## 2. Executive Summary of Audited Parameters

| Parameter | Audited Value | Physical Status | Provenance Level |
|:---|:---:|:---:|:---|
| **Gross Vehicle Weight (GVW)** | $165,500\text{ kg}$ ($165.5\text{ t}$) | **GREEN** | OEM Datasheet ($74.0\text{ t}$ tare + $91.5\text{ t}$ payload) |
| **Gross Rim Braking Force ($F_{\text{rim}}$)** | $550,000\text{ N}$ ($550\text{ kN}$) | **GREEN** | Mechanical design rating clamped by adhesion ($566.2\text{ kN}$) |
| **Emergency Deceleration (Canonical)** | $2.7856\text{ m/s}^2$ | **GREEN** | First-principles force balance on $-8\%$ ramp |
| **Emergency Deceleration (Legacy Model)** | $2.7466\text{ m/s}^2$ | **GREEN** | First-principles force balance ($165.0\text{ t}$, $C_{\text{rr}}=0.020$) |
| **Field Measured Deceleration** | **UNAVAILABLE** | **OPEN** | Requires physical pit decelerometer trial at Bailadila |
| **Service Deceleration ($a_{\text{service}}$)** | $1.2000\text{ m/s}^2$ | **YELLOW** | Operational comfort limit (prevents rock spillage) |
| **Local P99 Reaction Latency ($\tau_{\text{local}}$)** | $0.4371\text{ s}$ ($437.1\text{ ms}$) | **GREEN** | Bench-measured CAN/RF/surrogate + model budget |
| **Emergency Safe Speed @ 12m ($v_{\text{safe}}$)** | $5.1158\text{ m/s}$ ($18.42\text{ km/h}$) | **GREEN** | Closed-form quadratic root ($S_{\text{stop}}=7.0004\text{ m}$) |
| **Service Safe Speed @ 12m ($v_{\text{safe}}$)** | $3.6078\text{ m/s}$ ($12.99\text{ km/h}$) | **GREEN** | Closed-form quadratic root ($S_{\text{stop}}=7.0000\text{ m}$) |
| **Base Standstill Safety Margin ($S_{\text{base}}$)** | $5.0000\text{ m}$ | **GREEN** | DGMS metalliferous open-cast standoff standard |
| **Space Headway @ 12m ($h_{\text{space}}$)** | $22.5200\text{ m}$ | **GREEN** | $S_{\text{stop}}(7.0\text{m}) + S_{\text{margin}}(5.0\text{m}) + L_{\text{truck}}(10.52\text{m})$ |
| **Dense Fog Operating State ($3\text{--}5\text{ m}$)** | **HOLD ($v_{\text{safe}} = 0.0$)** | **GREEN** | Two-State Model: Controlled staging, $0\text{ TPH}$ flow |
| **Theoretical Road Flow (Emergency)** | $817.8\text{ VPH}$ | **GREEN** | Pure kinematic pipe flux ($(v/h)\times 3600$) |
| **Modeled Crusher Ceiling** | $1,647.0\text{ TPH}$ | **GREEN** | $200\text{ s}$ single pocket slot $\times 91.5\text{ t}$ ($18\text{ VPH}$) |
| **Sustained Steady-State Throughput** | $1,591.4\text{ TPH}$ | **GREEN** | $96.6\%$ crusher utilization over 2-hour horizon |
| **Baseline Level 0 Throughput** | $1,171.2\text{ TPH}$ | **GREEN** | Uncoordinated visual crawl |
| **Net Throughput Improvement** | **$+35.88\%$ ($+35.9\%$)** | **GREEN** | Identical routes, seeds, weather, and crusher model |
| **Ramp Queue Relocation** | **$-77.36\%$** | **GREEN** | Ramp wait: $625.4\text{ s} \to 141.6\text{ s}$; staging: $+401.0\text{ s}$ |
| **Net Trip Delay Reduction** | **$-11.60\%$ ($-82.8\text{ s}$)** | **GREEN** | Trip delay: $713.6\text{ s} \to 630.8\text{ s}$ via shockwave removal |
| **Safety Invariant Violations** | **0 in tested set** | **GREEN** | $v_{\text{command}} \le v_{\text{safe}}$ verified under 12 fault modes |
| **Monte Carlo Safety Margin Violations** | **0 in 10,000** | **GREEN** | Two-State Model yields zero moving/staged violations |

---

## 3. Key Forensic Retractions and Reframings
1. **Retraction of 74,828.7 TPH Headline:** Mathematical conversion of single-lane pipe capacity ($817.8\text{ VPH} \times 91.5\text{ t}$) is permanently retracted as an operational mine production claim. Road flow is reported solely in **$817.8\text{ VPH}$**, while mine capacity is strictly governed by the **$1,647.0\text{ TPH}$ modeled crusher ceiling**.
2. **Retraction of Total Waiting Time Reduction:** Claims of "77.4% total waiting reduction" are retracted. The $77.36\%$ reduction applies strictly to **hazardous ramp queue waiting** ($625.4\text{ s} \to 141.6\text{ s}$). Total cycle delay improves by **$-11.60\%$ ($-82.8\text{ s}$)**.
3. **Classification of Crusher Capacity:** $1,647.0\text{ TPH}$ is explicitly labeled as a **MODELED CRUSHER SERVICE CEILING**, based on a $200\text{ s}$ single-truck dump slot, not field-measured SCADA telemetry.
4. **Resolution of Monte Carlo Clearance Margin:** The apparent discrepancy between positive clearance margins ($+3.0018\text{ m}$) and $3\text{--}5\text{ m}$ dense fog is resolved by formulating the Two-State Safety Model: stopped vehicles require $0\text{ m}$ forward stopping distance, with $3\text{--}5\text{ m}$ representing standstill sight distance.
