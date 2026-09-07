"""
D005 — Bounded request body + field allowlist + WS snapshot.

Proves:
1. 2 MB POST returns 413.
2. Oversized request does not enter vehicle_telemetry_store.
3. Oversized request does not mutate Twin.
4. Oversized request does not poison the WS snapshot.
5. A fresh WS client can still connect afterward.
6. Normal <=64 KiB telemetry still works.
7. A payload with huge unknown fields cannot bypass the limit.
8. Snapshot contains canonical Twin state only; never raw request content.
"""

import json
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))

from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    try:
        from app.main import twin_store
        if twin_store is not None:
            with twin_store._lock:
                twin_store._vehicles.clear()
    except Exception:
        pass
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _normal_payload():
    return {
        "vehicle_id": "TRUCK_01",
        "rpm": 240.0,
        "speed": 2.5,
        "acceleration": {"x": 0.12, "y": -0.05, "z": 9.81},
        "gyroscope": {"x": 0.02, "y": 0.01, "z": -0.03},
        "data_quality": "OK",
        "timestamp": 1000000.0,
    }


class TestOversizedPayloadRejected:

    def test_2mb_post_returns_413(self, client):
        """A 2 MB payload must be rejected with 413."""
        big = {"vehicle_id": "TRUCK_01", "data": "x" * (2 * 1024 * 1024)}
        r = client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 413

    def test_oversized_does_not_enter_cache(self, client):
        """Oversized payload must not appear in vehicle_telemetry_store."""
        big = {"vehicle_id": "TRUCK_01", "data": "x" * (2 * 1024 * 1024)}
        client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )
        assert "TRUCK_01" not in vehicle_telemetry_store

    def test_oversized_does_not_mutate_twin(self, client):
        """Oversized payload must not reach the Twin."""
        # If Twin is wired, it should have no TRUCK_01 after the attack
        big = {"vehicle_id": "TRUCK_01", "data": "x" * (2 * 1024 * 1024)}
        client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )
        # Twin should have no record from this attack
        from app.main import twin_store
        if twin_store is not None:
            assert twin_store.get_vehicle("TRUCK_01") is None

    def test_ws_connect_after_attack(self, client):
        """A fresh WS client can still connect after an oversized payload attack."""
        big = {"vehicle_id": "TRUCK_01", "data": "x" * (2 * 1024 * 1024)}
        client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )
        # WS must still work
        with client.websocket_connect("/api/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connection_established"
            # D005: vehicles must be empty dict, not raw cache
            assert msg["vehicles"] == {}

    def test_huge_unknown_fields_above_limit_rejected(self, client):
        """A payload with huge unknown fields that exceeds 64KB total is rejected."""
        payload = {
            "vehicle_id": "TRUCK_01",
            "rpm": 240.0,
            "evil_field": "x" * 100000,  # ~100KB
        }
        r = client.post(
            "/api/telemetry",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 413
        assert "TRUCK_01" not in vehicle_telemetry_store


class TestNormalPayloadWorks:

    def test_normal_telemetry_accepted(self, client):
        """Normal <=64 KiB telemetry still works."""
        payload = _normal_payload()
        r = client.post("/api/telemetry", json=payload)
        assert r.status_code == 200
        assert r.json()["status"] == "INGESTED"
        assert "TRUCK_01" in vehicle_telemetry_store

    def test_allowlisted_fields_stored(self, client):
        """Only allowlisted fields are stored in the cache."""
        payload = _normal_payload()
        payload["evil_field"] = "should_not_be_stored"
        payload["another_unknown"] = {"nested": "garbage"}
        r = client.post("/api/telemetry", json=payload)
        assert r.status_code == 200
        stored = vehicle_telemetry_store["TRUCK_01"]
        assert "evil_field" not in stored
        assert "another_unknown" not in stored
        # Known fields are preserved
        assert stored["rpm"] == 240.0
        assert stored["vehicle_id"] == "TRUCK_01"


class TestWSSnapshotSafety:

    def test_ws_snapshot_vehicles_empty(self, client):
        """WS connection snapshot 'vehicles' key is always empty dict (D005)."""
        # Ingest some normal telemetry first
        client.post("/api/telemetry", json=_normal_payload())
        # WS connect
        with client.websocket_connect("/api/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connection_established"
            # D005: vehicles must be empty, never raw cache
            assert msg["vehicles"] == {}

    def test_ws_snapshot_never_contains_raw_payload(self, client):
        """Even after normal telemetry, WS snapshot must not contain raw cache content."""
        payload = _normal_payload()
        payload["evil"] = "attacker_data"
        client.post("/api/telemetry", json=payload)

        with client.websocket_connect("/api/ws") as ws:
            msg = ws.receive_json()
            snapshot_str = json.dumps(msg)
            assert "attacker_data" not in snapshot_str

    def test_2mb_attacker_payload_not_in_ws_snapshot(self, client):
        """Prove a 2 MB adversarial payload cannot appear anywhere in the WS snapshot."""
        attack_marker = "ATTACK_MARKER_" + "x" * 1000
        big = {"vehicle_id": "TRUCK_01", "data": attack_marker * 1000}
        client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )
        with client.websocket_connect("/api/ws") as ws:
            msg = ws.receive_json()
            snapshot_str = json.dumps(msg)
            assert "ATTACK_MARKER_" not in snapshot_str
