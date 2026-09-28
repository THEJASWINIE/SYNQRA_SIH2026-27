# STAGE 5.2: PHYSICAL COMMUNICATION FAILURE & LOCAL SAFETY INVARIANT
**Robustness Testing of LoRa V2V, Gateway Disconnect, Wi-Fi Drop, and Central Twin Outage**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Haulage)  
**Status:** VALIDATED EVIDENCE — TIER-1 LOCAL GOVERNOR INVARIANT STRICTLY PRESERVED  

---

## 1. NMDC Problem Statement Alignment

This experiment validates NMDC Problem Statement Requirements:
- **Requirement 11:** *Evaluate robust V2V / V2I communications in deep pit mine environments.*
- **Requirement 1:** *Ensure unconditional safety of dumper operations even during communication link degradation.*

Deep open-cast iron ore pits (such as NMDC Bailadila Deposit 5, featuring vertical pit walls $>200\text{ m}$) are severe RF multipath environments. Direct line-of-sight Wi-Fi or cellular links frequently experience signal shadows, high packet drops, or complete blackouts behind benches.

FOG-ORCHESTRATOR’s frozen architecture enforces a strict **three-tier safety hierarchy**:
1. **Tier 1 (Local Onboard Governor):** Highest authority. Executes locally on the dumper’s onboard computer / ESP32. Evaluates vehicle dynamics, local friction, and optical sight distance.
2. **Tier 2 (Road / Infrastructure Coordination):** Peer-to-peer LoRa V2V.
3. **Tier 3 (Central Digital Twin & Fleet Intelligence):** LoRa Gateway $\to$ Wi-Fi $\to$ FastAPI $\to$ TwinStateStore.

### The Immutable Architectural Invariant:
$$\mathbf{v_{\text{command}} \le v_{\text{safe}} \quad \forall t, \forall \text{ conditions}}$$
**Central dispatch, gateway state, or remote optimization can NEVER override the vehicle's Tier-1 local safety governor.** If communication with the central system or between vehicles fails, the local vehicle safety governor remains fully authoritative.

---

## 2. Experimental Test Matrix & Fail-Safe Modes

The experiment evaluated 12 discrete communication stress cases using `run_communication_safety_experiment(veh_cfg)`. Data is logged in [`docs/STAGE5_2_COMMUNICATION_FAILURES.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_COMMUNICATION_FAILURES.csv):

| # | Communication Stress Injection | Visibility | Packet Loss | Telemetry Age | Channel State | Central Target ($v_{\text{dispatch}}$) | Safe Limit ($v_{\text{safe}}$) | Commanded ($v_{\text{cmd}}$) | Active Fallback Strategy | Invariant Preserved? | Safety Violations | Local Authority Held? |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
| **1** | **Nominal LoRa V2V Link** | $12.0\text{ m}$ | $0\%$ | $50\text{ ms}$ | `V2V_ONLINE` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `NOMINAL_GOVERNED` | **PASS** | **0** | **YES** |
| **2** | **Moderate Packet Loss (25%)** | $12.0\text{ m}$ | $25\%$ | $200\text{ ms}$ | `DEGRADED` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `HEADWAY_EXPANSION` | **PASS** | **0** | **YES** |
| **3** | **Heavy Packet Loss (50%)** | $12.0\text{ m}$ | $50\%$ | $400\text{ ms}$ | `DEGRADED` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `HEADWAY_EXPANSION` | **PASS** | **0** | **YES** |
| **4** | **Severe Packet Loss (75%)** | $12.0\text{ m}$ | $75\%$ | $800\text{ ms}$ | `DEGRADED` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `HEADWAY_EXPANSION` | **PASS** | **0** | **YES** |
| **5** | **V2V Total Loss Timeout** | $12.0\text{ m}$ | $100\%$ | $4.50\text{ s}$ | `OFFLINE` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `LOCAL_VISUAL_SIGHT` | **PASS** | **0** | **YES** |
| **6** | **Stale Vehicle State** | $12.0\text{ m}$ | $0\%$ | $3.20\text{ s}$ | `STALE` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$3.00\text{ m/s}$** | `CONSERVATIVE_CLAMP` | **PASS** | **0** | **YES** |
| **7** | **Replay / Duplicate Packet** | $12.0\text{ m}$ | $0\%$ | $50\text{ ms}$ | `REJECTED_REPLAY` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$3.00\text{ m/s}$** | `CONSERVATIVE_CLAMP` | **PASS** | **0** | **YES** |
| **8** | **LoRa Gateway Disconnect** | $12.0\text{ m}$ | $100\%$ | $5.00\text{ s}$ | `GATEWAY_DOWN` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `LOCAL_VISUAL_SIGHT` | **PASS** | **0** | **YES** |
| **9** | **Wi-Fi Link Disconnect** | $12.0\text{ m}$ | $100\%$ | $6.00\text{ s}$ | `WIFI_DOWN` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `LOCAL_VISUAL_SIGHT` | **PASS** | **0** | **YES** |
| **10** | **Central Twin Crash / Loss** | $12.0\text{ m}$ | $100\%$ | $10.00\text{ s}$ | `CENTRAL_OFFLINE` | $8.00\text{ m/s}$ | $4.79\text{ m/s}$ | **$4.79\text{ m/s}$** | `LOCAL_VISUAL_SIGHT` | **PASS** | **0** | **YES** |
| **11** | **Central Unsafe Override** | $12.0\text{ m}$ | $0\%$ | $50\text{ ms}$ | `V2V_ONLINE` | **$15.00\text{ m/s}$** | **$4.79\text{ m/s}$** | **$4.79\text{ m/s}$** | `NOMINAL_GOVERNED` | **PASS** | **0** | **YES** |
| **12** | **Zero Visibility Comm Loss** | **$5.0\text{ m}$** | $100\%$ | $5.00\text{ s}$ | `OFFLINE` | $8.00\text{ m/s}$ | **$0.00\text{ m/s}$** | **$0.00\text{ m/s}$** | `LOCAL_VISUAL_SIGHT` | **PASS** | **0** | **YES** |

---

## 3. Analysis of Critical Failure Modes

### 3.1 Case 11: Central Dispatch Attempts Malicious / Erroneous Overspeed Override
- **Scenario:** The central orchestrator or dispatch server experiences a software malfunction or erroneous operator input, commanding $v_{\text{dispatch}} = 15.00\text{ m/s}$ ($54\text{ km/h}$) on an $8\%$ downhill grade in $12\text{ m}$ dense fog.
- **Governor Response:** The onboard Tier-1 governor evaluates local vehicle physics ($m = 165.5\text{ t}$, $\mu_{\text{safe}} = 0.282$, $V = 12\text{ m}$) and computes $v_{\text{safe}} = 4.79\text{ m/s}$.
- **Outcome:** The governor executes $v_{\text{command}} = \min(15.00, 4.79) = 4.79\text{ m/s}$. The central overspeed command is unconditionally rejected. Safety violations $= 0$.

### 3.2 Cases 5 & 10: Complete Loss of V2V and Central Digital Twin Outage
- **Scenario:** High pit walls block all radio communications; both direct V2V and central telemetry links go dark for $>4.5\text{ s}$.
- **Governor Response:** The vehicle transitions from collaborative headway control to `LOCAL_VISUAL_SIGHT_FALLBACK`.
- **Outcome:** The vehicle relies strictly on onboard optical sensors and conservative dead-reckoning. Headway margins are expanded by $50\%$. If optical sight distance cannot guarantee stopping clearance (e.g., Case 12 at $5\text{ m}$ fog), the vehicle comes to a complete, controlled standstill ($v_{\text{command}} = 0.00\text{ m/s}$).

### 3.3 Cases 6 & 7: Stale Telemetry and Replay Attack Injection
- **Scenario:** Out-of-order or stale telemetry packets (age $>2.0\text{ s}$) are received from a preceding vehicle.
- **Governor Response:** The packet sequence monitor rejects replayed frames (`REJECTED_REPLAY`) and clamps vehicle speed to a conservative crawl ($3.00\text{ m/s}$) to guarantee stopping safety until fresh telemetry is re-established.

---

## 4. Scientific Verdict

Across all 12 failure modes:
1. **The Safety Invariant ($v_{\text{command}} \le v_{\text{safe}}$) held with $100\%$ compliance (0 violations).**
2. **Local onboard safety never surrendered authority to central infrastructure.**
3. **The system demonstrated graceful, deterministic fail-safe degradation.**
