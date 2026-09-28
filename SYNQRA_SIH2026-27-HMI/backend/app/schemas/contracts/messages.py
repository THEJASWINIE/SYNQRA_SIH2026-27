"""Contract message mirrors — Pydantic. M2.

Source of truth: ``requirements/task1-data-contract.md`` §2–§11.

These are the backend half of the M2 definition of done: "every contract message has a
type on both sides". They are kept honest by ``backend/tests/test_contract_parity.py``,
which validates the same shared fixtures the TypeScript tests use — so a TypeScript schema
and its Pydantic mirror cannot silently drift apart.

SCOPE BOUNDARY (PAD-E): every operational field here is INBOUND ONLY. This module defines
shapes. It computes nothing, predicts nothing, and optimizes nothing.

Enum tolerance: fields the contract requires to accept unknown values are typed ``str``
rather than ``Literal``, matching the TypeScript raw schemas. Rejecting an otherwise valid
message because one enum member is unrecognised is forbidden (contract E-03). Mapping the
unknown value to ``UNKNOWN`` is normalization's job, and normalization lives on the
frontend in M2.
"""

from typing import Literal

from app.schemas.contracts.primitives import (
    CommandId,
    ComponentId,
    Estimate,
    Iso8601,
    NodeId,
    RouteId,
    SegmentId,
    SlotId,
    StrictModel,
    VehicleId,
)

# ---------------------------------------------------------------------------
# Strict enums — the contract defines no UNKNOWN member for these
# ---------------------------------------------------------------------------

SystemMode = Literal["NORMAL", "CAUTION", "DEGRADED", "LOCAL_SAFE", "STOP_UNSAFE"]
AlertSeverity = Literal["INFO", "WARNING", "CRITICAL"]
AlertOrigin = Literal["TASK2", "HMI"]
AlertCategory = Literal[
    "UNSAFE_SPEED",
    "UNSAFE_HEADWAY",
    "BOTTLENECK_RISK",
    "COMM_LOSS",
    "STALE_DATA",
    "SLOT_CONFLICT",
]
AlertSubjectKind = Literal["VEHICLE", "NODE", "SEGMENT", "SLOT", "SYSTEM"]
EventCategory = Literal[
    "FOG_CHANGE",
    "ALERT_RAISED",
    "ALERT_ACKNOWLEDGED",
    "COMMAND_RECEIVED",
    "COMMAND_ISSUED",
    "QUEUE_CHANGE",
    "VIOLATION",
    "RECOVERY",
    "MODE_TRANSITION",
]
DispatchState = Literal["RECOMMENDED", "ISSUED", "ACKNOWLEDGED", "SUPERSEDED", "REJECTED"]
Connectivity = Literal["CONNECTED", "DEGRADED", "DISCONNECTED"]
LinkKind = Literal["V2V", "V2I", "LORA", "BACKEND", "SENSOR"]
CvStatus = Literal["OK", "UNAVAILABLE", "STALE"]
NodeKind = Literal["SHOVEL", "CRUSHER", "INTERSECTION", "SWITCHBACK", "WAYPOINT"]
ArrivalDecision = Literal["HOLD", "METER", "RELEASE"]

# Unknown-tolerant enums are plain ``str`` — see the module docstring.
TolerantEnum = str


# ---------------------------------------------------------------------------
# 1. VehicleState — contract §2
# ---------------------------------------------------------------------------


class VehiclePosition(StrictModel):
    x: float | None
    y: float | None
    segment_id: SegmentId | None
    offset_m: float | None  # [EXT] E-01


class VehicleState(StrictModel):
    vehicle_id: VehicleId
    timestamp: Iso8601
    position: VehiclePosition
    speed_mps: float
    accel_mps2: float
    grade_rad: float
    friction_est: Estimate  # SUPPLIED — friction estimation is Task 2's
    mode: TolerantEnum
    comm_confidence: float
    vehicle_kind: str | None  # [EXT] E-02
    route_id: RouteId | None  # [EXT] E-02


# ---------------------------------------------------------------------------
# 2. SafetyState — contract §3
# ---------------------------------------------------------------------------


class SafetyState(StrictModel):
    vehicle_id: VehicleId
    timestamp: Iso8601  # [EXT] E-06
    v_safe: float | None  # SUPPLIED BY TASK 2. Never computed here (PAD-E).
    h_safe: float | None  # SUPPLIED. Units unresolved — AMB-001 / E-19.
    actual_speed: float
    headway_current: float | None  # [EXT] E-04
    lead_vehicle_id: VehicleId | None  # [EXT] E-04
    active_constraint: TolerantEnum
    risk_level: TolerantEnum
    headway_violation: bool | None  # [EXT] E-05
    envelope_violation: bool | None  # [EXT] E-05


# ---------------------------------------------------------------------------
# 3. RoadState + VisibilityForecast — contract §4
# ---------------------------------------------------------------------------


class RoadState(StrictModel):
    segment_id: SegmentId
    timestamp: Iso8601  # [EXT] E-06
    visibility: Estimate
    friction: Estimate  # [EXT] E-07 — SUPPLIED, no friction computation here
    grade: float
    capacity_vph: float | None
    queue: float | None
    utilization: float | None
    surface_state: TolerantEnum | None  # [EXT] E-07
    roughness: float | None  # [EXT] E-07


class VisibilityHorizonPoint(StrictModel):
    at: Iso8601
    visibility: Estimate


class VisibilityForecast(StrictModel):
    """[EXT] E-08 whole message. COMPUTED ENTIRELY BY TASK 2 (PAD-E)."""

    segment_id: SegmentId
    issued_at: Iso8601
    horizon: list[VisibilityHorizonPoint]


# ---------------------------------------------------------------------------
# 4. BottleneckState — contract §5
# ---------------------------------------------------------------------------


class QueueHistoryPoint(StrictModel):
    at: Iso8601
    queue: float


class QueueForecastPoint(StrictModel):
    at: Iso8601
    queue: float
    sigma: float | None


class BottleneckState(StrictModel):
    node_id: NodeId
    timestamp: Iso8601  # [EXT] E-06
    lambda_vph: float | None  # SUPPLIED
    mu_vph: float | None  # SUPPLIED
    queue: float | None
    queue_max: float | None
    utilization: float | None  # [EXT] E-09
    criticality: TolerantEnum
    bottleneck_score: float | None  # SUPPLIED — sorted by, never derived
    queue_history: list[QueueHistoryPoint] | None  # [EXT] E-09 measured
    #: [EXT] E-09 SUPPLIED BY TASK 2. The most scope-sensitive field in the contract:
    #: this is exactly the queue prediction Task 1 must never produce.
    queue_forecast: list[QueueForecastPoint] | None


# ---------------------------------------------------------------------------
# 5. DispatchCommand — contract §6
# ---------------------------------------------------------------------------


class DispatchCommand(StrictModel):
    """SUPPLIED BY TASK 2. Task 1 never selects, optimizes or issues an assignment."""

    command_id: CommandId
    vehicle_id: VehicleId
    route_id: RouteId | None
    departure_time: Iso8601 | None
    target_speed: float | None
    slot_id: SlotId | None
    reason_code: str  # mandatory per NFR-006
    timestamp: Iso8601
    state: DispatchState  # [EXT] E-11
    limiting_variables: list[str] | None  # [EXT] E-11
    route_node_ids: list[NodeId] | None  # [EXT] E-11


# ---------------------------------------------------------------------------
# 6. SlotState + ArrivalPlan — contract §7
# ---------------------------------------------------------------------------


class SlotState(StrictModel):
    """Conflicts are determined by Task 2. No slot solver runs here."""

    slot_id: SlotId
    resource_id: NodeId
    vehicle_id: VehicleId | None
    start_time: Iso8601
    end_time: Iso8601
    status: TolerantEnum
    eta: Iso8601 | None  # [EXT] E-12
    conflict_with: list[SlotId] | None  # [EXT] E-12


class ArrivalCount(StrictModel):
    at: Iso8601
    count: float


class ArrivalDecisionRecord(StrictModel):
    vehicle_id: VehicleId
    decision: ArrivalDecision
    until: Iso8601 | None
    reason_code: str


class ArrivalPlan(StrictModel):
    """[EXT] E-10 whole message (AMB-002). SUPPLIED BY TASK 2 (PAD-F)."""

    node_id: NodeId
    issued_at: Iso8601
    planned: list[ArrivalCount]
    actual: list[ArrivalCount]
    active_decisions: list[ArrivalDecisionRecord]


# ---------------------------------------------------------------------------
# 7. Alert + EventRecord — contract §8
# ---------------------------------------------------------------------------


class AlertSubject(StrictModel):
    kind: AlertSubjectKind
    id: str


class AlertAcknowledgement(StrictModel):
    by: str
    at: Iso8601


class Alert(StrictModel):
    """[EXT] E-13 whole message.

    The HMI may originate only STALE_DATA and COMM_LOSS. The other four categories are
    supplied by Task 2 and are never raised from a local calculation.
    """

    alert_id: str
    timestamp: Iso8601
    severity: AlertSeverity
    category: AlertCategory
    origin: AlertOrigin
    subject: AlertSubject
    message: str
    reason_code: str | None
    acknowledgeable: bool  # false for safety-critical (FR-015)
    acknowledged: AlertAcknowledgement | None
    active: bool


class EventRecord(StrictModel):
    """[EXT] E-14 append-only audit record backing S5 and NFR-007."""

    event_id: str
    timestamp: Iso8601
    category: EventCategory
    subject_id: str | None
    payload: object | None
    actor: str | None


# ---------------------------------------------------------------------------
# 8. Health + SystemHealth + KpiSnapshot — contract §9
# ---------------------------------------------------------------------------


class Health(StrictModel):
    """Component and link health SUPPLIED by the wider system.

    Distinct from ``app.schemas.health.HealthResponse``, which is the liveness of this
    backend process itself. The two answer different questions and are not merged.
    """

    component_id: ComponentId
    timestamp: Iso8601
    state: TolerantEnum
    latency_ms: float | None
    age_ms: float | None  # supplied by the producer; distinct from Sourced.age_ms
    error_code: str | None
    link_kind: LinkKind | None  # [EXT] E-15
    messages_received: float | None  # [EXT] E-15
    messages_dropped: float | None  # [EXT] E-15


class SystemHealth(StrictModel):
    """[EXT] E-15 whole message. ``system_mode`` is SUPPLIED, never aggregated here."""

    timestamp: Iso8601
    system_mode: SystemMode
    connectivity: Connectivity
    fleet_count: float
    components: list[Health]


class KpiSnapshot(StrictModel):
    """[EXT] E-16 whole message (AMB-003). All seven KPIs are SUPPLIED.

    Deriving these from telemetry history would be computing operational metrics over a
    simulation Task 1 does not own (PAD-F). Absent stays ``None``, never 0.
    """

    timestamp: Iso8601
    window_s: float | None
    throughput_tph: float | None
    cycle_time_s: float | None
    queue_length_avg: float | None
    utilization: float | None
    stops_count: float | None
    safety_envelope_violations: float | None
    recovery_time_s: float | None


# ---------------------------------------------------------------------------
# 9. CVResult — contract §10 (optional feature, M13)
# ---------------------------------------------------------------------------


class CvDetection(StrictModel):
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float] | None


class CVResult(StrictModel):
    """Optional. Advisory only (OPS-004). Typed so the contract is complete; no CV code."""

    timestamp: Iso8601
    source_id: ComponentId
    visibility_proxy: float | None
    confidence: float | None
    detections: list[CvDetection]
    road_state: TolerantEnum | None
    status: CvStatus  # [EXT] E-18
    frame_ref: str | None  # [EXT] E-18


# ---------------------------------------------------------------------------
# 10. MineTopology — contract §11
# ---------------------------------------------------------------------------


class TopologyNode(StrictModel):
    node_id: NodeId
    kind: NodeKind
    label: str
    x: float
    y: float


class TopologySegment(StrictModel):
    segment_id: SegmentId
    from_node: NodeId
    to_node: NodeId
    length_m: float
    grade_rad: float
    bidirectional: bool


class MineTopology(StrictModel):
    """[EXT] E-17 whole message (AMB-011). Quasi-static."""

    version: str
    nodes: list[TopologyNode]
    segments: list[TopologySegment]


# ---------------------------------------------------------------------------
# Registry — the fifteen contract messages, addressable by name
# ---------------------------------------------------------------------------

CONTRACT_MESSAGES: dict[str, type[StrictModel]] = {
    "VehicleState": VehicleState,
    "SafetyState": SafetyState,
    "RoadState": RoadState,
    "VisibilityForecast": VisibilityForecast,
    "BottleneckState": BottleneckState,
    "DispatchCommand": DispatchCommand,
    "SlotState": SlotState,
    "ArrivalPlan": ArrivalPlan,
    "Alert": Alert,
    "EventRecord": EventRecord,
    "Health": Health,
    "SystemHealth": SystemHealth,
    "KpiSnapshot": KpiSnapshot,
    "CVResult": CVResult,
    "MineTopology": MineTopology,
}
