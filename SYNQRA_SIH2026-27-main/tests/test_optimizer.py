import unittest
import numpy as np
from optimizer.baseline_dispatch import BaselineDispatch
from optimizer.milp_dispatch import DeterministicMPC
from optimizer.robust_mpc import RobustMPC
from optimizer.chance_mpc import ChanceConstrainedMPC

class TestOptimizer(unittest.TestCase):
    def setUp(self):
        self.v_cfg = {
            "tare_mass_kg": 74000.0,
            "payload_mass_kg": 91000.0,
            "hardware_max_brake_force_n": 600000.0,
            "max_retarder_power_w": 1200000.0,
            "ecu_hydraulic_latency_s": 0.25,
            "safety_stop_margin_m": 5.0,
            "safety_headway_margin_m": 5.0,
            "min_static_headway_m": 15.5,
            "traction_speed_factor_mps": 30.0  # reference vehicle value
        }
        self.r_cfg = {
            "road_id": "ROAD_2",
            "grade_percent": -8.0,
            "friction_mu": 0.60,
            "c_rr": 0.02,
            "curve_radius_m": 50.0,
            "speed_limit_mps": 11.11
        }
        
    def test_01_baseline_dispatch(self):
        disp = BaselineDispatch(shovel_service_rate_vph=15.0)
        self.assertAlmostEqual(disp.calculate_release_delay(0.0, {}), 240.0)

    def test_02_deterministic_mpc(self):
        # 1. Clear-sky case with no crusher bottleneck (crusher_mu >= shovel_mu)
        mpc_clear = DeterministicMPC(horizon_s=1800.0, step_s=10.0, crusher_service_rate_vph=15.0, 
                                     shovel_service_rate_vph=15.0, vehicle_config=self.v_cfg, road_config=self.r_cfg)
        forecast = np.full(180, 50.0)
        delay = mpc_clear.optimize_release_rate(current_queue=0.0, forecast_visibility=forecast)
        self.assertAlmostEqual(delay, 240.0) # normal baseline release
        
        # 2. Queue-hold case with crusher bottleneck (crusher_mu = 10.0 < shovel_mu = 15.0)
        mpc_bottleneck = DeterministicMPC(horizon_s=1800.0, step_s=10.0, crusher_service_rate_vph=10.0, 
                                          shovel_service_rate_vph=15.0, vehicle_config=self.v_cfg, road_config=self.r_cfg)
        delay_hold = mpc_bottleneck.optimize_release_rate(current_queue=2.0, forecast_visibility=forecast)
        self.assertTrue(delay_hold > 240.0)  # should throttle or hold release!

    def test_03_robust_mpc(self):
        mpc = RobustMPC(horizon_s=1800.0, step_s=10.0, crusher_service_rate_vph=10.0, 
                        shovel_service_rate_vph=15.0, vehicle_config=self.v_cfg, road_config=self.r_cfg)
        
        # Two scenarios: Scenario 0 is clear, Scenario 1 is dense fog (15m)
        scenarios = np.zeros((2, 180))
        scenarios[0, :] = 50.0 # Clear
        scenarios[1, :] = 15.0 # Fog
        
        # Under robust control, it should plan for the worst case (fog)
        delay_robust = mpc.optimize_release_rate(current_queue=0.0, scenarios_visibility=scenarios)
        
        # Compare with clear-only MPC
        det_mpc = DeterministicMPC(horizon_s=1800.0, step_s=10.0, crusher_service_rate_vph=10.0, 
                                   shovel_service_rate_vph=15.0, vehicle_config=self.v_cfg, road_config=self.r_cfg)
        delay_clear = det_mpc.optimize_release_rate(current_queue=0.0, forecast_visibility=np.full(180, 50.0))
        
        self.assertTrue(delay_robust >= delay_clear)

    def test_04_chance_constrained_mpc(self):
        mpc = ChanceConstrainedMPC(horizon_s=1800.0, step_s=10.0, crusher_service_rate_vph=10.0, 
                                   shovel_service_rate_vph=15.0, vehicle_config=self.v_cfg, road_config=self.r_cfg,
                                   confidence_level=0.95)
        
        forecast = np.full(180, 30.0)
        # Low uncertainty (std = 1.0) vs High uncertainty (std = 8.0)
        delay_low_unc = mpc.optimize_release_rate(current_queue=0.5, forecast_visibility=forecast, forecast_uncertainty_std=1.0)
        delay_high_unc = mpc.optimize_release_rate(current_queue=0.5, forecast_visibility=forecast, forecast_uncertainty_std=8.0)
        
        # High uncertainty should yield more conservative (longer) delays
        self.assertTrue(delay_high_unc >= delay_low_unc)
