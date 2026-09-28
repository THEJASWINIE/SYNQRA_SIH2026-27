# TASK 2 Requirement Traceability Matrix

| Requirement ID | Requirement Description | Implementation File | Test ID | Evidence/Output | PASS/FAIL | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| FTR-001 | Represent G=(V,E) graph | `twin/network.py` | `test_network.py` | Graph nodes & edges instantiated | PASS | [SIMULATION] |
| FTR-002 | Road geometry properties | `twin/network.py` | `test_network.py` | length, grade, curve radius, width | PASS | [SIMULATION] |
| FTR-003 | Typed mine nodes | `twin/network.py` | `test_network.py` | SHOVEL, INTERSECTION, CRUSHER, BUFFER queue, and single-lane SWITCHBACK segments are mapped | PASS | [SIMULATION] |
| FTR-004 | Vehicle dynamics | `models/vehicle.py` | `test_physics.py` | mass, payload, speed, acceleration | PASS | [SIMULATION] |
| FTR-005 | Loaded/empty state | `models/vehicle.py` | `test_physics.py` | mass dynamically changes on load/unload | PASS | [SIMULATION] |
| FTR-006 | Longitudinal dynamics | `models/vehicle_physics.py` | `test_physics.py` | Deceleration & acceleration forces | PASS | [SIMULATION] |
| FTR-007 | Road friction model | `twin/simulator.py` | `test_physics.py` | Configurable friction coefficients | PASS | [SIMULATION] |
| FTR-008 | Grade effect on braking | `models/braking.py` | `test_physics.py` | Downhill grade limits deceleration rates | PASS | [SIMULATION] |
| FTR-009 | Visibility maps | `weather/fog_model.py` | `test_weather.py` | Spatial/temporal visibility states | PASS | [SIMULATION] |
| FTR-010 | Fog scenarios library | `scenarios/demo_v01.py` | `test_weather.py` | Replays clear, dense, recovery | PASS | [SIMULATION] |
| FTR-011 | Road condition states | `twin/simulator.py` | `test_weather.py` | wet/damp/dry friction propagation | PASS | [SIMULATION] |
| FTR-012 | Weather forecast | `weather/uncertainty.py` | `test_optimizer.py` | Mean and sample error visibility bounds | PASS | [SIMULATION] |
| FTR-013 | Safe speed & headway | `models/vehicle_physics.py` | `test_physics.py` | Safe speed calculations (v_safe) | PASS | [VERIFICATION] |
| FTR-014 | Command speed clamp | `twin/simulator.py` | `test_physics.py` | v_command = min(v_dispatch, v_safe) | PASS | [VERIFICATION] |
| FTR-015 | Road capacity math | `models/road_capacity.py` | `test_capacity.py` | C = 3600 * v / H_meters | PASS | [MATHEMATICAL] |
| FTR-016 | Service Queue models | `models/queue_model.py` | `test_queue.py` | Step discharge & finite queue length | PASS | [SIMULATION] |
| FTR-017 | Bottleneck score | `models/bottleneck.py` | `test_bottleneck.py` | Criticality + queue length utilization | PASS | [MATHEMATICAL] |
| FTR-018 | Arrival shaping | `control/arrival_shaping.py` | `test_shaping.py` | Controlled departure release delays | PASS | [SIMULATION] |
| FTR-019 | Slot reservation | `models/switchback.py` | `test_switchback.py` | Time interval overlap conflict checks | PASS | [SIMULATION] |
| FTR-020 | Post-fog recovery | `scenarios/demo_v01.py` | `test_shaping.py` | Queue dissipation without overshoots | PASS | [SIMULATION] |
| FTR-021 | Telemetry communication | `interfaces/task3_vehicle_io.py` | `test_interfaces.py` | Signal loss safe fallback mode | PASS | [VERIFICATION] |
| FTR-022 | Failure injections | `twin/simulator.py` | `test_interfaces.py` | Stale sensors, comm degradation fallback | PASS | [VERIFICATION] |
| FTR-023 | Twin state sync | `twin/simulator.py` | `test_interfaces.py` | Compiled state matches current step state | PASS | [SIMULATION] |
| FTR-024 | Rolling MPC prediction | `interfaces/task1_hmi.py` | `test_interfaces.py` | Short-horizon trajectory, queue, and production predictions exported | PASS | [VERIFICATION] |
| FTR-025 | What-if scenarios | `scenarios/demo_v01.py` | `test_optimizer.py` | Parallel forecast paths simulation | PASS | [SIMULATION] |
| FTR-026 | Fleet scalability | `twin/simulator.py` | `verify_task2_final.py` | Runs up to 100 fleet vehicles successfully | PASS | [VERIFICATION] |
| FTR-027 | Scenario replay | `twin/simulator.py` | `verify_task2_final.py` | Replays identical runs with same seed | PASS | [VERIFICATION] |
| FTR-028 | Telemetry ingestion | `interfaces/task3_vehicle_io.py` | `test_interfaces.py` | Rejects malformed ESP32 data packet | PASS | [VERIFICATION] |
| FTR-029 | HMI state formatting | `interfaces/task1_hmi.py` | `test_interfaces.py` | Matches HMI_STATE_SCHEMA contract | PASS | [VERIFICATION] |
| FTR-030 | Unified logging audit | `main.py` | `verify_task2_final.py` | Logs inputs (scenarios), decisions (releases), outputs (CSV states), warnings (comm-loss alerts), and model version ("V2.0-MVP") | PASS | [SIMULATION] |
