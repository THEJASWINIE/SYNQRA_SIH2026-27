"""
Domain service for interactive (UI-driven) simulation stepping — P7.

WHY THIS EXISTS
    `game_ui.py` used to compute safe speed itself: it called `resolve_v_safe()` twice per
    frame, applied a stopping-distance formula, and fell back to a hardcoded 13.89 m/s
    when it had no answer. That made the renderer a second safety authority.

    That logic now lives here, in the domain layer, unchanged in behaviour. `game_ui.py`
    calls this service and then READS the results from the canonical Twin. The renderer
    computes no safety of its own.

AUTHORITY
    v_safe still comes from exactly one place: `models.vehicle_physics.resolve_v_safe`,
    which is the P2 compatibility adapter over `fog_safe.safety.solve_safe_speed`. This
    module orchestrates; it does not implement physics and contains no safety formula.

    v_command = min(v_dispatch, v_safe) is applied here because it is the existing domain
    contract (`twin/simulator.py` does the same). It is NOT a second solver.

NO OPTIMISTIC FALLBACKS
    A queued (stationary) vehicle gets `v_safe_mps = 0.0` - it is not cleared to move.
    The previous code gave it 13.89 m/s (50 km/h), which told the UI a queued truck could
    travel at road speed. Nothing here ever substitutes an optimistic ceiling.
"""

from __future__ import annotations

from models.braking import calculate_stopping_distance
from models.vehicle_physics import resolve_v_safe


class UISimulationDomain:
    """
    Owns the safety/dispatch evaluation the interactive UI needs.

    Constructed with the existing simulator and vehicle configuration; mutates the same
    domain objects `twin/simulator.py` already owns, so there is one state model.
    """

    def __init__(self, sim, vehicle_cfg):
        self.sim = sim
        self.vehicle_cfg = vehicle_cfg

    def _solve(self, mass_kg, edge, speed_limit_mps):
        """Single call-through to the authoritative solver. No formula lives here."""
        return resolve_v_safe(
            mass_kg=mass_kg,
            grade_percent=edge.grade_percent,
            friction_mu=edge.friction_mu,
            c_rr=edge.c_rr,
            hardware_max_brake_n=self.vehicle_cfg["hardware_max_brake_force_n"],
            max_retarder_power_w=self.vehicle_cfg["max_retarder_power_w"],
            curve_radius_m=edge.curve_radius_m,
            traction_speed_factor_mps=self.vehicle_cfg["traction_speed_factor_mps"],
            speed_limit_mps=speed_limit_mps,
            visibility_m=edge.visibility_m,
            tau_total=self.vehicle_cfg["ecu_hydraulic_latency_s"],
            s_margin=self.vehicle_cfg["safety_stop_margin_m"],
        )

    def evaluate(self, target_speed_kmh, e_stop_active, car_following_limit):
        """
        Evaluate safety and dispatch for every vehicle.

        `car_following_limit(vehicle, edge)` is supplied by the caller and returns
        (limit_mps, lead_id, gap_m, is_following_stopped) - the UI's spacing policy, which
        is a dispatch concern rather than a safety-physics one.

        Priority (unchanged from the previous in-UI implementation):
            E-STOP -> following-stop -> physical v_safe -> commanded target
        """
        target_mps = 0.0 if e_stop_active else (target_speed_kmh / 3.6)

        for edge in self.sim.network.edges.values():
            nom_limit = getattr(edge, "nominal_speed_limit", edge.speed_limit_mps)

            edge_result = self._solve(
                self.vehicle_cfg["tare_mass_kg"] + self.vehicle_cfg["payload_mass_kg"],
                edge,
                nom_limit,
            )
            edge.v_safe_mps = edge_result["v_safe"]

            edge.vehicles.sort(key=lambda x: getattr(x, "position_s", 0.0), reverse=True)

            for v in edge.vehicles:
                result = self._solve(v.mass_kg, edge, nom_limit)

                v.v_safe_mps = result["v_safe"]
                v.safety_primary_constraint = result.get("primary_constraint")
                v.safety_secondary_constraint = result.get("secondary_constraint")

                a_dec = max(0.1, result["a_dec"])
                v.stop_envelope_m = calculate_stopping_distance(
                    v.speed_mps, a_dec, self.vehicle_cfg["ecu_hydraulic_latency_s"]
                ) + self.vehicle_cfg["safety_stop_margin_m"]
                v.safe_headway_m = max(
                    v.stop_envelope_m + self.vehicle_cfg["safety_headway_margin_m"],
                    self.vehicle_cfg["min_static_headway_m"],
                )

                limit, lead_id, gap_m, following_stopped = car_following_limit(v, edge)
                v.lead_vehicle_id = lead_id
                v.lead_gap_m = gap_m
                v.is_following_stopped = following_stopped

                if e_stop_active or following_stopped:
                    v.v_dispatch_mps = 0.0
                else:
                    v.v_dispatch_mps = min(target_mps, nom_limit, limit)

                # Existing domain contract: the commanded speed never exceeds v_safe.
                v.v_command_mps = min(v.v_dispatch_mps, v.v_safe_mps)

        for node in self.sim.network.nodes.values():
            if not node.queue:
                continue
            for v in node.queue.vehicles:
                # A queued vehicle is stationary at a node. Its safe speed is 0.0 - it is
                # not cleared to move.
                #
                # This replaces the previous hardcoded 13.89 m/s (50 km/h), which told the
                # UI a queued truck could travel at road speed. 0.0 is the conservative,
                # correct answer; it is NOT an optimistic fallback.
                v.v_safe_mps = 0.0
                v.safety_primary_constraint = None
                v.safety_secondary_constraint = None
                v.v_dispatch_mps = 0.0
                v.v_command_mps = 0.0
                v.stop_envelope_m = 0.0
                v.safe_headway_m = self.vehicle_cfg["min_static_headway_m"]
                v.is_following_stopped = False
                v.lead_vehicle_id = None
                v.lead_gap_m = float("inf")
