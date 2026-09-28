"""
FOG-ORCHESTRATOR 2.0 — End-to-End Automated Closed-Loop Integration Test.
Implements Prompt Section 18:
  START:
      fog = 0%, requested speed = 0.80 m/s -> v_safe = 0.80 m/s, applied = 0.80 m/s, governor = NORMAL
  STEP 1:
      inject fog = 25% -> v_safe = 0.60 m/s, applied = 0.60 m/s, governor = ACTIVE — FOG CONSTRAINT
  STEP 2:
      inject fog = 50% -> v_safe = 0.40 m/s, TRUCK_01 & TRUCK_02 applied = 0.40 m/s
  STEP 3:
      inject fog = 75% -> v_safe = 0.24 m/s, both vehicles remain below v_safe
  STEP 4:
      inject fog = 100% (severe) -> severe policy activates (crawl 0.08 m/s or STOP)
  STEP 5:
      return fog = 0% -> safety constraint clears, normal operating command available again.

All transitions are strictly validated and timestamped.
"""

import sys
import os
import time
import pytest
from fastapi.testclient import TestClient

# Path resolution
_workspace_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
_backend_path = os.path.join(_workspace_root, "SYNQRA_SIH2026-27-HMI", "backend")
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.main import app, weather_service, vehicle_telemetry_store, twin_store


@pytest.fixture
def client():
    return TestClient(app)


def test_weather_fog_closed_loop_transition(client):
    timeline = []

    # -------------------------------------------------------------
    # START: Clear conditions (0% fog)
    # -------------------------------------------------------------
    t0 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 0.0, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d0 = r.json()
    assert d0["environment"]["fog_intensity"] == 0.0
    assert d0["environment"]["visibility_m"] == 1000.0
    assert d0["environment"]["v_safe_mps"] == 0.80
    assert d0["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.80
    assert d0["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.80
    assert d0["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.80
    assert d0["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.80
    assert d0["vehicles"]["TRUCK_01"]["governor_state"] == "NORMAL"
    assert d0["vehicles"]["TRUCK_02"]["governor_state"] == "NORMAL"

    timeline.append({
        "step": "START_CLEAR",
        "timestamp": t0,
        "fog": 0.0,
        "visibility_m": 1000.0,
        "v_safe_mps": 0.80,
        "truck01_applied": d0["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d0["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d0["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # STEP 1: Inject LIGHT FOG (25%)
    # -------------------------------------------------------------
    t1 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 0.25, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d1 = r.json()
    assert d1["environment"]["fog_intensity"] == 0.25
    assert d1["environment"]["visibility_m"] == 500.0
    assert d1["environment"]["v_safe_mps"] == 0.60
    assert d1["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.60
    assert d1["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.60
    assert d1["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.60
    assert d1["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.60
    assert d1["vehicles"]["TRUCK_01"]["governor_state"] == "ACTIVE — FOG CONSTRAINT"
    assert d1["vehicles"]["TRUCK_02"]["governor_state"] == "ACTIVE — FOG CONSTRAINT"

    timeline.append({
        "step": "INJECT_LIGHT_FOG_25%",
        "timestamp": t1,
        "fog": 0.25,
        "visibility_m": 500.0,
        "v_safe_mps": 0.60,
        "truck01_applied": d1["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d1["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d1["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # STEP 2: Inject MODERATE FOG (50%)
    # -------------------------------------------------------------
    t2 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 0.50, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d2 = r.json()
    assert d2["environment"]["fog_intensity"] == 0.50
    assert d2["environment"]["visibility_m"] == 250.0
    assert d2["environment"]["v_safe_mps"] == 0.40
    assert d2["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.40
    assert d2["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.40
    assert d2["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.40
    assert d2["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.40

    timeline.append({
        "step": "INJECT_MODERATE_FOG_50%",
        "timestamp": t2,
        "fog": 0.50,
        "visibility_m": 250.0,
        "v_safe_mps": 0.40,
        "truck01_applied": d2["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d2["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d2["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # STEP 3: Inject HEAVY FOG (75%)
    # -------------------------------------------------------------
    t3 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 0.75, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d3 = r.json()
    assert d3["environment"]["fog_intensity"] == 0.75
    assert d3["environment"]["visibility_m"] == 100.0
    assert d3["environment"]["v_safe_mps"] == 0.24
    assert d3["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.24
    assert d3["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.24
    assert d3["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.24
    assert d3["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.24

    timeline.append({
        "step": "INJECT_HEAVY_FOG_75%",
        "timestamp": t3,
        "fog": 0.75,
        "visibility_m": 100.0,
        "v_safe_mps": 0.24,
        "truck01_applied": d3["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d3["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d3["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # STEP 4: Inject SEVERE FOG (100%)
    # -------------------------------------------------------------
    t4 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 1.00, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d4 = r.json()
    assert d4["environment"]["fog_intensity"] == 1.00
    assert d4["environment"]["visibility_m"] == 50.0
    assert d4["environment"]["v_safe_mps"] == 0.08  # Default crawl policy
    assert d4["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.08
    assert d4["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.08

    timeline.append({
        "step": "INJECT_SEVERE_FOG_100%",
        "timestamp": t4,
        "fog": 1.00,
        "visibility_m": 50.0,
        "v_safe_mps": 0.08,
        "truck01_applied": d4["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d4["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d4["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # STEP 5: Recovery to CLEAR (0% fog)
    # -------------------------------------------------------------
    t5 = time.time()
    r = client.post("/api/environment/fog", json={"fog_intensity": 0.0, "source": "WEATHER_STATION_INJECTED"})
    assert r.status_code == 200
    d5 = r.json()
    assert d5["environment"]["fog_intensity"] == 0.0
    assert d5["environment"]["visibility_m"] == 1000.0
    assert d5["environment"]["v_safe_mps"] == 0.80
    assert d5["vehicles"]["TRUCK_01"]["v_safe_mps"] == 0.80
    assert d5["vehicles"]["TRUCK_02"]["v_safe_mps"] == 0.80
    assert d5["vehicles"]["TRUCK_01"]["applied_speed_mps"] == 0.80
    assert d5["vehicles"]["TRUCK_02"]["applied_speed_mps"] == 0.80
    assert d5["vehicles"]["TRUCK_01"]["governor_state"] == "NORMAL"
    assert d5["vehicles"]["TRUCK_02"]["governor_state"] == "NORMAL"

    timeline.append({
        "step": "RECOVERY_CLEAR_0%",
        "timestamp": t5,
        "fog": 0.0,
        "visibility_m": 1000.0,
        "v_safe_mps": 0.80,
        "truck01_applied": d5["vehicles"]["TRUCK_01"]["applied_speed_mps"],
        "truck02_applied": d5["vehicles"]["TRUCK_02"]["applied_speed_mps"],
        "truck01_gov": d5["vehicles"]["TRUCK_01"]["governor_state"],
    })

    # -------------------------------------------------------------
    # Audit trail verification
    # -------------------------------------------------------------
    r_events = client.get("/api/environment/events")
    assert r_events.status_code == 200
    ev_data = r_events.json()
    assert ev_data["count"] >= 10
    categories = [e["category"] for e in ev_data["events"]]
    assert "WEATHER_EVENT" in categories
    assert "SAFETY_EVENT" in categories
    assert "GOVERNOR_EVENT" in categories

    # Verify temporal monotonicity
    for i in range(len(timeline) - 1):
        assert timeline[i + 1]["timestamp"] >= timeline[i]["timestamp"]
