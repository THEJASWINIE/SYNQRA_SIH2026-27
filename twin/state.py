"""
twin/state.py
-------------
Defines the centralized, synchronized Digital Twin State container.
Maintains complete ground truth for environment, road segments, vehicles,
service nodes, queues, commands, warnings, and simulation clock.

Evidence Tags:
- State Synchronization: [VERIFIED / PRIMARY] Central synchronized twin representation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from models.vehicle import VehicleState


@dataclass
class EnvironmentState:
    """Instantaneous environmental and weather field state."""
    weather_mode: str = "CLEAR"         # 'CLEAR', 'MODERATE_FOG', 'DENSE_FOG', 'EXTREME_FOG'
    default_visibility_m: float = 50.0  # Network baseline optical visibility
    default_friction_mu: float = 0.65   # Baseline tire-road adhesion
    default_friction_sigma: float = 0.05
    default_crr: float = 0.025
    surface_state: str = "dry"          # 'dry', 'damp', 'wet', 'saturated'
    forecast_confidence: float = 1.0    # Forecast confidence score [0.0, 1.0]


@dataclass
class RoadSegmentState:
    """Instantaneous state of a road segment edge."""
    id: str
    from_node: str
    to_node: str
    length_m: float
    grade_pct: float
    curve_radius_m: float
    width_m: float
    direction_mode: str
    speed_limit_mps: float
    surface_state: str = "dry"
    visibility_m: float = 50.0
    friction_mu: float = 0.65
    friction_sigma: float = 0.05
    safe_speed_mps: float = 11.11
    safe_headway_m: float = 15.52
    capacity_vph: float = 600.0
    active_vehicles_count: int = 0
    bottleneck_score: float = 0.0
    active_slots: List[str] = field(default_factory=list)


@dataclass
class ServiceNodeState:
    """Instantaneous state of a shovel, crusher, switchback, or buffer node."""
    id: str
    node_type: str
    service_rate_vph: float
    queue_length: float = 0.0
    queue_max: int = 8
    utilization_rho: float = 0.0
    is_blocked: bool = False
    criticality: float = 0.5
    total_arrivals: float = 0.0
    total_departures: float = 0.0
    total_blocked: float = 0.0


@dataclass
class AlertEntry:
    """System notification, safety warning, or operational alert."""
    timestamp: float
    level: str  # 'INFO', 'WARNING', 'CRITICAL'
    source: str
    message: str


@dataclass
class TwinState:
    """
    Master synchronized state container for the FOG-ORCHESTRATOR 2.0 digital twin.
    """
    timestamp: float = 0.0
    step_count: int = 0
    dt_seconds: float = 1.0
    mode: str = "STANDALONE_SIMULATION"
    
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    roads: Dict[str, RoadSegmentState] = field(default_factory=dict)
    nodes: Dict[str, ServiceNodeState] = field(default_factory=dict)
    vehicles: Dict[str, VehicleState] = field(default_factory=dict)
    
    active_bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    active_alerts: List[AlertEntry] = field(default_factory=list)
    
    # Cumulative Operational KPIs
    total_tonnage_delivered: float = 0.0
    safety_violations_count: int = 0
    total_stops_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state container into serializable dictionary."""
        return {
            "timestamp": self.timestamp,
            "step_count": self.step_count,
            "dt_seconds": self.dt_seconds,
            "mode": self.mode,
            "environment": {
                "weather_mode": self.environment.weather_mode,
                "visibility_m": self.environment.default_visibility_m,
                "friction_mu": self.environment.default_friction_mu,
                "surface_state": self.environment.surface_state,
                "confidence": self.environment.forecast_confidence
            },
            "num_vehicles": len(self.vehicles),
            "num_roads": len(self.roads),
            "num_nodes": len(self.nodes),
            "total_tonnage_delivered": self.total_tonnage_delivered,
            "safety_violations_count": self.safety_violations_count,
            "active_alerts_count": len(self.active_alerts),
            "active_bottlenecks_count": len(self.active_bottlenecks)
        }
