"""
twin/simulator.py
-----------------
Master discrete-time digital twin simulation engine.
Coordinates environment, vehicle physics, safety governors, road capacities,
queues, bottleneck detection, arrival-rate shaping, and switchback coordination.

Step Update Order (STRICT INVARIANT):
1. Environment
2. Vehicle state
3. Safety
4. Road capacity
5. Queue
6. Bottleneck
7. Arrival shaping
8. Switchback state

Requirements:
- Configurable timestep dt <= 1.0 s
- Deterministic random seed support
- Traceable KPIs and state synchronization
"""

from typing import Dict, Any, List, Optional, Tuple
import math
import numpy as np

from twin.state import TwinState, EnvironmentState, RoadSegmentState, ServiceNodeState, AlertEntry
from twin.network import MineNetwork
from models.vehicle import Vehicle, VehicleState
from models.vehicle_physics import VehiclePhysics, GRAVITY_G
from models.friction import FrictionModel
from models.retarder import RetarderModel
from models.braking import BrakingModel
from models.road_capacity import RoadCapacityModel
from models.queue_model import QueueModel, ArrivalRateShaper
from models.bottleneck import BottleneckDetector, BottleneckEntry
from models.switchback import SwitchbackCoordinator, TimeSlot


class MineDigitalTwinSimulator:
    """
    Master digital twin simulation engine coordinating physical vehicle dynamics,
    environmental disturbances, queuing, and hierarchical safety / coordination layers.
    """
    def __init__(
        self,
        network: MineNetwork,
        vehicle_config: Dict[str, Any],
        weather_config: Optional[Dict[str, Any]] = None,
        dt_seconds: float = 1.0,
        seed: int = 42
    ):
        if dt_seconds <= 0.0 or dt_seconds > 1.0:
            raise ValueError(f"Simulation timestep dt must be in (0.0, 1.0] s, got {dt_seconds} s")

        self.network = network
        self.vehicle_config = vehicle_config
        self.weather_config = weather_config or {}
        self.dt_seconds = float(dt_seconds)
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Reference masses
        self.tare_mass = float(self.vehicle_config.get("mass", {}).get("tare_weight_kg", 74000.0))
        self.gross_mass = float(self.vehicle_config.get("mass", {}).get("gross_operating_weight_kg", 165500.0))

        # Initialize core sub-models
        self.physics_engine = VehiclePhysics(self.vehicle_config)
        self.friction_model = FrictionModel(self.weather_config)
        self.retarder_model = RetarderModel(self.vehicle_config)
        self.braking_model = BrakingModel(self.vehicle_config)
        self.capacity_model = RoadCapacityModel(self.vehicle_config)
        self.bottleneck_detector = BottleneckDetector({"bottleneck": {"w1": 1.0, "w2": 0.5, "w3": 1.0}})
        self.arrival_shaper = ArrivalRateShaper(default_delta_buffer_vph=2.0)
        
        # Switchback reservation and clearance parameters
        sb_cfg = self.vehicle_config.get("switchback", {})
        self.switchback_stop_line_margin: float = float(sb_cfg.get("stop_line_margin_m", 3.0))
        self.switchback_lookahead_m: float = float(sb_cfg.get("lookahead_m", 25.0))
        self.switchback_safety_buffer_s: float = float(sb_cfg.get("safety_buffer_s", 0.5))

        # Switchback coordinators (one per switchback node)
        self.switchback_coordinators: Dict[str, SwitchbackCoordinator] = {}
        for sb_id in self.network.get_nodes_by_type("SWITCHBACK"):
            self.switchback_coordinators[sb_id] = SwitchbackCoordinator(
                resource_id=sb_id,
                config={"safety_buffer_s": self.switchback_safety_buffer_s}
            )

        # Queue models (one per service node)
        self.queue_models: Dict[str, QueueModel] = {}
        for node_id, n_data in self.network.nodes_by_id.items():
            self.queue_models[node_id] = QueueModel(
                node_id=node_id,
                service_rate_vph=float(n_data.get("service_rate_vph", 15.0)),
                queue_max=int(n_data.get("queue_max", 8)),
                initial_queue=0.0
            )

        # Master synchronized state
        self.state = TwinState(dt_seconds=self.dt_seconds)
        self.vehicles: Dict[str, Vehicle] = {}
        self.vehicle_routes: Dict[str, List[str]] = {}
        self.vehicle_route_indices: Dict[str, int] = {}
        self.vehicle_target_speeds: Dict[str, float] = {}

        self._initialize_state_containers()

    def _initialize_state_containers(self) -> None:
        """Populate initial road and node state records from network topology."""
        # 1. Initialize Roads
        for road_id, r_data in self.network.roads_by_id.items():
            self.state.roads[road_id] = RoadSegmentState(
                id=road_id,
                from_node=r_data["from_node"],
                to_node=r_data["to_node"],
                length_m=r_data["length_m"],
                grade_pct=r_data["grade_pct"],
                curve_radius_m=r_data["curve_radius_m"],
                width_m=r_data["width_m"],
                direction_mode=r_data["direction_mode"],
                speed_limit_mps=r_data["speed_limit_mps"],
                surface_state=r_data.get("surface_state", "dry"),
                visibility_m=r_data.get("visibility_m", 50.0),
                friction_mu=r_data.get("friction_mu", 0.65),
                friction_sigma=r_data.get("friction_sigma", 0.05),
                safe_speed_mps=r_data["speed_limit_mps"],
                safe_headway_m=15.52,
                capacity_vph=600.0
            )

        # 2. Initialize Nodes
        for node_id, n_data in self.network.nodes_by_id.items():
            self.state.nodes[node_id] = ServiceNodeState(
                id=node_id,
                node_type=n_data["type"],
                service_rate_vph=n_data["service_rate_vph"],
                queue_length=0.0,
                queue_max=n_data["queue_max"],
                criticality=n_data.get("criticality", 0.5)
            )

    def spawn_vehicle(
        self,
        vehicle_id: str,
        initial_node_id: str,
        route_nodes: Optional[List[str]] = None,
        is_loaded: bool = False
    ) -> Vehicle:
        """
        Instantiate and spawn a new vehicle into the digital twin.
        """
        if vehicle_id in self.vehicles:
            raise ValueError(f"Vehicle '{vehicle_id}' is already spawned")
        if initial_node_id not in self.network.nodes_by_id:
            raise ValueError(f"Initial node '{initial_node_id}' not found in mine network")

        vehicle = Vehicle(vehicle_id=vehicle_id, config=self.vehicle_config)
        if is_loaded:
            vehicle.set_payload(91.5)  # 91.5 t payload [REFERENCE]
        else:
            vehicle.set_payload(0.0)

        # Default haul cycle route from shovel to crusher if not supplied
        if not route_nodes:
            crushers = self.network.get_nodes_by_type("CRUSHER")
            dest = crushers[0] if crushers else initial_node_id
            route_nodes = self.network.find_shortest_path(initial_node_id, dest)

        self.vehicles[vehicle_id] = vehicle
        self.vehicle_routes[vehicle_id] = route_nodes
        speed_limit = 11.11
        if len(route_nodes) >= 2:
            u, v = route_nodes[0], route_nodes[1]
            edge_data = self.network.get_edge_data(u, v)
            if edge_data:
                speed_limit = float(edge_data.get("speed_limit_mps", 11.11))
                vehicle.update_position(road_edge_id=edge_data["id"], position_s=0.0)
                vehicle.state.lane_or_direction = "reverse" if edge_data.get("is_reverse_edge") else "forward"
                self._update_vehicle_lateral_offset(vehicle)

        self.vehicle_target_speeds[vehicle_id] = speed_limit
        vehicle.state.target_speed = speed_limit
        self.state.vehicles[vehicle_id] = vehicle.get_state()
        return vehicle

    def spawn_fleet(
        self,
        num_vehicles: int,
        initial_nodes: Optional[List[str]] = None
    ) -> List[Vehicle]:
        """
        Spawn a fleet of num_vehicles (supports 4, 10, 20, 30, 40, 50 vehicles).
        Evenly distributes vehicles across loading shovel nodes and upstream approach routes
        with clean, safe longitudinal spacing along valid road centerlines.
        """
        if num_vehicles < 1:
            raise ValueError(f"num_vehicles must be at least 1, got {num_vehicles}")

        available_sources = initial_nodes or ["SHOVEL_01", "SHOVEL_02", "BUFFER_01"]
        crushers = self.network.get_nodes_by_type("CRUSHER")
        primary_crusher = crushers[0] if crushers else "CRUSHER_01"

        spawned_list = []
        for i in range(num_vehicles):
            vid = f"TRUCK_{i+1:03d}"
            source_node = available_sources[i % len(available_sources)]
            is_loaded = (i % 2 == 0)  # Interleave loaded and empty trucks

            route = self.network.find_shortest_path(source_node, primary_crusher)
            if not route:
                route = [source_node]

            truck = self.spawn_vehicle(
                vehicle_id=vid,
                initial_node_id=source_node,
                route_nodes=route,
                is_loaded=is_loaded
            )
            # Offset initial position to prevent overlap at start
            if len(route) >= 2:
                edge_data = self.network.get_edge_data(route[0], route[1])
                if edge_data:
                    # If all vehicles share a single approach road (e.g. switchback approach),
                    # distribute them progressively upstream along the road:
                    if len(available_sources) == 1:
                        init_pos = max(20.0, (edge_data["length_m"] * 0.70) - i * 35.0)
                    else:
                        init_pos = (i % 5) * 20.0  # 20m staggered spacing across multi-source nodes
                    truck.update_position(road_edge_id=edge_data["id"], position_s=min(init_pos, edge_data["length_m"] * 0.8))
                    truck.state.lane_or_direction = "reverse" if edge_data.get("is_reverse_edge") else "forward"
                    self._update_vehicle_lateral_offset(truck)
                    self.state.vehicles[vid] = truck.get_state()
            
            spawned_list.append(truck)

        return spawned_list

    def _update_vehicle_lateral_offset(self, vehicle: Vehicle) -> None:
        """Calculate and set virtual travel lane lateral offset in vehicle state."""
        road = self.state.roads.get(vehicle.state.road_edge)
        if not road or road.direction_mode == "single_lane_alternating" or road.id == "ROAD_04_SWITCH1_TO_INT2":
            vehicle.state.lateral_offset_m = 0.0
        else:
            w = getattr(road, "width_m", 16.0)
            offset = w / 4.0
            vehicle.state.lateral_offset_m = -offset if vehicle.state.lane_or_direction == "reverse" else offset

    def _assign_new_route(self, vid: str, vehicle: Vehicle, route_nodes: List[str]) -> None:
        """Assign a new route to a vehicle and place it on the first edge of that route."""
        self.vehicle_routes[vid] = route_nodes
        self.vehicle_route_indices[vid] = 0
        if len(route_nodes) >= 2:
            edge_data = self.network.get_edge_data(route_nodes[0], route_nodes[1])
            if edge_data:
                vehicle.update_position(road_edge_id=edge_data["id"], position_s=0.0)
                vehicle.state.lane_or_direction = "reverse" if edge_data.get("is_reverse_edge") else "forward"
                self._update_vehicle_lateral_offset(vehicle)
        vehicle.state.speed_v = 0.0

    def set_environmental_conditions(
        self,
        weather_mode: str = "CLEAR",
        visibility_m: float = 50.0,
        surface_state: str = "dry",
        friction_mu: Optional[float] = None,
        wind_speed_mps: float = 2.0
    ) -> None:
        """Update global environmental condition parameters and immediately recompute twin safety envelopes & capacities."""
        mu_mean, mu_sigma, c_rr = self.friction_model.get_surface_prior(surface_state)
        if friction_mu is not None and friction_mu > 0.0:
            mu_mean = float(friction_mu)
        
        self.state.environment.weather_mode = weather_mode
        self.state.environment.default_visibility_m = float(visibility_m)
        self.state.environment.surface_state = surface_state
        self.state.environment.default_friction_mu = float(mu_mean)
        self.state.environment.default_friction_sigma = float(mu_sigma)
        self.state.environment.default_crr = float(c_rr)
        setattr(self.state.environment, "wind_speed_mps", float(wind_speed_mps))

        # Apply to all road segments
        for road_state in self.state.roads.values():
            road_state.visibility_m = float(visibility_m)
            road_state.surface_state = surface_state
            road_state.friction_mu = float(mu_mean)
            road_state.friction_sigma = float(mu_sigma)

        # Immediate recalculation of safety envelopes, road capacities, and bottlenecks
        self._recalculate_safety_and_capacities()

    def update_weather(
        self,
        visibility_m: Optional[float] = None,
        friction_mu: Optional[float] = None,
        weather_mode: str = "FOG",
        surface_state: str = "damp"
    ) -> None:
        """Convenience helper to update environmental conditions and recalculate safety envelopes."""
        vis = visibility_m if visibility_m is not None else self.state.environment.default_visibility_m
        fric = friction_mu if friction_mu is not None else self.state.environment.default_friction_mu
        self.set_environmental_conditions(
            weather_mode=weather_mode,
            visibility_m=vis,
            surface_state=surface_state,
            friction_mu=fric
        )

    def _recalculate_safety_and_capacities(self) -> None:
        """Immediate re-evaluation of safety envelopes, road capacities, and bottlenecks after environment updates."""
        # 1. Update vehicle safety envelopes
        vehicles_by_road: Dict[Tuple[str, str], List[Tuple[str, VehicleState]]] = {}
        for vid, vehicle in self.vehicles.items():
            self._update_vehicle_lateral_offset(vehicle)
            v_state = vehicle.get_state()
            edge_id = v_state.road_edge
            dir_mode = v_state.lane_or_direction
            key = (edge_id, dir_mode)
            if key not in vehicles_by_road:
                vehicles_by_road[key] = []
            vehicles_by_road[key].append((vid, v_state))

        for (road_id, v_dir), v_list in vehicles_by_road.items():
            road = self.state.roads.get(road_id)
            if not road:
                continue

            v_list.sort(key=lambda item: item[1].position_s, reverse=True)
            eff_grade_pct = -road.grade_pct if v_dir == "reverse" else road.grade_pct
            grade_rad = math.atan(eff_grade_pct / 100.0)
            mu_safe = self.friction_model.calculate_safe_friction(road.friction_mu, road.friction_sigma)
            c_rr = self.state.environment.default_crr

            for idx, (vid, v_state) in enumerate(v_list):
                r_effective = road.visibility_m
                if idx > 0:
                    leader_vid, leader_state = v_list[idx - 1]
                    dist_to_leader = max(0.0, leader_state.position_s - v_state.position_s - 10.52)
                    r_effective = min(r_effective, dist_to_leader)

                safe_res = self.braking_model.calculate_safe_speed(
                    r_effective=r_effective,
                    grade_rad=grade_rad,
                    mass_kg=v_state.mass_m,
                    mu_safe=mu_safe,
                    curve_radius_m=road.curve_radius_m,
                    speed_limit_mine_mps=road.speed_limit_mps,
                    tau_total=self.braking_model.tau_total_default,
                    c_rr=c_rr,
                    s_margin=5.0
                )
                v_safe = safe_res["v_safe"]
                v_dispatch = self.vehicle_target_speeds.get(vid, 11.11)
                v_command = self.braking_model.compute_command_speed(v_dispatch, v_safe)
                v_state.target_speed = v_command

        # 2. Update road capacities & safe speeds
        for road_id, road in self.state.roads.items():
            grade_rad = math.atan(road.grade_pct / 100.0)
            mu_safe = self.friction_model.calculate_safe_friction(road.friction_mu, road.friction_sigma)
            safe_res = self.braking_model.calculate_safe_speed(
                r_effective=road.visibility_m,
                grade_rad=grade_rad,
                mass_kg=self.gross_mass,
                mu_safe=mu_safe,
                curve_radius_m=road.curve_radius_m,
                speed_limit_mine_mps=road.speed_limit_mps
            )
            v_safe_road = safe_res["v_safe"]
            a_dec_road = safe_res["a_dec"]
            h_safe = self.capacity_model.calculate_safe_headway(v_safe_road, a_dec_road)
            cap_dict = self.capacity_model.calculate_road_capacity(v_safe_road, h_safe)
            road.safe_speed_mps = v_safe_road
            road.safe_headway_m = h_safe
            road.capacity_vph = cap_dict["capacity_vph"]

        # 3. Update dynamic bottlenecks
        eval_elements = []
        for node_id, node_state in self.state.nodes.items():
            eval_elements.append({
                "id": node_id,
                "type": "NODE",
                "utilization": node_state.queue_length / max(1.0, node_state.queue_max),
                "queue": node_state.queue_length,
                "criticality": node_state.criticality
            })
        for road_id, road in self.state.roads.items():
            occupancy_ratio = road.active_vehicles_count / max(1.0, (road.capacity_vph / 3600.0) * (road.length_m / max(1.0, road.safe_speed_mps)))
            eval_elements.append({
                "id": road_id,
                "type": "ROAD",
                "utilization": min(1.5, occupancy_ratio),
                "queue": float(road.active_vehicles_count),
                "criticality": 0.8 if "SWITCH" in road_id else 0.5
            })
        ranked_bottlenecks = self.bottleneck_detector.rank_elements(eval_elements)
        self.state.active_bottlenecks = [
            {
                "id": b.element_id,
                "type": b.element_type,
                "rank": b.rank,
                "score": b.score,
                "utilization": b.utilization_rho,
                "queue": b.queue_length
            }
            for b in ranked_bottlenecks[:5]
        ]

    def step(self) -> TwinState:
        """
        Execute one deterministic simulation step in the exact required 8-stage sequence:
        1. Environment
        2. Vehicle state
        3. Safety
        4. Road capacity
        5. Queue
        6. Bottleneck
        7. Arrival shaping
        8. Switchback state
        """
        dt = self.dt_seconds
        self.state.timestamp += dt
        self.state.step_count += 1

        # ----------------------------------------------------------------------
        # 1. ENVIRONMENT STEP
        # ----------------------------------------------------------------------
        # Synchronize road environmental attributes
        for road in self.state.roads.values():
            road.visibility_m = self.state.environment.default_visibility_m
            road.surface_state = self.state.environment.surface_state
            road.friction_mu = self.state.environment.default_friction_mu
            road.friction_sigma = self.state.environment.default_friction_sigma

        # ----------------------------------------------------------------------
        # 2. VEHICLE STATE STEP (Longitudinal Dynamics & Movement)
        # ----------------------------------------------------------------------
        for vid, vehicle in self.vehicles.items():
            v_state = vehicle.get_state()
            current_edge_id = v_state.road_edge
            road = self.state.roads.get(current_edge_id)
            
            eff_grade_pct = -road.grade_pct if v_state.lane_or_direction == "reverse" else road.grade_pct
            grade_rad = math.atan(eff_grade_pct / 100.0) if road else 0.0
            mu = road.friction_mu if road else 0.65
            c_rr = self.state.environment.default_crr

            # Determine drive vs brake commands to track target speed
            v_target = v_state.target_speed
            v_curr = v_state.speed_v

            # Gravitational force along road (+ downhill, - uphill)
            f_grav = v_state.mass_m * 9.80665 * math.sin(grade_rad)
            f_roll = c_rr * v_state.mass_m * 9.80665 * math.cos(grade_rad)

            if v_curr < v_target:
                # Proportional drive effort accounting for downhill gravity
                speed_err = v_target - v_curr
                f_needed = (v_state.mass_m * (speed_err / dt)) - f_grav + f_roll
                if f_needed > 0.0:
                    f_drive = min(vehicle.physics.max_drive_force_n, f_needed)
                    f_brake = 0.0
                    f_ret = 0.0
                else:
                    # Gravity alone exceeds required speed; retard to maintain target speed
                    f_drive = 0.0
                    f_brake = 0.0
                    f_ret = self.retarder_model.calculate_required_retarding_force(v_state.mass_m, grade_rad, c_rr)
            else:
                # Braking / retarding effort to reduce speed
                speed_excess = v_curr - v_target
                f_drive = 0.0
                f_brake = min(vehicle.physics.f_hardware_max_n, v_state.mass_m * (speed_excess / dt))
                f_ret = self.retarder_model.calculate_required_retarding_force(v_state.mass_m, grade_rad, c_rr)

            # Advance kinematics
            new_pos, new_spd, accel = vehicle.step(
                dt=dt,
                f_drive=f_drive,
                f_brake=f_brake,
                f_retarder=f_ret,
                grade_rad=grade_rad,
                mu=mu,
                c_rr=c_rr
            )

            # Enforce speed governor clamp to prevent integration overshoot beyond target speed
            if v_target >= 0.0 and new_spd > v_target:
                new_spd = v_target
                vehicle.state.speed_v = v_target

            # Prevent discrete integration overshoot into a leader ahead on the same road in the same direction
            leader_positions = [
                v.state.position_s for v_id, v in self.vehicles.items()
                if v_id != vid and v.state.road_edge == current_edge_id
                and v.state.lane_or_direction == v_state.lane_or_direction
                and v.state.position_s > vehicle.state.position_s
            ]
            if leader_positions:
                immediate_leader_pos = min(leader_positions)
                # Minimum standstill headway bound is 15.52m (vehicle length 10.52m + 5.0m standstill margin)
                max_allowed_s = max(0.0, immediate_leader_pos - 15.52)
                if new_pos > max_allowed_s:
                    new_pos = max_allowed_s
                    new_spd = 0.0
                    vehicle.state.position_s = max_allowed_s
                    vehicle.state.speed_v = 0.0

            # Check road end and transition to next route segment if reached
            if road and new_pos >= road.length_m:
                route = self.vehicle_routes.get(vid, [])
                idx = self.vehicle_route_indices.get(vid, 0)
                
                if idx + 2 < len(route):
                    next_u = route[idx + 1]
                    next_v = route[idx + 2]
                    next_edge = self.network.get_edge_data(next_u, next_v)

                    # Check switchback entry permission (ROAD_04 single-lane alternating controlled section)
                    is_entering_sb = next_edge and (next_edge.get("direction_mode") == "single_lane_alternating" or next_edge.get("id") == "ROAD_04_SWITCH1_TO_INT2")
                    sb_id = "SWITCHBACK_01" if is_entering_sb else None
                    coord = self.switchback_coordinators.get(sb_id) if sb_id else None
                    can_enter = True
                    if coord:
                        # Hard safety interlock: cannot enter if another vehicle physically occupies the switchback
                        is_occupied = any(v_id != vid and v.state.road_edge == "ROAD_04_SWITCH1_TO_INT2" for v_id, v in self.vehicles.items())
                        has_my_slot = any(s.status in {"CONFIRMED", "ACTIVE"} and s.vehicle_id == vid for s in coord.active_slots)
                        if is_occupied or not has_my_slot:
                            can_enter = False

                    if can_enter and next_edge:
                        # Release lock on switchback if exiting switchback section
                        is_current_sb = (road.direction_mode == "single_lane_alternating" or road.id == "ROAD_04_SWITCH1_TO_INT2")
                        if is_current_sb and not is_entering_sb:
                            prev_coord = self.switchback_coordinators.get("SWITCHBACK_01")
                            if prev_coord:
                                for s in prev_coord.active_slots:
                                    if s.vehicle_id == vid:
                                        s.status = "COMPLETED"
                                occupied_sb_vids = {v_id for v_id, v in self.vehicles.items() if v.state.road_edge == "ROAD_04_SWITCH1_TO_INT2" and v_id != vid}
                                prev_coord.release_expired_slots(current_time=self.state.timestamp, occupied_vehicle_ids=occupied_sb_vids)
                                v_state.target_slot = None

                        self.vehicle_route_indices[vid] = idx + 1
                        vehicle.update_position(next_edge["id"], position_s=0.0)
                        next_spd_limit = float(next_edge.get("speed_limit_mps", 11.11))
                        next_road_state = self.state.roads.get(next_edge["id"])
                        if next_road_state and next_road_state.safe_speed_mps > 0:
                            next_spd_limit = min(next_spd_limit, next_road_state.safe_speed_mps)
                        if vehicle.state.speed_v > next_spd_limit:
                            vehicle.state.speed_v = next_spd_limit
                        vehicle.state.lane_or_direction = "reverse" if next_edge.get("is_reverse_edge") else "forward"
                        self._update_vehicle_lateral_offset(vehicle)
                    else:
                        # Hold vehicle safely at stop line before switchback entry without collapsing stop points
                        leader_positions_road = [
                            v.state.position_s for v_id, v in self.vehicles.items()
                            if v_id != vid and v.state.road_edge == road.id
                            and v.state.lane_or_direction == v_state.lane_or_direction
                            and v.state.position_s > vehicle.state.position_s
                        ]
                        if leader_positions_road:
                            imm_lead = min(leader_positions_road)
                            stop_pos = max(0.0, imm_lead - 15.52)
                        else:
                            # Leading waiting truck stops safely at entrance apron stop line before switchback
                            stop_pos = max(0.0, road.length_m - self.switchback_stop_line_margin)
                        vehicle.update_position(road.id, position_s=min(stop_pos, new_pos))
                        vehicle.state.speed_v = 0.0
                else:
                    # Reached destination node (e.g. Crusher / Dump / Shovel)
                    is_current_sb = (road.direction_mode == "single_lane_alternating" or road.id == "ROAD_04_SWITCH1_TO_INT2")
                    if is_current_sb:
                        prev_coord = self.switchback_coordinators.get("SWITCHBACK_01")
                        if prev_coord:
                            for s in prev_coord.active_slots:
                                if s.vehicle_id == vid:
                                    s.status = "COMPLETED"
                            prev_coord.release_expired_slots(current_time=self.state.timestamp)
                    v_state.target_slot = None

                    dest_node = route[-1] if route else "CRUSHER_01"
                    dest_type = self.network.nodes_by_id.get(dest_node, {}).get("type", "")

                    if dest_type == "CRUSHER":
                        # At crusher: unload if loaded, then assign return route to shovel
                        if v_state.is_loaded:
                            self.state.total_tonnage_delivered += v_state.payload_tonnes
                            vehicle.set_payload(0.0)
                        shovels = self.network.get_nodes_by_type("SHOVEL")
                        target_shovel = shovels[hash(vid) % len(shovels)] if shovels else "SHOVEL_01"
                        try:
                            return_route = self.network.find_shortest_path(dest_node, target_shovel)
                            self._assign_new_route(vid, vehicle, return_route)
                        except Exception:
                            vehicle.update_position(road.id, position_s=road.length_m)
                            vehicle.state.speed_v = 0.0
                    elif dest_type == "SHOVEL":
                        # At shovel: load if empty, then assign haul route to crusher
                        if not v_state.is_loaded:
                            vehicle.set_payload(91.5)
                        crushers = self.network.get_nodes_by_type("CRUSHER")
                        target_crusher = crushers[0] if crushers else "CRUSHER_01"
                        try:
                            haul_route = self.network.find_shortest_path(dest_node, target_crusher)
                            self._assign_new_route(vid, vehicle, haul_route)
                        except Exception:
                            vehicle.update_position(road.id, position_s=road.length_m)
                            vehicle.state.speed_v = 0.0
                    else:
                        # At other destination (e.g. DUMP_01, BUFFER, INTERSECTION)
                        if v_state.is_loaded:
                            self.state.total_tonnage_delivered += v_state.payload_tonnes
                            vehicle.set_payload(0.0)
                        # Reroute to nearest shovel to rejoin the haul cycle
                        shovels = self.network.get_nodes_by_type("SHOVEL")
                        target = shovels[hash(vid) % len(shovels)] if shovels else "SHOVEL_01"
                        try:
                            reroute = self.network.find_shortest_path(dest_node, target)
                            self._assign_new_route(vid, vehicle, reroute)
                        except Exception:
                            vehicle.update_position(road.id, position_s=road.length_m)
                            vehicle.state.speed_v = 0.0

            self._update_vehicle_lateral_offset(vehicle)
            self.state.vehicles[vid] = vehicle.get_state()

        # ----------------------------------------------------------------------
        # 3. SAFETY STEP (v_safe Multi-Constraint Solution & Car-Following)
        # ----------------------------------------------------------------------
        # Group active vehicles by road segment AND direction to compute car-following gaps
        vehicles_by_road: Dict[Tuple[str, str], List[Tuple[str, VehicleState]]] = {}
        for vid, vehicle in self.vehicles.items():
            v_state = vehicle.get_state()
            edge_id = v_state.road_edge
            dir_mode = v_state.lane_or_direction
            key = (edge_id, dir_mode)
            if key not in vehicles_by_road:
                vehicles_by_road[key] = []
            vehicles_by_road[key].append((vid, v_state))

        for (road_id, v_dir), v_list in vehicles_by_road.items():
            road = self.state.roads.get(road_id)
            if not road:
                continue

            # Sort descending by position along road segment (leader first)
            v_list.sort(key=lambda item: item[1].position_s, reverse=True)
            eff_grade_pct = -road.grade_pct if v_dir == "reverse" else road.grade_pct
            grade_rad = math.atan(eff_grade_pct / 100.0)
            mu_safe = self.friction_model.calculate_safe_friction(road.friction_mu, road.friction_sigma)
            c_rr = self.state.environment.default_crr

            for idx, (vid, v_state) in enumerate(v_list):
                # Optical visibility horizon
                r_effective = road.visibility_m

                # Identify if this vehicle is immediately approaching the switchback section (ROAD_04)
                approaching_sb = None
                route = self.vehicle_routes.get(vid, [])
                r_idx = self.vehicle_route_indices.get(vid, 0)
                if r_idx + 2 < len(route):
                    next_u = route[r_idx + 1]
                    next_v = route[r_idx + 2]
                    next_e = self.network.get_edge_data(next_u, next_v)
                    if next_e and (next_e.get("direction_mode") == "single_lane_alternating" or next_e.get("id") == "ROAD_04_SWITCH1_TO_INT2"):
                        approaching_sb = "SWITCHBACK_01"

                # Car-following gap to immediate leader ahead in the same direction on same road
                if idx > 0:
                    leader_vid, leader_state = v_list[idx - 1]
                    dist_to_leader = max(0.0, leader_state.position_s - v_state.position_s - 15.52)
                    r_effective = min(r_effective, dist_to_leader)
                elif approaching_sb:
                    sb_id = approaching_sb
                    coord = self.switchback_coordinators[sb_id]
                    has_other_owner = any(s.status in {"CONFIRMED", "ACTIVE"} and s.vehicle_id != vid for s in coord.active_slots)
                    has_my_slot = any(s.status in {"CONFIRMED", "ACTIVE"} and s.vehicle_id == vid for s in coord.active_slots)

                    if has_other_owner:
                        dist_to_sb = max(0.0, (road.length_m - self.switchback_stop_line_margin) - v_state.position_s)
                        r_effective = min(r_effective, dist_to_sb)
                    elif not has_my_slot and (road.length_m - v_state.position_s <= self.switchback_lookahead_m):
                        # Switchback is clear: leading truck requests slot reservation
                        route = self.vehicle_routes.get(vid, [])
                        r_idx = self.vehicle_route_indices.get(vid, 0)
                        next_edge_len = 250.0
                        next_edge_spd = 8.33
                        direction = "downhill" if eff_grade_pct < 0 else "uphill"
                        if r_idx + 2 < len(route):
                            next_e = self.network.get_edge_data(route[r_idx + 1], route[r_idx + 2])
                            if next_e:
                                next_edge_len = next_e.get("length_m", 250.0)
                                next_edge_spd = next_e.get("speed_limit_mps", 8.33)
                                next_eff_grade = -next_e.get("grade_pct", 0.0) if next_e.get("is_reverse_edge") else next_e.get("grade_pct", 0.0)
                                direction = "downhill" if next_eff_grade < 0 else "uphill"

                        est_dur = max(30.0, (next_edge_len / max(1.0, next_edge_spd)) + 25.0)
                        success, slot, reason = coord.request_reservation(
                            vehicle_id=vid,
                            start_time=self.state.timestamp,
                            duration_seconds=est_dur,
                            direction=direction,
                            is_loaded=v_state.is_loaded
                        )
                        if success and slot:
                            slot.status = "ACTIVE"
                            v_state.target_slot = slot.slot_id
                        else:
                            dist_to_sb = max(0.0, (road.length_m - self.switchback_stop_line_margin) - v_state.position_s)
                            r_effective = min(r_effective, dist_to_sb)

                # Multi-constraint safe speed envelope
                safe_res = self.braking_model.calculate_safe_speed(
                    r_effective=r_effective,
                    grade_rad=grade_rad,
                    mass_kg=v_state.mass_m,
                    mu_safe=mu_safe,
                    curve_radius_m=road.curve_radius_m,
                    speed_limit_mine_mps=road.speed_limit_mps,
                    tau_total=self.braking_model.tau_total_default,
                    c_rr=c_rr,
                    s_margin=5.0
                )
                
                v_safe = safe_res["v_safe"]

                # When approaching switchback with lower safe speed, smoothly adapt safe envelope
                if approaching_sb and (road.length_m - v_state.position_s <= self.switchback_lookahead_m):
                    sb_road_state = self.state.roads.get("ROAD_04_SWITCH1_TO_INT2")
                    if sb_road_state and sb_road_state.safe_speed_mps > 0:
                        v_safe = min(v_safe, max(3.0, sb_road_state.safe_speed_mps))
                
                # Invariant: v_command = min(v_dispatch, v_safe)
                v_dispatch = self.vehicle_target_speeds.get(vid, 11.11)
                v_command = self.braking_model.compute_command_speed(v_dispatch, v_safe)
                v_state.target_speed = v_command

                # Safety Governor Violation Audit
                if v_command > (v_safe + 1e-4):
                    self.state.safety_violations_count += 1
                    self.state.active_alerts.append(
                        AlertEntry(
                            timestamp=self.state.timestamp,
                            level="CRITICAL",
                            source=f"VEHICLE_{vid}",
                            message=f"Safety governor bypassed: v_command={v_command:.2f} > v_safe={v_safe:.2f}"
                        )
                    )

        # ----------------------------------------------------------------------
        # 4. ROAD CAPACITY STEP
        # ----------------------------------------------------------------------
        for road_id, road in self.state.roads.items():
            grade_rad = math.atan(road.grade_pct / 100.0)
            mu_safe = self.friction_model.calculate_safe_friction(road.friction_mu, road.friction_sigma)
            
            safe_res = self.braking_model.calculate_safe_speed(
                r_effective=road.visibility_m,
                grade_rad=grade_rad,
                mass_kg=self.gross_mass,  # Conservative capacity based on gross mass
                mu_safe=mu_safe,
                curve_radius_m=road.curve_radius_m,
                speed_limit_mine_mps=road.speed_limit_mps
            )
            v_safe_road = safe_res["v_safe"]
            a_dec_road = safe_res["a_dec"]
            
            h_safe = self.capacity_model.calculate_safe_headway(v_safe_road, a_dec_road)
            cap_dict = self.capacity_model.calculate_road_capacity(v_safe_road, h_safe)
            
            road.safe_speed_mps = v_safe_road
            road.safe_headway_m = h_safe
            road.capacity_vph = cap_dict["capacity_vph"]

            # Count vehicles currently on this segment
            road.active_vehicles_count = sum(
                1 for v in self.state.vehicles.values() if v.road_edge == road_id
            )

        # ----------------------------------------------------------------------
        # 5. QUEUE STEP
        # ----------------------------------------------------------------------
        for node_id, queue_model in self.queue_models.items():
            node_state = self.state.nodes[node_id]
            
            # Step queue with 0 instantaneous arrivals during steady simulation step
            departures, new_q, blocked = queue_model.step(dt_seconds=dt, arrivals=0.0)
            
            node_state.queue_length = new_q
            node_state.is_blocked = queue_model.is_blocked
            node_state.total_departures += departures
            node_state.total_blocked += blocked

        # ----------------------------------------------------------------------
        # 6. BOTTLENECK STEP (Dynamic Scoring, Ranking & Migration)
        # ----------------------------------------------------------------------
        eval_elements = []
        for node_id, node_state in self.state.nodes.items():
            eval_elements.append({
                "id": node_id,
                "type": "NODE",
                "utilization": node_state.queue_length / max(1.0, node_state.queue_max),
                "queue": node_state.queue_length,
                "criticality": node_state.criticality
            })
        for road_id, road_state in self.state.roads.items():
            flow_approx = road_state.active_vehicles_count * (3600.0 / max(1.0, road_state.safe_headway_m))
            rho_road = flow_approx / max(1.0, road_state.capacity_vph)
            eval_elements.append({
                "id": road_id,
                "type": "ROAD_SEGMENT",
                "utilization": rho_road,
                "queue": float(road_state.active_vehicles_count),
                "criticality": 0.8
            })

        ranked_bottlenecks = self.bottleneck_detector.rank_elements(eval_elements)
        self.state.active_bottlenecks = [
            {
                "id": b.element_id,
                "type": b.element_type,
                "rank": b.rank,
                "score": b.score,
                "utilization": b.utilization_rho,
                "queue": b.queue_length
            }
            for b in ranked_bottlenecks[:5]
        ]

        # Check for bottleneck migration
        migrated, mig_event = self.bottleneck_detector.check_migration(ranked_bottlenecks, timestamp=self.state.timestamp)
        if migrated and mig_event:
            self.state.active_alerts.append(
                AlertEntry(
                    timestamp=self.state.timestamp,
                    level="WARNING",
                    source="BOTTLENECK_DETECTOR",
                    message=mig_event.reason
                )
            )

        # ----------------------------------------------------------------------
        # 7. ARRIVAL SHAPING STEP
        # ----------------------------------------------------------------------
        crushers = self.network.get_nodes_by_type("CRUSHER")
        if crushers:
            crusher_id = crushers[0]
            crusher_node = self.state.nodes.get(crusher_id)
            if crusher_node:
                lambda_safe = self.arrival_shaper.calculate_safe_arrival_rate(crusher_node.service_rate_vph)
                release_interval = self.arrival_shaper.calculate_release_interval(crusher_node.service_rate_vph)

        # ----------------------------------------------------------------------
        # 8. SWITCHBACK STATE STEP
        # ----------------------------------------------------------------------
        for sb_id, coord in self.switchback_coordinators.items():
            for slot in list(coord.active_slots):
                vid = slot.vehicle_id
                veh = self.vehicles.get(vid)
                if veh:
                    v_edge = veh.state.road_edge
                    road_obj = self.state.roads.get(v_edge)
                    is_on_sb = road_obj and (road_obj.direction_mode == "single_lane_alternating" or road_obj.id == "ROAD_04_SWITCH1_TO_INT2")
                    is_approaching = False
                    if not is_on_sb and road_obj:
                        route = self.vehicle_routes.get(vid, [])
                        r_idx = self.vehicle_route_indices.get(vid, 0)
                        if r_idx + 2 < len(route):
                            next_e = self.network.get_edge_data(route[r_idx + 1], route[r_idx + 2])
                            if next_e and (next_e.get("direction_mode") == "single_lane_alternating" or next_e.get("id") == "ROAD_04_SWITCH1_TO_INT2"):
                                is_approaching = True
                    if not is_on_sb and not is_approaching:
                        slot.status = "COMPLETED"
            coord.release_expired_slots(current_time=self.state.timestamp)
            active_slots = coord.get_active_slots()
            # Update road segments with active reservation IDs
            for road in self.state.roads.values():
                if road.from_node == sb_id or road.to_node == sb_id:
                    road.active_slots = [s.slot_id for s in active_slots]

        return self.state

    def run_simulation(self, duration_seconds: float) -> Dict[str, Any]:
        """
        Execute simulation loop from current time until duration_seconds elapsed.
        """
        steps = int(duration_seconds / self.dt_seconds)
        for _ in range(steps):
            self.step()

        return self.state.to_dict()
