"""
P5 — command gateway hardening.

Everything here is SIMULATION / EMULATOR. No physical ESP32 was connected or exercised.
Emulator execution is NOT physical hardware validation.
"""

import threading

import pytest

from command_gateway import (
    CommandGateway,
    CommandSource,
    CommandStatus,
    VehicleCommand,
)
from twin.twin_state_store import (
    ClockDomain,
    Quality,
    Source,
    Sourced,
    TwinMode,
    TwinStateStore,
)

WALL_NOW = 1_788_000_000.0


class FixedClock:
    def __init__(self, t=WALL_NOW):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def store(clock):
    return TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)


def set_v_safe(store, vehicle_id, value, timestamp=WALL_NOW,
               quality=Quality.GOOD, domain=ClockDomain.WALL_CLOCK):
    """Place an authoritative v_safe in the Twin, as fog_safe/the simulator would."""
    if store.get_vehicle(vehicle_id) is None:
        store.register_vehicle(vehicle_id)
    store.update_vehicle_fields(
        vehicle_id,
        {"v_safe_mps": Sourced(value=value, timestamp=timestamp, source=Source.DERIVED,
                               quality=quality, clock_domain=domain)},
    )


@pytest.fixture
def gateway(store, clock):
    set_v_safe(store, "TRUCK_02", 9.0)
    return CommandGateway(store=store, clock=clock)


def cmd(**over):
    base = dict(
        vehicle_id="TRUCK_02",
        command_id="CMD_1",
        created_at=WALL_NOW,
        action="TARGET_SPEED",
        target_speed_mps=5.0,
        source=CommandSource.OPERATOR,
        reason="test",
        mode="SIMULATION",
    )
    base.update(over)
    return VehicleCommand(**base)


# ---------------------------------------------------------------------
# 1/2/3. basic acceptance, unknown vehicle, missing command_id
# ---------------------------------------------------------------------

def test_valid_known_vehicle_command_is_accepted(gateway):
    result = gateway.submit(cmd())
    assert result.accepted
    assert result.status == CommandStatus.ACCEPTED
    assert gateway.get_status("CMD_1") == CommandStatus.ACCEPTED


def test_unknown_vehicle_is_rejected(gateway, store):
    result = gateway.submit(cmd(vehicle_id="TRUCK_47", command_id="CMD_X"))
    assert result.status == CommandStatus.UNKNOWN_VEHICLE
    # A command must never register a vehicle or touch Twin state.
    assert store.get_vehicle("TRUCK_47") is None
    assert gateway.get_status("CMD_X") is None


def test_missing_command_id_is_rejected(gateway):
    for bad in ("", "   ", None):
        assert gateway.submit(cmd(command_id=bad)).status == CommandStatus.INVALID


def test_missing_vehicle_id_is_rejected(gateway):
    assert gateway.submit(cmd(vehicle_id="")).status == CommandStatus.INVALID


# ---------------------------------------------------------------------
# 4/5/27. duplicates and idempotency
# ---------------------------------------------------------------------

def test_identical_duplicate_is_idempotent(gateway):
    assert gateway.submit(cmd()).accepted
    again = gateway.submit(cmd())
    assert again.status == CommandStatus.DUPLICATE
    assert "Idempotent" in again.reason
    assert gateway.stats["accepted"] == 1          # no second actuation


def test_conflicting_duplicate_is_rejected_as_duplicate(gateway):
    assert gateway.submit(cmd(target_speed_mps=5.0)).accepted
    conflict = gateway.submit(cmd(target_speed_mps=8.0))
    assert conflict.status == CommandStatus.DUPLICATE
    assert "different payload" in conflict.reason
    # The originally accepted command is unchanged.
    assert gateway.get_command("CMD_1")["command"].target_speed_mps == 5.0


def test_concurrent_duplicate_submissions_remain_idempotent(gateway):
    results = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(gateway.submit(cmd()))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    accepted = [r for r in results if r.accepted]
    assert len(accepted) == 1, "check-duplicate + register was not atomic"
    assert gateway.stats["accepted"] == 1


# ---------------------------------------------------------------------
# 6/7/25/26. freshness — wall clock only
# ---------------------------------------------------------------------

def test_stale_command_is_rejected(gateway, clock):
    old = cmd(created_at=WALL_NOW - 60.0)
    assert gateway.submit(old).status == CommandStatus.STALE


def test_command_expires_after_the_configured_validity_window(gateway, store, clock):
    # Reuses config/integration_config.json max_recommendation_age_seconds (5.0 s).
    assert gateway.validity_window_s == 5.0

    clock.advance(4.0)
    set_v_safe(store, "TRUCK_02", 9.0, timestamp=clock.t)   # a live Twin keeps v_safe fresh
    # 4 s old, still inside the 5 s validity window.
    assert gateway.submit(cmd(command_id="A", created_at=WALL_NOW)).accepted

    clock.advance(2.0)
    set_v_safe(store, "TRUCK_02", 9.0, timestamp=clock.t)
    # Same origin, now 6 s old: past the window.
    assert gateway.submit(cmd(command_id="B", created_at=WALL_NOW)).status == CommandStatus.STALE


def test_explicit_expires_at_is_honoured(gateway, clock):
    assert gateway.submit(cmd(expires_at=WALL_NOW - 1.0)).status == CommandStatus.STALE


def test_future_timestamp_is_rejected(gateway):
    assert gateway.submit(cmd(created_at=WALL_NOW + 60.0)).status == CommandStatus.INVALID


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, "abc", None])
def test_malformed_created_at_is_rejected(gateway, bad):
    assert gateway.submit(cmd(created_at=bad)).status == CommandStatus.INVALID


def test_simulation_clock_is_never_used_for_command_freshness(store, clock):
    """
    A command created at simulation time 120.0 must not be judged fresh against a
    wall-clock gateway. It is simply an ancient wall-clock timestamp, and is refused.
    """
    set_v_safe(store, "TRUCK_02", 9.0)
    gw = CommandGateway(store=store, clock=clock)
    assert gw.submit(cmd(created_at=120.0)).status == CommandStatus.STALE


# ---------------------------------------------------------------------
# 8/9/10/11. value and source validation
# ---------------------------------------------------------------------

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_target_speed_is_rejected(gateway, bad):
    assert gateway.submit(cmd(target_speed_mps=bad)).status == CommandStatus.INVALID


def test_negative_target_speed_is_rejected(gateway):
    assert gateway.submit(cmd(target_speed_mps=-1.0)).status == CommandStatus.INVALID


def test_non_numeric_target_speed_is_rejected(gateway):
    assert gateway.submit(cmd(target_speed_mps="fast")).status == CommandStatus.INVALID


def test_invalid_source_is_rejected(gateway):
    assert gateway.submit(cmd(source="ANONYMOUS")).status == CommandStatus.INVALID


def test_invalid_action_is_rejected(gateway):
    assert gateway.submit(cmd(action="LAUNCH")).status == CommandStatus.INVALID


# ---------------------------------------------------------------------
# 12–16. safety-state dependency, fail closed
# ---------------------------------------------------------------------

def test_target_above_v_safe_is_rejected(gateway, store):
    result = gateway.submit(cmd(target_speed_mps=12.0))     # v_safe is 9.0
    assert result.status == CommandStatus.REJECTED
    assert result.v_safe_mps == 9.0
    assert "exceeds authoritative v_safe" in result.reason


def test_target_at_v_safe_is_accepted(gateway):
    assert gateway.submit(cmd(target_speed_mps=9.0)).accepted


def test_unavailable_safety_state_fails_closed(store, clock):
    store.register_vehicle("TRUCK_02")                       # no v_safe at all
    gw = CommandGateway(store=store, clock=clock)
    result = gw.submit(cmd(target_speed_mps=1.0))
    assert result.status == CommandStatus.REJECTED
    assert "unavailable" in result.reason


def test_missing_twin_fails_closed(clock):
    gw = CommandGateway(store=None, clock=clock)
    assert gw.submit(cmd(target_speed_mps=1.0)).status == CommandStatus.REJECTED


def test_vehicle_absent_from_twin_fails_closed(store, clock):
    gw = CommandGateway(store=store, clock=clock)            # TRUCK_02 never registered
    assert gw.submit(cmd(target_speed_mps=1.0)).status == CommandStatus.REJECTED


def test_stale_safety_state_fails_closed(store, clock):
    set_v_safe(store, "TRUCK_02", 9.0, timestamp=WALL_NOW)
    gw = CommandGateway(store=store, clock=clock)
    clock.advance(30.0)                                       # v_safe is now stale
    result = gw.submit(cmd(target_speed_mps=1.0, created_at=clock.t))
    assert result.status == CommandStatus.REJECTED
    assert "stale or invalid" in result.reason


def test_invalid_safety_state_fails_closed(store, clock):
    set_v_safe(store, "TRUCK_02", 9.0, quality=Quality.INVALID)
    gw = CommandGateway(store=store, clock=clock)
    assert gw.submit(cmd(target_speed_mps=1.0)).status == CommandStatus.REJECTED


@pytest.mark.parametrize("action", ["STOP", "HOLD"])
def test_defensive_command_allowed_under_degraded_safety_state(store, clock, action):
    """A STOP must never be refused because the Twin is unusable."""
    store.register_vehicle("TRUCK_02")                        # no v_safe
    gw = CommandGateway(store=store, clock=clock)
    assert gw.submit(cmd(action=action, target_speed_mps=0.0)).accepted

    gw_no_twin = CommandGateway(store=None, clock=clock)
    assert gw_no_twin.submit(cmd(command_id="CMD_STOP2", action=action,
                                 target_speed_mps=0.0)).accepted


def test_gateway_does_not_compute_safety():
    """The gateway must not import or contain a safe-speed solver."""
    import inspect

    import command_gateway

    src = inspect.getsource(command_gateway)
    executable = "".join(src.split('"""')[::2])
    for banned in ("solve_safe_speed", "resolve_v_safe", "fog_safe", "math.sqrt", "np.sqrt"):
        assert banned not in executable, f"gateway appears to compute safety: {banned}"


# ---------------------------------------------------------------------
# 17. command acceptance does not mutate vehicle telemetry
# ---------------------------------------------------------------------

def test_acceptance_does_not_mutate_vehicle_state(gateway, store, clock):
    store.update_vehicle_fields(
        "TRUCK_02",
        {"speed_mps": Sourced(value=3.0, timestamp=WALL_NOW, source=Source.HARDWARE,
                              quality=Quality.GOOD, origin=Source.HARDWARE,
                              clock_domain=ClockDomain.WALL_CLOCK)},
    )
    before = store.get_state_snapshot(now=clock.t)

    assert gateway.submit(cmd(target_speed_mps=7.0)).accepted

    # The truck has not moved just because a command was accepted.
    assert store.get_state_snapshot(now=clock.t) == before
    assert store.get_vehicle_field("TRUCK_02", "speed_mps").value == 3.0


# ---------------------------------------------------------------------
# 18/19/20. lifecycle: accepted != transmitted != acknowledged != executed
# ---------------------------------------------------------------------

def test_lifecycle_states_are_distinct(gateway, clock):
    assert gateway.submit(cmd(target_speed_mps=5.0)).accepted
    assert gateway.get_status("CMD_1") == CommandStatus.ACCEPTED

    assert gateway.mark_transmitted("CMD_1")
    assert gateway.get_status("CMD_1") == CommandStatus.TRANSMITTED

    gateway.record_ack("CMD_1", "ACCEPTED", applied_speed_mps=5.0)
    assert gateway.get_status("CMD_1") == CommandStatus.EXECUTED


def test_clamped_ack_is_acknowledged_not_executed(gateway):
    """The local governor clamped it: the requested target was NOT applied."""
    gateway.submit(cmd(target_speed_mps=9.0))
    gateway.mark_transmitted("CMD_1")
    gateway.record_ack("CMD_1", "CLAMPED", applied_speed_mps=4.0)

    assert gateway.get_status("CMD_1") == CommandStatus.ACKNOWLEDGED
    assert gateway.get_status("CMD_1") != CommandStatus.EXECUTED


def test_rejected_ack_is_recorded(gateway):
    gateway.submit(cmd())
    gateway.mark_transmitted("CMD_1")
    gateway.record_ack("CMD_1", "REJECTED", applied_speed_mps=0.0)
    assert gateway.get_status("CMD_1") == CommandStatus.REJECTED


def test_ack_for_unknown_command_is_rejected(gateway):
    assert gateway.record_ack("NOPE", "ACCEPTED", 1.0).status == CommandStatus.REJECTED


def test_untransmitted_command_never_times_out(gateway, clock):
    gateway.submit(cmd())
    clock.advance(100.0)
    assert gateway.expire_pending() == []
    assert gateway.get_status("CMD_1") == CommandStatus.ACCEPTED


def test_transmitted_command_times_out_without_ack(gateway, clock):
    # Reuses config command_ack_timeout_seconds (3.0 s).
    assert gateway.ack_timeout_s == 3.0
    gateway.submit(cmd())
    gateway.mark_transmitted("CMD_1")

    clock.advance(1.0)
    assert gateway.expire_pending() == []

    clock.advance(5.0)
    assert gateway.expire_pending() == ["CMD_1"]
    assert gateway.get_status("CMD_1") == CommandStatus.TIMEOUT


def test_acked_command_does_not_time_out(gateway, clock):
    gateway.submit(cmd(target_speed_mps=5.0))
    gateway.mark_transmitted("CMD_1")
    gateway.record_ack("CMD_1", "ACCEPTED", applied_speed_mps=5.0)
    clock.advance(100.0)
    assert gateway.expire_pending() == []
    assert gateway.get_status("CMD_1") == CommandStatus.EXECUTED


# ---------------------------------------------------------------------
# 21. firmware watchdog remains represented (emulator)
# ---------------------------------------------------------------------

def test_firmware_command_timeout_constant_is_intact():
    """
    The physical fail-safe must remain in the firmware, untouched.

    NOTE: the constant is 15000 ms, not the 3 s often quoted; the 3 s value in this
    project is `command_ack_timeout_seconds`, a different protection.
    """
    import os
    import re

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "esp32_code", "VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR",
        "VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino",
    )
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        source = handle.read()

    match = re.search(r"const unsigned long COMMAND_TIMEOUT_MS\s*=\s*(\d+);", source)
    assert match, "firmware command watchdog was removed"
    assert int(match.group(1)) == 15000
    assert "commandedSpeedMs = 0.0f;" in source          # timeout -> STOP


def test_gateway_ack_timeout_is_distinct_from_firmware_watchdog(gateway):
    """Two protections, deliberately different windows. Never merged."""
    assert gateway.ack_timeout_s == 3.0                 # gateway ACK timeout
    assert gateway.validity_window_s == 5.0             # gateway command validity
    # Firmware watchdog is 15 s and lives on the vehicle - see the test above.


# ---------------------------------------------------------------------
# 22. ordering
# ---------------------------------------------------------------------

def test_older_command_cannot_override_newer_command(gateway):
    assert gateway.submit(cmd(command_id="NEW", created_at=WALL_NOW)).accepted
    older = gateway.submit(cmd(command_id="OLD", created_at=WALL_NOW - 2.0))
    assert older.status == CommandStatus.SUPERSEDED


def test_ordering_is_per_vehicle(store, clock):
    set_v_safe(store, "TRUCK_01", 9.0)
    set_v_safe(store, "TRUCK_02", 9.0)
    gw = CommandGateway(store=store, clock=clock)

    assert gw.submit(cmd(vehicle_id="TRUCK_02", command_id="B", created_at=WALL_NOW)).accepted
    # An earlier command for a DIFFERENT vehicle is unaffected.
    assert gw.submit(cmd(vehicle_id="TRUCK_01", command_id="A", created_at=WALL_NOW - 2.0)).accepted


# ---------------------------------------------------------------------
# 23/24. provenance
# ---------------------------------------------------------------------

def test_simulation_command_provenance_is_preserved(gateway):
    gateway.submit(cmd(command_id="SIMCMD", mode="SIMULATION", source=CommandSource.SIMULATION))
    entry = [h for h in gateway.history() if h["command_id"] == "SIMCMD"][0]
    assert entry["mode"] == "SIMULATION"
    assert entry["source"] == "SIMULATION"


def test_hardware_command_provenance_is_preserved(gateway):
    gateway.submit(cmd(command_id="HWCMD", mode="HARDWARE", source=CommandSource.DISPATCH))
    entry = [h for h in gateway.history() if h["command_id"] == "HWCMD"][0]
    assert entry["mode"] == "HARDWARE"
    assert entry["source"] == "DISPATCH"


# ---------------------------------------------------------------------
# End-to-end against the EXISTING hardware emulator (SIMULATION, not hardware)
# ---------------------------------------------------------------------

def test_emulator_command_flow_gateway_to_ack(store, clock):
    """
    valid command -> gateway ACCEPTED -> emulator executes -> ACK -> telemetry.

    EMULATED. Not a physical hardware test.
    """
    from contracts import DispatchCommandMessage
    from hardware_emulator import VehicleHardwareEmulator

    truck = VehicleHardwareEmulator("TRUCK_02", initial_position=150.0, segment_id="ROAD_2")
    truck.update_environment(visibility_m=50.0, friction_mu=0.35, grade_pct=0.0)
    v_safe = truck.compute_local_safety_state().v_safe

    set_v_safe(store, "TRUCK_02", v_safe)
    gw = CommandGateway(store=store, clock=clock)

    target = min(1.0, v_safe)
    result = gw.submit(cmd(target_speed_mps=target))
    assert result.accepted

    gw.mark_transmitted("CMD_1")
    ack = truck.process_dispatch_command(
        DispatchCommandMessage(command_id="CMD_1", vehicle_id="TRUCK_02",
                               timestamp=clock.t, target_speed=target, action="TARGET_SPEED")
    )
    assert ack.status in ("ACCEPTED", "CLAMPED")

    final = gw.record_ack("CMD_1", ack.status, applied_speed_mps=ack.applied_speed)
    assert final.status in (CommandStatus.EXECUTED, CommandStatus.ACKNOWLEDGED)
    # The vehicle - not the gateway - decided the applied speed.
    assert truck.speed_mps == pytest.approx(ack.applied_speed)


def test_emulator_local_governor_still_outranks_the_gateway(store, clock):
    """
    A command the gateway would allow is still clamped by the vehicle's Tier-1 governor.
    The gateway never overrides local safety.
    """
    from contracts import DispatchCommandMessage
    from hardware_emulator import VehicleHardwareEmulator

    truck = VehicleHardwareEmulator("TRUCK_02", initial_position=150.0, segment_id="ROAD_2")
    truck.update_environment(visibility_m=8.0, friction_mu=0.20, grade_pct=-8.0)
    v_safe_real = truck.compute_local_safety_state().v_safe

    # The Twin briefly holds an optimistic v_safe, so the gateway lets a fast target pass.
    set_v_safe(store, "TRUCK_02", 50.0)
    gw = CommandGateway(store=store, clock=clock)
    assert gw.submit(cmd(target_speed_mps=20.0)).accepted

    ack = truck.process_dispatch_command(
        DispatchCommandMessage(command_id="CMD_1", vehicle_id="TRUCK_02",
                               timestamp=clock.t, target_speed=20.0, action="TARGET_SPEED")
    )
    assert ack.status == "CLAMPED"
    assert ack.applied_speed == pytest.approx(v_safe_real)
    assert ack.applied_speed < 20.0


# ---------------------------------------------------------------------
# HMI endpoint: submission path, not a state author
# ---------------------------------------------------------------------

def _backend_on_path():
    import os
    import sys

    backend = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "SYNQRA_SIH2026-27-HMI", "backend",
    )
    if backend not in sys.path:
        sys.path.insert(0, backend)


def test_hmi_command_endpoint_does_not_author_vehicle_state():
    _backend_on_path()

    from fastapi.testclient import TestClient

    from app.main import app, vehicle_telemetry_store

    with TestClient(app) as client:
        client.post(
            "/api/hardware/telemetry",
            json={"vehicle_id": "TRUCK_02", "sequence": 91001, "rpm": 240.0, "speed": 2.5,
                  "ax": 0.1, "ay": 0.0, "az": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.0,
                  "source": "DIRECT_WIFI"},
        )
        before_speed = vehicle_telemetry_store["TRUCK_02"].get("speed")

        resp = client.post(
            "/api/commands",
            json={"command_id": "HMI_STOP_1", "vehicle_id": "TRUCK_02",
                  "action": "STOP", "target_speed": 0.0, "reason": "operator"},
        )
        assert resp.status_code == 200

        # A STOP submission must NOT rewrite telemetry to speed 0 / safety CRITICAL.
        veh = vehicle_telemetry_store["TRUCK_02"]
        assert veh.get("speed") == before_speed
        assert veh.get("safety_state") != "CRITICAL"
        assert veh.get("mode") != "stopped"


def test_hmi_endpoint_rejects_unknown_vehicle():
    _backend_on_path()

    from fastapi.testclient import TestClient

    from app.main import app, command_gateway

    if command_gateway is None:
        pytest.skip("gateway unavailable in this environment")

    with TestClient(app) as client:
        resp = client.post(
            "/api/commands",
            json={"command_id": "HMI_UNKNOWN_1", "vehicle_id": "TRUCK_47",
                  "action": "STOP", "target_speed": 0.0, "reason": "operator"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == CommandStatus.UNKNOWN_VEHICLE
