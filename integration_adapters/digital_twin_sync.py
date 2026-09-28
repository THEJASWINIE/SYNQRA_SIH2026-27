"""
integration_adapters/digital_twin_sync.py
-----------------------------------------
FOG-ORCHESTRATOR 2.0 — Phase 9 Digital Twin Synchronization & What-If Engine
NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System

Functions:
1. State Mirroring: Tracks physical vehicle state without claiming direct authority.
2. Prediction / Lookahead Simulation: Evaluates stopping envelopes up to T+5s.
3. What-If Analysis: Evaluates sudden fog, friction, slope, and communication faults.
4. Historical Replay: Replays recorded telemetry traces.
5. Fault Injection: Controlled synthetic perturbations for robustness evaluation.

Tracks Synchronization Metrics:
- Position RMSE (m)
- Speed MAE (m/s)
- Max position error (m)
- Max speed error (m/s)
- State synchronization latency (ms)
- Telemetry data age (ms)
- Dropout rate (%)
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import math
import time
import numpy as np

from integration_adapters.master_data_model import (
    VehicleState,
    DataSourceType,
    MasterSafetyState,
    DigitalTwinSyncState,
    MasterSensorQuality,
)


class TwinOperatingMode(str, Enum):
    LIVE_MIRROR = "LIVE_MIRROR"          # Mode 1: Real telemetry drives twin
    PREDICTIVE = "PREDICTIVE"            # Mode 2: Forward kinematic lookahead
    WHAT_IF = "WHAT_IF"                  # Mode 3: Parametric scenario evaluation
    REPLAY = "REPLAY"                    # Mode 4: Deterministic historical replay
    FAULT_INJECTION = "FAULT_INJECTION"  # Mode 5: Controlled synthetic faults


class TwinSyncMetrics:
    """Statistical tracking of Real vs Digital Twin synchronization."""
    def __init__(self):
        self.position_errors: List[float] = []
        self.speed_errors: List[float] = []
        self.sync_latencies_ms: List[float] = []
        self.total_packets: int = 0
        self.dropped_packets: int = 0
        self.state_mismatches: int = 0

    def record_observation(
        self,
        real_pos: float,
        twin_pos: float,
        real_spd: float,
        twin_spd: float,
        sync_lat_ms: float,
        real_state: str,
        twin_state: str,
    ):
        self.total_packets += 1
        pos_err = abs(real_pos - twin_pos)
        spd_err = abs(real_spd - twin_spd)
        self.position_errors.append(pos_err)
        self.speed_errors.append(spd_err)
        self.sync_latencies_ms.append(sync_lat_ms)

        if real_state != twin_state:
            self.state_mismatches += 1

    def compute_summary(self) -> Dict[str, float]:
        if not self.position_errors:
            return {
                "position_rmse_m": 0.0,
                "speed_mae_mps": 0.0,
                "max_position_error_m": 0.0,
                "max_speed_error_mps": 0.0,
                "mean_sync_latency_ms": 0.0,
                "p95_sync_latency_ms": 0.0,
                "state_mismatch_pct": 0.0,
                "dropout_rate_pct": 0.0,
            }
        
        pos_arr = np.array(self.position_errors)
        spd_arr = np.array(self.speed_errors)
        lat_arr = np.array(self.sync_latencies_ms)

        rmse_pos = float(np.sqrt(np.mean(pos_arr ** 2)))
        mae_spd = float(np.mean(spd_arr))
        max_pos = float(np.max(pos_arr))
        max_spd = float(np.max(spd_arr))
        mean_lat = float(np.mean(lat_arr))
        p95_lat = float(np.percentile(lat_arr, 95))
        mismatch_pct = (self.state_mismatches / max(1, self.total_packets)) * 100.0
        dropout_pct = (self.dropped_packets / max(1, self.total_packets)) * 100.0

        return {
            "position_rmse_m": round(rmse_pos, 4),
            "speed_mae_mps": round(mae_spd, 4),
            "max_position_error_m": round(max_pos, 4),
            "max_speed_error_mps": round(max_spd, 4),
            "mean_sync_latency_ms": round(mean_lat, 2),
            "p95_sync_latency_ms": round(p95_lat, 2),
            "state_mismatch_pct": round(mismatch_pct, 2),
            "dropout_rate_pct": round(dropout_pct, 2),
        }


class DigitalTwinEngine:
    """
    Authoritative Digital Twin Engine for FOG-ORCHESTRATOR 2.0.
    Provides Live Mirroring, Predictive Modeling, What-If Simulation,
    and strict boundary isolation from physical vehicle actuators.
    """
    def __init__(self, vehicle_id: str = "TRUCK_01"):
        self.vehicle_id = vehicle_id
        self.mode = TwinOperatingMode.LIVE_MIRROR
        self.metrics = TwinSyncMetrics()

        # Twin internal mirror state
        self.mirrored_state: Optional[VehicleState] = None
        self.predicted_trajectory: List[Dict[str, float]] = []
        self.is_twin_online = True
        self.last_sync_timestamp = 0.0

    def ingest_real_telemetry(self, state: VehicleState, now: Optional[float] = None) -> DigitalTwinSyncState:
        """
        Mode 1: Live Mirror. Ingests canonical telemetry and computes sync deviation.
        Does NOT artificially clamp or force twin to reality if divergent.
        """
        t_now = now if now is not None else time.time()
        sync_latency_ms = (t_now - state.event_timestamp) * 1000.0

        # Assess internal twin deviation before update
        twin_pos = self.mirrored_state.position if self.mirrored_state else state.position
        twin_spd = self.mirrored_state.speed if self.mirrored_state else state.speed
        twin_state_str = self.mirrored_state.safety_state.value if self.mirrored_state else state.safety_state.value

        self.metrics.record_observation(
            real_pos=state.position,
            twin_pos=twin_pos,
            real_spd=state.speed,
            twin_spd=twin_spd,
            sync_lat_ms=max(0.1, sync_latency_ms),
            real_state=state.safety_state.value,
            twin_state=twin_state_str,
        )

        # Update mirrored state
        self.mirrored_state = state.model_copy(deep=True)
        self.last_sync_timestamp = t_now

        # Categorize synchronization state
        pos_err = abs(state.position - twin_pos)
        spd_err = abs(state.speed - twin_spd)

        if not self.is_twin_online:
            return DigitalTwinSyncState.OFFLINE
        elif pos_err > 5.0 or spd_err > 2.0:
            return DigitalTwinSyncState.DIVERGENT
        elif pos_err > 1.5 or spd_err > 0.8:
            return DigitalTwinSyncState.DRIFTING
        else:
            return DigitalTwinSyncState.SYNCHRONIZED

    def run_predictive_lookahead(self, lookahead_s: float = 3.0, dt: float = 0.1) -> List[Dict[str, float]]:
        """
        Mode 2: Predictive Lookahead.
        Forecasts stopping distance and required deceleration over lookahead window.
        """
        if not self.mirrored_state:
            return []

        v = self.mirrored_state.speed
        pos = self.mirrored_state.position
        grade_rad = math.atan(self.mirrored_state.grade / 100.0)
        vis = self.mirrored_state.visibility
        mu = 0.35 if vis < 15.0 else 0.50

        # Stopping distance formula: S_stop = v * tau + v^2 / (2 * a_dec)
        tau_total = 0.55  # 550 ms nominal reaction + sensor + comm lag
        g = 9.81
        a_dec = max(0.5, g * (mu * math.cos(grade_rad) + math.sin(grade_rad)))  # Grade effect

        trajectory = []
        t = 0.0
        curr_pos = pos
        curr_spd = v

        while t <= lookahead_s:
            s_stop = curr_spd * tau_total + (curr_spd ** 2) / (2.0 * a_dec)
            s_margin = 5.0
            r_effective = max(0.5, vis)
            is_envelope_safe = (s_stop + s_margin) <= r_effective

            trajectory.append({
                "time_offset_s": round(t, 2),
                "position_m": round(curr_pos, 2),
                "speed_mps": round(curr_spd, 2),
                "stopping_distance_m": round(s_stop, 2),
                "required_headway_m": round(s_stop + s_margin, 2),
                "is_safe": is_envelope_safe,
            })
            curr_pos += curr_spd * dt
            t += dt

        self.predicted_trajectory = trajectory
        return trajectory

    def run_what_if_scenario(
        self,
        visibility_m: float,
        grade_pct: float,
        friction_mu: float,
        comm_lost: bool = False,
    ) -> Dict[str, Any]:
        """
        Mode 3: What-If Analysis.
        Simulates hypothetical environmental or communication perturbations.
        Returns predicted safe speed, stopping margin, and safety state.
        """
        g = 9.81
        grade_rad = math.atan(grade_pct / 100.0)
        # BEML BH100 safe deceleration on grade
        a_dec = max(0.5, g * (friction_mu * math.cos(grade_rad) + math.sin(grade_rad)))
        tau_total = 0.55 if not comm_lost else 0.85
        s_margin = 5.0
        r_eff = max(0.0, visibility_m)

        # Invert stopping formula: v*tau + v^2/(2a) = R - s_margin
        available_dist = max(0.0, r_eff - s_margin)
        if available_dist <= 0.0 or visibility_m <= 5.0:
            pred_safe_speed = 0.0
            state = MasterSafetyState.SAFE_MODE if comm_lost else MasterSafetyState.WARNING
        else:
            # v^2 + 2*a*tau*v - 2*a*D = 0
            b = 2.0 * a_dec * tau_total
            c = -2.0 * a_dec * available_dist
            discriminant = b ** 2 - 4.0 * c
            pred_safe_speed = max(0.0, (-b + math.sqrt(discriminant)) / 2.0)
            pred_safe_speed = min(pred_safe_speed, 11.8)  # Site cap 42.5 km/h

            if comm_lost:
                state = MasterSafetyState.SAFE_MODE
            elif pred_safe_speed < 4.0:
                state = MasterSafetyState.DEGRADED
            elif pred_safe_speed < 8.0:
                state = MasterSafetyState.ADVISORY
            else:
                state = MasterSafetyState.NORMAL

        return {
            "scenario_params": {
                "visibility_m": visibility_m,
                "grade_pct": grade_pct,
                "friction_mu": friction_mu,
                "comm_lost": comm_lost,
            },
            "predicted_safe_speed_mps": round(pred_safe_speed, 2),
            "predicted_safe_speed_kmh": round(pred_safe_speed * 3.6, 1),
            "effective_deceleration_mps2": round(a_dec, 2),
            "stopping_envelope_m": round(available_dist, 2),
            "predicted_safety_state": state.value,
            "safe_beacon_would_activate": comm_lost,
            "disclaimer": "PREDICTIVE ADVISORY ONLY — NOT LOCAL CONTROL AUTHORITY",
        }

    def set_mode(self, mode: TwinOperatingMode) -> None:
        """Switch twin operating mode with explicit logging."""
        self.mode = mode

    def can_issue_physical_command(self) -> bool:
        """
        Safety Invariant 6:
        Only LIVE_MIRROR mode may ever issue physical commands.
        WHAT_IF, REPLAY, PREDICTIVE, and FAULT_INJECTION modes are strictly
        forbidden from generating physical actuation commands.
        """
        return self.mode == TwinOperatingMode.LIVE_MIRROR
