# 08 — SAFE BEACON & STANDALONE FAILSAFE VALIDATION
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `08_SAFE_BEACON_VALIDATION.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Bench & HIL Validated)  
**Status:** COMPLETE & FROZEN  

---

## 1. Executive Summary & Communication-Loss Cascade (Section 21)

When normal RF communication with the central orchestrator or serving gateway is severed, the system transitions through a deterministic, fail-closed cascade:

```
                  NORMAL (Serving Gateway Connected)
                            ↓
                  DEGRADED (Packet Loss > 30% / RSSI < -105 dBm)
                            ↓
               DISCONNECTED (Comm Timeout > 500 ms)
                            ↓
                SAFE BEACON (Autonomous 433 MHz Broadcast)
                            ↓
               LOCAL VEHICLE SAFETY GOVERNOR
                  (Sole Authority Over Actuators)
```

---

## 2. Cross-Subsystem Display Consistency Invariant (Section 21)

Upon communication loss and Safe Beacon activation, every subsystem interface must explicitly reflect the offline state:

| Subsystem | Required Display Indicator | Unacceptable Failure Mode | Validation Status |
|:---|:---|:---|:---:|
| **Operator HMI (Driver Screen)** | **`COMMUNICATION LOST — SAFE MODE`** | Displaying "ONLINE" or cached central dispatch speeds | **PASS** |
| **Control Room HMI** | **`TRUCK-XX OFFLINE — SAFE BEACON ACTIVE`** | Showing vehicle as actively connected to gateway | **PASS** |
| **Digital Twin** | **`COMMUNICATION STATE = LOST`** | Silently continuing to display vehicle as normally connected | **PASS** |
| **Safety Governor** | **Autonomous Safe Speed ($v_{\text{safe}}$)** | Accepting remote commands during comm blackout | **PASS** |

> **CRITICAL RULE:** The Digital Twin must **NOT** silently continue displaying the vehicle as normally connected. It marks communication as LOST and freezes/extrapolates position with explicit staleness warnings.

---

## 3. Protocol Specification & Adversarial Parsing

- **Frozen Protocol Payload:**
  `BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>`
- **Example Valid Packet:**
  `BEACON,TRUCK_01,1048,DEGRADED,1727134200.125,ZONE_RAMP_D5`
- **Supported States:** `NORMAL`, `DEGRADED`, `STOP`, `EMERGENCY`

### Automated Adversarial Parsing Test Results:
| Input Vector | Description | Expected Parsing Reaction | Actual Test Result |
|:---|:---|:---|:---:|
| Empty / null string | Corrupted transport buffer | Rejected (`EMPTY_PACKET`) | **PASS** |
| `BEACON,TRUCK_01,abc,NORMAL,100,Z1` | Non-integer sequence number | Rejected (`INVALID_SEQUENCE`) | **PASS** |
| `BEACON,TRUCK_01,1,OPTIMISTIC,100,Z1` | Unknown / unauthorized state token | Rejected (`UNKNOWN_STATE`) | **PASS** |
| `BEACON,TRUCK_01,1,NORMAL,NaN,Z1` | Non-finite timestamp injection | Rejected (`NON_FINITE_TIMESTAMP`) | **PASS** |
| Packet timestamp $t - t_{\text{local}} = 900\text{ s}$ | Future timestamp injection | Rejected (`FUTURE_TIMESTAMP`) | **PASS** |
| Packet timestamp age $> 2.0\text{ s}$ | Stale replay attack packet | Rejected (`STALE_TIMESTAMP`) | **PASS** |
| Valid nominal packet | Compliant over-the-air frame | Parsed successfully (`OK`) | **PASS** |

---

## 4. Activation Timing & Recovery Benchmark

| Parameter | Specification | Measured HIL Value | Compliance |
|:---|:---|:---:|:---:|
| **Communication Timeout Horizon** | $\le 1000\text{ ms}$ | $500.0\text{ ms}$ | **COMPLIANT** |
| **Safe Beacon Activation Latency**| $\le 1000\text{ ms}$ | $550.0\text{ ms}$ | **COMPLIANT** |
| **Beacon Broadcast Periodic Rate** | $2.0\text{ Hz}$ (nominal) | $2.0\text{ Hz}$ ($500\text{ ms}$ interval) | **COMPLIANT** |
| **Emergency Burst Broadcast Rate** | $5.0\text{ Hz}$ (emergency) | $5.0\text{ Hz}$ ($200\text{ ms}$ interval) | **COMPLIANT** |
| **Remote Command Rejection** | $100\%$ Rejected | $100\%$ Rejected | **COMPLIANT** |
| **Recovery Resynchronization** | 2 consecutive valid sequence frames required | 2 frames verified | **COMPLIANT** |
