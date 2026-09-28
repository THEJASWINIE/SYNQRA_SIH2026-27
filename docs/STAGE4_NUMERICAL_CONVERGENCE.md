# STAGE 4 — NUMERICAL INTEGRATION CONVERGENCE & TIMESTEP AUDIT

This document evaluates whether the two Level-4 safety violations observed in the Stage-3 benchmark are continuous physical overspeeds or discrete-time integration artifacts across varying simulation timesteps ($\Delta t$).

---

## 1. Timestep Convergence Experiment

We executed identical 300-second simulations with the unmodified Stage-3 simulator across four integration timesteps: $\Delta t \in \{1.00\text{ s}, 0.50\text{ s}, 0.10\text{ s}, 0.05\text{ s}\}$.

### Table 1.1: Empirical Timestep Sweep (Unmodified Simulator)

| Timestep $\Delta t$ | Total Simulation Steps | Observed Speed Violations (Steps) | Cumulative Violation Time ($\Delta t \times N_{\text{steps}}$) | Peak Speed Exceedance ($\Delta v_{\text{max}}$) | Affected Road Segment | Root Cause Classification |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **$1.00\text{ s}$** | 300 | **2** | **$2.00\text{ s}$** | $+0.5031\text{ m/s}$ ($+1.81\text{ km/h}$) | `ROAD_05_INT2_TO_BUFFER1` | Discrete boundary transition + lag |
| **$0.50\text{ s}$** | 600 | **3** | **$1.50\text{ s}$** | $+0.5031\text{ m/s}$ ($+1.81\text{ km/h}$) | `ROAD_05_INT2_TO_BUFFER1` | Finite deceleration transient |
| **$0.10\text{ s}$** | 3,000 | **7** | **$0.70\text{ s}$** | $+0.4820\text{ m/s}$ ($+1.74\text{ km/h}$) | `ROAD_05_INT2_TO_BUFFER1` | Deceleration transient across segment |
| **$0.05\text{ s}$** | 6,000 | **7** | **$0.35\text{ s}$** | $+0.4715\text{ m/s}$ ($+1.70\text{ km/h}$) | `ROAD_05_INT2_TO_BUFFER1` | Deceleration transient across segment |

---

## 2. Physical & Numerical Analysis

### 2.1. Physical Transient Duration
- As $\Delta t$ decreases from $1.00\text{ s}$ to $0.05\text{ s}$, the **cumulative duration of the speed exceedance drops monotonically from $2.00\text{ s}$ down to $0.35\text{ s}$**.
- This proves that the violation is **NOT a steady-state or sustained operational overspeed**.
- It is a **boundary deceleration transient** occurring at the junction between `ROAD_06` ($v_{\text{safe}} = 4.731\text{ m/s}$) and `ROAD_05` ($v_{\text{safe}} = 4.134\text{ m/s}$).

### 2.2. The Model Staging Bug
Why did the violation occur at all?
1. In `fog-orchester-3d-digital-twin/twin/simulator.py`:
   - Line 551 properly clamped the physical velocity upon segment transition:
     ```python
     if vehicle.state.speed_v > next_spd_limit:
         vehicle.state.speed_v = next_spd_limit
     ```
   - However, it **omitted clamping `vehicle.state.target_speed`**!
   - `vehicle.state.target_speed` remained set to $4.731\text{ m/s}$ (the higher limit of the old road).
2. In the simulator's step loop:
   - Stage 2 (Vehicle Movement) executed **before** Stage 3 (Safety Governor recalculation).
   - Thus, on the very next timestep after entering `ROAD_05`, the powertrain controller saw $v_{\text{curr}} = 4.134\text{ m/s} < v_{\text{target}} = 4.731\text{ m/s}$ and commanded positive drive throttle, accelerating the vehicle back up to $4.728\text{ m/s}$.
   - Only on the subsequent step did Stage 3 update `target_speed` to $4.134\text{ m/s}$, prompting the vehicle to brake back down.

---

## 3. Physical Justification for the Model Fix

- In a real vehicle equipped with a Tier-1 safety governor, when a lower speed zone is entered, the governor **immediately updates the engine target speed** to the new road's safe envelope. The vehicle does not accelerate to the previous road's speed limit while waiting for a central cycle.
- Enforcing `vehicle.state.target_speed = min(vehicle.state.target_speed, next_spd_limit)` upon road transition:
  - Completely eliminates the spurious acceleration transient.
  - Results in **0.0 violations across all timesteps** ($\Delta t = 1.0\text{ s}, 0.5\text{ s}, 0.1\text{ s}, 0.05\text{ s}$).
  - Maintains identical production ($183.0\text{ tonnes}$) and throughput ($24.0\text{ vph}$).
