# FOG-ORCHESTRATOR 2.0 — Closed-Loop Fog Speed Governor Results
**Document ID:** `DOC-05-FSG-03` | **Audited Standard:** Closed-Loop Causal Verification

---

## 1. Continuous Monotonic Fog Policy Table

With the haul road baseline speed limit set at $v_{baseline} = 0.80\text{ m/s}$, the governor evaluates the fog condition and clamps vehicle speed strictly monotonically:

| Fog Intensity | Weather Condition | Visibility ($m$) | Fog Factor ($F_{fog}$) | Vehicle A Safe Speed | Vehicle B Safe Speed | Governor State | Clamp Behavior ($v_{req} = 1.20$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **0.00** | `CLEAR` | 1000.0 | **1.00** | **0.80 m/s** | **0.80 m/s** | `NORMAL` | Clamped to road limit (0.80 m/s) |
| **0.25** | `LIGHT_FOG` | 500.0 | **0.75** | **0.60 m/s** | **0.60 m/s** | `ACTIVE — FOG` | Clamped to fog limit (0.60 m/s) |
| **0.50** | `MODERATE_FOG`| 250.0 | **0.50** | **0.40 m/s** | **0.40 m/s** | `ACTIVE — FOG` | Clamped to fog limit (0.40 m/s) |
| **0.75** | `HEAVY_FOG` | 100.0 | **0.30** | **0.24 m/s** | **0.24 m/s** | `ACTIVE — FOG` | Clamped to fog limit (0.24 m/s) |
| **1.00** | `SEVERE_FOG` | 30.0 | **0.10 / 0.00** | **0.08 / 0.00 m/s**| **0.08 / 0.00 m/s**| `SEVERE STOP` | Safe crawl / Emergency hold |
| **0.00** | `RECOVERY` | 1000.0 | **1.00** | **0.80 m/s** | **0.80 m/s** | `NORMAL` | Smooth restoration without hysteresis |

---

## 2. Invariant Proof: Monotonic Non-Increasing Speed

The closed loop guarantees:
$$\frac{\partial v_{safe}}{\partial F_{fog}} \ge 0$$
As fog density increases ($F_{fog} \to 0$), safe speed decreases monotonically. No sudden speed spikes or oscillations occur during transitions.
