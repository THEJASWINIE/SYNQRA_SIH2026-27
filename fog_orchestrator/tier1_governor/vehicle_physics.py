"""
Tier 1: Vehicle Physics Engine for FOG-ORCHESTRATOR 2.0 (Post-Audit Corrected Version)
Implements conservative longitudinal deceleration without aero credit, downhill dynamic weight transfer,
and exact thermal retarder power limits.
"""

import math
from typing import Dict, Tuple
from fog_orchestrator.core.config import VehicleParameters, EnvironmentalParameters, DEFAULT_VEHICLE, DEFAULT_ENV

class VehiclePhysics:
    """Calculates exact longitudinal forces, accelerations, and retarding capacity."""
    
    @staticmethod
    def calculate_longitudinal_forces(
        speed_mps: float,
        grade_rad: float,
        is_loaded: bool,
        friction_mu: float,
        f_drive_n: float = 0.0,
        f_retarder_n: float = 0.0,
        f_service_brake_n: float = 0.0,
        veh_params: VehicleParameters = DEFAULT_VEHICLE,
        env_params: EnvironmentalParameters = DEFAULT_ENV
    ) -> Dict[str, float]:
        """
        Calculates all longitudinal forces:
        m * dv/dt = F_drive + m*g*sin(theta) - F_roll - F_aero - F_retarder - F_brake
        """
        mass_kg = veh_params.mass_loaded_kg if is_loaded else veh_params.mass_empty_kg
        g = env_params.gravity_mps2

        # 1. Downhill Grade Force (N) - positive for downhill theta > 0
        f_grade = mass_kg * g * math.sin(grade_rad)

        # 2. Rolling Resistance Force (N) - always opposes motion
        f_roll = env_params.c_rr_default * mass_kg * g * math.cos(grade_rad)

        # 3. Aerodynamic Drag Force (N) - opposes motion
        f_aero = 0.5 * env_params.air_density_kgm3 * veh_params.drag_coeff * veh_params.frontal_area_m2 * (speed_mps ** 2)

        # 4. Maximum Tire Friction Limit Force (N) with downhill weight transfer correction
        weight_transfer_factor = max(0.80, 1.0 - (veh_params.cg_height_m / veh_params.wheelbase_m) * math.tan(max(0.0, grade_rad)))
        f_mu_limit = friction_mu * mass_kg * g * math.cos(grade_rad) * weight_transfer_factor

        # 5. Applied Service Brake Force limited by hardware and tire friction
        f_brake_applied = min(f_service_brake_n, f_mu_limit)

        # 6. Total Net Force (N)
        f_net = f_drive_n + f_grade - f_roll - f_aero - f_retarder_n - f_brake_applied

        # 7. Acceleration (m/s^2)
        acceleration_mps2 = f_net / mass_kg

        return {
            "mass_kg": mass_kg,
            "f_grade": f_grade,
            "f_roll": f_roll,
            "f_aero": f_aero,
            "f_mu_limit": f_mu_limit,
            "f_brake_applied": f_brake_applied,
            "f_net": f_net,
            "acceleration_mps2": acceleration_mps2
        }

    @staticmethod
    def calculate_effective_deceleration(
        grade_rad: float,
        is_loaded: bool,
        friction_mu: float,
        speed_mps: float = 0.0,  # Default 0.0 for conservative emergency stopping distance without aero credit
        veh_params: VehicleParameters = DEFAULT_VEHICLE,
        env_params: EnvironmentalParameters = DEFAULT_ENV
    ) -> float:
        """
        Calculates CONSERVATIVE emergency deceleration rate a_dec (m/s^2):
        Sets f_aero = 0 to ensure deceleration credit is guaranteed down to 0 km/h standstill.
        Includes downhill dynamic weight transfer reduction on braking limit.
        a_dec = [ min(F_hardware_max, mu_eff * m * g * cos(theta)) + F_roll - m * g * sin(theta) ] / m
        """
        mass_kg = veh_params.mass_loaded_kg if is_loaded else veh_params.mass_empty_kg
        g = env_params.gravity_mps2

        # Downhill weight transfer reduction factor on rear braking traction
        weight_transfer_factor = max(0.80, 1.0 - (veh_params.cg_height_m / veh_params.wheelbase_m) * math.tan(max(0.0, grade_rad)))
        f_mu_max = friction_mu * mass_kg * g * math.cos(grade_rad) * weight_transfer_factor
        f_brake_avail = min(veh_params.max_service_brake_n, f_mu_max)

        f_roll = env_params.c_rr_default * mass_kg * g * math.cos(grade_rad)
        f_grade = mass_kg * g * math.sin(grade_rad)

        # Conservative deceleration without aero drag credit (since speed drops to 0)
        net_retardation_force = f_brake_avail + f_roll - f_grade
        a_dec = net_retardation_force / mass_kg
        return a_dec

    @staticmethod
    def calculate_retarder_continuous_speed_limit(
        grade_rad: float,
        is_loaded: bool,
        veh_params: VehicleParameters = DEFAULT_VEHICLE,
        env_params: EnvironmentalParameters = DEFAULT_ENV
    ) -> float:
        """
        Calculates maximum continuous downhill speed allowed by dynamic retarder thermal power:
        P_ret_req = (m*g*sin(theta) - C_rr*m*g*cos(theta) - 0.5*rho*Cd*A*v^2) * v <= P_ret_max
        Returns v_retarder in m/s (or infinity if not downhill grade constrained).
        """
        if grade_rad <= 0:
            return float('inf')

        mass_kg = veh_params.mass_loaded_kg if is_loaded else veh_params.mass_empty_kg
        g = env_params.gravity_mps2
        p_ret_max_w = veh_params.max_retarder_kw * 1000.0

        f_grade = mass_kg * g * math.sin(grade_rad)
        f_roll = env_params.c_rr_default * mass_kg * g * math.cos(grade_rad)

        net_gravity_pull = f_grade - f_roll
        if net_gravity_pull <= 0:
            return float('inf')

        v_low = 0.1
        v_high = 35.0
        for _ in range(30):
            v_mid = (v_low + v_high) / 2.0
            f_aero = 0.5 * env_params.air_density_kgm3 * veh_params.drag_coeff * veh_params.frontal_area_m2 * (v_mid ** 2)
            f_ret_req = max(0.0, net_gravity_pull - f_aero)
            p_req = f_ret_req * v_mid
            if p_req > p_ret_max_w:
                v_high = v_mid
            else:
                v_low = v_mid

        return v_mid
