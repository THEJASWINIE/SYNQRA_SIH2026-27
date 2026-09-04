# AUTOMATED TEST RESULTS REPORT
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**EXECUTION DATE**: 2026-08-28  
**RUNNER**: Python 3.14.0 / pytest-9.1.1  

---

## 1. SUMMARY EXECUTION VERDICT

```
======================= 33 passed in 0.77s =======================
OVERALL VERDICT: PASSED (100% SUCCESS RATE)
```

---

## 2. DETAILED TEST RESULTS BY MODULE

| Test Module | Test Name | Execution Result | Measured Metric / Behavior |
|---|---|---|---|
| `test_data_contract.py` | `test_vehicle_state_contract` | **PASSED** | Validated `VehicleStateMessage` serialization & units |
| `test_data_contract.py` | `test_safety_state_contract` | **PASSED** | Validated `SafetyStateMessage` bounds |
| `test_data_contract.py` | `test_road_state_contract` | **PASSED** | Validated `RoadStateMessage` schema |
| `test_data_contract.py` | `test_dispatch_command_contract` | **PASSED** | Validated `DispatchCommandMessage` schema |
| `test_data_contract.py` | `test_invalid_data_contract_rejection` | **PASSED** | Rejected missing fields safely |
| `test_physics.py` | `test_stopping_distance_formula` | **PASSED** | Verified $d_{\rm stop} = v \tau + v^2/(2 a_{\rm dec})$ precision |
| `test_physics.py` | `test_v_stop_analytical_solver` | **PASSED** | Solved stopping speed quadratic equation |
| `test_physics.py` | `test_reduced_friction_physics` | **PASSED** | Verified $a_{\rm dec}$ reduction under $\mu = 0.25$ |
| `test_physics.py` | `test_downhill_grade_deceleration` | **PASSED** | Verified gravity penalty on $-8\%$ downhill grade |
| `test_safety_governor.py` | `test_safety_governor_command_clamping` | **PASSED** | Clamped central speed (12 m/s) to safe limit (5.4 m/s) |
| `test_safety_governor.py` | `test_scenario_1_clear_visibility_normal_friction` | **PASSED** | Safe speed ceiling $v_{\rm safe} > 10.0\text{ m/s}$ |
| `test_safety_governor.py` | `test_scenario_2_moderate_fog` | **PASSED** | Safe speed ceiling $v_{\rm safe} < 12.0\text{ m/s}$ |
| `test_safety_governor.py` | `test_scenario_3_dense_fog` | **PASSED** | Safe speed ceiling $v_{\rm safe} < 6.0\text{ m/s}$ |
| `test_safety_governor.py` | `test_scenario_4_dense_fog_reduced_friction` | **PASSED** | Safe speed ceiling $v_{\rm safe} < 4.5\text{ m/s}$ |
| `test_safety_governor.py` | `test_scenario_5_downhill_dense_fog` | **PASSED** | Safe speed ceiling $v_{\rm safe} < 4.0\text{ m/s}$ |
| `test_safety_governor.py` | `test_scenario_6_unsafe_central_target_speed` | **PASSED** | Clamped central target (15 m/s) to $< 4.0\text{ m/s}$ |
| `test_fog_propagation.py` | `test_fog_to_capacity_causal_chain` | **PASSED** | Verified visibility $\downarrow \implies$ safe speed $\downarrow \implies$ traversal time $\uparrow$ |
| `test_queue_model.py` | `test_queue_mass_balance_and_growth` | **PASSED** | Mass balance conserved; service timer verified |
| `test_queue_model.py` | `test_analytical_queue_dynamics_equation` | **PASSED** | Verified $Q(t+dt) = \max(0, Q(t) + \lambda - \mu)$ |
| `test_bottleneck_detection.py` | `test_bottleneck_score_calculation` | **PASSED** | Score scales monotonically with utilization & queue |
| `test_bottleneck_detection.py` | `test_dynamic_bottleneck_shift` | **PASSED** | Correctly identified Crusher as primary bottleneck |
| `test_optimizer.py` | `test_arrival_shaper_optimization_decision` | **PASSED** | Throttled shovel releases from 240s to $\ge 600\text{ s}$ |
| `test_command_flow.py` | `test_command_flow_and_acknowledgement` | **PASSED** | Emulator ingested command & returned valid ACK |
| `test_stale_data.py` | `test_stale_telemetry_detection_and_fallback` | **PASSED** | Telemetry age $> 5.0\text{ s}$ fallback $v_{\rm safe} \le 2.78\text{ m/s}$ |
| `test_failure_modes.py` | `test_failure_mode_a_twin_backend_stops` | **PASSED** | Handled twin backend stale signal |
| `test_failure_modes.py` | `test_failure_mode_b_telemetry_stops` | **PASSED** | Vehicle marked `OFFLINE` safely |
| `test_failure_modes.py` | `test_failure_mode_c_optimizer_crashes` | **PASSED** | Vehicle local governor operated safely without optimizer |
| `test_failure_modes.py` | `test_failure_mode_d_invalid_command` | **PASSED** | Invalid/comm loss command rejected |
| `test_failure_modes.py` | `test_failure_mode_e_central_speed_exceeds_safe` | **PASSED** | Local safety clamp enforced |
| `test_failure_modes.py` | `test_failure_mode_f_fog_sensor_disappears` | **PASSED** | Sensor loss fallback activated |
| `test_failure_modes.py` | `test_failure_mode_g_lora_comm_loss` | **PASSED** | LoRa comm loss fallback $v_{\rm safe} \le 2.78\text{ m/s}$ |
| `test_failure_modes.py` | `test_failure_mode_h_hmi_closes` | **PASSED** | Vehicle safety unaffected by HMI state |
| `test_end_to_end.py` | `test_full_15_step_demo_scenario` | **PASSED** | 1800s scenario replay completed; queue controlled |
