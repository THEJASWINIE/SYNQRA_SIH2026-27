# FOG-ORCHESTRATOR 2.0 — COORDINATE MAPPING SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Digital Twin Engineer  
**Scope**: Dead-Reckoning Trajectory Estimation and Logical Mine Coordinate Mapping Specification

---

## 1. Prototype Trajectory Kinematics

Because physical prototypes lack absolute GPS hardware, position is estimated using kinematic dead reckoning:

$$x_{k+1} = x_k + v \cdot \cos(\theta_k) \cdot \Delta t$$

$$y_{k+1} = y_k + v \cdot \sin(\theta_k) \cdot \Delta t$$

$$\theta_{k+1} = \theta_k + \omega_z \cdot \Delta t$$

where $v$ is linear speed from wheel encoder, $\omega_z$ is IMU yaw rate, and $\Delta t$ is timestep duration.

---

## 2. Logical Mine Grid Transformation

Prototype relative coordinates $(x_p, y_p)$ are mapped to Digital Twin mine grid coordinates $(x_t, y_t)$ via linear offset transformation:

$$x_t = x_{\text{node\_offset}} + x_p$$

$$y_t = y_{\text{node\_offset}} + y_p$$

- `TRUCK_01` initial mine node offset: $(100.0\text{ m}, 50.0\text{ m})$
- `TRUCK_02` initial mine node offset: $(105.0\text{ m}, 50.0\text{ m})$

---

## 3. Position Quality Flags

- **`ESTIMATED`**: Dead reckoning active with live telemetry ($<3.0\text{s}$ age).
- **`ESTIMATED_STALE`**: Telemetry interrupted; position frozen at last valid dead-reckoning state.
