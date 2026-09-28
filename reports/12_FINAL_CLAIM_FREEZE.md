# PHASE 7.3.3 — FINAL CLAIM FREEZE & SCIENTIFIC AUDIT
**Project:** FOG-ORCHESTRATOR 2.0 — SIH 2026-27 / SIH26007  
**Module:** Definitive Scientific Claims  
**Status:** AUDITED & FROZEN

---

## 1. Structure of Claims
All claims are classified into four strict categories:
1. **GREEN:** Fully demonstrated within prototype, laboratory bench, and deterministic simulation scope. Ready for technical presentation and evaluator cross-examination.
2. **YELLOW:** Credibly supported by engineering theory, literature, and surrogate bench testing, but dependent on uncalibrated machine parameters.
3. **OPEN:** Requires physical on-chassis field testing at NMDC Bailadila Deposit 5 to resolve.
4. **RED:** Disproven, mathematically inconsistent, or misleading claims that are permanently retracted.

---

## 2. Definitive Claims by Category

### GREEN CLAIMS (Demonstrated within Prototype / Simulation Scope)
1. **Physical Force Derivation:** Net emergency deceleration on an $-8\%$ ramp is derived from first principles as $2.7856\text{ m/s}^2$ (canonical $165.5\text{ t}$, $C_{\text{rr}}=0.025$, $g=9.80665\text{ m/s}^2$) and $2.7466\text{ m/s}^2$ (legacy $165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81\text{ m/s}^2$), clamped by tire adhesion ($566.2\text{ kN}$).
2. **Two-State Safety Model:** Separates moving travel margin ($S_{\text{stop}}(v) + S_{\text{base}} \le R_{\text{effective}}$ for $v>0$) from standstill staging ($v \equiv 0.0\text{ m/s}$, $S_{\text{stop}} \equiv 0\text{ m}$, $D_{\text{sight}} = V_{\text{fog}}$ for $V_{\text{fog}} \le 5.0\text{ m}$), eliminating false margin violation errors during dense fog blindout.
3. **Independent Quadratic Closed-Form Root:** Confirms safe speed at $12\text{ m}$ visibility with P99 latency ($\tau = 437.1\text{ ms}$) is $5.1158\text{ m/s}$ ($18.42\text{ km/h}$) under emergency deceleration ($S_{\text{stop}} = 7.0004\text{ m}$), and $3.6078\text{ m/s}$ ($12.99\text{ km/h}$) under service deceleration ($S_{\text{stop}} = 7.0000\text{ m}$).
4. **Space Headway & Road Flux:** Derives safe space headway at $12\text{ m}$ as $h_{\text{space}} = 22.5200\text{ m}$, yielding theoretical kinematic road flow of $817.8\text{ VPH}$ (emergency) and $587.2\text{ VPH}$ (service).
5. **Modeled Crusher Ceiling:** Confirms physical bottleneck ceiling of single tipping pocket with $200.0\text{ s}$ dump cycle is $1,647.0\text{ TPH}$ ($18.0\text{ trucks/hr} \times 91.5\text{ t}$).
6. **Sustained Steady-State Throughput:** Confirms Level 4 orchestration achieves $1,591.4\text{ TPH}$ ($96.6\%$ crusher utilization) across extended $1,800\text{ s}$, $3,600\text{ s}$, and $7,200\text{ s}$ horizons with warmup excluded.
7. **Baseline Throughput Comparison:** Confirms Level 4 achieves a $+35.88\%$ ($+35.9\%$) throughput gain over uncoordinated baseline Level 0 ($1,171.2\text{ TPH}$) under identical fleet, route, seed, weather, and crusher conditions.
8. **Hazardous Ramp Queue Relocation:** Confirms a $-77.36\%$ reduction in hazardous ramp queue waiting ($625.4\text{ s} \to 141.6\text{ s}$), moving waiting to safe shovel turnaround bays ($+401.0\text{ s}$).
9. **Net Cycle Delay Reduction:** Confirms a $-11.60\%$ ($-82.8\text{ s}$) net reduction in round-trip cycle delay directly caused by the elimination of ramp stop-start accordion waves ($4.8 \to 0.9$ stops/trip).
10. **Safety Invariant Preservation:** Confirms $v_{\text{command\_actual}} \le v_{\text{safe}}$ with zero violations across $1,200$ synthetic fault injection trials spanning stale, duplicate, replayed, and adversarial commands.
11. **Direct V2V Radio Latency:** Confirms physical dual-ESP32 SX1278 CSS-LoRa bench measurement achieves mean latency of $41.2\text{ ms}$ and P99 latency of $48.6\text{ ms}$ at $150\text{ m}$ LOS with $99.1\%$ PDR.
12. **Gateway Relay Latency:** Confirms physical ESP32 gateway serial-to-Wi-Fi relay achieves mean latency of $82.4\text{ ms}$ and P99 latency of $105.2\text{ ms}$.

---

### YELLOW CLAIMS (Supported by Literature / Bench / Surrogate Data)
1. **BEML BH100 Actuator Build-Up Delay:** Actuator response is modeled as $250.0\text{ ms}$ nominal and $350.0\text{ ms}$ worst-case based on heavy pneumatic literature, supported by an automotive electro-hydraulic surrogate bench (mean $200.16\text{ ms}$, P99 $237.1\text{ ms}$). Actual BEML BH100 valve timing remains unmeasured.
2. **Service Deceleration ($1.20\text{ m/s}^2$):** Based on open-cast haulage literature standards to prevent rock spillage; actual driver deceleration behavior on wet hematite remains unmeasured.
3. **DSSS / Gold Code Processing Gain:** The $+12.0\text{ dB}$ jamming margin improvement is demonstrated via software simulation modeling; physical transmission utilized commercial Semtech SX1278 chirp spread spectrum (CSS).
4. **Haul Road Rolling Resistance ($C_{\text{rr}} = 0.025$):** Literature value from SME Mining Engineering Handbook for unpaved unlit haul roads.

---

### OPEN CLAIMS (Requires Physical Field Validation at Bailadila)
1. **Measured BH100 Deceleration:** Decelerometer / GPS speed traces on a live loaded BEML BH100 descending the Deposit 5 ramp have not been recorded.
2. **Chassis J1939 CAN Bus Validation:** Physical sniffing of PGN 61444 and PGN 65265 on a live BH100 chassis harness requires NMDC pit access.
3. **Pit Topographic RF Multipath:** Real RF propagation, knife-edge diffraction over iron ore pit benches, and hematite dust attenuation at Deposit 5 have not been physically surveyed.

---

### RED CLAIMS (Permanently Retracted & Prohibited)
1. **74,828.7 TPH Headline:** RETRACTED. Converting single-lane road pipe capacity into mine production is physically invalid due to the crusher bottleneck ($1,647.0\text{ TPH}$).
2. **3,294.0 TPH & 2,745.0 TPH Throughput:** RETRACTED. These were transient initial queue-flush artifacts that do not represent steady-state production.
3. **"77.4% Total Waiting Reduction":** RETRACTED. The $77.4\%$ reduction applies strictly to hazardous ramp waiting; net cycle delay reduction is $-11.60\%$.
4. **"100% Real-World Safety":** RETRACTED. The system guarantees mathematical clamping ($v_{\text{command}} \le v_{\text{safe}}$) across tested failure modes; unmodeled mechanical or geotechnical failures cannot be claimed.
5. **"Bailadila Field Validated":** RETRACTED. All parameters are simulation models, bench measurements, or OEM specifications.
