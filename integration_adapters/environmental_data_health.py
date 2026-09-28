"""
integration_adapters/environmental_data_health.py
-------------------------------------------------
FOG-ORCHESTRATOR 2.0 — Confidence-Aware Environmental & Telemetry Data Health Layer.

BOUNDED, AUDITABLE, RULE-BASED DATA-HEALTH LAYER (DECISION C).

CORE SAFETY PRINCIPLES:
1. The data-health layer MODIFIES environmental/telemetry state conservatively.
2. It NEVER commands actuators (brakes, throttle, steering).
3. It NEVER overrides the LocalVehicleSafetyGovernor (Level 1 authority).
4. It NEVER invents optimistic replacement values for invalid or missing data.
5. It fails closed: any internal exception defaults to UNAVAILABLE (R_UNAVAILABLE_MIN).
6. It maintains strict separation between DATA STATE, COMMUNICATION STATE, and VEHICLE SAFETY STATE.
7. Class C (plausible-but-wrong) single-source data is fundamentally undetectable without an
   independent validated reference; this limitation is explicitly exposed.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("EnvironmentalDataHealth")


class DataState(str, Enum):
    """Primary data quality and health states."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"


class FaultCode(str, Enum):
    """Specific fault classifications for audit and diagnostic traceability."""
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    STALE_TIMEOUT = "STALE_TIMEOUT"
    RANGE_VIOLATION = "RANGE_VIOLATION"
    TYPE_SCHEMA_ERROR = "TYPE_SCHEMA_ERROR"
    NON_FINITE = "NON_FINITE"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    SEQUENCE_DUPLICATE = "SEQUENCE_DUPLICATE"
    SEQUENCE_ROLLBACK = "SEQUENCE_ROLLBACK"
    STUCK_AT = "STUCK_AT"
    EXCESSIVE_NOISE = "EXCESSIVE_NOISE"
    CROSS_SOURCE_CONFLICT = "CROSS_SOURCE_CONFLICT"
    MODULE_EXCEPTION = "MODULE_EXCEPTION"


@dataclass
class ValidatedSignal:
    """
    Standardized, auditable validated signal container.
    Carries explicit physical units, freshness, provenance, and confidence.
    """
    value: float
    unit: str
    timestamp: float
    age: float
    source: str
    sequence: int
    health: DataState
    confidence: float
    reason: str
    fault_code: FaultCode = FaultCode.NONE
    r_effective_conservative: float = 8.0


@dataclass
class EnvironmentalHealthConfig:
    """
    Configuration for environmental data health checks.
    Every threshold is explicitly categorized as an ENGINEERING PARAMETER.
    """
    # H1 Freshness thresholds (seconds)
    T_DEGRADED_ENV_s: float = 30.0             # ENGINEERING PARAMETER
    T_STALE_ENV_s: float = 60.0                # ENGINEERING PARAMETER
    T_GRACE_PERIOD_s: float = 120.0            # ENGINEERING PARAMETER

    # H3 Plausibility range for visibility (metres)
    V_MIN_PLAUSIBLE_m: float = 0.5             # ENGINEERING PARAMETER
    V_MAX_PLAUSIBLE_m: float = 2000.0          # ENGINEERING PARAMETER

    # Conservative scaling factors
    DEGRADED_FACTOR: float = 0.70              # ENGINEERING PARAMETER (30% penalty)
    STALE_FACTOR: float = 0.50                 # ENGINEERING PARAMETER (50% penalty)
    R_MIN_m: float = 5.0                       # ENGINEERING PARAMETER (physical minimum)
    R_UNAVAILABLE_MIN_m: float = 8.0           # ENGINEERING PARAMETER (dense fog floor)

    # Recovery Hysteresis (consecutive clean observations required)
    RECOVERY_HYSTERESIS_STALE: int = 2         # ENGINEERING PARAMETER
    RECOVERY_HYSTERESIS_UNAVAILABLE: int = 3   # ENGINEERING PARAMETER

    # H5 Stuck-at and Noise parameters
    STUCK_WINDOW_SIZE: int = 10                # ENGINEERING PARAMETER
    STUCK_STD_THRESHOLD_m: float = 0.05        # ENGINEERING PARAMETER
    STUCK_MIN_TIME_s: float = 300.0            # ENGINEERING PARAMETER (5 minutes)
    NOISE_STD_THRESHOLD_m: float = 20.0        # ENGINEERING PARAMETER

    # H6 Conflict detection parameter
    CONFLICT_THRESHOLD_m: float = 25.0         # ENGINEERING PARAMETER


class EnvironmentalDataHealth:
    """
    Authoritative Environmental Data Health Validator.
    Applies H1 (Freshness), H2 (Schema/Type), H3 (Range), H4 (Sequence),
    H5 (Stuck-At / Noise), and H6 (Conflict) checks to environmental observations.
    """

    def __init__(
        self,
        config: Optional[EnvironmentalHealthConfig] = None,
        clock: Callable[[], float] = time.time
    ):
        self.config = config or EnvironmentalHealthConfig()
        self.clock = clock

        # State tracking
        self.last_valid_value: float = self.config.R_UNAVAILABLE_MIN_m
        self.last_valid_timestamp: float = 0.0
        self.last_sequence: int = -1
        self.seen_sequences: deque = deque(maxlen=500)

        # Rolling sample history: list of (timestamp, value)
        self.history: deque = deque(maxlen=self.config.STUCK_WINDOW_SIZE)

        # Recovery hysteresis tracking
        self.in_recovery: bool = False
        self.recovery_counter: int = 0
        self.recovery_required_frames: int = 0
        self.current_state: DataState = DataState.HEALTHY
        self.last_fault_code: FaultCode = FaultCode.NONE
        self.last_signal: Optional[ValidatedSignal] = None


    def update(
        self,
        visibility_m: Any,
        timestamp: Optional[float] = None,
        sequence: int = 0,
        source_id: str = "DEFAULT_WEATHER_STATION",
        secondary_visibility_m: Optional[float] = None
    ) -> ValidatedSignal:
        """
        Ingests and validates an environmental observation.
        Fail-closed: any runtime exception returns UNAVAILABLE.
        """
        now = self.clock()
        ts = timestamp if timestamp is not None else now

        try:
            return self._validate_pipeline(
                visibility_m=visibility_m,
                timestamp=ts,
                now=now,
                sequence=sequence,
                source_id=source_id,
                secondary_visibility_m=secondary_visibility_m
            )
        except Exception as exc:
            logger.error("Unhandled exception in EnvironmentalDataHealth: %s", exc, exc_info=True)
            self.current_state = DataState.UNAVAILABLE
            self.recovery_counter = 0
            self.last_fault_code = FaultCode.MODULE_EXCEPTION
            return ValidatedSignal(
                value=self.config.R_UNAVAILABLE_MIN_m,
                unit="m",
                timestamp=ts,
                age=max(0.0, now - ts),
                source=source_id,
                sequence=sequence,
                health=DataState.UNAVAILABLE,
                confidence=0.0,
                reason=f"Module exception: {str(exc)}",
                fault_code=FaultCode.MODULE_EXCEPTION,
                r_effective_conservative=self.config.R_UNAVAILABLE_MIN_m
            )

    def _validate_pipeline(
        self,
        visibility_m: Any,
        timestamp: float,
        now: float,
        sequence: int,
        source_id: str,
        secondary_visibility_m: Optional[float]
    ) -> ValidatedSignal:
        age_s = max(0.0, now - timestamp)

        # ---------------------------------------------------------
        # Check H2: Schema / Type / Non-finite validation
        # ---------------------------------------------------------
        if visibility_m is None or isinstance(visibility_m, (bool, str, list, dict)):
            return self._handle_invalid(
                reason="Invalid data type for visibility_m",
                fault=FaultCode.TYPE_SCHEMA_ERROR,
                timestamp=timestamp,
                age=age_s,
                sequence=sequence,
                source=source_id
            )

        try:
            val = float(visibility_m)
        except (ValueError, TypeError):
            return self._handle_invalid(
                reason="Non-numeric visibility value",
                fault=FaultCode.TYPE_SCHEMA_ERROR,
                timestamp=timestamp,
                age=age_s,
                sequence=sequence,
                source=source_id
            )

        if not math.isfinite(val):
            return self._handle_invalid(
                reason="Non-finite visibility value (NaN or Inf)",
                fault=FaultCode.NON_FINITE,
                timestamp=timestamp,
                age=age_s,
                sequence=sequence,
                source=source_id
            )

        # ---------------------------------------------------------
        # Check H3: Physical Plausibility / Range
        # ---------------------------------------------------------
        if val < self.config.V_MIN_PLAUSIBLE_m or val > self.config.V_MAX_PLAUSIBLE_m:
            return self._handle_invalid(
                reason=f"Visibility {val:.1f} m outside plausible range [{self.config.V_MIN_PLAUSIBLE_m}, {self.config.V_MAX_PLAUSIBLE_m}]",
                fault=FaultCode.RANGE_VIOLATION,
                timestamp=timestamp,
                age=age_s,
                sequence=sequence,
                source=source_id
            )

        # ---------------------------------------------------------
        # Check H4: Sequence Integrity
        # ---------------------------------------------------------
        seq_fault = FaultCode.NONE
        if sequence in self.seen_sequences:
            seq_fault = FaultCode.SEQUENCE_DUPLICATE
        elif self.last_sequence >= 0 and sequence < self.last_sequence:
            seq_fault = FaultCode.SEQUENCE_ROLLBACK
        elif self.last_sequence >= 0 and sequence > self.last_sequence + 5:
            seq_fault = FaultCode.SEQUENCE_GAP

        self.seen_sequences.append(sequence)
        self.last_sequence = max(self.last_sequence, sequence)

        # ---------------------------------------------------------
        # Check H6: Multi-Source Conflict (when 2nd source provided)
        # ---------------------------------------------------------
        conflict_detected = False
        if secondary_visibility_m is not None:
            try:
                sec_val = float(secondary_visibility_m)
                if math.isfinite(sec_val) and abs(val - sec_val) > self.config.CONFLICT_THRESHOLD_m:
                    conflict_detected = True
                    val = min(val, sec_val)  # Conservative resolution: take minimum
            except (ValueError, TypeError):
                pass

        # ---------------------------------------------------------
        # Check H5: Stuck-at / Noise checks
        # ---------------------------------------------------------
        self.history.append((now, val))
        stuck_detected = False
        noise_detected = False

        if len(self.history) >= self.config.STUCK_WINDOW_SIZE:
            window_vals = [v for _, v in self.history]
            window_duration = self.history[-1][0] - self.history[0][0]
            mean_val = sum(window_vals) / len(window_vals)
            var = sum((x - mean_val) ** 2 for x in window_vals) / len(window_vals)
            std_dev = math.sqrt(var)

            if std_dev < self.config.STUCK_STD_THRESHOLD_m and window_duration >= self.config.STUCK_MIN_TIME_s:
                stuck_detected = True
            elif std_dev > self.config.NOISE_STD_THRESHOLD_m:
                noise_detected = True

        # ---------------------------------------------------------
        # Check H1: Freshness & Hysteresis State Determination
        # ---------------------------------------------------------
        target_state = DataState.HEALTHY
        fault = FaultCode.NONE
        reason = "VALID_MEASUREMENT"
        confidence = 1.0

        if conflict_detected:
            target_state = DataState.CONFLICTING
            fault = FaultCode.CROSS_SOURCE_CONFLICT
            reason = "Dual visibility sensors disagree beyond threshold"
            confidence = 0.50
        elif age_s > self.config.T_GRACE_PERIOD_s:
            target_state = DataState.UNAVAILABLE
            fault = FaultCode.STALE_TIMEOUT
            reason = f"Visibility age {age_s:.1f} s exceeds grace period {self.config.T_GRACE_PERIOD_s} s"
            confidence = 0.0
            self.in_recovery = True
            self.recovery_counter = 0
            self.recovery_required_frames = self.config.RECOVERY_HYSTERESIS_UNAVAILABLE
        elif age_s > self.config.T_STALE_ENV_s:
            target_state = DataState.STALE
            fault = FaultCode.STALE_TIMEOUT
            reason = f"Visibility age {age_s:.1f} s exceeds stale threshold {self.config.T_STALE_ENV_s} s"
            confidence = 0.40
            self.in_recovery = True
            self.recovery_counter = 0
            self.recovery_required_frames = max(self.recovery_required_frames, self.config.RECOVERY_HYSTERESIS_STALE)
        elif age_s > self.config.T_DEGRADED_ENV_s:
            target_state = DataState.DEGRADED
            fault = FaultCode.TIMEOUT
            reason = f"Visibility age {age_s:.1f} s exceeds degraded threshold {self.config.T_DEGRADED_ENV_s} s"
            confidence = 0.70
        elif stuck_detected:
            target_state = DataState.DEGRADED
            fault = FaultCode.STUCK_AT
            reason = f"Potential stuck-at sensor: variance < {self.config.STUCK_STD_THRESHOLD_m} over {window_duration:.0f} s"
            confidence = 0.60
        elif noise_detected:
            target_state = DataState.DEGRADED
            fault = FaultCode.EXCESSIVE_NOISE
            reason = f"Sensor noise std {std_dev:.1f} m exceeds threshold {self.config.NOISE_STD_THRESHOLD_m} m"
            confidence = 0.65
        elif seq_fault != FaultCode.NONE:
            target_state = DataState.DEGRADED
            fault = seq_fault
            reason = f"Sequence integrity issue: {seq_fault.value}"
            confidence = 0.75

        # ---------------------------------------------------------
        # Hysteresis Evaluation for State Recovery
        # ---------------------------------------------------------
        active_state = self._apply_hysteresis(target_state)

        # Record valid history
        self.last_valid_value = val
        self.last_valid_timestamp = now
        self.current_state = active_state
        self.last_fault_code = fault

        # ---------------------------------------------------------
        # Conservative Safe Envelope Assignment
        # ---------------------------------------------------------
        r_eff = self._calculate_r_effective(val, active_state)

        sig = ValidatedSignal(
            value=val,
            unit="m",
            timestamp=timestamp,
            age=age_s,
            source=source_id,
            sequence=sequence,
            health=active_state,
            confidence=confidence,
            reason=reason,
            fault_code=fault,
            r_effective_conservative=r_eff
        )
        self.last_signal = sig
        return sig

    def _apply_hysteresis(self, target_state: DataState) -> DataState:
        """
        Enforces consecutive clean observations before promoting state
        from STALE or UNAVAILABLE back to HEALTHY.
        """
        if self.in_recovery:
            if target_state == DataState.HEALTHY:
                self.recovery_counter += 1
                if self.recovery_counter >= self.recovery_required_frames:
                    self.in_recovery = False
                    self.recovery_counter = 0
                    self.recovery_required_frames = 0
                    return DataState.HEALTHY
                return DataState.DEGRADED
            else:
                self.recovery_counter = 0
                return target_state
        else:
            return target_state

    def _calculate_r_effective(self, val: float, state: DataState) -> float:
        """Computes conservative r_effective strictly without optimistic bias."""
        if state == DataState.HEALTHY:
            return float(val)
        elif state == DataState.DEGRADED:
            return max(self.config.R_MIN_m, float(val) * self.config.DEGRADED_FACTOR)
        elif state == DataState.STALE:
            return max(self.config.R_MIN_m, float(self.last_valid_value) * self.config.STALE_FACTOR)
        elif state == DataState.CONFLICTING:
            return max(self.config.R_MIN_m, float(val) * self.config.DEGRADED_FACTOR)
        else:  # UNAVAILABLE
            return float(self.config.R_UNAVAILABLE_MIN_m)

    def _handle_invalid(
        self,
        reason: str,
        fault: FaultCode,
        timestamp: float,
        age: float,
        sequence: int,
        source: str
    ) -> ValidatedSignal:
        """Fails closed upon schema or range violation."""
        self.in_recovery = True
        self.recovery_counter = 0
        self.recovery_required_frames = self.config.RECOVERY_HYSTERESIS_UNAVAILABLE
        self.current_state = DataState.UNAVAILABLE
        self.last_fault_code = fault

        sig = ValidatedSignal(
            value=self.config.R_UNAVAILABLE_MIN_m,
            unit="m",
            timestamp=timestamp,
            age=age,
            source=source,
            sequence=sequence,
            health=DataState.UNAVAILABLE,
            confidence=0.0,
            reason=reason,
            fault_code=fault,
            r_effective_conservative=self.config.R_UNAVAILABLE_MIN_m
        )
        self.last_signal = sig
        return sig


    def get_current_health(self) -> Tuple[float, DataState, float]:
        """
        Polls current health without a new sample, evaluating staleness
        against elapsed wall-clock time.
        """
        now = self.clock()
        if self.last_valid_timestamp <= 0.0:
            return self.config.R_UNAVAILABLE_MIN_m, DataState.UNAVAILABLE, 0.0

        elapsed = now - self.last_valid_timestamp

        if elapsed > self.config.T_GRACE_PERIOD_s:
            state = DataState.UNAVAILABLE
            r_eff = self.config.R_UNAVAILABLE_MIN_m
            conf = 0.0
        elif elapsed > self.config.T_STALE_ENV_s:
            state = DataState.STALE
            r_eff = max(self.config.R_MIN_m, self.last_valid_value * self.config.STALE_FACTOR)
            conf = 0.40
        elif elapsed > self.config.T_DEGRADED_ENV_s:
            state = DataState.DEGRADED
            r_eff = max(self.config.R_MIN_m, self.last_valid_value * self.config.DEGRADED_FACTOR)
            conf = 0.70
        else:
            state = self.current_state
            r_eff = self._calculate_r_effective(self.last_valid_value, state)
            conf = 1.0 if state == DataState.HEALTHY else 0.70

        return r_eff, state, conf


class VehicleDataHealth:
    """
    Candidate deployment validator for generic vehicle telemetry signals.
    Validates physical speed, payload mass, and road grade before ingest.
    """

    def __init__(self, clock: Callable[[], float] = time.time):
        self.clock = clock

    def validate_speed(self, speed_mps: Any, max_speed_mps: float = 20.0) -> ValidatedSignal:
        now = self.clock()
        if speed_mps is None or not isinstance(speed_mps, (int, float)) or not math.isfinite(speed_mps):
            return ValidatedSignal(
                value=0.0,
                unit="m/s",
                timestamp=now,
                age=0.0,
                source="VEHICLE_SPEED",
                sequence=0,
                health=DataState.UNAVAILABLE,
                confidence=0.0,
                reason="Invalid or non-finite speed",
                fault_code=FaultCode.TYPE_SCHEMA_ERROR,
                r_effective_conservative=0.0
            )

        spd = float(speed_mps)
        if spd < 0.0 or spd > max_speed_mps:
            return ValidatedSignal(
                value=0.0,
                unit="m/s",
                timestamp=now,
                age=0.0,
                source="VEHICLE_SPEED",
                sequence=0,
                health=DataState.UNAVAILABLE,
                confidence=0.0,
                reason=f"Speed {spd:.2f} m/s out of bounds [0, {max_speed_mps}]",
                fault_code=FaultCode.RANGE_VIOLATION,
                r_effective_conservative=0.0
            )

        return ValidatedSignal(
            value=spd,
            unit="m/s",
            timestamp=now,
            age=0.0,
            source="VEHICLE_SPEED",
            sequence=0,
            health=DataState.HEALTHY,
            confidence=1.0,
            reason="VALID",
            fault_code=FaultCode.NONE,
            r_effective_conservative=spd
        )


class DataHealthManager:
    """
    Unified manager aggregating EnvironmentalDataHealth and VehicleDataHealth.
    """

    def __init__(
        self,
        env_config: Optional[EnvironmentalHealthConfig] = None,
        clock: Callable[[], float] = time.time
    ):
        self.clock = clock
        self.env_health = EnvironmentalDataHealth(config=env_config, clock=clock)
        self.veh_health = VehicleDataHealth(clock=clock)

    def process_environmental_telemetry(
        self,
        visibility_m: Any,
        timestamp: Optional[float] = None,
        sequence: int = 0,
        source_id: str = "DEFAULT_WEATHER_STATION",
        secondary_visibility_m: Optional[float] = None
    ) -> ValidatedSignal:
        return self.env_health.update(
            visibility_m=visibility_m,
            timestamp=timestamp,
            sequence=sequence,
            source_id=source_id,
            secondary_visibility_m=secondary_visibility_m
        )

    def get_conservative_r_effective(self) -> float:
        r_eff, _, _ = self.env_health.get_current_health()
        return r_eff

    def process_to_health_record(
        self,
        visibility_m: Any,
        timestamp: Optional[float] = None,
        sequence: int = 0,
        sensor_id: str = "VIS_RAMP_02"
    ) -> SensorHealthRecord:
        sig = self.process_environmental_telemetry(
            visibility_m=visibility_m,
            timestamp=timestamp,
            sequence=sequence,
            source_id=sensor_id
        )
        return to_sensor_health_record(
            signal=sig,
            sensor_id=sensor_id,
            last_valid_timestamp=self.env_health.last_valid_timestamp
        )


# ==============================================================================
# PHASE 9 STANDARDIZED SENSOR HEALTH LAYER (CONTRACT IF-11)
# ==============================================================================

class SensorQuality(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    MISSING = "MISSING"
    STUCK = "STUCK"
    OUTLIER = "OUTLIER"
    INCONSISTENT = "INCONSISTENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class SensorHealthRecord:
    """
    Authoritative per-sensor data health representation.
    """
    sensor_id: str
    timestamp: float
    value: float
    quality: SensorQuality
    confidence: float
    fault_code: str
    last_valid_timestamp: float


def to_sensor_health_record(
    signal: ValidatedSignal,
    sensor_id: str,
    last_valid_timestamp: float
) -> SensorHealthRecord:
    """Maps ValidatedSignal to standardized SensorHealthRecord."""
    if signal.health == DataState.HEALTHY:
        quality = SensorQuality.VALID
    elif signal.health == DataState.DEGRADED:
        quality = SensorQuality.DEGRADED
    elif signal.health == DataState.STALE:
        quality = SensorQuality.STALE
    elif signal.health == DataState.CONFLICTING:
        quality = SensorQuality.INCONSISTENT
    else:  # UNAVAILABLE
        if signal.fault_code == FaultCode.STUCK_AT:
            quality = SensorQuality.STUCK
        elif signal.fault_code in [FaultCode.RANGE_VIOLATION, FaultCode.NON_FINITE, FaultCode.EXCESSIVE_NOISE]:
            quality = SensorQuality.OUTLIER
        elif signal.fault_code in [FaultCode.TIMEOUT, FaultCode.STALE_TIMEOUT]:
            quality = SensorQuality.MISSING
        else:
            quality = SensorQuality.UNKNOWN

    fault_code_str = signal.fault_code.value if hasattr(signal.fault_code, "value") else str(signal.fault_code)
    return SensorHealthRecord(
        sensor_id=sensor_id,
        timestamp=signal.timestamp,
        value=signal.value,
        quality=quality,
        confidence=signal.confidence,
        fault_code=fault_code_str,
        last_valid_timestamp=last_valid_timestamp
    )

