# 11_CAN_J1939_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — CAN Bus & SAE J1939 Protocol Abstraction Audit
**Date / Timestamp:** 2026-09-27T09:46:30+05:30  
**Evaluator Role:** Embedded Systems Engineer, Heavy Equipment Integration Engineer  
**Absolute Principle:** NO FABRICATION — Formal Protocol Verification vs Physical OEM HEMM Reality

---

### 1. SOFTWARE PROTOCOL ABSTRACTION

The platform implements an ISO 11898-1 / SAE J1939 abstraction layer (`fog_safe/can_interface.py` and `tests/test_phase8_hil.py`):

| Parameter / Protocol Feature | Software Implementation | Standard Reference | Verification State |
| :--- | :--- | :--- | :--- |
| **Identifier Format** | 29-bit Extended Frame | SAE J1939 / ISO 11898-1 | **PASS (SOFTWARE)** |
| **Baud Rate** | $250\text{ kbps}$ (Standard J1939) / $500\text{ kbps}$ | SAE J1939-14 | **CONFIGURED** |
| **PGN 61444 (EEC1)** | Engine Speed (SPN 190), Engine Torque (SPN 513) | SAE J1939-71 | **PASS (EMULATION)** |
| **PGN 65265 (CCVS1)** | Wheel-Based Vehicle Speed (SPN 84), Brake Switch (SPN 597) | SAE J1939-71 | **PASS (EMULATION)** |
| **PGN 61440 (ERC1)** | Retarder Enable (SPN 571), Retarder Torque (SPN 520) | SAE J1939-71 | **PASS (EMULATION)** |
| **Bus-Off Recovery** | Auto-recovery timer after 128 occurrences of 11 consecutive recessive bits | ISO 11898-1 | **PASS (UNIT TEST)** |

---

### 2. PHYSICAL OEM HEMM VALIDATION REALITY

$$\mathbf{OEM\ HEMM\ VALIDATION = NOT\ TESTED}$$

#### Strict Factual Boundary:
1. **Physical Mining Truck CAN Bus:**
   - No physical BEML BH100, Caterpillar 777, or Komatsu HD785 haul truck CAN bus was connected to this development workstation or scale prototype.
   - All tests demonstrating J1939 decoding were executed using ESP32 TWAI software loopback or simulated CAN frame injectors (`hardware_emulator.py`).
2. **Field Deployment:**
   - Any claim that the system was "validated on HEMM trucks in Bailadila Iron Ore Mine" is **FALSE / FABRICATED** if presented as physical evidence.
   - The correct engineering classification is: **EMULATED IN HIL / LAB PROTOTYPE ONLY; FIELD VALIDATION NOT YET PERFORMED**.
