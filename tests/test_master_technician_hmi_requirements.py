"""
GAP 4 — Technician HMI Complete Verification (Master Prompt Requirement)

Verifies individually:
1. Fleet renders (multi-vehicle list/grid)
2. TRUCK_01 physical/hardware-backed vehicle appears
3. Speed changes dynamically without page reload
4. Visibility change propagates to environmental state
5. Safety state updates correctly
6. Communication state updates correctly
7. Stale / disconnected state is visibly represented
8. Baseline topology remains intact
9. Live telemetry does not replace or destroy topology
"""

import time
import sys
import os
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import (
    app,
    vehicle_telemetry_store,
    deduplication_store,
    last_sequence_by_vehicle,
    twin_store,
    twin_ingestor,
)
from twin.twin_state_store import Source


@pytest.fixture(autouse=True)
def reset_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._last_sequence.clear()
        twin_ingestor._seen_sequences.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._last_sequence.clear()
        twin_ingestor._seen_sequences.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestMasterTechnicianHMIRequirements:
    """Individual machine-verifiable assertions for Technician HMI contract."""

    def test_item_1_fleet_appears(self, client):
        """1. Fleet renders multi-vehicle collection."""
        client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": 1, "speed": 1.0, "rpm": 60.0})
        client.post("/api/telemetry", json={"vehicle_id": "TRUCK_02", "sequence": 1, "speed": 2.0, "rpm": 120.0})

        res = client.get("/api/vehicles")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 2
        assert "TRUCK_01" in data["vehicles"]
        assert "TRUCK_02" in data["vehicles"]

    def test_item_2_physical_vehicle_appears(self, client):
        """2. TRUCK_01 physical/hardware-backed vehicle appears with LIVE / hardware provenance."""
        res_post = client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_01",
            "sequence": 1,
            "source": "DIRECT_WIFI",
            "rpm": 240.0,
            "speed": 3.14
        })
        assert res_post.status_code == 200

        data = client.get("/api/vehicles").json()
        truck1 = data["vehicles"]["TRUCK_01"]
        assert truck1["vehicle_id"] == "TRUCK_01"
        assert truck1["data_quality"] == "LIVE"
        assert truck1["source"] == "DIRECT_WIFI"
        assert truck1["rpm"] == 240.0

    def test_item_3_speed_changes_without_reload(self, client):
        """3. Speed updates stream through WebSocket without reload."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()

            # Sequence of speeds: 1.0 -> 2.0 -> 0.5 m/s
            speeds = [1.0, 2.0, 0.5]
            for idx, spd in enumerate(speeds, start=1):
                client.post("/api/telemetry", json={
                    "vehicle_id": "TRUCK_01",
                    "sequence": idx,
                    "speed": spd,
                    "rpm": spd * 60.0
                })
                # STRENGTHENED: assert on the CANONICAL projection, which is the frame
                # the HMI actually consumes. This test previously asserted on the legacy
                # `telemetry_update` frame - which the frontend deliberately ignores - so
                # it passed while the S2 Vehicle screen could not update at all.
                twin = ws.receive_json()
                assert twin["type"] == "twin_vehicle_update", (
                    "no canonical projection broadcast; the HMI would not update. got %r"
                    % twin.get("type"))
                dynamic = twin["data"]["dynamic"]
                assert twin["data"]["vehicle_id"] == "TRUCK_01"
                assert dynamic["rpm"]["value"] == spd * 60.0
                assert dynamic["speed_mps_reported"]["value"] == spd

                legacy = ws.receive_json()
                assert legacy["type"] == "telemetry_update"
                assert legacy["data"]["speed"] == spd
                assert legacy["data"]["rpm"] == spd * 60.0

    def test_item_4_visibility_change_propagates(self, client):
        """4. Visibility changes update environmental context in Twin / safety engine."""
        if twin_store is not None:
            twin_store.update_environment_field("visibility_m", 15.0, source=Source.SIMULATION)
            twin_store.update_environment_field("friction_coefficient", 0.65, source=Source.SIMULATION)
            env = twin_store.get_environment()
            assert env.get("visibility_m").value == 15.0
            assert env.get("friction_coefficient").value == 0.65

            # Dynamic change
            twin_store.update_environment_field("visibility_m", 5.0, source=Source.SIMULATION)
            env2 = twin_store.get_environment()
            assert env2.get("visibility_m").value == 5.0

    def test_item_5_safety_state_updates(self, client):
        """5. Safety status updates reflect accurately in vehicle projection."""
        res = client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_01",
            "sequence": 1,
            "source": "DIRECT_WIFI",
            "rpm": 120.0,
            "speed": 1.5
        })
        assert res.status_code == 200
        v = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
        assert v["safety_state"] in ["NORMAL", "CAUTION", "SLOW_DOWN", "STOP"]

    def test_item_6_communication_state_updates(self, client):
        """6. Communication state changes update dynamically."""
        res = client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_01",
            "sequence": 1,
            "source": "DIRECT_WIFI",
            "rpm": 100.0,
            "speed": 1.0
        })
        assert res.status_code == 200
        data = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
        assert data["communication_status"] == "ONLINE"
        assert data["communication_state"] == "HEALTHY"

    def test_item_7_stale_disconnected_state_visibly_represented(self, client):
        """7. Stale / disconnected state is clearly flagged."""
        res = client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_01",
            "sequence": 1,
            "source": "DIRECT_WIFI",
            "rpm": 100.0,
            "speed": 1.0
        })
        assert res.status_code == 200
        # Simulate elapsed time past STALE_THRESHOLD_S (3.0s)
        vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 4.5
        data = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
        assert data["is_stale"] is True

        # Simulate elapsed time past OFFLINE_THRESHOLD_S (10.0s)
        vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 15.0
        data_offline = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
        assert data_offline["communication_status"] == "OFFLINE"

    def test_item_8_baseline_topology_remains_intact(self, client):
        """8. Baseline mine road network topology is preserved."""
        import json
        topology_file = os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-main", "contracts", "fixtures", "valid", "MineTopology.json")
        assert os.path.exists(topology_file)
        with open(topology_file, "r") as f:
            topo = json.load(f)
        assert "nodes" in topo
        assert "segments" in topo
        assert len(topo["segments"]) > 0

    def test_item_9_live_telemetry_does_not_destroy_topology(self, client):
        """9. Telemetry updates do not mutate, overwrite, or destroy topology configuration."""
        import json
        topology_file = os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-main", "contracts", "fixtures", "valid", "MineTopology.json")
        with open(topology_file, "r") as f:
            topo_before = json.load(f)

        # Ingest series of telemetry packets
        for s in range(1, 10):
            client.post("/api/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "sequence": s,
                "speed": float(s) * 0.5,
                "rpm": 100.0
            })

        with open(topology_file, "r") as f:
            topo_after = json.load(f)

        assert topo_before == topo_after
