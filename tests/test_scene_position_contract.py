"""
MAP-02 — Digital Twin SCENE POSITION contract, backend side.

SOFTWARE ONLY. Every coordinate here is invented by `scene_position_sim`. No GNSS
receiver exists on this prototype, nothing physical was executed, and no test below
constitutes hardware verification.

    A SCENE POSE IS A DEMONSTRATION COORDINATE. IT IS NEVER A FIX.

Pins:
  - the simulation is deterministic, places both demo trucks well apart, keeps them
    inside the published extent, and refuses unknown vehicles;
  - a scene pose ingested through the canonical boundary lands in the Twin stamped
    SIMULATION / SIMULATION on EVERY ingress - including with `is_simulated=False` -
    because no branch can promote it;
  - `position_scene` is in NEVER_FROM_HARDWARE, so the ordinary `put()` path refuses it;
  - the projection exposes it, and it never claims GNSS/GPS/physical/surveyed wording;
  - TRUCK_01's LOCAL_ODOMETRY contract is untouched by any of this.
"""
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "SYNQRA_SIH2026-27-main")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scene_position_sim import (  # noqa: E402
    DEMO_SCENE_VEHICLES,
    EXTENT_SPAN_X_M,
    EXTENT_SPAN_Y_M,
    SCENE_FRAME,
    scene_position,
    scene_telemetry_fields,
)
from telemetry_ingest import NEVER_FROM_HARDWARE, TelemetryIngestor, Transport  # noqa: E402
from twin.twin_state_store import Source, TwinMode, TwinStateStore, UNAVAILABLE  # noqa: E402
from twin_projection import VEHICLE_PROJECTION_FIELDS, build_vehicle_projection  # noqa: E402

FORBIDDEN_WORDS = ("GNSS", "GPS", "PHYSICAL", "SURVEYED", "HARDWARE")


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


@pytest.fixture
def ingestor(store, clock):
    return TelemetryIngestor(store, clock=clock)


def frame(vehicle_id, seq=1, t_s=30.0, **over):
    """A SIMULATED telemetry frame carrying the demo scene pose."""
    f = {
        "vehicle_id": vehicle_id, "sequence": seq, "rpm": 1450.0, "speed": 7.8,
        "source": "DIRECT_WIFI",
    }
    f.update(scene_telemetry_fields(vehicle_id, t_s))
    f.update(over)
    return f


class TestSimulation:
    def test_both_demo_trucks_have_a_pose_and_it_is_deterministic(self):
        assert set(DEMO_SCENE_VEHICLES) == {"TRUCK_01", "TRUCK_02"}
        for vehicle_id in DEMO_SCENE_VEHICLES:
            first = scene_position(vehicle_id, 42.0)
            assert first is not None
            assert first == scene_position(vehicle_id, 42.0)
            assert first["frame"] == SCENE_FRAME

    def test_the_two_trucks_are_far_enough_apart_to_see_separately(self):
        for t_s in (0.0, 17.0, 61.0, 140.0, 300.0):
            a = scene_position("TRUCK_01", t_s)
            b = scene_position("TRUCK_02", t_s)
            assert a is not None and b is not None
            separation = math.dist((a["x_m"], a["y_m"]), (b["x_m"], b["y_m"]))
            assert separation > 500.0, (t_s, separation)

    def test_every_pose_stays_inside_the_published_extent(self):
        for vehicle_id in DEMO_SCENE_VEHICLES:
            for step in range(0, 600, 11):
                pose = scene_position(vehicle_id, float(step))
                assert pose is not None
                assert 0.0 < pose["x_m"] < EXTENT_SPAN_X_M
                assert 0.0 < pose["y_m"] < EXTENT_SPAN_Y_M

    def test_the_vehicles_actually_move(self):
        start = scene_position("TRUCK_01", 0.0)
        later = scene_position("TRUCK_01", 30.0)
        assert start is not None and later is not None
        assert math.dist((start["x_m"], start["y_m"]), (later["x_m"], later["y_m"])) > 100.0

    def test_an_unknown_vehicle_gets_nothing(self):
        assert scene_position("TRUCK_99", 0.0) is None
        assert scene_telemetry_fields("TRUCK_99", 0.0) == {}


class TestIngestion:
    def test_both_trucks_reach_the_twin_as_simulation(self, ingestor, store):
        for vehicle_id in ("TRUCK_01", "TRUCK_02"):
            assert ingestor.ingest_http_payload(frame(vehicle_id), is_simulated=True).accepted
            field = store.get_vehicle_field(vehicle_id, "position_scene")
            assert field is not UNAVAILABLE
            assert field.source is Source.SIMULATION
            assert field.origin is Source.SIMULATION
            assert field.value["frame"] == SCENE_FRAME
            assert field.value["source"] == "SIMULATION"
            assert field.value["origin"] == "SIMULATION"

    def test_a_scene_pose_is_simulation_even_when_the_caller_claims_hardware(
        self, ingestor, store
    ):
        # is_simulated False is the strongest hardware claim a caller can make. A scene
        # pose is STILL simulation, because nothing measures one.
        result = ingestor.ingest_parsed_record(
            frame("TRUCK_01"), transport=Transport.DIRECT_WIFI, is_simulated=False
        )
        assert result.accepted
        field = store.get_vehicle_field("TRUCK_01", "position_scene")
        assert field.source is Source.SIMULATION
        assert field.origin is Source.SIMULATION

    def test_position_scene_is_never_hardware_measurable(self):
        assert "position_scene" in NEVER_FROM_HARDWARE

    def test_a_frame_without_a_scene_pose_leaves_the_field_absent(self, ingestor, store):
        bare = {"vehicle_id": "TRUCK_01", "sequence": 1, "rpm": 1450.0, "speed": 7.8,
                "source": "DIRECT_WIFI"}
        assert ingestor.ingest_http_payload(bare, is_simulated=True).accepted
        assert store.get_vehicle_field("TRUCK_01", "position_scene") is UNAVAILABLE

    def test_a_non_finite_pose_is_refused_rather_than_stored(self, ingestor, store):
        assert ingestor.ingest_http_payload(
            frame("TRUCK_01", scene_x_m=float("inf")), is_simulated=True
        ).accepted
        assert store.get_vehicle_field("TRUCK_01", "position_scene") is UNAVAILABLE

    def test_a_scene_pose_creates_no_gnss_fix(self, ingestor, store):
        assert ingestor.ingest_http_payload(frame("TRUCK_01"), is_simulated=True).accepted
        # The scene pose must not leak into the geographic contract.
        assert store.get_vehicle_field("TRUCK_01", "position_gnss") is UNAVAILABLE


class TestProjection:
    def test_the_projection_exposes_the_scene_pose(self, ingestor, store):
        assert "position_scene" in VEHICLE_PROJECTION_FIELDS
        assert ingestor.ingest_http_payload(frame("TRUCK_02"), is_simulated=True).accepted
        projected = build_vehicle_projection(store, "TRUCK_02")["dynamic"]["position_scene"]
        assert projected["source"] == "SIMULATION"
        assert projected["origin"] == "SIMULATION"
        assert projected["freshness"] == "CURRENT"
        assert projected["value"]["method"] == "DIGITAL_TWIN_SCENE_SIM"

    def test_the_scene_pose_never_uses_measurement_wording(self, ingestor, store):
        assert ingestor.ingest_http_payload(frame("TRUCK_01"), is_simulated=True).accepted
        value = build_vehicle_projection(store, "TRUCK_01")["dynamic"]["position_scene"]["value"]
        # The reason is allowed to say what it is NOT ("not a GNSS fix"); the provenance
        # fields a consumer branches on are what must never carry the words.
        for key in ("frame", "status", "source", "origin", "provenance_label", "method"):
            upper = str(value[key]).upper()
            for word in FORBIDDEN_WORDS:
                assert word not in upper, (key, value[key])

    def test_truck01_local_odometry_is_unchanged_by_a_scene_pose(self, ingestor, store):
        assert ingestor.ingest_http_payload(
            frame("TRUCK_01", pulse_count=120, delta_pulses=12), is_simulated=True
        ).accepted
        odom = store.get_vehicle_field("TRUCK_01", "position_odom")
        assert odom is not UNAVAILABLE
        # Still its own local frame, still carrying no latitude/longitude.
        assert "latitude" not in odom.value and "longitude" not in odom.value
        assert odom.value.get("origin_type") != SCENE_FRAME


# ===========================================================================
# MINECAST-02 — route-following motion
# ===========================================================================

from scene_position_sim import ROUTES_PATH, ROUTE_DISCLOSURE, _ROUTES, route_speed_mps  # noqa: E402
from integration_adapters.unit_converter import UnitConverter  # noqa: E402


class TestRouteFollowing:
    def test_routes_come_from_the_frontend_export_with_synthetic_disclosure(self):
        import json
        with open(ROUTES_PATH, encoding="utf-8") as fh:
            doc = json.load(fh)
        assert doc["_provenance"]["source"] == "SYNTHETIC_FOR_DEMO"
        assert doc["_provenance"]["frame"] == "SCENE_METRES"
        assert "NOT NMDC INFRASTRUCTURE" in ROUTE_DISCLOSURE
        assert {r["vehicle_id"] for r in doc["routes"]} == {"TRUCK_01", "TRUCK_02"}
        # The follower owns no geometry: every waypoint it uses came from that file.
        for raw in doc["routes"]:
            assert _ROUTES[raw["vehicle_id"]].waypoints == [tuple(p) for p in raw["waypoints"]]

    def test_4_position_changes_with_elapsed_time_and_only_with_it(self):
        a = scene_position("TRUCK_01", 5.0)
        b = scene_position("TRUCK_01", 25.0)
        again = scene_position("TRUCK_01", 5.0)
        assert a is not None and b is not None
        assert math.dist((a["x_m"], a["y_m"]), (b["x_m"], b["y_m"])) > 50.0
        assert a == again, "same t, same pose - nothing but elapsed time moves a truck"

    def test_5_motion_is_continuous_not_random(self):
        # Consecutive 1 s samples must be within speed * 1 s of each other, for a long while.
        for vehicle_id in DEMO_SCENE_VEHICLES:
            speed = _ROUTES[vehicle_id].speed_mps
            prev = scene_position(vehicle_id, 0.0)
            for t in range(1, 1800):
                cur = scene_position(vehicle_id, float(t))
                assert prev is not None and cur is not None
                step = math.dist((prev["x_m"], prev["y_m"]), (cur["x_m"], cur["y_m"]))
                assert step <= speed * 1.0 + 0.005, (vehicle_id, t, step)  # 3-dp rounding on both endpoints
                prev = cur

    def test_7_heading_follows_the_direction_of_travel(self):
        for vehicle_id in DEMO_SCENE_VEHICLES:
            for t in (3.0, 47.0, 120.0, 400.0):
                a = scene_position(vehicle_id, t)
                b = scene_position(vehicle_id, t + 0.25)
                assert a is not None and b is not None
                dx, dy = b["x_m"] - a["x_m"], b["y_m"] - a["y_m"]
                if math.hypot(dx, dy) < 0.05:
                    continue  # sitting on a waypoint corner; direction undefined here
                travel = math.atan2(dy, dx)
                diff = abs(math.atan2(math.sin(a["heading_rad"] - travel), math.cos(a["heading_rad"] - travel)))
                # Within a corner's worth of turn; a waypoint change can fall inside 0.25 s.
                assert diff < 0.6, (vehicle_id, t, a["heading_rad"], travel)

    def test_ping_pong_turnaround_is_continuous_and_reverses_heading(self):
        # MINE-ROUTES-02: TRUCK_01 became a closed LOOP (ore cycle); its end-of-route
        # behaviour is asserted by test_loop_wrap_is_continuous below. Only PING_PONG
        # routes turn around.
        ping_pong = [v for v in DEMO_SCENE_VEHICLES if _ROUTES[v].behaviour == "PING_PONG"]
        assert ping_pong, "at least one demonstration route must be PING_PONG"
        for vehicle_id in ping_pong:
            route = _ROUTES[vehicle_id]
            t_turn = (route.length_m - route.start_progress_m) / route.speed_mps
            before = scene_position(vehicle_id, t_turn - 1.0)
            after = scene_position(vehicle_id, t_turn + 1.0)
            assert before is not None and after is not None
            assert before["direction"] == 1 and after["direction"] == -1
            # No teleport: two seconds of travel at most.
            assert math.dist((before["x_m"], before["y_m"]), (after["x_m"], after["y_m"])) <= route.speed_mps * 2.0 + 1e-6
            # And the truck now points back the way it came.
            flip = abs(math.atan2(math.sin(before["heading_rad"] - after["heading_rad"]),
                                  math.cos(before["heading_rad"] - after["heading_rad"])))
            assert flip > math.pi - 0.6

    def test_loop_wrap_is_continuous(self):
        """MINE-ROUTES-02: a LOOP route wraps without a teleport and never reverses."""
        loops = [v for v in DEMO_SCENE_VEHICLES if _ROUTES[v].behaviour == "LOOP"]
        assert loops, "TRUCK_01's ore cycle must be a closed LOOP"
        for vehicle_id in loops:
            route = _ROUTES[vehicle_id]
            t_wrap = (route.length_m - route.start_progress_m) / route.speed_mps
            before = scene_position(vehicle_id, t_wrap - 1.0)
            after = scene_position(vehicle_id, t_wrap + 1.0)
            assert before is not None and after is not None
            assert before["direction"] == 1 and after["direction"] == 1
            assert math.dist((before["x_m"], before["y_m"]), (after["x_m"], after["y_m"])) <= route.speed_mps * 2.0 + 1e-6

    def test_route_metadata_is_stamped_on_every_pose(self):
        """MINE-ROUTES-02: route id, classification and direction ride on the pose."""
        for vehicle_id in DEMO_SCENE_VEHICLES:
            pose = scene_position(vehicle_id, 33.0)
            assert pose is not None
            assert pose["route_id"].startswith("SYNTH-ROUTE-")
            assert pose["route_classification"] == "SYNTHETIC_DIGITAL_TWIN_ROUTE"
            assert pose["direction"] in (-1, 1)
            fields = scene_telemetry_fields(vehicle_id, 33.0)
            assert fields["scene_route_id"] == pose["route_id"]
            assert fields["scene_route_direction"] == pose["direction"]

    def test_route_id_and_direction_reach_the_twin(self, ingestor, store):
        """The Twin's position_scene carries the route metadata, still SIMULATION."""
        for vehicle_id in DEMO_SCENE_VEHICLES:
            assert ingestor.ingest_http_payload(frame(vehicle_id, t_s=33.0), is_simulated=True).accepted
            field = store.get_vehicle_field(vehicle_id, "position_scene")
            assert field.source is Source.SIMULATION
            assert field.value["route_id"] == scene_position(vehicle_id, 33.0)["route_id"]
            assert field.value["route_direction"] in (-1, 1)
            assert field.value["route_classification"] == "SYNTHETIC_DIGITAL_TWIN_ROUTE"

    def test_11_12_13_provenance_frame_and_no_gnss_survive_route_following(self, ingestor, store):
        for vehicle_id in DEMO_SCENE_VEHICLES:
            assert ingestor.ingest_http_payload(frame(vehicle_id, t_s=77.0), is_simulated=True).accepted
            field = store.get_vehicle_field(vehicle_id, "position_scene")
            assert field.source is Source.SIMULATION and field.origin is Source.SIMULATION
            assert field.value["frame"] == SCENE_FRAME
            assert store.get_vehicle_field(vehicle_id, "position_gnss") is UNAVAILABLE
            pose = scene_position(vehicle_id, 77.0)
            assert pose is not None
            for key in ("frame", "status", "source", "origin", "provenance_label", "method", "route_id"):
                for word in FORBIDDEN_WORDS:
                    assert word not in str(pose[key]).upper(), (key, pose[key])


class TestSpeedSynchronization:
    """
    DIGITAL-TWIN-OPERATIONAL-FLOW-01 - the displayed SIMULATION speed and the scene-route
    progression are the same simulation state. Nothing physical is touched.
    """

    def test_route_progression_corresponds_to_the_declared_simulation_speed(self):
        for vehicle_id in DEMO_SCENE_VEHICLES:
            v = route_speed_mps(vehicle_id)
            assert v is not None and v > 0
            assert v == _ROUTES[vehicle_id].speed_mps
            # Distance actually travelled along the route over a clean interval == v * dt,
            # measured on the pose progress the follower reports (not on chord length).
            a = scene_position(vehicle_id, 10.0)
            b = scene_position(vehicle_id, 14.0)
            assert a is not None and b is not None
            if a["direction"] == b["direction"] and b["progress_m"] >= a["progress_m"]:
                assert abs((b["progress_m"] - a["progress_m"]) - v * 4.0) < 0.01
        assert route_speed_mps("TRUCK_99") is None

    def test_route_speed_is_deterministic_and_not_wall_clock_dependent(self):
        first = [route_speed_mps(v) for v in DEMO_SCENE_VEHICLES]
        second = [route_speed_mps(v) for v in DEMO_SCENE_VEHICLES]
        assert first == second
        import inspect
        import scene_position_sim
        src = inspect.getsource(scene_position_sim)
        assert "random" not in src.replace("randomised", "").replace("no RNG", "")
        assert "time.time()" not in src

    def test_inverse_rpm_round_trips_through_the_one_calibration(self):
        uc = UnitConverter()
        for vehicle_id in DEMO_SCENE_VEHICLES:
            v = route_speed_mps(vehicle_id)
            rpm = uc.speed_mps_to_rpm(vehicle_id, v)
            assert rpm is not None and rpm > 0
            assert abs(uc.rpm_to_speed_mps(vehicle_id, rpm) - v) < 1e-3
        assert uc.speed_mps_to_rpm("TRUCK_99", 1.0) is None
        assert uc.speed_mps_to_rpm("TRUCK_01", -1.0) is None

    def test_displayed_simulation_speed_is_simulation_never_hardware(self, ingestor, store):
        """The producer's frame (route speed + matching RPM) lands in the Twin as SIMULATION."""
        uc = UnitConverter()
        for vehicle_id in DEMO_SCENE_VEHICLES:
            v = route_speed_mps(vehicle_id)
            f = frame(vehicle_id, t_s=12.0, speed_mps=v, rpm=uc.speed_mps_to_rpm(vehicle_id, v))
            f.pop("speed", None)
            assert ingestor.ingest_http_payload(f, is_simulated=True).accepted
            field = store.get_vehicle_field(vehicle_id, "speed_mps")
            assert field is not UNAVAILABLE
            assert field.source is Source.SIMULATION
            assert field.source is not Source.HARDWARE
            # The canonical (RPM-derived) speed equals the route speed the pose advances at.
            assert abs(field.value - v) < 1e-3
            # The reported value lands under the vehicle's own reported-speed field
            # (TRUCK_02's is PWM-derived by contract); either way it is SIMULATION.
            reported = store.get_vehicle_field(vehicle_id, "speed_mps_reported")
            if reported is UNAVAILABLE:
                reported = store.get_vehicle_field(vehicle_id, "speed_mps_pwm_derived")
            assert reported is not UNAVAILABLE and reported.source is Source.SIMULATION

    def test_physical_telemetry_path_is_unchanged(self, ingestor, store):
        """A hardware-transport frame still derives HARDWARE-provenance speed from its own RPM."""
        payload = {"vehicle_id": "TRUCK_01", "sequence": 5, "rpm": 240.0, "speed": 1.25,
                   "source": "DIRECT_WIFI"}
        assert ingestor.ingest_http_payload(payload, is_simulated=False).accepted
        field = store.get_vehicle_field("TRUCK_01", "speed_mps")
        assert field.source is not Source.SIMULATION
        # Derived from the hardware RPM via the calibrated radius, never from a route.
        assert abs(field.value - UnitConverter().rpm_to_speed_mps("TRUCK_01", 240.0)) < 1e-6
        assert field.value != route_speed_mps("TRUCK_01")
