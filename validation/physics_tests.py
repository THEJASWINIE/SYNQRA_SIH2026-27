"""
validation/physics_tests.py
---------------------------
Verification test suite for:
- Stage 2: Single-Vehicle Longitudinal Physics Model
- Stage 3: Vehicle Safety Engine (Braking, Retarder, Friction, Safe Speed)
- Stage 4: Road Carrying Capacity & Headway Lower Bound
- Stage 5: Queue Dynamics, Service Limits, Finite Buffers & Blocking
- Stage 6: Bottleneck Scoring, Dynamic Ranking & Migration Detection
- Stage 7: Arrival-Rate Shaping & Departure Metering (lambda <= mu - delta_buffer)
- Stage 8: Switchback / Intersection Slot Reservation & Conflict Arbitration

Equations & Invariants Verified:
1. m * dv/dt = F_drive + m*g*sin(theta) - F_roll - F_aero - F_retarder - F_brake
2. F_roll = C_rr * m * g * cos(theta)
3. F_aero = 0.5 * rho * C_D * A * v^2
4. F_mu = mu * m * g * cos(theta)
5. F_available = min(F_hardware_max, F_mu)
6. d_reaction = v * tau_total
7. d_brake = v^2 / (2 * a_dec)
8. S_stop = d_reaction + d_brake
9. S_stop + S_margin <= R_effective
10. v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
11. v_command = min(v_dispatch, v_safe)
12. mu_safe = max(mu_floor, mu_hat - k_sigma * sigma_mu)
13. C_r = 3600 * v_safe / H_safe
14. H_safe >= L_vehicle + S_standstill = 15.52 m (BH100 reference configuration)
15. Q(t+dt) = max(0, Q(t) + A(t) - D(t))
16. D(t) <= service_rate * dt
17. rho = lambda / mu
18. B = (w1 * rho) * (1 + w2 * Q) * (w3 * Criticality)
19. lambda_arrival <= mu_node - delta_buffer
20. Slot_A \cap Slot_B = \emptyset (Mutual exclusion of conflicting occupancy slots)
"""

import unittest
import os
import math
import yaml
from models.vehicle_physics import VehiclePhysics, GRAVITY_G
from models.vehicle import Vehicle, VehicleState
from models.friction import FrictionModel
from models.retarder import RetarderModel
from models.braking import BrakingModel
from models.road_capacity import RoadCapacityModel
from models.queue_model import QueueModel, ArrivalRateShaper
from models.bottleneck import BottleneckDetector, BottleneckEntry, BottleneckMigrationEvent
from models.switchback import SwitchbackCoordinator, TimeSlot


class TestVehiclePhysicsAndSafety(unittest.TestCase):
    """Combined Stage 2 through Stage 8 Verification Suite."""

    def setUp(self):
        """Load vehicle configuration from vehicle.yaml."""
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.vehicle_cfg_path = os.path.join(self.base_dir, "config", "vehicle.yaml")
        
        with open(self.vehicle_cfg_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
            
        self.physics = VehiclePhysics(self.cfg)
        self.friction_model = FrictionModel(self.cfg)
        self.retarder_model = RetarderModel(self.cfg)
        self.braking_model = BrakingModel(self.cfg)
        self.capacity_model = RoadCapacityModel(self.cfg)
        self.bottleneck_detector = BottleneckDetector({"bottleneck": {"w1": 1.0, "w2": 0.5, "w3": 1.0}})
        self.arrival_shaper = ArrivalRateShaper(default_delta_buffer_vph=2.0)
        self.switchback_coord = SwitchbackCoordinator(resource_id="SWITCHBACK_01", config={"safety_buffer_s": 2.0})

        self.tare_mass = 74000.0        # 74 t [REFERENCE]
        self.gross_mass = 165500.0      # 165.5 t [REFERENCE]

    # --------------------------------------------------------------------------
    # STAGE 2 TESTS: LONGITUDINAL FORCES AND MOTION
    # --------------------------------------------------------------------------

    def test_01_zero_speed_standstill(self):
        """Test zero-speed behavior: parked vehicle on flat road remains stationary."""
        forces = self.physics.calculate_longitudinal_forces(
            speed_mps=0.0, grade_rad=0.0, mass_kg=self.tare_mass,
            f_drive=0.0, f_brake=50000.0, f_retarder=0.0, mu=0.65, c_rr=0.025
        )
        self.assertAlmostEqual(forces["f_net"], 0.0, places=5)
        self.assertAlmostEqual(forces["f_aero"], 0.0, places=5)

        new_pos, new_spd, accel = self.physics.step(
            dt=1.0, current_position_m=0.0, current_speed_mps=0.0,
            grade_rad=0.0, mass_kg=self.tare_mass, f_drive=0.0,
            f_brake=50000.0, f_retarder=0.0, mu=0.65
        )
        self.assertEqual(new_pos, 0.0)
        self.assertEqual(new_spd, 0.0)
        self.assertEqual(accel, 0.0)

    def test_02_flat_road_behavior(self):
        """Test flat-road behavior: gravity longitudinal component is zero."""
        forces = self.physics.calculate_longitudinal_forces(
            speed_mps=10.0, grade_rad=0.0, mass_kg=self.gross_mass,
            f_drive=100000.0, f_brake=0.0, f_retarder=0.0, mu=0.65, c_rr=0.025
        )
        self.assertAlmostEqual(forces["f_grade"], 0.0, places=5)
        f_roll = 0.025 * self.gross_mass * GRAVITY_G * 1.0
        f_aero = 0.5 * 1.225 * 0.9 * 22.0 * (10.0 ** 2)
        expected_f_net = 100000.0 - f_roll - f_aero

        self.assertAlmostEqual(forces["f_roll"], f_roll, places=2)
        self.assertAlmostEqual(forces["f_aero"], f_aero, places=2)
        self.assertAlmostEqual(forces["f_net"], expected_f_net, places=2)

    def test_03_positive_and_negative_grade(self):
        """Test positive (downhill) and negative (uphill) grade forces."""
        grade_rad = math.atan(0.08)  # 8% slope
        forces_down = self.physics.calculate_longitudinal_forces(
            speed_mps=5.0, grade_rad=grade_rad, mass_kg=self.gross_mass,
            f_drive=0.0, f_brake=0.0, f_retarder=0.0, mu=0.65
        )
        self.assertGreater(forces_down["f_grade"], 0.0)
        expected_down_f_grade = self.gross_mass * GRAVITY_G * math.sin(grade_rad)
        self.assertAlmostEqual(forces_down["f_grade"], expected_down_f_grade, places=2)

        forces_up = self.physics.calculate_longitudinal_forces(
            speed_mps=5.0, grade_rad=-grade_rad, mass_kg=self.gross_mass,
            f_drive=0.0, f_brake=0.0, f_retarder=0.0, mu=0.65
        )
        self.assertLess(forces_up["f_grade"], 0.0)
        self.assertAlmostEqual(forces_up["f_grade"], -expected_down_f_grade, places=2)

    def test_04_rolling_resistance(self):
        """Test rolling resistance F_roll = C_rr * m * g * cos(theta)."""
        c_rr = 0.035
        grade_rad = math.atan(0.0625)
        f_roll = self.physics.calculate_rolling_resistance(
            mass_kg=self.gross_mass, grade_rad=grade_rad, c_rr=c_rr
        )
        expected = c_rr * self.gross_mass * GRAVITY_G * math.cos(grade_rad)
        self.assertAlmostEqual(f_roll, expected, places=2)

    def test_05_aerodynamic_drag(self):
        """Test aerodynamic drag quadratic scaling."""
        v1, v2 = 5.0, 10.0
        f_aero_1 = self.physics.calculate_aerodynamic_drag(v1)
        f_aero_2 = self.physics.calculate_aerodynamic_drag(v2)
        self.assertAlmostEqual(f_aero_2, 4.0 * f_aero_1, places=3)

    def test_06_friction_limit_traction_clamping(self):
        """Test traction limit F_mu = mu * m * g * cos(theta) clamping excessive drive force."""
        mu_slick = 0.20
        f_mu_limit = self.physics.calculate_traction_limit(
            mass_kg=self.tare_mass, grade_rad=0.0, mu=mu_slick
        )
        forces = self.physics.calculate_longitudinal_forces(
            speed_mps=5.0, grade_rad=0.0, mass_kg=self.tare_mass,
            f_drive=300000.0, f_brake=0.0, f_retarder=0.0, mu=mu_slick
        )
        self.assertAlmostEqual(forces["f_drive"], f_mu_limit, places=2)

    def test_07_available_braking_force_limit(self):
        """Test F_available = min(F_hardware_max, F_mu)."""
        mu_low = 0.18
        f_avail_low = self.physics.calculate_available_braking_force(
            mass_kg=self.gross_mass, grade_rad=0.0, mu=mu_low
        )
        expected_adhesion = mu_low * self.gross_mass * GRAVITY_G
        self.assertAlmostEqual(f_avail_low, expected_adhesion, places=2)

        mu_high = 0.85
        f_avail_high = self.physics.calculate_available_braking_force(
            mass_kg=self.gross_mass, grade_rad=0.0, mu=mu_high
        )
        self.assertEqual(f_avail_high, self.physics.f_hardware_max_n)

    def test_08_deterministic_timestep_behavior(self):
        """Test deterministic step repeatability."""
        run_1, run_2 = [], []
        pos, spd = 0.0, 0.0
        for _ in range(30):
            pos, spd, _ = self.physics.step(
                dt=0.5, current_position_m=pos, current_speed_mps=spd,
                grade_rad=0.04, mass_kg=self.gross_mass, f_drive=120000.0,
                f_brake=0.0, f_retarder=0.0, mu=0.55
            )
            run_1.append(pos)

        pos, spd = 0.0, 0.0
        for _ in range(30):
            pos, spd, _ = self.physics.step(
                dt=0.5, current_position_m=pos, current_speed_mps=spd,
                grade_rad=0.04, mass_kg=self.gross_mass, f_drive=120000.0,
                f_brake=0.0, f_retarder=0.0, mu=0.55
            )
            run_2.append(pos)

        self.assertEqual(run_1, run_2)

    # --------------------------------------------------------------------------
    # STAGE 3 TESTS: SAFETY ENGINE, STOPPING ENVELOPES & MONOTONICITY
    # --------------------------------------------------------------------------

    def test_09_reaction_and_braking_distance_equations(self):
        """Verify stopping distance equations."""
        d_reac, d_brk, s_stop = self.braking_model.calculate_stopping_distance(10.0, 2.5, 0.40)
        self.assertAlmostEqual(d_reac, 4.0, places=4)
        self.assertAlmostEqual(d_brk, 20.0, places=4)
        self.assertAlmostEqual(s_stop, 24.0, places=4)

    def test_10_stopping_invariant_inversion(self):
        """Verify that solving for v_stop guarantees S_stop(v_stop) + S_margin <= R_effective."""
        r_effective, s_margin, tau, a_dec = 30.0, 5.0, 0.40, 2.0
        v_stop = self.braking_model.solve_safe_speed_stopping(r_effective, a_dec, tau, s_margin)
        _, _, s_stop = self.braking_model.calculate_stopping_distance(v_stop, a_dec, tau)
        self.assertAlmostEqual(s_stop + s_margin, r_effective, places=3)

    def test_11_friction_reduction_effect(self):
        """Test that reduced tire-road friction lowers deceleration and reduces safe speed."""
        a_dec_dry = self.braking_model.calculate_deceleration_on_grade(self.gross_mass, 0.0, 0.65)
        a_dec_wet = self.braking_model.calculate_deceleration_on_grade(self.gross_mass, 0.0, 0.25)
        self.assertGreater(a_dec_dry, a_dec_wet)

        v_safe_dry = self.braking_model.solve_safe_speed_stopping(30.0, a_dec_dry, 0.40)
        v_safe_wet = self.braking_model.solve_safe_speed_stopping(30.0, a_dec_wet, 0.40)
        self.assertGreater(v_safe_dry, v_safe_wet)

    def test_12_visibility_reduction_monotonicity(self):
        """Monotonicity check: as visibility drops, safe speed must strictly decrease."""
        visibilities = [50.0, 30.0, 20.0, 15.0, 10.0, 5.0]
        safe_speeds = [
            self.braking_model.calculate_safe_speed(
                r_effective=v, grade_rad=math.atan(0.04), mass_kg=self.gross_mass,
                mu_safe=0.45, curve_radius_m=500.0, speed_limit_mine_mps=11.11
            )["v_safe"]
            for v in visibilities
        ]
        for i in range(len(safe_speeds) - 1):
            self.assertGreaterEqual(safe_speeds[i], safe_speeds[i + 1])

    def test_13_increased_latency_effect(self):
        """Test that increased system reaction latency reduces v_safe."""
        v_fast = self.braking_model.solve_safe_speed_stopping(25.0, 2.2, 0.20)
        v_slow = self.braking_model.solve_safe_speed_stopping(25.0, 2.2, 1.50)
        self.assertGreater(v_fast, v_slow)

    def test_14_downhill_grade_retarder_constraint(self):
        """Test that steep downhill slopes activate retarder power constraint."""
        c_rr = 0.025
        grades_pct = [4.0, 6.25, 8.0, 10.0]
        v_ret_list = [
            self.retarder_model.calculate_max_sustainable_downhill_speed(
                mass_kg=self.gross_mass, grade_rad=math.atan(g / 100.0), c_rr=c_rr
            )
            for g in grades_pct
        ]
        for i in range(len(v_ret_list) - 1):
            self.assertGreaterEqual(v_ret_list[i], v_ret_list[i + 1])

    def test_15_command_speed_constraint(self):
        """Verify mandatory architectural invariant: v_command = min(v_dispatch, v_safe)."""
        self.assertEqual(self.braking_model.compute_command_speed(10.0, 11.11), 10.0)
        self.assertEqual(self.braking_model.compute_command_speed(10.0, 4.2), 4.2)
        self.assertEqual(self.braking_model.compute_command_speed(30.0, 6.5), 6.5)

    def test_16_conservative_friction_confidence_bound(self):
        """Test mu_safe = max(mu_floor, mu_hat - k_sigma * sigma_mu)."""
        mu_safe_normal = self.friction_model.calculate_safe_friction(0.50, 0.08, 0.18, 1.645)
        self.assertAlmostEqual(mu_safe_normal, 0.50 - (1.645 * 0.08), places=4)

        mu_safe_clamped = self.friction_model.calculate_safe_friction(0.22, 0.10, 0.18, 1.645)
        self.assertEqual(mu_safe_clamped, 0.18)

    # --------------------------------------------------------------------------
    # STAGE 4 TESTS: ROAD CAPACITY & PHYSICAL HEADWAY LOWER BOUND
    # --------------------------------------------------------------------------

    def test_17_road_capacity_calculation_formula(self):
        """Verify C_r_h = 3600 * v_safe / H_safe."""
        cap_res = self.capacity_model.calculate_road_capacity(v_safe_mps=10.0, h_safe_m=40.0)
        self.assertAlmostEqual(cap_res["capacity_vps"], 0.25, places=4)
        self.assertAlmostEqual(cap_res["capacity_vph"], 900.0, places=4)

    def test_18_physical_headway_lower_bound(self):
        """Verify H_safe >= 15.52 m even at v_safe = 0 m/s."""
        h_standstill = self.capacity_model.calculate_safe_headway(0.0, 2.5, 0.40)
        self.assertEqual(h_standstill, 15.52)

        cap_res = self.capacity_model.calculate_road_capacity(5.0, 5.0)
        self.assertEqual(cap_res["h_safe_m"], 15.52)

    def test_19_capacity_response_to_lower_safe_speed(self):
        """Verify that reduced safe speed reduces road capacity."""
        cap_high = self.capacity_model.calculate_capacity_from_conditions(10.0, 2.0)
        cap_low = self.capacity_model.calculate_capacity_from_conditions(3.0, 2.0)
        self.assertGreater(cap_high["capacity_vph"], cap_low["capacity_vph"])

    def test_20_capacity_response_to_increased_headway(self):
        """Verify that expanded safe headway reduces road capacity."""
        cap_dry = self.capacity_model.calculate_road_capacity(8.0, 25.0)
        cap_wet = self.capacity_model.calculate_road_capacity(8.0, 50.0)
        self.assertGreater(cap_dry["capacity_vph"], cap_wet["capacity_vph"])

    def test_21_capacity_deterministic_results(self):
        """Verify deterministic road capacity output."""
        r1 = self.capacity_model.calculate_capacity_from_conditions(7.2, 1.85, 0.45)
        r2 = self.capacity_model.calculate_capacity_from_conditions(7.2, 1.85, 0.45)
        self.assertEqual(r1["capacity_vph"], r2["capacity_vph"])

    def test_22_physical_capacity_bounds(self):
        """Verify non-negative capacity and zero speed handling."""
        cap_zero = self.capacity_model.calculate_road_capacity(0.0, 20.0)
        self.assertEqual(cap_zero["capacity_vph"], 0.0)
        with self.assertRaises(ValueError):
            self.capacity_model.calculate_road_capacity(-5.0, 20.0)

    # --------------------------------------------------------------------------
    # STAGE 5 TESTS: QUEUE DYNAMICS, SERVICE CONSTRAINTS & BLOCKING
    # --------------------------------------------------------------------------

    def test_23_empty_queue_initial_state(self):
        """Test empty queue: Q=0 with 0 arrivals yields 0 departures and remains 0."""
        queue = QueueModel(node_id="CRUSHER_01", service_rate_vph=18.0, queue_max=6, initial_queue=0.0)
        departures, new_q, blocked = queue.step(dt_seconds=60.0, arrivals=0.0)
        self.assertEqual(departures, 0.0)
        self.assertEqual(new_q, 0.0)
        self.assertEqual(blocked, 0.0)

    def test_24_queue_arrivals_and_accumulation(self):
        """Test that vehicle arrivals accumulate correctly in the queue."""
        queue = QueueModel(node_id="SHOVEL_01", service_rate_vph=15.0, queue_max=8, initial_queue=0.0)
        departures, new_q, blocked = queue.step(dt_seconds=1.0, arrivals=3.0)
        self.assertAlmostEqual(departures, (15.0 / 3600.0) * 1.0, places=4)
        self.assertAlmostEqual(new_q, 3.0 - departures, places=4)
        self.assertEqual(blocked, 0.0)

    def test_25_queue_departures_and_service_rate_limit(self):
        """Verify D <= service_rate * dt."""
        queue = QueueModel(node_id="CRUSHER_01", service_rate_vph=18.0, queue_max=10, initial_queue=5.0)
        departures, new_q, blocked = queue.step(dt_seconds=100.0, arrivals=0.0)
        self.assertAlmostEqual(departures, 0.5, places=5)
        self.assertAlmostEqual(new_q, 4.5, places=5)

    def test_26_queue_mass_conservation(self):
        """Verify discrete mass conservation."""
        queue = QueueModel(node_id="BUFFER_01", service_rate_vph=30.0, queue_max=15, initial_queue=4.0)
        q_init, arrivals, dt = queue.current_queue, 3.5, 120.0
        departures, q_new, blocked = queue.step(dt_seconds=dt, arrivals=arrivals)
        self.assertAlmostEqual(q_new, q_init + (arrivals - blocked) - departures, places=5)

    def test_27_finite_buffer_blocking_and_overflow(self):
        """Verify finite buffer clamping: Q <= Q_max and is_blocked flag."""
        queue = QueueModel(node_id="CRUSHER_01", service_rate_vph=18.0, queue_max=5, initial_queue=4.0)
        departures, new_q, blocked = queue.step(dt_seconds=0.1, arrivals=4.0)
        self.assertEqual(new_q, 5.0)
        self.assertTrue(queue.is_blocked)
        self.assertGreater(blocked, 2.0)

    def test_28_queue_stability_when_arrival_rate_below_service(self):
        """Verify queue stability when rho = lambda / mu < 1.0."""
        queue = QueueModel(node_id="NODE_STABLE", service_rate_vph=20.0, queue_max=10, initial_queue=6.0)
        lambda_vph, dt = 10.0, 60.0
        for _ in range(45):
            queue.step(dt_seconds=dt, arrivals=(lambda_vph / 3600.0) * dt)
        self.assertAlmostEqual(queue.current_queue, 0.0, places=2)

    def test_29_queue_growth_when_arrival_rate_exceeds_service(self):
        """Verify unstable queue growth when rho = lambda / mu > 1.0."""
        queue = QueueModel(node_id="NODE_UNSTABLE", service_rate_vph=12.0, queue_max=8, initial_queue=0.0)
        lambda_vph, dt = 24.0, 60.0
        for _ in range(50):
            queue.step(dt_seconds=dt, arrivals=(lambda_vph / 3600.0) * dt)
        self.assertEqual(queue.current_queue, 8.0)
        self.assertTrue(queue.is_blocked)

    # --------------------------------------------------------------------------
    # STAGE 6 TESTS: BOTTLENECK SCORING, RANKING & MIGRATION DETECTION
    # --------------------------------------------------------------------------

    def test_30_bottleneck_score_calculation(self):
        """Verify B = (w1 * rho) * (1 + w2 * Q) * (w3 * Criticality)."""
        score = self.bottleneck_detector.calculate_bottleneck_score(
            utilization_rho=1.2, queue_length=4.0, criticality=0.8,
            w1=1.0, w2=0.5, w3=1.0
        )
        self.assertAlmostEqual(score, 2.88, places=4)

    def test_31_bottleneck_ranking_across_elements(self):
        """Test ranking of multiple heterogeneous network elements."""
        elements = [
            {"id": "CRUSHER_01", "type": "NODE", "utilization": 0.8, "queue": 1.0, "criticality": 1.0},
            {"id": "HAUL_ROAD_04", "type": "ROAD_SEGMENT", "utilization": 1.5, "queue": 5.0, "criticality": 0.9},
            {"id": "SHOVEL_01", "type": "NODE", "utilization": 0.5, "queue": 0.0, "criticality": 0.8},
        ]
        ranked = self.bottleneck_detector.rank_elements(elements)
        self.assertEqual(ranked[0].element_id, "HAUL_ROAD_04")
        self.assertEqual(ranked[1].element_id, "CRUSHER_01")
        self.assertEqual(ranked[2].element_id, "SHOVEL_01")

    def test_32_queue_driven_bottleneck_dominance(self):
        """Test that with identical utilization and criticality, higher queue produces higher score."""
        score_low_q = self.bottleneck_detector.calculate_bottleneck_score(utilization_rho=1.0, queue_length=1.0, criticality=0.8)
        score_high_q = self.bottleneck_detector.calculate_bottleneck_score(utilization_rho=1.0, queue_length=6.0, criticality=0.8)
        self.assertGreater(score_high_q, score_low_q)

    def test_33_utilization_driven_bottleneck_dominance(self):
        """Test that with identical queue and criticality, higher utilization produces higher score."""
        score_low_rho = self.bottleneck_detector.calculate_bottleneck_score(utilization_rho=0.6, queue_length=2.0, criticality=0.8)
        score_high_rho = self.bottleneck_detector.calculate_bottleneck_score(utilization_rho=1.4, queue_length=2.0, criticality=0.8)
        self.assertGreater(score_high_rho, score_low_rho)

    def test_34_bottleneck_migration_cycle(self):
        """Test dynamic bottleneck migration cycle."""
        detector = BottleneckDetector({"bottleneck": {"w1": 1.0, "w2": 0.5, "w3": 1.0}})
        state_clear = [
            {"id": "CRUSHER_01", "type": "NODE", "utilization": 0.95, "queue": 3.0, "criticality": 1.0},
            {"id": "RAMP_ROAD_04", "type": "ROAD_SEGMENT", "utilization": 0.40, "queue": 0.0, "criticality": 0.7}
        ]
        detector.rank_elements(state_clear)
        detector.check_migration(detector.rank_elements(state_clear), timestamp=0.0)

        state_fog = [
            {"id": "CRUSHER_01", "type": "NODE", "utilization": 0.60, "queue": 0.0, "criticality": 1.0},
            {"id": "RAMP_ROAD_04", "type": "ROAD_SEGMENT", "utilization": 1.80, "queue": 7.0, "criticality": 0.7}
        ]
        migrated_fog, event_fog = detector.check_migration(detector.rank_elements(state_fog), timestamp=600.0)
        self.assertTrue(migrated_fog)
        self.assertEqual(event_fog.new_primary_id, "RAMP_ROAD_04")

        state_recovered = [
            {"id": "CRUSHER_01", "type": "NODE", "utilization": 1.10, "queue": 4.0, "criticality": 1.0},
            {"id": "RAMP_ROAD_04", "type": "ROAD_SEGMENT", "utilization": 0.35, "queue": 0.0, "criticality": 0.7}
        ]
        migrated_rec, event_rec = detector.check_migration(detector.rank_elements(state_recovered), timestamp=1800.0)
        self.assertTrue(migrated_rec)
        self.assertEqual(event_rec.new_primary_id, "CRUSHER_01")

    def test_35_bottleneck_deterministic_behavior(self):
        """Verify deterministic bottleneck ranking."""
        elements = [
            {"id": "A", "type": "NODE", "utilization": 0.9, "queue": 2.0, "criticality": 0.7},
            {"id": "B", "type": "NODE", "utilization": 0.8, "queue": 3.0, "criticality": 0.8},
        ]
        r1 = self.bottleneck_detector.rank_elements(elements)
        r2 = self.bottleneck_detector.rank_elements(elements)
        self.assertEqual([e.score for e in r1], [e.score for e in r2])

    # --------------------------------------------------------------------------
    # STAGE 7 TESTS: ARRIVAL-RATE SHAPING & RELEASE METERING
    # --------------------------------------------------------------------------

    def test_36_arrival_rate_below_capacity(self):
        """Test arrival rate below safe capacity."""
        lambda_shaped = self.arrival_shaper.shape_arrival_rate(10.0, 18.0, 2.0)
        self.assertEqual(lambda_shaped, 10.0)

    def test_37_arrival_rate_equal_to_capacity(self):
        """Test arrival rate equal to service capacity."""
        lambda_shaped = self.arrival_shaper.shape_arrival_rate(18.0, 18.0, 2.0)
        self.assertEqual(lambda_shaped, 16.0)

    def test_38_arrival_rate_above_capacity(self):
        """Test arrival rate heavily exceeding capacity."""
        lambda_shaped = self.arrival_shaper.shape_arrival_rate(35.0, 18.0, 2.0)
        self.assertEqual(lambda_shaped, 16.0)

    def test_39_buffer_margin_effect(self):
        """Test effect of varying delta_buffer margin."""
        interval_zero = self.arrival_shaper.calculate_release_interval(20.0, 0.0)
        self.assertEqual(interval_zero, 180.0)
        interval_buffered = self.arrival_shaper.calculate_release_interval(20.0, 4.0)
        self.assertEqual(interval_buffered, 225.0)

    def test_40_controlled_release_metering_and_blocking(self):
        """Test release decision evaluation."""
        can_rel_a, delay_a, reason_a = self.arrival_shaper.evaluate_truck_release(
            100.0, 0.0, 18.0, 2.0, 6.0, 2.0
        )
        self.assertFalse(can_rel_a)
        self.assertEqual(reason_a, "METERING_HEADWAY_ACTIVE")

        can_rel_b, delay_b, reason_b = self.arrival_shaper.evaluate_truck_release(
            250.0, 0.0, 18.0, 2.0, 6.0, 2.0
        )
        self.assertTrue(can_rel_b)
        self.assertEqual(reason_b, "RELEASE_PERMITTED")

        can_rel_c, delay_c, reason_c = self.arrival_shaper.evaluate_truck_release(
            300.0, 0.0, 18.0, 6.0, 6.0, 2.0
        )
        self.assertFalse(can_rel_c)
        self.assertEqual(reason_c, "DOWNSTREAM_BUFFER_SATURATED")

    def test_41_arrival_shaper_deterministic_behavior(self):
        """Verify repeatable deterministic results for arrival shaping."""
        r1 = [self.arrival_shaper.calculate_release_interval(18.0, 2.0) for _ in range(20)]
        self.assertTrue(all(val == 225.0 for val in r1))

    # --------------------------------------------------------------------------
    # STAGE 8 TESTS: SWITCHBACK / INTERSECTION SLOT RESERVATION
    # --------------------------------------------------------------------------

    def test_42_slot_creation_and_properties(self):
        """Test TimeSlot dataclass initialization, duration, and overlap checks."""
        slot = TimeSlot(
            slot_id="SLOT_001",
            vehicle_id="TRUCK_01",
            resource_id="SWITCHBACK_01",
            start_time=100.0,
            end_time=130.0,
            direction="downhill",
            is_loaded=True,
            priority_level=2
        )
        self.assertEqual(slot.duration, 30.0)
        self.assertEqual(slot.priority_level, 2)
        
        # Test overlaps: [110, 140] overlaps with [100, 130]
        self.assertTrue(slot.overlaps_with(110.0, 140.0, buffer_s=2.0))
        # Test non-overlap: [150, 180] does not overlap with [100, 130] + 2s buffer
        self.assertFalse(slot.overlaps_with(150.0, 180.0, buffer_s=2.0))

    def test_43_valid_single_reservation(self):
        """Test reserving an available time window on a switchback."""
        coord = SwitchbackCoordinator(resource_id="SWITCH_A", config={"safety_buffer_s": 2.0})
        success, slot, reason = coord.request_reservation(
            vehicle_id="TRUCK_BH100_01",
            start_time=50.0,
            duration_seconds=30.0,
            direction="downhill",
            is_loaded=True
        )
        self.assertTrue(success)
        self.assertIsNotNone(slot)
        self.assertEqual(slot.start_time, 50.0)
        self.assertEqual(slot.end_time, 80.0)
        self.assertEqual(slot.priority_level, 2)
        self.assertEqual(reason, "RESERVATION_CONFIRMED")
        self.assertEqual(len(coord.get_active_slots()), 1)

    def test_44_conflicting_reservation_rejection(self):
        """
        Verify: Slot_A \cap Slot_B = \emptyset.
        An overlapping request is strictly rejected.
        """
        coord = SwitchbackCoordinator(resource_id="SWITCH_A", config={"safety_buffer_s": 2.0})
        
        # Vehicle 1 reserves [50, 80]
        coord.request_reservation("TRUCK_01", start_time=50.0, duration_seconds=30.0, direction="downhill", is_loaded=True)

        # Vehicle 2 attempts to reserve overlapping interval [60, 90] -> REJECTED
        success_conf, slot_conf, reason_conf = coord.request_reservation(
            "TRUCK_02", start_time=60.0, duration_seconds=30.0, direction="uphill", is_loaded=False
        )
        self.assertFalse(success_conf)
        self.assertIsNone(slot_conf)
        self.assertEqual(reason_conf, "CONFLICT_INTERVAL_OVERLAPS_EXISTING_SLOT")

    def test_45_non_conflicting_sequential_reservations(self):
        """Test that non-overlapping sequential reservations with proper buffer are accepted."""
        coord = SwitchbackCoordinator(resource_id="SWITCH_A", config={"safety_buffer_s": 2.0})
        
        # Slot 1: [50, 80] (buffer until 82s)
        success1, slot1, _ = coord.request_reservation("TRUCK_01", start_time=50.0, duration_seconds=30.0)
        # Slot 2: [85, 115] (starts after 80s + 2s buffer)
        success2, slot2, _ = coord.request_reservation("TRUCK_02", start_time=85.0, duration_seconds=30.0)

        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertEqual(len(coord.get_active_slots()), 2)

    def test_46_slot_release_and_expiration(self):
        """Test that past completed slots are pruned when time advances."""
        coord = SwitchbackCoordinator(resource_id="SWITCH_A", config={"safety_buffer_s": 2.0})
        coord.request_reservation("TRUCK_01", start_time=10.0, duration_seconds=20.0) # ends at 30s
        coord.request_reservation("TRUCK_02", start_time=40.0, duration_seconds=20.0) # ends at 60s

        self.assertEqual(len(coord.get_active_slots()), 2)

        # At t = 35s, slot 1 has finished
        completed = coord.release_expired_slots(current_time=35.0)
        self.assertEqual(completed, 1)
        active = coord.get_active_slots()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].vehicle_id, "TRUCK_02")

    def test_47_multiple_vehicles_interleaving(self):
        """
        Test scheduling multiple opposing vehicles (loaded downhill + empty uphill)
        using find_earliest_slot.
        """
        coord = SwitchbackCoordinator(resource_id="SWITCHBACK_RAMP", config={"safety_buffer_s": 3.0})
        
        # 3 loaded downhill trucks and 2 empty uphill trucks arriving around t = 0
        vehicles = [
            ("TRUCK_DOWN_1", "downhill", True),
            ("TRUCK_UP_1", "uphill", False),
            ("TRUCK_DOWN_2", "downhill", True),
            ("TRUCK_UP_2", "uphill", False),
            ("TRUCK_DOWN_3", "downhill", True),
        ]

        allocated_slots = []
        for vid, direction, is_loaded in vehicles:
            slot = coord.find_earliest_slot(
                vehicle_id=vid,
                earliest_start=0.0,
                duration_seconds=25.0,
                direction=direction,
                is_loaded=is_loaded
            )
            allocated_slots.append(slot)

        # Check mutual exclusion across all allocated pairs
        for i in range(len(allocated_slots)):
            for j in range(i + 1, len(allocated_slots)):
                s1 = allocated_slots[i]
                s2 = allocated_slots[j]
                # Either s1 ends before s2 starts, or s2 ends before s1 starts
                non_overlapping = (s1.end_time <= s2.start_time) or (s2.end_time <= s1.start_time)
                self.assertTrue(
                    non_overlapping,
                    f"Collision detected between {s1.slot_id} [{s1.start_time}, {s1.end_time}] and {s2.slot_id} [{s2.start_time}, {s2.end_time}]"
                )

    def test_48_deterministic_slot_scheduling(self):
        """Verify that slot allocation algorithm is 100% deterministic."""
        def run_schedule():
            c = SwitchbackCoordinator(resource_id="SWITCH_DET", config={"safety_buffer_s": 2.0})
            slots = []
            for i in range(5):
                s = c.find_earliest_slot(f"T_{i}", earliest_start=0.0, duration_seconds=20.0)
                slots.append((s.start_time, s.end_time))
            return slots

        sched1 = run_schedule()
        sched2 = run_schedule()
        self.assertEqual(sched1, sched2)


if __name__ == "__main__":
    unittest.main()
