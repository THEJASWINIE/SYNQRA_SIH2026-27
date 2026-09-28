# FOG-ORCHESTRATOR 2.0 — DEMO FINAL NUMBERS
## Authoritative Numerical Reference for Demonstration & HMI Display
### Problem Statement SIH26007 — SIH 2026-27

---

### Strict Demonstration Rule
The HMI HUD, operator dashboard, and live demonstration must **NEVER** display a number that the forensic audit rejected. Every displayed metric must match the canonical values verified below:

| UI Field / Metric | Display Value | Display Unit | Applicable Operational Scenario | Physical / Mathematical Basis | Scope & Known Limitations |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **Emergency Safe Speed** | **18.4** | $\text{km/h}$ ($5.12\text{ m/s}$) | $12\text{ m}$ visibility, wet $-8\%$ ramp | $v_{\text{max}} = -a\tau + \sqrt{(a\tau)^2 + 2a R_{\text{avail}}}$ with $a = 2.75\text{ m/s}^2$, $\tau = 0.437\text{ s}$ | Emergency contingency ceiling; full brake application. |
| **Service Operating Speed**| **13.0** | $\text{km/h}$ ($3.61\text{ m/s}$) | $12\text{ m}$ visibility, normal haulage | $v_{\text{max}}$ solved with $a = 1.20\text{ m/s}^2$ service comfort limit | Normal haulage speed to prevent rock spillage. |
| **Clear Weather Speed Limit**| **20.0** | $\text{km/h}$ ($5.56\text{ m/s}$) | Visibility $\ge 25\text{ m}$, clear weather | DGMS Technical Circular 09/2008 regulatory site cap | Hard site regulation ceiling. |
| **Dense Fog Safe Speed** | **0.0** | $\text{km/h}$ ($0.00\text{ m/s}$) | Optical visibility $\le 5.0\text{ m}$ | Available stopping range $R_{\text{avail}} \le 0\text{ m}$ | Vehicle halted in **CONTROLLED STAGING / HOLD**. |
| **Emergency Stopping Distance**| **7.0** | $\text{m}$ | Full stop from $18.4\text{ km/h}$ at $12\text{ m}$ vis | $S_{\text{stop}} = 2.24\text{ m}$ (reaction) $+ 4.76\text{ m}$ (braking) | Requires full mechanical emergency retarding. |
| **Standstill Safety Margin**| **5.0** | $\text{m}$ | All operational scenarios | DGMS Open-cast standoff distance regulation | Mandatory clearance buffer behind obstacles. |
| **Space Headway** | **22.5** | $\text{m}$ | $12\text{ m}$ visibility haul ramp following | $H_{\text{space}} = S_{\text{stop}}(7.0) + S_{\text{base}}(5.0) + L_{\text{truck}}(10.5)$ | Minimum longitudinal vehicle separation. |
| **Crusher Processing Ceiling**| **1647.0** | $\text{TPH}$ | Steady-state continuous haulage | Single tipping pocket, $200.0\text{ s}$ dump slot ($18\text{ VPH} \times 91.5\text{ t}$)| Hard equipment bottleneck ceiling. |
| **Delivered Steady-State TPH**| **1591.4** | $\text{TPH}$ | Level 4 Orchestration in $12\text{ m}$ fog | Continuous 2-hour simulation steady-state ($96.6\%$ util) | Verified across 30 matched seed runs. |
| **Baseline Fog Throughput** | **1171.2** | $\text{TPH}$ | Level 0 Unmanaged in $12\text{ m}$ fog | Conventional haulage with uncoordinated ramp jams | Baseline benchmark ($71.1\%$ crusher utilization). |
| **Delivered Throughput Gain**| **+35.9%** | $\%$ | Level 4 vs Level 0 comparison | $(1591.4 - 1171.2) / 1171.2 \times 100\%$ | Same fleet, route, seeds, horizon, and weather. |
| **Hazardous Ramp Wait Reduction**| **-77.4%** | $\%$ | Level 4 vs Level 1 ramp queue | Ramp wait reduced from $625.4\text{ s} \to 141.6\text{ s}$ | Waiting time relocated to safe shovel bench. |
| **Net Total Cycle Delay Savings**| **-11.6%** | $\%$ ($-82.8\text{ s}$) | Level 4 vs Level 1 round-trip | Net trip delay reduced from $713.6\text{ s} \to 630.8\text{ s}$ | Caused by momentum conservation (shockwave cut). |
| **Local Autonomous Reaction**| **437.1** | $\text{ms}$ ($0.44\text{ s}$) | Statistical P99 local safety loop | Convolution of sensor(25), decision(50), CAN(50), actuator(304) | Canonical safety governor reaction budget. |
| **Fail-Safe Software Reaction**| **52.4** | $\text{ms}$ | Onboard fault / timeout detection | Software fault clamp in discrete 20 Hz governor loop | Software clamp only; vehicle stop requires $2.30\text{ s}$. |
| **V2V Wireless Packet Delivery**| **99.1%** | $\%$ | Physical Semtech SX1278 transceivers | 433 MHz CSS-LoRa bench experiment at $150\text{ m}$ LOS | Bench measured; pit rock shadow unvalidated. |

---

### Strictly Prohibited Display Values
* **DO NOT DISPLAY 3,294 TPH or 2,745 TPH** (Permanently retracted transient flush bursts).
* **DO NOT DISPLAY 77.4% as "Total Mine Waiting Reduction"** (It is ramp hazard relocation; total delay reduces by $11.6\%$).
* **DO NOT DISPLAY 7m stopping distance alongside 1.20 m/s² deceleration** (7m stopping strictly requires $2.75\text{ m/s}^2$).
* **DO NOT DISPLAY "DSSS" as the physical transceiver modulation** (Physical transceivers use CSS-LoRa).
