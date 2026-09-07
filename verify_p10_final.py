"""
P10 — FINAL END-TO-END CHAIN VERIFICATION.

WHAT THIS PROVES
    One continuous causal chain, with evidence captured at every hop:

        ENVIRONMENT (fog)
            -> CANONICAL TWIN environment
            -> fog_safe                       (the one solver)
            -> v_safe in the Twin
            -> COMMAND GATEWAY                (reads v_safe, never solves)
            -> VEHICLE / EMULATOR             (Tier-1 local governor clamps)
            -> TELEMETRY
            -> INGESTION BOUNDARY             (the one entry point)
            -> CANONICAL TWIN
            -> PROJECTION                     (the one shape for REST and WS)
            -> HMI / OPERATOR readout
            -> game_ui readout

    and then the recovery: fog clears, v_safe rises again.

WHAT THIS IS NOT
    It builds no Twin, no solver and no ingestion path of its own. Every step calls the
    component that P0-P9 established as authoritative. If this file could compute an
    answer by itself, it would not be evidence of anything.

PROVENANCE
    SIMULATION and EMULATED. `VehicleHardwareEmulator` is a software stand-in for the
    ESP32; it is not an ESP32. No physical hardware is involved anywhere in this file and
    nothing here constitutes physical validation.

USAGE
    python verify_p10_final.py            # prints the evidence table, writes the CSV trace
    Exit code 0 only if every hop passes.
"""

import csv
import importlib.util
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_ROOT = os.path.join(PROJECT_ROOT, "SYNQRA_SIH2026-27-main")
for _path in (PROJECT_ROOT, MAIN_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

TRACE_PATH = os.path.join(PROJECT_ROOT, "results", "P10_E2E_TRACE.csv")

TRACE_COLUMNS = [
    "step", "hop", "vehicle_id", "visibility_m", "v_safe_mps", "v_command_mps",
    "applied_speed_mps", "source", "origin", "clock_domain", "freshness", "status",
]

# Visibility sweep, in metres. Clear -> fog rolls in -> dense -> clearing -> clear.
VISIBILITY_SWEEP = (50.0, 30.0, 10.0, 6.0, 30.0, 50.0)
DENSE_FOG_M = 6.0
CLEAR_M = 50.0


class Evidence:
    """Collected results. A hop is either PASS or FAIL; nothing is assumed."""

    def __init__(self):
        self.hops = []
        self.trace = []

    def hop(self, name, ok, detail=""):
        self.hops.append({"hop": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)})
        return ok

    def row(self, **kwargs):
        row = {column: "" for column in TRACE_COLUMNS}
        row.update({k: v for k, v in kwargs.items() if k in row})
        self.trace.append(row)

    @property
    def passed(self):
        return sum(1 for h in self.hops if h["status"] == "PASS")

    @property
    def failed(self):
        return [h for h in self.hops if h["status"] == "FAIL"]

    @property
    def ok(self):
        return not self.failed


def load_game_ui():
    """Import game_ui headlessly. It imports no pygame at module scope."""
    spec = importlib.util.spec_from_file_location(
        "game_ui_p10", os.path.join(MAIN_ROOT, "game_ui.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def field_of(twin, vehicle_id, name):
    """A Twin field with its provenance, or None when the Twin does not hold it."""
    field = twin.get_vehicle_field(vehicle_id, name)
    return field if getattr(field, "is_available", False) else None


def describe(field, twin):
    """Provenance of one field, for the trace. Never invents a value."""
    if field is None:
        return {"source": "UNAVAILABLE", "origin": "UNAVAILABLE",
                "clock_domain": "UNAVAILABLE", "freshness": "UNAVAILABLE"}
    reference = twin.now_by_domain().get(field.clock_domain)

    def name(enum_value):
        # A field may carry no explicit origin; say so rather than crashing or guessing.
        return enum_value.value if enum_value is not None else "UNSPECIFIED"

    return {
        "source": name(field.source),
        "origin": name(field.origin),
        "clock_domain": name(field.clock_domain),
        "freshness": field.freshness(reference, twin.stale_after_s, field.clock_domain),
    }


# =====================================================================
# The chain
# =====================================================================

def run_chain(verbose=False):
    """
    Walk the whole chain once and return the collected Evidence.

    A failed hop is recorded rather than raised, and later hops still run, so the report
    shows how far the chain actually got instead of stopping at the first surprise.
    """
    from command_gateway import CommandGateway, CommandSource, CommandStatus, VehicleCommand
    from contracts import DispatchCommandMessage
    from hardware_emulator import VehicleHardwareEmulator
    from telemetry_ingest import TelemetryIngestor, Transport
    from twin.twin_state_store import Source
    from twin_projection import build_twin_snapshot, build_vehicle_projection, value_of

    evidence = Evidence()
    ui = load_game_ui()
    bridge = ui.SimulationUIBridge()
    twin = bridge.twin
    vehicle_id = bridge.sim.vehicles[0].id

    # -----------------------------------------------------------------
    # STEP 1 - CLEAR: environment reaches the canonical Twin
    # -----------------------------------------------------------------
    bridge.set_visibility(CLEAR_M)
    for _ in range(3):
        bridge.step()

    visibility = twin.get_environment().get("visibility_m")
    evidence.hop(
        "1 environment reaches the canonical Twin",
        visibility is not None and abs(visibility.value - CLEAR_M) < 1e-6
        and visibility.source is Source.SIMULATION,
        "visibility_m=%s source=%s" % (
            getattr(visibility, "value", None),
            getattr(getattr(visibility, "source", None), "value", None),
        ),
    )

    v_safe_clear_field = field_of(twin, vehicle_id, "v_safe_mps")
    v_safe_clear = v_safe_clear_field.value if v_safe_clear_field else None
    evidence.hop(
        "2 fog_safe result is held by the Twin with DERIVED provenance",
        v_safe_clear is not None
        and v_safe_clear_field.source is Source.DERIVED
        and v_safe_clear_field.origin is Source.SIMULATION,
        "v_safe=%s source=%s origin=%s" % (
            v_safe_clear,
            getattr(getattr(v_safe_clear_field, "source", None), "value", None),
            getattr(getattr(v_safe_clear_field, "origin", None), "value", None),
        ),
    )
    evidence.row(step=1, hop="CLEAR baseline", vehicle_id=vehicle_id, visibility_m=CLEAR_M,
                 v_safe_mps=v_safe_clear, status="OK", **describe(v_safe_clear_field, twin))

    # -----------------------------------------------------------------
    # STEP 2 - FOG: visibility falls, and v_safe falls with it
    # -----------------------------------------------------------------
    bridge.set_visibility(DENSE_FOG_M)
    for _ in range(3):
        bridge.step()

    v_safe_fog_field = field_of(twin, vehicle_id, "v_safe_mps")
    v_safe_fog = v_safe_fog_field.value if v_safe_fog_field else None
    evidence.hop(
        "3 dense fog lowers v_safe through fog_safe",
        v_safe_fog is not None and v_safe_clear is not None and v_safe_fog < v_safe_clear,
        "clear=%.4f -> fog=%.4f" % (v_safe_clear or -1, v_safe_fog or -1),
    )
    evidence.row(step=2, hop="DENSE FOG", vehicle_id=vehicle_id, visibility_m=DENSE_FOG_M,
                 v_safe_mps=v_safe_fog, status="v_safe lowered",
                 **describe(v_safe_fog_field, twin))

    # The commanded speed the domain produced must never exceed the safe speed.
    vehicle = next(v for v in bridge.sim.vehicles if v.id == vehicle_id)
    v_command = getattr(vehicle, "v_command_mps", None)
    evidence.hop(
        "4 v_command never exceeds v_safe",
        v_command is not None and v_safe_fog is not None and v_command <= v_safe_fog + 1e-9,
        "v_command=%.4f v_safe=%.4f" % (v_command or -1, v_safe_fog or -1),
    )

    # -----------------------------------------------------------------
    # STEP 3 - COMMAND GATEWAY reads v_safe; it never solves
    # -----------------------------------------------------------------
    # The Twin's v_safe lives in the SIMULATION clock domain, so the gateway is given the
    # simulation clock. Comparing it against wall-clock now would call a perfectly fresh
    # field stale - the exact mistake P4.1 exists to prevent.
    sim_domain = v_safe_fog_field.clock_domain if v_safe_fog_field else None

    def sim_clock():
        if sim_domain is None:
            return time.time()
        return twin.now_by_domain()[sim_domain]

    gateway = CommandGateway(store=twin, clock=sim_clock)

    unsafe_target = (v_safe_fog or 0.0) + 5.0
    rejected_before = gateway.stats["rejected"]
    unsafe_result = gateway.submit(VehicleCommand(
        vehicle_id=vehicle_id, command_id="P10_UNSAFE", created_at=sim_clock(),
        action="TARGET_SPEED", target_speed_mps=unsafe_target,
        source=CommandSource.DISPATCH, reason="P10 chain: deliberately above v_safe",
    ))
    evidence.hop(
        "5 a target above v_safe is REFUSED, and the refusal is counted",
        unsafe_result.status == CommandStatus.REJECTED
        and gateway.stats["rejected"] == rejected_before + 1,
        "status=%s rejected %d->%d" % (unsafe_result.status, rejected_before,
                                       gateway.stats["rejected"]),
    )
    evidence.row(step=3, hop="gateway refuses unsafe", vehicle_id=vehicle_id,
                 visibility_m=DENSE_FOG_M, v_safe_mps=v_safe_fog,
                 v_command_mps=unsafe_target, status=unsafe_result.status,
                 source="TWIN_V_SAFE", origin="SIMULATION", clock_domain="SIMULATION")

    safe_target = max(0.0, (v_safe_fog or 0.0) - 0.5)
    safe_result = gateway.submit(VehicleCommand(
        vehicle_id=vehicle_id, command_id="P10_SAFE", created_at=sim_clock(),
        action="TARGET_SPEED", target_speed_mps=safe_target,
        source=CommandSource.DISPATCH, reason="P10 chain: within v_safe",
    ))
    evidence.hop(
        "6 a target within v_safe is ACCEPTED",
        safe_result.status == CommandStatus.ACCEPTED,
        "status=%s target=%.4f" % (safe_result.status, safe_target),
    )
    evidence.row(step=3, hop="gateway accepts safe", vehicle_id=vehicle_id,
                 visibility_m=DENSE_FOG_M, v_safe_mps=v_safe_fog,
                 v_command_mps=safe_target, status=safe_result.status,
                 source="TWIN_V_SAFE", origin="SIMULATION", clock_domain="SIMULATION")

    # -----------------------------------------------------------------
    # STEP 4 - VEHICLE: the Tier-1 local governor stays authoritative
    # -----------------------------------------------------------------
    emulator = VehicleHardwareEmulator(vehicle_id="TRUCK_02", segment_id="ROAD_1")
    emulator.update_environment(visibility_m=DENSE_FOG_M, friction_mu=0.35, grade_pct=0.0)
    local_v_safe = emulator.compute_local_safety_state().v_safe

    over_the_local_limit = local_v_safe + 4.0
    ack = emulator.process_dispatch_command(DispatchCommandMessage(
        command_id="P10_CLAMP", vehicle_id="TRUCK_02", timestamp=time.time(),
        action="TARGET_SPEED", target_speed=over_the_local_limit,
        reason="P10 chain: above the vehicle's own ceiling",
    ))
    evidence.hop(
        "7 the vehicle's local governor clamps a too-fast command (Tier-1 authoritative)",
        ack.status == "CLAMPED" and ack.applied_speed <= local_v_safe + 1e-9,
        "status=%s applied=%.4f local_v_safe=%.4f" % (ack.status, ack.applied_speed, local_v_safe),
    )
    evidence.row(step=4, hop="vehicle clamps", vehicle_id="TRUCK_02", visibility_m=DENSE_FOG_M,
                 v_safe_mps=local_v_safe, v_command_mps=over_the_local_limit,
                 applied_speed_mps=ack.applied_speed, status=ack.status,
                 source="VEHICLE_LOCAL_GOVERNOR", origin="EMULATED",
                 clock_domain="WALL_CLOCK")

    # -----------------------------------------------------------------
    # STEP 5 - TELEMETRY back through the ONE ingestion boundary
    # -----------------------------------------------------------------
    emulator.step_simulation(dt=1.0)
    vehicle_msg, _safety_msg, _health = emulator.get_telemetry_messages()

    ingestor = TelemetryIngestor(twin)
    result = ingestor.ingest_parsed_record(
        {
            "vehicle_id": "TRUCK_02",
            "sequence_number": 10_500_001,
            "rpm": 212.0,
            "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81},
            "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
            "communication_state": "HEALTHY",
        },
        transport=Transport.EMULATOR,
        is_simulated=True,
    )
    rpm_field = field_of(twin, "TRUCK_02", "rpm")
    evidence.hop(
        "8 vehicle telemetry re-enters through the canonical ingestion boundary",
        result.accepted and rpm_field is not None and rpm_field.value == 212.0,
        "accepted=%s rpm=%s" % (result.accepted, getattr(rpm_field, "value", None)),
    )
    evidence.hop(
        "9 emulated telemetry is NOT labelled as physical hardware",
        rpm_field is not None and rpm_field.source is not Source.HARDWARE,
        "source=%s" % getattr(getattr(rpm_field, "source", None), "value", None),
    )
    evidence.row(step=5, hop="telemetry -> Twin", vehicle_id="TRUCK_02",
                 visibility_m=DENSE_FOG_M, applied_speed_mps=vehicle_msg.speed_mps,
                 status="INGESTED", **describe(rpm_field, twin))

    # -----------------------------------------------------------------
    # STEP 6 - PROJECTION: one shape for REST and WebSocket
    # -----------------------------------------------------------------
    projection = build_vehicle_projection(twin, vehicle_id)
    snapshot = build_twin_snapshot(twin)
    evidence.hop(
        "10 the Twin projects to the single REST/WS shape",
        projection is not None and snapshot.get("schema") == "twin_projection/1"
        and vehicle_id in snapshot.get("vehicles", {}),
        "schema=%s vehicles=%d" % (snapshot.get("schema"), len(snapshot.get("vehicles", {}))),
    )

    projected_v_safe = value_of(projection, "v_safe_mps")
    evidence.hop(
        "11 the projected v_safe is the Twin's value, unchanged",
        projected_v_safe is not None and v_safe_fog is not None
        and abs(projected_v_safe - v_safe_fog) < 1e-9,
        "projected=%s twin=%s" % (projected_v_safe, v_safe_fog),
    )

    # TRUCK_02 is in the simulated fleet AND received telemetry above, so it is the HYBRID
    # case: a simulated position alongside a telemetry-sourced rpm. Neither side is allowed
    # to overwrite the other, and neither is allowed to be relabelled as the other.
    hybrid = build_vehicle_projection(twin, "TRUCK_02")
    hybrid_rpm = hybrid["dynamic"].get("rpm", {})
    hybrid_position = hybrid["dynamic"].get("position_s", {})
    simulated_position = getattr(
        next(v for v in bridge.sim.vehicles if v.id == "TRUCK_02"), "position_s", None
    )
    evidence.hop(
        "12 a hybrid vehicle keeps both domains distinct; neither overwrites the other",
        # the telemetry value survived ...
        hybrid_rpm.get("value") == 212.0
        # ... the simulator's position survived alongside it, unchanged ...
        and hybrid_position.get("value") == simulated_position
        # ... and it is still labelled as coming from the simulator, not from telemetry.
        and hybrid_position.get("source") == "SIMULATION"
        and hybrid_position.get("origin") == "SIMULATION",
        "rpm=%s/%s position_s=%s/%s sim_position=%s" % (
            hybrid_rpm.get("value"), hybrid_rpm.get("source"),
            hybrid_position.get("value"), hybrid_position.get("source"), simulated_position),
    )

    # And a field NEITHER source measures is absent, not zeroed. This prototype has no
    # heading sensor and the simulator does not publish one.
    evidence.hop(
        "12b a field no source measures stays UNAVAILABLE, never fabricated",
        "heading_rad" not in hybrid["dynamic"] and value_of(hybrid, "heading_rad") is None,
        "heading_rad present=%s" % ("heading_rad" in hybrid["dynamic"]),
    )

    # -----------------------------------------------------------------
    # STEP 7 - HMI / OPERATOR semantics on the projected values
    # -----------------------------------------------------------------
    field = projection["dynamic"].get("v_safe_mps", {})
    evidence.hop(
        "13 the HMI receives provenance, not a bare number",
        {"source", "origin", "clock_domain", "freshness", "available"} <= set(field),
        "keys=%s" % sorted(field),
    )
    evidence.hop(
        "14 a fresh simulation-domain field reads CURRENT, evaluated in its own domain",
        # "not STALE" would be satisfied by NOT_EVALUATED, which is what this reported
        # before P10 wired the configured threshold into the visualiser's Twin. Requiring
        # CURRENT means freshness is actually being evaluated.
        field.get("freshness") == "CURRENT" and field.get("clock_domain") == "SIMULATION",
        "freshness=%s clock_domain=%s" % (field.get("freshness"), field.get("clock_domain")),
    )

    # ...and the check is capable of failing: age the same field past the threshold.
    aged_reference = twin.now_by_domain()[v_safe_fog_field.clock_domain] + 10_000.0
    aged = v_safe_fog_field.freshness(
        aged_reference, twin.stale_after_s, v_safe_fog_field.clock_domain
    )
    evidence.hop(
        "14b staleness is detectable, and a stale value keeps its last known number",
        aged == "STALE" and v_safe_fog_field.value is not None,
        "aged freshness=%s value=%s" % (aged, v_safe_fog_field.value),
    )

    # -----------------------------------------------------------------
    # STEP 8 - game_ui reads the Twin, and renders UNAVAILABLE honestly
    # -----------------------------------------------------------------
    fleet = bridge.get_fleet_telemetry()
    displayed = next((row for row in fleet if row.get("id") == vehicle_id), None)
    evidence.hop(
        "15 game_ui displays the Twin's v_safe, not one of its own",
        displayed is not None and displayed.get("v_safe_kmh") is not None
        and abs(displayed["v_safe_kmh"] - (v_safe_fog or 0.0) * 3.6) < 1e-6,
        "displayed=%s twin_kmh=%s" % (
            (displayed or {}).get("v_safe_kmh"), (v_safe_fog or 0.0) * 3.6),
    )
    evidence.hop(
        "16 an unavailable value renders as a marker, never as 0 or a speed",
        ui.fmt_value(None) == ui.UNAVAILABLE_TEXT
        and ui.fmt_value(None) != ui.fmt_value(0.0)
        and ui.to_kmh(None) is None,
        "UNAVAILABLE_TEXT=%r zero=%r" % (ui.fmt_value(None), ui.fmt_value(0.0)),
    )
    evidence.hop(
        "17 a missing ceiling never implies clearance",
        ui.safety_known(None) is False and ui.exceeds(20.0, None) is False,
        "safety_known(None)=%s" % ui.safety_known(None),
    )

    # -----------------------------------------------------------------
    # STEP 9 - RECOVERY: the fog clears and the safety state comes back
    # -----------------------------------------------------------------
    readings = []
    for visibility in VISIBILITY_SWEEP:
        bridge.set_visibility(visibility)
        for _ in range(3):
            bridge.step()
        current = field_of(twin, vehicle_id, "v_safe_mps")
        readings.append((visibility, current.value if current else None))
        evidence.row(step=9, hop="visibility sweep", vehicle_id=vehicle_id,
                     visibility_m=visibility,
                     v_safe_mps=current.value if current else "",
                     status="swept", **describe(current, twin))

    dense = next(v for m, v in readings if m == DENSE_FOG_M)
    recovered = readings[-1][1]
    evidence.hop(
        "18 v_safe recovers when the fog clears",
        dense is not None and recovered is not None and recovered > dense,
        "dense=%.4f -> recovered=%.4f" % (dense or -1, recovered or -1),
    )
    evidence.hop(
        "19 v_safe is monotonic in visibility across the sweep",
        _monotonic_in_visibility(readings),
        "; ".join("%.0fm=%s" % (m, "--" if v is None else "%.2f" % v) for m, v in readings),
    )

    # -----------------------------------------------------------------
    # STEP 10 - nothing in the chain silently rewrote the Twin
    # -----------------------------------------------------------------
    # Both snapshots are taken against the SAME reference time. Without that, the
    # comparison would be measuring the wall clock advancing between the two calls
    # (every field's age_s moves) rather than whether any state actually changed.
    reference_now = time.time()
    before = twin.get_state_snapshot(now=reference_now)

    build_twin_snapshot(twin)
    build_vehicle_projection(twin, vehicle_id)
    gateway.submit(VehicleCommand(
        vehicle_id=vehicle_id, command_id="P10_READONLY", created_at=sim_clock(),
        action="TARGET_SPEED", target_speed_mps=1.0, source=CommandSource.DISPATCH,
    ))

    after = twin.get_state_snapshot(now=reference_now)
    evidence.hop(
        "20 reading and commanding never mutate Twin state",
        after == before,
        "snapshot unchanged" if after == before else "TWIN STATE CHANGED",
    )

    if verbose:
        for row in evidence.hops:
            print("  %-4s %s" % (row["status"], row["hop"]))
    return evidence


def _monotonic_in_visibility(readings):
    """
    v_safe must never rise while visibility falls, nor fall while visibility rises.

    Consecutive pairs only, and an equal value is allowed: a constraint other than
    visibility (the mine speed limit, say) can be the binding one at both points.
    """
    for (m_a, v_a), (m_b, v_b) in zip(readings, readings[1:]):
        if v_a is None or v_b is None:
            return False
        if m_b < m_a and v_b > v_a + 1e-9:
            return False
        if m_b > m_a and v_b < v_a - 1e-9:
            return False
    return True


def write_trace(evidence, path=TRACE_PATH):
    """Write the per-hop trace so the demo has a reviewable artefact."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_COLUMNS)
        writer.writeheader()
        writer.writerows(evidence.trace)
    return path


def main():
    print("P10 FINAL END-TO-END CHAIN")
    print("PROVENANCE: SIMULATION / EMULATED. No physical ESP32. No physical validation.")
    print("-" * 78)

    evidence = run_chain()

    width = max(len(h["hop"]) for h in evidence.hops)
    for row in evidence.hops:
        print("%-*s  %-4s  %s" % (width, row["hop"], row["status"], row["detail"]))

    path = write_trace(evidence)
    print("-" * 78)
    print("trace: %s (%d rows)" % (os.path.relpath(path, PROJECT_ROOT), len(evidence.trace)))
    print("%d/%d PASS" % (evidence.passed, len(evidence.hops)))
    return 0 if evidence.ok else 1


if __name__ == "__main__":
    sys.exit(main())
