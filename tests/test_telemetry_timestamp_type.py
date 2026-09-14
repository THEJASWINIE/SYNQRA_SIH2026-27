"""
Telemetry timestamp type validation.

`TelemetryPayload.timestamp` is unix epoch seconds (float). A packet that carried an
ISO-8601 string instead was accepted by POST /api/telemetry, cached as-is, and then made
GET /api/vehicles raise `TypeError: unsupported operand type(s) for -: 'float' and 'str'`
- one malformed packet breaking a fleet endpoint for everyone (CLAUDE.md §16).

Verifies:
- string timestamp -> 400, nothing cached, /api/vehicles still 200
- non-finite timestamp -> 400
- numeric timestamp -> 200 and /api/vehicles reports the vehicle
"""
import math
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))
from app.main import app, deduplication_store, last_sequence_by_vehicle, vehicle_telemetry_store  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def reset_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _payload(**overrides):
    body = {"vehicle_id": "TRUCK_02", "sequence": 1, "rpm": 1200.0, "speed": 6.7}
    body.update(overrides)
    return body


class TestTimestampType:
    def test_iso_string_timestamp_rejected_and_nothing_cached(self, client):
        r = client.post("/api/telemetry", json=_payload(timestamp="2026-09-11T10:00:00Z"))
        assert r.status_code == 400
        assert "timestamp" in r.json()["detail"]
        assert "TRUCK_02" not in vehicle_telemetry_store
        # The fleet endpoint must survive the bad packet.
        assert client.get("/api/vehicles").status_code == 200

    def test_source_timestamp_string_rejected(self, client):
        r = client.post("/api/telemetry", json=_payload(source_timestamp="yesterday"))
        assert r.status_code == 400

    @pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan, True])
    def test_non_finite_or_bool_timestamp_rejected(self, client, bad):
        # json cannot carry inf/nan; send as a raw body the way a buggy client would.
        import json as _json

        body = _json.dumps(_payload(timestamp=bad))
        r = client.post("/api/telemetry", content=body, headers={"content-type": "application/json"})
        assert r.status_code == 400

    def test_numeric_timestamp_accepted_and_listed(self, client):
        r = client.post("/api/telemetry", json=_payload(timestamp=time.time()))
        assert r.status_code == 200
        fleet = client.get("/api/vehicles")
        assert fleet.status_code == 200
        assert "TRUCK_02" in fleet.json()["vehicles"]
