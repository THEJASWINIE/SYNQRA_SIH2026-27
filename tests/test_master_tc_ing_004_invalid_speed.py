"""
TC-ING-004: Master Prompt Requirement — Invalid Speed Type Handling

Requirements:
- A malformed/non-numeric speed supplied where speed is expected must be rejected at the ingestion boundary.
- No cache mutation.
- No Twin mutation.
- No broadcast.
- No fabricated zero/unavailable replacement for this test path.
- Return appropriate 4xx semantic.
- Preserve valid numeric speed behavior.
- Preserve missing optional speed behavior if the field is genuinely absent.

Tests:
1. string speed -> rejected
2. list speed -> rejected
3. object/dict speed -> rejected
4. NaN speed -> rejected
5. +Inf speed -> rejected
6. -Inf speed -> rejected
7. valid 0.0 speed -> valid
8. absent optional speed -> valid and preserved as unavailable (None)
"""

import math
import pytest
from fastapi.testclient import TestClient

from telemetry_ingest import (
    TelemetryIngestor,
    Transport,
    REJECT_BAD_SPEED,
    REJECT_NON_FINITE,
)
from twin.twin_state_store import TwinStateStore, TwinMode, UNAVAILABLE


@pytest.fixture
def store():
    return TwinStateStore(mode=TwinMode.HYBRID)


@pytest.fixture
def ingestor(store):
    return TelemetryIngestor(store)


def base_payload(vehicle_id="TRUCK_01", seq=1, **kwargs):
    rec = {
        "vehicle_id": vehicle_id,
        "sequence_number": seq,
        "rpm": 150.0,
        "acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
        "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
    }
    rec.update(kwargs)
    return rec


class TestMasterTCING004InvalidSpeed:
    """Rigorous boundary tests for TC-ING-004."""

    @pytest.mark.parametrize("bad_speed", ["hello", "fast", "", "   ", "12.5mps"])
    def test_string_speed_is_rejected_at_ingestor(self, ingestor, store, bad_speed):
        payload = base_payload(speed=bad_speed)
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert not result.accepted, f"Expected rejection for string speed '{bad_speed}'"
        assert result.reason == REJECT_BAD_SPEED
        # Assert Twin has not been mutated
        assert store.get_vehicle("TRUCK_01") is None

    def test_list_speed_is_rejected_at_ingestor(self, ingestor, store):
        payload = base_payload(speed=[12.5])
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert not result.accepted
        assert result.reason == REJECT_BAD_SPEED
        assert store.get_vehicle("TRUCK_01") is None

    def test_dict_speed_is_rejected_at_ingestor(self, ingestor, store):
        payload = base_payload(speed={"value": 12.5})
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert not result.accepted
        assert result.reason == REJECT_BAD_SPEED
        assert store.get_vehicle("TRUCK_01") is None

    def test_boolean_speed_is_rejected_at_ingestor(self, ingestor, store):
        # In python bool is a subclass of int (True == 1)
        payload = base_payload(speed=True)
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert not result.accepted
        assert result.reason == REJECT_BAD_SPEED
        assert store.get_vehicle("TRUCK_01") is None

    @pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_speed_is_rejected_at_ingestor(self, ingestor, store, non_finite):
        payload = base_payload(speed=non_finite)
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert not result.accepted
        assert result.reason == REJECT_NON_FINITE
        assert store.get_vehicle("TRUCK_01") is None

    def test_valid_zero_speed_is_accepted(self, ingestor, store):
        payload = base_payload(speed=0.0)
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert result.accepted
        veh = store.get_vehicle("TRUCK_01")
        assert veh is not None
        speed_field = store.get_vehicle_field("TRUCK_01", "speed_mps_reported")
        assert speed_field.is_available
        assert speed_field.value == 0.0

    def test_absent_optional_speed_is_accepted_as_unavailable(self, ingestor, store):
        # Speed not provided in payload
        payload = base_payload()
        assert "speed" not in payload
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert result.accepted
        veh = store.get_vehicle("TRUCK_01")
        assert veh is not None
        # Must stay UNAVAILABLE - not fabricated to 0.0
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported") is UNAVAILABLE

    def test_explicit_none_speed_is_accepted_as_unavailable(self, ingestor, store):
        # Speed explicitly null
        payload = base_payload(speed=None)
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        assert result.accepted
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported") is UNAVAILABLE


class TestMasterTCING004HttpEndpoint:
    """Verify HTTP API boundaries reject malformed speed before cache/Twin/WS mutation."""

    @pytest.fixture(autouse=True)
    def setup_backend(self):
        import sys
        import os
        backend_dir = os.path.join(os.getcwd(), "SYNQRA_SIH2026-27-HMI", "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from app.main import app, vehicle_telemetry_store, twin_store
        self.app = app
        self.cache = vehicle_telemetry_store
        self.twin = twin_store
        self.client = TestClient(app)
        self.cache.clear()
        if self.twin is not None:
            with self.twin._lock:
                self.twin._vehicles.clear()
        yield
        self.cache.clear()
        if self.twin is not None:
            with self.twin._lock:
                self.twin._vehicles.clear()

    def test_api_telemetry_rejects_string_speed_with_400(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "speed": "hello",
            "rpm": 120.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        assert res.status_code == 400
        assert "Invalid speed" in res.json()["detail"]
        assert "TRUCK_01" not in self.cache

    def test_api_telemetry_rejects_list_speed_with_400(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "speed": [12.0],
            "rpm": 120.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        assert res.status_code == 400
        assert "TRUCK_01" not in self.cache

    def test_api_telemetry_rejects_dict_speed_with_400(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "speed": {"val": 12.0},
            "rpm": 120.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        assert res.status_code == 400
        assert "TRUCK_01" not in self.cache

    def test_api_telemetry_accepts_absent_speed(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "rpm": 120.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        assert res.status_code == 200
        assert "TRUCK_01" in self.cache
        assert "speed" not in self.cache["TRUCK_01"]

    def test_api_telemetry_accepts_valid_zero_speed(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "speed": 0.0,
            "rpm": 0.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        assert res.status_code == 200
        assert "TRUCK_01" in self.cache
        assert self.cache["TRUCK_01"]["speed"] == 0.0

    def test_api_hardware_telemetry_rejects_string_speed(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "sequence": 101,
            "source": "DIRECT_WIFI",
            "rpm": 200.0,
            "speed": "hello"
        }
        res = self.client.post("/api/hardware/telemetry", json=payload)
        assert res.status_code == 422
        assert "TRUCK_01" not in self.cache
