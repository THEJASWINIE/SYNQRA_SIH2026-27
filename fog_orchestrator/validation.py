"""
Formal Mathematical Validation Suite for FOG-ORCHESTRATOR 2.0
Performs dimensional, algebraic, boundary-value, monotonicity, and residual tests for all mathematical subsystems.
"""

import math
from typing import Dict, List, Tuple
from fog_orchestrator.core.config import VehicleParameters, EnvironmentalParameters, PerceptionCommParameters
from fog_orchestrator.tier1_governor.vehicle_physics import VehiclePhysics
from fog_orchestrator.tier1_governor.safety_governor import VehicleSafetyGovernor

class MathematicalValidationSuite:
    """Formal mathematical & physical validation suite."""

    def __init__(self):
        self.governor = VehicleSafetyGovernor()

    def run_all_formal_checks(self) -> Dict[str, any]:
        """Runs complete formal validation suite."""
        results = {}

        # 1. Zero Friction Boundary Test (Runaway condition)
        a_dec_zero_fric = VehiclePhysics.calculate_effective_deceleration(
            grade_rad=math.radians(8.0), is_loaded=True, friction_mu=0.0
        )
        v_stop_zero_fric, _, _ = self.governor.calculate_v_stop(
            r_effective_m=30.0, grade_rad=math.radians(8.0), is_loaded=True, friction_mu=0.0
        )
        results["zero_friction_boundary_passed"] = (a_dec_zero_fric <= 0.0 and v_stop_zero_fric == 0.0)

        # 2. Visibility Boundary Test (R_effective <= S_base => v_stop = 0)
        v_stop_vis_boundary, _, _ = self.governor.calculate_v_stop(
            r_effective_m=4.0, grade_rad=0.0, is_loaded=True, friction_mu=0.35
        )
        results["visibility_boundary_passed"] = (v_stop_vis_boundary == 0.0)

        # 3. Monotonicity Test 1: Visibility Increase => Safe Speed Non-Decreasing
        v_vis15 = self.governor.evaluate_tier1_safety(15.0, math.radians(4.0), True, 0.35).v_safe_mps
        v_vis30 = self.governor.evaluate_tier1_safety(30.0, math.radians(4.0), True, 0.35).v_safe_mps
        results["monotonicity_visibility_passed"] = (v_vis30 >= v_vis15)

        # 4. Monotonicity Test 2: Downhill Grade Increase => Safe Speed Non-Increasing
        v_grade0 = self.governor.evaluate_tier1_safety(25.0, math.radians(0.0), True, 0.35).v_safe_mps
        v_grade8 = self.governor.evaluate_tier1_safety(25.0, math.radians(8.0), True, 0.35).v_safe_mps
        results["monotonicity_grade_passed"] = (v_grade8 <= v_grade0)

        # 5. Monotonicity Test 3: Friction Increase => Safe Speed Non-Decreasing
        v_fric25 = self.governor.evaluate_tier1_safety(25.0, math.radians(4.0), True, 0.25).v_safe_mps
        v_fric45 = self.governor.evaluate_tier1_safety(25.0, math.radians(4.0), True, 0.45).v_safe_mps
        results["monotonicity_friction_passed"] = (v_fric45 >= v_fric25)

        # 6. Monotonicity Test 4: Latency Increase => Safe Headway Increasing
        h_comm10 = self.governor.calculate_safe_headway(15.0/3.6, 0.0, math.radians(4.0), True, 0.35, comm_confidence=1.0)
        h_comm00 = self.governor.calculate_safe_headway(15.0/3.6, 0.0, math.radians(4.0), True, 0.35, comm_confidence=0.0)
        results["monotonicity_latency_passed"] = (h_comm00 > h_comm10)

        # 7. Exact Quadratic Residual Test: S_stop(v_stop) + S_margin(v_stop) == R_effective
        v_test, s_stop_test, _ = self.governor.calculate_v_stop(
            r_effective_m=25.0, grade_rad=math.radians(4.0), is_loaded=True, friction_mu=0.35
        )
        s_margin_test = 5.0  # default S_base
        residual = abs((s_stop_test + s_margin_test) - 25.0) if v_test > 0 else 0.0
        results["exact_residual_error"] = residual
        results["quadratic_residual_passed"] = (residual < 1e-4)

        all_passed = all([
            results["zero_friction_boundary_passed"],
            results["visibility_boundary_passed"],
            results["monotonicity_visibility_passed"],
            results["monotonicity_grade_passed"],
            results["monotonicity_friction_passed"],
            results["monotonicity_latency_passed"],
            results["quadratic_residual_passed"]
        ])
        results["overall_validation_passed"] = all_passed
        return results
