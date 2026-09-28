"""
FOG-ORCHESTRATOR 2.0 — Functional Mining Digital Twin Visualization UI
Standalone interactive Pygame visualization interface running on top of
the canonical TwinStateStore. Physics/safety are computed in the domain layer
(twin/ui_domain.py -> models.vehicle_physics -> fog_safe); this module only renders.

Usage:
    python game_ui.py          # Interactive Graphical UI
    python game_ui.py --test   # Automated Headless Verification Test
"""

import os
import sys
import math
import time
import argparse
import collections
from typing import Dict, List, Tuple, Any, Optional

import yaml
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Backend Digital Twin Imports (Strictly preserved)
from twin.network import MineNetwork
from twin.simulator import Simulator
# P7: game_ui is a VISUALIZATION CLIENT. It no longer imports the authoritative
# safety solver. Domain computation lives in twin/ui_domain.py; authoritative
# values are read back from the canonical TwinStateStore.
from twin.ui_domain import UISimulationDomain
from twin.twin_state_store import TwinStateStore, TwinMode
from interfaces.simulation_snapshot import SimulationSnapshot

# P9 - READ-ONLY canonical Twin client.
#
# This is the ONLY link from the visualiser to the HMI backend's Twin, and it does
# exactly one thing: GET /api/twin/snapshot. It issues no command and writes no
# state, so the command path (HMI -> POST /api/commands -> CommandGateway) is
# untouched. Import is guarded so the simulator still starts with no adapters
# present, exactly as before.
try:
    from integration_adapters.canonical_twin_client import CanonicalTwinClient
except Exception:  # noqa: BLE001 - the visualiser must start with or without adapters
    CanonicalTwinClient = None

# ==============================================================================
# 1. UI Simulation Bridge (Clean Adapter on Top of Verified Simulator)
# ==============================================================================


# =====================================================================
# P7.1 — UNAVAILABLE PRESENTATION SEAM
#
# The canonical Twin legitimately reports "no value" (a hardware-only truck has no
# simulated road limit; a vehicle whose safe speed has not been evaluated has no v_safe).
# These helpers are PURE - they import no pygame - so the unavailable-value behaviour is
# testable headlessly.
#
# THE RULE: UNAVAILABLE is not 0, and it is never a safety fallback. A missing safe speed
# renders as a dash; it never becomes an optimistic number.
# =====================================================================

UNAVAILABLE_TEXT = "--"


def fmt_value(value, spec="4.1f"):
    """Format a number for display, or the UNAVAILABLE marker when there is none."""
    if value is None:
        return UNAVAILABLE_TEXT
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return UNAVAILABLE_TEXT


def to_kmh(value_mps):
    """m/s -> km/h, preserving UNAVAILABLE as None. Never substitutes a number."""
    return None if value_mps is None else value_mps * 3.6


def exceeds(actual, ceiling, margin=0.0):
    """
    True only when `actual` is KNOWN to exceed `ceiling`.

    With no ceiling there is no evidence of a violation, so this returns False. The caller
    must present the safety state as unknown rather than as safe - see `safety_known()`.
    """
    if actual is None or ceiling is None:
        return False
    return actual > ceiling + margin


# Configuration lives beside this module, not beside the process that launched it.
DEFAULT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")

# Age at which a Twin field is STALE, in seconds. Configured, never invented: the same
# `max_telemetry_age_seconds` the HMI backend and the command gateway read (P9).
try:
    from integration_adapters.config_paths import load_timeouts as _load_timeouts

    TWIN_STALE_AFTER_S = float(_load_timeouts()["max_telemetry_age_seconds"])
except Exception:  # noqa: BLE001 - the visualiser must start with or without the adapters
    TWIN_STALE_AFTER_S = 3.0


def safety_known(v_safe_mps):
    """Whether an authoritative safe speed exists to judge against."""
    return v_safe_mps is not None


class SimulationUIBridge:
    """
    Connects the graphical UI layer to the authoritative digital twin Simulator.
    Preserves all physical models, safe speed calculators, and state machines.
    """
    def __init__(self, config_dir: str = None, canonical_client=None):
        # P9 - THE CANONICAL TWIN IS READ, NEVER MERGED.
        #
        # `self.twin` below is this SIMULATOR's own TwinStateStore, holding the
        # simulated fleet. `self.canonical` is a read-only view of the HMI backend's
        # Twin, holding whatever telemetry actually arrived there. They are two
        # different modelled systems that happen to share vehicle ids, and nothing
        # copies a value from one into the other. Off unless explicitly supplied, so
        # the existing offline demonstration is unchanged.
        self.canonical = canonical_client

        # P9 - CWD INDEPENDENCE.
        # The default used to be the relative string "config", so the bridge only found
        # its YAML when the process happened to be started from
        # `SYNQRA_SIH2026-27-main/`. Two test suites already worked around that with
        # `os.chdir`. Configuration is now located from THIS FILE, so it resolves the
        # same from any working directory. The VALUES are unchanged.
        self.config_dir = config_dir if config_dir is not None else DEFAULT_CONFIG_DIR
        self.load_configurations()
        self.reset()

    def load_configurations(self):
        """Loads authoritative YAML configuration files."""
        with open(os.path.join(self.config_dir, "vehicle.yaml"), "r") as f:
            self.vehicle_cfg = yaml.safe_load(f)
        with open(os.path.join(self.config_dir, "roads.yaml"), "r") as f:
            self.roads_cfg = yaml.safe_load(f)
        with open(os.path.join(self.config_dir, "nodes.yaml"), "r") as f:
            self.nodes_cfg = yaml.safe_load(f)
        with open(os.path.join(self.config_dir, "weather.yaml"), "r") as f:
            self.weather_cfg = yaml.safe_load(f)
        with open(os.path.join(self.config_dir, "scenarios.yaml"), "r") as f:
            self.scenario_cfg = yaml.safe_load(f)

    def build_network(self) -> MineNetwork:
        """Builds network graph matching roads and nodes config."""
        network = MineNetwork()
        for n in self.nodes_cfg["nodes"]:
            network.add_node(
                node_id=n["id"],
                node_type=n["type"],
                service_rate_vph=n["service_rate_vph"],
                criticality=n.get("criticality", 1.0)
            )
        for r in self.roads_cfg["segments"]:
            network.add_edge(
                road_id=r["road_id"],
                start_node=r["start_node"],
                end_node=r["end_node"],
                length_m=r["length_m"],
                grade_percent=r["grade_percent"],
                curve_radius_m=r["curve_radius_m"],
                speed_limit_mps=r["speed_limit_mps"],
                width_m=r.get("width_m", 15.0)
            )
        return network

    def reset(self):
        """Resets the simulator and interactive UI control states."""
        self.network = self.build_network()
        
        # Interactive scenario config base
        sim_scenario_cfg = dict(self.scenario_cfg)
        sim_scenario_cfg["name"] = "interactive_ui"
        sim_scenario_cfg["timestep_s"] = 1.0
        sim_scenario_cfg["fleet_size"] = 4
        sim_scenario_cfg["local_governor_active"] = True
        sim_scenario_cfg["slot_reservation_active"] = True
        sim_scenario_cfg["optimization_mode"] = "baseline"

        self.sim = Simulator(self.network, self.vehicle_cfg, self.weather_cfg, sim_scenario_cfg)

        # P7 - ONE canonical Twin, in this process, alongside the simulator.
        #
        # Option A from the P7 brief: the simulator and the Twin share a process, so
        # they share one TwinStateStore object honestly. No cross-process claim is
        # made here; publishing to the FastAPI backend remains a separate transport.
        self.domain = UISimulationDomain(self.sim, self.vehicle_cfg)
        # P10 - freshness is now EVALUATED in this process too.
        #
        # This store was built with `stale_after_s=None`, which under the P1 rule means
        # freshness is never evaluated: every field reported NOT_EVALUATED and the
        # renderer could never show STALE. The threshold is not invented here - it is the
        # same configured `max_telemetry_age_seconds` the backend and the command gateway
        # already use (P9 centralization), so all three agree on when a value has aged out.
        self.twin = TwinStateStore(network=self.network, mode=TwinMode.SIMULATION,
                                   stale_after_s=TWIN_STALE_AFTER_S)
        for _v in self.sim.vehicles:
            self.twin.register_vehicle(_v)
        
        # Store nominal physical design speed limits on edges
        for edge in self.sim.network.edges.values():
            edge.nominal_speed_limit = float(edge.speed_limit_mps)

        # Interactive UI controls state
        self.running = False
        self.speed_multiplier = 1  # 1x, 2x, 5x, 10x, 20x
        self.manual_fog_active = False
        self.current_visibility_m = 50.0
        self.target_speed_kmh = 35.0   # Default user commanded target
        self.e_stop_active = False
        self.selected_truck_id = "TRUCK_01"
        
        # History for real-time graphs (sliding window of 120 points)
        self.history_time = collections.deque(maxlen=120)
        self.history_speed = collections.deque(maxlen=120)
        self.history_safe_speed = collections.deque(maxlen=120)
        self.history_cmd_speed = collections.deque(maxlen=120)
        
        # Car-following safety state tracking (per vehicle ID)
        self.following_stop_state: Dict[str, bool] = {}
        
        # Initial truck position configuration for instant visual feedback:
        # TRUCK_01 starts on ROAD_1 heading towards the downhill switchback
        t1 = self.get_truck(self.selected_truck_id)
        if t1:
            if t1 in self.sim.network.nodes["SHOVEL"].queue.vehicles:
                self.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t1)
            t1.state = "traveling"
            t1.current_edge = "ROAD_1"
            t1.current_node = None
            t1.position_s = 60.0
            t1.is_loaded = True
            t1.mass_kg = self.vehicle_cfg["tare_mass_kg"] + self.vehicle_cfg["payload_mass_kg"]
            t1.speed_mps = 6.0
            self.sim.network.edges["ROAD_1"].vehicles.append(t1)
            
        self.apply_environment_parameters()
        self.evaluate_physics()
        self.record_history_point()

    def get_truck(self, truck_id: str):
        """Retrieves vehicle object by ID."""
        for v in self.sim.vehicles:
            if v.id == truck_id:
                return v
        return self.sim.vehicles[0] if self.sim.vehicles else None

    def set_visibility(self, visibility_m: float):
        """
        Updates live visibility (5.0m - 50.0m) and calculates physical friction/surface.
        Propagates directly into simulator's FogModel and road segments.
        """
        self.current_visibility_m = float(np.clip(visibility_m, 5.0, 50.0))
        self.manual_fog_active = True
        self.apply_environment_parameters()
        self.evaluate_physics()

    def apply_environment_parameters(self):
        """
        Interpolates road friction (mu), rolling resistance (Crr), and surface condition
        matching the physics configuration in weather.yaml.
        """
        v = self.current_visibility_m
        
        # Physics interpolation based on weather.yaml:
        # Clear: 50m -> mu=0.60, Crr=0.02, dry
        # Dense: 15m -> mu=0.25, Crr=0.03, wet
        # Extreme: 5m -> mu=0.15, Crr=0.04, saturated
        if v >= 15.0:
            frac = (v - 15.0) / 35.0
            mu = 0.25 + frac * (0.60 - 0.25)
            crr = 0.03 + frac * (0.02 - 0.03)
            surface = "dry" if v >= 35.0 else ("damp" if v >= 20.0 else "wet")
        else:
            frac = (v - 5.0) / 10.0
            mu = 0.15 + frac * (0.25 - 0.15)
            crr = 0.04 + frac * (0.03 - 0.04)
            surface = "saturated" if v <= 8.0 else "wet"

        # Apply to simulator FogModel
        self.sim.fog_model.current_visibility = v
        self.sim.fog_model.current_friction = mu
        self.sim.fog_model.current_rr = crr
        self.sim.fog_model.current_state = surface

        # Apply environmental parameters to all road edges
        for edge in self.sim.network.edges.values():
            edge.visibility_m = v
            edge.friction_mu = mu
            edge.c_rr = crr
            edge.surface_state = surface
            
            # Keep the nominal speed limit intact on the edge for the domain solver.
            # P7: fall back to the edge's own CONFIGURED limit, never a literal.
            nom_limit = getattr(edge, "nominal_speed_limit", edge.speed_limit_mps)
            
            # The edge speed limit for dispatch represents the commanded limit clamped to nominal road limit
            target_mps = 0.0 if self.e_stop_active else (self.target_speed_kmh / 3.6)
            edge.speed_limit_mps = min(nom_limit, target_mps)

    def compute_car_following_limit(self, vehicle, edge) -> Tuple[float, Optional[str], float, bool]:
        """
        Calculates the longitudinal gap and car-following speed limit for a vehicle on a road edge.
        Enforces a safety stop when gap <= safe_headway, with 5m hysteresis buffer before resuming.
        
        Returns:
            (car_following_speed_limit_mps, lead_vehicle_id, gap_m, is_following_stopped)
        """
        if not edge or vehicle not in edge.vehicles:
            self.following_stop_state[vehicle.id] = False
            return float('inf'), None, float('inf'), False

        veh_len = float(getattr(vehicle, "length", self.vehicle_cfg.get("length_m", 14.5)))
        safe_hw = float(getattr(vehicle, "safe_headway_m", self.vehicle_cfg.get("min_static_headway_m", 15.5)))

        # Find position safely
        try:
            curr_pos = float(getattr(vehicle, "position_s", 0.0))
            if math.isnan(curr_pos) or math.isinf(curr_pos):
                curr_pos = 0.0
        except Exception:
            curr_pos = 0.0

        lead_v = None
        min_pos_diff = float('inf')

        # Find the vehicle immediately ahead on the SAME road edge
        for other in edge.vehicles:
            if other.id == vehicle.id:
                continue
            try:
                other_pos = float(getattr(other, "position_s", 0.0))
                if math.isnan(other_pos) or math.isinf(other_pos):
                    continue
            except Exception:
                continue

            pos_diff = other_pos - curr_pos
            if 0.0 < pos_diff < min_pos_diff:
                min_pos_diff = pos_diff
                lead_v = other

        if not lead_v:
            self.following_stop_state[vehicle.id] = False
            return float('inf'), None, float('inf'), False

        lead_len = float(getattr(lead_v, "length", self.vehicle_cfg.get("length_m", 14.5)))
        gap = max(0.0, min_pos_diff - lead_len)

        # Hysteresis Logic:
        # Stop when gap <= safe_headway
        # Resume only when gap >= safe_headway + 5.0m
        hysteresis_margin = 5.0
        was_stopped = self.following_stop_state.get(vehicle.id, False)

        if was_stopped:
            if gap >= safe_hw + hysteresis_margin:
                is_stopped = False
            else:
                is_stopped = True
        else:
            if gap <= safe_hw:
                is_stopped = True
            else:
                is_stopped = False

        self.following_stop_state[vehicle.id] = is_stopped

        if is_stopped:
            return 0.0, lead_v.id, gap, True
        else:
            return float('inf'), lead_v.id, gap, False

    def evaluate_physics(self):
        """
        P7: delegate to the DOMAIN, then publish to the canonical Twin.

        This method no longer computes safety. `twin/ui_domain.py` calls the single
        authoritative solver (fog_safe via the P2 adapter); this bridge then syncs the
        resulting domain state into the canonical TwinStateStore, which is what the
        renderer reads.
        """
        self.domain.evaluate(
            target_speed_kmh=self.target_speed_kmh,
            e_stop_active=self.e_stop_active,
            car_following_limit=self.compute_car_following_limit,
        )
        self.sync_twin()

    def sync_twin(self):
        """Publish current domain state into the canonical Twin (simulation clock)."""
        self.twin.sync_from_simulation(
            network=self.sim.network,
            vehicles=self.sim.vehicles,
            fog_model=self.sim.fog_model,
            timestamp=self.sim.current_time,
        )

    def twin_v_safe_mps(self, vehicle_id):
        """
        Authoritative safe speed for one vehicle, READ FROM THE CANONICAL TWIN.

        Returns None when the Twin has no value. The caller must render UNAVAILABLE
        rather than substituting an optimistic number.
        """
        field = self.twin.get_vehicle_field(vehicle_id, "v_safe_mps")
        return field.value if field.is_available else None

    def twin_field(self, vehicle_id, name):
        """Full provenance envelope for a field, for display (source/quality/freshness)."""
        return self.twin.get_vehicle_field(vehicle_id, name)

    def set_target_speed(self, speed_kmh: float):
        """Sets commanded target speed (km/h). Local governor automatically clamps to v_safe."""
        self.target_speed_kmh = float(np.clip(speed_kmh, 0.0, 50.0))
        self.apply_environment_parameters()
        self.evaluate_physics()

    def trigger_emergency_stop(self):
        """Activates emergency stop."""
        self.e_stop_active = True
        self.apply_environment_parameters()
        self.evaluate_physics()

    def release_emergency_stop(self):
        """Releases emergency stop."""
        self.e_stop_active = False
        self.target_speed_kmh = 35.0
        self.apply_environment_parameters()
        self.evaluate_physics()

    def step(self):
        """Advances simulation by 1 timestep (dt) and records telemetry."""
        # Record pre-step state of traveling vehicles
        pre_states = {}
        for edge in self.sim.network.edges.values():
            for v in edge.vehicles:
                pre_states[v.id] = {
                    "position_s": v.position_s,
                    "speed_mps": v.speed_mps,
                    "is_following_stopped": self.following_stop_state.get(v.id, False)
                }

        self.apply_environment_parameters()

        # Advance backend simulation step (preserves authoritative state machine)
        self.sim.run_step()

        # Update environment parameters and resolve physics
        self.apply_environment_parameters()
        self.evaluate_physics()

        # Enforce following stop holding and braking
        for edge in self.sim.network.edges.values():
            for v in edge.vehicles:
                if getattr(v, "is_following_stopped", False):
                    prev = pre_states.get(v.id)
                    if prev:
                        if prev["speed_mps"] <= 0.05:
                            # Stationary hold
                            v.speed_mps = 0.0
                            v.acceleration_mps2 = 0.0
                            v.position_s = prev["position_s"]
                        else:
                            # Decelerate smoothly to 0 m/s using physics braking
                            phys_a_dec = max(1.5, getattr(v, "a_dec", 2.5))
                            new_spd = max(0.0, prev["speed_mps"] - phys_a_dec * self.sim.dt)
                            v.speed_mps = new_spd
                            v.acceleration_mps2 = -phys_a_dec
                            v.position_s = prev["position_s"] + 0.5 * (prev["speed_mps"] + new_spd) * self.sim.dt
                    v.v_command_mps = 0.0
                    v.v_dispatch_mps = 0.0

        # Refresh evaluation and record telemetry point
        self.evaluate_physics()
        self.record_history_point()

    def record_history_point(self):
        """Records telemetry point for real-time chart."""
        t1 = self.get_truck(self.selected_truck_id)
        t = self.sim.current_time
        speed_kmh = (t1.speed_mps * 3.6) if t1 else 0.0
        # P7.1: authoritative v_safe from the canonical Twin. None = UNAVAILABLE;
        # there is deliberately no 0.0 fallback, which would read as 'stopped'.
        safe_kmh = to_kmh(self.twin_v_safe_mps(t1.id)) if t1 else None
        cmd_kmh = (t1.v_command_mps * 3.6) if t1 else 0.0

        self.history_time.append(t)
        self.history_speed.append(speed_kmh)
        self.history_safe_speed.append(safe_kmh)
        self.history_cmd_speed.append(cmd_kmh)

    def get_vehicle_location(self, v) -> Dict[str, Any]:
        """
        Determines exact physical location (edge or node queue) of a vehicle.
        """
        if not v:
            return {"type": "none", "id": "UNKNOWN", "pos": 0.0, "desc": "Unknown"}

        # Check Node Queues first
        crusher_node = self.sim.network.nodes.get("CRUSHER")
        if crusher_node and crusher_node.queue and v in crusher_node.queue.vehicles:
            q_idx = crusher_node.queue.vehicles.index(v)
            service_rem = max(0.0, crusher_node.queue.service_time_s - crusher_node.queue.accumulated_service_time)
            return {
                "type": "node",
                "node_id": "CRUSHER",
                "queue_index": q_idx,
                "queue_len": crusher_node.queue.length,
                "service_rem_s": service_rem,
                "service_total_s": crusher_node.queue.service_time_s,
                "desc": f"CRUSHER (Unloading: {service_rem:.0f}s left)" if q_idx == 0 else f"CRUSHER (Queue #{q_idx+1})"
            }

        shovel_node = self.sim.network.nodes.get("SHOVEL")
        if shovel_node and shovel_node.queue and v in shovel_node.queue.vehicles:
            q_idx = shovel_node.queue.vehicles.index(v)
            service_rem = max(0.0, shovel_node.queue.service_time_s - shovel_node.queue.accumulated_service_time)
            return {
                "type": "node",
                "node_id": "SHOVEL",
                "queue_index": q_idx,
                "queue_len": shovel_node.queue.length,
                "service_rem_s": service_rem,
                "service_total_s": shovel_node.queue.service_time_s,
                "desc": f"SHOVEL (Loading: {service_rem:.0f}s left)" if q_idx == 0 else f"SHOVEL (Queue #{q_idx+1})"
            }

        if v in getattr(self.sim, "shovel_departure_buffer", []):
            return {
                "type": "node",
                "node_id": "SHOVEL",
                "queue_index": 0,
                "queue_len": len(self.sim.shovel_departure_buffer),
                "service_rem_s": 0.0,
                "service_total_s": 0.0,
                "desc": "SHOVEL (Awaiting Departure Slot)"
            }

        intersection_node = self.sim.network.nodes.get("INTERSECTION")
        if intersection_node and intersection_node.queue and v in intersection_node.queue.vehicles:
            q_idx = intersection_node.queue.vehicles.index(v)
            return {
                "type": "node",
                "node_id": "INTERSECTION",
                "queue_index": q_idx,
                "queue_len": intersection_node.queue.length,
                "service_rem_s": 0.0,
                "service_total_s": 0.0,
                "desc": f"INTERSECTION (Queued for Slot #{q_idx+1})"
            }

        # Check Road Edges
        for edge_id, edge in self.sim.network.edges.items():
            if v in edge.vehicles:
                return {
                    "type": "edge",
                    "edge_id": edge_id,
                    "pos_m": v.position_s,
                    "length_m": edge.length_m,
                    "desc": f"{edge_id} (Traveling)"
                }

        # Fallback to vehicle's current_edge or current_node attributes
        if v.current_edge:
            edge = self.sim.network.edges.get(v.current_edge)
            l_m = edge.length_m if edge else 500.0
            return {"type": "edge", "edge_id": v.current_edge, "pos_m": v.position_s, "length_m": l_m, "desc": f"{v.current_edge} (Traveling)"}
        elif v.current_node:
            return {"type": "node", "node_id": v.current_node, "queue_index": 0, "queue_len": 1, "service_rem_s": 0.0, "service_total_s": 0.0, "desc": f"{v.current_node} (Node)"}

        return {"type": "node", "node_id": "SHOVEL", "queue_index": 0, "queue_len": 0, "service_rem_s": 0.0, "service_total_s": 0.0, "desc": "SHOVEL"}

    def get_fleet_telemetry(self) -> List[Dict[str, Any]]:
        """
        Extracts live, authoritative per-vehicle telemetry for all trucks in the fleet.
        Derives speed, v_safe, commanded speed, location, gap, and operational status directly
        from the Simulator state.
        """
        fleet_data = []
        crusher_node = self.sim.network.nodes.get("CRUSHER")
        shovel_node = self.sim.network.nodes.get("SHOVEL")
        intersection_node = self.sim.network.nodes.get("INTERSECTION")

        for v in self.sim.vehicles:
            speed_mps = float(getattr(v, "speed_mps", 0.0))
            speed_kmh = speed_mps * 3.6
            # P7: authoritative v_safe comes from the canonical Twin. No fallback
            # literal - an unknown safe speed is UNAVAILABLE, never an optimistic number.
            v_safe_mps = self.twin_v_safe_mps(v.id)
            v_safe_kmh = None if v_safe_mps is None else v_safe_mps * 3.6
            v_cmd_mps = float(getattr(v, "v_command_mps", 0.0))
            v_cmd_kmh = v_cmd_mps * 3.6

            loc = self.get_vehicle_location(v)
            if loc["type"] == "edge":
                loc_badge = loc["edge_id"]
            else:
                loc_badge = loc["node_id"]

            lead_id = getattr(v, "lead_vehicle_id", None)
            lead_gap_m = float(getattr(v, "lead_gap_m", float('inf')))
            is_fol_stopped = bool(getattr(v, "is_following_stopped", False))

            # Determine operational status label & color
            if self.e_stop_active:
                status_label = "E-STOP"
                status_color = (255, 60, 60)
            elif not safety_known(v_safe_mps):
                # No authoritative safe speed: state is UNKNOWN, never implied safe.
                status_label = "NO V_SAFE"
                status_color = (150, 150, 160)
            elif exceeds(speed_mps, v_safe_mps, 0.1) or getattr(v, "warning_fault", False):
                status_label = "UNSAFE"
                status_color = (255, 60, 60)
            elif crusher_node and crusher_node.queue and v in crusher_node.queue.vehicles:
                q_idx = crusher_node.queue.vehicles.index(v)
                if q_idx == 0:
                    status_label = "UNLOAD"
                    status_color = (255, 170, 60)
                else:
                    status_label = f"QUEUED #{q_idx+1}"
                    status_color = (180, 150, 220)
            elif shovel_node and shovel_node.queue and v in shovel_node.queue.vehicles:
                q_idx = shovel_node.queue.vehicles.index(v)
                if q_idx == 0:
                    status_label = "LOADING"
                    status_color = (100, 200, 255)
                else:
                    status_label = f"QUEUED #{q_idx+1}"
                    status_color = (180, 150, 220)
            elif v in getattr(self.sim, "shovel_departure_buffer", []):
                status_label = "BUFFER"
                status_color = (180, 150, 220)
            elif intersection_node and intersection_node.queue and v in intersection_node.queue.vehicles:
                q_idx = intersection_node.queue.vehicles.index(v)
                status_label = f"QUEUED #{q_idx+1}"
                status_color = (180, 150, 220)
            elif is_fol_stopped:
                status_label = "FOLLOWING"
                status_color = (250, 180, 45)
            elif speed_mps > 0.5:
                if (safety_known(v_safe_mps) and speed_mps > 0.88 * v_safe_mps) \
                        or self.current_visibility_m <= 10.0:
                    status_label = "CAUTION"
                    status_color = (250, 180, 45)
                else:
                    status_label = "MOVING"
                    status_color = (50, 225, 110)
            else:
                status_label = "STOPPED"
                status_color = (160, 170, 185)

            fleet_data.append({
                "id": v.id,
                "speed_mps": speed_mps,
                "speed_kmh": speed_kmh,
                "v_safe_mps": v_safe_mps,
                "v_safe_kmh": v_safe_kmh,
                "v_command_mps": v_cmd_mps,
                "v_command_kmh": v_cmd_kmh,
                "is_loaded": bool(getattr(v, "is_loaded", False)),
                "mass_kg": float(getattr(v, "mass_kg", 74000.0)),
                "location_id": loc_badge,
                "location_desc": loc["desc"],
                "lead_vehicle_id": lead_id,
                "lead_gap_m": lead_gap_m,
                "is_following_stopped": is_fol_stopped,
                "status_label": status_label,
                "status_color": status_color,
                "is_selected": (v.id == self.selected_truck_id)
            })

        return fleet_data

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Extracts comprehensive telemetry for UI display.
        Uses authoritative backend physics values.
        """
        t1 = self.get_truck(self.selected_truck_id)
        loc = self.get_vehicle_location(t1)

        speed_mps = float(t1.speed_mps) if t1 else 0.0
        # P7: no optimistic fallback; None means UNAVAILABLE.
        v_safe_mps = self.twin_v_safe_mps(t1.id) if t1 else None
        v_cmd_mps = float(t1.v_command_mps) if t1 else 0.0
        v_disp_mps = float(getattr(t1, "v_dispatch_mps", speed_mps)) if t1 else 0.0
        is_loaded = bool(t1.is_loaded) if t1 else False
        mass_kg = float(t1.mass_kg) if t1 else 74000.0
        state = str(t1.state) if t1 else "idle"

        # Road / Node environment values
        if loc["type"] == "edge":
            curr_edge_id = loc["edge_id"]
            edge = self.sim.network.edges.get(curr_edge_id)
            grade_pct = float(edge.grade_percent) if edge else 0.0
            friction_mu = float(edge.friction_mu) if edge else 0.60
            surface_state = str(edge.surface_state) if edge else "dry"
            # P7: no edge => no configured road limit. UNAVAILABLE, not an assumed 50 km/h.
            road_limit_mps = float(getattr(edge, "nominal_speed_limit", edge.speed_limit_mps)) if edge else None
            road_length_m = float(edge.length_m) if edge else 500.0
            curve_radius_m = float(edge.curve_radius_m) if edge else 0.0
            vis_m = float(edge.visibility_m) if edge else self.current_visibility_m
            pos_m = float(t1.position_s)
            progress_pct = min(100.0, (pos_m / max(1.0, road_length_m)) * 100.0)
            location_label = loc["desc"]
        else:
            curr_edge_id = loc["node_id"]
            grade_pct = 0.0
            # P7: nothing is known about this road. Report UNAVAILABLE rather than
            # inventing friction, surface or a speed limit.
            friction_mu = None
            surface_state = None
            road_limit_mps = None
            road_length_m = 0.0
            curve_radius_m = 0.0
            vis_m = self.current_visibility_m
            pos_m = 0.0
            progress_pct = 100.0
            location_label = loc["desc"]

        stop_envelope_m = float(getattr(t1, "stop_envelope_m", 15.5)) if t1 else 15.5
        safe_headway_m = float(getattr(t1, "safe_headway_m", 15.5)) if t1 else 15.5
        is_fol_stopped = bool(getattr(t1, "is_following_stopped", False)) if t1 else False
        lead_veh_id = getattr(t1, "lead_vehicle_id", None) if t1 else None
        lead_gap_m = float(getattr(t1, "lead_gap_m", float('inf'))) if t1 else float('inf')

        # Safety status classification (SAFE, CAUTION, UNSAFE)
        if self.e_stop_active:
            safety_status = "E-STOP"
            safety_color = (255, 60, 60)
            safety_desc = "EMERGENCY STOP ACTIVATED"
        elif not safety_known(v_safe_mps):
            safety_status = "NO V_SAFE"
            safety_color = (150, 150, 160)
            safety_desc = "SAFE SPEED UNAVAILABLE - NOT EVALUATED"
        elif exceeds(speed_mps, v_safe_mps, 0.1) or getattr(t1, "warning_fault", False):
            safety_status = "UNSAFE"
            safety_color = (245, 60, 60)
            safety_desc = "SPEED EXCEEDS SAFE CEILING!"
        elif is_fol_stopped:
            safety_status = "CAUTION"
            safety_color = (250, 180, 45)
            lead_str = f"behind {lead_veh_id} (Gap: {lead_gap_m:.1f}m)" if lead_veh_id else "(Lead Truck Ahead)"
            safety_desc = f"FOLLOWING STOP — MAINTAINING SAFE HEADWAY {lead_str}"
        elif vis_m <= 10.0 \
                or (safety_known(v_safe_mps) and speed_mps > 0.88 * v_safe_mps) \
                or (grade_pct is not None and grade_pct < -5.0 and surface_state in ["wet", "saturated"]):
            safety_status = "CAUTION"
            safety_color = (250, 180, 45)
            safety_desc = "HAZARDOUS CONDITIONS / NEAR LIMIT"
        else:
            safety_status = "SAFE"
            safety_color = (50, 225, 110)
            safety_desc = "OPERATING SAFELY WITHIN LIMITS"

        # Crusher & Shovel Queue objects directly from authoritative Simulator network
        crusher_q = self.sim.network.nodes["CRUSHER"].queue
        shovel_q = self.sim.network.nodes["SHOVEL"].queue
        crusher_rem_s = max(0.0, crusher_q.service_time_s - crusher_q.accumulated_service_time) if crusher_q and crusher_q.length > 0 else 0.0
        shovel_rem_s = max(0.0, shovel_q.service_time_s - shovel_q.accumulated_service_time) if shovel_q and shovel_q.length > 0 else 0.0

        return {
            "timestamp": self.sim.current_time,
            "running": self.running,
            "e_stop": self.e_stop_active,
            "speed_multiplier": self.speed_multiplier,
            "truck_id": self.selected_truck_id,
            "truck_state": state,
            "location_info": loc,
            "location_label": location_label,
            "is_loaded": is_loaded,
            "mass_kg": mass_kg,
            "speed_mps": speed_mps,
            "speed_kmh": speed_mps * 3.6,
            "v_safe_mps": v_safe_mps,
            "v_safe_kmh": to_kmh(v_safe_mps),
            "v_command_mps": v_cmd_mps,
            "v_command_kmh": v_cmd_mps * 3.6,
            "v_dispatch_mps": v_disp_mps,
            "v_dispatch_kmh": v_disp_mps * 3.6,
            "target_speed_kmh": self.target_speed_kmh,
            "current_edge": curr_edge_id,
            "position_m": pos_m,
            "road_length_m": road_length_m,
            "progress_pct": progress_pct,
            "grade_percent": grade_pct,
            "curve_radius_m": curve_radius_m,
            "friction_mu": friction_mu,
            "surface_state": surface_state,
            "visibility_m": vis_m,
            "speed_limit_mps": road_limit_mps,
            "speed_limit_kmh": to_kmh(road_limit_mps),
            "stop_envelope_m": stop_envelope_m,
            "safe_headway_m": safe_headway_m,
            "is_following_stopped": is_fol_stopped,
            "lead_vehicle_id": lead_veh_id,
            "lead_gap_m": lead_gap_m,
            "safety_status": safety_status,
            "safety_color": safety_color,
            "safety_desc": safety_desc,
            "crusher_queue_len": crusher_q.length if crusher_q else 0,
            "crusher_service_rem_s": crusher_rem_s,
            "shovel_queue_len": shovel_q.length if shovel_q else 0,
            "shovel_service_rem_s": shovel_rem_s,
            "total_tonnes": sum(getattr(v, "total_tonnes_hauled", 0.0) for v in self.sim.vehicles),
            "fleet": self.get_fleet_telemetry()
        }


# ==============================================================================
# 2. Pygame UI & 2.5D Mine Visualization Engine
# ==============================================================================

# Palette Definitions (High Contrast Dark Control Room Theme)
COLOR_BG = (13, 17, 23)
COLOR_PANEL_BG = (22, 27, 34)
COLOR_PANEL_BORDER = (48, 54, 61)
COLOR_HEADER_BG = (9, 12, 16)
COLOR_TEXT_PRIMARY = (240, 246, 252)
COLOR_TEXT_SECONDARY = (139, 148, 158)
COLOR_TEXT_MUTED = (80, 90, 100)

COLOR_CYAN = (56, 189, 248)
COLOR_GREEN = (52, 211, 153)
COLOR_AMBER = (251, 191, 36)
COLOR_RED = (248, 113, 113)
COLOR_BLUE = (96, 165, 250)
COLOR_PURPLE = (168, 85, 247)

# Road & Terrain Colors
COLOR_MINE_GROUND = (28, 24, 20)
COLOR_ROAD_SURFACE = (65, 60, 55)
COLOR_ROAD_EDGE = (120, 110, 95)
COLOR_ROAD_LINE = (180, 170, 150)
COLOR_BERM = (45, 38, 30)
COLOR_ORE_ROCK = (180, 120, 50)

class UIElementButton:
    """Interactive clickable button."""
    def __init__(self, rect: Tuple[int, int, int, int], text: str, callback,
                 bg_color=COLOR_PANEL_BG, text_color=COLOR_TEXT_PRIMARY, tag=""):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.bg_color = bg_color
        self.text_color = text_color
        self.tag = tag
        self.hovered = False

    def handle_event(self, event, mouse_pos) -> bool:
        import pygame
        x, y, w, h = self.rect
        self.hovered = (x <= mouse_pos[0] <= x + w and y <= mouse_pos[1] <= y + h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            if self.callback:
                self.callback()
            return True
        return False

    def draw(self, surface, font):
        import pygame
        x, y, w, h = self.rect
        col = (min(255, self.bg_color[0] + 30), min(255, self.bg_color[1] + 30), min(255, self.bg_color[2] + 30)) if self.hovered else self.bg_color
        pygame.draw.rect(surface, col, (x, y, w, h), border_radius=6)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER if not self.hovered else COLOR_CYAN, (x, y, w, h), 1, border_radius=6)
        
        lbl = font.render(self.text, True, self.text_color)
        lx = x + (w - lbl.get_width()) // 2
        ly = y + (h - lbl.get_height()) // 2
        surface.blit(lbl, (lx, ly))


class UIElementSlider:
    """Interactive drag slider."""
    def __init__(self, rect: Tuple[int, int, int, int], min_val: float, max_val: float,
                 initial_val: float, label: str, unit: str, on_change):
        self.rect = rect
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.label = label
        self.unit = unit
        self.on_change = on_change
        self.dragging = False

    def handle_event(self, event, mouse_pos) -> bool:
        import pygame
        x, y, w, h = self.rect
        handle_x = x + int(((self.val - self.min_val) / (self.max_val - self.min_val)) * w)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (x - 8 <= mouse_pos[0] <= x + w + 8) and (y - 12 <= mouse_pos[1] <= y + h + 12):
                self.dragging = True
                self.update_from_mouse(mouse_pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_from_mouse(mouse_pos[0])
            return True
        return False

    def update_from_mouse(self, mouse_x: int):
        x, y, w, h = self.rect
        rel = np.clip((mouse_x - x) / float(w), 0.0, 1.0)
        self.val = float(self.min_val + rel * (self.max_val - self.min_val))
        if self.on_change:
            self.on_change(self.val)

    def draw(self, surface, font, val_font):
        import pygame
        x, y, w, h = self.rect
        
        # Track background
        pygame.draw.rect(surface, (30, 36, 44), (x, y + 4, w, h - 8), border_radius=4)
        
        # Filled track
        frac = (self.val - self.min_val) / (self.max_val - self.min_val)
        fill_w = int(frac * w)
        if fill_w > 0:
            pygame.draw.rect(surface, COLOR_CYAN, (x, y + 4, fill_w, h - 8), border_radius=4)
            
        # Slider Knob Handle
        handle_x = x + fill_w
        handle_y = y + h // 2
        pygame.draw.circle(surface, COLOR_TEXT_PRIMARY, (handle_x, handle_y), 8)
        pygame.draw.circle(surface, (15, 23, 42), (handle_x, handle_y), 4)


class MiningVisualizerUI:
    """
    Main Pygame Interactive Application for FOG-ORCHESTRATOR 2.0.
    """
    def __init__(self, bridge: SimulationUIBridge, headless: bool = False):
        self.bridge = bridge
        self.headless = headless
        
        # Window Dimensions
        self.width = 1320
        self.height = 840
        self.fps = 60
        self.last_wall_time = time.time()
        self.sim_time_accumulator = 0.0

        # Initialize Pygame
        import pygame
        self.pygame = pygame
        
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            
        self.pygame.init()
        self.pygame.font.init()
        
        if not headless:
            self.screen = self.pygame.display.set_mode((self.width, self.height))
            self.pygame.display.set_caption("FOG-ORCHESTRATOR 2.0 — Mine Haulage Digital Twin & Fog Safety Monitor")
        else:
            self.screen = self.pygame.Surface((self.width, self.height))
            
        self.clock = self.pygame.time.Clock()
        self.init_fonts()
        self.init_ui_controls()
        self.init_road_path()

    def init_fonts(self):
        """Initializes system fonts with graceful fallback."""
        pygame = self.pygame
        font_names = ["Segoe UI", "Arial", "DejaVu Sans", "Helvetica"]
        
        self.font_title = pygame.font.SysFont(font_names, 19, bold=True)
        self.font_section = pygame.font.SysFont(font_names, 15, bold=True)
        self.font_body = pygame.font.SysFont(font_names, 13)
        self.font_bold = pygame.font.SysFont(font_names, 13, bold=True)
        self.font_small = pygame.font.SysFont(font_names, 11)
        self.font_digits_large = pygame.font.SysFont(["Consolas", "Courier New", "monospace"], 24, bold=True)
        self.font_digits_med = pygame.font.SysFont(["Consolas", "Courier New", "monospace"], 16, bold=True)
        self.font_badge = pygame.font.SysFont(font_names, 16, bold=True)

    def init_road_path(self):
        """
        Defines the 2.5D visual mine circuit trajectory.
        Maps the 3 road segments to screen coordinates:
        - ROAD_1 (Flat 0% grade, 500m): High pit bench traversal
        - ROAD_2 (Downhill -8% grade, 400m, curve R=50m): Steep curved switchback descending to basin
        - ROAD_RETURN (Uphill +4% grade, 900m): Long ascending return ramp climbing back up
        """
        self.view_x = 24
        self.view_y = 68
        self.view_w = 1272
        self.view_h = 320

        # Trajectory Anchor Waypoints in viewport space (x_norm, y_norm, elevation_z, grade_pct)
        self.waypoints = [
            # SHOVEL Loading Area (Left Bench, Elev 0)
            {"id": "SHOVEL", "s": 0.0, "x": 0.08, "y": 0.32, "z": 0.0, "edge": "ROAD_1"},
            # ROAD_1 Flat Section (Bench traversing right)
            {"id": "R1_MID", "s": 250.0, "x": 0.40, "y": 0.32, "z": 0.0, "edge": "ROAD_1"},
            {"id": "INTERSECTION", "s": 500.0, "x": 0.72, "y": 0.34, "z": 0.0, "edge": "ROAD_1"},
            
            # ROAD_2 Downhill Switchback Curve (-8% Grade descending to Crusher basin)
            {"id": "R2_CURVE_1", "s": 650.0, "x": 0.90, "y": 0.48, "z": -12.0, "edge": "ROAD_2"},
            {"id": "R2_CURVE_2", "s": 800.0, "x": 0.85, "y": 0.78, "z": -24.0, "edge": "ROAD_2"},
            {"id": "CRUSHER", "s": 900.0, "x": 0.68, "y": 0.86, "z": -32.0, "edge": "ROAD_2"},
            
            # ROAD_RETURN Uphill Ramp (+4% Grade climbing back from Crusher to Shovel)
            {"id": "RET_MID_1", "s": 1200.0, "x": 0.38, "y": 0.84, "z": -20.0, "edge": "ROAD_RETURN"},
            {"id": "RET_MID_2", "s": 1500.0, "x": 0.12, "y": 0.72, "z": -8.0, "edge": "ROAD_RETURN"},
            {"id": "RET_TURN", "s": 1750.0, "x": 0.05, "y": 0.50, "z": -2.0, "edge": "ROAD_RETURN"},
            {"id": "LOOP_END", "s": 1800.0, "x": 0.08, "y": 0.32, "z": 0.0, "edge": "ROAD_RETURN"}
        ]

    def get_screen_pos_from_edge(self, edge_id: str, position_s: float) -> Tuple[float, float, float, float]:
        """
        Maps a truck's current road edge and position (s meters) to screen pixel (x, y),
        heading angle (radians), and perspective scale factor.
        """
        # Determine global circuit distance (0m to 1800m)
        if edge_id == "ROAD_1":
            s_global = np.clip(position_s, 0.0, 500.0)
        elif edge_id == "ROAD_2":
            s_global = 500.0 + np.clip(position_s, 0.0, 400.0)
        elif edge_id == "ROAD_RETURN":
            s_global = 900.0 + np.clip(position_s, 0.0, 900.0)
        else:
            s_global = 0.0

        # Find interpolation segment between waypoints
        n = len(self.waypoints)
        idx = 0
        for i in range(n - 1):
            if self.waypoints[i]["s"] <= s_global <= self.waypoints[i + 1]["s"]:
                idx = i
                break

        w1 = self.waypoints[idx]
        w2 = self.waypoints[idx + 1]
        
        seg_len = max(1.0, w2["s"] - w1["s"])
        frac = (s_global - w1["s"]) / seg_len
        smooth_frac = 0.5 - 0.5 * math.cos(frac * math.pi)
        
        norm_x = w1["x"] + (w2["x"] - w1["x"]) * smooth_frac
        norm_y = w1["y"] + (w2["y"] - w1["y"]) * smooth_frac
        norm_z = w1["z"] + (w2["z"] - w1["z"]) * smooth_frac
        
        px = self.view_x + norm_x * self.view_w
        py = self.view_y + norm_y * self.view_h
        
        dx = (w2["x"] - w1["x"]) * self.view_w
        dy = (w2["y"] - w1["y"]) * self.view_h
        heading = math.atan2(dy, dx)
        
        depth_scale = 1.0 + (norm_z / 100.0) * 0.25
        depth_scale = np.clip(depth_scale, 0.75, 1.25)
        
        return px, py, heading, depth_scale

    def get_vehicle_screen_pos(self, vehicle) -> Tuple[float, float, float, float]:
        """
        Calculates screen coordinates for vehicle whether traveling on edge or queued at node.
        """
        loc = self.bridge.get_vehicle_location(vehicle)
        vx, vy, vw, vh = self.view_x, self.view_y, self.view_w, self.view_h

        if loc["type"] == "edge":
            return self.get_screen_pos_from_edge(loc["edge_id"], loc["pos_m"])
        elif loc["type"] == "node":
            node_id = loc["node_id"]
            q_idx = loc.get("queue_index", 0)
            if node_id == "CRUSHER":
                cx = vx + self.waypoints[5]["x"] * vw + q_idx * 34.0
                cy = vy + self.waypoints[5]["y"] * vh
                return cx, cy, math.pi, 0.95
            elif node_id == "SHOVEL":
                # Position queued trucks following the loop curve leading into Shovel
                cx = vx + (self.waypoints[0]["x"] - 0.02 - q_idx * 0.032) * vw
                cy = vy + (self.waypoints[0]["y"] + 0.04 + q_idx * 0.07) * vh
                return cx, cy, -math.pi / 2.8, 1.0
            elif node_id == "INTERSECTION":
                cx = vx + self.waypoints[2]["x"] * vw
                cy = vy + self.waypoints[2]["y"] * vh - 20.0
                return cx, cy, math.pi / 4.0, 1.0

        return vx + vw * 0.08, vy + vh * 0.32, 0.0, 1.0

    def init_ui_controls(self):
        """Creates interactive buttons, sliders, and controls."""
        self.buttons: List[UIElementButton] = []
        self.sliders: List[UIElementSlider] = []

        # -------------------------------------------------------------
        # Left Panel: Fog / Visibility Controls (x: 24, y: 404, w: 380, h: 220)
        # -------------------------------------------------------------
        self.slider_fog = UIElementSlider(
            rect=(44, 466, 340, 20),
            min_val=5.0,
            max_val=50.0,
            initial_val=self.bridge.current_visibility_m,
            label="Visibility Distance",
            unit="m",
            on_change=lambda v: self.bridge.set_visibility(v)
        )
        self.sliders.append(self.slider_fog)

        # Quick Preset Buttons
        self.buttons.append(UIElementButton((44, 530, 76, 28), "CLEAR 50m", lambda: self.set_fog_preset(50.0), bg_color=(20, 40, 30), text_color=COLOR_GREEN))
        self.buttons.append(UIElementButton((132, 530, 76, 28), "MOD 30m", lambda: self.set_fog_preset(30.0), bg_color=(24, 34, 44), text_color=COLOR_CYAN))
        self.buttons.append(UIElementButton((220, 530, 76, 28), "DENSE 15m", lambda: self.set_fog_preset(15.0), bg_color=(44, 36, 20), text_color=COLOR_AMBER))
        self.buttons.append(UIElementButton((308, 530, 76, 28), "EXT 5m", lambda: self.set_fog_preset(5.0), bg_color=(44, 20, 20), text_color=COLOR_RED))

        # -------------------------------------------------------------
        # Right Panel: Simulation & Speed Controls (x: 476, y: 636, w: 386, h: 184)
        # -------------------------------------------------------------
        # Start / Pause Toggle
        self.btn_start_pause = UIElementButton((492, 672, 78, 30), "START", self.toggle_start_pause, bg_color=(20, 60, 35), text_color=COLOR_GREEN)
        self.buttons.append(self.btn_start_pause)

        # Step 1s Button
        self.buttons.append(UIElementButton((576, 672, 78, 30), "STEP (1s)", self.step_single, bg_color=(28, 38, 48), text_color=COLOR_TEXT_PRIMARY))
        
        # Reset Button
        self.buttons.append(UIElementButton((660, 672, 78, 30), "RESET", self.reset_sim, bg_color=(40, 32, 28), text_color=COLOR_AMBER))

        # Emergency Stop Button
        self.btn_estop = UIElementButton((744, 672, 94, 30), "E-STOP", self.toggle_estop, bg_color=(60, 20, 20), text_color=COLOR_RED)
        self.buttons.append(self.btn_estop)

        # Commanded Speed Slider (0 to 50 km/h)
        self.slider_speed = UIElementSlider(
            rect=(492, 734, 354, 16),
            min_val=0.0,
            max_val=50.0,
            initial_val=self.bridge.target_speed_kmh,
            label="Commanded Speed Target",
            unit="km/h",
            on_change=lambda v: self.bridge.set_target_speed(v)
        )
        self.sliders.append(self.slider_speed)

        # Speed Multiplier Buttons (1x, 2x, 5x, 10x, 20x)
        self.buttons.append(UIElementButton((590, 762, 44, 22), "1x", lambda: self.set_speed_mult(1), bg_color=(24, 30, 38)))
        self.buttons.append(UIElementButton((638, 762, 44, 22), "2x", lambda: self.set_speed_mult(2), bg_color=(24, 30, 38)))
        self.buttons.append(UIElementButton((686, 762, 44, 22), "5x", lambda: self.set_speed_mult(5), bg_color=(24, 30, 38)))
        self.buttons.append(UIElementButton((734, 762, 50, 22), "10x", lambda: self.set_speed_mult(10), bg_color=(24, 30, 38)))
        self.buttons.append(UIElementButton((788, 762, 50, 22), "20x", lambda: self.set_speed_mult(20), bg_color=(24, 30, 38)))

    # Control Callbacks
    def toggle_start_pause(self):
        self.bridge.running = not self.bridge.running
        self.btn_start_pause.text = "PAUSE" if self.bridge.running else "START"
        self.btn_start_pause.bg_color = (40, 30, 20) if self.bridge.running else (20, 60, 35)
        self.btn_start_pause.text_color = COLOR_AMBER if self.bridge.running else COLOR_GREEN

    def step_single(self):
        self.bridge.running = False
        self.btn_start_pause.text = "START"
        self.btn_start_pause.bg_color = (20, 60, 35)
        self.btn_start_pause.text_color = COLOR_GREEN
        self.bridge.step()

    def reset_sim(self):
        self.bridge.reset()
        self.slider_fog.val = self.bridge.current_visibility_m
        self.slider_speed.val = self.bridge.target_speed_kmh
        self.btn_start_pause.text = "START"
        self.btn_start_pause.bg_color = (20, 60, 35)
        self.btn_start_pause.text_color = COLOR_GREEN
        self.btn_estop.text = "E-STOP"
        self.btn_estop.bg_color = (60, 20, 20)

    def toggle_estop(self):
        if not self.bridge.e_stop_active:
            self.bridge.trigger_emergency_stop()
            self.btn_estop.text = "RESUME"
            self.btn_estop.bg_color = (80, 20, 20)
        else:
            self.bridge.release_emergency_stop()
            self.slider_speed.val = self.bridge.target_speed_kmh
            self.btn_estop.text = "E-STOP"
            self.btn_estop.bg_color = (60, 20, 20)

    def set_fog_preset(self, vis_m: float):
        self.bridge.set_visibility(vis_m)
        self.slider_fog.val = vis_m

    def set_speed_mult(self, mult: int):
        self.bridge.speed_multiplier = mult

    # Event Handling
    def handle_input(self):
        """Processes user input events and keyboard shortcuts."""
        mouse_pos = self.pygame.mouse.get_pos()
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                return False

            # Sliders
            handled_by_slider = False
            for slider in self.sliders:
                if slider.handle_event(event, mouse_pos):
                    handled_by_slider = True

            # Buttons
            if not handled_by_slider:
                for btn in self.buttons:
                    btn.handle_event(event, mouse_pos)

            # Mouse click on Fleet Telemetry rows or Viewport trucks to select active truck
            if event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Check click on Fleet Telemetry rows (x: 416, y: 404, w: 446, h: 220)
                fx, fy, fw = 416, 404, 446
                if fx + 6 <= mouse_pos[0] <= fx + fw - 6 and fy + 51 <= mouse_pos[1] <= fy + 51 + 4 * 36:
                    row_idx = (mouse_pos[1] - (fy + 51)) // 36
                    if 0 <= row_idx < len(self.bridge.sim.vehicles):
                        self.bridge.selected_truck_id = self.bridge.sim.vehicles[row_idx].id

                # 2. Check click near a truck in 2.5D Viewport
                for v in self.bridge.sim.vehicles:
                    tx, ty, _, _ = self.get_vehicle_screen_pos(v)
                    if math.hypot(mouse_pos[0] - tx, mouse_pos[1] - ty) <= 28:
                        self.bridge.selected_truck_id = v.id
                        break

            # Keyboard Shortcuts
            if event.type == self.pygame.KEYDOWN:
                if event.key == self.pygame.K_ESCAPE:
                    return False
                elif event.key == self.pygame.K_SPACE:
                    self.toggle_start_pause()
                elif event.key == self.pygame.K_s:
                    self.step_single()
                elif event.key == self.pygame.K_r:
                    self.reset_sim()
                elif event.key == self.pygame.K_e:
                    self.toggle_estop()
                elif event.key == self.pygame.K_1:
                    self.set_fog_preset(50.0)
                elif event.key == self.pygame.K_2:
                    self.set_fog_preset(30.0)
                elif event.key == self.pygame.K_3:
                    self.set_fog_preset(15.0)
                elif event.key == self.pygame.K_4:
                    self.set_fog_preset(5.0)
                elif event.key == self.pygame.K_UP:
                    new_sp = min(50.0, self.bridge.target_speed_kmh + 2.0)
                    self.bridge.set_target_speed(new_sp)
                    self.slider_speed.val = new_sp
                elif event.key == self.pygame.K_DOWN:
                    new_sp = max(0.0, self.bridge.target_speed_kmh - 2.0)
                    self.bridge.set_target_speed(new_sp)
                    self.slider_speed.val = new_sp

        return True

    # ==============================================================================
    # Drawing & Rendering Methods
    # ==============================================================================

    def render(self):
        """Renders complete UI frame."""
        pygame = self.pygame
        self.screen.fill(COLOR_BG)

        # 1. Top Header Banner
        self.draw_header()

        # 2. Main 2.5D Simulation Viewport
        self.draw_simulation_viewport()

        # 3. Middle 4 Informational Panels
        self.draw_fog_control_panel()
        self.draw_fleet_telemetry_panel()
        self.draw_road_environment_panel()
        self.draw_simulation_control_panel()

        # 4. Bottom Real-time Telemetry Speed Graph
        self.draw_speed_graph()

        # 5. P9 - canonical Twin, read-only and clearly separated from the simulator.
        self.draw_canonical_twin_panel()

        if not self.headless:
            pygame.display.flip()

    def draw_header(self):
        """Draws top title bar and global status clock."""
        pygame = self.pygame
        pygame.draw.rect(self.screen, COLOR_HEADER_BG, (0, 0, self.width, 54))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, 54), (self.width, 54), 1)

        # Brand / Title
        title_surf = self.font_title.render("FOG-ORCHESTRATOR 2.0", True, COLOR_CYAN)
        sub_surf = self.font_body.render("Mine Haulage Digital Twin & Fog Safety Governor", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(title_surf, (24, 10))
        self.screen.blit(sub_surf, (270, 14))

        # Simulation Time & Status Callouts
        tel = self.bridge.get_telemetry()
        t_sec = int(tel["timestamp"])
        time_str = f"SIM TIME: {t_sec // 60:02d}:{t_sec % 60:02d} ({t_sec}s)"
        time_surf = self.font_digits_med.render(time_str, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(time_surf, (self.width - 430, 14))

        # Mode Badge
        mode_str = "RUNNING" if tel["running"] else "PAUSED"
        mode_col = COLOR_GREEN if tel["running"] else COLOR_AMBER
        if tel["e_stop"]:
            mode_str = "EMERGENCY STOP"
            mode_col = COLOR_RED
            
        pygame.draw.rect(self.screen, (mode_col[0] // 5, mode_col[1] // 5, mode_col[2] // 5), (self.width - 170, 10, 146, 32), border_radius=6)
        pygame.draw.rect(self.screen, mode_col, (self.width - 170, 10, 146, 32), 1, border_radius=6)
        mode_lbl = self.font_bold.render(mode_str, True, mode_col)
        self.screen.blit(mode_lbl, (self.width - 170 + (146 - mode_lbl.get_width()) // 2, 18))

    def draw_simulation_viewport(self):
        """
        Renders the 2.5D open-pit mine haul road scene:
        - Pit floor, highwall benches, and crusher basin terrain
        - Road segments with elevation drop / climb indicators
        - Gradient callout flags (-8% Downhill, +4% Uphill, Flat)
        - Mining Haul Truck (wheels, dump bed with ore, headlights)
        - Volumetric Fog Overlay based on current visibility distance
        """
        pygame = self.pygame
        vx, vy, vw, vh = self.view_x, self.view_y, self.view_w, self.view_h

        # Viewport Frame
        pygame.draw.rect(self.screen, COLOR_MINE_GROUND, (vx, vy, vw, vh), border_radius=8)

        # 1. Background Mine Bench Terraces / Highwalls
        for bench_y, col in [(vy + 40, (38, 32, 26)), (vy + 100, (44, 38, 30)), (vy + 200, (34, 28, 22))]:
            pygame.draw.line(self.screen, col, (vx + 10, bench_y), (vx + vw - 10, bench_y), 2)
            # Hatchings
            for hx in range(vx + 30, vx + vw - 30, 45):
                pygame.draw.line(self.screen, col, (hx, bench_y), (hx - 15, bench_y + 12), 1)

        # 2. Road Circuit Polygon Strip
        road_pts = []
        for w in self.waypoints:
            px = vx + w["x"] * vw
            py = vy + w["y"] * vh
            road_pts.append((px, py))

        # Draw Outer Berm / Shoulder
        pygame.draw.lines(self.screen, COLOR_BERM, False, road_pts, 34)
        # Draw Road Edge
        pygame.draw.lines(self.screen, COLOR_ROAD_EDGE, False, road_pts, 28)
        # Draw Asphalt / Gravel Road Surface
        pygame.draw.lines(self.screen, COLOR_ROAD_SURFACE, False, road_pts, 22)
        # Draw Centerline Dashes
        pygame.draw.lines(self.screen, COLOR_ROAD_LINE, False, road_pts, 2)

        # 3. Facility Landmarks & Live Queuing Overlays
        # Shovel Loading Facility (Left)
        sh_pos = (vx + self.waypoints[0]["x"] * vw, vy + self.waypoints[0]["y"] * vh)
        pygame.draw.circle(self.screen, (70, 55, 35), (int(sh_pos[0]), int(sh_pos[1])), 22)
        pygame.draw.circle(self.screen, COLOR_AMBER, (int(sh_pos[0]), int(sh_pos[1])), 14)
        
        tel = self.bridge.get_telemetry()
        if tel["shovel_queue_len"] > 0:
            sh_lbl = self.font_bold.render(f"SHOVEL: LOADING ({tel['shovel_service_rem_s']:.0f}s)", True, COLOR_AMBER)
        else:
            sh_lbl = self.font_bold.render("SHOVEL (0%)", True, COLOR_AMBER)
        self.screen.blit(sh_lbl, (sh_pos[0] - 25, sh_pos[1] - 46))

        # Crusher Unloading Facility (Bottom Basin)
        cr_pos = (vx + self.waypoints[5]["x"] * vw, vy + self.waypoints[5]["y"] * vh)
        pygame.draw.circle(self.screen, (50, 60, 70), (int(cr_pos[0]), int(cr_pos[1])), 24)
        pygame.draw.rect(self.screen, COLOR_CYAN, (int(cr_pos[0]) - 12, int(cr_pos[1]) - 12, 24, 24), border_radius=4)
        
        if tel["crusher_queue_len"] > 0:
            cr_lbl = self.font_bold.render(f"CRUSHER: UNLOADING ({tel['crusher_service_rem_s']:.0f}s left)", True, COLOR_CYAN)
        else:
            cr_lbl = self.font_bold.render("CRUSHER BASIN (-32m)", True, COLOR_CYAN)
        self.screen.blit(cr_lbl, (cr_pos[0] - 80, cr_pos[1] + 18))

        # Intersection / Switchback Entry
        it_pos = (vx + self.waypoints[2]["x"] * vw, vy + self.waypoints[2]["y"] * vh)
        pygame.draw.circle(self.screen, (60, 70, 80), (int(it_pos[0]), int(it_pos[1])), 10)

        # Gradient Signposts
        # Downhill Sign on ROAD_2
        r2_mid = (vx + self.waypoints[3]["x"] * vw, vy + self.waypoints[3]["y"] * vh)
        pygame.draw.rect(self.screen, (40, 20, 20), (int(r2_mid[0]) - 55, int(r2_mid[1]) - 32, 110, 22), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_RED, (int(r2_mid[0]) - 55, int(r2_mid[1]) - 32, 110, 22), 1, border_radius=4)
        r2_lbl = self.font_small.render("▼ GRADE -8.0% (R=50m)", True, COLOR_RED)
        self.screen.blit(r2_lbl, (r2_mid[0] - 50, r2_mid[1] - 28))

        # Uphill Sign on ROAD_RETURN
        ret_mid = (vx + self.waypoints[7]["x"] * vw, vy + self.waypoints[7]["y"] * vh)
        pygame.draw.rect(self.screen, (20, 35, 25), (int(ret_mid[0]) - 45, int(ret_mid[1]) + 16, 96, 22), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_GREEN, (int(ret_mid[0]) - 45, int(ret_mid[1]) + 16, 96, 22), 1, border_radius=4)
        ret_lbl = self.font_small.render("▲ GRADE +4.0%", True, COLOR_GREEN)
        self.screen.blit(ret_lbl, (ret_mid[0] - 40, ret_mid[1] + 20))

        # Flat Sign on ROAD_1
        r1_mid = (vx + self.waypoints[1]["x"] * vw, vy + self.waypoints[1]["y"] * vh)
        r1_lbl = self.font_small.render("ROAD_1 (Flat 0% Grade, 500m)", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(r1_lbl, (r1_mid[0] - 60, r1_mid[1] - 26))

        # 4. Render All Fleet Trucks (Edge Traveling & Node Queuing)
        for v in self.bridge.sim.vehicles:
            tx, ty, th, sc = self.get_vehicle_screen_pos(v)
            is_selected = (v.id == self.bridge.selected_truck_id)
            self.draw_haul_truck(tx, ty, th, sc, v, is_selected)

        # 5. Volumetric Atmospheric Fog Overlay
        self.draw_fog_effect(vx, vy, vw, vh)

        # Viewport Outer Border
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (vx, vy, vw, vh), 1, border_radius=8)

    def draw_haul_truck(self, cx: float, cy: float, heading: float, scale: float, vehicle, is_selected: bool):
        """
        Draws a realistic heavy mining haul truck (CAT 797 / Komatsu 930E style):
        - Heavy dump bed / payload box (filled with ore rocks if loaded)
        - Operator cab on left front with safety glass
        - 4 giant heavy-duty tires
        - Front headlights casting visible light beams
        - Brake lights glowing when decelerating
        - Telemetry tag badge
        """
        pygame = self.pygame
        
        # Dimensions scaled by perspective depth
        w = 34 * scale
        h = 20 * scale

        # Headlight Beam Cones (projected in front of truck)
        beam_len = 50 * scale * (self.bridge.current_visibility_m / 50.0)
        beam_spread = 22 * scale
        h_cos = math.cos(heading)
        h_sin = math.sin(heading)

        front_x = cx + h_cos * (w * 0.6)
        front_y = cy + h_sin * (w * 0.6)

        # Draw semi-transparent headlight cone
        cone_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        p1 = (front_x, front_y)
        p2 = (front_x + h_cos * beam_len - h_sin * beam_spread, front_y + h_sin * beam_len + h_cos * beam_spread)
        p3 = (front_x + h_cos * beam_len + h_sin * beam_spread, front_y + h_sin * beam_len - h_cos * beam_spread)
        pygame.draw.polygon(cone_surf, (255, 245, 180, 50), [p1, p2, p3])
        self.screen.blit(cone_surf, (0, 0))

        # Truck Body Surface (Rotated)
        truck_surf = pygame.Surface((int(w * 1.8), int(h * 1.8)), pygame.SRCALPHA)
        tcx = int(w * 0.9)
        tcy = int(h * 0.9)

        # 4 Heavy Off-road Tires
        tire_w = 12 * scale
        tire_h = 6 * scale
        # Front tires
        pygame.draw.rect(truck_surf, (15, 15, 18), (tcx + w*0.15, tcy - h*0.58, tire_w, tire_h), border_radius=2)
        pygame.draw.rect(truck_surf, (15, 15, 18), (tcx + w*0.15, tcy + h*0.28, tire_w, tire_h), border_radius=2)
        # Dual Rear tires
        pygame.draw.rect(truck_surf, (15, 15, 18), (tcx - w*0.45, tcy - h*0.58, tire_w, tire_h), border_radius=2)
        pygame.draw.rect(truck_surf, (15, 15, 18), (tcx - w*0.45, tcy + h*0.28, tire_w, tire_h), border_radius=2)

        # Main Heavy Dump Bed Body
        body_col = (245, 175, 35) if is_selected else (200, 150, 40)
        pygame.draw.rect(truck_surf, body_col, (tcx - w*0.4, tcy - h*0.45, w*0.75, h*0.9), border_radius=3)
        pygame.draw.rect(truck_surf, (40, 40, 45), (tcx - w*0.4, tcy - h*0.45, w*0.75, h*0.9), 1, border_radius=3)

        # Payload Bed Interior (Ore Rocks if loaded)
        if vehicle.is_loaded:
            pygame.draw.rect(truck_surf, COLOR_ORE_ROCK, (tcx - w*0.35, tcy - h*0.35, w*0.55, h*0.7), border_radius=2)
            # Rock texture spots
            for rox, roy in [(tcx - w*0.2, tcy - h*0.1), (tcx - w*0.05, tcy + h*0.1), (tcx - w*0.25, tcy + h*0.15)]:
                pygame.draw.circle(truck_surf, (130, 80, 30), (int(rox), int(roy)), int(3 * scale))
        else:
            pygame.draw.rect(truck_surf, (60, 60, 65), (tcx - w*0.35, tcy - h*0.35, w*0.55, h*0.7), border_radius=2)

        # Operator Cabin (Front Left)
        pygame.draw.rect(truck_surf, (240, 240, 245), (tcx + w*0.1, tcy - h*0.42, w*0.25, h*0.45), border_radius=2)
        # Cab Window Glass
        pygame.draw.rect(truck_surf, (40, 140, 200), (tcx + w*0.14, tcy - h*0.38, w*0.18, h*0.35), border_radius=1)

        # Headlights & Tail lights
        pygame.draw.circle(truck_surf, (255, 255, 200), (int(tcx + w*0.35), int(tcy - h*0.3)), int(2 * scale))
        pygame.draw.circle(truck_surf, (255, 255, 200), (int(tcx + w*0.35), int(tcy + h*0.3)), int(2 * scale))
        
        # Tail lights (Red)
        tail_col = (255, 40, 40) if vehicle.acceleration_mps2 < -0.1 else (150, 30, 30)
        pygame.draw.circle(truck_surf, tail_col, (int(tcx - w*0.4), int(tcy - h*0.35)), int(2 * scale))
        pygame.draw.circle(truck_surf, tail_col, (int(tcx - w*0.4), int(tcy + h*0.35)), int(2 * scale))

        # Rotate and Blit to Screen
        angle_deg = -math.degrees(heading)
        rotated_surf = pygame.transform.rotate(truck_surf, angle_deg)
        rx = cx - rotated_surf.get_width() // 2
        ry = cy - rotated_surf.get_height() // 2
        self.screen.blit(rotated_surf, (rx, ry))

        # Tag Badge above vehicle
        is_fol_stop = getattr(vehicle, "is_following_stopped", False)
        tag_bg_col = (45, 28, 12, 230) if is_fol_stop else (15, 23, 42, 220)
        badge_w = 126 if is_fol_stop else 112
        badge_h = 22
        bx = int(cx - badge_w // 2)
        by = int(cy - 28 * scale - badge_h)
        
        tag_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        pygame.draw.rect(tag_surf, tag_bg_col, (0, 0, badge_w, badge_h), border_radius=4)
        border_col = COLOR_AMBER if is_fol_stop else (COLOR_CYAN if is_selected else COLOR_PANEL_BORDER)
        pygame.draw.rect(tag_surf, border_col, (0, 0, badge_w, badge_h), 1, border_radius=4)
        
        if is_fol_stop:
            lbl_id = self.font_small.render(f"{vehicle.id} FOLLOWING STOP", True, COLOR_AMBER)
        else:
            lbl_id = self.font_small.render(f"{vehicle.id} {vehicle.speed_mps*3.6:.0f}km/h", True, COLOR_TEXT_PRIMARY)
        tag_surf.blit(lbl_id, (6, 4))
        self.screen.blit(tag_surf, (bx, by))

    def draw_fog_effect(self, vx: int, vy: int, vw: int, vh: int):
        """
        Draws dynamic volumetric atmospheric fog over the simulation viewport.
        When visibility drops from 50m to 5m, the opacity and mist depth increase smoothly.
        Uses soft multi-layer depth blending for a realistic atmospheric haze effect.
        """
        pygame = self.pygame
        vis = self.bridge.current_visibility_m
        
        # Calculate alpha density (0 at 50m clear, up to ~220 at 5m extreme fog)
        fog_factor = np.clip(1.0 - (vis - 5.0) / 45.0, 0.0, 1.0)
        alpha_base = int(12 + fog_factor * 190)

        fog_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
        
        # Smooth vertical elevation gradient: distant mine highwall benches have denser mist
        haze_top = min(245, int(alpha_base * 1.35))
        haze_bot = int(alpha_base * 0.70)
        
        strips = 32
        strip_h = vh / float(strips)
        for i in range(strips):
            fr = i / float(strips)
            a = int(haze_top + fr * (haze_bot - haze_top))
            pygame.draw.rect(fog_surf, (175, 190, 202, a), (0, int(i * strip_h), vw, int(strip_h) + 1))

        # In dense/extreme fog, add soft horizontal drifting mist bands with smooth alpha
        if vis <= 30.0:
            mist_alpha = int(fog_factor * 35)
            for band_y, band_h in [(int(vh * 0.2), int(vh * 0.25)), (int(vh * 0.55), int(vh * 0.3))]:
                pygame.draw.rect(fog_surf, (200, 215, 225, mist_alpha), (0, band_y, vw, band_h))

        self.screen.blit(fog_surf, (vx, vy))

        # Visibility Watermark in Viewport Corner
        vis_tag = f"ATMOSPHERIC VISIBILITY: {vis:.1f} m"
        vis_surf = self.font_bold.render(vis_tag, True, (255, 255, 255) if vis > 20 else COLOR_AMBER)
        tag_w = vis_surf.get_width() + 16
        tag_bg = pygame.Surface((tag_w, 24), pygame.SRCALPHA)
        tag_bg.fill((10, 14, 20, 210))
        pygame.draw.rect(tag_bg, COLOR_PANEL_BORDER, (0, 0, tag_w, 24), 1, border_radius=4)
        self.screen.blit(tag_bg, (vx + 14, vy + 14))
        self.screen.blit(vis_surf, (vx + 22, vy + 18))

    # ==============================================================================
    # Middle 4 Control & Telemetry Panels
    # ==============================================================================

    def draw_fog_control_panel(self):
        """Panel 1: Fog / Visibility Slider and Presets."""
        pygame = self.pygame
        x, y, w, h = 24, 404, 380, 220
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        # Header
        hdr = self.font_section.render("FOG / VISIBILITY CONTROL", True, COLOR_CYAN)
        self.screen.blit(hdr, (x + 16, y + 14))

        # Visibility Readout Value
        vis = self.bridge.current_visibility_m
        v_str = f"{vis:.1f} m"
        v_lbl = self.font_digits_large.render(v_str, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(v_lbl, (x + 16, y + 36))

        # State descriptor
        if vis >= 40.0:
            cond_str = "CLEAR (Optimal Traction)"
            cond_col = COLOR_GREEN
        elif vis >= 25.0:
            cond_str = "MODERATE FOG (Damp Road)"
            cond_col = COLOR_CYAN
        elif vis >= 12.0:
            cond_str = "DENSE FOG (Wet Road, Low Vis)"
            cond_col = COLOR_AMBER
        else:
            cond_str = "EXTREME FOG (Saturated, Critical)"
            cond_col = COLOR_RED

        cond_surf = self.font_bold.render(cond_str, True, cond_col)
        self.screen.blit(cond_surf, (x + 140, y + 42))

        # Draw Slider
        self.slider_fog.draw(self.screen, self.font_body, self.font_bold)

        # Slider Range Labels
        self.screen.blit(self.font_small.render("5m (Extreme)", True, COLOR_TEXT_MUTED), (x + 20, y + 86))
        self.screen.blit(self.font_small.render("50m (Clear)", True, COLOR_TEXT_MUTED), (x + w - 75, y + 86))

        # Quick Preset Buttons Section Label
        ps_lbl = self.font_small.render("QUICK PRESETS (Keys 1-4):", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(ps_lbl, (x + 20, y + 110))

        # Draw Preset Buttons
        for btn in self.buttons[:4]:
            btn.draw(self.screen, self.font_bold)

        # Backend Model Synced Note
        note = self.font_small.render("● Reading canonical Twin state (fog, friction, v_safe)", True, COLOR_TEXT_MUTED)
        self.screen.blit(note, (x + 20, y + 194))

    def draw_fleet_telemetry_panel(self):
        """Panel 2: Segregated Live Fleet Telemetry with Live Speed, v_safe, Commanded Speed, Gap and Status."""
        pygame = self.pygame
        x, y, w, h = 416, 404, 446, 220
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        tel = self.bridge.get_telemetry()
        fleet = tel.get("fleet", [])

        # Panel Header
        hdr = self.font_section.render("FLEET TELEMETRY & LOCAL GOVERNOR", True, COLOR_CYAN)
        self.screen.blit(hdr, (x + 12, y + 10))

        # Overall Status Badge / Global Callout on Top-Right
        if tel["e_stop"]:
            top_badge_text = "● E-STOP"
            top_badge_col = COLOR_RED
        elif any(trk["status_label"] == "UNSAFE" for trk in fleet):
            top_badge_text = "● UNSAFE LIMIT"
            top_badge_col = COLOR_RED
        elif any(trk["status_label"] == "FOLLOWING" for trk in fleet):
            top_badge_text = "● SAFE GAP ACTIVE"
            top_badge_col = COLOR_AMBER
        else:
            top_badge_text = "● 4 UNITS ACTIVE"
            top_badge_col = COLOR_GREEN

        top_tag = self.font_small.render(top_badge_text, True, top_badge_col)
        self.screen.blit(top_tag, (x + w - top_tag.get_width() - 14, y + 12))

        # Table Column Headers
        col_y = y + 32
        cols = [
            ("TRUCK", 10),
            ("SPEED", 82),
            ("V_SAFE", 144),
            ("CMD", 198),
            ("LOC", 248),
            ("GAP", 310),
            ("STATUS", 362)
        ]
        for col_name, col_offset in cols:
            self.screen.blit(self.font_small.render(col_name, True, COLOR_TEXT_MUTED), (x + col_offset, col_y))

        # Divider line under column headers
        pygame.draw.line(self.screen, (36, 42, 52), (x + 8, col_y + 16), (x + w - 8, col_y + 16), 1)

        # Render 4 Truck Rows (36px height each)
        for i, truck in enumerate(fleet[:4]):
            ry = y + 51 + i * 36
            is_sel = truck.get("is_selected", False)

            # Row Background Strip
            if is_sel:
                pygame.draw.rect(self.screen, (24, 38, 55), (x + 6, ry, w - 12, 33), border_radius=4)
                pygame.draw.rect(self.screen, (0, 180, 216, 180), (x + 6, ry, w - 12, 33), 1, border_radius=4)
            else:
                bg_col = (19, 24, 32) if i % 2 == 0 else (15, 19, 25)
                pygame.draw.rect(self.screen, bg_col, (x + 6, ry, w - 12, 33), border_radius=4)

            # Col 0: TRUCK ID
            truck_name_col = COLOR_CYAN if is_sel else COLOR_TEXT_PRIMARY
            t_lbl = self.font_bold.render(truck["id"], True, truck_name_col)
            self.screen.blit(t_lbl, (x + 10, ry + 8))

            # Col 1: SPEED
            spd_val = self.font_digits_med.render(f"{truck['speed_kmh']:4.1f}", True, COLOR_TEXT_PRIMARY)
            self.screen.blit(spd_val, (x + 78, ry + 6))
            self.screen.blit(self.font_small.render("kph", True, COLOR_TEXT_MUTED), (x + 118, ry + 9))

            # Col 2: V_SAFE
            safe_val = self.font_digits_med.render(fmt_value(truck["v_safe_kmh"]), True, COLOR_AMBER)
            self.screen.blit(safe_val, (x + 142, ry + 6))

            # Col 3: COMMAND
            cmd_val = self.font_digits_med.render(f"{truck['v_command_kmh']:4.1f}", True, COLOR_GREEN if truck['v_command_kmh'] > 0 else (220, 70, 70))
            self.screen.blit(cmd_val, (x + 196, ry + 6))

            # Col 4: LOCATION (Short badge)
            loc_str = truck["location_id"]
            if loc_str == "ROAD_RETURN":
                loc_str = "RETURN"
            elif loc_str == "INTERSECTION":
                loc_str = "INTER"
            loc_lbl = self.font_small.render(loc_str, True, COLOR_TEXT_SECONDARY)
            self.screen.blit(loc_lbl, (x + 248, ry + 9))

            # Col 5: GAP
            lead_id = truck.get("lead_vehicle_id")
            gap_m = truck.get("lead_gap_m", float('inf'))
            if lead_id and not math.isinf(gap_m):
                gap_str = f"{gap_m:.1f}m"
                gap_col = COLOR_AMBER if truck.get("is_following_stopped") else COLOR_TEXT_PRIMARY
            else:
                gap_str = "--"
                gap_col = COLOR_TEXT_MUTED
            gap_lbl = self.font_small.render(gap_str, True, gap_col)
            self.screen.blit(gap_lbl, (x + 310, ry + 9))

            # Col 6: STATUS BADGE PILL
            st_lbl_text = truck["status_label"]
            st_col = truck["status_color"]
            pill_w = 74
            pill_h = 22
            pill_x = x + 362
            pill_y = ry + 5
            
            # Pill Background & Border
            pygame.draw.rect(self.screen, (st_col[0] // 5, st_col[1] // 5, st_col[2] // 5), (pill_x, pill_y, pill_w, pill_h), border_radius=4)
            pygame.draw.rect(self.screen, st_col, (pill_x, pill_y, pill_w, pill_h), 1, border_radius=4)
            
            st_text_surf = self.font_small.render(st_lbl_text, True, st_col)
            st_tx = pill_x + (pill_w - st_text_surf.get_width()) // 2
            st_ty = pill_y + (pill_h - st_text_surf.get_height()) // 2
            self.screen.blit(st_text_surf, (st_tx, st_ty))

        # Bottom Sub-status Bar
        gov_str = "● Local Safety Governor: ACTIVE (Authoritative Physics Enforced across Fleet)"
        gov_surf = self.font_small.render(gov_str, True, COLOR_GREEN if not tel["e_stop"] else COLOR_RED)
        self.screen.blit(gov_surf, (x + 14, y + 198))

    def draw_truck_status_panel(self):
        """Legacy compatibility alias for draw_fleet_telemetry_panel."""
        return self.draw_fleet_telemetry_panel()

    def draw_road_environment_panel(self):
        """Panel 3: Road & Environment Information (Grade, Friction, Surface)."""
        pygame = self.pygame
        x, y, w, h = 24, 636, 440, 184
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        tel = self.bridge.get_telemetry()

        # Header
        hdr = self.font_section.render("ROAD & ENVIRONMENT CONDITIONS", True, COLOR_CYAN)
        self.screen.blit(hdr, (x + 16, y + 12))

        # Safe headway formatted with gap if lead vehicle present
        if tel.get("lead_vehicle_id"):
            hw_str = f"{tel['safe_headway_m']:.1f}m (Gap: {tel['lead_gap_m']:.1f}m)"
        else:
            hw_str = f"{tel['safe_headway_m']:.1f} m"

        # Key-Value Grid
        items_left = [
            ("Segment / Node:", f"{tel['current_edge']}"),
            ("Gradient:", f"{tel['grade_percent']:+.1f} % ({'Downhill' if tel['grade_percent'] < 0 else ('Uphill' if tel['grade_percent'] > 0 else 'Flat')})"),
            # A vehicle at a NODE is not on a road, so no friction or surface state is
            # known for it (see get_telemetry: "nothing is known about this road").
            # Both arrive as None and must render as UNAVAILABLE - never as an assumed
            # 0.60 / "dry", which would tell the operator the road is gripping when
            # nothing has been observed.
            ("Friction (μ):", fmt_value(tel["friction_mu"], ".2f")),
            ("Surface State:",
             tel["surface_state"].upper() if tel["surface_state"] else UNAVAILABLE_TEXT),
        ]

        items_right = [
            ("Stopping Margin:", f"{tel['stop_envelope_m']:.1f} m"),
            ("Safe Headway:", hw_str),
            ("Truck Progress:", f"{tel['position_m']:.0f} / {tel['road_length_m']:.0f} m ({tel['progress_pct']:.0f}%)" if tel['road_length_m'] > 0 else f"{tel['truck_state'].upper()}"),
            ("Payload Mass:", f"{tel['mass_kg']/1000.0:.0f} tonnes ({'LOADED' if tel['is_loaded'] else 'EMPTY'})")
        ]

        # Render Left Column
        ly = y + 36
        for lbl, val in items_left:
            self.screen.blit(self.font_body.render(lbl, True, COLOR_TEXT_SECONDARY), (x + 16, ly))
            # UNAVAILABLE is dimmed, not alarmed. The sign-based rule below reads the "-"
            # in the marker as negative and would colour an unknown value like a warning;
            # "not measured" is not the same as "bad".
            if val == UNAVAILABLE_TEXT:
                col = COLOR_TEXT_SECONDARY
            else:
                col = COLOR_RED if "-" in val else (COLOR_GREEN if "+" in val else COLOR_TEXT_PRIMARY)
            self.screen.blit(self.font_bold.render(val, True, col), (x + 130, ly))
            ly += 24

        # Render Right Column
        ry = y + 36
        for lbl, val in items_right:
            self.screen.blit(self.font_body.render(lbl, True, COLOR_TEXT_SECONDARY), (x + 236, ry))
            self.screen.blit(self.font_bold.render(val, True, COLOR_TEXT_PRIMARY), (x + 342, ry))
            ry += 24

        # Progress bar of current segment or queue
        p_bar_y = y + 144
        pygame.draw.rect(self.screen, (30, 36, 44), (x + 16, p_bar_y, w - 32, 10), border_radius=4)
        prog_w = int((w - 32) * (tel["progress_pct"] / 100.0))
        if prog_w > 0:
            pygame.draw.rect(self.screen, COLOR_CYAN, (x + 16, p_bar_y, prog_w, 10), border_radius=4)

        # Progress text
        p_txt = self.font_small.render(f"Haul Cycle Progress: {tel['location_label'].upper()}", True, COLOR_TEXT_MUTED)
        self.screen.blit(p_txt, (x + 16, y + 160))

    def draw_simulation_control_panel(self):
        """Panel 4: Simulation Execution & Commanded Speed Controls."""
        pygame = self.pygame
        x, y, w, h = 476, 636, 386, 184
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        # Header
        hdr = self.font_section.render("SIMULATION & SPEED CONTROLS", True, COLOR_CYAN)
        self.screen.blit(hdr, (x + 16, y + 12))

        # Simulation Action Buttons (Start, Pause, Step, Reset, E-Stop)
        btn_start = self.buttons[4]
        btn_start.rect = (x + 16, y + 36, 78, 30)
        btn_start.draw(self.screen, self.font_bold)

        btn_step = self.buttons[5]
        btn_step.rect = (x + 100, y + 36, 78, 30)
        btn_step.draw(self.screen, self.font_bold)

        btn_reset = self.buttons[6]
        btn_reset.rect = (x + 184, y + 36, 78, 30)
        btn_reset.draw(self.screen, self.font_bold)

        btn_estop = self.buttons[7]
        btn_estop.rect = (x + 268, y + 36, 94, 30)
        btn_estop.draw(self.screen, self.font_bold)

        # Commanded Speed Slider Label & Readout
        sp_lbl = self.font_small.render("COMMANDED SPEED TARGET (Keys Up/Down):", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(sp_lbl, (x + 16, y + 78))
        
        target_str = f"{self.bridge.target_speed_kmh:.1f} km/h"
        target_surf = self.font_digits_med.render(target_str, True, COLOR_CYAN)
        self.screen.blit(target_surf, (x + w - 100, y + 74))

        # Commanded Speed Slider
        self.slider_speed.rect = (x + 16, y + 98, w - 32, 16)
        self.slider_speed.draw(self.screen, self.font_body, self.font_bold)

        # Speed Multiplier Buttons Label
        self.screen.blit(self.font_small.render("TIME WARP:", True, COLOR_TEXT_SECONDARY), (x + 16, y + 128))
        
        # Multipliers (1x, 2x, 5x, 10x, 20x)
        mult_configs = [("1x", 1, 44), ("2x", 2, 44), ("5x", 5, 44), ("10x", 10, 50), ("20x", 20, 50)]
        bx_cur = x + 95
        for idx, (mlbl, mult, bw) in enumerate(mult_configs):
            btn_m = self.buttons[8 + idx]
            btn_m.rect = (bx_cur, y + 122, bw, 24)
            is_active = (self.bridge.speed_multiplier == mult)
            btn_m.bg_color = (20, 60, 40) if is_active else COLOR_PANEL_BG
            btn_m.text_color = COLOR_GREEN if is_active else COLOR_TEXT_SECONDARY
            btn_m.draw(self.screen, self.font_bold)
            bx_cur += bw + 6

        # Note
        self.screen.blit(self.font_small.render("SPACE=Play/Pause | S=Step | R=Reset | E=E-Stop | 1-4=Fog", True, COLOR_TEXT_MUTED), (x + 16, y + 160))

    # ==============================================================================
    # Bottom Section: Real-time Telemetry Speed Graph
    # ==============================================================================

    def canonical_twin_rows(self):
        """
        P9 - the canonical Twin panel's render model. PURE: no pygame, so it is
        testable headlessly, and no Twin logic lives inside a drawing function.

        Returns (header_text, rows). Every row states, for one canonical vehicle,
        the SUPPLIED speed, provenance and freshness. Nothing is computed, nothing
        is defaulted and no simulator value is substituted for a missing canonical
        one - a field the backend Twin does not carry renders UNAVAILABLE.
        """
        client = getattr(self.bridge, "canonical", None)
        if client is None:
            return ("CANONICAL TWIN NOT CONNECTED - simulator-local only", [])

        rows = []
        for vehicle_id in sorted(client.vehicles()):
            vehicle = client.vehicle(vehicle_id)
            if vehicle is None:
                continue
            speed_kmh = to_kmh(vehicle.speed_mps)
            rows.append({
                "vehicle_id": vehicle_id,
                "speed_kmh": fmt_value(speed_kmh, ".1f"),
                "rpm": fmt_value(vehicle.rpm, ".0f"),
                "provenance": vehicle.provenance_label(),
                "freshness": vehicle.freshness_label(),
                "comms": vehicle.communication_state or "UNKNOWN",
            })
        return (client.status_text(), rows)

    def canonical_unavailable_notes(self):
        """
        P9 - what the canonical Twin does NOT carry, stated rather than hidden.

        The live backend returns empty `environment`, `roads` and `mine` blocks. An
        empty environment panel and a hazard-free one look identical, so the absence
        is named instead of drawn as nothing.
        """
        client = getattr(self.bridge, "canonical", None)
        if client is None:
            return []
        notes = []
        for block, label in (("environment", "environment"), ("roads", "road state"),
                             ("mine", "topology")):
            if client.block_is_empty(block):
                notes.append("canonical %s UNAVAILABLE" % label)
        return notes

    def draw_canonical_twin_panel(self):
        """
        Panel 5: the canonical Twin, READ-ONLY.

        Deliberately separate from every simulator panel. A value here came from the
        HMI backend's Twin; a value anywhere else on this screen came from this
        process's simulator. The two are never interleaved in one list, because a
        reader cannot tell them apart once they are.
        """
        pygame = self.pygame
        x, y, w, h = 848, 636, 400, 184
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        header, rows = self.canonical_twin_rows()
        self.screen.blit(self.font_section.render("CANONICAL DIGITAL TWIN (READ-ONLY)",
                                                  True, COLOR_CYAN), (x + 16, y + 12))
        self.screen.blit(self.font_small.render(header, True, COLOR_TEXT_SECONDARY), (x + 16, y + 34))

        row_y = y + 56
        if not rows:
            self.screen.blit(
                self.font_small.render("No canonical vehicle supplied.", True, COLOR_TEXT_SECONDARY),
                (x + 16, row_y))
            row_y += 18
        for row in rows[:4]:
            line = "%s  %s km/h  %s  %s" % (row["vehicle_id"], row["speed_kmh"],
                                            row["provenance"], row["freshness"])
            self.screen.blit(self.font_small.render(line, True, COLOR_TEXT_PRIMARY), (x + 16, row_y))
            row_y += 18

        for note in self.canonical_unavailable_notes()[:3]:
            self.screen.blit(self.font_small.render(note, True, COLOR_TEXT_SECONDARY), (x + 16, row_y))
            row_y += 16

    def draw_speed_graph(self):
        """
        Renders real-time rolling telemetry graph of:
        - Solid Cyan Line: Current Truck Speed (km/h)
        - Dashed Amber Line: Safe Speed Limit Ceiling (km/h)
        - Dotted White/Green Line: Commanded Target Speed (km/h)
        """
        pygame = self.pygame
        x, y, w, h = 874, 404, 422, 416
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), 1, border_radius=8)

        # Header & Legend
        hdr = self.font_section.render("LIVE SPEED vs SAFE SPEED GRAPH", True, COLOR_CYAN)
        self.screen.blit(hdr, (x + 16, y + 12))

        # Legend Callout
        pygame.draw.line(self.screen, COLOR_CYAN, (x + 16, y + 36), (x + 36, y + 36), 3)
        self.screen.blit(self.font_small.render("Current Speed", True, COLOR_TEXT_PRIMARY), (x + 42, y + 30))
        
        pygame.draw.line(self.screen, COLOR_AMBER, (x + 140, y + 36), (x + 160, y + 36), 2)
        self.screen.blit(self.font_small.render("Safe Limit (v_safe)", True, COLOR_AMBER), (x + 166, y + 30))
        
        pygame.draw.line(self.screen, COLOR_GREEN, (x + 285, y + 36), (x + 305, y + 36), 1)
        self.screen.blit(self.font_small.render("Commanded", True, COLOR_GREEN), (x + 310, y + 30))

        # Plot Canvas Box
        gx = x + 40
        gy = y + 54
        gw = w - 56
        gh = h - 84

        pygame.draw.rect(self.screen, (15, 19, 26), (gx, gy, gw, gh), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (gx, gy, gw, gh), 1, border_radius=4)

        # Horizontal Gridlines (0, 10, 20, 30, 40, 50 km/h)
        max_speed_axis = 50.0
        for sp_val in [0, 10, 20, 30, 40, 50]:
            ly = gy + gh - int((sp_val / max_speed_axis) * gh)
            pygame.draw.line(self.screen, (28, 36, 48), (gx, ly), (gx + gw, ly), 1)
            lbl = self.font_small.render(f"{sp_val}", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl, (gx - 24, ly - 7))

        # Axis Units
        self.screen.blit(self.font_small.render("km/h", True, COLOR_TEXT_MUTED), (gx - 28, gy - 12))
        self.screen.blit(self.font_small.render("Simulation Time (Rolling 120s Window) ►", True, COLOR_TEXT_MUTED), (gx + gw - 220, gy + gh + 6))

        # Plot Data Lines
        pts_count = len(self.bridge.history_time)
        if pts_count > 1:
            pts_speed = []
            pts_safe = []
            pts_cmd = []

            for i in range(pts_count):
                px = gx + int((i / float(max(1, pts_count - 1))) * gw)
                
                # Speed
                sy = gy + gh - int((np.clip(self.bridge.history_speed[i], 0.0, max_speed_axis) / max_speed_axis) * gh)
                pts_speed.append((px, sy))
                
                # Safe Speed
                sfy = gy + gh - int((np.clip(self.bridge.history_safe_speed[i], 0.0, max_speed_axis) / max_speed_axis) * gh)
                pts_safe.append((px, sfy))
                
                # Commanded Speed
                cy_val = gy + gh - int((np.clip(self.bridge.history_cmd_speed[i], 0.0, max_speed_axis) / max_speed_axis) * gh)
                pts_cmd.append((px, cy_val))

            # Draw Lines
            pygame.draw.lines(self.screen, COLOR_GREEN, False, pts_cmd, 1)
            pygame.draw.lines(self.screen, COLOR_AMBER, False, pts_safe, 2)
            pygame.draw.lines(self.screen, COLOR_CYAN, False, pts_speed, 3)

            # Draw Current Point Marker
            if pts_speed:
                pygame.draw.circle(self.screen, COLOR_CYAN, pts_speed[-1], 4)
                pygame.draw.circle(self.screen, COLOR_AMBER, pts_safe[-1], 4)

    # ==============================================================================
    # Main Execution Loop
    # ==============================================================================

    def run(self):
        """Main real-time rendering and simulation loop."""
        running = True
        self.last_wall_time = time.time()
        self.sim_time_accumulator = 0.0

        while running:
            # Handle Inputs
            running = self.handle_input()
            if not running:
                break

            # Fixed Timestep Simulation Pacing
            now = time.time()
            dt_wall = min(0.25, now - self.last_wall_time)
            self.last_wall_time = now

            if self.bridge.running:
                # Accumulate simulated time based on speed multiplier
                self.sim_time_accumulator += dt_wall * self.bridge.speed_multiplier
                # Step simulation while accumulated time >= dt (1.0s)
                while self.sim_time_accumulator >= self.bridge.sim.dt:
                    self.bridge.step()
                    self.sim_time_accumulator -= self.bridge.sim.dt

            # Render Frame
            self.render()
            self.clock.tick(self.fps)

        self.pygame.quit()


# ==============================================================================
# 3. Headless Verification Test
# ==============================================================================

def run_headless_test() -> bool:
    """
    Executes an automated, headless test of the UI, simulation bridge,
    and visual rendering pipeline.
    """
    print("\n==================================================")
    print("FOG-ORCHESTRATOR 2.0 — UI Headless Verification")
    print("==================================================")

    try:
        # 1. Initialize UI Bridge
        print("[1/7] Initializing Simulation UI Bridge...")
        bridge = SimulationUIBridge()
        tel_init = bridge.get_telemetry()
        assert tel_init["truck_id"] == "TRUCK_01"
        assert tel_init["visibility_m"] == 50.0
        assert tel_init["safety_status"] == "SAFE"
        print(f"      Initial state: Speed={tel_init['speed_kmh']:.1f} km/h, Safe={tel_init['v_safe_kmh']:.1f} km/h, Vis={tel_init['visibility_m']:.1f}m")

        # 2. Advance Simulation Steps along ROAD_1
        print("[2/7] Advancing simulation timesteps on ROAD_1...")
        bridge.running = True
        for _ in range(10):
            bridge.step()
        tel_step = bridge.get_telemetry()
        assert tel_step["timestamp"] >= 10.0
        print(f"      Advanced to t={tel_step['timestamp']:.1f}s, Position={tel_step['position_m']:.1f}m, Speed={tel_step['speed_kmh']:.1f} km/h")

        # 3. Test Fog/Visibility Adjustment & Safe Speed Propagation
        print("[3/7] Testing Fog adjustment (50m -> 15m DENSE FOG)...")
        bridge.set_visibility(15.0)
        for _ in range(4):
            bridge.step()
        tel_fog = bridge.get_telemetry()
        assert tel_fog["visibility_m"] == 15.0
        assert tel_fog["v_safe_kmh"] < tel_init["v_safe_kmh"]
        assert tel_fog["surface_state"] == "wet"
        print(f"      Fog updated: Vis={tel_fog['visibility_m']:.1f}m, Safe Speed reduced to {tel_fog['v_safe_kmh']:.1f} km/h (Surface: {tel_fog['surface_state']})")

        # 4. Test Speed Command & Local Safety Governor Clamping
        print("[4/7] Testing Commanded Speed adjustments & Local Governor...")
        bridge.set_target_speed(45.0)
        bridge.step()
        tel_spd = bridge.get_telemetry()
        # Local safety governor strictly clamps commanded speed to safe speed ceiling
        assert tel_spd["v_command_mps"] <= tel_spd["v_safe_mps"] + 1e-4
        print(f"      Commanded Target=45.0 km/h, Clamped Command={tel_spd['v_command_kmh']:.1f} km/h <= Safe={tel_spd['v_safe_kmh']:.1f} km/h")

        # 5. Test Emergency Stop & Release
        print("[5/7] Testing Emergency Stop and Reset...")
        bridge.trigger_emergency_stop()
        bridge.step()
        tel_estop = bridge.get_telemetry()
        assert tel_estop["e_stop"] is True
        assert tel_estop["v_command_kmh"] == 0.0
        assert tel_estop["safety_status"] == "E-STOP"
        print("      Emergency Stop active: Status=E-STOP, Commanded Speed=0.0 km/h")
        
        bridge.release_emergency_stop()
        bridge.set_target_speed(35.0)
        bridge.set_visibility(50.0)

        # 6. Test Car-Following Proximity Hold & Headway Queue
        print("[6/8] Testing Car-Following Safety Proximity & Queue Formation...")
        # Reset and configure 2 trucks on ROAD_1 in close proximity
        bridge.reset()
        t1 = bridge.get_truck("TRUCK_01")
        t1.position_s = 180.0
        t1.speed_mps = 0.0

        t2 = bridge.get_truck("TRUCK_02")
        if t2 in bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_1"
        t2.current_node = None
        t2.position_s = 155.0  # gap = 180 - 155 - 14.5 = 10.5m <= safe_hw (~15.5m)
        t2.speed_mps = 6.0
        bridge.sim.network.edges["ROAD_1"].vehicles.append(t2)

        bridge.evaluate_physics()
        assert t2.is_following_stopped is True
        assert t2.v_command_mps == 0.0
        
        # Advance 3 steps: Following truck must safely stop behind lead truck without overlap
        for _ in range(3):
            t1.speed_mps = 0.0
            bridge.step()
        assert t2.speed_mps == 0.0
        assert t2.position_s < t1.position_s - 14.0
        print(f"      Car-Following verified: TRUCK_02 stopped behind TRUCK_01 (Pos: {t2.position_s:.1f}m < {t1.position_s:.1f}m, Gap: {t2.lead_gap_m:.1f}m)")

        # 7. Test Full Circuit Progression: Crusher Queue Arrival & Return Transition
        print("[7/8] Testing Crusher Arrival, Service Queuing & ROAD_RETURN Transition...")
        # Reset to clean circuit
        bridge.reset()
        bridge.running = True
        # Step through ROAD_1 and ROAD_2 until Crusher is reached
        for _ in range(120):
            bridge.step()
            if bridge.get_truck("TRUCK_01").current_node == "CRUSHER" or bridge.sim.network.nodes["CRUSHER"].queue.length > 0:
                break

        tel_crush = bridge.get_telemetry()
        assert tel_crush["crusher_queue_len"] >= 1 or tel_crush["current_edge"] == "CRUSHER"
        print(f"      Truck arrived at CRUSHER: State={tel_crush['truck_state']}, Desc={tel_crush['location_label']}")

        # Advance through the dynamic Crusher service time (derived from service_rate_vph) to verify return transition
        crusher_service_steps = int(bridge.sim.network.nodes["CRUSHER"].queue.service_time_s) + 10
        for _ in range(crusher_service_steps):
            bridge.step()
            if bridge.get_truck("TRUCK_01").current_edge == "ROAD_RETURN":
                break

        tel_ret = bridge.get_telemetry()
        assert tel_ret["current_edge"] == "ROAD_RETURN" or bridge.get_truck("TRUCK_01").current_edge == "ROAD_RETURN"
        assert tel_ret["is_loaded"] is False  # Ore was successfully unloaded
        print(f"      Crusher service complete: Truck transitioned to ROAD_RETURN (Empty: {tel_ret['is_loaded']==False})")

        # 8. Initialize UI Engine and Render Headless Frame
        print("[8/8] Initializing Pygame Renderer and rendering frame...")
        ui = MiningVisualizerUI(bridge, headless=True)
        ui.render()
        
        # Test screenshot export
        screenshot_path = os.path.join(PROJECT_ROOT, "ui_headless_render.png")
        ui.pygame.image.save(ui.screen, screenshot_path)
        assert os.path.exists(screenshot_path)
        print(f"      Rendered frame successfully saved to: {screenshot_path}")
        ui.pygame.quit()

        print("\n==================================================")
        print("UI HEADLESS TEST: PASS")
        print("==================================================")
        return True

    except Exception as e:
        print(f"\nUI HEADLESS TEST: FAIL -> {e}")
        import traceback
        traceback.print_exc()
        return False


# ==============================================================================
# Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="FOG-ORCHESTRATOR 2.0 Mine Visualization UI")
    parser.add_argument("--test", action="store_true", help="Run automated headless verification test and exit")
    # P9 - OPT-IN, so the documented launch command behaves exactly as before.
    #
    # Without this flag game_ui is the same self-contained simulator it has always
    # been. With it, the canonical Twin panel additionally DISPLAYS the HMI
    # backend's Twin, read-only. Either way the simulator is unchanged.
    parser.add_argument("--canonical-twin", action="store_true",
                        help="Also display the HMI backend's canonical Twin (read-only)")
    parser.add_argument("--twin-url", default=None,
                        help="Canonical Twin snapshot URL (implies --canonical-twin)")
    args = parser.parse_args()

    if args.test:
        success = run_headless_test()
        sys.exit(0 if success else 1)

    client = None
    if (args.canonical_twin or args.twin_url) and CanonicalTwinClient is not None:
        client = CanonicalTwinClient(url=args.twin_url) if args.twin_url else CanonicalTwinClient()
        client.start()

    bridge = SimulationUIBridge(canonical_client=client)
    ui = MiningVisualizerUI(bridge, headless=False)
    try:
        ui.run()
    finally:
        if client is not None:
            client.stop()

if __name__ == "__main__":
    main()
