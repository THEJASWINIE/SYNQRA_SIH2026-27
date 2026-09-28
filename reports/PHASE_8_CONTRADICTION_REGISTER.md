# PHASE 8 — CONTRADICTION & OBSOLESCENCE REGISTER
## FOG-ORCHESTRATOR 2.0 — SIH26007
### Forensic Audit of Legacy Terminology, Parameter Evolutions & Unsupported Assertions

---

## 1. Forensic Audit Protocol

In accordance with Master Prompt Section 22, the repository was scanned for forbidden, over-claimed, or contradictory phrasing:
- *"BH100 validated"*
- *"BH100 braking measured"*
- *"production J1939"*
- *"autonomous braking"*
- *"collision-free"*
- *"mathematically proven"*
- *"field validated"*
- *"production ready"*
- *"real mine testing"*
- *"DSSS hardware"*

---

## 2. Contradiction Resolution Register

| Contradiction ID | Target Concept / Term | Legacy / Forbidden Formulation | Current Canonical Resolution | Status | Historical Origin & Rationale |
|---|---|---|---|---|---|
| **P8-C01** | Vehicle Validation Scope | *"BEML BH100 integrated & braking validated"* | **"HIL validation using ESP32 / TWAI and simulated vehicle ECU behavior."** | **RESOLVED & FROZEN** | Replaced over-claimed vehicle validation with honest HIL boundary. |
| **P8-C02** | CAN Bus Architecture | *"Production J1939 haul truck bus interface"* | **"J1939-compatible simulation with project-defined PGN layouts."** | **RESOLVED & FROZEN** | Clarified that frames are project-defined, not an OEM factory tap. |
| **P8-C03** | Braking Deceleration | *"Physical braking deceleration of 2.7856 m/s² measured on BH100"* | **"2.7856 m/s² is model-derived from DGMS stopping constraints; 1.20 m/s² is an engineering assumption."** | **RESOLVED & FROZEN** | Decoupled model equations from unmeasured physical brake disc friction. |
| **P8-C04** | Latency Characterization | *"Software timing of 216 ms called braking latency"* | **"HIL command-path latency (216 ms) strictly separated from physical vehicle stopping distance."** | **RESOLVED & FROZEN** | Prevented conflating electronic compute delay with Newtonian vehicle stopping distance. |
| **P8-C05** | Safety Guarantee | *"100% collision-free guaranteed"* | **"Maintained non-colliding trajectories across all tested simulation scenarios (zero violations in 105 HIL runs)."** | **RESOLVED & FROZEN** | Prohibited absolute guarantees; framed as verified empirical bounds within modeled conditions. |
| **P8-C06** | Mathematical Proof | *"Mathematically proven collision avoidance"* | **"Deterministic safety invariant v_applied <= v_safe enforced algorithmically."** | **RESOLVED & FROZEN** | Replaced pseudo-formal proof claims with algorithmic invariant verification. |
| **P8-C07** | RF Hardware Scope | *"DSSS physical transceiver hardware validated"* | **"DSSS processing gain (10.2 dB) modeled in simulation; LoRa physical transceivers tested on bench."** | **RESOLVED & FROZEN** | Distinguishes bench LoRa testing from custom DSSS ASIC basebands. |
| **P8-C08** | RF Security State | *"Unconditional secure communications"* | **"Unauthenticated RF: overspeed attacks clamped by governor, but nuisance STOP / DoS remains possible without HMAC."** | **RESOLVED & FROZEN** | Documents realistic attack surfaces without falsely claiming military crypto. |

---

## 3. Parameter Evolution & Obsolescence Register

To prevent confusion between historical test values and current canonical numbers:

| Parameter Name | Obsolete / Historical Value | Current Canonical Value | Classification | Context / Authority |
|---|---|---|---|---|
| **Vehicle Total Mass (GVM)** | $85.0\text{ tonnes}$ (Phase 1–4 toy truck) | **$165.5\text{ tonnes}$** ($165,500\text{ kg}$) | `CURRENT CANONICAL` | BEML BH100 full rated GVM |
| **Empty Vehicle Mass** | $35.0\text{ tonnes}$ | **$70.0\text{ tonnes}$** ($70,000\text{ kg}$) | `CURRENT CANONICAL` | BH100 tare weight |
| **Rated Payload** | $50.0\text{ tonnes}$ | **$95.5\text{ tonnes}$** ($95,500\text{ kg}$) | `CURRENT CANONICAL` | BH100 net payload capacity |
| **Emergency Deceleration** | $3.50\text{ m/s}^2$ / $4.0\text{ m/s}^2$ (unbounded) | **$2.7856\text{ m/s}^2$** | `CURRENT CANONICAL` | Canonical DGMS model-derived ceiling |
| **Service Deceleration** | $0.80\text{ m/s}^2$ / variable | **$1.20\text{ m/s}^2$** | `CURRENT CANONICAL` | Standard heavy haul engineering assumption |
| **Rolling Resistance ($C_{rr}$)** | $0.05$ (Phase 2 loose gravel) | **$0.02$** | `CURRENT CANONICAL` | Compacted mine haul road standard |
| **Base Safety Buffer ($S_{\text{base}}$)** | $10.0\text{ m}$ / $2.0\text{ m}$ | **$5.0\text{ m}$** | `CURRENT CANONICAL` | Canonical physical bumper safety buffer |
| **Civil Road Grade Limits** | $0\text{ to }15\%$ (unrealistic) | **$\pm 8.0\%$** ($-8\%$ downhill, $+8\%$ uphill) | `CURRENT CANONICAL` | DGMS maximum allowable open-cast haul road grade |

---

## 4. Audit Conclusion

All legacy contradictions have been indexed, classified, and permanently reconciled. No unsupported claims of physical BH100 braking, production J1939 vehicle bus access, or universal safety guarantees remain active in the codebase or technical documentation.
