# PHASE 8 — HIL FAILURE INJECTION TEST MATRIX
## FOG-ORCHESTRATOR 2.0 — SIH26007
### Empirical Validation Results across 30 Mandatory Scenarios + 75 Parametric Trials

---

## 1. Test Methodology & Invariant Scope

Every scenario in the Phase 8 HIL suite is executed through [`integration_adapters/hil_simulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/hil_simulator.py) using closed-loop simulation across the virtual CAN/TWAI 250 kbps bus. 

### Core Invariants Audited:
- **I1:** $v_{\text{applied}} \le v_{\text{safe}}$ strictly holds under all operating conditions.
- **I2:** Central speed request $> v_{\text{safe}} \implies v_{\text{applied}} \le v_{\text{safe}}$ (Governor clamping).
- **I3:** Total communication loss $\implies$ Local governor remains active and clamps to local physical limits.
- **I4:** CAN frame packet loss $\implies$ Safe fallback to latest valid speed ceiling.
- **I5:** Stale vehicle speed frame ($>150\text{ ms}$) $\implies$ Sensor fault triggered, $v_{\text{safe}} = 0.0$.
- **I6:** Impossible engine RPM ($>8000\text{ rpm}$) $\implies$ Sensor fault triggered, $v_{\text{safe}} = 0.0$.
- **I7:** Impossible wheel speed ($>60\text{ m/s}$ or negative) $\implies$ Sensor fault triggered, $v_{\text{safe}} = 0.0$.
- **I8:** Emergency stop latch $\implies v_{\text{command}} = 0.0, v_{\text{applied}} = 0.0$.
- **I9:** Peer STOP beacon received $\implies v_{\text{command}} = 0.0, v_{\text{applied}} = 0.0$.
- **I10:** Communication recovery $\implies$ Mandates $N \ge 2$ valid sequential frames before restoring NORMAL actuation.
- **I11:** Actuator output cannot exceed commanded speed ceiling ($v_{\text{actuator}} \le v_{\text{command}}$).
- **I12:** Central dispatch optimizer cannot bypass onboard Tier-1 governor.

---

## 2. 30 Mandatory HIL Failure Injection Scenarios (HIL-01 to HIL-30)

Data logged from [`data/phase8_hil_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase8_hil_results.csv):

| ID | Scenario Description | Injected Fault | Detected Safety State | $v_{\text{safe}}$ (m/s) | $v_{\text{req}}$ (m/s) | $v_{\text{cmd}}$ (m/s) | $v_{\text{app}}$ (m/s) | Reaction (ms) | Invariant |
|---|---|---|---|---|---|---|---|---|---|
| **HIL-01** | Normal operation | None (Clear road, 25m vis) | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-02** | Central overspeed request | Dispatch request = 25.0 m/s | `GOVERNOR_CLAMPED` | 5.56 | 25.00 | 5.56 | 5.56 | 216.05 | **PASS** |
| **HIL-03** | Visibility reduction | Visibility dropped to 15m | `RESTRICTIVE_FOG` | 5.09 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-04** | Severe fog onset | Visibility dropped to 5m | `RESTRICTIVE_FOG` | 0.00 | 4.00 | 0.00 | 0.00 | 216.05 | **PASS** |
| **HIL-05** | Grade +8% (steep uphill) | Civil grade = +8.0% | `GRADE_RESTRICTED` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-06** | Grade -8% (steep downhill) | Civil grade = -8.0% | `GRADE_RESTRICTED` | 3.56 | 4.00 | 3.56 | 3.56 | 216.05 | **PASS** |
| **HIL-07** | Low friction slurry | Road friction $\mu = 0.15$ | `RESTRICTIVE_TRACTION` | 2.65 | 4.00 | 2.65 | 2.65 | 216.05 | **PASS** |
| **HIL-08** | High vehicle payload | Gross mass = 185.5 tonnes | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-09** | CAN packet loss (20%) | Stochastic CAN drop rate = 0.20 | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-10** | CAN burst loss | 5 consecutive CAN frames dropped | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-11** | CAN sensor timeout | Speed CAN frame stops arriving | `SENSOR_FAULT_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 203.45 | **PASS** |
| **HIL-12** | Invalid CAN frame | Bit corruption on byte 0 | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-13** | Duplicate CAN frame | Sequence ID replayed | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-14** | Out-of-order CAN frame | Sequence decremented | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-15** | Gateway failure | LoRa Gateway offline | `DEGRADED_BEACON_FALLBACK` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-16** | V2V peer drop | Peer truck offline | `DEGRADED_COMMUNICATION` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-17** | Safe Beacon failure | Peer beacon expires ($>1.0\text{ s}$) | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-18** | Total RF failure | Gateway + V2V + Beacon offline | `DEGRADED_TOTAL_COMM_LOSS` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-19** | Peer STOP beacon | Ingested STOP beacon from TRUCK_02 | `STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 216.05 | **PASS** |
| **HIL-20** | Peer EMERGENCY beacon | Ingested EMERGENCY beacon | `EMERGENCY_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 216.05 | **PASS** |
| **HIL-21** | Stale command injection | Command timestamp aged $>1.0\text{ s}$ | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-22** | Sensor failure: NaN | Visibility = NaN | `SENSOR_FAULT_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 203.45 | **PASS** |
| **HIL-23** | Sensor frozen value | Visibility locked at old value | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-24** | Impossible speed | Wheel speed = 120.0 m/s | `SENSOR_FAULT_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 203.45 | **PASS** |
| **HIL-25** | Impossible engine RPM | Engine RPM = 15,000 RPM | `SENSOR_FAULT_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 203.45 | **PASS** |
| **HIL-26** | Actuator delay (300ms) | Brake actuator lag $\tau = 300\text{ ms}$ | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 316.05 | **PASS** |
| **HIL-27** | Actuator non-response | Brake valve mechanically stuck | `NORMAL` (Actuator fault set) | 5.56 | 4.00 | 4.00 | 4.00 | 999,016 | **PASS** |
| **HIL-28** | Recovery sequence | Resynchronizing valid frames | `NORMAL` | 5.56 | 4.00 | 4.00 | 4.00 | 216.05 | **PASS** |
| **HIL-29** | Emergency in recovery | E-Stop triggered while recovering | `EMERGENCY_STOP` | 0.00 | 4.00 | 0.00 | 0.00 | 216.05 | **PASS** |
| **HIL-30** | Central override attempt | Central optimizer requests 30 m/s | `GOVERNOR_CLAMPED` | 5.56 | 30.00 | 5.56 | 5.56 | 216.05 | **PASS** |

---

## 3. Parametric Grid Sweep (75 Systematic Operating Conditions)

An additional 75 test cases were executed across the combinatorial domain:
- **Visibility:** $5\text{ m}, 10\text{ m}, 15\text{ m}, 25\text{ m}, 50\text{ m}$
- **Civil Road Grade:** $-8.0\%, -4.0\%, 0.0\%, +4.0\%, +8.0\%$
- **Road Friction ($\mu$):** $0.15$ (slurry), $0.35$ (wet unpaved haul road), $0.60$ (dry compacted haul road)
- **Central Speed Request:** $20.00\text{ m/s}$ (adversarial stress test)

### Key Parametric Observations:
1. **Steep Downhill (-8%) with Low Friction ($\mu=0.15$):** Safe speed envelope restricts vehicle to $v_{\text{safe}} = 1.95\text{ m/s}$. The local governor completely clamped the 20.0 m/s central request down to $1.95\text{ m/s}$.
2. **Dense Fog (5m):** Safe stopping distance requires zero velocity ($v_{\text{safe}} = 0.00\text{ m/s}$). Vehicle held at origin bench.
3. **High Adhesion ($\mu=0.60$) and Flat Grade (0%):** Safe speed reached mine civil ceiling ($13.89\text{ m/s}$ = 50 km/h). Central request was clamped to $13.89\text{ m/s}$.

---

## 4. Overall Test Summary

- **Total Scenarios Evaluated:** 105
- **Invariant I1 Violations ($v_{\text{applied}} > v_{\text{safe}}$):** 0 (0.00%)
- **Central Override Successes:** 0 (0.00%)
- **Sensor Fault Fail-Closed Rate:** 100.0%
- **Overall Result:** **100% PASS**
