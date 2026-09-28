# EXPERIMENT E7 — 75% PACKET LOSS & SAFETY ROBUSTNESS REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Fail-Safe Communication Invariant Verification  
**Evidence Level:** L7 — Bench Measured / L1 — Deterministic Logic Verification  
**Dataset Reference:** [`data/packet_loss_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/packet_loss_results.csv)  
**Figure:** [`figures/packet_loss_vs_safety.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/packet_loss_vs_safety.png)  

---

## 1. Redefining the "75% Packet Loss" Claim

> [!CAUTION]
> **SCIENTIFIC CLARIFICATION OF PREVIOUS CLAIMS**  
> Previous project statements claiming that "the system operates normally with 75% packet loss" were misleading. A wireless link with 75% packet loss is severely degraded; normal real-time cloud dispatch cannot operate optimally under such loss.
>
> What is **actually proven** by FOG-ORCHESTRATOR 2.0 is:  
> **"Local safety invariants are 100% preserved even under 75% (and up to 99%) RF packet loss, because the vehicle does not rely on central commands to remain safe."**

---

## 2. Experimental Test Matrix & Governor Response

500 commands sent at 20 Hz (0.050 s period) with excessive requested speed ($v_{\text{cmd}} = 12.0\text{ m/s}$), testing vehicle governor clamp at $v_{\text{safe}} = 4.50\text{ m/s}$:

| Injected Loss Rate (%) | Commands Sent | Commands Delivered | Actual PDR (%) | Clamped Commands | Fallback Activations | Safety Violations ($v > v_{\text{safe}}$) | Safety Invariant Preserved? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0% (Ideal)** | 500 | 500 | 100.0% | 500 | 0 | **0** | **YES (100%)** |
| **25% (Mild Loss)**| 500 | 378 | 75.6% | 378 | 500 | **0** | **YES (100%)** |
| **50% (Moderate)** | 500 | 244 | 48.8% | 244 | 500 | **0** | **YES (100%)** |
| **75% (Severe)** | 500 | 129 | 25.8% | 129 | 500 | **0** | **YES (100%)** |
| **90% (Extreme)** | 500 | 52 | 10.4% | 52 | 500 | **0** | **YES (100%)** |
| **99% (Blackout)**| 500 | 4 | 0.8% | 4 | 500 | **0** | **YES (100%)** |

---

## 3. Invariant Enforcement Mechanisms

1. **Watchdog Expiration under Prolonged Loss:**  
   If packet loss persists for $> 1.0\text{ s}$ (20 consecutive dropped frames), the onboard governor watchdog expires, latching the vehicle into `EMERGENCY_STOP` and forcing applied speed to $0.0\text{ m/s}$.

2. **Clamping under Intermittent Reception:**  
   When occasional central commands arrive through the lossy channel, any requested speed above the locally computed $v_{\text{safe}}$ (e.g. 12.0 m/s > 4.50 m/s) is instantly clamped.

3. **Prevention of Stale Re-acceleration:**  
   Lost or delayed packets can never cause the vehicle to accelerate unsafely. The vehicle safety envelope is owned strictly by the local wheel controllers.
