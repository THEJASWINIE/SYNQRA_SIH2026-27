"""
Physics Trajectory Simulator & Time-Stepping Engine.
"""

from dataclasses import dataclass
import numpy as np
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed, SafeSpeedResult

@dataclass
class SimulationStepState:
    """State vector at a single simulation time step t."""
    t: float
    position: float
    speed: float
    v_safe_result: SafeSpeedResult
    mu_true: float
    mu_hat: float
    r_effective: float
    c_comm: float
    headway: float
    safety_violation: bool

class DynamicSimulator:
    """
    Time-stepping physics simulator for vehicle haulage dynamics.
    """
    def __init__(
        self,
        vehicle: MiningVehicle,
        road: RoadSegment,
        env: EnvironmentState,
        comm: CommunicationModel,
        dt: float = 0.1
    ):
        self.vehicle = vehicle
        self.road = road
        self.env = env
        self.comm = comm
        self.dt = dt

    def run_timeline_scenario(
        self,
        duration: float,
        visibility_profile_fn,
        friction_profile_fn,
        comm_profile_fn,
        policy_type: str = "FOG_SAFE"
    ) -> list[SimulationStepState]:
        """
        Runs a time-series simulation under varying visibility, friction, and comm conditions.
        :param policy_type: "FOG_SAFE" (dynamic physics speed) or "STATIC_CONSERVATIVE" (fixed 10 km/h in fog)
        """
        num_steps = int(duration / self.dt)
        pos = 0.0
        v_current = 0.0

        trajectory = []

        for i in range(num_steps):
            t = i * self.dt
            r_eff = visibility_profile_fn(t)
            mu_t = friction_profile_fn(t)
            c_c = comm_profile_fn(t)

            self.env.r_effective = r_eff
            self.env.mu_true = mu_t
            self.comm.c_comm = c_c

            safe_res = solve_safe_speed(
                self.vehicle,
                self.road,
                self.env,
                self.comm,
                mu_effective=mu_t,
                r_effective=r_eff
            )

            if policy_type == "FOG_SAFE":
                v_target = safe_res.v_safe_ms
            elif policy_type == "STATIC_CONSERVATIVE":
                # Fixed conservative policy: 10 km/h (2.78 m/s) in fog (r_eff <= 30m), 20 km/h otherwise
                v_target = 2.778 if r_eff <= 30.0 else 5.556
            else:
                raise ValueError(f"Unknown policy type: {policy_type}")

            # Closed-loop speed controller: accelerate up to 1.0 m/s^2, decelerate up to a_dec
            a_dec_avail = safe_res.a_dec
            if v_current < v_target:
                dv_max = 1.0 * self.dt  # acceleration limit
                v_current = min(v_target, v_current + dv_max)
            else:
                dv_brake = max(0.5, a_dec_avail) * self.dt  # physical emergency braking rate
                v_current = max(v_target, v_current - dv_brake)

            pos += v_current * self.dt

            # Check safety violation: actual stopping distance at v_current vs r_eff
            tau_tot = self.comm.tau_total
            a_dec = safe_res.a_dec
            s_stop_act = v_current * tau_tot + ((v_current**2)/(2.0*a_dec) if a_dec > 0 else 1e6)
            s_margin_act = self.comm.calculate_safety_margin(v_current)

            violation = (s_stop_act + s_margin_act > r_eff + 1e-3) and (v_current > 0.1)

            step_state = SimulationStepState(
                t=t,
                position=pos,
                speed=v_current,
                v_safe_result=safe_res,
                mu_true=mu_t,
                mu_hat=mu_t, # assume baseline estimation
                r_effective=r_eff,
                c_comm=c_c,
                headway=s_stop_act + s_margin_act,
                safety_violation=violation
            )
            trajectory.append(step_state)

        return trajectory
