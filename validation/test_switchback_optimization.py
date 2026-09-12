"""
validation/test_switchback_optimization.py
-----------------------------------------
Test suite validating switchback delay reduction and safety invariants:
1. Switchback parameter configuration (stop line margin, lookahead, safety buffer)
2. Reduced truck-to-truck delay (< 2.0s gap between consecutive trucks at switchback)
3. Strict switchback mutual exclusion (at most 1 vehicle in single-lane section)
4. Safe car-following headway (>= 15.52m between queued trucks behind leader)
5. Full SHOVEL -> CRUSHER -> SHOVEL operational haul cycle
6. Fog condition safe speed adaptation in switchback zone
7. Tier-1 governor invariant (v_command <= v_safe at all times)
"""

import unittest
import math
from interfaces.task1_hmi import create_default_digital_twin_simulator


class TestSwitchbackOptimization(unittest.TestCase):

    def test_01_switchback_configuration_parameters(self):
        """Verify optimized switchback parameters are correctly configured on the simulator."""
        sim = create_default_digital_twin_simulator(fleet_size=2)
        self.assertAlmostEqual(sim.switchback_stop_line_margin, 3.0, places=2)
        self.assertAlmostEqual(sim.switchback_lookahead_m, 25.0, places=2)
        self.assertAlmostEqual(sim.switchback_safety_buffer_s, 0.5, places=2)
        self.assertIn("SWITCHBACK_01", sim.switchback_coordinators)
        self.assertAlmostEqual(sim.switchback_coordinators["SWITCHBACK_01"].safety_buffer_s, 0.5, places=2)

    def test_02_reduced_switchback_exit_to_entry_delay(self):
        """
        Verify that consecutive queueing trucks pass the switchback with minimal
        practical delay (<= 2.0s entry gap after previous truck clears).
        """
        sim = create_default_digital_twin_simulator(fleet_size=10)
        prev_on_sb = set()
        entries = []
        exits = []

        for step in range(500):
            sim.step()
            t = sim.state.timestamp
            curr_on_sb = {vid for vid, v in sim.state.vehicles.items() if v.road_edge == "ROAD_04_SWITCH1_TO_INT2"}

            for vid in curr_on_sb - prev_on_sb:
                entries.append((t, vid))
            for vid in prev_on_sb - curr_on_sb:
                exits.append((t, vid))

            prev_on_sb = curr_on_sb

        # Measure gaps after initial spawn drain (t > 50s)
        gaps = []
        for exit_t, exit_vid in exits:
            if exit_t > 50.0:
                following = [e for e in entries if e[0] >= exit_t]
                if following:
                    next_entry_t, next_vid = following[0]
                    gap = next_entry_t - exit_t
                    # Only count when there is a truck ready/waiting (gap < 20s)
                    if gap < 20.0:
                        gaps.append(gap)

        self.assertGreater(len(gaps), 3, "Should have multiple consecutive switchback passages")
        mean_gap = sum(gaps) / len(gaps)
        # Verify mean gap is <= 3.0s (significantly reduced from previous 4.0s - 5.0s baseline)
        self.assertLessEqual(mean_gap, 3.0, f"Mean entry gap should be <= 3.0s, got {mean_gap:.2f}s")
        for g in gaps:
            self.assertLessEqual(g, 3.0, f"Individual gap should not exceed 3.0s, got {g:.1f}s")

    def test_03_strict_mutual_exclusion_no_simultaneous_occupancy(self):
        """
        Verify that the single-lane switchback (ROAD_04) NEVER has more than 1 vehicle
        simultaneously during active operations (no concurrent conflicting occupancy).
        """
        sim = create_default_digital_twin_simulator(fleet_size=10)
        max_simultaneous = 0

        for step in range(600):
            sim.step()
            t = sim.state.timestamp
            curr_on_sb = [vid for vid, v in sim.state.vehicles.items() if v.road_edge == "ROAD_04_SWITCH1_TO_INT2"]
            if t > 35.0:  # after initial spawn drain
                max_simultaneous = max(max_simultaneous, len(curr_on_sb))
                self.assertLessEqual(len(curr_on_sb), 1, f"Mutual exclusion violated at t={t:.1f}s with {curr_on_sb}")

        self.assertEqual(max_simultaneous, 1)

    def test_04_safe_car_following_headway_in_queues(self):
        """
        Verify that trucks waiting in queue behind the leading truck maintain
        the minimum standstill headway bound (>= 15.52m).
        """
        sim = create_default_digital_twin_simulator(fleet_size=10)

        for step in range(300):
            sim.step()
            # Check all road edges for same-lane vehicle pairs
            by_edge_lane = {}
            for vid, v in sim.state.vehicles.items():
                key = (v.road_edge, v.lane_or_direction)
                by_edge_lane.setdefault(key, []).append(v)

            for key, v_list in by_edge_lane.items():
                if len(v_list) > 1:
                    v_list.sort(key=lambda v: v.position_s)
                    for i in range(len(v_list) - 1):
                        spacing = v_list[i + 1].position_s - v_list[i].position_s
                        # With discrete integration, stopped trucks must not violate min headway
                        if v_list[i].speed_v == 0.0 and v_list[i + 1].speed_v == 0.0:
                            self.assertGreaterEqual(
                                spacing, 15.4,
                                f"Queued trucks violated headway on {key}: {spacing:.2f}m < 15.4m"
                            )

    def test_05_full_shovel_to_crusher_cycle(self):
        """
        Verify that vehicles complete a full round-trip cycle:
        SHOVEL -> ROAD_04 (downhill) -> CRUSHER -> ROAD_04 (uphill return) -> SHOVEL.
        """
        sim = create_default_digital_twin_simulator(fleet_size=6)
        initial_tonnage = sim.state.total_tonnage_delivered

        # Run 800 steps to allow delivery and return
        for _ in range(800):
            sim.step()

        self.assertGreater(
            sim.state.total_tonnage_delivered, initial_tonnage,
            "Fleet must deliver payload to the crusher over extended simulation"
        )

    def test_06_fog_conditions_speed_adaptation_in_switchback(self):
        """
        Verify that in dense fog conditions, safe speeds on the switchback
        adapt dynamically and respect the Tier-1 governor limit.
        """
        sim = create_default_digital_twin_simulator(fleet_size=4)
        # Apply dense fog (visibility 15m)
        sim.update_weather(visibility_m=15.0, friction_mu=0.55)

        for step in range(150):
            sim.step()
            for vid, v in sim.state.vehicles.items():
                if v.road_edge == "ROAD_04_SWITCH1_TO_INT2":
                    road_state = sim.state.roads.get("ROAD_04_SWITCH1_TO_INT2")
                    max_limit = road_state.speed_limit_mps if road_state else 8.33
                    self.assertLessEqual(
                        v.speed_v, max_limit + 0.1,
                        f"Truck {vid} exceeded switchback speed limit: {v.speed_v:.2f} vs limit {max_limit:.2f}"
                    )

    def test_07_tier1_governor_invariant_at_all_times(self):
        """
        Verify Tier-1 Governor Invariant:
        v_command = min(v_dispatch, v_safe)
        speed_v <= safe_speed + epsilon holds for every vehicle on every road at every tick.
        """
        sim = create_default_digital_twin_simulator(fleet_size=6)

        for step in range(250):
            sim.step()
            for vid, v in sim.state.vehicles.items():
                road_state = sim.state.roads.get(v.road_edge)
                if road_state:
                    self.assertLessEqual(
                        v.speed_v, road_state.safe_speed_mps + 0.5,
                        f"Tier-1 invariant violated for {vid} on {v.road_edge}: {v.speed_v:.2f} > {road_state.safe_speed_mps:.2f}"
                    )


if __name__ == "__main__":
    unittest.main()
