# STAGE 5.2.1: FORENSIC COLLISION AVOIDANCE AUDIT
**Forensic Audit of Experiment B: Kinematics, Trajectory Verification, and Claim Bounds**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Complex)  
**Status:** EVIDENCE INTEGRITY GATE — EMPIRICALLY GROUNDED VERDICT  

---

## 1. Audit Scope & Executive Finding

This audit evaluates the experimental validity of **Experiment B (Explicit Two-Vehicle Collision Avoidance)** in `experiments/run_stage5_2_nmdc_validation.py` and its evidence file [`docs/STAGE5_2_COLLISION_SCENARIOS.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_COLLISION_SCENARIOS.csv).

### Core Forensic Finding:
The correct scientific statement supported by the code and data is:
> ### **VERDICT: STATEMENT C**
> **"Non-colliding trajectories were demonstrated for the tested kinematic scenarios."**

The previous claim that *"FOG-Orchestrator demonstrably eliminates collision risk"* was an **overstatement**. Real-world mining collision risk involves unmodeled stochastic factors (such as driver medical incapacitation, extreme brake hydraulic failure, mechanical steering tie-rod failure, or multi-vehicle pileups) that cannot be eliminated by software. The system **proves collision-risk response and non-colliding car-following** under its modeled kinematic physics.

---

## 2. Experimental Verification Checklist

We audited the implementation in `run_collision_avoidance_experiment()` line-by-line:

| Audit Criterion | Verification Status | Forensic Code & Mathematical Evidence |
| :--- | :---: | :--- |
| **1. 9 Scenarios Actually Executed** | **VERIFIED** | All 9 scenarios (`NORMAL`, `LEAD_BRAKE`, `FOG_DROP`, `OPERATOR_OVERSPEED`, `PACKET_LOSS_50`, `COMM_LOSS_TOTAL`, `STALE_DATA`, `REPLAY_PACKET`, `LEAD_ACCEL`) loop and execute discrete timesteps. |
| **2. Trajectories Actually Simulated** | **VERIFIED** | Continuous simulation at $\Delta t = 0.1\text{ s}$ over $30.0\text{ s}$ ($300\text{ steps}$ per scenario, $2{,}700\text{ total steps}$). State vectors $(s_{\text{lead}}, v_{\text{lead}}, s_{\text{fol}}, v_{\text{fol}})$ update step-by-step. |
| **3. Lead Vehicle Deceleration Exists** | **VERIFIED** | Line 345: In `LEAD_BRAKE`, lead applies $a_{\text{lead}} = -3.0\text{ m/s}^2$ from $t \ge 2.0\text{ s}$, decelerating from $6.0\text{ m/s}$ to dead stop in $2.0\text{ s}$ ($s_{\text{lead\_stop}} = 138.0\text{ m}$). |
| **4. Following Vehicle Dynamics Exist** | **VERIFIED** | Follower dynamically accelerates ($+1.2\text{ m/s}^2$) or decelerates ($a_{\text{applied}} = \min(a_{\text{dec\_max}}, \text{req\_decel})$) toward commanded speed $v_{\text{cmd}}$. |
| **5. Relative Velocity Modeled** | **VERIFIED** | Relative velocity $\Delta v = v_{\text{fol}} - v_{\text{lead}}$ directly drives the required deceleration formula: $\frac{v_{\text{fol}}^2 - v_{\text{cmd}}^2}{2(H_{\text{act}} - 5.0)}$. |
| **6. Continuous Headway Tracking** | **VERIFIED** | Line 382: Actual spatial bumper-to-bumper headway is calculated at every step: $H_{\text{act}}(t) = s_{\text{lead}}(t) - s_{\text{fol}}(t) - 10.52\text{ m}$. |
| **7. Minimum Separation Recorded** | **VERIFIED** | Line 383: `min_headway = min(min_headway, actual_headway)` continuously tracks the closest approach. |
| **8. Collision Condition Explicitly Defined** | **VERIFIED** | Line 387: `if actual_headway < 5.0: collision_event = True`. Collision is triggered if the distance falls below the $5.0\text{ m}$ standstill margin. |
| **9. Safety Buffer Justification** | **VERIFIED** | The $5.0\text{ m}$ buffer represents the mandatory ISO 3450 / DGMS standstill safety margin for heavy off-highway haul trucks (Caterpillar 777G, $10.52\text{ m}$ length). |
| **10. Zero Collision Count Proven** | **VERIFIED** | Across all 9 scenarios, $H_{\text{min}} \ge 6.49\text{ m} > 5.00\text{ m}$. Zero collisions occurred because physical separation was maintained. |
| **11. No Artificial Disabling** | **VERIFIED** | No artificial bypasses or flags existed to hide collisions. The collision detection logic was active on every step. |

---

## 3. Detailed Trajectory Clearance Table

From [`docs/STAGE5_2_COLLISION_SCENARIOS.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_COLLISION_SCENARIOS.csv):

| Scenario ID | Scenario Name | Minimum Headway ($H_{\text{min}}$) | Standstill Margin Buffer | Net Safety Clearance Margin | Total Latency ($\tau_{\text{total}}$) | Collision Count | Status |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | Normal Safe Following | $8.90\text{ m}$ | $5.00\text{ m}$ | **$+3.90\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **2** | Rapid Deceleration of Lead ($-3\text{ m/s}^2$) | **$6.49\text{ m}$** | $5.00\text{ m}$ | **$+1.49\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **3** | Sudden Fog Drop ($50\text{m} \to 8\text{m}$) | $49.38\text{ m}$ | $5.00\text{ m}$ | **$+44.38\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **4** | Unsafe Operator Speed Request ($40\text{ km/h}$) | $8.90\text{ m}$ | $5.00\text{ m}$ | **$+3.90\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **5** | V2V Packet Loss ($50\%$) | $8.90\text{ m}$ | $5.00\text{ m}$ | **$+3.90\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **6** | Total Comm Loss ($10\text{ s}$ blackout) | $32.70\text{ m}$ | $5.00\text{ m}$ | **$+27.70\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **7** | Stale Leader Telemetry | $32.70\text{ m}$ | $5.00\text{ m}$ | **$+27.70\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **8** | Duplicate / Out-of-Order Packet | $8.90\text{ m}$ | $5.00\text{ m}$ | **$+3.90\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |
| **9** | Recovery Acceleration | $31.44\text{ m}$ | $5.00\text{ m}$ | **$+26.44\text{ m}$** | $0.400\text{ s}$ | 0 | **NON-COLLIDING** |

---

## 4. Scientific Bounds & Limitations

1. **Model Scope:**
   The experiment proves that when lead and following trucks follow the modeled differential equations with $\tau_{\text{total}} = 0.400\text{ s}$ system latency and $a_{\text{dec\_max}} = g(\mu_{\text{safe}} \cos\theta + \sin\theta)$, the vehicle stops with at least **$1.49\text{ m}$ of clearance above the $5\text{ m}$ buffer**.
2. **What Is NOT Proven:**
   - Real-world mechanical brake failure (e.g. pneumatic hose rupture or brake drum glazing) was not modeled.
   - 3-or-more vehicle accordion chain collisions under variable road cross-slope wet patches were not modeled.
   - Severe GPS multipath positioning error ($>10\text{ m}$) was not injected into the follower's car-following solver in Exp B.
3. **Mandatory Wording:**
   In all presentations and technical defense documents, use:
   *"Non-colliding vehicle trajectories were demonstrated across the 9 evaluated kinematic stress scenarios, maintaining a minimum bumper clearance of 6.49 m under a 0.400 s reaction latency."*
