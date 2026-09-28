# 17 — CLAIM LANGUAGE CORRECTION & RETRACTION DIRECTIVE
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Governing Standard |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-17** | `reports/17_FINAL_CLAIM_CORRECTION.md` | 2026-09-18 | **FROZEN / LOCKED** | ISO 3450 / DGMS 09/2008 |

---

### 1. Mandatory Language Replacement Table

To protect the project from evaluator skepticism, all technical reports, slides, and code comments are subjected to mandatory terminology corrections:

```markdown
| # | Dangerous / Exaggerated Language | Mandatory Reconciled Scientific Language | Audit Rationale |
| :- | :--- | :--- | :--- |
| **1** | *"Eliminates all collision risk in mine fog."* | **"Maintained non-colliding trajectories across all tested operational scenarios and failure modes."** | Absolute elimination of physical collision risk in the real world cannot be proven by simulation or bench testbeds. |
| **2** | *"100% safety guaranteed under low visibility."*| **"Zero safety-invariant violations observed within the 10,000 tested Monte Carlo parameter combinations."** | Scientific integrity requires bounding claims strictly to the evaluated parameter envelope. |
| **3** | *"FOG-Orchestrator delivers instant recovery after fog clears."* | **"Achieved multi-stage staged recovery (45–90s local platoon spacing, 300–600s crusher feed stabilization)."** | Physical heavy haulers cannot accelerate instantaneously; recovery occurs in discrete kinematic stages. |
| **4** | *"FOG-Orchestrator delivers 3,294 TPH / 2,745 TPH mine production."* | **"Sustained steady-state throughput is 1,591.4 TPH (96.6% utilization of the 1,647.0 TPH crusher ceiling). 3,294 TPH is a retracted 10-minute queue-flush burst."** | Physical primary gyratory crusher pocket cannot service more than 18 dumps/hour (1,647.0 TPH) continuously. |
| **5** | *"Reduces total waiting time by 77.4% across the mine."* | **"Reduces hazardous haul ramp stationary queue waiting by 77.4% by relocating waiting to safe shovel bays; net total cycle delay decreases by -11.6% (-82.8 s/cycle)."** | Little's Law dictates that waiting cannot disappear when bottleneck capacity is fixed; queues are relocated to safe staging zones. |
| **6** | *"Field-validated on active mine dump trucks at Bailadila."* | **"Bench-validated on hardware testbeds (ESP32 TWAI CAN, SX1278 CSS-LoRa, proportional hydraulic bench); field validation on active BH100 chassis at Bailadila remains pending."** | No physical equipment at NMDC Bailadila was tapped or modified; bench and surrogate data must be explicitly acknowledged. |
| **7** | *"BEML BH100 measured brake response is 200.16 ms."* | **"Surrogate actuator bench measurement is 200.16 ms mean (P99 = 237.1 ms); real BH100 in-situ brake line pressure rise remains unmeasured."** | The testbed used a commercial industrial proportional valve, not an actual BH100 brake cylinder. |
| **8** | *"Communication is reliable at 99% packet loss."* | **"Communication fails at 99% packet loss; the safety invariant is preserved because the local governor autonomously enforces safe stopping upon heartbeat timeout."** | Distinguishes communication link availability from autonomous vehicle fail-safe enforcement. |
| **9** | *"DSSS with Gold codes deployed on hardware transceivers."* | **"Physical hardware transceivers use Semtech SX1278 Chirp Spread Spectrum (CSS) LoRa at 433 MHz; DSSS is an architectural simulation model."** | Eliminates confusion between physical transceiver firmware and simulated research models. |
| **10**| *"ISO 3450 specifies BH100 deceleration = 1.20 m/s²."* | **"1.20 m/s² is a conservative service braking / operator comfort assumption. Full emergency friction braking provides 2.75 m/s² on -8% ramps."** | ISO 3450 Annex A specifies stopping distance criteria, not a single 1.20 m/s² deceleration clause for BH100. |
```

---

### 2. Formal Register of Retracted Claims

The following historical claims are **PERMANENTLY RETRACTED** from all official project evaluation materials:

1. **RETRACTED**: *"Mine production under fog reaches 3,294 TPH."*  
   *Reason*: Disproven as a 10-minute initial queue flush artifact.
2. **RETRACTED**: *"FOG-Orchestrator eliminates 77.1% of total waiting across the mine."*  
   *Reason*: Disproven by Little's Law; 77.4% applies specifically to hazardous ramp queue waiting.
3. **RETRACTED**: *"J1939 brake deceleration telemetry has been field-validated on active mining machinery."*  
   *Reason*: J1939 was bench-validated against ESP32 TWAI CAN emulators; active BH100 chassis testing remains pending.
4. **RETRACTED**: *"DSSS modulation is compiled into SX1278 hardware firmware."*  
   *Reason*: Physical silicon uses Semtech proprietary CSS-LoRa.
5. **RETRACTED**: *"At v = 5.12 m/s and a = 1.20 m/s², the stopping distance is 7.0 m."*  
   *Reason*: Mathematically contradictory; $S_{\text{stop}}(5.12, \tau=0.375, a=1.20) = \mathbf{12.84\text{ m}}$. $5.12\text{ m/s}$ requires $a = 2.75\text{ m/s}^2$ to stop in $7.0\text{ m}$.
