"""
P9 — game_ui as a read-only client of the CANONICAL Digital Twin.

SIMULATION only. No physical hardware is exercised here, and no socket is opened:
the client takes an injected opener, so the contract is tested without a backend.

THE CENTRAL ASSERTION OF THIS FILE: the visualiser may DISPLAY canonical Twin state,
but it never merges that state into its simulator, never writes back, and never
substitutes one domain's value for the other's. Two Twins exist in two processes
modelling two different things; the failure this file guards against is letting a
reader believe they are one.
"""

import importlib.util
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ROOT = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")
GAME_UI_PATH = os.path.join(MAIN_ROOT, "game_ui.py")
CLIENT_PATH = os.path.join(REPO_ROOT, "integration_adapters", "canonical_twin_client.py")

for _path in (REPO_ROOT, MAIN_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from integration_adapters.canonical_twin_client import (  # noqa: E402
    ABSENT_FIELD,
    UNAVAILABLE_TEXT,
    CanonicalTwinClient,
    parse_snapshot,
    snapshot_is_empty,
)


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def executable_source(text: str) -> str:
    """Source with docstrings and comments stripped, so prose cannot satisfy a check."""
    without_docstrings = "".join(text.split('"""')[::2])
    return "\n".join(
        line for line in without_docstrings.splitlines() if not line.strip().startswith("#")
    )


def field(**overrides):
    """One canonical field in the exact shape the backend snapshot supplies."""
    base = {
        "value": 0.9797,
        "timestamp": 1788681152.0,
        "source": "SIMULATION",
        "origin": "SIMULATION",
        "quality": "GOOD",
        "age_s": 0.2,
        "available": True,
        "clock_domain": "WALL_CLOCK",
        "freshness": "CURRENT",
    }
    base.update(overrides)
    return base


def snapshot(vehicles=None, environment=None, roads=None, mine=None):
    """A snapshot payload. Defaults mirror the MEASURED live backend response."""
    return {
        "vehicles": vehicles
        if vehicles is not None
        else {
            "TRUCK_01": {
                "vehicle_id": "TRUCK_01",
                "static": {},
                "dynamic": {
                    "speed_mps": field(),
                    "rpm": field(value=136.8),
                    "communication_state": field(value="HEALTHY"),
                },
            }
        },
        "environment": environment if environment is not None else {},
        "roads": roads if roads is not None else {},
        "mine": mine if mine is not None else {"nodes": {}, "adjacency": {}},
    }


def client_with(payload):
    """A client wired to a fake opener. No socket, no backend, no thread."""
    encoded = json.dumps(payload).encode("utf-8")
    twin = CanonicalTwinClient(opener=lambda url, timeout: encoded)
    assert twin.fetch_once() is True
    return twin


@pytest.fixture(scope="module")
def ui_module():
    """game_ui imported as a module."""
    spec = importlib.util.spec_from_file_location("game_ui_p9", GAME_UI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bridge(ui_module):
    """A real bridge with NO canonical client — the existing offline demonstration."""
    return ui_module.SimulationUIBridge()


# ---------------------------------------------------------------------------
# 1..6, 17 — the existing demonstration is preserved
# ---------------------------------------------------------------------------


def test_1_game_ui_starts_without_a_canonical_client(bridge):
    """The documented launch path is unchanged: no backend needed to start."""
    assert bridge.canonical is None
    assert bridge.twin is not None
    bridge.step()


def test_2_normal_mode_preserved(bridge):
    bridge.set_visibility(50.0)
    for _ in range(3):
        bridge.step()
    v_safe = bridge.twin_v_safe_mps("TRUCK_01")
    assert v_safe is not None, "a safe speed must still be solved in normal conditions"
    assert v_safe > 0


def test_3_and_4_dense_then_extreme_fog_lower_the_safe_speed(bridge):
    bridge.set_visibility(50.0)
    for _ in range(3):
        bridge.step()
    clear = bridge.twin_v_safe_mps("TRUCK_01")

    bridge.set_visibility(15.0)  # DENSE
    for _ in range(3):
        bridge.step()
    dense = bridge.twin_v_safe_mps("TRUCK_01")

    bridge.set_visibility(5.0)  # EXTREME
    for _ in range(3):
        bridge.step()
    extreme = bridge.twin_v_safe_mps("TRUCK_01")

    assert clear is not None and dense is not None and extreme is not None
    assert dense < clear, "dense fog must reduce the solved safe speed"
    assert extreme < dense, "extreme fog must reduce it further"


def test_5_clear_recovery_preserved(bridge):
    bridge.set_visibility(5.0)
    for _ in range(3):
        bridge.step()
    extreme = bridge.twin_v_safe_mps("TRUCK_01")

    bridge.set_visibility(50.0)
    for _ in range(5):
        bridge.step()
    recovered = bridge.twin_v_safe_mps("TRUCK_01")

    assert extreme is not None and recovered is not None
    assert recovered > extreme, "clearing the fog must recover the safe speed"


def test_6_and_17_estop_is_preserved_and_distinct_from_the_environment(bridge):
    """
    E-STOP is an EMERGENCY, not a fog limit.

    The simulator must keep the two representable independently: an E-STOP with
    perfectly clear visibility is still an E-STOP, and it must not be explained as
    an environmental limitation.
    """
    bridge.set_visibility(50.0)  # clear — no environmental reason to stop
    for _ in range(2):
        bridge.step()
    bridge.e_stop_active = True
    try:
        assert bridge.e_stop_active is True
        # The environmental solver is untouched by the emergency: v_safe still
        # reflects the road and the fog, not the E-STOP.
        assert bridge.twin_v_safe_mps("TRUCK_01") is not None
    finally:
        bridge.e_stop_active = False

    source = executable_source(read(GAME_UI_PATH))
    assert 'status_label = "E-STOP"' in source
    assert 'safety_status = "E-STOP"' in source


# ---------------------------------------------------------------------------
# 7..11 — canonical consumption and provenance
# ---------------------------------------------------------------------------


def test_7_canonical_vehicle_data_can_be_consumed():
    twin = client_with(snapshot())
    vehicle = twin.vehicle("TRUCK_01")
    assert vehicle is not None
    assert vehicle.speed_mps == pytest.approx(0.9797)
    assert vehicle.rpm == pytest.approx(136.8)
    assert vehicle.communication_state == "HEALTHY"


def test_8_provenance_is_preserved_verbatim():
    twin = client_with(snapshot())
    assert twin.vehicle("TRUCK_01").provenance_label() == "SIMULATION"
    assert twin.vehicle("TRUCK_01").freshness_label() == "CURRENT"


def test_9_simulation_remains_simulation():
    twin = client_with(snapshot())
    label = twin.vehicle("TRUCK_01").provenance_label()
    assert label == "SIMULATION"
    for forbidden in ("PHYSICAL", "LIVE", "REAL", "HARDWARE"):
        assert forbidden not in label


def test_10_physical_only_with_hardware_origin():
    """
    Vehicle A's speed is DERIVED from a genuinely measured LM393 encoder RPM, so it
    is physical and says it was derived. Nothing else may claim PHYSICAL.
    """
    measured = snapshot(
        vehicles={
            "TRUCK_01": {"dynamic": {"speed_mps": field(source="DERIVED", origin="HARDWARE")}},
            "TRUCK_02": {"dynamic": {"speed_mps": field()}},
        }
    )
    twin = client_with(measured)
    assert twin.vehicle("TRUCK_01").provenance_label() == "PHYSICAL (derived)"
    # Vehicle B is PWM-derived synthetic data and must not be called encoder-measured.
    assert twin.vehicle("TRUCK_02").provenance_label() == "SIMULATION"


def test_10b_a_directly_measured_value_is_distinct_from_a_derived_one():
    twin = client_with(
        snapshot(
            vehicles={"T": {"dynamic": {"speed_mps": field(source="MEASURED", origin="HARDWARE")}}}
        )
    )
    assert twin.vehicle("T").provenance_label() == "PHYSICAL"


def test_11_unavailable_twin_fields_remain_unavailable():
    """A field the snapshot never carried is absent — not zero, not a fallback."""
    twin = client_with(snapshot(vehicles={"T": {"dynamic": {"speed_mps": field()}}}))
    vehicle = twin.vehicle("T")
    for missing in ("v_safe_mps", "visibility_m", "friction_mu", "position", "heading"):
        assert vehicle.get(missing) is ABSENT_FIELD
        assert vehicle.get(missing).available is False
        assert vehicle.get(missing).provenance_label() == UNAVAILABLE_TEXT
    assert vehicle.get("v_safe_mps").freshness_label() == "UNAVAILABLE"


def test_11b_a_supplied_zero_is_kept_as_zero():
    """0 m/s is a stopped truck. It must never be mistaken for an absent value."""
    twin = client_with(snapshot(vehicles={"T": {"dynamic": {"speed_mps": field(value=0.0)}}}))
    assert twin.vehicle("T").speed_mps == 0.0
    assert twin.vehicle("T").get("speed_mps").available is True


def test_11c_an_unavailable_field_is_not_treated_as_fresh():
    twin = client_with(snapshot(vehicles={"T": {"dynamic": {"speed_mps": field(available=False)}}}))
    assert twin.vehicle("T").freshness_label() == "UNAVAILABLE"


def test_11d_an_unrecognised_freshness_verdict_is_unknown_not_current():
    twin = client_with(
        snapshot(vehicles={"T": {"dynamic": {"speed_mps": field(freshness="NOT_EVALUATED")}}})
    )
    assert twin.vehicle("T").freshness_label() == "UNKNOWN"


# ---------------------------------------------------------------------------
# 12, 13, 18 — no invention
# ---------------------------------------------------------------------------


def test_12_no_fake_coordinates_are_produced():
    """The live snapshot carries no position, and none is manufactured."""
    twin = client_with(snapshot())
    vehicle = twin.vehicle("TRUCK_01")
    for spatial in ("position", "x", "y", "lat", "lon", "heading"):
        assert vehicle.get(spatial).value is None


def test_13_no_random_or_derived_placement_in_the_client():
    body = executable_source(read(CLIENT_PATH))
    for forbidden in ("random", "math.sin", "math.cos", "atan2", "dead_reckon"):
        assert forbidden not in body


def test_18_live_limitations_are_reported_honestly():
    """environment / roads / mine come back empty live, and that is stated."""
    twin = client_with(snapshot())
    assert twin.block_is_empty("environment") is True
    assert twin.block_is_empty("roads") is True
    assert twin.block_is_empty("mine") is True


def test_18b_a_populated_block_is_not_reported_as_empty():
    twin = client_with(snapshot(mine={"nodes": {"N-1": {}}, "adjacency": {}}))
    assert twin.block_is_empty("mine") is False


def test_18c_snapshot_is_empty_is_pure_and_tolerates_rubbish():
    assert snapshot_is_empty(None, "environment") is True
    assert snapshot_is_empty({"environment": "not a dict"}, "environment") is True


# ---------------------------------------------------------------------------
# 14, 15, 16 — architectural boundaries
# ---------------------------------------------------------------------------


def test_14_the_client_is_not_a_twin():
    """
    It holds a decoded COPY for display. It exposes no mutation, so the simulator
    cannot write into it and it cannot become a second authority.
    """
    twin = client_with(snapshot())
    for mutator in (
        "register_vehicle",
        "sync_from_simulation",
        "update_vehicle",
        "set_vehicle_field",
        "update_environment",
    ):
        assert not hasattr(twin, mutator), "the client must not offer %s" % mutator


def test_14b_canonical_state_is_never_written_into_the_simulator():
    """
    The bridge holds the canonical client as a SEPARATE attribute. Nothing copies a
    canonical value into the simulator's own Twin or its vehicles.
    """
    body = executable_source(read(GAME_UI_PATH))
    assert "self.canonical" in body
    for forbidden in (
        "self.twin.sync_from_simulation(self.canonical",
        "self.sim.vehicles =",
        "self.twin.register_vehicle(self.canonical",
    ):
        assert forbidden not in body


def test_15_no_second_command_pathway():
    """GET only. No POST and no command verb anywhere in the client."""
    body = executable_source(read(CLIENT_PATH))
    for forbidden in ("POST", "api/commands", "CommandGateway", "issue_command", "requests.post"):
        assert forbidden not in body, "the client must not carry %s" % forbidden


def test_15b_game_ui_opens_no_command_transport():
    body = executable_source(read(GAME_UI_PATH))
    for forbidden in ("requests.post", "urlopen", "api/commands", "http.client"):
        assert forbidden not in body


def test_16_the_client_contains_no_safety_solver():
    """
    Safety stays with the authoritative solver. The client reads v_safe if the Twin
    supplies it and otherwise reports UNAVAILABLE; it never computes one.
    """
    body = executable_source(read(CLIENT_PATH))
    for forbidden in ("min(", "sqrt", "fog_safe", "v_stop", "stopping_distance"):
        assert forbidden not in body


# ---------------------------------------------------------------------------
# the render model stays pure and honest
# ---------------------------------------------------------------------------


class _RenderModelHost:
    """
    Just enough object to call the render-model methods unbound.

    Constructing a real `MiningVisualizerUI` would import pygame into `sys.modules`,
    which breaks the sibling suite's proof that game_ui's helpers are pure. Calling
    the methods against this stub proves the same thing more strongly: the render
    model needs NOTHING but the bridge, so no Twin logic can be hiding in a drawing
    function.
    """

    def __init__(self, bridge):
        self.bridge = bridge


def render_model(ui_module, bridge):
    return _RenderModelHost(bridge)


def test_render_model_is_pure_and_reports_unavailable_without_a_client(ui_module, bridge):
    host = render_model(ui_module, bridge)
    header, rows = ui_module.MiningVisualizerUI.canonical_twin_rows(host)
    assert rows == []
    assert "NOT CONNECTED" in header


def test_render_model_lists_canonical_vehicles_when_supplied(ui_module):
    twin = client_with(snapshot())
    supplied_bridge = ui_module.SimulationUIBridge(canonical_client=twin)
    host = render_model(ui_module, supplied_bridge)
    header, rows = ui_module.MiningVisualizerUI.canonical_twin_rows(host)
    assert "CANONICAL TWIN" in header
    assert [row["vehicle_id"] for row in rows] == ["TRUCK_01"]
    assert rows[0]["provenance"] == "SIMULATION"
    assert rows[0]["freshness"] == "CURRENT"
    assert rows[0]["speed_kmh"] == "3.5"  # 0.9797 m/s -> km/h, a unit conversion
    assert rows[0]["comms"] == "HEALTHY"


def test_render_model_names_what_the_canonical_twin_lacks(ui_module):
    twin = client_with(snapshot())
    supplied_bridge = ui_module.SimulationUIBridge(canonical_client=twin)
    host = render_model(ui_module, supplied_bridge)
    notes = ui_module.MiningVisualizerUI.canonical_unavailable_notes(host)
    assert any("environment" in note for note in notes)
    assert any("topology" in note for note in notes)


def test_importing_game_ui_does_not_pull_in_pygame(ui_module):
    """Guards the sibling suite's purity assertion against this file's ordering."""
    assert "pygame" not in sys.modules


def test_a_failed_fetch_never_raises_and_never_invents_data():
    def broken(url, timeout):
        raise OSError("connection refused")

    twin = CanonicalTwinClient(opener=broken)
    assert twin.fetch_once() is False
    assert twin.connected is False
    assert twin.vehicles() == {}
    assert "UNAVAILABLE" in twin.status_text()


def test_malformed_json_is_survived():
    twin = CanonicalTwinClient(opener=lambda url, timeout: b"{not json")
    assert twin.fetch_once() is False
    assert twin.vehicles() == {}


def test_parse_snapshot_is_pure_and_tolerates_partial_payloads():
    assert parse_snapshot(None) == {}
    assert parse_snapshot({"vehicles": "wrong type"}) == {}
    assert parse_snapshot({"vehicles": {"T": "wrong type"}}) == {}
    assert list(parse_snapshot({"vehicles": {"T": {}}})) == ["T"]
