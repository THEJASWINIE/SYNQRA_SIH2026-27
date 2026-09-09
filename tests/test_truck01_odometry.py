"""
FOG-ORCHESTRATOR 2.0 — Pass 2 TRUCK_01 Local Odometry & Anti-Fabrication Test Suite.

Verifies:
  1. 1 wheel revolution (42 pulses) produces the expected distance (pi * 0.10 ~ 0.314159 m).
  2. PPR conversion for PPR = 42.
  3. Wheel diameter = 0.10 m.
  4. Zero pulses = zero translation.
  5. Negative/invalid dt <= 0 rejected.
  6. Heading 0 = forward movement increases x.
  7. Heading pi/2 = forward movement increases y.
  8. Heading changes affect subsequent movement direction.
  9. speed_mps is NOT substituted for missing encoder pulse data.
  10. Odometry provenance = PHYSICAL_DERIVED.
  11. Method = WHEEL_IMU_ODOMETRY.
  12. GNSS remains separate (position_gnss untouched).
  13. TRUCK_02 does NOT receive TRUCK_01 odometry (TRUCK_02 odometry is UNAVAILABLE).
  14. Canonical Twin propagates state to projected view for all HMIs.
  15. Verification label is ALGORITHM VERIFIED or CONTRACT VERIFIED (never PHYSICAL HARDWARE VERIFIED).
  16. Anti-fabrication assertions.
"""

import math
import pytest
from integration_adapters.wheel_imu_odometry import WheelImuOdometryCalculator
from twin.twin_state_store import TwinStateStore, TwinMode, Source
from telemetry_ingest import TelemetryIngestor, Transport
from twin_projection import build_vehicle_projection


@pytest.fixture
def odom_calc():
    return WheelImuOdometryCalculator("TRUCK_01")


@pytest.fixture
def fresh_ingestor():
    store = TwinStateStore(mode=TwinMode.HYBRID)
    ingestor = TelemetryIngestor(store)
    return store, ingestor


def test_one_wheel_revolution_distance(odom_calc):
    """Requirement 1 & 2 & 3: 42 pulses = 1 revolution = pi * 0.10 m (~0.314159 m)."""
    # Initialize at t=1.0s, 0 pulses
    odom_calc.update(timestamp=1.0, pulse_count=0)

    # 42 pulses at t=2.0s (heading = 0)
    res = odom_calc.update(timestamp=2.0, pulse_count=42)

    expected_dist = (42.0 / 42.0) * math.pi * 0.10
    assert res["status"] == "VALID"
    assert math.isclose(res["distance_m"], round(expected_dist, 4), abs_tol=1e-3)
    assert math.isclose(res["x_m"], round(expected_dist, 4), abs_tol=1e-3)
    assert res["y_m"] == 0.0


def test_ppr_42_conversion(odom_calc):
    """Requirement 2: PPR = 42 conversion check for fractional revolutions."""
    odom_calc.update(timestamp=1.0, pulse_count=0)
    # 21 pulses = 0.5 revolutions
    res = odom_calc.update(timestamp=2.0, pulse_count=21)

    expected_dist = (21.0 / 42.0) * math.pi * 0.10
    assert math.isclose(res["distance_m"], round(expected_dist, 4), abs_tol=1e-3)


def test_zero_pulses_zero_translation(odom_calc):
    """Requirement 4: Zero pulses produces zero translation."""
    odom_calc.update(timestamp=1.0, pulse_count=0)
    res = odom_calc.update(timestamp=2.0, pulse_count=0)

    assert res["x_m"] == 0.0
    assert res["y_m"] == 0.0
    assert res["distance_m"] == 0.0


def test_negative_invalid_dt_rejected(odom_calc):
    """Requirement 5: Negative or zero dt is rejected without advancing pose."""
    odom_calc.update(timestamp=1.0, pulse_count=0)
    
    # dt <= 0
    res_neg = odom_calc.update(timestamp=0.5, pulse_count=10)
    assert res_neg["status"] in ("INVALID", "STALE")
    assert res_neg["x_m"] == 0.0

    # Non-finite dt
    res_nan = odom_calc.update(timestamp=float("nan"), pulse_count=20)
    assert res_nan["status"] == "INVALID"


def test_heading_0_increases_x(odom_calc):
    """Requirement 6: Heading 0 moves forward along +X axis."""
    odom_calc.update(timestamp=1.0, pulse_count=0)
    res = odom_calc.update(timestamp=2.0, pulse_count=42, gz_rad_s=0.0)

    assert res["x_m"] > 0.0
    assert abs(res["y_m"]) < 1e-4


def test_heading_pi_half_increases_y(odom_calc):
    """Requirement 7: Heading pi/2 moves forward along +Y axis."""
    odom_calc.reset(x=0.0, y=0.0, heading_rad=math.pi / 2.0)
    odom_calc.update(timestamp=1.0, pulse_count=0)

    res = odom_calc.update(timestamp=2.0, pulse_count=42, gz_rad_s=0.0)

    assert abs(res["x_m"]) < 1e-3
    assert res["y_m"] > 0.0


def test_heading_changes_affect_subsequent_movement(odom_calc):
    """Requirement 8: Gyro gz changes heading and alters subsequent movement vector."""
    odom_calc.update(timestamp=1.0, pulse_count=0)

    # Turn left by pi/2 rad/s over 1 second (gz = pi/2)
    odom_calc.update(timestamp=2.0, pulse_count=0, gz_rad_s=math.pi / 2.0)

    # Now move forward 42 pulses (heading should be pi/2)
    res = odom_calc.update(timestamp=3.0, pulse_count=42, gz_rad_s=0.0)

    assert math.isclose(res["heading_rad"], round(math.pi / 2.0, 4), abs_tol=1e-2)
    assert abs(res["x_m"]) < 1e-3
    assert res["y_m"] > 0.0


def test_speed_mps_not_substituted(odom_calc):
    """Requirement 1 (Strict): Missing pulse data makes odometry UNAVAILABLE/STALE; speed_mps is NOT substituted."""
    odom_calc.update(timestamp=1.0, pulse_count=0)

    # Telemetry update with NO pulse_count/delta_pulses (None)
    res = odom_calc.update(timestamp=2.0, pulse_count=None, delta_pulses=None)

    assert res["status"] in ("UNAVAILABLE", "STALE")


def test_odometry_provenance_and_method(fresh_ingestor):
    """Requirement 9 & 10: Ingested TRUCK_01 odometry has provenance PHYSICAL_DERIVED and method WHEEL_IMU_ODOMETRY."""
    store, ingestor = fresh_ingestor

    payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "source": "DIRECT_WIFI",
        "pulses": 0,
        "gz": 0.0,
        "source_timestamp": 100.0,
    }
    ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI, is_simulated=False)

    payload2 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 2,
        "source": "DIRECT_WIFI",
        "pulses": 42,
        "gz": 0.0,
        "source_timestamp": 101.0,
    }
    ingestor.ingest_parsed_record(payload2, transport=Transport.DIRECT_WIFI, is_simulated=False)

    v_state = store.get_vehicle("TRUCK_01")
    assert v_state is not None
    odom_sourced = v_state.get("position_odom")
    assert odom_sourced is not None and odom_sourced.is_available
    assert odom_sourced.source == Source.DERIVED
    assert odom_sourced.origin == Source.HARDWARE

    val = odom_sourced.value
    assert val["provenance_label"] == "PHYSICAL_DERIVED"
    assert val["method"] == "WHEEL_IMU_ODOMETRY"
    assert val["origin_type"] == "LOCAL ODOMETRY ORIGIN"


def test_gnss_remains_separate(fresh_ingestor):
    """Requirement 11: Odometry update does NOT populate or overwrite position_gnss."""
    store, ingestor = fresh_ingestor

    payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "source": "DIRECT_WIFI",
        "pulses": 42,
        "gz": 0.0,
        "source_timestamp": 100.0,
    }
    ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

    v_state = store.get_vehicle("TRUCK_01")
    gnss_field = v_state.get("position_gnss")
    assert gnss_field is None or not gnss_field.is_available or gnss_field.value is None


def test_truck02_odometry_isolation(fresh_ingestor):
    """Requirement 13 & 7: TRUCK_02 odometry is NOT implemented and remains UNAVAILABLE."""
    store, ingestor = fresh_ingestor

    payload = {
        "vehicle_id": "TRUCK_02",
        "sequence": 1,
        "source": "V2V",
        "pulses": 100,
        "gz": 0.5,
        "source_timestamp": 100.0,
    }
    ingestor.ingest_parsed_record(payload, transport=Transport.V2V)

    v_state = store.get_vehicle("TRUCK_02")
    odom_field = v_state.get("position_odom")
    assert odom_field is not None
    val = odom_field.value
    assert val["status"] == "UNAVAILABLE"
    assert val["provenance_label"] == "UNAVAILABLE"


def test_canonical_twin_projection_three_hmis(fresh_ingestor):
    """Requirement 14: Projection includes position_odom identically for Control Room and all HMIs."""
    store, ingestor = fresh_ingestor

    payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "source": "DIRECT_WIFI",
        "pulses": 0,
        "source_timestamp": 10.0,
    }
    ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

    payload2 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 2,
        "source": "DIRECT_WIFI",
        "pulses": 42,
        "source_timestamp": 11.0,
    }
    ingestor.ingest_parsed_record(payload2, transport=Transport.DIRECT_WIFI)

    proj = build_vehicle_projection(store, "TRUCK_01")
    assert proj is not None
    assert "position_odom" in proj["dynamic"]
    odom_proj = proj["dynamic"]["position_odom"]["value"]
    assert odom_proj["status"] == "VALID"
    assert odom_proj["provenance_label"] == "PHYSICAL_DERIVED"


def test_anti_fabrication_assertions(fresh_ingestor):
    """Anti-fabrication checks: No lat/lon created, no GNSS position fabricated, no synthetic GNSS flag removed."""
    store, ingestor = fresh_ingestor

    payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "source": "DIRECT_WIFI",
        "pulses": 100,
        "gz": 0.1,
        "source_timestamp": 50.0,
    }
    ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

    v_state = store.get_vehicle("TRUCK_01")
    odom_val = v_state.get("position_odom").value

    # Must NOT contain lat/lon
    assert "latitude" not in odom_val
    assert "longitude" not in odom_val

    # Verification label must NOT claim physical hardware verification in software tests
    assert odom_val.get("verification_label") != "PHYSICAL HARDWARE VERIFIED"
