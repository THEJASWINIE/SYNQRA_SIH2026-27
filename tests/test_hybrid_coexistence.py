"""
P4 — simulation / hardware coexistence in ONE canonical Twin.

All hardware-shaped data here is REPLAYED / EMULATED. No physical ESP32 was connected or
exercised. Nothing in this file is a physical hardware validation.

The rule under test:

    For the SAME vehicle and the SAME field,
    a valid & current HARDWARE-backed observation outranks a SIMULATION value.

Field-level, not entity-level: a hardware truck keeps simulated position beside its
measured RPM.
"""

import threading

import pytest

from telemetry_ingest import TelemetryIngestor, Transport
from twin.twin_state_store import (
    SIMULATION_FALLBACK_FIELDS,
    Quality,
    Source,
    Sourced,
    TwinMode,
    TwinStateStore,
    UNAVAILABLE,
)


class FixedClock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class SimVehicle:
    """Attribute surface of models.vehicle.Vehicle (the simulator's own object)."""

    def __init__(self, vehicle_id, position_s=40.0, speed_mps=7.5):
        self.id = vehicle_id
        self.tare_mass = 74000.0
        self.payload_capacity = 91000.0
        self.length = 10.52
        self.width = 5.52
        self.wheelbase = 5.25
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
# 1/2/3. one Twin, both registration paths
# ---------------------------------------------------------------------

def test_one_twin_holds_simulation_and_hardware_vehicles(store, ingestor, clock):
    sim_truck = SimVehicle("TRUCK_01")
    store.register_vehicle(sim_truck)                       # simulator registration
    store.sync_from_simulation(vehicles=[sim_truck], fog_model=SimFog(), timestamp=clock.t)

    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)  # hardware registration

    assert set(store.get_all_vehicles()) == {"TRUCK_01", "TRUCK_02"}
    assert store.mode is TwinMode.HYBRID
    assert store.get_vehicle_field("TRUCK_01", "position_s").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE


def test_hardware_vehicle_needs_no_simulation_object(store, ingestor):
    ingestor.ingest_parsed_record(hw("TRUCK_02"), Transport.DIRECT_WIFI)
    assert store.get_vehicle("TRUCK_02").domain_vehicle is None
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 180.0


# ---------------------------------------------------------------------
# 4/6/11. field-level precedence, not entity-level
# ---------------------------------------------------------------------

def test_hardware_field_survives_later_simulation_sync(store, ingestor, clock):
    """HARDWARE first, SIMULATION later: the measured field must not be overwritten."""
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    sim_truck = SimVehicle("TRUCK_02", speed_mps=7.5)
    sim_truck.rpm = 999.0                                   # simulation tries to supply rpm
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 180.0
    assert rpm.source is Source.HARDWARE


def test_simulation_field_arrives_first_then_hardware_wins(store, ingestor, clock):
    """SIMULATION first, HARDWARE later: the measurement takes over the field."""
    sim_truck = SimVehicle("TRUCK_02", speed_mps=7.5)
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").source is Source.SIMULATION

    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    speed = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert speed.is_hardware_backed()                       # derived from measured rpm
    assert speed.source is Source.DERIVED
    assert speed.value != 7.5


def test_precedence_is_field_level_not_entity_level(store, ingestor, clock):
    """
    THE CORE P4 GUARANTEE.

    A hardware truck keeps its measured fields AND its simulated fields, each with its
    own provenance. Hardware does not take over the whole entity.
    """
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    sim_truck = SimVehicle("TRUCK_02", position_s=40.0)
    store.sync_from_simulation(vehicles=[sim_truck], fog_model=SimFog(), timestamp=clock.t)

    v = store.get_vehicle("TRUCK_02")
    # measured, protected
    assert v.get("rpm").value == 180.0 and v.get("rpm").source is Source.HARDWARE
    assert v.get("ax_mps2").source is Source.HARDWARE
    assert v.get("rssi_dbm").source is Source.HARDWARE
    # simulated, coexisting on the SAME vehicle
    assert v.get("position_s").value == 40.0 and v.get("position_s").source is Source.SIMULATION
    assert v.get("road_id").value == "ROAD_2" and v.get("road_id").source is Source.SIMULATION
    assert v.get("state").source is Source.SIMULATION
    # solver outputs stay DERIVED even though the vehicle object is simulated
    assert v.get("v_safe_mps").source is Source.DERIVED
    assert v.get("v_command_mps").source is Source.DERIVED


def test_unrelated_fields_update_independently(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)
    sim_truck = SimVehicle("TRUCK_02", position_s=40.0)
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    # Simulation advances position; measured rpm is untouched.
    sim_truck.position_s = 95.0
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t + 1.0)
    assert store.get_vehicle_field("TRUCK_02", "position_s").value == 95.0
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 180.0

    # New telemetry advances rpm; simulated position is untouched.
    ingestor.ingest_parsed_record(hw("TRUCK_02", 2, rpm=200.0), Transport.DIRECT_WIFI)
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 200.0
    assert store.get_vehicle_field("TRUCK_02", "position_s").value == 95.0


# ---------------------------------------------------------------------
# 3(HW newer / SIM newer). freshness, not arrival order
# ---------------------------------------------------------------------

def test_newer_simulation_still_loses_to_current_hardware(store, ingestor, clock):
    """A *newer* simulation timestamp does not beat a current hardware observation."""
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    sim_truck = SimVehicle("TRUCK_02")
    sim_truck.rpm = 42.0
    clock.advance(1.0)                                       # sim value is strictly newer
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 180.0


# ---------------------------------------------------------------------
# 5/8/9. stale and invalid hardware
# ---------------------------------------------------------------------

def test_stale_hardware_allows_explicit_simulation_fallback(store, ingestor, clock):
    """
    Fallback is allowed ONLY for fields on the explicit allowlist, and the takeover is
    visible: provenance flips to SIMULATION, so no false HARDWARE label survives.
    """
    assert "speed_mps" in SIMULATION_FALLBACK_FIELDS

    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)
    hw_speed = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert hw_speed.is_hardware_backed()

    clock.advance(10.0)                                       # past stale_after_s = 3.0
    assert not store.get_vehicle_field("TRUCK_02", "speed_mps").is_current(clock.t, 3.0)

    sim_truck = SimVehicle("TRUCK_02", speed_mps=7.5)
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    took_over = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert took_over.value == 7.5
    assert took_over.source is Source.SIMULATION              # transition is observable
    assert not took_over.is_hardware_backed()                 # no false HARDWARE label


def test_stale_hardware_measurement_is_not_replaced_by_simulation(store, ingestor, clock):
    """
    A measured quantity NOT on the fallback allowlist stays put even when stale. Reading
    STALE is the honest answer; quietly substituting a simulated RPM is not.
    """
    assert "rpm" not in SIMULATION_FALLBACK_FIELDS

    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)
    clock.advance(10.0)

    sim_truck = SimVehicle("TRUCK_02")
    sim_truck.rpm = 42.0
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 180.0
    assert rpm.source is Source.HARDWARE
    assert rpm.effective_quality(clock.t, 3.0) is Quality.STALE   # visibly stale


def test_invalid_hardware_allows_fallback_on_permitted_field(store, clock):
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_fields(
        "TRUCK_02",
        {"speed_mps": Sourced(value=2.0, timestamp=clock.t, source=Source.DERIVED,
                              quality=Quality.INVALID, origin=Source.HARDWARE)},
    )
    assert not store.get_vehicle_field("TRUCK_02", "speed_mps").is_current(clock.t, 3.0)

    sim_truck = SimVehicle("TRUCK_02", speed_mps=7.5)
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    got = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert got.value == 7.5
    assert got.source is Source.SIMULATION


def test_degraded_hardware_still_outranks_simulation(store, clock):
    """DEGRADED is still valid and current - it must not hand the field to simulation."""
    store.register_vehicle("TRUCK_02")
    store.update_vehicle_fields(
        "TRUCK_02",
        {"speed_mps": Sourced(value=2.0, timestamp=clock.t, source=Source.DERIVED,
                              quality=Quality.DEGRADED, origin=Source.HARDWARE)},
    )
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02", speed_mps=7.5)], timestamp=clock.t)

    got = store.get_vehicle_field("TRUCK_02", "speed_mps")
    assert got.value == 2.0
    assert got.is_hardware_backed()


# ---------------------------------------------------------------------
# 6/7. hardware provenance and quality survive simulator sync
# ---------------------------------------------------------------------

def test_hardware_provenance_and_quality_survive_sync(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, data_quality="DELAYED"), Transport.DIRECT_WIFI)
    before = store.get_vehicle_field("TRUCK_02", "rpm")
    assert before.quality is Quality.DEGRADED

    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], fog_model=SimFog(), timestamp=clock.t)

    after = store.get_vehicle_field("TRUCK_02", "rpm")
    assert after.source is Source.HARDWARE
    assert after.quality is Quality.DEGRADED
    assert after.timestamp == before.timestamp


def test_source_and_quality_survive_snapshots(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1), Transport.DIRECT_WIFI)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], fog_model=SimFog(), timestamp=clock.t)

    snap = store.get_state_snapshot(now=clock.t)["vehicles"]["TRUCK_02"]["dynamic"]
    assert snap["rpm"]["source"] == "HARDWARE"
    assert snap["rpm"]["quality"] == "GOOD"
    assert snap["position_s"]["source"] == "SIMULATION"
    assert snap["v_safe_mps"]["source"] == "DERIVED"


# ---------------------------------------------------------------------
# 10. no fabricated hardware-only fields
# ---------------------------------------------------------------------

def test_simulation_supplied_environment_is_labelled_simulation(store, ingestor, clock):
    """
    Position / visibility / road are unavailable from this prototype's hardware. They may
    come from simulation, but ONLY with source=SIMULATION.
    """
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1), Transport.DIRECT_WIFI)
    for name in ("position_s", "road_id"):
        assert store.get_vehicle_field("TRUCK_02", name) is UNAVAILABLE

    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], fog_model=SimFog(), timestamp=clock.t)

    for name in ("position_s", "road_id"):
        got = store.get_vehicle_field("TRUCK_02", name)
        assert got.is_available
        assert got.source is Source.SIMULATION
        assert not got.is_hardware_backed()

    env = store.get_environment().get("visibility_m")
    assert env.value == 15.0
    assert env.source is Source.SIMULATION


def test_hardware_only_fields_are_never_invented_by_sync(store, clock):
    """A purely simulated vehicle gains no measured fields from a simulator sync."""
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=clock.t)
    for name in ("rpm", "ax_mps2", "gx_rad_s", "rssi_dbm", "heading_rad"):
        assert store.get_vehicle_field("TRUCK_01", name) is UNAVAILABLE


# ---------------------------------------------------------------------
# 12. transport sequences must not arbitrate provenance
# ---------------------------------------------------------------------

def test_transport_sequence_numbers_do_not_arbitrate_provenance(store, ingestor, clock):
    """
    Sequence counters are transport-specific. A simulation carrying a huge 'sequence' must
    not win a field just because its counter is larger.
    """
    ingestor.ingest_parsed_record(hw("TRUCK_02", 5, rpm=180.0), Transport.DIRECT_WIFI)

    sim_truck = SimVehicle("TRUCK_02")
    sim_truck.rpm = 1.0
    sim_truck.sequence = 999_999
    store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 180.0
    assert rpm.source is Source.HARDWARE
    # The Twin's own sequence field still reflects the telemetry that set it.
    assert store.get_vehicle_field("TRUCK_02", "sequence").value == 5


def test_out_of_order_and_duplicate_still_cannot_corrupt_hybrid_state(store, ingestor, clock):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 10, rpm=180.0), Transport.DIRECT_WIFI)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], fog_model=SimFog(), timestamp=clock.t)
    before = store.get_state_snapshot(now=clock.t)

    assert not ingestor.ingest_parsed_record(hw("TRUCK_02", 10, rpm=1.0), Transport.DIRECT_WIFI).accepted
    assert not ingestor.ingest_parsed_record(hw("TRUCK_02", 4, rpm=2.0), Transport.DIRECT_WIFI).accepted

    assert store.get_state_snapshot(now=clock.t) == before


# ---------------------------------------------------------------------
# The required deterministic HYBRID scenario
# ---------------------------------------------------------------------

def test_hybrid_scenario_sim_then_hardware_then_sim(store, ingestor, clock):
    """
    Initial: TRUCK_01 = SIMULATION, TRUCK_02 = HARDWARE
    Then:    simulator updates both -> hardware packet updates TRUCK_02 -> simulator again
    """
    truck1 = SimVehicle("TRUCK_01", position_s=10.0, speed_mps=6.0)
    truck2 = SimVehicle("TRUCK_02", position_s=20.0, speed_mps=7.0)

    # --- initial state
    store.sync_from_simulation(vehicles=[truck1, truck2], fog_model=SimFog(), timestamp=clock.t)
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    # --- simulator updates both
    clock.advance(1.0)
    truck1.position_s, truck2.position_s = 15.0, 25.0
    store.sync_from_simulation(vehicles=[truck1, truck2], fog_model=SimFog(), timestamp=clock.t)

    # --- hardware packet updates TRUCK_02
    clock.advance(1.0)
    ingestor.ingest_parsed_record(hw("TRUCK_02", 2, rpm=190.0), Transport.DIRECT_WIFI)

    # --- simulator updates again
    clock.advance(1.0)
    truck1.position_s, truck2.position_s = 20.0, 30.0
    store.sync_from_simulation(vehicles=[truck1, truck2], fog_model=SimFog(), timestamp=clock.t)

    # TRUCK_02 hardware-originated fields remain hardware-originated
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 190.0
    assert store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE
    assert store.get_vehicle_field("TRUCK_02", "ax_mps2").source is Source.HARDWARE
    assert store.get_vehicle_field("TRUCK_02", "rssi_dbm").source is Source.HARDWARE

    # TRUCK_02 simulation-only fields remain simulation-originated and kept advancing
    assert store.get_vehicle_field("TRUCK_02", "position_s").value == 30.0
    assert store.get_vehicle_field("TRUCK_02", "position_s").source is Source.SIMULATION

    # TRUCK_01 is entirely simulation-originated, with no invented measurements
    assert store.get_vehicle_field("TRUCK_01", "position_s").value == 20.0
    assert store.get_vehicle_field("TRUCK_01", "position_s").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_01", "rpm") is UNAVAILABLE

    # ...and the whole thing is one Twin in HYBRID mode
    snap = store.get_state_snapshot(now=clock.t)
    assert snap["mode"] == "HYBRID"
    assert set(snap["vehicles"]) == {"TRUCK_01", "TRUCK_02"}


# ---------------------------------------------------------------------
# 13. concurrency
# ---------------------------------------------------------------------

def test_concurrent_simulation_and_hardware_updates_stay_atomic(store, clock):
    ingestor = TelemetryIngestor(store, clock=clock)
    sim_truck = SimVehicle("TRUCK_02")
    errors = []

    def sim_writer():
        try:
            for i in range(60):
                sim_truck.position_s = float(i)
                store.sync_from_simulation(vehicles=[sim_truck], timestamp=clock.t)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def hw_writer():
        try:
            for seq in range(1, 61):
                ingestor.ingest_parsed_record(
                    hw("TRUCK_02", seq, rpm=float(100 + seq)), Transport.DIRECT_WIFI
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=sim_writer), threading.Thread(target=hw_writer)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    dynamic = store.get_state_snapshot(now=clock.t)["vehicles"]["TRUCK_02"]["dynamic"]
    # Measured rpm survived every simulation sync, and rpm/sequence remain consistent.
    assert dynamic["rpm"]["source"] == "HARDWARE"
    assert dynamic["rpm"]["value"] == 100.0 + dynamic["sequence"]["value"]
    assert dynamic["position_s"]["source"] == "SIMULATION"


# ---------------------------------------------------------------------
# Integration with the REAL simulator (no simulator changes)
# ---------------------------------------------------------------------

def test_real_simulator_coexists_with_hardware_vehicle(clock):
    from run_baseline_vs_orchestrator import build_graph, load_configs
    from twin.simulator import Simulator

    vehicle_cfg, roads_cfg, nodes_cfg, weather_cfg, scenario_cfg = load_configs()
    sim = Simulator(build_graph(nodes_cfg, roads_cfg), vehicle_cfg, weather_cfg, dict(scenario_cfg))

    store = TwinStateStore(network=sim.network, mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)
    ingestor = TelemetryIngestor(store, clock=clock)

    for v in sim.vehicles:
        store.register_vehicle(v)

    # TRUCK_02 exists in the simulation fleet AND reports real telemetry.
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=180.0), Transport.DIRECT_WIFI)

    for _ in range(20):
        sim.run_step()
    store.sync_from_simulation(sim)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 180.0
    assert rpm.source is Source.HARDWARE          # 20 simulator steps did not clobber it

    # Simulation-owned fields for the same vehicle did advance.
    assert store.get_vehicle_field("TRUCK_02", "state").source is Source.SIMULATION
    # Physics output stays DERIVED (P2 authority), not relabelled SIMULATION.
    assert store.get_vehicle_field("TRUCK_02", "v_safe_mps").source is Source.DERIVED
