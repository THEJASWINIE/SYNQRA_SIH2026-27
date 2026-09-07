"""
Configuration dataclasses and default parameters for FOG-SAFE system.
Reference Vehicle: BEML BH100 Heavy Mining Dumper (NMDC Open-Cast Haulage).
"""

from dataclasses import dataclass, field
import numpy as np

@dataclass
class VehicleParameters:
    """Representative parameters for BEML BH100-class heavy dumper."""
    mass_empty: float = 74000.0        # kg
    mass_loaded: float = 165000.0      # kg (74,000 kg empty + 91,000 kg payload)
    payload_rated: float = 91000.0     # kg
    frontal_area: float = 20.0         # m^2
    drag_coefficient: float = 0.7      # Cd (dimensionless)
    retarder_power_max: float = 1200000.0 # W (1200 kW continuous retarding capacity)
    hardware_brake_max_force: float = 550000.0 # N (Maximum service brake mechanical limit)
    wheel_base: float = 5.0            # m
    cg_height: float = 2.5             # m

@dataclass
class EnvironmentParameters:
    """Environmental and ambient condition parameters."""
    air_density: float = 1.225         # kg/m^3
    gravity: float = 9.81              # m/s^2
    mu_prior: float = 0.35             # Standard simulation prior (wet mine haul road)
    c_rr_default: float = 0.02         # Default rolling resistance coefficient

@dataclass
class ReactionTimeParameters:
    """Latency decomposition for total reaction time tau_total (seconds)."""
    tau_sensor: float = 0.10           # Sensor processing latency (s)
    tau_comm_base: float = 0.10        # Nominal V2X communication latency (s)
    tau_decision: float = 0.10        # ECU decision loop latency (s)
    tau_human: float = 0.50           # Driver reaction / override latency (s)

    @property
    def tau_total_nominal(self) -> float:
        return self.tau_sensor + self.tau_comm_base + self.tau_decision + self.tau_human

@dataclass
class SafetyMarginParameters:
    """Safety margin parameters (meters)."""
    s_base: float = 5.0                # Base buffer distance (m)
    k_comm: float = 0.5                # Adaptive margin factor for comm degradation (s)

@dataclass
class TractionCeilingParameters:
    """
    SAFETY CONSTRAINT — conservative operational ceiling on traction-limited speed.

    This is a safety constraint, NOT a hidden tuning constant. It exists because the
    purely physical traction limit

        v_traction = sqrt(2 * a_tr_max * R_effective)

    permits speeds on low-friction surfaces that the project does not accept
    operationally. The ceiling bounds permitted speed proportionally to the available
    tire-road friction:

        v_traction_ceiling = ceiling_factor_mps * mu

    PROVENANCE: `ceiling_factor_mps` is the EXISTING project parameter
    `traction_speed_factor_mps`, defined in
    `SYNQRA_SIH2026-27-main/config/vehicle.yaml` (MODEL CONFIG section) as
    "Traction safe speed multiplier (v_traction = factor * mu)". It is supplied by the
    caller; no value is invented or hardcoded here.

    When `ceiling_factor_mps` is None the ceiling is NOT applied and the solver uses the
    physical traction limit alone. A caller with no configured value therefore gets the
    unmodified physical model rather than a silently assumed ceiling.
    """
    ceiling_factor_mps: float = None    # m/s per unit mu; None => ceiling not configured


@dataclass
class SiteParameters:
    """Mine site operational speed & geometry bounds (NMDC reference)."""
    v_mine_max_kmh: float = 20.0       # km/h (Site regulatory speed limit)
    default_curve_radius: float = 50.0 # m

    @property
    def v_mine_max_ms(self) -> float:
        return self.v_mine_max_kmh / 3.6
