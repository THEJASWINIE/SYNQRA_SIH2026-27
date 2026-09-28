"""
D004 — HTTP status codes for rejection responses.

Verifies:
- duplicate → 409
- out-of-order → 409
- mock overwrite attempt → 409
- accepted → 200
- JSON body shape preserved (existing tests depend on it)
"""

import json
import sys
import os
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))

from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _hw_payload(vehicle_id="TRUCK_01", seq=1, source="DIRECT_WIFI", rpm=240.0):
    return {
        "vehicle_id": vehicle_id,
        "sequence": seq,
        "rpm": rpm,
        "speed": 0.0,
        "ax": 0, "ay": 0, "az": 16384,
        "gx": 0, "gy": 0, "gz": 0,
        "rssi": -75, "snr": 9.5,
        "source": source,
    }


class TestAcceptedReturns200:

    def test_first_packet_accepted_200(self, client):
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        assert r.status_code == 200
        assert r.json()["status"] == "ACCEPTED"

    def test_new_sequence_accepted_200(self, client):
        client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=2))
        assert r.status_code == 200
        assert r.json()["status"] == "ACCEPTED"


class TestDuplicateReturns409:

    def test_duplicate_returns_409(self, client):
        client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        assert r.status_code == 409
        body = r.json()
        assert body["status"] == "ACCEPTED_DUPLICATE"
        assert body["is_duplicate"] is True
        assert body["vehicle_id"] == "TRUCK_01"

    def test_duplicate_body_shape_preserved(self, client):
        """Existing tests depend on the body shape. Verify keys."""
        client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        body = r.json()
        assert "status" in body
        assert "vehicle_id" in body
        assert "sequence" in body
        assert "source" in body
        assert "is_duplicate" in body


class TestOutOfOrderReturns409:

    def test_out_of_order_returns_409(self, client):
        client.post("/api/hardware/telemetry", json=_hw_payload(seq=10))
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=5))
        assert r.status_code == 409
        body = r.json()
        assert body["status"] == "REJECTED_OUT_OF_ORDER"
        assert body["is_duplicate"] is False

    def test_out_of_order_body_shape_preserved(self, client):
        client.post("/api/hardware/telemetry", json=_hw_payload(seq=10))
        r = client.post("/api/hardware/telemetry", json=_hw_payload(seq=5))
        body = r.json()
        assert "status" in body
        assert "vehicle_id" in body
        assert "sequence" in body
        assert "last_sequence" in body
        assert "message" in body


class TestMockOverwriteReturns409:

    def test_mock_overwrite_returns_409(self, client):
        # First, ingest a LIVE hardware packet
        r1 = client.post("/api/hardware/telemetry", json=_hw_payload(seq=1))
        assert r1.status_code == 200

        # Mark it as LIVE in the store
        vehicle_telemetry_store["TRUCK_01"]["data_quality"] = "LIVE"
        vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time()

        # Now try to overwrite with mock telemetry
        mock_payload = {
            "vehicle_id": "TRUCK_01",
            "rpm": 100.0,
            "speed": 1.0,
            "timestamp": time.time(),
        }
        r2 = client.post("/api/telemetry", json=mock_payload)
        assert r2.status_code == 409
        body = r2.json()
        assert body["status"] == "IGNORED_MOCK_OVERWRITE"
