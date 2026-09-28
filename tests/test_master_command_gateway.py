"""
GAP 8 — Command Gateway Complete Matrix (Master Prompt Requirement)

The master prompt requires explicit execution of:
1. Valid command within v_safe -> ACCEPTED (never EXECUTED immediately)
2. Invalid speed:
   - target_speed > v_safe -> REJECTED
   - negative target_speed -> INVALID
   - NaN / Inf target_speed -> INVALID
   - non-numeric string target_speed -> INVALID
3. Unknown vehicle -> UNKNOWN_VEHICLE
4. Stale command (expired deadline) -> STALE
5. Duplicate command (same command_id) -> DUPLICATE
6. Missing / empty command_id -> INVALID
7. Future timestamp (> now + 1.0s) -> INVALID
8. Old / superseded timestamp (< last accepted) -> SUPERSEDED
9. Disconnected vehicle / safety data stale -> REJECTED (fail closed)
10. Defensive actions (STOP / HOLD) permitted even when safety data is missing

For EVERY case:
- Prove unsafe/invalid command was NOT executed
- Preserve accepted != executed (execution requires vehicle acknowledgement)
- Safety governor remains authoritative
"""

import math
import pytest

from command_gateway import (
    CommandGateway,
    CommandSource,
    CommandStatus,
    VehicleCommand,
)
from twin.twin_state_store import (
    TwinStateStore,
    TwinMode,
    Source,
    Quality,
    ClockDomain,
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
    s = TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)
    s.register_vehicle("TRUCK_01")
    # Populate authoritative v_safe = 8.0 m/s
    s.update_vehicle_field(
        "TRUCK_01", "v_safe_mps", 8.0,
        source=Source.DERIVED,
        timestamp=clock.t,
        quality=Quality.GOOD,
        clock_domain=ClockDomain.WALL_CLOCK
    )
    return s


@pytest.fixture
def gateway(store, clock):
    return CommandGateway(store=store, clock=clock, validity_window_s=5.0)


class TestMasterCommandGatewayCompleteMatrix:
    """Master Prompt GAP 8 Command Gateway Complete Verification."""

    def test_case_1_valid_command_accepted_not_executed(self, gateway, clock):
        """Valid command within authoritative v_safe is ACCEPTED, not EXECUTED."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-VALID-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=5.0,  # <= 8.0 m/s
            source=CommandSource.OPERATOR
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.ACCEPTED
        assert res.status != CommandStatus.EXECUTED
        assert gateway.stats["accepted"] == 1
        assert gateway.stats["rejected"] == 0

    def test_case_2a_speed_exceeding_v_safe_rejected(self, gateway, clock):
        """target_speed > v_safe is REJECTED by safety governor."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-UNSAFE-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=12.0,  # > 8.0 m/s v_safe
            source=CommandSource.OPERATOR
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.REJECTED
        assert "exceeds authoritative v_safe" in res.reason
        assert res.status != CommandStatus.EXECUTED
        assert gateway.stats["unsafe"] == 1
        assert gateway.stats["rejected"] == 1

    def test_case_2b_negative_speed_invalid(self, gateway, clock):
        """Negative speed is INVALID."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-NEG-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=-2.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.INVALID
        assert "negative" in res.reason
        assert res.status != CommandStatus.EXECUTED
        assert gateway.stats["invalid"] == 1

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_case_2c_non_finite_speed_invalid(self, gateway, clock, bad_val):
        """NaN / Inf speed is INVALID."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-NAN-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=bad_val,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.INVALID
        assert res.status != CommandStatus.EXECUTED

    def test_case_3_unknown_vehicle_rejected(self, gateway, clock):
        """Unknown vehicle rejected before state mutation."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_UNKNOWN_99",
            command_id="CMD-UNK-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=5.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.UNKNOWN_VEHICLE
        assert res.status != CommandStatus.EXECUTED
        assert gateway.stats["unknown_vehicle"] == 1

    def test_case_4_stale_expired_command_rejected(self, gateway, clock):
        """Command whose validity window has expired is STALE."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-STALE-01",
            created_at=clock.t - 10.0,  # 10s old, validity is 5s
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.STALE
        assert res.status != CommandStatus.EXECUTED
        assert gateway.stats["stale"] == 1

    def test_case_5_duplicate_command_id_rejected(self, gateway, clock):
        """Duplicate command_id is rejected."""
        cmd1 = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-DUP-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res1 = gateway.submit(cmd1)
        assert res1.status == CommandStatus.ACCEPTED

        # Resubmit with same command_id
        cmd2 = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-DUP-01",
            created_at=clock.t + 0.1,
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res2 = gateway.submit(cmd2)
        assert res2.status == CommandStatus.DUPLICATE
        assert res2.status != CommandStatus.EXECUTED
        assert gateway.stats["duplicate"] == 1

    @pytest.mark.parametrize("bad_id", [None, "", "   ", 1234])
    def test_case_6_missing_command_id_invalid(self, gateway, clock, bad_id):
        """Missing or malformed command_id is INVALID."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id=bad_id,
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.INVALID
        assert res.status != CommandStatus.EXECUTED

    def test_case_7_future_timestamp_invalid(self, gateway, clock):
        """created_at > now + 1.0s is INVALID."""
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-FUT-01",
            created_at=clock.t + 10.0,  # 10s in future
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.INVALID
        assert "future" in res.reason
        assert res.status != CommandStatus.EXECUTED

    def test_case_8_superseded_older_timestamp(self, gateway, clock):
        """Command older than latest accepted command is SUPERSEDED."""
        cmd1 = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-NEW-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=3.0,
        )
        assert gateway.submit(cmd1).status == CommandStatus.ACCEPTED

        # Command with created_at earlier than cmd1
        cmd_old = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-OLD-01",
            created_at=clock.t - 1.0,
            action="TARGET_SPEED",
            target_speed_mps=3.0,
        )
        res_old = gateway.submit(cmd_old)
        assert res_old.status == CommandStatus.SUPERSEDED
        assert res_old.status != CommandStatus.EXECUTED

    def test_case_9_disconnected_vehicle_stale_safety(self, gateway, store, clock):
        """Speed-increasing command rejected when safety data is stale/disconnected."""
        # Age the clock past stale threshold (3.0s)
        clock.t += 5.0
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-DISCONN-01",
            created_at=clock.t,
            action="TARGET_SPEED",
            target_speed_mps=4.0,
        )
        res = gateway.submit(cmd)
        assert res.status == CommandStatus.REJECTED
        assert "stale" in res.reason.lower() or "fail closed" in res.reason.lower()
        assert res.status != CommandStatus.EXECUTED

    def test_case_10_defensive_action_stop_always_permitted(self, gateway, clock):
        """Defensive actions (STOP, HOLD) are permitted even when disconnected/stale."""
        clock.t += 10.0  # severely stale
        cmd_stop = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-STOP-01",
            created_at=clock.t,
            action="STOP",
            target_speed_mps=0.0,
        )
        res = gateway.submit(cmd_stop)
        assert res.status == CommandStatus.ACCEPTED
