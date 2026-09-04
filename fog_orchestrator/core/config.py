"""
Configuration Parameters for FOG-ORCHESTRATOR 2.0 (Post-Audit Corrected Version)
Operational Targets: NMDC Limited (BIOM-Kirandul, BIOM-Bacheli, Donimalai)
Reference Vehicle: BEML BH100 Heavy Mining Dumper Class
"""

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class VehicleParameters:
    """Parameters for representative BH100 Heavy Mining Dumper."""
    mass_empty_kg: float = 74000.0        # Empty tare mass (kg)
    mass_loaded_kg: float = 165000.0      # Maximum gross mass (kg)
    payload_rated_kg: float = 91000.0     # Rated iron ore payload (kg)
    length_m: float = 10.5                # Vehicle length (m)
    width_m: float = 5.2                  # Vehicle width (m)
    frontal_area_m2: float = 20.0         # Aerodynamic frontal area (m^2)
    drag_coeff: float = 0.70              # Aerodynamic drag coefficient (dimensionless)
    max_retarder_kw: float = 1200.0       # Dynamic electrical/hydraulic retarder power (kW)
    max_service_brake_n: float = 550000.0 # Maximum hydraulic service brake force (N)
    wheel_radius_m: float = 1.2           # Dynamic tire rolling radius (m)
    cg_height_m: float = 2.2              # Center of gravity height (m)
    wheelbase_m: float = 5.5              # Wheelbase length (m)
    max_acceleration_mps2: float = 1.2    # Maximum drive acceleration (m/s^2)
    max_deceleration_mps2: float = 3.5    # Maximum service brake deceleration (m/s^2)

@dataclass
class EnvironmentalParameters:
    """Ground-truth environmental and road parameters."""
    gravity_mps2: float = 9.81            # Acceleration due to gravity (m/s^2)
    air_density_kgm3: float = 1.225       # Standard sea-level air density (kg/m^3)
    c_rr_default: float = 0.020           # Baseline haul road rolling resistance coefficient
    mu_dry_default: float = 0.65          # Dry compacted haul road friction coefficient
    mu_wet_default: float = 0.35          # Wet/slick haul road friction coefficient
    mu_floor: float = 0.05                # Extreme slick friction lower bound
    v_mine_limit_kmh: float = 20.0        # Site regulatory maximum speed limit (km/h)

@dataclass
class PerceptionCommParameters:
    """Perception latency and communication confidence parameters."""
    tau_sensor_s: float = 0.10            # FMCW Radar / LiDAR processing latency (s)
    tau_comm_s: float = 0.10              # V2X network transmission latency (s)
    tau_ecu_s: float = 0.25               # ECU brake actuation & hydraulic line pressure buildup delay (s)
    tau_human_s: float = 0.50             # Human driver reaction time (s)
    s_base_m: float = 5.0                 # Standstill safety buffer margin (m)
    k_comm_s: float = 0.50                # Communication uncertainty penalty factor (s)
    k_sigma_friction: float = 2.0         # Friction estimation uncertainty multiplier (k * sigma_mu)

@dataclass
class SolverParameters:
    """Parameters for Tier 3 RHC / MPC Optimization Engine."""
    prediction_horizon: int = 10          # Prediction steps
    time_step_s: float = 2.0              # MPC time step dt (s)
    prob_safety_target: float = 0.99      # Chance constraint target for vehicle safe speed
    prob_flow_target: float = 0.95        # Chance constraint target for road segment flow
    prob_queue_target: float = 0.95       # Chance constraint target for node queue capacity
    arrival_shaping_buffer: float = 0.10  # Delta buffer reduction on arrival rate (fraction of mu)
    max_solve_time_s: float = 10.0        # Optimizer maximum allowed solve time limit (s)

DEFAULT_VEHICLE = VehicleParameters()
DEFAULT_ENV = EnvironmentalParameters()
DEFAULT_COMM = PerceptionCommParameters()
DEFAULT_SOLVER = SolverParameters()
