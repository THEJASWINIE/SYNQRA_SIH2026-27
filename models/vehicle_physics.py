"""
models/vehicle_physics.py
-------------------------
Implements the longitudinal force balance and deterministic kinematic motion
equations for heavy mining haul trucks (BEML BH100-class reference model).

Equations:
- m * dv/dt = F_drive + m*g*sin(theta) - F_roll - F_aero - F_retarder - F_brake
- F_roll = C_rr * m * g * cos(theta)
- F_aero = 0.5 * rho * C_D * A * v^2
- F_mu = mu * m * g * cos(theta)
- F_available = min(F_hardware_max, F_mu)

Evidence Tags:
- Dynamic Model: [VERIFIED / PRIMARY] Classical longitudinal dynamics.
- Parameters: [REFERENCE] for BH100 geometry; [MODEL CONFIG] for standard atmospheric/tire constants.
"""

from typing import Dict, Any, Tuple
import math


GRAVITY_G: float = 9.81  # Standard gravitational acceleration (m/s^2) [VERIFIED]


class VehiclePhysics:
    """
    Longitudinal vehicle dynamics engine calculating instantaneous forces,
    accelerations, tractive/braking constraints, and single-step numerical integration.
    """
    def __init__(self, vehicle_config: Dict[str, Any]):
        """
        Initialize vehicle physics model with parameters from vehicle.yaml.
        """
        v_cfg = vehicle_config.get("vehicle", vehicle_config)
        
        powertrain = v_cfg.get("powertrain", {})
        braking = v_cfg.get("braking", {})
        geometry = v_cfg.get("geometry", {})
        
        self.max_engine_power_w = float(powertrain.get("max_engine_power_kw", 895.0)) * 1000.0
        self.max_retarder_power_w = float(powertrain.get("max_retarder_power_kw", 1200.0)) * 1000.0
        self.max_drive_force_n = float(powertrain.get("max_drive_force_n", 350000.0))
        
        self.f_hardware_max_n = float(braking.get("f_hardware_max_n", 450000.0))
        self.c_rr_default = float(braking.get("rolling_resistance_coeff", 0.025))
        self.cd = float(braking.get("drag_coefficient_cd", 0.9))
        self.frontal_area = float(braking.get("frontal_area_m2", 22.0))
        self.rho_air = float(braking.get("air_density_kg_m3", 1.225))

    def _validate_inputs(self, **kwargs: float) -> None:
        """Ensure no input is NaN, infinite, or physically invalid."""
        for name, val in kwargs.items():
            if not isinstance(val, (int, float)):
                raise TypeError(f"Input '{name}' must be numeric, got {type(val).__name__}")
            if math.isnan(val):
                raise ValueError(f"Input '{name}' cannot be NaN")
            if math.isinf(val):
                raise ValueError(f"Input '{name}' cannot be infinite")

    def calculate_rolling_resistance(
        self,
        mass_kg: float,
        grade_rad: float,
        c_rr: float
    ) -> float:
        """
        Calculate rolling resistance force magnitude:
        F_roll = C_rr * m * g * cos(theta)
        """
        self._validate_inputs(mass_kg=mass_kg, grade_rad=grade_rad, c_rr=c_rr)
        if mass_kg <= 0.0:
            raise ValueError(f"Vehicle mass must be strictly positive, got {mass_kg} kg")
        if c_rr < 0.0:
            raise ValueError(f"Rolling resistance coefficient must be non-negative, got {c_rr}")

        return c_rr * mass_kg * GRAVITY_G * math.cos(grade_rad)

    def calculate_aerodynamic_drag(
        self,
        speed_mps: float
    ) -> float:
        """
        Calculate aerodynamic drag force magnitude:
        F_aero = 0.5 * rho * C_D * A * v^2
        """
        self._validate_inputs(speed_mps=speed_mps)
        return 0.5 * self.rho_air * self.cd * self.frontal_area * (speed_mps ** 2)

    def calculate_traction_limit(
        self,
        mass_kg: float,
        grade_rad: float,
        mu: float
    ) -> float:
        """
        Calculate maximum longitudinal tire-road traction/friction force:
        F_mu = mu * m * g * cos(theta)
        """
        self._validate_inputs(mass_kg=mass_kg, grade_rad=grade_rad, mu=mu)
        if mass_kg <= 0.0:
            raise ValueError(f"Vehicle mass must be strictly positive, got {mass_kg} kg")
        if mu <= 0.0:
            raise ValueError(f"Friction coefficient mu must be positive, got {mu}")

        return mu * mass_kg * GRAVITY_G * math.cos(grade_rad)

    def calculate_available_braking_force(
        self,
        mass_kg: float,
        grade_rad: float,
        mu: float
    ) -> float:
        """
        Calculate maximum available friction braking force bounded by hardware and tire adhesion:
        F_available = min(F_hardware_max, F_mu)
        """
        f_mu = self.calculate_traction_limit(mass_kg, grade_rad, mu)
        return min(self.f_hardware_max_n, f_mu)

    def calculate_longitudinal_forces(
        self,
        speed_mps: float,
        grade_rad: float,
        mass_kg: float,
        f_drive: float,
        f_brake: float,
        f_retarder: float,
        mu: float,
        c_rr: float = 0.025
    ) -> Dict[str, float]:
        """
        Evaluate full longitudinal force breakdown acting on the vehicle.
        
        m * dv/dt = F_drive + m*g*sin(theta) - F_roll - F_aero - F_retarder - F_brake
        """
        self._validate_inputs(
            speed_mps=speed_mps,
            grade_rad=grade_rad,
            mass_kg=mass_kg,
            f_drive=f_drive,
            f_brake=f_brake,
            f_retarder=f_retarder,
            mu=mu,
            c_rr=c_rr
        )

        if mass_kg <= 0.0:
            raise ValueError(f"Vehicle mass must be strictly positive, got {mass_kg} kg")
        if f_drive < 0.0:
            raise ValueError(f"f_drive must be non-negative, got {f_drive}")
        if f_brake < 0.0:
            raise ValueError(f"f_brake must be non-negative, got {f_brake}")
        if f_retarder < 0.0:
            raise ValueError(f"f_retarder must be non-negative, got {f_retarder}")

        # 1. Tire traction limit
        f_mu = self.calculate_traction_limit(mass_kg, grade_rad, mu)

        # 2. Bound drive force by hardware max and tire slip limit
        f_drive_clamped = min(f_drive, self.max_drive_force_n, f_mu)

        # 3. Grade force: + downhill, - uphill
        f_grade = mass_kg * GRAVITY_G * math.sin(grade_rad)

        # 4. Rolling resistance
        f_roll_mag = self.calculate_rolling_resistance(mass_kg, grade_rad, c_rr)

        # 5. Aerodynamic drag
        f_aero_mag = self.calculate_aerodynamic_drag(speed_mps)

        # 6. Available braking limit
        f_avail_brake = min(self.f_hardware_max_n, f_mu)
        
        # Total commanded braking bounded by physical available limit
        total_requested_braking = f_brake + f_retarder
        if total_requested_braking > f_avail_brake and total_requested_braking > 0:
            scale = f_avail_brake / total_requested_braking
            f_brake_clamped = f_brake * scale
            f_retarder_clamped = f_retarder * scale
        else:
            f_brake_clamped = f_brake
            f_retarder_clamped = f_retarder

        # Determine directional resistance
        if speed_mps > 1e-4:
            f_roll = f_roll_mag
            f_aero = f_aero_mag
            f_brake_effective = f_brake_clamped
            f_retarder_effective = f_retarder_clamped
            net_force = f_drive_clamped + f_grade - f_roll - f_aero - f_retarder_effective - f_brake_effective
        elif speed_mps < -1e-4:
            f_roll = -f_roll_mag
            f_aero = -f_aero_mag
            f_brake_effective = -f_brake_clamped
            f_retarder_effective = -f_retarder_clamped
            net_force = f_drive_clamped + f_grade - f_roll - f_aero - f_retarder_effective - f_brake_effective
        else:
            # Standstill (v ~= 0)
            f_aero = 0.0
            driving_tendency = f_drive_clamped + f_grade
            
            # Static resistance + brakes balance driving tendency up to threshold
            max_static_holding = f_roll_mag + f_avail_brake
            if abs(driving_tendency) <= max_static_holding and f_drive_clamped == 0.0 and (f_brake_clamped > 0.0 or abs(driving_tendency) <= f_roll_mag):
                net_force = 0.0
                f_roll = driving_tendency if abs(driving_tendency) <= f_roll_mag else f_roll_mag * (1.0 if driving_tendency > 0 else -1.0)
                f_brake_effective = max(0.0, abs(driving_tendency) - abs(f_roll))
                f_retarder_effective = 0.0
            else:
                f_roll = f_roll_mag if driving_tendency > 0 else -f_roll_mag
                f_brake_effective = f_brake_clamped if driving_tendency > 0 else -f_brake_clamped
                f_retarder_effective = f_retarder_clamped if driving_tendency > 0 else -f_retarder_clamped
                net_force = driving_tendency - f_roll - f_brake_effective - f_retarder_effective

        return {
            "f_drive": f_drive_clamped,
            "f_grade": f_grade,
            "f_roll": f_roll,
            "f_aero": f_aero,
            "f_retarder": f_retarder_effective,
            "f_brake": f_brake_effective,
            "f_mu_limit": f_mu,
            "f_available_brake": f_avail_brake,
            "f_net": net_force
        }

    def step(
        self,
        dt: float,
        current_position_m: float,
        current_speed_mps: float,
        grade_rad: float,
        mass_kg: float,
        f_drive: float,
        f_brake: float,
        f_retarder: float,
        mu: float,
        c_rr: float = 0.025
    ) -> Tuple[float, float, float]:
        """
        Execute one deterministic numerical simulation timestep dt.
        
        Returns:
            Tuple[float, float, float]: (new_position_m, new_speed_mps, new_acceleration_mps2)
        """
        self._validate_inputs(
            dt=dt,
            current_position_m=current_position_m,
            current_speed_mps=current_speed_mps,
            grade_rad=grade_rad,
            mass_kg=mass_kg,
            f_drive=f_drive,
            f_brake=f_brake,
            f_retarder=f_retarder,
            mu=mu,
            c_rr=c_rr
        )

        if dt <= 0.0:
            raise ValueError(f"Simulation timestep dt must be strictly positive, got {dt} s")
        if mass_kg <= 0.0:
            raise ValueError(f"Mass must be strictly positive, got {mass_kg} kg")

        forces = self.calculate_longitudinal_forces(
            speed_mps=current_speed_mps,
            grade_rad=grade_rad,
            mass_kg=mass_kg,
            f_drive=f_drive,
            f_brake=f_brake,
            f_retarder=f_retarder,
            mu=mu,
            c_rr=c_rr
        )

        f_net = forces["f_net"]
        acceleration = f_net / mass_kg

        # Euler integration with standstill velocity clamping
        new_speed = current_speed_mps + acceleration * dt

        # If braking brings forward motion to zero, clamp at zero (prevent reverse acceleration from brakes)
        if current_speed_mps > 0.0 and new_speed < 0.0 and f_drive == 0.0:
            new_speed = 0.0
            acceleration = -current_speed_mps / dt

        # Average velocity for displacement update
        v_avg = 0.5 * (current_speed_mps + new_speed)
        new_position = current_position_m + v_avg * dt

        return new_position, new_speed, acceleration
