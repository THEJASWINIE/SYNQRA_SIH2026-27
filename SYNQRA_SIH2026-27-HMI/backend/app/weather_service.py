"""
FOG-ORCHESTRATOR 2.0 — Authoritative Environmental / Weather Station & Speed Governor Service.

Implements the authoritative causal closed loop:
    VEHICLE A / VEHICLE B
            │
            ▼
    LIVE MAX-SPEED CALIBRATION
            │
            ├── Vmax_A (TRUCK_01: 1.40 m/s, TB6612FNG)
            └── Vmax_B (TRUCK_02: 1.30 m/s, TB6612FNG)
                    │
                    ▼
          WEATHER / FOG INPUT
                    │
                    ▼
        DIGITAL TWIN ENVIRONMENT
                    │
                    ▼
          SAFETY SOLVER / GOVERNOR
                    │
                    ▼
       VEHICLE-SPECIFIC SAFE SPEED
                    │
                    ▼
          COMMAND SPEED CLAMP
                    │
                    ▼
        PWM COMMAND TO MOTOR
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       VEHICLE A           VEHICLE B

CLASSIFICATION:
  INJECTED ENVIRONMENTAL INPUT + PHYSICAL ACTUATOR RESPONSE
  (Explicit provenance: "WEATHER_STATION_INJECTED" / "INJECTED WEATHER-STATION ENVIRONMENTAL CONDITION")
"""

from __future__ import annotations

import json
import math
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FogCondition(str, Enum):
    CLEAR = "CLEAR"
    LIGHT = "LIGHT"
    LIGHT_FOG = "LIGHT_FOG"
    MODERATE = "MODERATE"
    MODERATE_FOG = "MODERATE_FOG"
    HEAVY = "HEAVY"
    HEAVY_FOG = "HEAVY_FOG"
    SEVERE = "SEVERE"
    SEVERE_FOG = "SEVERE_FOG"
    CRITICAL = "CRITICAL"
    CRITICAL_FOG = "CRITICAL_FOG"


# Authoritative engineering demonstration policy factors (Section 7)
FOG_POLICY_FACTORS: Dict[str, float] = {
    "CLEAR": 1.00,
    "LIGHT": 0.85,
    "LIGHT_FOG": 0.85,
    "MODERATE": 0.65,
    "MODERATE_FOG": 0.65,
    "HEAVY": 0.40,
    "HEAVY_FOG": 0.40,
    "SEVERE": 0.20,
    "SEVERE_FOG": 0.20,
}


def get_fog_factor(fog_intensity: float, severe_stop: bool = False) -> float:
    """
    Continuous monotonic non-increasing piecewise linear policy mapping
    fog intensity in [0.0, 1.0] to speed reduction factor:
      [0.00, 0.25] -> [1.00, 0.75] (CLEAR to LIGHT_FOG, v_safe = 0.80 -> 0.60 m/s)
      [0.25, 0.50] -> [0.75, 0.50] (LIGHT_FOG to MODERATE_FOG, v_safe = 0.60 -> 0.40 m/s)
      [0.50, 0.75] -> [0.50, 0.30] (MODERATE_FOG to HEAVY_FOG, v_safe = 0.40 -> 0.24 m/s)
      [0.75, 1.00] -> [0.30, 0.10 or 0.00] (HEAVY_FOG to SEVERE_FOG, v_safe = 0.24 -> 0.08 / 0.00 m/s)

    Invariant 3: dfactor / dfog <= 0 everywhere.
    """
    f = max(0.0, min(1.0, float(fog_intensity)))
    if f <= 0.25:
        frac = f / 0.25
        factor = 1.00 - frac * 0.25
    elif f <= 0.50:
        frac = (f - 0.25) / 0.25
        factor = 0.75 - frac * 0.25
    elif f <= 0.75:
        frac = (f - 0.50) / 0.25
        factor = 0.50 - frac * 0.20
    else:
        frac = (f - 0.75) / 0.25
        target = 0.00 if severe_stop else 0.10
        factor = 0.30 - frac * (0.30 - target)

    return max(0.0, min(1.0, round(float(factor), 4)))


def fog_to_visibility_m(fog_intensity: float) -> float:
    """
    Continuous piecewise linear mapping from fog intensity (0.0 to 1.0) to visibility (m):
      0.00 -> 1000.0 m (CLEAR)
      0.25 -> 500.0 m  (LIGHT_FOG)
      0.50 -> 250.0 m  (MODERATE_FOG)
      0.75 -> 100.0 m  (HEAVY_FOG)
      1.00 -> 50.0 m   (SEVERE_FOG)
    """
    f = max(0.0, min(1.0, float(fog_intensity)))
    if f <= 0.25:
        frac = f / 0.25
        return round(1000.0 - frac * 500.0, 1)
    elif f <= 0.50:
        frac = (f - 0.25) / 0.25
        return round(500.0 - frac * 250.0, 1)
    elif f <= 0.75:
        frac = (f - 0.50) / 0.25
        return round(250.0 - frac * 150.0, 1)
    else:
        frac = (f - 0.75) / 0.25
        return round(100.0 - frac * 50.0, 1)


def fog_to_condition(fog_intensity: float) -> str:
    """Classifies numeric fog intensity into standard condition name."""
    f = max(0.0, min(1.0, float(fog_intensity)))
    if f < 0.125:
        return "CLEAR"
    elif f < 0.375:
        return "LIGHT_FOG"
    elif f < 0.625:
        return "MODERATE_FOG"
    elif f < 0.875:
        return "HEAVY_FOG"
    else:
        return "SEVERE_FOG"


def condition_to_fog(condition_str: str) -> float:
    """Maps condition name to canonical midpoint fog intensity."""
    c = condition_str.strip().upper().replace(" ", "_")
    if "CLEAR" in c:
        return 0.00
    elif "LIGHT" in c:
        return 0.25
    elif "MODERATE" in c:
        return 0.50
    elif "HEAVY" in c:
        return 0.75
    elif "CRITICAL" in c or "SEVERE" in c or "EXTREME" in c or "DENSE" in c:
        return 1.00
    raise ValueError(f"Unknown fog condition '{condition_str}'")


def compute_fog_v_safe(
    fog_intensity: float,
    baseline_mps: float = 0.80,
    severe_stop: bool = False,
) -> float:
    """
    Computes safe speed limit for a given baseline maximum speed.
    v_safe = baseline_mps * get_fog_factor(fog_intensity, severe_stop=severe_stop)
    """
    factor = get_fog_factor(fog_intensity, severe_stop=severe_stop)
    return max(0.0, round(float(baseline_mps * factor), 4))


class VehicleCalibration(BaseModel):
    vehicle_id: str
    description: str
    motor_driver: str
    raw_ppr: float
    k_cal: float
    wheel_diameter_m: float
    wheel_circumference_m: float
    distance_per_pulse_m: float
    max_pwm: int
    max_rpm: float
    vmax_mps: float
    vmax_kmh: float
    sample_count: int
    measurement_window: str
    calibration_timestamp: str
    provenance: str
    notes: str


DEFAULT_VEHICLE_CALIBRATIONS: Dict[str, VehicleCalibration] = {
    "TRUCK_01": VehicleCalibration(
        vehicle_id="TRUCK_01",
        description="Vehicle A - 4-wheel differential drive prototype",
        motor_driver="TB6612FNG",
        raw_ppr=42.0,
        k_cal=34.58,
        wheel_diameter_m=0.060,
        wheel_circumference_m=0.18849556,
        distance_per_pulse_m=0.005451,
        max_pwm=220,
        max_rpm=445.6,
        vmax_mps=1.40,
        vmax_kmh=5.04,
        sample_count=184,
        measurement_window="STABILIZED_BENCH_CHASSIS",
        calibration_timestamp="2026-09-27T13:02:00Z",
        provenance="PHYSICAL (derived)",
        notes="Calibrated with TB6612FNG driver, PWM limited to 220. Effective PPR K_cal=34.58.",
    ),
    "TRUCK_02": VehicleCalibration(
        vehicle_id="TRUCK_02",
        description="Vehicle B - 2-wheel drive prototype with TB6612FNG driver",
        motor_driver="TB6612FNG",
        raw_ppr=43.0,
        k_cal=34.58,
        wheel_diameter_m=0.060,
        wheel_circumference_m=0.18849556,
        distance_per_pulse_m=0.005451,
        max_pwm=240,
        max_rpm=413.8,
        vmax_mps=1.30,
        vmax_kmh=4.68,
        sample_count=178,
        measurement_window="STABILIZED_BENCH_CHASSIS",
        calibration_timestamp="2026-09-27T13:11:00Z",
        provenance="PHYSICAL (derived)",
        notes="Calibrated with TB6612FNG driver, safe PWM limited to 240. 43 physical slots distinct from Vehicle A.",
    ),
}


def load_calibrations() -> Dict[str, VehicleCalibration]:
    """Loads vehicle calibrations from persistent artifact or returns canonical baseline."""
    candidates = [
        os.path.join(os.getcwd(), "config", "vehicle_speed_calibration.json"),
        os.path.join(os.getcwd(), "vehicle_speed_calibration.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "vehicle_speed_calibration.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    vehicles = data.get("vehicles", {})
                    loaded = {}
                    for vid, vdata in vehicles.items():
                        loaded[vid] = VehicleCalibration(**vdata)
                    if loaded:
                        return loaded
            except Exception:
                pass
    return dict(DEFAULT_VEHICLE_CALIBRATIONS)


class EnvironmentalState(BaseModel):
    fog_intensity: float = Field(..., ge=0.0, le=1.0, description="Fog intensity 0.0 to 1.0")
    visibility_m: float = Field(..., description="Derived visibility in metres")
    weather_condition: str = Field(..., description="Condition category (CLEAR, LIGHT, MODERATE, HEAVY, SEVERE, CRITICAL)")
    fog_factor: float = Field(..., description="Active speed scaling factor (1.00 to 0.00)")
    source: str = Field("WEATHER_STATION_INJECTED", description="Environmental data provenance")
    timestamp: float = Field(..., description="Epoch seconds of observation/injection")
    confidence: float = Field(1.0, description="Measurement/injection confidence factor")
    is_injected: bool = Field(True, description="Strict provenance flag: True for weather-station injection")
    active_policy: str = Field("FOG_VISIBILITY_CONSTRAINT", description="Governing safety policy")
    v_safe_baseline_mps: float = Field(1.40, description="Reference baseline speed ceiling in m/s")
    v_safe_mps: float = Field(..., description="Active safe speed ceiling in m/s")
    constraint_reason: str = Field("FOG_VISIBILITY_CONSTRAINT", description="Reason for active constraint")


class VehicleGovernorReport(BaseModel):
    vehicle_id: str
    vmax_mps: float
    vmax_kmh: float
    vmax_provenance: str
    fog_factor: float
    v_safe_mps: float
    requested_speed_mps: float
    applied_speed_mps: float
    clamp_active: bool
    governor_state: str
    governor_reason: str
    motor_driver: str


class FogInjectionRequest(BaseModel):
    fog_intensity: Optional[float] = Field(None, description="Fog intensity between 0.0 and 1.0")
    condition: Optional[str] = Field(None, description="Pre-set condition name (e.g. CLEAR, LIGHT, MODERATE, HEAVY, SEVERE, CRITICAL)")
    source: Optional[str] = Field("WEATHER_STATION_INJECTED", description="Source declaration")
    severe_stop_policy: Optional[bool] = Field(False, description="Whether severe/critical fog forces v_safe = 0.0 (STOP)")


class CausalAuditEvent(BaseModel):
    event_id: str
    timestamp: float
    category: str  # WEATHER_EVENT, SAFETY_EVENT, GOVERNOR_EVENT
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WeatherStationService:
    """
    Authoritative state holder and normalizer for weather station environmental input
    and vehicle-specific speed governor.
    Ensures ONE single authoritative environmental & governor truth exists.
    """

    def __init__(self, baseline_speed_mps: float = 0.80):
        self.baseline_speed_mps = baseline_speed_mps
        self.calibrations = load_calibrations()
        now = time.time()
        self.current_state = EnvironmentalState(
            fog_intensity=0.0,
            visibility_m=1000.0,
            weather_condition="CLEAR",
            fog_factor=1.00,
            source="WEATHER_STATION_INJECTED",
            timestamp=now,
            confidence=1.0,
            is_injected=True,
            active_policy="FOG_VISIBILITY_CONSTRAINT",
            v_safe_baseline_mps=baseline_speed_mps,
            v_safe_mps=baseline_speed_mps,
            constraint_reason="FOG_VISIBILITY_CONSTRAINT",
        )
        self.audit_log: List[CausalAuditEvent] = []
        self._event_counter = 0

    def _next_event_id(self, prefix: str) -> str:
        self._event_counter += 1
        return f"{prefix}_{int(time.time())}_{self._event_counter}"

    def get_current_environment(self) -> EnvironmentalState:
        """Returns the current authoritative EnvironmentalState."""
        return self.current_state

    def get_vehicle_vmax(self, vehicle_id: str) -> float:
        """Returns measured Vmax for vehicle or defaults cleanly without fabrication."""
        cal = self.calibrations.get(vehicle_id)
        if cal and cal.vmax_mps is not None and cal.vmax_mps > 0:
            return cal.vmax_mps
        return self.baseline_speed_mps

    def compute_vehicle_governor(
        self,
        vehicle_id: str,
        requested_speed_mps: float = 0.80,
        fog_factor: Optional[float] = None,
        severe_stop: bool = False,
    ) -> VehicleGovernorReport:
        """
        Calculates authoritative vehicle-specific safe speed and applies command clamp:
            Vmax_i = measured maximum speed
            v_safe_i = min(Vmax_i, baseline_ceiling) * fog_factor
            v_command_i = 0.0 if (critical or severe_stop) else min(requested_speed_mps, v_safe_i)
        """
        cal = self.calibrations.get(vehicle_id, DEFAULT_VEHICLE_CALIBRATIONS.get(vehicle_id))
        vmax = cal.vmax_mps if cal else self.baseline_speed_mps
        vmax_kmh = cal.vmax_kmh if cal else (vmax * 3.6)
        provenance = cal.provenance if cal else "NOT_CALIBRATED"
        driver = cal.motor_driver if cal else "UNKNOWN"

        factor = self.current_state.fog_factor if fog_factor is None else fog_factor

        eff_ceiling = min(vmax, self.baseline_speed_mps)

        if factor == 0.0 or (severe_stop and factor <= 0.10):
            v_safe = 0.0
            applied = 0.0
            clamp_active = requested_speed_mps > 0.0
            gov_state = "ACTIVE — SEVERE FOG STOP"
            gov_reason = f"SEVERE_FOG_EMERGENCY_STOP (Vmax={vmax:.2f} m/s, factor=0.0)"
        else:
            v_safe = round(float(eff_ceiling * factor), 4)
            clamp_active = requested_speed_mps > v_safe + 1e-6
            applied = v_safe if clamp_active else requested_speed_mps
            gov_state = "ACTIVE — FOG CONSTRAINT" if (clamp_active or factor < 1.0) else "NORMAL"
            gov_reason = f"FOG_VISIBILITY_CONSTRAINT (factor={factor:.2f}, Vmax={vmax:.2f} m/s, limit={eff_ceiling:.2f} m/s)"

        return VehicleGovernorReport(
            vehicle_id=vehicle_id,
            vmax_mps=vmax,
            vmax_kmh=vmax_kmh,
            vmax_provenance=provenance,
            fog_factor=factor,
            v_safe_mps=v_safe,
            requested_speed_mps=requested_speed_mps,
            applied_speed_mps=applied,
            clamp_active=clamp_active,
            governor_state=gov_state,
            governor_reason=gov_reason,
            motor_driver=driver,
        )

    def update_fog(
        self,
        fog_intensity: Optional[float] = None,
        condition: Optional[str] = None,
        source: str = "WEATHER_STATION_INJECTED",
        severe_stop_policy: bool = False,
        now: Optional[float] = None,
    ) -> tuple[EnvironmentalState, List[CausalAuditEvent]]:
        """
        Validates, normalizes, and applies environmental state transition.
        Generates auditable causal events: WEATHER_EVENT and SAFETY_EVENT.
        """
        ts = now if now is not None else time.time()

        # Validate input
        if fog_intensity is not None:
            if isinstance(fog_intensity, bool) or not isinstance(fog_intensity, (int, float)):
                raise ValueError("fog_intensity must be a finite number between 0.0 and 1.0")
            if not math.isfinite(fog_intensity):
                raise ValueError("fog_intensity must be finite")
            if fog_intensity < 0.0 or fog_intensity > 1.0:
                raise ValueError(f"fog_intensity {fog_intensity} out of valid range [0.0, 1.0]")
            target_fog = float(fog_intensity)
            target_cond = fog_to_condition(target_fog) if condition is None else condition.upper()
        elif condition is not None:
            target_fog = condition_to_fog(condition)
            target_cond = condition.upper()
        else:
            raise ValueError("Either fog_intensity or condition must be specified")

        old_fog = self.current_state.fog_intensity
        old_cond = self.current_state.weather_condition
        old_v_safe = self.current_state.v_safe_mps

        vis_m = fog_to_visibility_m(target_fog)
        factor = get_fog_factor(target_fog, severe_stop=severe_stop_policy)
        new_v_safe = round(float(self.baseline_speed_mps * factor), 4)

        self.current_state = EnvironmentalState(
            fog_intensity=target_fog,
            visibility_m=vis_m,
            weather_condition=target_cond,
            fog_factor=factor,
            source=source,
            timestamp=ts,
            confidence=1.0,
            is_injected=True,
            active_policy="FOG_VISIBILITY_CONSTRAINT",
            v_safe_baseline_mps=self.baseline_speed_mps,
            v_safe_mps=new_v_safe,
            constraint_reason="FOG_VISIBILITY_CONSTRAINT",
        )

        events: List[CausalAuditEvent] = []

        # 1. ENVIRONMENT_EVENT / WEATHER_EVENT (Requirement 30: Command Audit Logging)
        env_meta = {
            "operator_or_cli_source": source,
            "source": source,
            "old_condition": old_cond,
            "new_condition": target_cond,
            "old_intensity": old_fog,
            "new_intensity": target_fog,
            "previous_fog_intensity": old_fog,
            "new_fog_intensity": target_fog,
            "condition": target_cond,
            "visibility_m": vis_m,
            "fog_factor": factor,
            "provenance": "INJECTED",
            "is_injected": True,
        }
        w_event = CausalAuditEvent(
            event_id=self._next_event_id("WTHR"),
            timestamp=ts,
            category="WEATHER_EVENT",
            description=f"Fog intensity transition: {int(old_fog * 100)}% → {int(target_fog * 100)}% ({target_cond}), visibility {vis_m:.0f}m, speed factor {int(factor * 100)}%",
            metadata=env_meta,
        )
        events.append(w_event)
        self.audit_log.append(w_event)

        e_event = CausalAuditEvent(
            event_id=self._next_event_id("ENV"),
            timestamp=ts,
            category="ENVIRONMENT_EVENT",
            description=f"{old_cond} → {target_cond} | intensity {old_fog:.2f} → {target_fog:.2f} | visibility {vis_m:.0f}m | fog_factor {factor:.2f} | source: {source} | provenance: INJECTED",
            metadata=env_meta,
        )
        events.append(e_event)
        self.audit_log.append(e_event)

        # 2. SAFETY_EVENT
        s_event = CausalAuditEvent(
            event_id=self._next_event_id("SAFE"),
            timestamp=ts,
            category="SAFETY_EVENT",
            description=f"Safety solver recalculated fleet safe speed ceilings (factor {int(factor * 100)}%): TRUCK_01={1.40 * factor:.2f} m/s, TRUCK_02={1.30 * factor:.2f} m/s [FOG_VISIBILITY_CONSTRAINT]",
            metadata={
                "previous_v_safe_mps": old_v_safe,
                "new_v_safe_mps": new_v_safe,
                "visibility_m": vis_m,
                "fog_factor": factor,
                "active_constraint": "FOG_VISIBILITY_CONSTRAINT",
            },
        )
        events.append(s_event)
        self.audit_log.append(s_event)

        return self.current_state, events

    def record_governor_event(
        self,
        vehicle_id: str,
        requested_speed_mps: float,
        safe_limit_mps: float,
        applied_speed_mps: float,
        governor_state: str,
        vmax_mps: Optional[float] = None,
        now: Optional[float] = None,
    ) -> CausalAuditEvent:
        """Records governor speed clamping decision for a specific vehicle."""
        ts = now if now is not None else time.time()
        is_clamped = requested_speed_mps > safe_limit_mps + 1e-6
        vmax_str = f" (Vmax={vmax_mps:.2f} m/s)" if vmax_mps is not None else ""
        if safe_limit_mps == 0.0:
            desc = f"{vehicle_id} Governor CRITICAL STOP: commanded speed set to 0.0 m/s{vmax_str}"
        elif is_clamped:
            desc = f"{vehicle_id} Governor CLAMPED target {requested_speed_mps:.2f} m/s to safe limit {applied_speed_mps:.2f} m/s{vmax_str} [FOG_VISIBILITY_CONSTRAINT]"
        else:
            desc = f"{vehicle_id} Governor approved target {applied_speed_mps:.2f} m/s (below safe limit {safe_limit_mps:.2f} m/s){vmax_str}"

        g_event = CausalAuditEvent(
            event_id=self._next_event_id("GOV"),
            timestamp=ts,
            category="GOVERNOR_EVENT",
            description=desc,
            metadata={
                "vehicle_id": vehicle_id,
                "requested_speed_mps": requested_speed_mps,
                "safe_limit_mps": safe_limit_mps,
                "applied_speed_mps": applied_speed_mps,
                "governor_state": governor_state,
                "is_clamped": is_clamped,
                "vmax_mps": vmax_mps,
            },
        )
        self.audit_log.append(g_event)
        return g_event
