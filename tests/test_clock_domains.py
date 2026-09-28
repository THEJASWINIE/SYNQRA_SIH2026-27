"""
P4.1 — explicit per-field clock domains.

The simulator runs on deterministic simulation seconds; telemetry carries wall-clock
epoch seconds. Those are different number lines and must never be compared.

All hardware-shaped data here is REPLAYED / EMULATED. No physical ESP32 was connected.
"""

import pytest

from telemetry_ingest import TelemetryIngestor, Transport
from twin.twin_state_store import (
    ClockDomain,
    Quality,
    Source,
    Sourced,
    TwinMode,
    TwinStateStore,
)

# Representative values from the two clocks. Deliberately far apart.
SIM_NOW = 120.0
WALL_NOW = 1_788_000_000.0


class FixedClock:
    """Wall clock only. The simulation clock comes from the simulator itself."""

    def __init__(self, t=WALL_NOW):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class SimVehicle:
    def __init__(self, vehicle_id, position_s=40.0, speed_mps=7.5):
        self.id = vehicle_id
        self.tare_mass = 74000.0
        self.length = 10.52
        self.position_s = position_s
        self.current_edge = "ROAD_2"
        self.current_node = None
        self.speed_mps = speed_mps
        self.acceleration_mps2 = 0.4
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


class SimFog:
    current_visibility = 15.0
    current_friction = 0.35
    current_rr = 0.02
    current_state = "wet"
    scenario_name = "dense_fog"


def hw(vehicle_id="TRUCK_02", sequence=1, **over):
    rec = dict(
        vehicle_id=vehicle_id,
        sequence_number=sequence,
        rpm=180.0,
        speed=2.5,
        acceleration={"x": 0.10, "y": 0.0, "z": 9.81},
        gyroscope={"x": 0.0, "y": 0.0, "z": 0.0},
        communication={"rssi": -65, "snr": 9.2},
        communication_state="HEALTHY",
        data_quality="LIVE",
    )
    rec.update(over)
    return rec


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def store(clock):
    return TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)


@pytest.fixture
def ingestor(store, clock):
    return TelemetryIngestor(store, clock=clock)


# ---------------------------------------------------------------------
# 1. simulation fields are not stale merely because a wall clock is used
# ---------------------------------------------------------------------

def test_simulation_field_is_not_stale_against_wall_clock(store, clock):
    """The regression P4 uncovered: sim time 120 vs wall time 1.788e9."""
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=SIM_NOW)

    field = store.get_vehicle_field("TRUCK_01", "position_s")
    assert field.clock_domain is ClockDomain.SIMULATION

    # Aged in its OWN domain, it is current.
    assert field.effective_quality(SIM_NOW, 3.0, ClockDomain.SIMULATION) is Quality.GOOD

    # And the snapshot, taken with a wall clock, does not call it stale.
    snap = store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]
    assert snap["quality"] == "GOOD"
    assert snap["clock_domain"] == "SIMULATION"


def test_whole_simulated_vehicle_is_not_stale_in_snapshot(store, clock):
    store.sync_from_simulation(
        vehicles=[SimVehicle("TRUCK_01")], fog_model=SimFog(), timestamp=SIM_NOW
    )
    snap = store.get_state_snapshot()

    for name, field in snap["vehicles"]["TRUCK_01"]["dynamic"].items():
        assert field["quality"] != "STALE", f"{name} wrongly stale across clock domains"
    assert snap["environment"]["dynamic"]["visibility_m"]["quality"] != "STALE"


# ---------------------------------------------------------------------
# 2/4. hardware fields still use wall-clock freshness
# ---------------------------------------------------------------------

def test_hardware_field_uses_wall_clock_freshness(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.clock_domain is ClockDomain.WALL_CLOCK
    assert store.get_state_snapshot()["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["freshness"] == "CURRENT"

    clock.advance(10.0)                                   # wall clock moves past 3 s
    snap = store.get_state_snapshot()["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]
    assert snap["quality"] == "STALE"
    assert snap["freshness"] == "STALE"
    assert snap["age_s"] == pytest.approx(10.0)


def test_hardware_timestamp_is_not_aged_against_simulation_time(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)
    rpm = store.get_vehicle_field("TRUCK_02", "rpm")

    # Comparing a wall-clock stamp to simulation time yields no age at all.
    assert rpm.age_in(SIM_NOW, ClockDomain.SIMULATION) is None
    assert rpm.effective_quality(SIM_NOW, 3.0, ClockDomain.SIMULATION) is Quality.GOOD


# ---------------------------------------------------------------------
# 3/5. cross-domain comparison is refused, never manufactured
# ---------------------------------------------------------------------

def test_cross_domain_freshness_is_not_evaluated():
    sim_field = Sourced(value=1.0, timestamp=118.5, source=Source.SIMULATION,
                        quality=Quality.GOOD, clock_domain=ClockDomain.SIMULATION)

    # Same domain: a real age.
    assert sim_field.age_in(SIM_NOW, ClockDomain.SIMULATION) == pytest.approx(1.5)
    assert sim_field.freshness(SIM_NOW, 3.0, ClockDomain.SIMULATION) == "CURRENT"

    # Cross domain: no age is manufactured, and it is NOT called stale.
    assert sim_field.age_in(WALL_NOW, ClockDomain.WALL_CLOCK) is None
    assert sim_field.freshness(WALL_NOW, 3.0, ClockDomain.WALL_CLOCK) == "NOT_EVALUATED"
    assert sim_field.effective_quality(WALL_NOW, 3.0, ClockDomain.WALL_CLOCK) is Quality.GOOD


def test_undeclared_domain_is_never_compared():
    unknown = Sourced(value=1.0, timestamp=100.0, source=Source.SIMULATION,
                      quality=Quality.GOOD)
    assert unknown.clock_domain is ClockDomain.UNKNOWN
    assert unknown.age_in(WALL_NOW, ClockDomain.WALL_CLOCK) is None
    assert unknown.freshness(WALL_NOW, 3.0, ClockDomain.WALL_CLOCK) == "NOT_EVALUATED"


def test_domain_is_never_inferred_from_magnitude():
    """A simulation timestamp that happens to be large is still SIMULATION."""
    big_sim = Sourced(value=1.0, timestamp=1_788_000_000.0, source=Source.SIMULATION,
                      quality=Quality.GOOD, clock_domain=ClockDomain.SIMULATION)
    assert big_sim.age_in(WALL_NOW, ClockDomain.WALL_CLOCK) is None

    small_wall = Sourced(value=1.0, timestamp=120.0, source=Source.HARDWARE,
                         quality=Quality.GOOD, clock_domain=ClockDomain.WALL_CLOCK)
    assert small_wall.age_in(SIM_NOW, ClockDomain.SIMULATION) is None


# ---------------------------------------------------------------------
# 6. derived fields inherit the correct domain
# ---------------------------------------------------------------------

def test_derived_fields_inherit_their_source_clock(store, ingestor, clock):
    # Solver output produced during a simulation sync -> SIMULATION clock.
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=SIM_NOW)
    v_safe = store.get_vehicle_field("TRUCK_01", "v_safe_mps")
    assert v_safe.source is Source.DERIVED
    assert v_safe.clock_domain is ClockDomain.SIMULATION

    # Speed derived from a measured RPM -> WALL_CLOCK, like the telemetry it came from.
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)
    speed = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert speed.source is Source.DERIVED
    assert speed.is_hardware_backed()
    assert speed.clock_domain is ClockDomain.WALL_CLOCK

    # received_at is a wall-clock quantity by definition.
    assert store.get_vehicle_field("TRUCK_02", "received_at").clock_domain is ClockDomain.WALL_CLOCK


# ---------------------------------------------------------------------
# 7. HYBRID state holds both domains at once
# ---------------------------------------------------------------------

def test_hybrid_state_contains_both_clock_domains(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)
    store.sync_from_simulation(
        vehicles=[SimVehicle("TRUCK_01"), SimVehicle("TRUCK_02")],
        fog_model=SimFog(), timestamp=SIM_NOW,
    )

    snap = store.get_state_snapshot()
    assert snap["simulation_time"] == SIM_NOW

    truck2 = snap["vehicles"]["TRUCK_02"]["dynamic"]
    assert truck2["rpm"]["clock_domain"] == "WALL_CLOCK"
    assert truck2["position_s"]["clock_domain"] == "SIMULATION"
    # Both are current in their own domains.
    assert truck2["rpm"]["quality"] == "GOOD"
    assert truck2["position_s"]["quality"] == "GOOD"


# ---------------------------------------------------------------------
# 8. hardware precedence unchanged
# ---------------------------------------------------------------------

def test_hardware_precedence_is_unchanged_by_clock_domains(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    sim_truck = SimVehicle("TRUCK_02")
    sim_truck.rpm = 999.0
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=SIM_NOW)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 180.0
    assert rpm.source is Source.HARDWARE


def test_precedence_gate_ages_hardware_in_its_own_domain(store, ingestor, clock):
    """
    The precedence gate must not think a fresh hardware field is stale (or vice versa)
    because it grabbed the wrong clock.
    """
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    # Simulation time advances a long way; the hardware field is still wall-clock fresh.
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], timestamp=SIM_NOW + 10_000.0)
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 180.0

    # Now age the WALL clock past the threshold: speed_mps may fall back, rpm may not.
    clock.advance(10.0)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02", speed_mps=7.5)],
                               timestamp=SIM_NOW + 10_001.0)
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").value == 7.5
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 180.0     # never falls back


# ---------------------------------------------------------------------
# 9/10. each domain still goes stale when ITS OWN clock advances
# ---------------------------------------------------------------------

def test_stale_hardware_remains_correctly_stale(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)
    clock.advance(10.0)

    snap = store.get_state_snapshot()["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]
    assert snap["quality"] == "STALE"
    assert snap["freshness"] == "STALE"


def test_stale_simulation_is_stale_when_simulation_time_advances(store, clock):
    """Clock domains must not become an excuse for simulation state never going stale."""
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=SIM_NOW)
    assert store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]["quality"] == "GOOD"

    # The simulation clock moves on while this vehicle stops being updated.
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_09")], timestamp=SIM_NOW + 50.0)

    snap = store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]
    assert snap["quality"] == "STALE"
    assert snap["freshness"] == "STALE"
    assert snap["age_s"] == pytest.approx(50.0)


def test_simulation_freshness_boundary(store, clock):
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=100.0)

    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_09")], timestamp=102.0)   # age 2 <= 3
    assert store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]["freshness"] == "CURRENT"

    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_09")], timestamp=104.0)   # age 4 > 3
    assert store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]["freshness"] == "STALE"


def test_no_threshold_means_freshness_is_not_evaluated(clock):
    store = TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=None)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=SIM_NOW)

    snap = store.get_state_snapshot()["vehicles"]["TRUCK_01"]["dynamic"]["position_s"]
    assert snap["freshness"] == "NOT_EVALUATED"
    assert snap["quality"] == "GOOD"


def test_simulation_domain_has_no_reference_before_first_sync(store, ingestor):
    """Without a simulation sync there is no SIMULATION reference time - and none is invented."""
    assert store.simulation_now is None
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_fields(
        "TRUCK_02",
        {"position_s": Sourced(value=5.0, timestamp=118.0, source=Source.SIMULATION,
                               quality=Quality.GOOD, clock_domain=ClockDomain.SIMULATION)},
    )
    snap = store.get_state_snapshot()["vehicles"]["TRUCK_02"]["dynamic"]["position_s"]
    assert snap["freshness"] == "NOT_EVALUATED"
    assert snap["age_s"] is None
    assert snap["quality"] == "GOOD"


# ---------------------------------------------------------------------
# 11. simulator determinism unchanged
# ---------------------------------------------------------------------

def test_real_simulator_determinism_and_domains_unchanged(clock):
    from run_baseline_vs_orchestrator import build_graph, load_configs
    from twin.simulator import Simulator

    def run(steps):
        vehicle_cfg, roads_cfg, nodes_cfg, weather_cfg, scenario_cfg = load_configs()
        sim = Simulator(build_graph(nodes_cfg, roads_cfg), vehicle_cfg, weather_cfg, dict(scenario_cfg))
        for _ in range(steps):
            sim.run_step()
        return sim

    a, b = run(40), run(40)
    # Deterministic: identical simulator state from identical inputs.
    assert a.current_time == b.current_time
    assert [v.position_s for v in a.vehicles] == [v.position_s for v in b.vehicles]
    assert [v.speed_mps for v in a.vehicles] == [v.speed_mps for v in b.vehicles]

    store = TwinStateStore(network=a.network, mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)
    for v in a.vehicles:
        store.register_vehicle(v)
    store.sync_from_simulation(a)

    # The store adopted the simulator's own clock, unconverted.
    assert store.simulation_now == pytest.approx(a.current_time)
    snap = store.get_state_snapshot()
    assert snap["simulation_time"] == pytest.approx(a.current_time)

    first = a.vehicles[0].id
    assert snap["vehicles"][first]["dynamic"]["position_s"]["clock_domain"] == "SIMULATION"
    assert snap["vehicles"][first]["dynamic"]["position_s"]["quality"] != "STALE"
    assert snap["roads"]["ROAD_2"]["dynamic"]["visibility_m"]["clock_domain"] == "SIMULATION"
