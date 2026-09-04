# FOG-ORCHESTRATOR 2.0 — INTEGRATION ADAPTER REQUIREMENTS (AUDIT PART 8)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Specifications for Required Integration Adapters for Future Controlled Integration

---

## 1. Adapter 1: Vehicle ID Mapper Adapter
- **Input**: Physical `vehicle_id` (`TRUCK_01`, `TRUCK_02`).
- **Transformation**: Maps physical hardware IDs to Digital Twin fleet identifiers (`TRUCK_01` $\rightarrow$ `HIL_DUMPER_01`).
- **Output**: Canonical string matching Digital Twin contracts (`contracts.py`).
- **Failure Behavior**: Unmapped IDs are rejected silently with error logging.
- **Validation Method**: Unit test verifying bidirectional ID lookup dictionary.

---

## 2. Adapter 2: Unit Converter Adapter
- **Input**: Wheel `RPM` float, vehicle scale parameters.
- **Transformation**: $v = \frac{\text{RPM} \cdot 2\pi r}{60}$, then applies kinematic scale factor $\lambda_{\text{scale}} \approx 0.27$.
- **Output**: Scaled linear speed $v$ in $\text{m/s}$.
- **Failure Behavior**: Clamps negative or non-numeric values to $0.0\text{ m/s}$.
- **Validation Method**: Numerical assertion comparing RPM input against exact analytical m/s output.

---

## 3. Adapter 3: IMU Processor Adapter
- **Input**: MPU6050 raw LSB telemetry (`AcX`, `AcY`, `AcZ`, `GyX`, `GyY`, `GyZ`).
- **Transformation**: Converts LSB to physical units ($a = \frac{\text{Ac}}{16384} \cdot 9.81\text{ m/s}^2$, $\omega = \frac{\text{Gy}}{131} \cdot \frac{\pi}{180}\text{ rad/s}$).
- **Output**: Normalized `acceleration` $\{x, y, z\}$ and `gyroscope` $\{x, y, z\}$ dict.
- **Failure Behavior**: Values exceeding physical limits ($\pm 16g$) are clamped.
- **Validation Method**: Verification test validating gravity vector ($9.81\text{ m/s}^2$) at rest.

---

## 4. Adapter 4: Time Adapter
- **Input**: Host POSIX timestamp (`1787935000.125`).
- **Transformation**: Computes simulation time offset ($\Delta T = T_{\text{host}} - t_{\text{sim}}$).
- **Output**: Aligned simulation timestamp matching Digital Twin discrete timesteps.
- **Failure Behavior**: Timestamps lagging by $> 3.0\text{s}$ trigger `STALE` status.
- **Validation Method**: Assertion testing monotonicity across 1,000 synthetic timestamps.

---

## 5. Adapter 5: Coordinate Mapper Adapter
- **Input**: Dead reckoning speed $v$ and yaw rate $\omega$.
- **Transformation**: Kinematic position integration ($x_{k+1} = x_k + v \cdot \cos\theta \cdot \Delta t$, $y_{k+1} = y_k + v \cdot \sin\theta \cdot \Delta t$) mapped onto mine graph segment.
- **Output**: Estimated mine coordinates $(X, Y)$ and `road_segment_id`.
- **Failure Behavior**: Out-of-bounds positions reset to nearest mine entry node.
- **Validation Method**: Map matching verification test on mine graph.

---

## 6. Adapter 6: Telemetry Quality Filter Adapter
- **Input**: Vehicle heartbeat timestamp and sequence numbers (`SEQ`).
- **Transformation**: Evaluates heartbeat age ($<3.0\text{s} \rightarrow \text{ONLINE}$, $3.0-10.0\text{s} \rightarrow \text{STALE}$, $>10.0\text{s} \rightarrow \text{OFFLINE}$).
- **Output**: Filtered telemetry stream with verified quality flags (`communication_status`).
- **Failure Behavior**: Flags stale data explicitly (`is_stale: true`).
- **Validation Method**: Synthetic dropout test suite.

---

## 7. Adapter 7: Command Adapter
- **Input**: Digital Twin advisory target speed ($v_{\text{rec}}$).
- **Transformation**: Constructs canonical `HMICommandRequest`, applies scaling, formats `command_id`.
- **Output**: Dispatch command string formatted for HMI Backend `/api/commands`.
- **Failure Behavior**: Unsafe recommendations ($> 12.0\text{ m/s}$) clamped before dispatch.
- **Validation Method**: Integration test verifying command generation and ACK tracking.
