"""
Operator identity, vehicle assignment and command authorization.

==============================================================================
 PROTOTYPE AUTHENTICATION. NOT ENTERPRISE IAM. NOT PRODUCTION SECURITY.

 What this DOES give you:
   - the server establishes operator identity ITSELF, from a token it issued,
     and never from anything the caller asserts about itself
   - a forged `operator_id` in a request body cannot override that identity
   - an operator can only command a vehicle they are actually assigned to
   - every authorization decision is auditable

 What this does NOT give you:
   - no password hashing, no user store, no rotation, no revocation list,
     no TLS, no rate limiting
   - a single shared secret gates token issue, so anyone holding the secret
     can obtain any operator's token
   - tokens live in memory and die with the process

 It is enough to make "OP_001 cannot command TRUCK_02" a SERVER-ENFORCED fact
 rather than a frontend convention. It is not enough to protect a real mine.
==============================================================================

OPERATOR IS NOT VEHICLE.

The two identities are deliberately separate objects joined by an explicit
`Assignment`. A vehicle id is never used as an operator id, an operator id never
enters a telemetry payload, and reassigning an operator does not touch vehicle
identity or any telemetry provenance.
"""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------

ROLE_OPERATOR = "OPERATOR"
ROLE_SUPERVISOR = "SUPERVISOR"
ROLE_DISPATCHER = "DISPATCHER"
ROLE_SAFETY_CONTROLLER = "SAFETY_CONTROLLER"
ROLE_ADMIN = "ADMIN"

ALL_ROLES = frozenset(
    {ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_DISPATCHER, ROLE_SAFETY_CONTROLLER, ROLE_ADMIN}
)

# Roles that may command a vehicle WITHOUT holding an assignment to it. An
# OPERATOR is deliberately absent: an operator commands only their own vehicle.
ROLES_WITH_FLEET_COMMAND = frozenset({ROLE_SUPERVISOR, ROLE_DISPATCHER, ROLE_ADMIN})

# Rejection reasons, returned verbatim so a caller learns WHY and tests can
# assert on the specific failure rather than on a generic denial.
DENY_NO_TOKEN = "NO_AUTHENTICATED_OPERATOR"
DENY_NOT_ASSIGNED = "OPERATOR_NOT_ASSIGNED_TO_VEHICLE"
DENY_INACTIVE = "OPERATOR_NOT_ACTIVE"
DENY_UNKNOWN_VEHICLE = "UNKNOWN_VEHICLE"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Operator:
    operator_id: str
    name: str
    role: str
    status: str = "ACTIVE"
    #: DEMO fixtures are not real people. Surfaced so the HMI can label them.
    provenance: str = "DEMO"


@dataclass(frozen=True)
class Shift:
    shift_id: str
    name: str
    status: str = "ACTIVE"


@dataclass
class Assignment:
    vehicle_id: str
    operator_id: str
    assigned_at: str
    shift_id: Optional[str] = None
    unassigned_at: Optional[str] = None
    status: str = "ACTIVE"


@dataclass
class AuthorizationDecision:
    """Why a command was allowed or refused. Always recorded, never inferred."""

    allowed: bool
    operator_id: Optional[str]
    vehicle_id: str
    reason: str
    decided_at: str = field(default_factory=_now_iso)


class OperatorRegistry:
    """
    Operators, shifts, assignments, sessions and the authorization decision.

    In-memory on purpose: this is prototype scaffolding, and persisting operator
    identity would imply a durability guarantee it does not have.
    """

    #: How long an issued token stays valid.
    TOKEN_TTL_SECONDS = 8 * 3600

    def __init__(self, token_ttl_seconds: Optional[int] = None):
        self._operators: Dict[str, Operator] = {}
        self._shifts: Dict[str, Shift] = {}
        self._assignments: List[Assignment] = []
        #: token -> (operator_id, issued_at_monotonic)
        self._sessions: Dict[str, tuple] = {}
        self._audit: List[AuthorizationDecision] = []
        self._ttl = token_ttl_seconds if token_ttl_seconds is not None else self.TOKEN_TTL_SECONDS

    # -- registration ------------------------------------------------------

    def register_operator(self, operator: Operator) -> None:
        if operator.role not in ALL_ROLES:
            raise ValueError("unknown role: %s" % operator.role)
        self._operators[operator.operator_id] = operator

    def register_shift(self, shift: Shift) -> None:
        self._shifts[shift.shift_id] = shift

    def operator(self, operator_id: str) -> Optional[Operator]:
        return self._operators.get(operator_id)

    def operators(self) -> List[Operator]:
        return list(self._operators.values())

    def shift(self, shift_id: str) -> Optional[Shift]:
        return self._shifts.get(shift_id)

    # -- assignment --------------------------------------------------------

    def assign(
        self, vehicle_id: str, operator_id: str, shift_id: Optional[str] = None
    ) -> Assignment:
        """
        Assign an operator to a vehicle. Explicit, never inferred from connection
        order, IP address or array position.
        """
        if operator_id not in self._operators:
            raise ValueError("unknown operator: %s" % operator_id)
        self.unassign(vehicle_id)
        assignment = Assignment(
            vehicle_id=vehicle_id,
            operator_id=operator_id,
            assigned_at=_now_iso(),
            shift_id=shift_id,
        )
        self._assignments.append(assignment)
        return assignment

    def unassign(self, vehicle_id: str) -> None:
        """End any active assignment for this vehicle. History is kept, not erased."""
        for a in self._assignments:
            if a.vehicle_id == vehicle_id and a.status == "ACTIVE":
                a.status = "ENDED"
                a.unassigned_at = _now_iso()

    def active_assignment_for_vehicle(self, vehicle_id: str) -> Optional[Assignment]:
        for a in self._assignments:
            if a.vehicle_id == vehicle_id and a.status == "ACTIVE":
                return a
        return None

    def active_assignment_for_operator(self, operator_id: str) -> Optional[Assignment]:
        for a in self._assignments:
            if a.operator_id == operator_id and a.status == "ACTIVE":
                return a
        return None

    def assignment_history(self) -> List[Assignment]:
        """Full history, including ended assignments. Auditable."""
        return list(self._assignments)

    # -- authentication ----------------------------------------------------

    def issue_token(self, operator_id: str, secret: str) -> Optional[str]:
        """
        Exchange the shared secret for a token bound to an operator.

        The secret comes from the environment, never from source control. A wrong
        secret, or an unknown or inactive operator, yields no token.
        """
        expected = os.environ.get("FOG_OPERATOR_SECRET")
        if not expected or not secrets.compare_digest(str(secret), str(expected)):
            return None
        operator = self._operators.get(operator_id)
        if operator is None or operator.status != "ACTIVE":
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (operator_id, time.monotonic())
        return token

    def operator_for_token(self, token: Optional[str]) -> Optional[Operator]:
        """
        THE ONLY WAY THE SERVER LEARNS WHO IS ASKING.

        Nothing in a request body, query string or vehicle id can reach this. A
        caller presenting no token, or a stale one, is nobody.
        """
        if not token:
            return None
        entry = self._sessions.get(token)
        if entry is None:
            return None
        operator_id, issued_at = entry
        if time.monotonic() - issued_at > self._ttl:
            self._sessions.pop(token, None)
            return None
        return self._operators.get(operator_id)

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)

    # -- authorization -----------------------------------------------------

    def authorize_command(
        self,
        token: Optional[str],
        vehicle_id: str,
        known_vehicles: Optional[frozenset] = None,
    ) -> AuthorizationDecision:
        """
        May the holder of this token command this vehicle?

        Runs BEFORE the command gateway. It answers a question about permission,
        never about safety - the gateway remains the sole safety authority, and an
        `allowed` decision here means only "this operator may ask".
        """
        operator = self.operator_for_token(token)
        if operator is None:
            return self._record(AuthorizationDecision(False, None, vehicle_id, DENY_NO_TOKEN))

        if operator.status != "ACTIVE":
            return self._record(
                AuthorizationDecision(False, operator.operator_id, vehicle_id, DENY_INACTIVE)
            )

        if known_vehicles is not None and vehicle_id not in known_vehicles:
            return self._record(
                AuthorizationDecision(False, operator.operator_id, vehicle_id, DENY_UNKNOWN_VEHICLE)
            )

        if operator.role in ROLES_WITH_FLEET_COMMAND:
            return self._record(
                AuthorizationDecision(
                    True, operator.operator_id, vehicle_id, "ROLE_%s" % operator.role
                )
            )

        assignment = self.active_assignment_for_vehicle(vehicle_id)
        if assignment is not None and assignment.operator_id == operator.operator_id:
            return self._record(
                AuthorizationDecision(True, operator.operator_id, vehicle_id, "ASSIGNED")
            )

        return self._record(
            AuthorizationDecision(False, operator.operator_id, vehicle_id, DENY_NOT_ASSIGNED)
        )

    def _record(self, decision: AuthorizationDecision) -> AuthorizationDecision:
        self._audit.append(decision)
        return decision

    def audit_log(self) -> List[AuthorizationDecision]:
        return list(self._audit)


# ---------------------------------------------------------------------------
# demo fixtures
# ---------------------------------------------------------------------------

#: DEVELOPMENT / DEMONSTRATION DATA. These are not real NMDC employees and must
#: never be presented as such. Every operator carries provenance="DEMO" so the
#: HMI can label them.
DEMO_OPERATORS = (
    Operator("OP_001", "Demo Operator 1", ROLE_OPERATOR),
    Operator("OP_002", "Demo Operator 2", ROLE_OPERATOR),
    Operator("SUP_001", "Demo Supervisor", ROLE_SUPERVISOR),
)

DEMO_SHIFT = Shift("SHIFT_DAY", "Day shift")

#: The demonstration assignment used by the two-truck prototype.
DEMO_ASSIGNMENTS = (("TRUCK_01", "OP_001"), ("TRUCK_02", "OP_002"))


def build_demo_registry(token_ttl_seconds: Optional[int] = None) -> OperatorRegistry:
    """A registry preloaded with the DEMO operators, shift and assignments."""
    registry = OperatorRegistry(token_ttl_seconds=token_ttl_seconds)
    for operator in DEMO_OPERATORS:
        registry.register_operator(operator)
    registry.register_shift(DEMO_SHIFT)
    for vehicle_id, operator_id in DEMO_ASSIGNMENTS:
        registry.assign(vehicle_id, operator_id, shift_id=DEMO_SHIFT.shift_id)
    return registry
