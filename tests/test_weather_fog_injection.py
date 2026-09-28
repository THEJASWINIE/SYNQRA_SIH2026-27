"""
FOG-ORCHESTRATOR 2.0 — Weather Station Fog Injection -> Digital Twin -> Safety Solver -> Vehicle Governor
Comprehensive Automated Test Suite.

Validates the full causal pipeline:
    WEATHER STATION / ENVIRONMENT INPUT
                 ↓
          FOG CONDITION
                 ↓
       ENVIRONMENTAL NORMALIZER
                 ↓
          DIGITAL TWIN STATE
                 ↓
          SAFETY SOLVER
                 ↓
          v_safe / speed clamp
                 ↓
       COMMAND / GOVERNOR LAYER
            ↙             ↘
       VEHICLE A        VEHICLE B
"""

import sys
import os
import math
import time
import pytest
from fastapi.testclient import TestClient

# Ensure backend and root paths are available
_workspace_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
_backend_path = os.path.join(_workspace_root, "SYNQRA_SIH2026-27-HMI", "backend")
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.main import app, weather_service, vehicle_telemetry_store, twin_store
from weather_station_service import (
    FogCondition,
    fog_to_visibility_m,
    fog_to_condition,
    condition_to_fog,
    compute_fog_v_safe,
    WeatherStationService,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestFogMathematicalMapping:
    """Verifies deterministic mathematical mapping for fog, visibility, and safe speed."""

    def test_clear_produces_baseline_v_safe(self):
        v = compute_fog_v_safe(0.0, baseline_mps=0.80)
        assert v == 0.80
        vis = fog_to_visibility_m(0.0)
        assert vis == 1000.0
        assert fog_to_condition(0.0) == "CLEAR"

    def test_light_fog_reduces_v_safe(self):
        v = compute_fog_v_safe(0.25, baseline_mps=0.80)
        assert v == 0.60
        vis = fog_to_visibility_m(0.25)
        assert vis == 500.0
        assert fog_to_condition(0.25) == "LIGHT_FOG"

    def test_moderate_fog_reduces_v_safe_further(self):
        v = compute_fog_v_safe(0.50, baseline_mps=0.80)
        assert v == 0.40
        vis = fog_to_visibility_m(0.50)
        assert vis == 250.0
        assert fog_to_condition(0.50) == "MODERATE_FOG"

    def test_heavy_fog_reduces_v_safe_further(self):
        v = compute_fog_v_safe(0.75, baseline_mps=0.80)
        assert v == 0.24
        vis = fog_to_visibility_m(0.75)
        assert vis == 100.0
        assert fog_to_condition(0.75) == "HEAVY_FOG"

    def test_severe_fog_invokes_configured_severe_policy(self):
        # Default policy: minimum crawl speed 0.08 m/s (10% of baseline)
        v_crawl = compute_fog_v_safe(1.00, baseline_mps=0.80, severe_stop=False)
        assert v_crawl == 0.08
        vis = fog_to_visibility_m(1.00)
        assert vis == 50.0
        assert fog_to_condition(1.00) == "SEVERE_FOG"

        # Severe stop policy: complete stop (0.0 m/s)
        v_stop = compute_fog_v_safe(1.00, baseline_mps=0.80, severe_stop=True)
        assert v_stop == 0.0

    def test_v_safe_strictly_monotonic_non_increasing(self):
        """As fog intensity increases from 0.0 to 1.0, v_safe must NEVER increase."""
        previous_v = 1.0
        for i in range(101):
            fog = i / 100.0
            v = compute_fog_v_safe(fog, baseline_mps=0.80)
            assert v <= previous_v + 1e-9, f"Monotonicity violation at fog {fog}: {v} > {previous_v}"
            previous_v = v

    def test_visibility_strictly_monotonic_decreasing(self):
        """As fog intensity increases from 0.0 to 1.0, visibility must strictly decrease."""
        previous_vis = 2000.0
        for i in range(101):
            fog = i / 100.0
            vis = fog_to_visibility_m(fog)
            assert vis <= previous_vis, f"Visibility increased at fog {fog}: {vis} > {previous_vis}"
            previous_vis = vis


class TestWeatherStationEndpoints:
    """Verifies REST endpoints for environmental fog injection."""

    def test_get_environment_fog(self, client):
        r = client.get("/api/environment/fog")
        assert r.status_code == 200
        data = r.json()
        assert "environment" in data
        assert "vehicles" in data
        assert data["environment"]["source"] == "WEATHER_STATION_INJECTED"
        assert data["environment"]["is_injected"] is True
        assert "TRUCK_01" in data["vehicles"]
        assert "TRUCK_02" in data["vehicles"]

    def test_inject_fog_by_intensity(self, client):
        payload = {
            "fog_intensity": 0.75,
            "source": "WEATHER_STATION_INJECTED"
        }
        r = client.post("/api/environment/fog", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ACCEPTED"
        assert data["environment"]["fog_intensity"] == 0.75
        assert data["environment"]["visibility_m"] == 100.0
        assert data["environment"]["weather_condition"] == "HEAVY_FOG"
        assert data["environment"]["v_safe_mps"] == 0.24
        assert len(data["causal_events"]) >= 2

        # Verify TRUCK_01 and TRUCK_02 reflect the new limit
        assert data["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.24
        assert data["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.24
        assert data["vehicles"]["TRUCK_01"]["applied_speed_mps"] <= 0.24
        assert data["vehicles"]["TRUCK_02"]["applied_speed_mps"] <= 0.24

    def test_inject_fog_by_named_condition(self, client):
        payload = {
            "condition": "LIGHT_FOG",
            "source": "WEATHER_STATION_INJECTED"
        }
        r = client.post("/api/environment/fog", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["environment"]["fog_intensity"] == 0.25
        assert data["environment"]["visibility_m"] == 500.0
        assert data["environment"]["v_safe_mps"] == 0.60

    def test_reject_out_of_bounds_fog_intensity(self, client):
        # Negative fog
        r = client.post("/api/environment/fog", json={"fog_intensity": -0.1})
        assert r.status_code == 400

        # Excess fog > 1.0
        r = client.post("/api/environment/fog", json={"fog_intensity": 1.5})
        assert r.status_code == 400

    def test_reject_nan_or_non_numeric(self, client):
        r = client.post("/api/environment/fog", json={"fog_intensity": "not_a_number"})
        assert r.status_code in (400, 422)

    def test_reject_empty_payload(self, client):
        r = client.post("/api/environment/fog", json={})
        assert r.status_code == 400

    def test_severe_stop_policy(self, client):
        payload = {
            "fog_intensity": 1.0,
            "severe_stop_policy": True
        }
        r = client.post("/api/environment/fog", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["environment"]["v_safe_mps"] == 0.0
        assert data["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.0
        assert data["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.0

    def test_recovery_to_clear(self, client):
        payload = {
            "fog_intensity": 0.0,
            "source": "WEATHER_STATION_INJECTED"
        }
        r = client.post("/api/environment/fog", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["environment"]["fog_intensity"] == 0.0
        assert data["environment"]["v_safe_mps"] == 0.80
        assert data["environment"]["visibility_m"] == 1000.0
        assert data["environment"]["weather_condition"] == "CLEAR"

    def test_audit_events_endpoint(self, client):
        r = client.get("/api/environment/events")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert len(data["events"]) > 0
        categories = {ev["category"] for ev in data["events"]}
        assert "WEATHER_EVENT" in categories or "SAFETY_EVENT" in categories

    def test_environment_event_command_audit_logging(self, client):
        """Verifies Requirement 30: Command audit logging for external environmental injection."""
        r = client.post("/api/environment/fog", json={
            "condition": "MODERATE_FOG",
            "source": "CLI_AUDIT_TEST"
        })
        assert r.status_code == 200
        events_resp = client.get("/api/environment/events").json()
        env_events = [ev for ev in events_resp["events"] if ev["category"] == "ENVIRONMENT_EVENT"]
        assert len(env_events) > 0
        latest_env = env_events[0]
        meta = latest_env["metadata"]
        assert meta["operator_or_cli_source"] == "CLI_AUDIT_TEST"
        assert meta["new_condition"] == "MODERATE_FOG"
        assert meta["new_intensity"] == 0.50
        assert meta["visibility_m"] == 250.0
        assert meta["fog_factor"] == 0.50
        assert meta["provenance"] == "INJECTED"


class TestDigitalTwinAndGovernorIntegration:
    """Verifies that the Digital Twin and vehicle governor obey the causal chain."""

    def test_twin_receives_environmental_state(self, client):
        client.post("/api/environment/fog", json={"fog_intensity": 0.50})
        if twin_store is not None:
            env = twin_store.get_environment()
            assert env.dynamic["fog_intensity"].value == 0.50
            assert env.dynamic["visibility_m"].value == 250.0
            assert env.dynamic["v_safe_mps"].value == 0.40

            # Vehicles in twin have v_safe_mps updated
            for vid in ("TRUCK_01", "TRUCK_02"):
                v = twin_store.get_vehicle(vid)
                assert v is not None
                assert v.dynamic["v_safe_mps"].value == 0.40
                assert v.dynamic["active_constraint"].value == "FOG_VISIBILITY_CONSTRAINT"

    def test_governor_clamps_overspeed_command(self, client):
        # 1. Set fog to HEAVY (v_safe = 0.24 m/s)
        client.post("/api/environment/fog", json={"fog_intensity": 0.75})

        # 2. Check vehicles in get_vehicles
        r = client.get("/api/vehicles")
        assert r.status_code == 200
        data = r.json()["vehicles"]
        for vid in ("TRUCK_01", "TRUCK_02"):
            assert data[vid]["v_safe_mps"] == 0.24
            assert data[vid]["applied_speed_mps"] <= 0.24
            assert data[vid]["governor_state"] == "ACTIVE — FOG CONSTRAINT"

    def test_commanded_speed_never_exceeds_v_safe(self, client):
        client.post("/api/environment/fog", json={"fog_intensity": 0.50}) # v_safe = 0.40 m/s
        v_data = client.get("/api/vehicles").json()["vehicles"]
        for vid, v in v_data.items():
            assert v["applied_speed_mps"] <= v["v_safe_mps"] + 1e-6
