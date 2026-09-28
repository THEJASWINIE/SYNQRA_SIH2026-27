"""
FOG-ORCHESTRATOR 2.0 — Canonical Kinematics & Calibration Verification Test Suite
SIH 2026-27 | Phase H11 Parameter Reconciliation

Verifies:
  - Wheel diameter D = 0.060 m (R = 0.030 m)
  - Effective PPR = 34.58 pulses/rev
  - Circumference C = pi * D = 0.188495559 m
  - Distance per revolution = C = 0.188496 m
  - Distance per pulse = C / 34.58 = 0.00545100 m/pulse
  - Exact pulse progression: 0, 1, 34.58, 100, 1000 pulses
  - RPM to linear velocity conversion: v = (RPM * C) / 60
  - Numerical stability of fractional effective PPR over 1,000,000 pulses
  - Parity between Vehicle A and Vehicle B configurations
"""

import math
import json
import pytest
from integration_adapters.unit_converter import UnitConverter

CANONICAL_D_M = 0.060
CANONICAL_R_M = 0.030
CANONICAL_PPR_EFF = 34.58
CANONICAL_CIRCUMFERENCE_M = math.pi * CANONICAL_D_M
DISTANCE_PER_PULSE_M = CANONICAL_CIRCUMFERENCE_M / CANONICAL_PPR_EFF


class TestCanonicalKinematicsMathematics:
    """Rigorous verification of canonical wheel kinematics and calibration math."""

    def test_circumference_and_distance_per_revolution(self):
        """Verify C = pi * D and distance per rev."""
        c = math.pi * CANONICAL_D_M
        assert math.isclose(c, 0.188495559, rel_tol=1e-6)
        # Distance per mechanical revolution is identical to wheel circumference
        dist_per_rev = c
        assert math.isclose(dist_per_rev, CANONICAL_CIRCUMFERENCE_M, rel_tol=1e-9)

    def test_distance_per_pulse_calculation(self):
        """Verify distance per pulse = C / PPR_eff."""
        d_pulse = CANONICAL_CIRCUMFERENCE_M / CANONICAL_PPR_EFF
        assert math.isclose(d_pulse, 0.00545100, abs_tol=1e-5)
        assert math.isclose(d_pulse * 1000.0, 5.45100, abs_tol=1e-3)  # mm/pulse

    @pytest.mark.parametrize(
        "pulses, expected_revs, expected_distance_m",
        [
            (0, 0.0, 0.0),
            (1, 1.0 / 34.58, 1.0 * DISTANCE_PER_PULSE_M),
            (34.58, 1.0, CANONICAL_CIRCUMFERENCE_M),
            (100, 100.0 / 34.58, 100.0 * DISTANCE_PER_PULSE_M),
            (1000, 1000.0 / 34.58, 1000.0 * DISTANCE_PER_PULSE_M),
        ],
    )
    def test_exact_pulse_count_progression(self, pulses, expected_revs, expected_distance_m):
        """Verify 0, 1, 34.58, 100, and 1000 pulse conversions."""
        calc_revs = pulses / CANONICAL_PPR_EFF
        calc_distance = calc_revs * CANONICAL_CIRCUMFERENCE_M

        assert math.isclose(calc_revs, expected_revs, rel_tol=1e-6)
        assert math.isclose(calc_distance, expected_distance_m, rel_tol=1e-6)

        # 34.58 effective pulses MUST equal exactly 1 revolution (0.188496 m)
        if pulses == 34.58:
            assert math.isclose(calc_revs, 1.0, rel_tol=1e-9)
            assert math.isclose(calc_distance, 0.188496, abs_tol=1e-4)

    @pytest.mark.parametrize(
        "rpm, expected_speed_mps",
        [
            (0.0, 0.0),
            (180.0, (180.0 * CANONICAL_CIRCUMFERENCE_M) / 60.0),
            (240.0, (240.0 * CANONICAL_CIRCUMFERENCE_M) / 60.0),
            (445.6338, 1.4000),  # Max prototype speed ceiling
        ],
    )
    def test_rpm_to_linear_speed_conversion(self, rpm, expected_speed_mps):
        """Verify v = (RPM * C) / 60 across nominal, crawl, and max speeds."""
        v = (rpm * CANONICAL_CIRCUMFERENCE_M) / 60.0
        assert math.isclose(v, expected_speed_mps, rel_tol=1e-4)

    def test_numerical_stability_fractional_ppr(self):
        """Verify numerical stability over a long haul run of 1,000,000 pulses."""
        n_pulses = 1_000_000
        revs = n_pulses / CANONICAL_PPR_EFF
        distance = revs * CANONICAL_CIRCUMFERENCE_M
        # Distance should be ~5,451.00 meters without floating point drift
        assert math.isclose(distance, 5451.00, abs_tol=0.1)

    def test_unit_converter_backend_integration(self):
        """Verify UnitConverter produces identical results for Vehicle A and Vehicle B."""
        converter = UnitConverter("config/physical_vehicle_parameters.json")
        speed_a = converter.rpm_to_speed_mps("TRUCK_01", 240.0)
        speed_b = converter.rpm_to_speed_mps("TRUCK_02", 240.0)

        assert speed_a is not None
        assert speed_b is not None
        assert speed_a == speed_b
        assert math.isclose(speed_a, 0.7540, abs_tol=1e-3)

    def test_config_parity_across_vehicles(self):
        """Verify config/physical_vehicle_parameters.json has zero parameter drift."""
        with open("config/physical_vehicle_parameters.json", "r") as f:
            data = json.load(f)

        assert data["TRUCK_01"]["wheel_diameter_m"] == 0.060
        assert data["TRUCK_02"]["wheel_diameter_m"] == 0.060
        assert data["TRUCK_01"]["wheel_radius_m"] == 0.030
        assert data["TRUCK_02"]["wheel_radius_m"] == 0.030
        assert data["TRUCK_01"]["pulses_per_revolution"] == 34.58
        assert data["TRUCK_02"]["pulses_per_revolution"] == 34.58
        assert data["TRUCK_01"]["encoder_effective_ppr"] == 34.58
        assert data["TRUCK_02"]["encoder_effective_ppr"] == 34.58
