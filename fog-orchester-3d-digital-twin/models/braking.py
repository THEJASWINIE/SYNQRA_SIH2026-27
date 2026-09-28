"""
models/braking.py
-----------------
Implements the core FOG-SAFE vehicle safety engine:
- Stopping distance, reaction distance, and conservative emergency braking
- Safe stopping distance invariant: S_stop + S_margin <= R_effective
- Safe-speed multi-constraint envelope solution:
  v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
- Command speed enforcement:
  v_command = min(v_dispatch, v_safe)

Evidence Tags:
- Invariant: [VERIFIED / PRIMARY] Physical stopping envelope.
- Safety Engine: [MODEL CONFIG] Multi-constraint lower envelope.
- Latencies & Margins: [MODEL CONFIG] From vehicle.yaml configuration.
"""

from typing import Dict, Any, Tuple, Optional
import math
from models.vehicle_physics import GRAVITY_G
from models.retarder import RetarderModel


class BrakingModel:
    """
    Evaluates reaction latencies, conservative deceleration on grade,
    stopping envelopes, and solves for the physical safe-speed ceiling v_safe.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        v_cfg = cfg.get("vehicle", cfg)
        
        braking = v_cfg.get("braking", {})
        latency = v_cfg.get("latency", {})
        geometry = v_cfg.get("geometry", {})
        powertrain = v_cfg.get("powertrain", {})

        self.f_hardware_max_n = float(braking.get("f_hardware_max_n", 450000.0))
        self.c_rr_default = float(braking.get("rolling_resistance_coeff", 0.025))
        self.standstill_margin_m = float(geometry.get("standstill_margin_m", 5.0))
        self.max_drive_force_n = float(powertrain.get("max_drive_force_n", 350000.0))

        # Latency breakdown
        self.tau_sensor = float(latency.get("sensor_s", 0.05))
        self.tau_comm = float(latency.get("comm_s", 0.05))
        self.tau_decision = float(latency.get("decision_s", 0.05))
        self.tau_human = float(latency.get("human_reaction_s", 0.00))
        self.tau_hydraulic = float(latency.get("hydraulic_buildup_s", 0.25))
        
        self.tau_total_default = self.calculate_total_latency(
            self.tau_sensor, self.tau_comm, self.tau_decision, self.tau_human, self.tau_hydraulic
        )

        self.retarder_model = RetarderModel(cfg)

    def calculate_total_latency(
        self,
        tau_sensor: Optional[float] = None,
        tau_comm: Optional[float] = None,
        tau_decision: Optional[float] = None,
        tau_human: Optional[float] = None,
        tau_hydraulic: Optional[float] = None
    ) -> float:
        """
        Calculate total system reaction latency:
        tau_total = tau_sensor + tau_communication + tau_decision + tau_human + tau_hydraulic
        """
        ts = self.tau_sensor if tau_sensor is None else tau_sensor
        tc = self.tau_comm if tau_comm is None else tau_comm
        td = self.tau_decision if tau_decision is None else tau_decision
        th = self.tau_human if tau_human is None else tau_human
        thyd = self.tau_hydraulic if tau_hydraulic is None else tau_hydraulic

        for name, val in [("tau_sensor", ts), ("tau_comm", tc), ("tau_decision", td), ("tau_human", th), ("tau_hydraulic", thyd)]:
            if math.isnan(val) or math.isinf(val) or val < 0.0:
                raise ValueError(f"Latency component '{name}' must be non-negative, got {val}")

        return ts + tc + td + th + thyd

    def calculate_deceleration_on_grade(
        self,
        mass_kg: float,
        grade_rad: float,
        mu_safe: float,
        c_rr: float = 0.025
    ) -> float:
        """
        Evaluate conservative emergency braking deceleration on a given slope:
        a_dec = (min(F_hardware_max, mu_safe * m * g * cos(theta)) + C_rr * m * g * cos(theta) - m * g * sin(theta)) / m
        """
        if mass_kg <= 0.0 or math.isnan(mass_kg) or math.isinf(mass_kg):
            raise ValueError(f"Mass must be strictly positive, got {mass_kg} kg")
        if mu_safe <= 0.0 or math.isnan(mu_safe) or math.isinf(mu_safe):
            raise ValueError(f"mu_safe must be positive, got {mu_safe}")

        # Conservative available friction braking force (aero drag strictly excluded)
        f_mu = mu_safe * mass_kg * GRAVITY_G * math.cos(grade_rad)
        f_avail_brake = min(self.f_hardware_max_n, f_mu)
        
        f_roll = c_rr * mass_kg * GRAVITY_G * math.cos(grade_rad)
        f_grade = mass_kg * GRAVITY_G * math.sin(grade_rad)

        net_stopping_force = f_avail_brake + f_roll - f_grade
        a_dec = net_stopping_force / mass_kg

        return max(0.01, a_dec)  # Ensure non-zero positive deceleration

    def calculate_stopping_distance(
        self,
        speed_mps: float,
        a_dec: float,
        tau_total: float
    ) -> Tuple[float, float, float]:
        """
        Calculate stopping distance components:
        d_reaction = v * tau_total
        d_brake = v^2 / (2 * a_dec)
        S_stop = d_reaction + d_brake
        """
        if speed_mps < 0.0 or math.isnan(speed_mps) or math.isinf(speed_mps):
            raise ValueError(f"speed_mps must be non-negative, got {speed_mps}")
        if a_dec <= 0.0 or math.isnan(a_dec) or math.isinf(a_dec):
            raise ValueError(f"a_dec must be positive, got {a_dec}")
        if tau_total < 0.0 or math.isnan(tau_total) or math.isinf(tau_total):
            raise ValueError(f"tau_total must be non-negative, got {tau_total}")

        d_reaction = speed_mps * tau_total
        d_brake = (speed_mps ** 2) / (2.0 * a_dec)
        s_stop = d_reaction + d_brake

        return d_reaction, d_brake, s_stop

    def solve_safe_speed_stopping(
        self,
        r_effective: float,
        a_dec: float,
        tau_total: float,
        s_margin: float = 5.0
    ) -> float:
        """
        Inverts S_stop + S_margin <= R_effective to solve for maximum allowable entry speed v_stop:
        v_stop = -a_dec * tau_total + sqrt((a_dec * tau_total)^2 + 2 * a_dec * max(0, R_eff - S_margin))
        """
        if r_effective < 0.0 or math.isnan(r_effective) or math.isinf(r_effective):
            raise ValueError(f"r_effective must be non-negative, got {r_effective}")
        if a_dec <= 0.0:
            raise ValueError(f"a_dec must be strictly positive, got {a_dec}")

        d_avail = max(0.0, r_effective - s_margin)
        if d_avail <= 1e-4:
            return 0.0

        b = a_dec * tau_total
        discriminant = (b ** 2) + (2.0 * a_dec * d_avail)
        v_stop = -b + math.sqrt(discriminant)

        return max(0.0, v_stop)

    def calculate_curve_speed(
        self,
        curve_radius_m: float,
        mu_safe: float,
        lateral_factor: float = 0.7
    ) -> float:
        """
        Calculate maximum safe speed on a curve to prevent lateral slip / rollover:
        v_curve = sqrt(lateral_factor * mu_safe * g * R_curve)
        """
        if curve_radius_m <= 0.0 or math.isnan(curve_radius_m) or math.isinf(curve_radius_m):
            raise ValueError(f"curve_radius_m must be strictly positive, got {curve_radius_m}")
        return math.sqrt(lateral_factor * mu_safe * GRAVITY_G * curve_radius_m)

    def calculate_safe_speed(
        self,
        r_effective: float,
        grade_rad: float,
        mass_kg: float,
        mu_safe: float,
        curve_radius_m: float,
        speed_limit_mine_mps: float,
        tau_total: Optional[float] = None,
        c_rr: float = 0.025,
        s_margin: float = 5.0
    ) -> Dict[str, float]:
        """
        Compute the complete multi-constraint safe speed envelope:
        v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
        """
        tau = self.tau_total_default if tau_total is None else tau_total

        # 1. Stopping sight distance speed
        a_dec = self.calculate_deceleration_on_grade(mass_kg, grade_rad, mu_safe, c_rr)
        v_stop = self.solve_safe_speed_stopping(r_effective, a_dec, tau, s_margin)

        # 2. Downhill retarder thermal speed
        v_ret = self.retarder_model.calculate_max_sustainable_downhill_speed(
            mass_kg=mass_kg,
            grade_rad=grade_rad,
            c_rr=c_rr
        )

        # 3. Curve slip / rollover speed
        v_curve = self.calculate_curve_speed(curve_radius_m, mu_safe)

        # 4. Traction / Grade stability speed limit
        # Heavy mining dumpers operate up to nominal speed limit unless restricted
        v_traction = speed_limit_mine_mps

        # 5. Mine operational speed limit
        v_mine = speed_limit_mine_mps

        # Final physical envelope
        v_safe = min(v_stop, v_ret, v_traction, v_curve, v_mine)

        return {
            "v_safe": v_safe,
            "v_stop": v_stop,
            "v_retarder": v_ret,
            "v_curve": v_curve,
            "v_traction": v_traction,
            "v_mine": v_mine,
            "a_dec": a_dec,
            "tau_total": tau
        }

    @staticmethod
    def compute_command_speed(v_dispatch: float, v_safe: float) -> float:
        """
        Enforce the mandatory architectural invariant:
        v_command = min(v_dispatch, v_safe)
        Central optimization can NEVER override the local physics safety ceiling.
        """
        if math.isnan(v_dispatch) or math.isnan(v_safe):
            raise ValueError("Speed inputs cannot be NaN")
        return max(0.0, min(v_dispatch, v_safe))
