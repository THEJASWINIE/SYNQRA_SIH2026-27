"""
tests/test_environmental_data_health.py
---------------------------------------
Comprehensive verification suite for EnvironmentalDataHealth and DataHealthManager.
Verifies rules H1 (Freshness), H2 (Schema/Type), H3 (Range), H4 (Sequence),
H5 (Stuck-At / Noise), H6 (Conflict), Recovery Hysteresis, and Class C Plausible-But-Wrong.
"""

import math
import time
import pytest

from integration_adapters.environmental_data_health import (
    DataState,
    FaultCode,
    ValidatedSignal,
    EnvironmentalHealthConfig,
    EnvironmentalDataHealth,
    VehicleDataHealth,
    DataHealthManager,
)
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed


class MockClock:
    """Controllable mock clock for deterministic time advancing."""
    def __init__(self, start_time: float = 1000.0):
        self._time = start_time

    def __call__(self) -> float:
        return self._time

    def advance(self, dt: float) -> None:
        self._time += dt

    def set(self, t: float) -> None:
        self._time = t


@pytest.fixture
def mock_clock():
    return MockClock()


@pytest.fixture
def config():
    return EnvironmentalHealthConfig(
        T_DEGRADED_ENV_s=30.0,
        T_STALE_ENV_s=60.0,
        T_GRACE_PERIOD_s=120.0,
        V_MIN_PLAUSIBLE_m=0.5,
        V_MAX_PLAUSIBLE_m=2000.0,
        DEGRADED_FACTOR=0.70,
        STALE_FACTOR=0.50,
        R_MIN_m=5.0,
        R_UNAVAILABLE_MIN_m=8.0,
        RECOVERY_HYSTERESIS_STALE=2,
        RECOVERY_HYSTERESIS_UNAVAILABLE=3,
        STUCK_WINDOW_SIZE=10,
        STUCK_STD_THRESHOLD_m=0.05,
        STUCK_MIN_TIME_s=300.0,
        NOISE_STD_THRESHOLD_m=20.0,
        CONFLICT_THRESHOLD_m=25.0
    )


@pytest.fixture
def env_health(config, mock_clock):
    return EnvironmentalDataHealth(config=config, clock=mock_clock)


def test_h1_fresh_nominal(env_health, mock_clock):
    """Rule H1: Fresh, in-range observation produces HEALTHY state."""
    sig = env_health.update(visibility_m=50.0, timestamp=mock_clock(), sequence=1)
    assert sig.health == DataState.HEALTHY
    assert sig.fault_code == FaultCode.NONE
    assert sig.confidence == 1.0
    assert sig.r_effective_conservative == 50.0
    assert sig.unit == "m"


def test_h1_freshness_degraded_age(env_health, mock_clock):
    """Rule H1: Observation older than T_DEGRADED transitions to DEGRADED with 30% penalty."""
    t0 = mock_clock()
    # Telemetry produced at t0, arrives at t0 + 35s (> 30s)
    sig = env_health.update(visibility_m=50.0, timestamp=t0, sequence=1)
    mock_clock.advance(35.0)

    # Ingest packet that is 35 seconds old
    sig_old = env_health.update(visibility_m=50.0, timestamp=t0, sequence=2)
    assert sig_old.health == DataState.DEGRADED
    assert sig_old.fault_code == FaultCode.TIMEOUT
    assert sig_old.confidence == 0.70
    assert sig_old.r_effective_conservative == pytest.approx(35.0)  # 50.0 * 0.7


def test_h1_freshness_stale_age(env_health, mock_clock):
    """Rule H1: Observation older than T_STALE transitions to STALE with 50% penalty."""
    t0 = mock_clock()
    sig0 = env_health.update(visibility_m=50.0, timestamp=t0, sequence=1)
    mock_clock.advance(70.0)

    sig_stale = env_health.update(visibility_m=50.0, timestamp=t0, sequence=2)
    assert sig_stale.health == DataState.STALE
    assert sig_stale.fault_code == FaultCode.STALE_TIMEOUT
    assert sig_stale.confidence == 0.40
    assert sig_stale.r_effective_conservative == pytest.approx(25.0)  # 50.0 * 0.5


def test_h1_freshness_unavailable_grace_exceeded(env_health, mock_clock):
    """Rule H1: Observation older than T_GRACE_PERIOD transitions to UNAVAILABLE (R_UNAVAILABLE_MIN)."""
    t0 = mock_clock()
    env_health.update(visibility_m=50.0, timestamp=t0, sequence=1)
    mock_clock.advance(130.0)

    sig_unavail = env_health.update(visibility_m=50.0, timestamp=t0, sequence=2)
    assert sig_unavail.health == DataState.UNAVAILABLE
    assert sig_unavail.fault_code == FaultCode.STALE_TIMEOUT
    assert sig_unavail.confidence == 0.0
    assert sig_unavail.r_effective_conservative == 8.0


def test_h2_schema_and_type_rejection(env_health, mock_clock):
    """Rule H2: Rejects None, non-numeric, string, boolean, list."""
    bad_inputs = [None, "fifty_metres", [50.0], {"vis": 50.0}, True, False]
    for bad in bad_inputs:
        sig = env_health.update(visibility_m=bad, timestamp=mock_clock(), sequence=1)
        assert sig.health == DataState.UNAVAILABLE
        assert sig.fault_code == FaultCode.TYPE_SCHEMA_ERROR
        assert sig.r_effective_conservative == 8.0


def test_h2_non_finite_rejection(env_health, mock_clock):
    """Rule H2: Rejects NaN, +Inf, -Inf."""
    non_finites = [float("nan"), float("inf"), float("-inf")]
    for nf in non_finites:
        sig = env_health.update(visibility_m=nf, timestamp=mock_clock(), sequence=1)
        assert sig.health == DataState.UNAVAILABLE
        assert sig.fault_code == FaultCode.NON_FINITE
        assert sig.r_effective_conservative == 8.0


def test_h3_range_plausibility(env_health, mock_clock):
    """Rule H3: Rejects negative visibility, zero, or > 2000m."""
    out_of_bounds = [-10.0, 0.0, 0.49, 2000.1, 50000.0]
    for oob in out_of_bounds:
        sig = env_health.update(visibility_m=oob, timestamp=mock_clock(), sequence=1)
        assert sig.health == DataState.UNAVAILABLE
        assert sig.fault_code == FaultCode.RANGE_VIOLATION
        assert sig.r_effective_conservative == 8.0


def test_h4_sequence_tracking(env_health, mock_clock):
    """Rule H4: Detects duplicate sequence and rollback."""
    t0 = mock_clock()
    sig1 = env_health.update(visibility_m=50.0, timestamp=t0, sequence=10)
    assert sig1.health == DataState.HEALTHY

    # Duplicate sequence 10
    sig_dup = env_health.update(visibility_m=50.0, timestamp=t0 + 1.0, sequence=10)
    assert sig_dup.health == DataState.DEGRADED
    assert sig_dup.fault_code == FaultCode.SEQUENCE_DUPLICATE

    # Sequence rollback: sequence 5 (< 10)
    sig_roll = env_health.update(visibility_m=50.0, timestamp=t0 + 2.0, sequence=5)
    assert sig_roll.health == DataState.DEGRADED
    assert sig_roll.fault_code == FaultCode.SEQUENCE_ROLLBACK


def test_h5_stuck_at_sensor(env_health, mock_clock):
    """Rule H5: Constant sensor value across window > 300s flags STUCK_AT."""
    t = mock_clock()
    for seq in range(1, 11):
        mock_clock.set(t + seq * 35.0)  # total span = 350s (> 300s)
        sig = env_health.update(visibility_m=30.0, timestamp=mock_clock(), sequence=seq)

    assert sig.health == DataState.DEGRADED
    assert sig.fault_code == FaultCode.STUCK_AT
    assert "Potential stuck-at" in sig.reason


def test_h5_noisy_sensor(env_health, mock_clock):
    """Rule H5: Sensor with excessive standard deviation flags EXCESSIVE_NOISE."""
    noisy_vals = [10.0, 60.0, 15.0, 75.0, 20.0, 80.0, 10.0, 70.0, 15.0, 85.0]
    t = mock_clock()
    for idx, val in enumerate(noisy_vals):
        mock_clock.set(t + idx * 1.0)
        sig = env_health.update(visibility_m=val, timestamp=mock_clock(), sequence=idx + 1)

    assert sig.health == DataState.DEGRADED
    assert sig.fault_code == FaultCode.EXCESSIVE_NOISE


def test_h6_cross_source_conflict(env_health, mock_clock):
    """Rule H6: Dual sources disagreeing beyond 25m flags CONFLICTING and chooses minimum."""
    sig = env_health.update(
        visibility_m=60.0,
        timestamp=mock_clock(),
        sequence=1,
        secondary_visibility_m=20.0  # Disagreement: 40m (> 25m)
    )
    assert sig.health == DataState.CONFLICTING
    assert sig.fault_code == FaultCode.CROSS_SOURCE_CONFLICT
    # Resolves conservatively to min(60, 20) * 0.7 = 14.0 m
    assert sig.r_effective_conservative == pytest.approx(14.0)


def test_recovery_hysteresis(env_health, mock_clock):
    """Rule Hysteresis: Recovery from UNAVAILABLE requires 3 consecutive clean frames."""
    t0 = mock_clock()
    # Force UNAVAILABLE via range violation
    sig_bad = env_health.update(visibility_m=-5.0, timestamp=t0, sequence=1)
    assert sig_bad.health == DataState.UNAVAILABLE

    # Frame 1 clean -> still DEGRADED (recovery observation 1/3)
    sig_r1 = env_health.update(visibility_m=40.0, timestamp=t0 + 1.0, sequence=2)
    assert sig_r1.health == DataState.DEGRADED

    # Frame 2 clean -> still DEGRADED (recovery observation 2/3)
    sig_r2 = env_health.update(visibility_m=40.0, timestamp=t0 + 2.0, sequence=3)
    assert sig_r2.health == DataState.DEGRADED

    # Frame 3 clean -> promoted to HEALTHY (recovery observation 3/3)
    sig_r3 = env_health.update(visibility_m=40.0, timestamp=t0 + 3.0, sequence=4)
    assert sig_r3.health == DataState.HEALTHY
    assert sig_r3.r_effective_conservative == 40.0


def test_class_c_plausible_but_wrong_limitation(env_health, mock_clock):
    """
    CRITICAL SCIENTIFIC PROOF:
    Plausible-but-wrong single-source data (True=5m, Reported=50m) CANNOT be detected
    by a single-source rule-based health layer. The health layer marks it HEALTHY.
    This demonstrates the documented Class C boundary.
    """
    true_visibility_m = 5.0
    reported_visibility_m = 50.0  # Plausible, fresh, valid format

    sig = env_health.update(
        visibility_m=reported_visibility_m,
        timestamp=mock_clock(),
        sequence=1
    )
    # The health layer has no reference, so it classifies HEALTHY
    assert sig.health == DataState.HEALTHY
    assert sig.r_effective_conservative == 50.0
    # Safety implication: This is why an independent validated reference is required
    # for Class C dangerous undetected failures.


def test_fail_closed_on_unhandled_exception(env_health, monkeypatch):
    """Fail-closed principle: Any internal error returns UNAVAILABLE without crashing."""
    def crash_pipeline(*args, **kwargs):
        raise RuntimeError("Simulated internal algorithmic crash")

    monkeypatch.setattr(env_health, "_validate_pipeline", crash_pipeline)
    sig = env_health.update(visibility_m=50.0)

    assert sig.health == DataState.UNAVAILABLE
    assert sig.fault_code == FaultCode.MODULE_EXCEPTION
    assert sig.r_effective_conservative == 8.0
    assert sig.confidence == 0.0


def test_solve_safe_speed_integration(env_health, mock_clock):
    """Verifies that health-aware r_effective strictly tightens v_safe in the physics solver."""
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=8.0, speed_limit_kmh=40.0)
    env = EnvironmentState(r_effective=50.0, mu_true=0.35)

    comm = CommunicationModel()

    # Nominal healthy visibility (50m)
    sig_healthy = env_health.update(visibility_m=50.0, timestamp=mock_clock(), sequence=1)
    res_healthy = solve_safe_speed(
        veh, road, env, comm, mu_effective=0.35, r_effective=sig_healthy.r_effective_conservative
    )

    # Degraded visibility (stale 35s -> r_effective = 35m)
    mock_clock.advance(35.0)
    sig_degraded = env_health.update(visibility_m=50.0, timestamp=mock_clock() - 35.0, sequence=2)
    res_degraded = solve_safe_speed(
        veh, road, env, comm, mu_effective=0.35, r_effective=sig_degraded.r_effective_conservative
    )

    # Unavailable visibility -> r_effective = 8m
    mock_clock.advance(200.0)
    sig_unavail = env_health.update(visibility_m=50.0, timestamp=mock_clock() - 200.0, sequence=3)
    res_unavail = solve_safe_speed(
        veh, road, env, comm, mu_effective=0.35, r_effective=sig_unavail.r_effective_conservative
    )

    # Assert monotonic conservative tightening
    assert res_healthy.v_safe_ms > res_degraded.v_safe_ms
    assert res_degraded.v_safe_ms > res_unavail.v_safe_ms
    assert res_unavail.v_safe_ms > 0.0  # Still positive crawl speed at 8m


def test_vehicle_data_health_validation(mock_clock):
    """Verifies vehicle speed validation: valid, negative, out of bounds, non-finite."""
    v_health = VehicleDataHealth(clock=mock_clock)

    # Valid speed
    sig1 = v_health.validate_speed(8.5)
    assert sig1.health == DataState.HEALTHY
    assert sig1.value == 8.5

    # Negative speed
    sig_neg = v_health.validate_speed(-2.0)
    assert sig_neg.health == DataState.UNAVAILABLE
    assert sig_neg.fault_code == FaultCode.RANGE_VIOLATION
    assert sig_neg.value == 0.0

    # Overspeed impossible for dump truck (> 20 m/s)
    sig_over = v_health.validate_speed(35.0)
    assert sig_over.health == DataState.UNAVAILABLE
    assert sig_over.fault_code == FaultCode.RANGE_VIOLATION

    # Non-finite
    sig_nan = v_health.validate_speed(float("nan"))
    assert sig_nan.health == DataState.UNAVAILABLE
    assert sig_nan.fault_code == FaultCode.TYPE_SCHEMA_ERROR


def test_data_health_manager_coordination(mock_clock):
    """Verifies unified coordination of environmental and vehicle health."""
    mgr = DataHealthManager(clock=mock_clock)
    sig_env = mgr.process_environmental_telemetry(visibility_m=45.0, timestamp=mock_clock(), sequence=1)
    assert sig_env.health == DataState.HEALTHY
    assert mgr.get_conservative_r_effective() == 45.0

    # Fast forward time to stale
    mock_clock.advance(70.0)
    r_eff = mgr.get_conservative_r_effective()
    assert r_eff == pytest.approx(45.0 * 0.5)  # 22.5 m

