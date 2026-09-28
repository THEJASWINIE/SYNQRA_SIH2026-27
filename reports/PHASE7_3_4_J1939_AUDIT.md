# PHASE 7.3.4 — ATTACK #17: J1939 / CAN BUS INTEGRATION & VEHICLE HARNESS AUDIT
**Module:** In-Vehicle Telemetry & Chassis Network  
**Dataset:** `data/phase7_3_4_j1939_scoping.csv`  
**Classification:** **BENCH EMULATION VERIFIED (YELLOW) / BH100 CHASSIS UNVALIDATED (OPEN)**  

---

## 1. Technical Boundary: Controller Area Network vs Real Vehicle

The hostile audit evaluated claims regarding SAE J1939 heavy-vehicle integration:
> *"Does successful ESP32 TWAI (Two-Wire Automotive Interface) transmission prove vehicle integration on a BEML BH100 dumper?"*

**The Definite Technical Answer is NO.**  
A critical distinction must be maintained between:
1. **Controller Hardware Interface Capability:** The ESP32 silicon contains an ISO 11898-1 compatible CAN controller (TWAI). When wired to a CAN transceiver (e.g., Texas Instruments SN65HVD230 or VP230), it can successfully transmit and receive 29-bit identifier extended CAN frames at $250\text{ kbps}$.
2. **On-Chassis Vehicle Integration:** Physical access to the J1939 backbone of a running BEML BH100 haul truck requires tapping into the Deutsch 9-pin diagnostic connector or splicing into the J1939 twisted pair (CAN_H / CAN_L).

---

## 2. Forensic Audit of J1939 Data Files

The repository was searched for live raw CAN log captures (`.asc`, `.blf`, `.csv`, or socketcan logs) from a physical BEML BH100 chassis.
- **Findings:**
  - `telemetry/` contains synthetically packed J1939 parameter group numbers (PGN 61444 for engine speed/torque, PGN 65265 for cruise control/wheel-based vehicle speed).
  - ESP32 C firmware packs and decodes these frames correctly on a bench bus.
  - **ZERO PHYSICAL J1939 CHASSIS CAPTURES EXIST.** No live frames have been recorded from a real Cummins KTA38-C engine ECM or Allison transmission controller.

**Formal Classification:**  
$$\mathbf{BEML\;BH100\;J1939\;CHASSIS\;INTEGRATION = UNVALIDATED\;(OPEN)}$$

---

## 3. Four Unresolved In-Vehicle Engineering Challenges

When the team physically approaches a BEML BH100 at NMDC Bailadila, four major engineering challenges must be resolved before claiming vehicle integration:
1. **Proprietary CAN Shielding & Firewalling:** Many modern mining machines implement security firewalls that block external nodes from transmitting override commands onto the primary powertrain CAN bus.
2. **Baud Rate Mismatches:** While modern trucks use J1939-14 at $250\text{ kbps}$ or $500\text{ kbps}$, older legacy BH100 dumpers may use proprietary RS-485 or legacy proprietary baud rates.
3. **Electronic Throttle / Retarder Control Authority:** Injecting a commanded speed into the ECM requires specific TSC1 (Torque/Speed Control 1) PGN permissions. If the ECM firmware does not enable external auxiliary speed governors, transmission of speed commands on the bus will be ignored by the engine.
4. **Harsh Mining Electrical Environment:** 24V commercial vehicle alternator load dumps, inductive spikes from hydraulic hoist solenoids, and extreme vibration require automotive-grade TVS diodes and galvanic optoisolators that standard development boards lack.

---

## 4. Mandatory Presentation Language Rule

> **Allowed Statement:**  
> *"The system implements an ISO 11898-1 / SAE J1939 protocol stack validated on ESP32 TWAI bench hardware at 250 kbps, ready for future on-chassis vehicle tapping."*

> **Prohibited Statement:**  
> *"The software is integrated and tested with the BEML BH100 vehicle CAN bus." (FALSE)*
