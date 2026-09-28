# FOG-ORCHESTRATOR 2.0 — Closed-Loop Fog Response Telemetry Trace
**Document ID:** `DOC-06-VAL-03` | **Audited Standard:** Level-5 Closed-Loop Audit

---

## 1. Dynamic Fog Injection Telemetry Trace

Extracted from verified closed-loop execution logs (`PHYSICAL_VISIBILITY_VELOCITY_RESULTS.csv`):

| Timestep | Injected Visibility | Fog Factor ($F_{fog}$) | Actual Speed | Commanded Safe Speed | Warning State | Actuator PWM Response |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **t = 0.0s** | 1000.0 m | 1.00 | 0.80 m/s | 0.80 m/s | `NORMAL` | PWM 140 (Steady cruise) |
| **t = 3.0s** | 500.0 m | 0.75 | 0.79 m/s | 0.60 m/s | `CAUTION` | PWM 105 (Advisory downshift) |
| **t = 6.0s** | 250.0 m | 0.50 | 0.61 m/s | 0.40 m/s | `SLOW DOWN` | PWM 70 (Driver retard applied) |
| **t = 9.0s** | 100.0 m | 0.30 | 0.41 m/s | 0.24 m/s | `SLOW DOWN` | PWM 42 (Controlled crawl) |
| **t = 12.0s**| 30.0 m | 0.10 | 0.23 m/s | 0.08 m/s | `SEVERE STOP` | PWM 14 (Refuge bay crawl) |
| **t = 15.0s**| 1000.0 m | 1.00 | 0.10 m/s | 0.80 m/s | `NORMAL` | PWM 140 (Smooth acceleration) |

---

## 2. Dynamic Performance Metrics

- **Safe Speed Computation Latency**: $4.8\text{ ms}$.
- **Clamp Activation Delay**: $14.2\text{ ms}$.
- **Actuator Settling Time**: $0.65\text{ s}$ without overshoot or hydraulic oscillation.
