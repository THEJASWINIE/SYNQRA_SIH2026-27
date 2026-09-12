"""
models/vehicle.py
-----------------
Defines the Vehicle entity and state vector for the BEML BH100-class reference
mining dump truck in the FOG-ORCHESTRATOR 2.0 digital twin.

Features:
- Complete state vector (position, speed, acceleration, mass, payload, etc.)
- Strict input validation against NaN, Inf, and negative mass
- Integration with VehiclePhysics for single-vehicle deterministic time stepping

Evidence Tags:
- Mass & Dimensions: [REFERENCE] BEML BH100 specifications.
- State Schema: [MODEL CONFIG] System state vector for Task 2.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
import math
import os
import yaml

from models.vehicle_physics import VehiclePhysics


@dataclass
class VehicleState:
    """
    Complete state vector for an individual haul vehicle in the digital twin.
    Maps directly to internal state and Task-3 telemetry data structures.
    """
    id: str
    timestamp: float = 0.0
    position_s: float = 0.0              # Longitudinal position along current road segment (m)
    road_edge: str = ""                  # Current road segment ID
    lane_or_direction: str = "forward"   # Direction of travel: 'forward' or 'reverse'
    lateral_offset_m: float = 0.0        # Virtual lane lateral offset from road centerline (m)
    speed_v: float = 0.0                 # Longitudinal speed (m/s)
    acceleration_a: float = 0.0          # Longitudinal acceleration (m/s^2)
    grade_theta: float = 0.0             # Local road grade (radians)
    mass_m: float = 74000.0              # Total vehicle mass (kg) [REFERENCE: Tare ~74 t]
    payload_tonnes: float = 0.0          # Ore payload mass (tonnes) [REFERENCE: Rated ~91.5 t]
    is_loaded: bool = False              # True if vehicle is carrying payload
    friction_est_mu: float = 0.65        # Estimated tire-road friction coefficient
    friction_sigma: float = 0.05         # Uncertainty standard deviation on friction
    visibility_R: float = 50.0           # Effective optical visibility / perception range (m)
    comm_confidence: float = 1.0         # V2V / LoRa communication confidence score [0.0, 1.0]
    brake_state: str = "RELEASED"        # Mechanical / hydraulic brake state
    retarder_state: str = "OFF"          # Downhill retarder status
    risk_state: str = "NOMINAL"          # Risk status: 'NOMINAL', 'CAUTION', 'CRITICAL'
    availability_state: str = "READY"    # 'READY', 'HAULING', 'QUEUED', 'LOADING', 'DUMPING', 'FAULT'
    target_speed: float = 0.0            # Commanded target speed (m/s)
    target_slot: Optional[str] = None    # Assigned Tier-2 conflict slot ID


class Vehicle:
    """
    Represents an individual mining haul truck instance in the digital twin.
    Encapsulates physical parameters, vehicle state, and longitudinal dynamics integration.
    """
    def __init__(self, vehicle_id: str, config: Optional[Dict[str, Any]] = None):
        self.vehicle_id = vehicle_id
        self.config = config or {}
        
        # Extract vehicle config
        v_cfg = self.config.get("vehicle", self.config)
        mass_cfg = v_cfg.get("mass", {})
        
        self.tare_mass_kg = float(mass_cfg.get("tare_tonnes", 74.0)) * 1000.0
        self.rated_payload_kg = float(mass_cfg.get("rated_payload_tonnes", 91.5)) * 1000.0
        
        if self.tare_mass_kg <= 0.0:
            raise ValueError(f"Tare mass must be strictly positive, got {self.tare_mass_kg} kg")

        self.state = VehicleState(id=vehicle_id, mass_m=self.tare_mass_kg)
        self.physics = VehiclePhysics(self.config)

    @classmethod
    def from_yaml(cls, vehicle_id: str, yaml_path: str) -> "Vehicle":
        """Factory constructor loading physical parameters directly from vehicle.yaml."""
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Vehicle config file not found: {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cls(vehicle_id=vehicle_id, config=cfg)

    def set_payload(self, payload_tonnes: float) -> None:
        """
        Update vehicle payload and gross mass.
        Ensures mass invariants (mass > 0, no NaN/Inf).
        """
        if not isinstance(payload_tonnes, (int, float)):
            raise TypeError("Payload must be numeric")
        if math.isnan(payload_tonnes) or math.isinf(payload_tonnes):
            raise ValueError("Payload cannot be NaN or Infinite")
        if payload_tonnes < 0.0:
            raise ValueError(f"Payload cannot be negative, got {payload_tonnes} t")

        self.state.payload_tonnes = float(payload_tonnes)
        self.state.is_loaded = (payload_tonnes > 0.0)
        self.state.mass_m = self.tare_mass_kg + (self.state.payload_tonnes * 1000.0)

    def update_position(self, road_edge_id: str, position_s: float) -> None:
        """Update road segment ID and longitudinal position."""
        if math.isnan(position_s) or math.isinf(position_s):
            raise ValueError("position_s cannot be NaN or Infinite")
        self.state.road_edge = road_edge_id
        self.state.position_s = position_s

    def update_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Update vehicle state vector from a telemetry packet."""
        for key, value in telemetry.items():
            if hasattr(self.state, key):
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    raise ValueError(f"Telemetry field '{key}' contains invalid NaN/Inf value")
                setattr(self.state, key, value)

    def step(
        self,
        dt: float,
        f_drive: float,
        f_brake: float,
        f_retarder: float,
        grade_rad: float,
        mu: float,
        c_rr: float = 0.025
    ) -> Tuple[float, float, float]:
        """
        Advance vehicle kinematics by one deterministic timestep dt.
        Updates internal VehicleState and returns (new_position, new_speed, acceleration).
        """
        new_pos, new_speed, accel = self.physics.step(
            dt=dt,
            current_position_m=self.state.position_s,
            current_speed_mps=self.state.speed_v,
            grade_rad=grade_rad,
            mass_kg=self.state.mass_m,
            f_drive=f_drive,
            f_brake=f_brake,
            f_retarder=f_retarder,
            mu=mu,
            c_rr=c_rr
        )

        self.state.position_s = new_pos
        self.state.speed_v = new_speed
        self.state.acceleration_a = accel
        self.state.grade_theta = grade_rad
        self.state.friction_est_mu = mu
        self.state.timestamp += dt

        return new_pos, new_speed, accel

    def get_state(self) -> VehicleState:
        """Return the current vehicle state vector."""
        return self.state
