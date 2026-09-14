"""
FOG-ORCHESTRATOR 2.0 — Canonical Twin projection (P6).

    TwinStateStore  (authoritative)
          |
          v
    build_vehicle_projection() / build_twin_snapshot()      <- THIS MODULE
          |
     +----+----+
     |         |
    REST      WebSocket
     |         |
     v         v
        React HMI (presentation only)

ONE projection function feeds every read path, so `GET /api/vehicles`, `GET
/api/twin/snapshot` and the WS broadcast can never drift apart.

WHAT A PROJECTION IS
  A read-only view of canonical Twin state. It copies values and their provenance. It
  computes no physics, invents no field, and never writes back.

WHAT IT REFUSES TO DO
  - fabricate position, heading, friction, grade or comm confidence to satisfy a schema
  - coerce an unavailable field to 0.0
  - relabel a DERIVED value as HARDWARE to simplify a consumer
  - compare a SIMULATION timestamp against a wall clock

FIELD SHAPE
  Every dynamic field is projected as the full P4.1 envelope:

      {"value", "timestamp", "source", "quality", "age_s",
       "available", "clock_domain", "freshness", "origin"}

  `origin` is added here (additively) so a consumer can tell
      source=DERIVED origin=HARDWARE   (speed computed from a measured RPM)
  from
      source=DERIVED origin=SIMULATION (a solver output for a simulated truck)
  without changing the meaning of `source`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Fields the HMI cares about, in the Twin's own naming. Absent ones stay absent.
VEHICLE_PROJECTION_FIELDS = (
    "speed_mps",
    "speed_mps_reported",
    "speed_mps_pwm_derived",
    "rpm",
    "position_s",
    "road_id",
    "node_id",
    "heading_rad",
    "acceleration_mps2",
    "ax_mps2",
    "ay_mps2",
    "az_mps2",
    "gx_rad_s",
    "gy_rad_s",
    "gz_rad_s",
    "mass_kg",
    "payload_kg",
    "is_loaded",
    "state",
    "v_safe_mps",
    "v_dispatch_mps",
    "v_command_mps",
    "safe_headway_m",
    "stop_envelope_m",
    "warning_fault",
    # HMI-SAFETY-01: the remaining outputs of the safety producer (contracts.py
    # SafetyStateMessage: risk_level, active_constraint; FR-005: lead vehicle, headway and
    # the two violation verdicts). Projected ONLY when a producer wrote them into the
    # Twin - nothing here computes or defaults them, and today no producer on the HMI
    # backend path does, so they are simply absent.
    "risk_level",
    "active_constraint",
    "lead_vehicle_id",
    "headway_m",
    "headway_violation",
    "envelope_violation",
    "communication_state",
    # Per-radio metrics. Separated at ingestion by transport, and separated here too -
    # a Wi-Fi reading must never reach the HMI under a LoRa heading.
    "wifi_rssi_dbm",
    "lora_rssi_dbm",
    "lora_snr_db",
    # HMI-COMMS-01: the LoRa frame's sequence and the modem that received it
    # (a vehicle id for a relayed frame, LORA_GATEWAY for the bench gateway).
    "v2v_sequence",
    "lora_receiver_id",
    # LEGACY, ambiguous about which radio produced it. Retained for existing consumers.
    "rssi_dbm",
    "snr_db",
    "sequence",
    "received_at",
    "telemetry_transport",
    "position_gnss",
    "position_odom",
    # MAP-02: the Digital Twin demonstration scene pose (SCENE_METRES). Projected so the
    # HMIs can draw both trucks; always stamped SIMULATION by the ingestor.
    "position_scene",
)

ROAD_PROJECTION_FIELDS = (
    "visibility_m",
    "friction_mu",
    "c_rr",
    "surface_state",
    "v_safe_mps",
    "safe_headway_m",
    "capacity_vph",
    "vehicle_count",
)


def project_field(sourced, now_by_domain, stale_after_s: Optional[float]) -> Dict[str, Any]:
    """
    Project one `Sourced` field, aged in ITS OWN clock domain (P4.1).

    A field whose domain has no reference time is reported NOT_EVALUATED - never stale.
    """
    domain = sourced.clock_domain
    reference = now_by_domain.get(domain)
    projected = sourced.as_dict(reference, stale_after_s, domain)
    # Additive: expose origin so DERIVED-from-hardware is distinguishable from
    # DERIVED-from-simulation without overloading `source`.
    projected["origin"] = sourced.effective_origin.value
    return projected


def build_vehicle_projection(store, vehicle_id: str) -> Optional[Dict[str, Any]]:
    """
    Canonical read-only projection of one vehicle. Returns None for an unknown vehicle.

    Only fields the Twin actually holds appear. Nothing is defaulted.
    """
    vehicle = store.get_vehicle(vehicle_id)
    if vehicle is None:
        return None

    now_by_domain = store.now_by_domain()
    stale_after_s = store.stale_after_s

    dynamic = {
        name: project_field(vehicle.get(name), now_by_domain, stale_after_s)
        for name in VEHICLE_PROJECTION_FIELDS
        if name in vehicle.dynamic
    }

    return {
        "vehicle_id": vehicle.entity_id,
        "static": dict(vehicle.static),
        "dynamic": dynamic,
        # Convenience for consumers that only need to know whether a real sensor is
        # behind ANY field of this vehicle. Derived from provenance, not guessed.
        "has_hardware_data": any(
            vehicle.get(name).is_hardware_backed() for name in vehicle.dynamic
        ),
    }


def build_fleet_projection(store) -> Dict[str, Any]:
    """Projection of every vehicle the Twin knows about."""
    return {
        vehicle_id: build_vehicle_projection(store, vehicle_id)
        for vehicle_id in store.get_all_vehicles()
    }


def build_road_projection(store, road_id: str) -> Optional[Dict[str, Any]]:
    road = store.get_road(road_id)
    if road is None:
        return None

    now_by_domain = store.now_by_domain()
    stale_after_s = store.stale_after_s
    return {
        "road_id": road.entity_id,
        "static": dict(road.static),
        "dynamic": {
            name: project_field(road.get(name), now_by_domain, stale_after_s)
            for name in ROAD_PROJECTION_FIELDS
            if name in road.dynamic
        },
    }


def build_environment_projection(store) -> Dict[str, Any]:
    environment = store.get_environment()
    now_by_domain = store.now_by_domain()
    stale_after_s = store.stale_after_s
    return {
        name: project_field(sourced, now_by_domain, stale_after_s)
        for name, sourced in environment.dynamic.items()
    }


def build_twin_snapshot(store) -> Dict[str, Any]:
    """
    Full canonical snapshot for `GET /api/twin/snapshot` and WS broadcast.

    READ-ONLY. Nothing here mutates the Twin.
    """
    return {
        "schema": "twin_projection/1",
        "mode": store.mode.value,
        "snapshot_timestamp": store.now(),
        "simulation_time": store.simulation_now,
        "stale_after_s": store.stale_after_s,
        "environment": build_environment_projection(store),
        "mine": store.get_mine(),
        "roads": {rid: build_road_projection(store, rid) for rid in store.get_all_roads()},
        "vehicles": build_fleet_projection(store),
    }


def value_of(projection: Dict[str, Any], field_name: str, default=None):
    """
    Read a projected field's value, or `default` when it is absent/unavailable.

    Helper for legacy consumers. It never invents a value - the caller supplies the
    default and is responsible for what that default means.
    """
    field = (projection or {}).get("dynamic", {}).get(field_name)
    if not field or not field.get("available"):
        return default
    return field.get("value")
