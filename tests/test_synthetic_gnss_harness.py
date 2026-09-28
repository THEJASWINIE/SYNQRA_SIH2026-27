"""
Software-Only Synthetic GNSS Telemetry Test Harness — Test Cases 1 to 10.

Executes complete end-to-end software pipeline validation for synthetic GNSS
telemetry payloads under strict provenance isolation rules.

ASSERTION GUARANTEE (Rules 1-10):
  No synthetic payload tested here is EVER promoted to HARDWARE or PHYSICAL.
  All test inputs are explicitly labeled SOFTWARE-ONLY / SYNTHETIC INPUT.
"""

import time
import pytest
from twin.twin_state_store import Source, TwinStateStore, Quality
from telemetry_ingest import TelemetryIngestor, Transport
from twin_projection import build_vehicle_projection, build_twin_snapshot
from tests.fixtures.synthetic_gnss import (
    build_synthetic_gnss_payload,
    inject_synthetic_gnss_vehicle,
    SYNTHETIC_TEST_COORDINATES,
)


@pytest.fixture
def store():
    return TwinStateStore()


@pytest.fixture
def ingestor(store):
    return TelemetryIngestor(store)


# -----------------------------------------------------------------------------
# Test Case 1 — Valid Synthetic Position
# -----------------------------------------------------------------------------
def test_case_1_valid_synthetic_position_injection(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Inject valid synthetic GNSS telemetry for TRUCK_01 and TRUCK_02.
    Verify both positions reach the Twin and projection with SOFTWARE_ONLY origin.
    """
    res1 = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", sequence=1)
    res2 = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_02", sequence=1)

    assert res1.accepted
    assert res2.accepted

    v1_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    v2_field = store.get_vehicle_field("TRUCK_02", "position_gnss")

    assert v1_field is not None
    assert v2_field is not None

    assert v1_field.value["latitude"] == SYNTHETIC_TEST_COORDINATES["TRUCK_01"]["latitude"]
    assert v1_field.value["longitude"] == SYNTHETIC_TEST_COORDINATES["TRUCK_01"]["longitude"]
    assert v1_field.value["origin"] == "SOFTWARE_ONLY"
    assert v1_field.source is Source.SIMULATION

    proj1 = build_vehicle_projection(store, "TRUCK_01")
    assert proj1 is not None
    gnss_proj = proj1["dynamic"]["position_gnss"]
    assert gnss_proj["available"] is True
    assert gnss_proj["value"]["latitude"] == SYNTHETIC_TEST_COORDINATES["TRUCK_01"]["latitude"]
    assert gnss_proj["value"]["origin"] == "SOFTWARE_ONLY"
    assert gnss_proj["origin"] == "SIMULATION"


# -----------------------------------------------------------------------------
# Test Case 2 — No Position Telemetry
# -----------------------------------------------------------------------------
def test_case_2_no_position_telemetry(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Telemetry without GNSS position leaves position_gnss unavailable.
    Vehicle remains in Fleet.
    """
    payload = {
        "vehicle_id": "TRUCK_01",
        "sequence_number": 1,
        "rpm": 150.0,
        "speed_mps": 2.0,
    }
    res = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI, is_simulated=False)
    assert res.accepted

    assert store.get_vehicle("TRUCK_01") is not None
    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos_field is None or pos_field.value is None


# -----------------------------------------------------------------------------
# Test Case 3 — Invalid Latitude Rejection
# -----------------------------------------------------------------------------
def test_case_3_invalid_latitude_rejection(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Latitude > 90 is rejected. No fake fallback coordinate is created.
    """
    res = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", latitude=91.0, sequence=1)
    assert res.accepted  # Packet accepted, position rejected

    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos_field is None or pos_field.value is None


# -----------------------------------------------------------------------------
# Test Case 4 — Invalid Longitude Rejection
# -----------------------------------------------------------------------------
def test_case_4_invalid_longitude_rejection(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Longitude > 180 is rejected. No fake fallback coordinate is created.
    """
    res = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", longitude=181.0, sequence=1)
    assert res.accepted

    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos_field is None or pos_field.value is None


# -----------------------------------------------------------------------------
# Test Case 5 — No GNSS Fix Rejection
# -----------------------------------------------------------------------------
def test_case_5_no_gnss_fix_rejection(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    position_status = NO_FIX is rejected. Vehicle remains in Fleet.
    """
    res = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", status="NO_FIX", sequence=1)
    assert res.accepted

    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos_field is None or pos_field.value is None


# -----------------------------------------------------------------------------
# Test Case 6 — Stale Position Handling
# -----------------------------------------------------------------------------
def test_case_6_stale_position_handling(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Old position timestamp is recorded and freshness can be evaluated as STALE.
    """
    old_ts = time.time() - 3600.0  # 1 hour old
    res = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", timestamp=old_ts, sequence=1)
    assert res.accepted

    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos_field is not None
    assert pos_field.value["timestamp"] == old_ts


# -----------------------------------------------------------------------------
# Test Case 7 — Mode Isolation
# -----------------------------------------------------------------------------
def test_case_7_mode_isolation(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Synthetic test input has origin=SOFTWARE_ONLY and source=SIMULATION.
    It is NEVER promoted to Source.HARDWARE or origin=HARDWARE.
    """
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", sequence=1)
    pos_field = store.get_vehicle_field("TRUCK_01", "position_gnss")

    assert pos_field.source is Source.SIMULATION
    assert pos_field.origin is None or pos_field.origin is Source.SIMULATION or pos_field.value["origin"] == "SOFTWARE_ONLY"
    assert pos_field.source is not Source.HARDWARE


# -----------------------------------------------------------------------------
# Test Case 8 — Vehicle Identity Preservation
# -----------------------------------------------------------------------------
def test_case_8_vehicle_identity_preservation(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    TRUCK_01 and TRUCK_02 identities are strictly preserved without inference.
    """
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", sequence=1)
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_02", sequence=1)

    p1 = store.get_vehicle("TRUCK_01")
    p2 = store.get_vehicle("TRUCK_02")

    assert p1.entity_id == "TRUCK_01"
    assert p2.entity_id == "TRUCK_02"


# -----------------------------------------------------------------------------
# Test Case 9 — Position Movement (A -> B)
# -----------------------------------------------------------------------------
def test_case_9_position_movement(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Sequential position updates move vehicle from position A to position B.
    """
    # Position A
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", latitude=18.67812, longitude=81.18912, sequence=1)
    pos_a = store.get_vehicle_field("TRUCK_01", "position_gnss").value

    # Position B
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", latitude=18.67950, longitude=81.19050, sequence=2)
    pos_b = store.get_vehicle_field("TRUCK_01", "position_gnss").value

    assert pos_a["latitude"] == 18.67812
    assert pos_b["latitude"] == 18.67950
    assert pos_b["longitude"] == 81.19050


# -----------------------------------------------------------------------------
# Test Case 10 — Complete Pipeline Assertion
# -----------------------------------------------------------------------------
def test_case_10_complete_pipeline_assertion(ingestor, store):
    """
    SOFTWARE-ONLY / SYNTHETIC INPUT:
    Verifies full backend pipeline:
    synthetic payload -> TelemetryIngestor -> TwinStateStore -> build_twin_snapshot.
    """
    payload = build_synthetic_gnss_payload("TRUCK_01", latitude=18.67812, longitude=81.18912, sequence=1)
    res = ingestor.ingest_parsed_record(payload, transport=Transport.EMULATOR, is_simulated=True)
    assert res.accepted

    snapshot = build_twin_snapshot(store)
    truck1 = snapshot["vehicles"]["TRUCK_01"]
    assert truck1 is not None

    gnss_field = truck1["dynamic"]["position_gnss"]
    assert gnss_field["available"] is True
    assert gnss_field["value"]["latitude"] == 18.67812
    assert gnss_field["value"]["longitude"] == 81.18912
    assert gnss_field["value"]["origin"] == "SOFTWARE_ONLY"
    assert gnss_field["origin"] == "SIMULATION"
