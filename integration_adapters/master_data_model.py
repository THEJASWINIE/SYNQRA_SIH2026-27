"""
integration_adapters/master_data_model.py
-----------------------------------------
FOG-ORCHESTRATOR 2.0 — Phase 9 Master Canonical Vehicle State Model
NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System

ONE Authoritative Vehicle State Model -> Multiple Specialized Views:
- Operator HMI View (Driver Screen)
- Control Room HMI View (Fleet Card & Alerts)
- Digital Twin View (State Mirror & Prediction)
- Safety Governor View (Local Tier-1 Authority)

Enforces:
1. Canonical field definitions across all subsystems.
2. Triple timestamping (event, receive, processing).
3. Explicit data age and freshness tracking.
4. Truthful data source identification (HARDWARE / SIMULATION / HYBRID).
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum
import time
from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    HARDWARE = "HARDWARE"
    SIMULATION = "SIMULATION"
    HYBRID = "HYBRID"


class MasterSensorQuality(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    MISSING = "MISSING"
    STUCK = "STUCK"
    OUTLIER = "OUTLIER"
    INCONSISTENT = "INCONSISTENT"
    UNKNOWN = "UNKNOWN"


class MasterSafetyState(str, Enum):
    NORMAL = "NORMAL"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE MODE"
    EMERGENCY = "EMERGENCY"


class DigitalTwinSyncState(str, Enum):
    SYNCHRONIZED = "SYNCHRONIZED"
    DRIFTING = "DRIFTING"
    DIVERGENT = "DIVERGENT"
    OFFLINE = "OFFLINE"


class MasterCanState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    TIMEOUT = "TIMEOUT"
    BUS_OFF = "BUS_OFF"


class VehicleState(BaseModel):
    """
    The Single Authoritative Canonical Vehicle State Model.
    All clients (Operator HMI, Control Room HMI, Digital Twin, Safety Governor)
    consume projected views derived from this exact schema.
    """
    # Vehicle Identity & Source
    vehicle_id: str = Field(..., description="Unique HEMM identifier, e.g. 'TRUCK_01'")
    data_source: DataSourceType = Field(DataSourceType.HARDWARE, description="HARDWARE, SIMULATION, or HYBRID")

    # Triple Timestamping & Synchronization Policy (Section 5)
    event_timestamp: float = Field(..., description="Sensor sampling timestamp (UTC or monotonic epoch seconds)")
    receive_timestamp: float = Field(..., description="Gateway arrival timestamp (UTC epoch seconds)")
    processing_timestamp: float = Field(..., description="Orchestrator processing timestamp (UTC epoch seconds)")
    clock_source: str = Field("UTC_NTP", description="Clock synchronization source: UTC_NTP, GPS_PPS, LOCAL_MONOTONIC")

    # Kinematics & Spatial Position
    position: float = Field(0.0, description="Linear track/segment position (meters)")
    position_x: float = Field(0.0, description="Mine Cartesian X coordinate (meters)")
    position_y: float = Field(0.0, description="Mine Cartesian Y coordinate (meters)")
    segment_id: str = Field("RAMP_01", description="Authoritative road segment identifier")
    heading: float = Field(0.0, description="Heading angle in radians (-pi to +pi)")
    speed: float = Field(0.0, ge=0.0, description="Current vehicle forward speed in m/s")
    acceleration: float = Field(0.0, description="Longitudinal acceleration in m/s^2")
    grade: float = Field(0.0, description="Road grade percentage (%): negative=downhill, positive=uphill")

    # Environmental Context
    visibility: float = Field(50.0, ge=0.0, description="Effective optical/fog visibility in meters")
    weather_state: str = Field("CLEAR", description="CLEAR, FOG_ENTRY, DENSE_FOG, FOG_PATCH, FOG_CLEARING")

    # Sensor Health & Confidence (Section 7)
    sensor_health: MasterSensorQuality = Field(MasterSensorQuality.VALID, description="8-state sensor quality")
    sensor_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Sensor confidence metric (0.0 to 1.0)")

    # RF & Gateway Metrics (Section 6 & 19)
    gateway_id: str = Field("GW_01", description="Associated or nearest gateway identifier")
    gateway_state: str = Field("CONNECTED", description="CONNECTED, DEGRADED, HANDOVER, DISCONNECTED")
    correlation_score: float = Field(1.0, ge=0.0, le=1.0, description="DSSS/PN correlation score or signal quality")
    RSSI: float = Field(-75.0, description="Received signal strength indicator in dBm")
    SNR: float = Field(8.0, description="Signal-to-noise ratio in dB")
    packet_loss: float = Field(0.0, ge=0.0, le=1.0, description="Calculated packet loss ratio (0.0 to 1.0)")

    # CAN / TWAI Bus Status (Section 22)
    CAN_state: MasterCanState = Field(MasterCanState.NORMAL, description="Vehicle CAN bus health state")
    CAN_latency: float = Field(1.2, ge=0.0, description="CAN frame round-trip/delivery latency in ms")

    # Safety & Actuation Envelope (Section 6 & 9)
    commanded_speed: float = Field(0.0, ge=0.0, description="Speed requested by central dispatch or driver in m/s")
    safe_speed: float = Field(11.8, ge=0.0, description="Authoritative Tier-1 safe speed envelope ceiling in m/s")
    brake_state: str = Field("RELEASED", description="Brake actuator state: RELEASED, ACTIVE, EMERGENCY, HOLD")
    safety_state: MasterSafetyState = Field(MasterSafetyState.NORMAL, description="6-state safety classification")
    failsafe_state: str = Field("NOMINAL", description="NOMINAL, STALE_HOLD, DEGRADED_SPEED, STOP, EMERGENCY")
    safe_beacon_state: str = Field("INACTIVE", description="INACTIVE, ACTIVE, RECOVERY")
    fault_code: str = Field("NONE", description="Diagnostic trouble code / fault string")

    # Digital Twin Synchronization State (Section 15)
    digital_twin_sync_state: DigitalTwinSyncState = Field(
        DigitalTwinSyncState.SYNCHRONIZED,
        description="SYNCHRONIZED, DRIFTING, DIVERGENT, OFFLINE"
    )

    # --------------------------------------------------------------------------
    # FRESHNESS & TIMING HELPERS
    # --------------------------------------------------------------------------
    def data_age_ms(self, now: Optional[float] = None) -> float:
        """Calculate data age in milliseconds relative to current epoch."""
        t_ref = now if now is not None else time.time()
        age_s = max(0.0, t_ref - self.event_timestamp)
        return age_s * 1000.0

    def is_stale(self, threshold_s: float = 1.0, now: Optional[float] = None) -> bool:
        """Return True if event timestamp is older than threshold."""
        t_ref = now if now is not None else time.time()
        return (t_ref - self.event_timestamp) > threshold_s

    def get_freshness_label(self, now: Optional[float] = None) -> str:
        """Formatted string for UI display: e.g. 'DATA AGE: 240 ms' or 'STALE: 2.4 s'."""
        age_ms = self.data_age_ms(now=now)
        if age_ms < 1000.0:
            return f"DATA AGE: {int(age_ms)} ms"
        else:
            return f"STALE: {age_ms / 1000.0:.1f} s"

    # --------------------------------------------------------------------------
    # SPECIALIZED VIEWS (PROJECTIONS)
    # --------------------------------------------------------------------------
    def to_operator_hmi_view(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Operator HMI (Driver Screen) View.
        Focused strictly on situational awareness, warnings, and safe guidance.
        """
        speed_kmh = round(self.speed * 3.6, 1)
        safe_kmh = round(self.safe_speed * 3.6, 1)

        # Map active operator action recommendation
        action = "MAINTAIN SPEED"
        if self.safety_state == MasterSafetyState.EMERGENCY:
            action = "EMERGENCY STOP IMMEDIATELY"
        elif self.speed > self.safe_speed + 0.1:
            action = "REDUCE SPEED"
        elif self.safety_state in [MasterSafetyState.SAFE_MODE, MasterSafetyState.DEGRADED]:
            action = "PROCEED WITH EXTREME CAUTION"
        elif self.visibility < 10.0:
            action = "DENSE FOG — SLOW DOWN"

        comm_status = "ONLINE"
        if self.safe_beacon_state == "ACTIVE" or self.gateway_state == "DISCONNECTED":
            comm_status = "COMMUNICATION LOST — SAFE MODE"
        elif self.gateway_state in ["DEGRADED", "HANDOVER"]:
            comm_status = "DEGRADED"

        return {
            "vehicle_id": self.vehicle_id,
            "speed_kmh": speed_kmh,
            "speed_mps": round(self.speed, 2),
            "safe_speed_kmh": safe_kmh,
            "safe_speed_mps": round(self.safe_speed, 2),
            "visibility_m": round(self.visibility, 1),
            "grade_pct": round(self.grade, 1),
            "brake_status": self.brake_state,
            "sensor_health": self.sensor_health.value,
            "communication_status": comm_status,
            "gateway_status": f"{self.gateway_id} ({self.gateway_state})",
            "safety_state": self.safety_state.value,
            "failsafe_state": self.failsafe_state,
            "active_warning": action,
            "data_age_label": self.get_freshness_label(now=now),
            "is_stale": self.is_stale(now=now),
        }

    def to_control_room_view(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Control Room HMI View.
        Fleet-level awareness, diagnostics, gateway associations, and incident cards.
        """
        return {
            "vehicle_id": self.vehicle_id,
            "data_source": self.data_source.value,
            "position": {
                "track_m": round(self.position, 1),
                "x_m": round(self.position_x, 1),
                "y_m": round(self.position_y, 1),
                "segment_id": self.segment_id,
            },
            "speed_kmh": round(self.speed * 3.6, 1),
            "safe_speed_kmh": round(self.safe_speed * 3.6, 1),
            "visibility_m": round(self.visibility, 1),
            "grade_pct": round(self.grade, 1),
            "gateway_id": self.gateway_id,
            "rf_metrics": {
                "rssi_dbm": self.RSSI,
                "snr_db": self.SNR,
                "packet_loss_pct": round(self.packet_loss * 100.0, 1),
                "correlation": round(self.correlation_score, 2),
            },
            "sensor_quality": self.sensor_health.value,
            "sensor_confidence": round(self.sensor_confidence, 2),
            "can_state": self.CAN_state.value,
            "can_latency_ms": round(self.CAN_latency, 2),
            "safety_state": self.safety_state.value,
            "failsafe_state": self.failsafe_state,
            "safe_beacon_active": (self.safe_beacon_state == "ACTIVE"),
            "digital_twin_sync": self.digital_twin_sync_state.value,
            "last_event_timestamp": self.event_timestamp,
            "data_age_ms": round(self.data_age_ms(now=now), 1),
            "freshness_label": self.get_freshness_label(now=now),
            "is_stale": self.is_stale(now=now),
            "fault_code": self.fault_code,
        }

    def to_digital_twin_view(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Digital Twin View.
        State mirroring and input for predictive simulation and what-if envelopes.
        """
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": self.event_timestamp,
            "position_m": self.position,
            "segment_id": self.segment_id,
            "heading_rad": self.heading,
            "speed_mps": self.speed,
            "accel_mps2": self.acceleration,
            "grade_pct": self.grade,
            "visibility_m": self.visibility,
            "friction_mu": 0.35 if self.weather_state in ["DENSE_FOG", "RAIN"] else 0.50,
            "safe_speed_mps": self.safe_speed,
            "safety_state": self.safety_state.value,
            "gateway_state": self.gateway_state,
            "safe_beacon_state": self.safe_beacon_state,
            "sensor_health": self.sensor_health.value,
            "confidence": self.sensor_confidence,
            "sync_status": self.digital_twin_sync_state.value,
            "data_age_ms": self.data_age_ms(now=now),
        }

    def to_safety_governor_view(self) -> Dict[str, Any]:
        """
        Local Safety Governor View.
        Vehicle-resident authoritative safety solver inputs.
        """
        return {
            "vehicle_id": self.vehicle_id,
            "actual_speed_mps": self.speed,
            "commanded_speed_mps": self.commanded_speed,
            "visibility_m": self.visibility,
            "grade_pct": self.grade,
            "sensor_quality": self.sensor_health.value,
            "sensor_confidence": self.sensor_confidence,
            "can_state": self.CAN_state.value,
            "safe_beacon_active": (self.safe_beacon_state == "ACTIVE"),
            "emergency_stop_latched": (self.safety_state == MasterSafetyState.EMERGENCY),
        }
