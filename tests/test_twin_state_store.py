"""
P1 — Canonical Digital Twin State Store tests.

Covers the 14 required P1 cases plus an integration check against the REAL
`twin.simulator.Simulator`, proving the store observes the existing Twin without
altering it.
"""

import pytest

from twin.twin_state_store import (
    Quality,
    Source,
    Sourced,
    TwinMode,
    TwinStateStore,
    UNAVAILABLE,
)


# ---------------------------------------------------------------------
# Fakes: minimal stand-ins shaped like the real domain objects.
# Structural typing is what the store relies on, so these are faithful.
# ---------------------------------------------------------------------

class FakeEdge:
    def __init__(self, road_id, start="SHOVEL", end="CRUSHER"):
        self.id = road_id
        self.start_node = start
        self.end_node = end
        self.length_m = 1200.0
        self.grade_percent = -8.0
        self.curve_radius_m = 50.0
        self.speed_limit_mps = 11.11
        self.width_m = 12.0
        self.visibility_m = 50.0
        self.friction_mu = 0.60
        self.c_rr = 0.02
        self.surface_state = "dry"
        self.v_safe_mps = 9.5
        self.safe_headway_m = 40.0
        self.capacity_vph = 120.0
        self.vehicles = []


class FakeQueue:
    length = 0


class FakeNode:
    def __init__(self, node_id, node_type="CRUSHER"):
        self.id = node_id
        self.type = node_type
        self.service_rate_vph = 20.0
        self.criticality = 1.0
        self.queue = FakeQueue()


class FakeNetwork:
    def __init__(self):
        self.edges = {"ROAD_1": FakeEdge("ROAD_1"), "ROAD_2": FakeEdge("ROAD_2")}
        self.nodes = {"SHOVEL": FakeNode("SHOVEL", "SHOVEL"), "CRUSHER": FakeNode("CRUSHER", "CRUSHER")}
        self.adjacency = {"SHOVEL": [self.edges["ROAD_1"]], "CRUSHER": [self.edges["ROAD_2"]]}


class FakeVehicle:
    """Same attribute surface as models.vehicle.Vehicle."""

    def __init__(self, vehicle_id="TRUCK_01"):
        self.id = vehicle_id
        self.tare_mass = 74000.0
        self.payload_capacity = 91000.0
        self.length = 10.5
        self.width = 6.0
        self.wheelbase = 4.8
        self.position_s = 100.0
        self.current_edge = "ROAD_1"
        self.current_node = None
        self.speed_mps = 8.0
        self.acceleration_mps2 = 0.5
        self.mass_kg = 165000.0
        self.payload_kg = 91000.0
        self.is_loaded = True
        self.state = "traveling"
        self.v_safe_mps = 9.5
        self.v_dispatch_mps = 11.11
        self.v_command_mps = 9.5
        self.safe_headway_m = 40.0
        self.stop_envelope_m = 35.0
        self.warning_fault = False


class FakeFog:
    current_visibility = 15.0
    current_friction = 0.25
    current_rr = 0.03
    current_state = "wet"
    scenario_name = "dense_fog"


class FakeClock:
    """Controllable clock so staleness is tested deterministically, not by sleeping."""

    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def store():
    return TwinStateStore(network=FakeNetwork(), mode=TwinMode.SIMULATION, clock=FakeClock())


# ---------------------------------------------------------------------
# 1. store initialization
# ---------------------------------------------------------------------

def test_store_initialization():
    empty = TwinStateStore()
    assert empty.mode is TwinMode.SIMULATION
    assert empty.get_all_vehicles() == {}
    assert empty.get_all_roads() == {}
    assert empty.last_sync_timestamp is None

    bound = TwinStateStore(network=FakeNetwork())
    assert set(bound.get_all_roads()) == {"ROAD_1", "ROAD_2"}
    assert set(bound.get_mine()["nodes"]) == {"SHOVEL", "CRUSHER"}


# ---------------------------------------------------------------------
# 2. vehicle registration / retrieval
# ---------------------------------------------------------------------

def test_vehicle_registration_and_retrieval(store):
    vehicle = FakeVehicle("TRUCK_01")
    registered = store.register_vehicle(vehicle)

    assert registered.entity_id == "TRUCK_01"
    assert store.get_vehicle("TRUCK_01") is registered
    assert list(store.get_all_vehicles()) == ["TRUCK_01"]

    # Existing vehicle object is reused, not copied into a parallel model.
    assert registered.domain_vehicle is vehicle

    # Static/configured properties only; no physical provenance implied.
    assert registered.static["tare_mass_kg"] == 74000.0
    assert registered.static["length_m"] == 10.5

    # Registration alone observes nothing dynamic.
    assert registered.get("speed_mps") is UNAVAILABLE

    # A physical truck may be registered by bare id before any telemetry arrives.
    store.register_vehicle("TRUCK_02")
    assert store.get_vehicle("TRUCK_02").domain_vehicle is None
    assert store.get_vehicle("TRUCK_02").static == {}


def test_register_vehicle_without_id_is_rejected(store):
    class Anonymous:
        pass

    with pytest.raises(ValueError):
        store.register_vehicle(Anonymous())


# ---------------------------------------------------------------------
# 3. road retrieval
# ---------------------------------------------------------------------

def test_road_retrieval(store):
    road = store.get_road("ROAD_1")
    assert road is not None
    assert road.static["length_m"] == 1200.0
    assert road.static["grade_percent"] == -8.0
    assert road.static["speed_limit_mps"] == pytest.approx(11.11)
    assert store.get_road("ROAD_NOPE") is None
    assert set(store.get_all_roads()) == {"ROAD_1", "ROAD_2"}


# ---------------------------------------------------------------------
# 4. environment retrieval
# ---------------------------------------------------------------------

def test_environment_retrieval(store):
    env = store.get_environment()
    assert env.get("visibility_m") is UNAVAILABLE  # nothing observed yet

    store.sync_from_simulation(fog_model=FakeFog(), timestamp=1000.0)
    visibility = store.get_environment().get("visibility_m")
    assert visibility.value == 15.0
    assert visibility.source is Source.SIMULATION
    assert store.get_environment().get("scenario").value == "dense_fog"


# ---------------------------------------------------------------------
# 5/6/7. simulation, hardware and derived provenance
# ---------------------------------------------------------------------

def test_simulation_provenance(store):
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(
        network=FakeNetwork(), vehicles=[FakeVehicle("TRUCK_01")], fog_model=FakeFog(), timestamp=500.0
    )

    speed = store.get_vehicle_field("TRUCK_01", "speed_mps")
    assert speed.value == 8.0
    assert speed.source is Source.SIMULATION
    assert speed.quality is Quality.GOOD

    # Road environment likewise comes from the simulation.
    assert store.get_road("ROAD_1").get("visibility_m").source is Source.SIMULATION


def test_hardware_provenance(store):
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=1234.0)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 240.0
    assert rpm.source is Source.HARDWARE
    assert rpm.timestamp == 1234.0
    assert rpm.is_available


def test_derived_provenance(store):
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(vehicles=[FakeVehicle("TRUCK_01")], timestamp=500.0)

    # Physics/solver outputs are DERIVED, never presented as measurements.
    for name in ("v_safe_mps", "v_command_mps", "safe_headway_m", "stop_envelope_m"):
        assert store.get_vehicle_field("TRUCK_01", name).source is Source.DERIVED

    assert store.get_road("ROAD_1").get("v_safe_mps").source is Source.DERIVED
    assert store.get_road("ROAD_1").get("capacity_vph").source is Source.DERIVED


def test_configured_static_data_is_not_given_physical_provenance(store):
    """Geometry and vehicle spec are reference data. They never appear as sourced fields."""
    store.register_vehicle(FakeVehicle("TRUCK_01"))

    road = store.get_road("ROAD_1")
    for static_key in ("length_m", "grade_percent", "curve_radius_m", "width_m"):
        assert static_key in road.static
        assert static_key not in road.dynamic

    vehicle = store.get_vehicle("TRUCK_01")
    assert "tare_mass_kg" in vehicle.static
    assert "tare_mass_kg" not in vehicle.dynamic


# ---------------------------------------------------------------------
# 8. per-field timestamps
# ---------------------------------------------------------------------

def test_per_field_timestamps_are_independent(store):
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=100.0)
    store.update_vehicle_field("TRUCK_02", "speed_mps", 2.5, Source.HARDWARE, timestamp=175.0)

    assert store.get_vehicle_field("TRUCK_02", "rpm").timestamp == 100.0
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").timestamp == 175.0

    # Ages differ at a single read time — one global timestamp would hide this.
    assert store.get_vehicle_field("TRUCK_02", "rpm").age_s(200.0) == 100.0
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").age_s(200.0) == 25.0


# ---------------------------------------------------------------------
# 9. quality states
# ---------------------------------------------------------------------

def test_quality_states_and_staleness():
    clock = FakeClock(1000.0)
    store = TwinStateStore(network=FakeNetwork(), clock=clock, stale_after_s=3.0)
    store.register_vehicle("TRUCK_02")

    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=1000.0)
    assert store.get_vehicle_field("TRUCK_02", "rpm").effective_quality(1000.0, 3.0) is Quality.GOOD

    # Same stored value, read later: GOOD decays to STALE.
    assert store.get_vehicle_field("TRUCK_02", "rpm").effective_quality(1010.0, 3.0) is Quality.STALE

    # Stored quality itself is never mutated by a read.
    assert store.get_vehicle_field("TRUCK_02", "rpm").quality is Quality.GOOD

    # Explicit degraded and invalid states survive.
    store.update_vehicle_field("TRUCK_02", "snr", 3.0, Source.HARDWARE, timestamp=1000.0, quality=Quality.DEGRADED)
    assert store.get_vehicle_field("TRUCK_02", "snr").effective_quality(1000.0, 3.0) is Quality.DEGRADED

    store.update_vehicle_field(
        "TRUCK_02", "ax", float("nan"), Source.HARDWARE, timestamp=1000.0, quality=Quality.INVALID
    )
    assert store.get_vehicle_field("TRUCK_02", "ax").effective_quality(1000.0, 3.0) is Quality.INVALID
    assert store.get_vehicle_field("TRUCK_02", "ax").effective_quality(9999.0, 3.0) is Quality.INVALID

    # No configured threshold means staleness is NOT evaluated — never silently assumed.
    assert store.get_vehicle_field("TRUCK_02", "rpm").effective_quality(99999.0, None) is Quality.GOOD


def test_unavailable_field_quality_is_unknown(store):
    assert UNAVAILABLE.effective_quality(1000.0, 3.0) is Quality.UNKNOWN
    assert not UNAVAILABLE.is_available
    assert UNAVAILABLE.age_s(1000.0) is None


# ---------------------------------------------------------------------
# 10. SIMULATION / HARDWARE / HYBRID modes
# ---------------------------------------------------------------------

def test_twin_modes():
    assert [m.value for m in TwinMode] == ["SIMULATION", "HARDWARE", "HYBRID"]

    store = TwinStateStore(mode=TwinMode.HARDWARE)
    assert store.mode is TwinMode.HARDWARE
    store.set_mode(TwinMode.HYBRID)
    assert store.mode is TwinMode.HYBRID
    assert store.get_state_snapshot()["mode"] == "HYBRID"

    with pytest.raises(ValueError):
        TwinStateStore(mode="TELEPATHY")


def test_hybrid_mode_keeps_per_field_source_visible(store):
    """A simulated truck and a physical truck coexist; each field says where it came from."""
    store.set_mode(TwinMode.HYBRID)
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.register_vehicle("TRUCK_02")

    store.sync_from_simulation(vehicles=[FakeVehicle("TRUCK_01")], timestamp=500.0)
    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=501.0)

    assert store.get_vehicle_field("TRUCK_01", "speed_mps").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE
    # The physical truck has no simulated position, and none is invented for it.
    assert store.get_vehicle_field("TRUCK_02", "position_s") is UNAVAILABLE


# ---------------------------------------------------------------------
# 11. missing vehicle handling
# ---------------------------------------------------------------------

def test_missing_vehicle_handling(store):
    assert store.get_vehicle("GHOST") is None
    assert store.get_vehicle_field("GHOST", "speed_mps") is UNAVAILABLE

    with pytest.raises(KeyError):
        store.update_vehicle_field("GHOST", "speed_mps", 5.0, Source.HARDWARE)

    with pytest.raises(KeyError):
        store.update_road_field("ROAD_NOPE", "visibility_m", 20.0, Source.SIMULATION)


# ---------------------------------------------------------------------
# 12. snapshot generation
# ---------------------------------------------------------------------

def test_snapshot_generation(store):
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(vehicles=[FakeVehicle("TRUCK_01")], fog_model=FakeFog(), timestamp=500.0)

    snap = store.get_state_snapshot(now=505.0)

    assert snap["schema"] == "twin_state_snapshot/1"
    assert snap["mode"] == "SIMULATION"
    assert snap["snapshot_timestamp"] == 505.0
    assert snap["last_sync_timestamp"] == 500.0
    assert set(snap) >= {"environment", "mine", "roads", "vehicles"}

    speed = snap["vehicles"]["TRUCK_01"]["dynamic"]["speed_mps"]
    # P4.1 added `clock_domain` and `freshness`. The field was written by a simulation
    # sync, so it lives in the SIMULATION domain and is aged against the simulation clock
    # (500.0), not against the wall clock passed as `now`.
    assert speed == {
        "value": 8.0,
        "timestamp": 500.0,
        "source": "SIMULATION",
        "quality": "GOOD",
        "age_s": 0.0,
        "available": True,
        "clock_domain": "SIMULATION",
        "freshness": "NOT_EVALUATED",
    }

    assert snap["environment"]["dynamic"]["visibility_m"]["value"] == 15.0
    assert snap["mine"]["nodes"]["CRUSHER"]["type"] == "CRUSHER"
    assert snap["roads"]["ROAD_1"]["static"]["length_m"] == 1200.0


def test_snapshot_is_a_copy_not_a_live_handle(store):
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=100.0)

    snap = store.get_state_snapshot(now=100.0)
    snap["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["value"] = 9999.0

    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 240.0


# ---------------------------------------------------------------------
# 13. one field update does not corrupt unrelated fields
# ---------------------------------------------------------------------

def test_single_field_update_does_not_disturb_other_state(store):
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(
        vehicles=[FakeVehicle("TRUCK_01")], fog_model=FakeFog(), timestamp=500.0
    )
    before = store.get_state_snapshot(now=500.0)

    store.update_vehicle_field("TRUCK_01", "rpm", 240.0, Source.HARDWARE, timestamp=600.0)
    after = store.get_state_snapshot(now=500.0)

    # The touched field is the only vehicle field that changed.
    before_dyn = before["vehicles"]["TRUCK_01"]["dynamic"]
    after_dyn = after["vehicles"]["TRUCK_01"]["dynamic"]
    changed = {
        name
        for name in set(before_dyn) | set(after_dyn)
        if before_dyn.get(name) != after_dyn.get(name)
    }
    assert changed == {"rpm"}

    # Roads, environment and mine are untouched.
    assert before["roads"] == after["roads"]
    assert before["environment"] == after["environment"]
    assert before["mine"] == after["mine"]

    # Timestamps and sources of neighbouring fields survive intact.
    speed = store.get_vehicle_field("TRUCK_01", "speed_mps")
    assert (speed.value, speed.timestamp, speed.source) == (8.0, 500.0, Source.SIMULATION)


def test_rebinding_network_preserves_observed_state():
    network = FakeNetwork()
    store = TwinStateStore(network=network, clock=FakeClock())
    store.update_road_field("ROAD_1", "visibility_m", 12.0, Source.SIMULATION, timestamp=100.0)

    store.bind_network(network)
    assert store.get_road("ROAD_1").get("visibility_m").value == 12.0


def test_reregistering_vehicle_preserves_observed_state(store):
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE, timestamp=100.0)
    store.register_vehicle(FakeVehicle("TRUCK_02"))

    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 240.0
    assert store.get_vehicle("TRUCK_02").static["tare_mass_kg"] == 74000.0


# ---------------------------------------------------------------------
# 14. no fabricated value insertion
# ---------------------------------------------------------------------

def test_no_fabricated_values_for_unmeasured_fields(store):
    """
    The single most important guarantee: the store never manufactures hardware
    position, heading, rpm, road_id, friction or visibility.
    """
    store.set_mode(TwinMode.HARDWARE)
    store.register_vehicle("TRUCK_02")  # physical truck, telemetry not yet arrived

    for name in ("position_s", "road_id", "heading_rad", "rpm", "speed_mps", "communication_state"):
        got = store.get_vehicle_field("TRUCK_02", name)
        assert got is UNAVAILABLE, f"{name} was fabricated: {got}"
        assert got.value is None
        assert got.source is Source.UNKNOWN

    snap = store.get_state_snapshot(now=1000.0)
    assert snap["vehicles"]["TRUCK_02"]["dynamic"] == {}


def test_simulation_sync_does_not_invent_hardware_only_fields(store):
    """The simulation has no rpm/heading/comm sensor, so it must not supply them."""
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(vehicles=[FakeVehicle("TRUCK_01")], timestamp=500.0)

    for name in ("rpm", "heading_rad", "communication_state"):
        assert store.get_vehicle_field("TRUCK_01", name) is UNAVAILABLE


def test_mode_change_does_not_relabel_stored_values(store):
    """Switching mode never rewrites the provenance of already-stored values."""
    store.register_vehicle(FakeVehicle("TRUCK_01"))
    store.sync_from_simulation(vehicles=[FakeVehicle("TRUCK_01")], timestamp=500.0)

    store.set_mode(TwinMode.HARDWARE)
    assert store.get_vehicle_field("TRUCK_01", "speed_mps").source is Source.SIMULATION


# ---------------------------------------------------------------------
# 15. integration against the REAL Twin (observe without altering)
# ---------------------------------------------------------------------

def test_store_observes_real_simulator_without_altering_it():
    from run_baseline_vs_orchestrator import build_graph, load_configs
    from twin.simulator import Simulator

    vehicle_cfg, roads_cfg, nodes_cfg, weather_cfg, scenario_cfg = load_configs()
    network = build_graph(nodes_cfg, roads_cfg)

    # scenario_cfg is flat (config/scenarios.yaml) and is passed straight through,
    # exactly as scenarios/demo_v01.run_scenario does.
    sim = Simulator(network, vehicle_cfg, weather_cfg, dict(scenario_cfg))

    store = TwinStateStore(network=sim.network, mode=TwinMode.SIMULATION)
    for vehicle in sim.vehicles:
        store.register_vehicle(vehicle)

    for _ in range(25):
        sim.run_step()
    ts = store.sync_from_simulation(sim)

    # The store observed the real Twin.
    assert ts == pytest.approx(sim.current_time)
    assert set(store.get_all_vehicles()) == {v.id for v in sim.vehicles}
    assert set(store.get_all_roads()) == set(sim.network.edges)

    first = sim.vehicles[0]
    assert store.get_vehicle_field(first.id, "speed_mps").value == first.speed_mps
    assert store.get_vehicle_field(first.id, "v_safe_mps").value == first.v_safe_mps
    assert store.get_vehicle_field(first.id, "v_safe_mps").source is Source.DERIVED
    assert store.get_environment().get("visibility_m").value == sim.fog_model.current_visibility

    # Reading through the store changed nothing in the Twin.
    before = (first.speed_mps, first.position_s, first.v_command_mps, sim.current_time)
    store.get_state_snapshot()
    store.sync_from_simulation(sim)
    assert (first.speed_mps, first.position_s, first.v_command_mps, sim.current_time) == before


def test_sourced_is_immutable():
    """Provenance cannot be edited in place by a consumer."""
    s = Sourced(value=1.0, timestamp=10.0, source=Source.HARDWARE, quality=Quality.GOOD)
    with pytest.raises(Exception):
        s.value = 2.0
