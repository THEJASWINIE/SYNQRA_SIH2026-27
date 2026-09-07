"""
D007 — Twin consistency for /api/vehicles and /api/twin/vehicles/{id}.

Proves:
1. /api/vehicles and /api/twin/vehicles/{id} never disagree on communication_state.
2. The canonical Twin projection is authoritative whenever twin_store exists; cache is not.
3. Deliberately conflicting:
   - cache communication_state = "HEALTHY" vs Twin = "COMMUNICATION_DEGRADED" -> API returns Twin state.
   - cache communication_state = "COMMUNICATION_DEGRADED" vs Twin = "HEALTHY" -> API returns Twin state.
4. When Twin is unavailable, cache provides fallback compatibility.
"""

import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))

import app.main as backend
from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle, twin_store

# Import domain Source for Twin updates
try:
    from twin.twin_state_store import Source
except ImportError:
    from twin_state_store import Source


@pytest.fixture(autouse=True)
def reset_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if getattr(backend, "twin_ingestor", None) is not None:
        backend.twin_ingestor._last_sequence.clear()
        backend.twin_ingestor._seen_sequences.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if getattr(backend, "twin_ingestor", None) is not None:
        backend.twin_ingestor._last_sequence.clear()
        backend.twin_ingestor._seen_sequences.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _populate_cache_vehicle(vehicle_id: str, comm_state: str, comm_status: str = "ONLINE"):
    now = time.time()
    vehicle_telemetry_store[vehicle_id] = {
        "vehicle_id": vehicle_id,
        "sequence_number": 1,
        "rpm": 240.0,
        "speed": 2.5,
        "speed_mps": 2.5,
        "communication": {
            "status": comm_status,
            "last_seen": now,
            "rssi": -75,
            "snr": 10.0,
        },
        "communication_status": comm_status,
        "communication_state": comm_state,
        "safety_state": "NORMAL",
        "data_quality": "LIVE",
        "stale_threshold_s": 3.0,
        "offline_threshold_s": 10.0,
        "timestamp": now,
        "received_at": now,
    }


def _populate_twin_vehicle(vehicle_id: str, comm_state: str):
    twin_store.register_vehicle(vehicle_id)
    twin_store.update_vehicle_field(
        vehicle_id=vehicle_id,
        name="communication_state",
        value=comm_state,
        source=Source.DERIVED,
        timestamp=time.time(),
    )


class TestDefect007TwinConsistency:

    def test_conflict_cache_healthy_twin_degraded(self, client):
        """
        When cache says HEALTHY but Twin says COMMUNICATION_DEGRADED:
        Both /api/vehicles and /api/twin/vehicles/{id} must return COMMUNICATION_DEGRADED.
        The backend cache is NOT authoritative.
        """
        vid = "TRUCK_01"
        _populate_cache_vehicle(vid, comm_state="HEALTHY", comm_status="ONLINE")
        _populate_twin_vehicle(vid, comm_state="COMMUNICATION_DEGRADED")

        # 1. Query /api/vehicles
        res_vehicles = client.get("/api/vehicles")
        assert res_vehicles.status_code == 200
        v_data = res_vehicles.json()["vehicles"][vid]
        assert v_data["communication_state"] == "COMMUNICATION_DEGRADED", (
            f"Expected Twin state 'COMMUNICATION_DEGRADED', got '{v_data['communication_state']}'"
        )

        # 2. Query /api/twin/vehicles/{vid}
        res_twin = client.get(f"/api/twin/vehicles/{vid}")
        assert res_twin.status_code == 200
        twin_data = res_twin.json()
        assert twin_data["dynamic"]["communication_state"]["value"] == "COMMUNICATION_DEGRADED"

        # 3. Invariant: Both must agree on the canonical Twin state
        assert v_data["communication_state"] == twin_data["dynamic"]["communication_state"]["value"]

    def test_conflict_cache_degraded_twin_healthy(self, client):
        """
        When cache says COMMUNICATION_DEGRADED but Twin says HEALTHY:
        Both /api/vehicles and /api/twin/vehicles/{id} must return HEALTHY.
        """
        vid = "TRUCK_01"
        _populate_cache_vehicle(vid, comm_state="COMMUNICATION_DEGRADED", comm_status="STALE")
        _populate_twin_vehicle(vid, comm_state="HEALTHY")

        res_vehicles = client.get("/api/vehicles")
        assert res_vehicles.status_code == 200
        v_data = res_vehicles.json()["vehicles"][vid]
        assert v_data["communication_state"] == "HEALTHY", (
            f"Expected Twin state 'HEALTHY', got '{v_data['communication_state']}'"
        )

        res_twin = client.get(f"/api/twin/vehicles/{vid}")
        assert res_twin.status_code == 200
        twin_data = res_twin.json()
        assert twin_data["dynamic"]["communication_state"]["value"] == "HEALTHY"

        assert v_data["communication_state"] == twin_data["dynamic"]["communication_state"]["value"]

    def test_fallback_when_twin_unavailable(self, client, monkeypatch):
        """
        When twin_store is genuinely unavailable (None), /api/vehicles must fall back
        to cache state rather than erroring.
        """
        vid = "TRUCK_01"
        _populate_cache_vehicle(vid, comm_state="HEALTHY", comm_status="ONLINE")

        monkeypatch.setattr(backend, "twin_store", None)

        res_vehicles = client.get("/api/vehicles")
        assert res_vehicles.status_code == 200
        v_data = res_vehicles.json()["vehicles"][vid]
        assert v_data["communication_state"] == "HEALTHY"

        # Twin endpoint should report 503 when Twin is unavailable
        res_twin = client.get(f"/api/twin/vehicles/{vid}")
        assert res_twin.status_code == 503

    def test_telemetry_ingestion_aligns_both_endpoints(self, client):
        """
        After posting telemetry through the API, both /api/vehicles and /api/twin/vehicles/{id}
        must reflect the canonical state consistently.
        """
        vid = "TRUCK_01"
        payload = {
            "vehicle_id": vid,
            "sequence_number": 1,
            "rpm": 180.0,
            "speed": 1.8,
            "communication_state": "HEALTHY",
            "communication_status": "ONLINE",
            "timestamp": time.time(),
        }
        post_res = client.post("/api/telemetry", json=payload)
        assert post_res.status_code == 200

        res_vehicles = client.get("/api/vehicles").json()
        res_twin = client.get(f"/api/twin/vehicles/{vid}").json()

        v_comm = res_vehicles["vehicles"][vid]["communication_state"]
        twin_comm = res_twin["dynamic"]["communication_state"]["value"]
        assert v_comm == twin_comm == "HEALTHY"

    def test_twin_exists_projection_succeeds_returns_twin_state(self, client):
        """
        Twin exists + projection succeeds -> Twin state is returned.
        """
        vid = "TRUCK_01"
        _populate_cache_vehicle(vid, comm_state="HEALTHY", comm_status="ONLINE")
        _populate_twin_vehicle(vid, comm_state="COMMUNICATION_DEGRADED")

        res = client.get("/api/vehicles")
        assert res.status_code == 200
        v_data = res.json()["vehicles"][vid]
        assert v_data["communication_state"] == "COMMUNICATION_DEGRADED"

    def test_twin_exists_projection_raises_does_not_substitute_cache(self, client, monkeypatch):
        """
        Twin exists + projection raises -> cache value is NOT silently substituted.
        Surfaces projection failure and returns safe deterministic degraded state.
        """
        vid = "TRUCK_01"
        _populate_cache_vehicle(vid, comm_state="HEALTHY", comm_status="ONLINE")
        _populate_twin_vehicle(vid, comm_state="HEALTHY")

        def _exploding_projection(*args, **kwargs):
            raise RuntimeError("Authoritative Twin projection failed unexpectedly")

        monkeypatch.setattr(backend, "build_vehicle_projection", _exploding_projection)

        res_vehicles = client.get("/api/vehicles")
        assert res_vehicles.status_code == 200
        v_data = res_vehicles.json()["vehicles"][vid]

        # Invariant: Must NOT silently substitute or retain cached "HEALTHY" value
        assert v_data["communication_state"] != "HEALTHY"
        assert v_data["communication_state"] == "COMMUNICATION_DEGRADED"
        assert v_data["communication_status"] in ("STALE", "OFFLINE")
        assert v_data["is_stale"] is True
        assert v_data["safety_state"] == "COMMUNICATION_DEGRADED"
        assert v_data["communication"]["status"] in ("STALE", "OFFLINE")

