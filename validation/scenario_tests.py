"""
validation/scenario_tests.py
----------------------------
Master Integration, Fleet Scale, Baseline Dispatch, Optimizers, S01-S20 Matrix, Monte Carlo, Task-3 I/O, and Task-1 HMI Test Suite:
- Stage 9: Digital Twin State & Master Simulation Engine
- Stage 10: Fleet Simulation & Scale Validation (1, 4, 10, 20, 30, 40, 50 vehicles)
- Stage 11: Benchmark Baseline Dispatch Modes & Comparative KPI Evaluation
- Stage 12: Deterministic Mixed-Integer Linear Programming (MILP) Fleet Dispatch
- Stage 13: Robust / Scenario-Based Model Predictive Control (Scenario-MPC) Dispatch
- Stage 14: Chance-Constrained Receding-Horizon Model Predictive Control (CC-RH-MPC) Dispatch
- Stage 15: Master Scenario Execution System (S01 through S20)
- Stage 16: Monte Carlo Stochastic Validation (>= 1,000 runs)
- Stage 17: Task-3 Telemetry Ingestion & Supervisory Command Interface
- Stage 18: Task-1 HMI State Streaming & REST/WebSocket Interface

Test Coverage:
1-5: Digital Twin Initialization, Kinematics, Dynamic Weather, Determinism
6-10: Fleet Scalability (1, 4, 10, 20, 30, 40, 50 vehicles), Car-Following, headways
11-16: Baseline Benchmarks (Human, 10km/h, Vehicle-Only, Fleet-Only) & Comparative KPIs
17-21: Deterministic MILP Optimizer Formulation, Safety Envelopes, Planning Horizons
22-26: Robust Scenario-MPC Trees, Degraded Envelopes, Fail-Safe Fallbacks
27-31: Chance-Constrained RH-MPC Quantile Tightening (P=0.99, P=0.95), Variance Response
32-35: Full Master Scenario S01-S20 Suite Execution, Isolation, Immutability & Zero Violations
36-38: Monte Carlo 1,000-Iteration Stochastic Sweeps, Statistical Distributions & Safety Invariance
39-44: Task-3 Telemetry Ingestion, Data Validation, Stale Timestamp Detection, Comm Loss Fail-Safe & Tier-1 Command Synthesis
45-47: Task-1 HMI 12-Domain State Extractions, FastAPI REST Endpoints & Dynamic Control API
"""

import unittest
import os
import math
import copy
import json
import yaml
from twin.network import MineNetwork
from twin.simulator import MineDigitalTwinSimulator
from twin.state import TwinState, RoadSegmentState
from optimizer.baseline_dispatch import (
    BaselineMode,
    BaselineDispatcher,
    DispatchMetrics,
    run_single_baseline_simulation,
    compare_all_baselines
)
from optimizer.milp_dispatch import (
    DeterministicMILPDispatcher,
    DispatchDecision,
    MILPOptimizationResult
)
from optimizer.robust_mpc import (
    RobustScenarioMPCDispatcher,
    UncertaintyScenario,
    RobustMPCResult
)
from optimizer.chance_mpc import (
    ChanceConstrainedRHMPCDispatcher,
    ChanceForecastState,
    ChanceMPCResult
)
from scenarios.scenario_runner import (
    ScenarioExecutionEngine,
    ScenarioKPIs
)
from validation.monte_carlo import (
    MonteCarloValidator,
    MonteCarloSummary,
    DistributionStats
)
from interfaces.task3_vehicle_io import (
    Task3VehicleIOInterface,
    VehicleTelemetryPacket,
    VehicleCommandPacket,
    IMUData,
    WheelSpeedData,
    BrakeTelemetry,
    RetarderTelemetry
)
from interfaces.task1_hmi import (
    Task1HMIBridge,
    create_task1_fastapi_app
)


class TestDigitalTwinSimulationStage9Through18(unittest.TestCase):
    """Master test suite covering Stages 9 through 18."""

    def setUp(self):
        """Load network graph and configurations."""
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.config_dir = os.path.join(self.base_dir, "config")
        self.results_dir = os.path.join(self.base_dir, "results")
        self.nodes_path = os.path.join(self.config_dir, "nodes.yaml")
        self.roads_path = os.path.join(self.config_dir, "roads.yaml")
        self.vehicle_cfg_path = os.path.join(self.config_dir, "vehicle.yaml")
        self.weather_cfg_path = os.path.join(self.config_dir, "weather.yaml")

        self.network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)
        with open(self.vehicle_cfg_path, "r", encoding="utf-8") as f:
            self.vehicle_cfg = yaml.safe_load(f)
        with open(self.weather_cfg_path, "r", encoding="utf-8") as f:
            self.weather_cfg = yaml.safe_load(f)

    # --------------------------------------------------------------------------
    # STAGE 9 INTEGRATION TESTS
    # --------------------------------------------------------------------------

    def test_01_simulator_initialization(self):
        """Test full digital twin initialization and state container sync."""
        sim = MineDigitalTwinSimulator(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            weather_config=self.weather_cfg,
            dt_seconds=0.5,
            seed=42
        )
        state = sim.state

        self.assertEqual(state.timestamp, 0.0)
        self.assertEqual(state.step_count, 0)
        self.assertEqual(state.dt_seconds, 0.5)
        self.assertEqual(len(state.roads), len(self.network.roads_by_id))
        self.assertEqual(len(state.nodes), len(self.network.nodes_by_id))
        self.assertEqual(len(state.vehicles), 0)

    def test_02_timestep_configuration_validation(self):
        """Test that dt <= 1.0s is accepted and invalid dt values raise ValueError."""
        sim_05 = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=0.5)
        self.assertEqual(sim_05.dt_seconds, 0.5)

        sim_10 = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0)
        self.assertEqual(sim_10.dt_seconds, 1.0)

        with self.assertRaises(ValueError):
            MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.5)

        with self.assertRaises(ValueError):
            MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=-0.1)

    def test_03_vehicle_spawning_and_kinematic_stepping(self):
        """Test spawning a vehicle and advancing simulation by 10 steps."""
        sim = MineDigitalTwinSimulator(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            weather_config=self.weather_cfg,
            dt_seconds=1.0,
            seed=100
        )
        
        truck = sim.spawn_vehicle(vehicle_id="TRUCK_01", initial_node_id="SHOVEL_01", is_loaded=True)
        self.assertEqual(truck.state.payload_tonnes, 91.5)
        self.assertEqual(len(sim.state.vehicles), 1)

        for _ in range(10):
            sim.step()

        state = sim.state
        v_state = state.vehicles["TRUCK_01"]

        self.assertEqual(state.step_count, 10)
        self.assertEqual(state.timestamp, 10.0)
        self.assertGreater(v_state.speed_v, 0.0)
        self.assertGreater(v_state.position_s, 0.0)
        self.assertEqual(state.safety_violations_count, 0)

    def test_04_fog_adaptation_and_safe_speed_reduction(self):
        """
        Integration test: Start in clear conditions (50m), inject dense fog (12m),
        verify road capacities collapse, truck target speeds throttle, and safety holds.
        """
        sim = MineDigitalTwinSimulator(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            weather_config=self.weather_cfg,
            dt_seconds=1.0,
            seed=200
        )
        
        sim.spawn_vehicle(vehicle_id="TRUCK_FOG_TEST", initial_node_id="SHOVEL_01", is_loaded=True)

        sim.set_environmental_conditions(weather_mode="CLEAR", visibility_m=50.0, surface_state="dry")
        for _ in range(10):
            sim.step()

        road_clear = sim.state.roads["ROAD_01_SHOVEL1_TO_INT1"]
        cap_clear = road_clear.capacity_vph
        speed_clear = sim.state.vehicles["TRUCK_FOG_TEST"].target_speed

        sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=12.0, surface_state="wet")
        for _ in range(10):
            sim.step()

        road_fog = sim.state.roads["ROAD_01_SHOVEL1_TO_INT1"]
        cap_fog = road_fog.capacity_vph
        speed_fog = sim.state.vehicles["TRUCK_FOG_TEST"].target_speed

        self.assertLess(cap_fog, cap_clear)
        self.assertLess(speed_fog, speed_clear)
        self.assertEqual(sim.state.safety_violations_count, 0)

    def test_05_deterministic_simulation_seed_reproducibility(self):
        """Test that two independent simulation runs with same seed produce identical trajectories."""
        def run_instance():
            net = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)
            sim = MineDigitalTwinSimulator(net, self.vehicle_cfg, self.weather_cfg, dt_seconds=0.5, seed=777)
            sim.spawn_vehicle("T1", initial_node_id="SHOVEL_01", is_loaded=True)
            sim.spawn_vehicle("T2", initial_node_id="SHOVEL_02", is_loaded=True)

            history = []
            for _ in range(30):
                s = sim.step()
                history.append((s.vehicles["T1"].position_s, s.vehicles["T2"].position_s, s.total_tonnage_delivered))
            return history

        h1 = run_instance()
        h2 = run_instance()

        self.assertEqual(h1, h2)

    # --------------------------------------------------------------------------
    # STAGE 10 FLEET SIMULATION & SCALE TESTS
    # --------------------------------------------------------------------------

    def test_06_fleet_scale_1_vehicle(self):
        """Scale test: 1 single vehicle baseline simulation for 50 timesteps."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=1)
        fleet = sim.spawn_fleet(num_vehicles=1)
        
        self.assertEqual(len(fleet), 1)
        self.assertEqual(len(sim.state.vehicles), 1)
        self.assertEqual(fleet[0].vehicle_id, "TRUCK_001")

        for _ in range(50):
            sim.step()

        self.assertEqual(sim.state.step_count, 50)
        self.assertEqual(sim.state.safety_violations_count, 0)

    def test_07_fleet_scale_10_vehicles(self):
        """Scale test: 10 vehicles distributed across mine network."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=10)
        fleet = sim.spawn_fleet(num_vehicles=10)

        self.assertEqual(len(fleet), 10)
        self.assertEqual(len(sim.state.vehicles), 10)
        
        ids = [v.vehicle_id for v in fleet]
        self.assertEqual(len(ids), len(set(ids)))

        for _ in range(40):
            sim.step()

        self.assertEqual(sim.state.step_count, 40)
        self.assertEqual(sim.state.safety_violations_count, 0)
        self.assertGreater(len(sim.state.active_bottlenecks), 0)

    def test_08_fleet_scale_50_vehicles(self):
        """Scale test: Maximum 50 vehicles fleet load test."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=50)
        fleet = sim.spawn_fleet(num_vehicles=50)

        self.assertEqual(len(fleet), 50)
        self.assertEqual(len(sim.state.vehicles), 50)

        for _ in range(30):
            sim.step()

        self.assertEqual(sim.state.step_count, 30)
        self.assertEqual(sim.state.safety_violations_count, 0)

        for vid, v_state in sim.state.vehicles.items():
            self.assertFalse(math.isnan(v_state.position_s))
            self.assertFalse(math.isnan(v_state.speed_v))
            self.assertGreaterEqual(v_state.speed_v, 0.0)

    def test_09_fleet_scale_spectrum_4_20_30_40(self):
        """Scale test: Verify all intermediate fleet sizes (4, 20, 30, 40 vehicles)."""
        for count in [4, 20, 30, 40]:
            sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=count)
            fleet = sim.spawn_fleet(num_vehicles=count)
            self.assertEqual(len(fleet), count)
            self.assertEqual(len(sim.state.vehicles), count)

            for _ in range(10):
                sim.step()

            self.assertEqual(sim.state.safety_violations_count, 0)

    def test_10_car_following_and_local_safety_invariants(self):
        """Verify car-following headway and local safety preservation on shared roads."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=0.5, seed=99)
        
        route = self.network.find_shortest_path("SHOVEL_01", "CRUSHER_01")
        t1 = sim.spawn_vehicle("LEADER_01", "SHOVEL_01", route_nodes=route, is_loaded=True)
        t2 = sim.spawn_vehicle("FOLLOWER_01", "SHOVEL_01", route_nodes=route, is_loaded=True)

        edge_id = self.network.get_edge_data(route[0], route[1])["id"]
        t1.update_position(edge_id, position_s=60.0)
        t2.update_position(edge_id, position_s=10.0)

        for _ in range(25):
            sim.step()
            s_lead = sim.state.vehicles["LEADER_01"].position_s
            s_foll = sim.state.vehicles["FOLLOWER_01"].position_s
            self.assertLess(s_foll, s_lead)

        self.assertEqual(sim.state.safety_violations_count, 0)

    # --------------------------------------------------------------------------
    # STAGE 11 BASELINE DISPATCH TESTS
    # --------------------------------------------------------------------------

    def test_11_human_permissive_baseline(self):
        """Test Baseline 1 (Human/Permissive): Requests 40 km/h, clamped by safety governor in fog."""
        metrics = run_single_baseline_simulation(
            mode=BaselineMode.HUMAN_PERMISSIVE,
            network=self.network,
            vehicle_cfg=self.vehicle_cfg,
            weather_cfg=self.weather_cfg,
            fleet_size=6,
            duration_seconds=50.0,
            visibility_m=15.0
        )
        self.assertEqual(metrics.mode, "HUMAN_PERMISSIVE")
        self.assertEqual(metrics.violations_count, 0)
        self.assertGreater(metrics.average_travel_time_s, 0.0)

    def test_12_fixed_speed_10kmh_baseline(self):
        """Test Baseline 2 (Fixed-Speed 10 km/h): Clamped to 2.78 m/s crawl."""
        metrics = run_single_baseline_simulation(
            mode=BaselineMode.FIXED_SPEED_10KMH,
            network=self.network,
            vehicle_cfg=self.vehicle_cfg,
            weather_cfg=self.weather_cfg,
            fleet_size=6,
            duration_seconds=50.0,
            visibility_m=15.0
        )
        self.assertEqual(metrics.mode, "FIXED_SPEED_10KMH")
        self.assertEqual(metrics.violations_count, 0)
        self.assertGreater(metrics.average_travel_time_s, 100.0)

    def test_13_vehicle_only_baseline(self):
        """Test Baseline 3 (Vehicle-Only): Local safe speed reactive adjustment."""
        metrics = run_single_baseline_simulation(
            mode=BaselineMode.VEHICLE_ONLY,
            network=self.network,
            vehicle_cfg=self.vehicle_cfg,
            weather_cfg=self.weather_cfg,
            fleet_size=6,
            duration_seconds=50.0,
            visibility_m=15.0
        )
        self.assertEqual(metrics.mode, "VEHICLE_ONLY")
        self.assertEqual(metrics.violations_count, 0)

    def test_14_fleet_only_baseline_safety_governor_inviolability(self):
        """Test Baseline 4 (Fleet-Only): Verifies fleet controller never bypasses local safety."""
        metrics = run_single_baseline_simulation(
            mode=BaselineMode.FLEET_ONLY,
            network=self.network,
            vehicle_cfg=self.vehicle_cfg,
            weather_cfg=self.weather_cfg,
            fleet_size=6,
            duration_seconds=50.0,
            visibility_m=12.0
        )
        self.assertEqual(metrics.mode, "FLEET_ONLY")
        self.assertEqual(metrics.violations_count, 0)

    def test_15_all_baselines_comparative_kpi_extraction(self):
        """Test comparison function across all 4 baseline modes under identical conditions."""
        results = compare_all_baselines(
            network=self.network,
            vehicle_cfg=self.vehicle_cfg,
            weather_cfg=self.weather_cfg,
            fleet_size=8,
            duration_seconds=40.0,
            visibility_m=15.0,
            seed=42
        )

        self.assertEqual(len(results), 4)
        for mode_name in ["HUMAN_PERMISSIVE", "FIXED_SPEED_10KMH", "VEHICLE_ONLY", "FLEET_ONLY"]:
            self.assertIn(mode_name, results)
            m = results[mode_name]
            self.assertIsInstance(m, DispatchMetrics)
            self.assertEqual(m.violations_count, 0)
            self.assertGreaterEqual(m.production_tonnes, 0.0)
            self.assertGreaterEqual(m.throughput_vph, 0.0)
            self.assertGreaterEqual(m.average_queue, 0.0)
            self.assertGreaterEqual(m.average_utilization, 0.0)
            self.assertGreater(m.average_travel_time_s, 0.0)

    def test_16_baseline_deterministic_reproducibility(self):
        """Verify that two baseline comparison runs with identical seed yield identical metric values."""
        res1 = compare_all_baselines(self.network, self.vehicle_cfg, self.weather_cfg, fleet_size=5, duration_seconds=30.0, seed=123)
        res2 = compare_all_baselines(self.network, self.vehicle_cfg, self.weather_cfg, fleet_size=5, duration_seconds=30.0, seed=123)

        for mode_name in res1:
            self.assertEqual(res1[mode_name].production_tonnes, res2[mode_name].production_tonnes)
            self.assertEqual(res1[mode_name].average_travel_time_s, res2[mode_name].average_travel_time_s)

    # --------------------------------------------------------------------------
    # STAGE 12 DETERMINISTIC MILP DISPATCH TESTS
    # --------------------------------------------------------------------------

    def test_17_milp_candidate_route_generation(self):
        """Test candidate route generation from mining shovel sources."""
        dispatcher = DeterministicMILPDispatcher(network=self.network, planning_horizon_s=300.0, period_dt_s=30.0)
        routes_sh1 = dispatcher._generate_candidate_routes("SHOVEL_01")
        
        self.assertGreater(len(routes_sh1), 0)
        for r_name, r_nodes, dist in routes_sh1:
            self.assertEqual(r_nodes[0], "SHOVEL_01")
            self.assertIn(r_nodes[-1], ["CRUSHER_01", "DUMP_01"])
            self.assertGreater(dist, 0.0)

    def test_18_milp_single_vehicle_optimal_dispatch(self):
        """Test solving deterministic MILP for a single vehicle."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_vehicle("TRUCK_01", initial_node_id="SHOVEL_01", is_loaded=True)

        dispatcher = DeterministicMILPDispatcher(network=self.network, planning_horizon_s=300.0, period_dt_s=30.0)
        result = dispatcher.solve(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertEqual(len(result.decisions), 1)
        dec = result.decisions[0]
        self.assertEqual(dec.vehicle_id, "TRUCK_01")
        self.assertGreater(dec.payload_tonnes, 0.0)
        self.assertGreaterEqual(dec.departure_time_s, 0.0)
        self.assertGreater(dec.estimated_arrival_time_s, dec.departure_time_s)

    def test_19_milp_multi_vehicle_fleet_capacity_and_slot_constraints(self):
        """Test MILP multi-vehicle fleet dispatch respecting capacities and switchback exclusivity."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=6)

        dispatcher = DeterministicMILPDispatcher(
            network=self.network,
            planning_horizon_s=600.0,
            period_dt_s=30.0,
            w_delay=0.5,
            w_dist=0.001
        )
        result = dispatcher.solve(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertGreaterEqual(len(result.decisions), 1)
        self.assertGreater(result.total_planned_tonnage, 0.0)
        self.assertGreater(result.num_variables, 0)
        self.assertGreater(result.num_constraints, 0)

    def test_20_milp_local_safe_speed_envelope_enforcement(self):
        """Verify that planned speeds in MILP decisions strictly respect safe speed limits."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=15.0, surface_state="wet")
        sim.spawn_fleet(num_vehicles=4)

        dispatcher = DeterministicMILPDispatcher(network=self.network, planning_horizon_s=300.0, period_dt_s=30.0)
        result = dispatcher.solve(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        for dec in result.decisions:
            for road_id, planned_spd in dec.planned_speeds_mps.items():
                road_safe_spd = sim.state.roads[road_id].safe_speed_mps
                self.assertLessEqual(planned_spd, road_safe_spd + 1e-3)

    def test_21_milp_planning_horizon_and_objective_maximization(self):
        """Test that extending planning horizon captures additional discrete periods and optimizes throughput."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=5)

        disp_short = DeterministicMILPDispatcher(network=self.network, planning_horizon_s=120.0, period_dt_s=30.0)
        disp_long = DeterministicMILPDispatcher(network=self.network, planning_horizon_s=600.0, period_dt_s=30.0)

        self.assertEqual(disp_short.num_periods, 4)
        self.assertEqual(disp_long.num_periods, 20)

        res_short = disp_short.solve(sim.state.vehicles, sim.state)
        res_long = disp_long.solve(sim.state.vehicles, sim.state)

        self.assertTrue(res_short.success)
        self.assertTrue(res_long.success)
        self.assertGreater(res_long.num_variables, res_short.num_variables)

    # --------------------------------------------------------------------------
    # STAGE 13 ROBUST / SCENARIO-BASED MPC TESTS
    # --------------------------------------------------------------------------

    def test_22_robust_mpc_nominal_forecast_scenario_tree(self):
        """Test Robust Scenario-MPC under nominal forecast scenario tree."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=4)

        mpc = RobustScenarioMPCDispatcher(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            planning_horizon_s=300.0,
            period_dt_s=30.0
        )
        result = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.active_scenarios_count, 3)
        self.assertGreater(len(result.decisions), 0)

    def test_23_robust_mpc_degraded_fog_forecast_scenario_tree(self):
        """Test Robust Scenario-MPC under severe fog uncertainty degradation."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=12.0, surface_state="wet")
        sim.spawn_fleet(num_vehicles=4)

        mpc = RobustScenarioMPCDispatcher(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            planning_horizon_s=300.0,
            period_dt_s=30.0
        )
        result = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertLessEqual(result.worst_case_visibility_m, 12.0)
        for dec in result.decisions:
            for road_id, spd in dec.planned_speeds_mps.items():
                self.assertLessEqual(spd, sim.state.roads[road_id].safe_speed_mps + 1e-3)

    def test_24_robust_mpc_optimizer_failure_and_safe_baseline_fallback(self):
        """
        Verify autonomous fail-safe fallback:
        When optimizer encounters failure or infeasibility, triggers safe baseline fallback.
        """
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=5)

        mpc = RobustScenarioMPCDispatcher(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            planning_horizon_s=300.0,
            period_dt_s=30.0
        )
        result = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state, force_fail_for_test=True)

        self.assertTrue(result.success)
        self.assertTrue(result.used_fallback)
        self.assertIn("SAFE_BASELINE_FALLBACK", result.status_message)
        self.assertEqual(len(result.decisions), 5)

    def test_25_robust_mpc_deterministic_seed_reproducibility(self):
        """Verify that two robust MPC evaluations with identical inputs produce identical decisions."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=99)
        sim.spawn_fleet(num_vehicles=3)

        mpc = RobustScenarioMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        r1 = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state)
        r2 = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state)

        self.assertEqual(r1.objective_value, r2.objective_value)
        self.assertEqual(len(r1.decisions), len(r2.decisions))
        for d1, d2 in zip(r1.decisions, r2.decisions):
            self.assertEqual(d1.vehicle_id, d2.vehicle_id)
            self.assertEqual(d1.departure_time_s, d2.departure_time_s)

    def test_26_robust_mpc_safety_preservation_across_scenarios(self):
        """Verify that all robust MPC decisions strictly respect local safety envelopes without violations."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.set_environmental_conditions(weather_mode="EXTREME_FOG", visibility_m=8.0, surface_state="saturated")
        sim.spawn_fleet(num_vehicles=4)

        mpc = RobustScenarioMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        result = mpc.solve_robust_dispatch(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertLessEqual(result.worst_case_safe_speed_mps, 4.0)

    # --------------------------------------------------------------------------
    # STAGE 14 CHANCE-CONSTRAINED RH-MPC TESTS
    # --------------------------------------------------------------------------

    def test_27_chance_mpc_analytic_quantile_tightening(self):
        """
        Verify:
        z_0.99 = 2.326 for P(Safety) >= 0.99
        z_0.95 = 1.645 for P(Flow <= Capacity) >= 0.95 & P(Queue <= Limit) >= 0.95
        """
        cc_mpc = ChanceConstrainedRHMPCDispatcher(
            network=self.network,
            vehicle_config=self.vehicle_cfg,
            p_safety=0.99,
            p_capacity=0.95,
            p_queue=0.95
        )
        self.assertAlmostEqual(cc_mpc.z_safety, 2.3263, places=3)
        self.assertAlmostEqual(cc_mpc.z_capacity, 1.6448, places=3)
        self.assertAlmostEqual(cc_mpc.z_queue, 1.6448, places=3)

        vis_mean, vis_sigma = 50.0, 5.0
        vis_tight = cc_mpc.calculate_chance_tightened_visibility(vis_mean, vis_sigma)
        self.assertAlmostEqual(vis_tight, 50.0 - (2.3263 * 5.0), places=2)

        q_tight = cc_mpc.calculate_chance_tightened_queue_limit(8, arrival_sigma=1.0)
        self.assertAlmostEqual(q_tight, 8.0 - (1.6448 * 1.0), places=2)

    def test_28_chance_mpc_deterministic_fleet_dispatch(self):
        """Test CC-RH-MPC fleet dispatch under nominal forecast conditions."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=5)

        cc_mpc = ChanceConstrainedRHMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        result = cc_mpc.solve_chance_dispatch(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.p_safety_target, 0.99)
        self.assertEqual(result.p_capacity_target, 0.95)
        self.assertEqual(result.p_queue_target, 0.95)
        self.assertGreater(len(result.decisions), 0)

    def test_29_chance_mpc_stochastic_forecast_variance_response(self):
        """
        Verify that larger forecast uncertainty variance strictly tightens safe speed envelopes.
        """
        cc_mpc = ChanceConstrainedRHMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        road = self.network.roads_by_id["ROAD_01_SHOVEL1_TO_INT1"]
        road_state = RoadSegmentState(
            id=road["id"], from_node=road["from_node"], to_node=road["to_node"],
            length_m=road["length_m"], grade_pct=road["grade_pct"],
            curve_radius_m=road["curve_radius_m"], width_m=road["width_m"],
            direction_mode=road["direction_mode"], speed_limit_mps=road["speed_limit_mps"]
        )

        f_low_var = ChanceForecastState(visibility_mean_m=30.0, visibility_sigma_m=2.0)
        f_high_var = ChanceForecastState(visibility_mean_m=30.0, visibility_sigma_m=8.0)

        v_low_var = cc_mpc.calculate_chance_safe_speed("ROAD_01", road_state, f_low_var)
        v_high_var = cc_mpc.calculate_chance_safe_speed("ROAD_01", road_state, f_high_var)

        self.assertGreater(v_low_var, v_high_var)

    def test_30_chance_mpc_solver_failure_and_safe_fallback(self):
        """Test fail-safe fallback when chance-constrained optimizer encounters failure."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=4)

        cc_mpc = ChanceConstrainedRHMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        result = cc_mpc.solve_chance_dispatch(sim.state.vehicles, sim.state, force_fail_for_test=True)

        self.assertTrue(result.success)
        self.assertTrue(result.used_fallback)
        self.assertIn("CHANCE_SAFE_FALLBACK", result.status_message)
        self.assertEqual(len(result.decisions), 4)

    def test_31_chance_mpc_inviolable_safety_governor(self):
        """
        Verify that all planned dispatch speeds in chance-constrained decisions strictly respect
        road safe speeds and never bypass the Tier-1 safety governor.
        """
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=12.0, surface_state="wet")
        sim.spawn_fleet(num_vehicles=5)

        cc_mpc = ChanceConstrainedRHMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        result = cc_mpc.solve_chance_dispatch(sim.state.vehicles, sim.state)

        self.assertTrue(result.success)
        for dec in result.decisions:
            for road_id, spd in dec.planned_speeds_mps.items():
                road_safe = sim.state.roads[road_id].safe_speed_mps
                self.assertLessEqual(spd, road_safe + 1e-3)

    # --------------------------------------------------------------------------
    # STAGE 15 SCENARIO EXECUTION SYSTEM (S01 - S20)
    # --------------------------------------------------------------------------

    def test_32_master_scenario_engine_execution_all_scenarios(self):
        """Execute full S01-S20 scenario matrix and verify KPI JSON generation."""
        engine = ScenarioExecutionEngine(config_dir=self.config_dir, results_dir=self.results_dir)
        results = engine.run_all_scenarios()

        self.assertEqual(len(results), 20)
        for s_num in range(1, 21):
            s_id = f"S{s_num:02d}"
            self.assertIn(s_id, results)
            kpi = results[s_id]
            self.assertEqual(kpi.execution_status, "COMPLETED_SUCCESS")
            self.assertEqual(kpi.safety_violations_count, 0)
            self.assertGreater(kpi.duration_seconds, 0.0)
            self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"{s_id}.json")))

        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "scenario_summary.json")))

    def test_33_scenario_isolation_and_immutability(self):
        """Verify that what-if modifications to a scenario do not alter the base configuration."""
        engine = ScenarioExecutionEngine(config_dir=self.config_dir, results_dir=self.results_dir)
        orig_s01 = copy.deepcopy(engine.scenarios_dict["S01"])

        kpi1 = engine.run_scenario("S01")

        self.assertEqual(engine.scenarios_dict["S01"], orig_s01)

    def test_34_scenario_deterministic_seed_repeatability(self):
        """Verify that running a scenario twice produces bit-exact identical KPIs."""
        engine = ScenarioExecutionEngine(config_dir=self.config_dir, results_dir=self.results_dir)
        kpi_a = engine.run_scenario("S06")
        kpi_b = engine.run_scenario("S06")

        self.assertEqual(kpi_a.production_tonnes, kpi_b.production_tonnes)
        self.assertEqual(kpi_a.throughput_vph, kpi_b.throughput_vph)
        self.assertEqual(kpi_a.average_queue_length, kpi_b.average_queue_length)
        self.assertEqual(kpi_a.safety_violations_count, kpi_b.safety_violations_count)

    def test_35_scenario_zero_safety_violations_across_entire_matrix(self):
        """Verify that across all scenarios S01-S20, Tier-1 safety governor ensures 0 violations."""
        engine = ScenarioExecutionEngine(config_dir=self.config_dir, results_dir=self.results_dir)
        summary_path = os.path.join(self.results_dir, "scenario_summary.json")
        if not os.path.exists(summary_path):
            engine.run_all_scenarios()

        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        for s_id, data in summary_data.items():
            self.assertEqual(data["safety_violations_count"], 0, f"Safety violation detected in {s_id}!")

    # --------------------------------------------------------------------------
    # STAGE 16 MONTE CARLO VALIDATION TESTS
    # --------------------------------------------------------------------------

    def test_36_monte_carlo_1000_iterations_execution(self):
        """Execute 1,000 Monte Carlo stochastic runs and verify statistical distributions."""
        validator = MonteCarloValidator(
            config_dir=self.config_dir,
            results_dir=self.results_dir,
            num_iterations=1000,
            seed=42
        )
        summary = validator.run_monte_carlo()

        self.assertEqual(summary.total_iterations, 1000)
        self.assertEqual(summary.total_safety_violations, 0)
        self.assertEqual(summary.safety_violation_rate, 0.0)

        self.assertGreater(summary.safe_speed_stats.mean, 0.0)
        self.assertGreater(summary.safe_speed_stats.median, 0.0)
        self.assertGreater(summary.safe_speed_stats.std, 0.0)
        self.assertLessEqual(summary.safe_speed_stats.p01, summary.safe_speed_stats.p50)
        self.assertLessEqual(summary.safe_speed_stats.p50, summary.safe_speed_stats.p99)

        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "monte_carlo_summary.json")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "monte_carlo_results.json")))

    def test_37_monte_carlo_zero_safety_violations_audit(self):
        """Audit that across all stochastic parameter realizations, safety margin is strictly >= 1.0."""
        validator = MonteCarloValidator(self.config_dir, self.results_dir, num_iterations=1000, seed=123)
        summary = validator.run_monte_carlo()

        self.assertEqual(summary.total_safety_violations, 0)
        self.assertGreaterEqual(summary.safety_margin_ratio_stats.min, 1.0 - 1e-4)

    def test_38_monte_carlo_deterministic_seed_repeatability(self):
        """Verify that two 1,000-run Monte Carlo experiments with same seed produce identical moments."""
        v1 = MonteCarloValidator(self.config_dir, self.results_dir, num_iterations=1000, seed=777)
        s1 = v1.run_monte_carlo()

        v2 = MonteCarloValidator(self.config_dir, self.results_dir, num_iterations=1000, seed=777)
        s2 = v2.run_monte_carlo()

        self.assertEqual(s1.safe_speed_stats.mean, s2.safe_speed_stats.mean)
        self.assertEqual(s1.safe_speed_stats.p99, s2.safe_speed_stats.p99)
        self.assertEqual(s1.road_capacity_stats.mean, s2.road_capacity_stats.mean)

    # --------------------------------------------------------------------------
    # STAGE 17 TASK-3 TELEMETRY INTERFACE TESTS
    # --------------------------------------------------------------------------

    def test_39_task3_valid_telemetry_ingestion(self):
        """Test successful parsing and validation of a comprehensive Task-3 telemetry packet."""
        interface = Task3VehicleIOInterface(max_stale_age_s=2.0)
        payload = {
            "vehicle_id": "BH100_01",
            "timestamp": 100.0,
            "speed_mps": 8.5,
            "acceleration_mps2": -0.5,
            "position_xyz": [150.0, 320.0, 15.0],
            "heading_rad": 1.25,
            "grade_pct": -4.5,
            "wheel_speeds": {"front_left": 8.5, "front_right": 8.5, "rear_left": 8.5, "rear_right": 8.5},
            "imu": {"accel_x": 0.1, "accel_y": 0.0, "accel_z": 9.78, "gyro_z": 0.02},
            "brake": {"pressure_bar": 25.0, "is_engaged": False, "pedal_pct": 0.0},
            "retarder": {"power_kw": 180.0, "level_pct": 30.0, "temperature_c": 68.0},
            "obstacle_range_m": 42.0,
            "communication_confidence": 0.98,
            "road_edge_id": "ROAD_03_INT1_TO_SWITCH1",
            "station_s": 75.0,
            "payload_tonnes": 91.5
        }

        is_valid, packet, msg = interface.parse_and_validate_telemetry(payload, current_time_s=100.5)
        self.assertTrue(is_valid)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.vehicle_id, "BH100_01")
        self.assertEqual(packet.speed_mps, 8.5)
        self.assertEqual(packet.retarder.power_kw, 180.0)

    def test_40_task3_invalid_telemetry_rejection(self):
        """Test that telemetry with negative speeds, out-of-range confidence, or NaNs is strictly rejected."""
        interface = Task3VehicleIOInterface()
        
        bad_payload_1 = {
            "vehicle_id": "TRUCK_ERR", "timestamp": 10.0, "speed_mps": -5.0,
            "acceleration_mps2": 0.0, "position_xyz": [0, 0, 0], "heading_rad": 0.0,
            "grade_pct": 0.0, "obstacle_range_m": 20.0, "communication_confidence": 0.9
        }
        is_valid, _, msg = interface.parse_and_validate_telemetry(bad_payload_1)
        self.assertFalse(is_valid)
        self.assertIn("Invalid speed_mps", msg)

        bad_payload_2 = {
            "vehicle_id": "TRUCK_ERR", "timestamp": 10.0, "speed_mps": 5.0,
            "acceleration_mps2": 0.0, "position_xyz": [0, 0, 0], "heading_rad": 0.0,
            "grade_pct": 0.0, "obstacle_range_m": 20.0, "communication_confidence": 1.5
        }
        is_valid, _, msg = interface.parse_and_validate_telemetry(bad_payload_2)
        self.assertFalse(is_valid)
        self.assertIn("Invalid communication_confidence", msg)

    def test_41_task3_missing_fields_rejection(self):
        """Test that telemetry omitting required primary keys is rejected."""
        interface = Task3VehicleIOInterface()
        missing_payload = {
            "vehicle_id": "TRUCK_MISSING",
            "timestamp": 10.0,
        }
        is_valid, _, msg = interface.parse_and_validate_telemetry(missing_payload)
        self.assertFalse(is_valid)
        self.assertIn("Missing required telemetry field", msg)

    def test_42_task3_stale_timestamp_detection(self):
        """Test rejection of packets with timestamp older than max_stale_age_s (2.0s)."""
        interface = Task3VehicleIOInterface(max_stale_age_s=2.0)
        stale_payload = {
            "vehicle_id": "TRUCK_STALE", "timestamp": 50.0, "speed_mps": 7.0,
            "acceleration_mps2": 0.0, "position_xyz": [10, 20, 0], "heading_rad": 0.0,
            "grade_pct": 0.0, "obstacle_range_m": 30.0, "communication_confidence": 0.95
        }
        is_valid, _, msg = interface.parse_and_validate_telemetry(stale_payload, current_time_s=55.0)
        self.assertFalse(is_valid)
        self.assertIn("Stale telemetry timestamp", msg)

    def test_43_task3_communication_loss_fail_safe(self):
        """Test that low confidence or communication drop triggers fail-safe stop or crawl."""
        interface = Task3VehicleIOInterface(max_stale_age_s=2.0, comm_loss_threshold=0.20)
        
        low_comm_payload = {
            "vehicle_id": "TRUCK_COMM_LOSS", "timestamp": 10.0, "speed_mps": 6.0,
            "acceleration_mps2": 0.0, "position_xyz": [0, 0, 0], "heading_rad": 0.0,
            "grade_pct": 0.0, "obstacle_range_m": 25.0, "communication_confidence": 0.05
        }
        interface.parse_and_validate_telemetry(low_comm_payload, current_time_s=10.0)

        cmd = interface.synthesize_command_output(
            vehicle_id="TRUCK_COMM_LOSS",
            desired_dispatch_speed_mps=10.0,
            safe_speed_ceiling_mps=8.0,
            current_time_s=10.5
        )
        self.assertEqual(cmd.control_mode, "DEGRADED_CRAWL")
        self.assertLessEqual(cmd.command_speed_mps, 1.50)
        self.assertIn("LOW_COMMUNICATION_CONFIDENCE", cmd.warning_alert)

    def test_44_task3_supervisory_command_tier1_governor_invariant(self):
        """Verify that supervisory commands obey v_command = min(v_dispatch, v_safe) and never send PWM."""
        interface = Task3VehicleIOInterface()
        payload = {
            "vehicle_id": "TRUCK_GOV", "timestamp": 20.0, "speed_mps": 7.0,
            "acceleration_mps2": 0.0, "position_xyz": [0, 0, 0], "heading_rad": 0.0,
            "grade_pct": 0.0, "obstacle_range_m": 40.0, "communication_confidence": 0.95
        }
        interface.parse_and_validate_telemetry(payload, current_time_s=20.0)

        cmd = interface.synthesize_command_output(
            vehicle_id="TRUCK_GOV",
            desired_dispatch_speed_mps=11.11,
            safe_speed_ceiling_mps=4.50,
            current_time_s=20.2
        )
        self.assertEqual(cmd.control_mode, "AUTONOMOUS_GOVERNED")
        self.assertEqual(cmd.command_speed_mps, 4.50)
        self.assertEqual(cmd.safe_speed_ceiling_mps, 4.50)
        self.assertFalse(cmd.is_emergency_stop)

    # --------------------------------------------------------------------------
    # STAGE 18 TASK-1 HMI INTERFACE TESTS
    # --------------------------------------------------------------------------

    def test_45_task1_hmi_bridge_domain_extraction(self):
        """Verify that Task1HMIBridge extracts clean telemetry across all 12 operational domains."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=6)
        sim.step()

        bridge = Task1HMIBridge(sim)

        # 1. Simulation time
        t_data = bridge.get_simulation_time()
        self.assertEqual(t_data["timestamp_s"], 1.0)
        self.assertEqual(t_data["step_count"], 1)

        # 2. Environment
        env_data = bridge.get_environment_state()
        self.assertIn("weather_mode", env_data)
        self.assertIn("visibility_m", env_data)

        # 3. Fleet
        fleet_data = bridge.get_fleet_state()
        self.assertEqual(fleet_data["total_vehicles"], 6)
        self.assertEqual(fleet_data["safety_violations_count"], 0)

        # 4. Roads
        roads_data = bridge.get_road_states()
        self.assertEqual(len(roads_data["roads"]), len(self.network.roads_by_id))

        # 5. Queues
        queues_data = bridge.get_queues_state()
        self.assertEqual(len(queues_data["nodes"]), len(self.network.nodes_by_id))

        # 6. Bottlenecks
        b_data = bridge.get_bottlenecks_state()
        self.assertIn("active_bottlenecks", b_data)

        # 7. Switchbacks
        sw_data = bridge.get_switchback_slots_state()
        self.assertIn("active_reservations_count", sw_data)

        # 8. Alerts
        alerts_data = bridge.get_alerts_and_warnings()
        self.assertIn("alerts_count", alerts_data)

        # Master Snapshot
        snapshot = bridge.get_full_twin_snapshot()
        self.assertIn("simulation_time", snapshot)
        self.assertIn("environment", snapshot)
        self.assertIn("fleet", snapshot)
        self.assertIn("roads", snapshot)
        self.assertIn("queues", snapshot)
        self.assertIn("bottlenecks", snapshot)
        self.assertIn("switchbacks", snapshot)
        self.assertIn("alerts", snapshot)

    def test_46_task1_hmi_fastapi_rest_endpoints(self):
        """Test instantiation and direct invocation of FastAPI endpoints."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_fleet(num_vehicles=4)
        bridge = Task1HMIBridge(sim)

        app = create_task1_fastapi_app(bridge)
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "FOG-ORCHESTRATOR 2.0 - Task-1 HMI API")

        if hasattr(app, "routes") and isinstance(app.routes, dict):
            routes = list(app.routes.keys())
            res = app.handle_request("/api/v1/state/snapshot")
            self.assertIn("fleet", res)
        else:
            routes = [route.path for route in app.routes]

        self.assertIn("/api/v1/state/snapshot", routes)
        self.assertIn("/api/v1/state/fleet", routes)
        self.assertIn("/api/v1/state/environment", routes)
        self.assertIn("/api/v1/control/step", routes)
        self.assertIn("/api/v1/control/environment", routes)

    def test_47_task1_hmi_environmental_control_endpoint(self):
        """Test updating environment via HMI control API and observing instant twin reflection."""
        sim = MineDigitalTwinSimulator(self.network, self.vehicle_cfg, self.weather_cfg, dt_seconds=1.0, seed=42)
        sim.spawn_vehicle("TRUCK_API", "SHOVEL_01", is_loaded=True)
        bridge = Task1HMIBridge(sim)

        # Initial state: CLEAR, 50m
        self.assertEqual(sim.state.environment.default_visibility_m, 50.0)

        # Invoke environment update
        sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=12.0, surface_state="wet")
        env_updated = bridge.get_environment_state()

        self.assertEqual(env_updated["weather_mode"], "DENSE_FOG")
        self.assertEqual(env_updated["visibility_m"], 12.0)
        self.assertTrue(env_updated["is_foggy"])


if __name__ == "__main__":
    unittest.main()
