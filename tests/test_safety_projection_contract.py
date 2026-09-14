"""
HMI-SAFETY-01 — canonical safety state contract, backend side.

SOFTWARE ONLY. Safety values written here are TEST-ONLY deterministic fixtures with
source=DERIVED origin=SIMULATION. No solver runs; nothing physical executed.

Pins:
  - the Twin projection carries a safety producer's fields ONLY when a producer wrote
    them (v_safe_mps, safe_headway_m, headway_m, lead_vehicle_id, active_constraint,
    risk_level, headway_violation, envelope_violation) - never defaulted;
  - telemetry alone produces none of them (no producer on the HMI backend path);
  - a solver output keeps source=DERIVED / origin=SIMULATION through the projection;
  - the HMI command path fails closed: TARGET_SPEED is REJECTED while v_safe is
    unavailable, HOLD/STOP keep their behaviour, and the lifecycle vocabulary is intact.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))

from command_gateway import CommandStatus  # noqa: E402
from telemetry_ingest import TelemetryIngestor, Transport  # noqa: E402
from twin.twin_state_store import ClockDomain, Source, Sourced, TwinMode, TwinStateStore  # noqa: E402
from twin_projection import VEHICLE_PROJECTION_FIELDS, build_vehicle_projection  # noqa: E402

SAFETY_FIELDS = (
    "v_safe_mps", "safe_headway_m", "headway_m", "lead_vehicle_id",
    "active_constraint", "risk_level", "headway_violation", "envelope_violation",
)


class FixedClock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def store(clock):
    return TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)


def _telemetry(store, clock):
    ing = TelemetryIngestor(store, clock=clock)
    r = ing.ingest_parsed_record(
        {"vehicle_id": "TRUCK_01", "sequence_number": 1, "rpm": 1528.0, "speed": 8.0},
        transport=Transport.DIRECT_WIFI, is_simulated=True,
    )
    assert r.accepted


def _fixture_safety(clock, **over):
    values = dict(
        v_safe_mps=6.0, safe_headway_m=25.0, headway_m=18.0, lead_vehicle_id="TRUCK_02",
        active_constraint="HEADWAY", risk_level="HIGH", headway_violation=False, envelope_violation=False,
    )
    values.update(over)
    return {
        k: Sourced(value=v, timestamp=clock(), source=Source.DERIVED, origin=Source.SIMULATION,
                   clock_domain=ClockDomain.WALL_CLOCK)
        for k, v in values.items() if v is not None
    }


class TestProjection:
    def test_projection_declares_every_safety_field(self):
        for name in SAFETY_FIELDS:
            assert name in VEHICLE_PROJECTION_FIELDS, name

    def test_telemetry_alone_yields_no_safety_fields(self, store, clock):
        _telemetry(store, clock)
        dynamic = build_vehicle_projection(store, "TRUCK_01")["dynamic"]
        for name in SAFETY_FIELDS:
            assert name not in dynamic, f"{name} must be absent without a producer"

    def test_producer_fields_project_verbatim_with_provenance(self, store, clock):
        _telemetry(store, clock)
        store.update_vehicle_fields("TRUCK_01", _fixture_safety(clock))
        dynamic = build_vehicle_projection(store, "TRUCK_01")["dynamic"]
        assert dynamic["v_safe_mps"]["value"] == 6.0
        assert dynamic["safe_headway_m"]["value"] == 25.0
        assert dynamic["headway_m"]["value"] == 18.0
        assert dynamic["lead_vehicle_id"]["value"] == "TRUCK_02"
        assert dynamic["active_constraint"]["value"] == "HEADWAY"
        assert dynamic["risk_level"]["value"] == "HIGH"
        assert dynamic["headway_violation"]["value"] is False
        for name in SAFETY_FIELDS:
            assert dynamic[name]["source"] == "DERIVED"
            assert dynamic[name]["origin"] == "SIMULATION"
            assert dynamic[name]["freshness"] == "CURRENT"
        # actual speed and v_safe stay two different numbers.
        assert dynamic["speed_mps"]["value"] != dynamic["v_safe_mps"]["value"]

    def test_partial_producer_output_leaves_the_rest_absent(self, store, clock):
        _telemetry(store, clock)
        store.update_vehicle_fields(
            "TRUCK_01", _fixture_safety(clock, risk_level=None, active_constraint=None, headway_m=None)
        )
        dynamic = build_vehicle_projection(store, "TRUCK_01")["dynamic"]
        assert "risk_level" not in dynamic
        assert "active_constraint" not in dynamic
        assert "headway_m" not in dynamic
        assert dynamic["v_safe_mps"]["value"] == 6.0

    def test_safety_goes_stale_and_is_kept(self, store, clock):
        _telemetry(store, clock)
        store.update_vehicle_fields("TRUCK_01", _fixture_safety(clock))
        clock.t += 3.5
        f = build_vehicle_projection(store, "TRUCK_01")["dynamic"]["v_safe_mps"]
        assert f["freshness"] == "STALE"
        assert f["value"] == 6.0


class TestFailClosedCommands:
    @pytest.fixture(autouse=True)
    def reset(self, monkeypatch):
        from app.main import deduplication_store, last_sequence_by_vehicle, vehicle_telemetry_store
        vehicle_telemetry_store.clear()
        deduplication_store.clear()
        last_sequence_by_vehicle.clear()
        monkeypatch.setenv("FOG_OPERATOR_SECRET", "test-only-secret")
        yield

    def _client(self):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def _session(self, c):
        r = c.post("/api/operator/session", json={"operator_id": "OP_001", "secret": "test-only-secret"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def test_target_speed_rejected_without_v_safe_hold_and_stop_accepted(self):
        c = self._client()
        seq = int(time.time()) * 10
        assert c.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": seq, "rpm": 1528.0, "speed": 8.0}).status_code == 200
        assert "v_safe_mps" not in c.get("/api/twin/vehicles/TRUCK_01").json()["dynamic"]
        headers = self._session(c)
        tag = f"{seq}"
        r = c.post("/api/commands", headers=headers, json={
            "command_id": f"SAFETY01-T-{tag}", "vehicle_id": "TRUCK_01", "action": "TARGET_SPEED", "target_speed": 12.0,
        })
        assert r.status_code == 200, r.text
        assert r.json()["status"] == CommandStatus.REJECTED
        assert "v_safe" in r.json()["message"]
        for action in ("HOLD", "STOP"):
            r = c.post("/api/commands", headers=headers, json={
                "command_id": f"SAFETY01-{action}-{tag}", "vehicle_id": "TRUCK_01", "action": action, "target_speed": 0.0,
            })
            assert r.status_code == 200, r.text
            assert r.json()["status"] == CommandStatus.ACCEPTED, action
        # Nothing about the command touched actual speed or created a v_safe.
        d = c.get("/api/twin/vehicles/TRUCK_01").json()["dynamic"]
        assert "v_safe_mps" not in d
        assert d["speed_mps"]["value"] == pytest.approx(1528.0 * 2 * 3.141592653589793 * 0.05 / 60, abs=1e-3)

    def test_lifecycle_vocabulary_intact(self):
        for name in ("ACCEPTED", "TRANSMITTED", "ACKNOWLEDGED", "EXECUTED", "REJECTED", "DUPLICATE",
                     "STALE", "UNKNOWN_VEHICLE", "INVALID", "TIMEOUT", "SUPERSEDED"):
            assert getattr(CommandStatus, name) == name
