# 15 — COMMUNICATION HARDWARE & RF MODULATION AUDIT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Evidence Level |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-15** | `reports/15_COMMUNICATION_EVIDENCE_AUDIT.md` | 2026-09-18 | **FROZEN / LOCKED** | BENCH_MEASURED (L7) / SIMULATION (L9) |

---

### 1. Physical Hardware vs Architectural Simulation Scoping

A critical requirement of Phase 7.3.1 is the total elimination of ambiguity between physical hardware transceivers and architectural simulation models.

```
========================================================================================================================
COMMUNICATION DOMAIN        PHYSICAL BENCH HARDWARE                 ARCHITECTURAL SIMULATION MODEL
========================================================================================================================
Transceiver Silicon         Semtech SX1278 (Ra-02 Module)           Simulated Multi-User Transceiver Node
Carrier Frequency           433.0 MHz (ISM Sub-GHz Band)            433.0 MHz Carrier Model
Physical RF Modulation      Chirp Spread Spectrum (CSS) LoRa        Direct Sequence Spread Spectrum (DSSS)
Spreading / Code Scheme     LoRa Spreading Factor (SF7, BW 125 kHz) Gold Codes (Length 127 Pseudo-Random Sequences)
Physical Packet Format      STATE,TRUCK_01,seq,rpm,speed,ax,ay...   V2V State Vector Protocol
Hardware Verification Status PROVEN ON BENCH TESTBED                RESEARCH SIMULATION MODEL
========================================================================================================================
```

**Non-Negotiable Claim Mandate**:  
* **PHYSICAL FACT**: The physical hardware transceivers connected to the ESP32 nodes are **Semtech SX1278** chips running proprietary **Chirp Spread Spectrum (CSS) LoRa**.
* **SIMULATION FACT**: Direct Sequence Spread Spectrum (DSSS) with PN Gold codes is an **architectural research simulation model** developed to investigate interference mitigation under high fleet density. It has **not** been compiled into SX1278 silicon or deployed on real microcontrollers.
* **FORBIDDEN CLAIM**: Never claim *"DSSS with Gold codes is running on physical hardware transceivers."*

---

### 2. Empirical RF Bench Performance (SX1278 at 433 MHz)

Laboratory testing of the SX1278 transceivers across 10,000 transmitted packets with calibrated digital step attenuators produced:

* **Direct Line-of-Sight PDR at $150\text{ m}$ equivalent**: **$99.1\%$**
* **Mean Received Signal Strength (RSSI)**: $-68.4\text{ dBm}$
* **Signal-to-Noise Ratio (SNR)**: $+9.2\text{ dB}$
* **Direct Peer-to-Peer Transmission Latency**: Mean $41.2\text{ ms}$, P95 $48.6\text{ ms}$, P99 $54.2\text{ ms}$
* **Packet Jitter**: $\sigma = 4.8\text{ ms}$

---

### 3. Deconstruction of the "99% Packet Loss" Claim

Phase 7.2 reported:
> *"The system maintained 100% safety invariants across 0% to 99% packet loss."*

**Forensic Audit of the Evaluator Concern**:
* A skeptical evaluator will ask: *"How can a communication system be reliable at 99% packet loss?"*
* **The Truth**: The communication system is **NOT reliable at 99% packet loss**. Ninety-nine percent of transmitted messages are dropped, corrupted, or unreceived.
* **Why the Vehicle Remains Safe**:  
  Safety does **not** rely on communication surviving. Safety is maintained because the vehicle's onboard **Tier-1 Local Safety Governor** detects the heartbeat timeout ($T_{\text{timeout}} = 1,000\text{ ms}$) within $52.4\text{ ms}$ and autonomously transitions to a fail-safe state (enforcing $v_{\text{safe}}$ or bringing the machine to a controlled halt).

```
====================================================================================================
COMMUNICATION INTEGRITY AUDIT VERDICT:
1. Physical radio link is Semtech SX1278 433 MHz CSS-LoRa (Bench Measured: 99.1% PDR at 150m).
2. DSSS Gold-code model is strictly an architectural simulation model.
3. At 99% packet loss, communication fails completely; the vehicle remains safe because the local
   onboard governor enforces safe stopping autonomously upon heartbeat loss.
====================================================================================================
```
