# 07 — SAFE BEACON & STANDALONE FAILSAFE VALIDATION
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Evidence Classification:** LEVEL 3 / LEVEL 4 (Bench & HIL Validated)

---

## 1. SAFE BEACON PURPOSE & NON-NEGOTIABLE SAFETY CONSTRAINTS

When normal communication with the central orchestrator is severed, the system transitions deterministically:
```
NORMAL COMMUNICATION
        ↓
    DEGRADED
        ↓
  DISCONNECTED
        ↓
LOCAL SAFETY AUTHORITY
        ↓
SAFE BEACON / STANDALONE MODE
```

### Critical Invariants & Rules:
1. **NOT a Replacement for Braking Safety:** The Safe Beacon does not command vehicle actuators. It provides autonomous peer awareness and decentralized coordination in zero-visibility conditions.
2. **Strict Rejection of Remote Commands:** While in `COMMUNICATION_LOST` or `STANDALONE` mode, **NO REMOTE DISPATCH OR FLEET COMMAND IS ACCEPTED**.
3. **Local Safety Governor Remains Authoritative:** The onboard vehicle safety governor evaluates local visibility and road inclination to enforce the kinematic safe stopping ceiling.
4. **Autonomous Crawling Floor:** In dense fog ($R_{\text{vis}} = 8.0\text{ m}$), the vehicle crawls at $3.52\text{ m/s}$ ($12.67\text{ km/h}$). At blindout ($R_{\text{vis}} \le 5.0\text{ m}$), the vehicle executes a controlled halt ($0.0\text{ m/s}$).

---

## 2. PROTOCOL SPECIFICATION & PARSING VERIFICATION

- **Frozen Protocol Payload:**
  `BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>`
- **Example Valid Packet:**
  `BEACON,TRUCK_01,1048,DEGRADED,1727134200.125,ZONE_RAMP_D5`
- **Supported States:** `NORMAL`, `DEGRADED`, `STOP`, `EMERGENCY`

### Automated Adversarial Parsing Test Results:
| Input Vector | Description | Expected Parsing Reaction | Actual Test Result |
| :--- | :--- | :--- | :--- |
| Empty / null string | Corrupted transport buffer | Rejected (`EMPTY_PACKET`) | **PASS** |
| `BEACON,TRUCK_01,abc,NORMAL,100,Z1` | Non-integer sequence number | Rejected (`INVALID_SEQUENCE`) | **PASS** |
| `BEACON,TRUCK_01,1,OPTIMISTIC,100,Z1` | Unknown / unauthorized state token | Rejected (`UNKNOWN_STATE`) | **PASS** |
| `BEACON,TRUCK_01,1,NORMAL,NaN,Z1` | Non-finite timestamp injection | Rejected (`NON_FINITE_TIMESTAMP`)| **PASS** |
| Packet timestamp $t - t_{\text{local}} = 900\text{ s}$ | Future timestamp injection | Rejected (`FUTURE_TIMESTAMP`) | **PASS** |
| Packet timestamp age $> 2.0\text{ s}$ | Stale replay attack packet | Rejected (`STALE_TIMESTAMP`) | **PASS** |
| Valid nominal packet | Compliant over-the-air frame | Parsed successfully (`OK`) | **PASS** |

---

## 3. TIMING & ACTIVATION BENCHMARK

| Parameter | Specification | Measured HIL Value | Compliance |
| :--- | :--- | :--- | :--- |
| **Communication Timeout Horizon** | $\le 1000\text{ ms}$ | $500.0\text{ ms}$ | **COMPLIANT** |
| **Safe Beacon Activation Latency**| $\le 1000\text{ ms}$ | $550.0\text{ ms}$ | **COMPLIANT** (Activates in $<1\text{s}$) |
| **Beacon Broadcast Periodic Rate** | $2.0\text{ Hz}$ (nominal) | $2.0\text{ Hz}$ ($500\text{ ms}$ interval) | **COMPLIANT** |
| **Emergency Burst Broadcast Rate** | $5.0\text{ Hz}$ (emergency) | $5.0\text{ Hz}$ ($200\text{ ms}$ interval) | **COMPLIANT** |
| **Over-the-Air Payload Size** | $< 64\text{ bytes}$ | $44\text{ bytes}$ nominal | **COMPLIANT** |

---

## 4. SCHMITT-TRIGGER DEBOUNCE AROUND 5.0m BLINDOUT

To prevent chattering and abrupt stops/starts when visibility hovers around the $5.0\text{ m}$ safety buffer boundary:
- **Halt Threshold ($S_{\text{base}}$):** $R_{\text{vis}} \le 5.0\text{ m} \implies$ Immediate emergency staging halt ($v_{\text{safe}} = 0.0\text{ m/s}$, $0\text{ ms}$ delay).
- **Clearing Threshold:** $R_{\text{vis}} \ge 5.2\text{ m}$ ($S_{\text{base}} + 0.20\text{ m}$).
- **Persistence Count:** Requires $2$ consecutive observations above $5.2\text{ m}$ before resuming crawl.
- **Verification Result:** Zero limit-cycle chattering observed under fluctuating $4.9\text{ m} \leftrightarrow 5.1\text{ m}$ sightline signals.

---

## 5. AUDIT VERDICT

The standalone Safe Beacon architecture (`failsafe/safe_beacon.py` & `integration_adapters/safe_beacon_adapter.py`) satisfies all Phase 9 requirements:
- Deterministic failsafe activation upon communication timeout.
- Total rejection of remote commands during communication loss.
- Full preservation of local safety authority and kinematic stopping bounds.
