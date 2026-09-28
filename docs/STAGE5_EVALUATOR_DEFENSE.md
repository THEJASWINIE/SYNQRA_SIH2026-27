# STAGE 5: HOSTILE EVALUATOR DEFENSE & ATTACK SCRIPTS
**SIH 2026-27 — NMDC Bailadila Haulage Fog Stress Problem Statement**  
**Role:** Lead Simulation / Research Engineer, FOG-ORCHESTRATOR 2.0  
**Status:** COMPLETE & FIELD-READY

---

## 1. Primary Defense Axiom: The Lexicographic Safety Invariant

When presenting to evaluators, mining engineers, and safety directors, maintain this unwavering priority hierarchy:

```
                  ┌──────────────────────────────────────────────┐
                  │ 1. TIER-1 SAFETY FEASIBILITY (SOVEREIGN)     │
                  │    v_actual <= v_safe(R_v, mu, theta)        │
                  │    Strictly local autonomous braking authority│
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ 2. PHYSICAL KINEMATIC FEASIBILITY            │
                  │    Headway >= H_safe, zero collisions,        │
                  │    Retarder thermal limits respected         │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ 3. OPERATIONAL PRODUCTIVITY (PR)             │
                  │    Maximize ore flow within safe envelope:   │
                  │    PR = (Q_actual / Q_fog_feasible) * 100    │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ 4. DISPATCH & OPTIMIZATION EFFICIENCY        │
                  │    Minimize fleet idle delay & queue size    │
                  └──────────────────────────────────────────────┘
```

> **Non-Negotiable Rule:**  
> Safety feasibility strictly precedes productivity optimization. If an evaluator asks whether central dispatch can speed up trucks in dense fog to hit production targets, the answer is an unconditional:  
> **"NO. The central server has zero authority to override local vehicle safety."**

---

## 2. Attack Vectors & Authoritative Responses

### Attack 1: "At 3 meters visibility, no haul truck can see anything. How can you claim to operate?"
- **Evaluator Trap:** The evaluator suspects you are fabricating sensor ranges or claiming autonomous driving through dense fog without physical perception.
- **Authoritative Defense:**
  1. *"We agree completely. In fact, our physical braking model explicitly proves that at 3–5 m visibility, safe travel speed is mathematically $0.0\text{ m/s}$."*
  2. *Point to [`docs/STAGE5_CAPACITY_CEILING.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_CAPACITY_CEILING.md):*
     $$S_{\text{stop}} + S_{\text{margin}} \le R_v \implies v_{\text{safe}} = -a_{\text{dec}} \tau_{\text{total}} + \sqrt{(a_{\text{dec}} \tau_{\text{total}})^2 + 2 a_{\text{dec}} \max(0, R_v - S_{\text{margin}})}$$
     With a standstill safety margin $S_{\text{margin}} = 5.0\text{ m}$, any visibility $R_v \le 5.0\text{ m}$ forces $\max(0, R_v - S_{\text{margin}}) = 0 \implies v_{\text{safe}} = 0.0\text{ m/s}$.
  3. *"Our system does not claim to drive at speed through 3m fog. Rather, FOG-ORCHESTRATOR predicts the fog onset and executes an orderly **SAFETY STAGING HOLD** at loading bays and buffer yards, preventing trucks from entering steep downhill ramps where they would become trapped. When fog clears, metered departures resume smoothly without gridlock."*

---

### Attack 2: "If your 10-truck production is 183 TPH for both Safety-Only and FOG-Orchestrator, where is the benefit?"
- **Evaluator Trap:** The evaluator notices identical tonnage delivered in small-fleet short windows and claims the orchestrator provides no value.
- **Authoritative Defense:**
  1. *"In a 10-truck fleet over 300 seconds, the haul network is in the unconstrained fleet-availability regime: only 2 trucks reach the crusher tipping pad, so both policies deliver $2 \times 91.5 = 183.0\text{ tonnes}$."*
  2. *"The true benefit at 10 trucks is operational delay mitigation:*
     - *Fleet idle delay reduced by **$33.3\%$** ($1.5\% \to 1.0\%$, $p < 10^{-12}$).*
     - *Standstill waiting time reduced by **$31.8\%$** ($4.4\text{ s} \to 3.0\text{ s}$, $p < 10^{-12}$)."*
  3. *"Furthermore, when fleet density scales to realistic mine operations ($20\text{--}50$ trucks) or during dynamic 1500s fog transitions:*
     - *Safety-Only suffers crusher queue explosion ($Q \ge 6.0$ trucks), pad spillback, and post-clearance accordion gridlock.*
     - *FOG-ORCHESTRATOR's departure holding meters arrivals to match crusher intake ($18\text{ VPH}$), preserving **$91.5\%$ Productivity Retention** while Safety-Only drops significantly."*

---

### Attack 3: "How do you prove HOLD actually caused the queue reduction? Isn't that just a correlation?"
- **Evaluator Trap:** The evaluator claims queue reduction happened by chance or initial vehicle distribution.
- **Authoritative Defense:**
  1. *"We conducted direct counterfactual ablation tests across 10 identical random seeds (`STAGE5_COUNTERFACTUAL_ANALYSIS.md`)."*
  2. *"For every single seed, with identical initial truck positions and identical fog weather trajectories, we disabled the HOLD mechanism (un-metered immediate departures):*
     - *Peak queue at the crusher spiked by an average of **$+48.6\%$** ($+1.7\text{ trucks}$).*
     - *Average vehicle waiting time increased by **$+38.4\text{ s}$**.*
     - *Fleet idle time increased by **$+12.5\%$**."*
  3. *"Because the only variable changed between runs was the HOLD logic, the queue mitigation is mathematically proven to be causally induced by FOG-ORCHESTRATOR."*

---

### Attack 4: "Did you actually run 50 physical 165-tonne haul trucks?"
- **Evaluator Trap:** Checking for fabricated hardware scaling claims.
- **Authoritative Defense:**
  1. *"NO. 50-truck scaling is strictly **SIMULATION ONLY** in the verified digital twin engine."*
  2. *"Physical hardware validation is strictly bounded to our physical prototype:*
     - `TRUCK_01` (ESP32 + LoRa + OLED HMI)
     - `TRUCK_02` (ESP32 + LoRa + OLED HMI)
     - LoRa Gateway ESP32 connected via USB/Wi-Fi to the FastAPI server.
     - Physical V2V telemetry protocol (`STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz`)."
  3. *"We do not claim 50 physical trucks or mine-site deployment. We claim a calibrated physical proof-of-concept for the V2V communication and local safety governor layers, coupled with an audited digital twin for network fleet scaling."*

---

### Attack 5: "Why not just use Chance-Constrained MPC (Level 5) for everything?"
- **Evaluator Trap:** Asking why you didn't default to the most advanced mathematical solver.
- **Authoritative Defense:**
  1. *"We evaluated Level 5 (Chance-MPC) extensively across all 20 seeds (`STAGE5_STATISTICAL_ANALYSIS.md`)."*
  2. *"Chance-MPC enforces an ultra-conservative $2\sigma$ friction bound ($\mu_{\text{safe}} = 0.25$ instead of $0.35$). While it achieves near-zero idle time ($0.1\%$), it imposes a severe **$+41.6\%$ travel time penalty** ($660.8\text{ s}$ vs $466.6\text{ s}$) because trucks crawl across the entire mine."*
  3. *"Level 4 (Deterministic Receding-Horizon MILP + Tier-1 Autonomous Safety Governor) provides the optimal engineering compromise: it maintains **$0.0$ safety violations**, captures the full feasible production envelope, and avoids the crippling travel time penalties of hyper-conservative stochastic control."*
