"""
Operator authentication and command authorization.

THE CENTRAL ASSERTION OF THIS FILE: the server decides who is asking.

A caller can put any `operator_id` it likes in a request body. That string is not
identity - it is a claim, and a claim is not evidence. Identity comes from a token
the server itself issued, and nothing a caller asserts about itself can override it.

No hardware, no network, no files. The shared secret is injected per test via the
environment so nothing sensitive is ever written to source control.
"""

import pytest

from operator_registry import (
    DENY_INACTIVE,
    DENY_NO_TOKEN,
    DENY_NOT_ASSIGNED,
    DENY_UNKNOWN_VEHICLE,
    ROLE_OPERATOR,
    Operator,
    build_demo_registry,
)

SECRET = "test-secret-not-a-real-credential"


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setenv("FOG_OPERATOR_SECRET", SECRET)
    return build_demo_registry()


@pytest.fixture
def op1(registry):
    return registry.issue_token("OP_001", SECRET)


@pytest.fixture
def op2(registry):
    return registry.issue_token("OP_002", SECRET)


# ---------------------------------------------------------------------------
# the four-case matrix
# ---------------------------------------------------------------------------


def test_op001_may_command_truck_01(registry, op1):
    decision = registry.authorize_command(op1, "TRUCK_01")
    assert decision.allowed is True
    assert decision.operator_id == "OP_001"
    assert decision.reason == "ASSIGNED"


def test_op001_may_not_command_truck_02(registry, op1):
    decision = registry.authorize_command(op1, "TRUCK_02")
    assert decision.allowed is False
    assert decision.reason == DENY_NOT_ASSIGNED


def test_op002_may_command_truck_02(registry, op2):
    decision = registry.authorize_command(op2, "TRUCK_02")
    assert decision.allowed is True
    assert decision.operator_id == "OP_002"


def test_op002_may_not_command_truck_01(registry, op2):
    decision = registry.authorize_command(op2, "TRUCK_01")
    assert decision.allowed is False
    assert decision.reason == DENY_NOT_ASSIGNED


# ---------------------------------------------------------------------------
# identity cannot be asserted by the caller
# ---------------------------------------------------------------------------


def test_a_forged_operator_id_cannot_override_the_token(registry, op2):
    """
    The decisive test.

    A caller holding OP_002's token asks for TRUCK_01 while claiming to be OP_001.
    The claim is simply not an input: `authorize_command` takes a token and a
    vehicle, and there is no parameter through which a body-supplied operator id
    could arrive. The decision names OP_002, the real holder.
    """
    decision = registry.authorize_command(op2, "TRUCK_01")
    assert decision.allowed is False
    assert decision.operator_id == "OP_002", "the token holder, not the claimed identity"


def test_an_unauthenticated_request_is_rejected(registry):
    for token in (None, "", "not-a-real-token"):
        decision = registry.authorize_command(token, "TRUCK_01")
        assert decision.allowed is False
        assert decision.reason == DENY_NO_TOKEN


def test_a_wrong_secret_yields_no_token(registry):
    assert registry.issue_token("OP_001", "wrong-secret") is None
    assert registry.issue_token("OP_001", "") is None


def test_an_unknown_operator_yields_no_token(registry):
    assert registry.issue_token("OP_NOT_REAL", SECRET) is None


def test_a_token_cannot_be_issued_without_a_configured_secret(monkeypatch):
    monkeypatch.delenv("FOG_OPERATOR_SECRET", raising=False)
    registry = build_demo_registry()
    assert registry.issue_token("OP_001", "anything") is None


def test_an_expired_token_is_nobody(monkeypatch):
    monkeypatch.setenv("FOG_OPERATOR_SECRET", SECRET)
    registry = build_demo_registry(token_ttl_seconds=-1)  # already expired
    token = registry.issue_token("OP_001", SECRET)
    assert registry.operator_for_token(token) is None
    assert registry.authorize_command(token, "TRUCK_01").allowed is False


def test_a_revoked_token_stops_working(registry, op1):
    assert registry.authorize_command(op1, "TRUCK_01").allowed is True
    registry.revoke(op1)
    assert registry.authorize_command(op1, "TRUCK_01").allowed is False


# ---------------------------------------------------------------------------
# operator and vehicle are separate identities
# ---------------------------------------------------------------------------


def test_operator_exists_independently_of_any_vehicle(registry):
    operator = registry.operator("SUP_001")
    assert operator is not None
    assert registry.active_assignment_for_operator("SUP_001") is None


def test_a_vehicle_id_is_never_an_operator_id(registry):
    assert registry.operator("TRUCK_01") is None
    assert registry.operator("TRUCK_02") is None


def test_reassignment_is_explicit_and_auditable(registry):
    before = registry.active_assignment_for_vehicle("TRUCK_01")
    assert before is not None and before.operator_id == "OP_001"

    registry.assign("TRUCK_01", "OP_002")

    after = registry.active_assignment_for_vehicle("TRUCK_01")
    assert after is not None and after.operator_id == "OP_002"

    # The old assignment is ENDED, not erased - the history survives.
    ended = [
        a
        for a in registry.assignment_history()
        if a.vehicle_id == "TRUCK_01" and a.status == "ENDED"
    ]
    assert len(ended) == 1
    assert ended[0].operator_id == "OP_001"
    assert ended[0].unassigned_at is not None


def test_assignment_carries_a_shift(registry):
    assignment = registry.active_assignment_for_vehicle("TRUCK_01")
    assert assignment is not None
    assert assignment.shift_id == "SHIFT_DAY"
    assert registry.shift("SHIFT_DAY") is not None


def test_an_unassigned_vehicle_cannot_be_commanded_by_an_operator(registry, op1):
    registry.unassign("TRUCK_01")
    decision = registry.authorize_command(op1, "TRUCK_01")
    assert decision.allowed is False
    assert decision.reason == DENY_NOT_ASSIGNED


# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------


def test_a_supervisor_may_command_without_an_assignment(registry):
    token = registry.issue_token("SUP_001", SECRET)
    for vehicle in ("TRUCK_01", "TRUCK_02"):
        decision = registry.authorize_command(token, vehicle)
        assert decision.allowed is True
        assert decision.reason == "ROLE_SUPERVISOR"


def test_an_inactive_operator_is_refused(monkeypatch):
    monkeypatch.setenv("FOG_OPERATOR_SECRET", SECRET)
    registry = build_demo_registry()
    token = registry.issue_token("OP_001", SECRET)
    # Deactivate after the token was issued: the decision re-checks status.
    registry.register_operator(
        Operator("OP_001", "Demo Operator 1", ROLE_OPERATOR, status="INACTIVE")
    )
    decision = registry.authorize_command(token, "TRUCK_01")
    assert decision.allowed is False
    assert decision.reason == DENY_INACTIVE


def test_an_unknown_vehicle_is_refused(registry, op1):
    decision = registry.authorize_command(op1, "TRUCK_99", known_vehicles=frozenset({"TRUCK_01"}))
    assert decision.allowed is False
    assert decision.reason == DENY_UNKNOWN_VEHICLE


# ---------------------------------------------------------------------------
# auditability and isolation
# ---------------------------------------------------------------------------


def test_every_decision_is_recorded(registry, op1):
    registry.authorize_command(op1, "TRUCK_01")
    registry.authorize_command(op1, "TRUCK_02")
    registry.authorize_command(None, "TRUCK_01")

    log = registry.audit_log()
    assert len(log) == 3
    assert [d.allowed for d in log] == [True, False, False]
    for entry in log:
        assert entry.decided_at, "a decision without a timestamp is not auditable"
        assert entry.reason


def test_demo_operators_are_labelled_demo(registry):
    for operator in registry.operators():
        assert operator.provenance == "DEMO", "demo fixtures must never look like real staff"


def test_the_registry_holds_no_telemetry(registry):
    """
    Operator identity must not leak into vehicle data, and vehicle data must not
    leak into operator identity. The registry knows vehicle IDs and nothing else
    about vehicles - no speed, no position, no provenance.
    """
    assignment = registry.active_assignment_for_vehicle("TRUCK_01")
    assert assignment is not None
    for forbidden in ("speed", "rpm", "position", "latitude", "provenance", "telemetry"):
        assert not hasattr(assignment, forbidden)


# ---------------------------------------------------------------------------
# FAIL CLOSED
#
# If the thing that decides permission is not there, the answer is NO.
#
# Graceful degradation is right for a dashboard and wrong for a command path: a
# missing authorizer must not become an open one. These tests drive the real HTTP
# endpoint with the registry removed and prove the command gateway is never even
# reached.
# ---------------------------------------------------------------------------

_COMMANDS = "/api/commands"


def _backend_client():
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend = os.path.join(root, "SYNQRA_SIH2026-27-HMI", "backend")
    for path in (root, backend):
        if path not in sys.path:
            sys.path.insert(0, path)

    from fastapi.testclient import TestClient

    import app.main as main

    return TestClient(main.app), main


def _stop_command(vehicle_id, command_id):
    return {
        "command_id": command_id,
        "vehicle_id": vehicle_id,
        "action": "STOP",
        "target_speed": 0.0,
    }


def test_registry_unavailable_rejects_every_command(monkeypatch):
    client, main = _backend_client()
    monkeypatch.setattr(main, "operator_registry", None, raising=False)

    with client as c:
        response = c.post(_COMMANDS, json=_stop_command("TRUCK_01", "FC_1"))

    assert response.status_code != 200, "a command must not succeed with no authorizer"
    assert response.status_code in (401, 403, 503)
    assert "AUTHORIZ" in response.json()["detail"].upper()


def test_registry_unavailable_does_not_reach_the_command_gateway(monkeypatch):
    """
    THE DECISIVE ONE.

    Rejecting with the right status code is not enough - the gateway must never be
    invoked at all. A spy records any call; the assertion is that it stays empty.
    """
    client, main = _backend_client()

    if main.command_gateway is None:
        pytest.skip("gateway unavailable in this environment")

    calls = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("command gateway invoked while authorization was unavailable")

    monkeypatch.setattr(main, "operator_registry", None, raising=False)
    monkeypatch.setattr(main.command_gateway, "submit", spy, raising=True)

    with client as c:
        response = c.post(_COMMANDS, json=_stop_command("TRUCK_01", "FC_2"))

    assert response.status_code != 200
    assert calls == [], "the gateway was reached despite authorization being unavailable"


def test_registry_unavailable_rejects_even_a_well_formed_token_shape(monkeypatch):
    """A plausible-looking bearer token does not help when there is nobody to ask."""
    client, main = _backend_client()
    monkeypatch.setattr(main, "operator_registry", None, raising=False)

    with client as c:
        response = c.post(
            _COMMANDS,
            json=_stop_command("TRUCK_01", "FC_3"),
            headers={"Authorization": "Bearer looks-real-but-cannot-be-checked"},
        )

    assert response.status_code != 200


def test_a_healthy_registry_still_authorizes_normally(monkeypatch):
    """Fail-closed must not break the working path."""
    import os

    monkeypatch.setenv("FOG_OPERATOR_SECRET", SECRET)
    client, main = _backend_client()

    if main.operator_registry is None:
        pytest.skip("registry unavailable in this environment")

    token = main.operator_registry.issue_token("OP_001", os.environ["FOG_OPERATOR_SECRET"])
    assert token

    with client as c:
        allowed = c.post(
            _COMMANDS,
            json=_stop_command("TRUCK_01", "FC_4"),
            headers={"Authorization": "Bearer %s" % token},
        )
        refused = c.post(
            _COMMANDS,
            json=_stop_command("TRUCK_02", "FC_5"),
            headers={"Authorization": "Bearer %s" % token},
        )

    assert allowed.status_code == 200
    assert refused.status_code == 403
