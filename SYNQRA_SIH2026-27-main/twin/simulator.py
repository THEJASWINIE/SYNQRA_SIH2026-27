from models.vehicle_physics import resolve_v_safe, calculate_acceleration
from models.road_capacity import calculate_road_capacity
from models.braking import calculate_stopping_distance
from control.arrival_shaping import ArrivalShaper
from weather.fog_model import FogModel
from twin.state import TwinState
import numpy as np

class Simulator:
    """
    Coordinates the FOG-ORCHESTRATOR 2.0 digital twin simulation.
    Manages the step-by-step state propagation of weather, physics, queues, and arrival shaping.
    """
    def __init__(self, network, vehicle_config: dict, weather_config: dict, scenario_config: dict):
        self.network = network
        self.vehicle_config = vehicle_config
        self.weather_config = weather_config
        self.scenario_config = scenario_config
        
        self.dt = scenario_config["timestep_s"]
        self.current_time = 0.0
        self.shaping_active = False
        
        # Initialize weather and forecast models
        self.fog_model = FogModel(weather_config)
        from weather.forecast_model import ForecastModel
        self.forecast_model = ForecastModel(horizon_s=1800.0, step_s=10.0)
        
        # Initialize arrival shaper and optimization mode
        self.arrival_shaper = ArrivalShaper("CRUSHER", self.network.nodes["SHOVEL"].service_rate_vph)
        self.optimization_mode = scenario_config.get("optimization_mode", "baseline")
        self.last_shovel_release_time = -999.0
        self.shovel_departure_buffer = []  # Loaded vehicles waiting for release
        
        # Initialize switchback coordinator
        from models.switchback import SwitchbackCoordinator
        self.switchback_coordinator = SwitchbackCoordinator(priority_policy="stopping_difficulty")
        self.intersection_pending_releases = {}
        
        # Create fleet of vehicles
        self.vehicles = []
        self.fleet_size = scenario_config["fleet_size"]
        for i in range(self.fleet_size):
            # Stagger trucks at shovel initially
            v_id = f"TRUCK_{i+1:02d}"
            # Put them in the shovel queue to start
            vehicle = self.vehicles_list_init(v_id)
            self.vehicles.append(vehicle)
            self.network.nodes["SHOVEL"].queue.add_vehicle(vehicle)
            
        # Log history for results
        self.state_history = []
        
    def vehicles_list_init(self, v_id: str):
        from models.vehicle import Vehicle
        return Vehicle(v_id, self.vehicle_config, "SHOVEL")

    def run_step(self):
        """Advance the simulation by dt seconds."""
        # 1. Update weather states
        self.fog_model.update(self.current_time)
        
        # 2. Update environmental and capacity states on road edges
        for edge_id, edge in self.network.edges.items():
            edge.visibility_m = self.fog_model.current_visibility
            edge.friction_mu = self.fog_model.current_friction
            edge.c_rr = self.fog_model.current_rr
            edge.surface_state = self.fog_model.current_state
            
            # Compute a representative safe speed and headway to evaluate road capacity
            # Using loaded mass for ROAD_1 & ROAD_2, empty mass for ROAD_RETURN
            rep_mass = self.vehicle_config["tare_mass_kg"]
            if edge_id in ["ROAD_1", "ROAD_2"]:
                rep_mass += self.vehicle_config["payload_mass_kg"]
                
            phys_res = resolve_v_safe(
                mass_kg=rep_mass,
                grade_percent=edge.grade_percent,
                friction_mu=edge.friction_mu,
                c_rr=edge.c_rr,
                hardware_max_brake_n=self.vehicle_config["hardware_max_brake_force_n"],
                max_retarder_power_w=self.vehicle_config["max_retarder_power_w"],
                curve_radius_m=edge.curve_radius_m,
                traction_speed_factor_mps=self.vehicle_config["traction_speed_factor_mps"],
                speed_limit_mps=edge.speed_limit_mps,
                visibility_m=edge.visibility_m,
                tau_total=self.vehicle_config["ecu_hydraulic_latency_s"],
                s_margin=self.vehicle_config["safety_stop_margin_m"]
            )
            edge.v_safe_mps = phys_res["v_safe"]
            edge.safe_headway_m = max(
                calculate_stopping_distance(edge.v_safe_mps, phys_res["a_dec"], self.vehicle_config["ecu_hydraulic_latency_s"]) + self.vehicle_config["safety_headway_margin_m"],
                self.vehicle_config["min_static_headway_m"]
            )
            edge.capacity_vph = calculate_road_capacity(edge.v_safe_mps, edge.safe_headway_m, self.vehicle_config["min_static_headway_m"])

        # 3. Update arrival-rate shaper (Tier 3)
        crusher_queue_len = self.network.nodes["CRUSHER"].queue.length
        crusher_service_rate = self.network.nodes["CRUSHER"].service_rate_vph
        
        # Check if we should re-optimize (every 10 seconds or at first step)
        if not hasattr(self, "_cached_shovel_delay") or (int(self.current_time) % 10 == 0):
            if self.optimization_mode == "baseline":
                self._cached_shovel_delay = self.arrival_shaper.update_release_delay(
                    shaping_active=self.shaping_active,
                    downstream_queue_len=crusher_queue_len,
                    downstream_service_rate_vph=crusher_service_rate,
                    delta_buffer_vph=self.scenario_config.get("delta_buffer_vph", 2.0)
                )
            elif self.optimization_mode == "deterministic_mpc":
                from optimizer.milp_dispatch import DeterministicMPC
                mpc = DeterministicMPC(
                    horizon_s=1800.0, step_s=10.0, 
                    crusher_service_rate_vph=crusher_service_rate,
                    shovel_service_rate_vph=self.network.nodes["SHOVEL"].service_rate_vph,
                    vehicle_config=self.vehicle_config,
                    road_config={
                        "grade_percent": -8.0, "friction_mu": self.network.edges["ROAD_2"].friction_mu, 
                        "c_rr": self.network.edges["ROAD_2"].c_rr, 
                        "curve_radius_m": 50.0, "speed_limit_mps": 11.11
                    }
                )
                forecast = self.forecast_model.generate_forecast(
                    self.current_time, self.network.edges["ROAD_2"].visibility_m, self.scenario_config.get("name", "demo_06")
                )
                self._cached_shovel_delay = mpc.optimize_release_rate(crusher_queue_len, forecast)
                
            elif self.optimization_mode == "robust_mpc":
                from optimizer.robust_mpc import RobustMPC
                mpc = RobustMPC(
                    horizon_s=1800.0, step_s=10.0, 
                    crusher_service_rate_vph=crusher_service_rate,
                    shovel_service_rate_vph=self.network.nodes["SHOVEL"].service_rate_vph,
                    vehicle_config=self.vehicle_config,
                    road_config={
                        "grade_percent": -8.0, "friction_mu": self.network.edges["ROAD_2"].friction_mu, 
                        "c_rr": self.network.edges["ROAD_2"].c_rr, 
                        "curve_radius_m": 50.0, "speed_limit_mps": 11.11
                    }
                )
                # Generate 3 scenarios (nominal, -20% fog, +20% fog)
                forecast_nominal = self.forecast_model.generate_forecast(
                    self.current_time, self.network.edges["ROAD_2"].visibility_m, self.scenario_config.get("name", "demo_06"), error_pct=0.0
                )
                forecast_low = self.forecast_model.generate_forecast(
                    self.current_time, self.network.edges["ROAD_2"].visibility_m, self.scenario_config.get("name", "demo_06"), error_pct=-0.2
                )
                forecast_high = self.forecast_model.generate_forecast(
                    self.current_time, self.network.edges["ROAD_2"].visibility_m, self.scenario_config.get("name", "demo_06"), error_pct=0.2
                )
                scenarios = np.vstack([forecast_nominal, forecast_low, forecast_high])
                self._cached_shovel_delay = mpc.optimize_release_rate(crusher_queue_len, scenarios)
                
            elif self.optimization_mode == "chance_mpc":
                from optimizer.chance_mpc import ChanceConstrainedMPC
                mpc = ChanceConstrainedMPC(
                    horizon_s=1800.0, step_s=10.0, 
                    crusher_service_rate_vph=crusher_service_rate,
                    shovel_service_rate_vph=self.network.nodes["SHOVEL"].service_rate_vph,
                    vehicle_config=self.vehicle_config,
                    road_config={
                        "grade_percent": -8.0, "friction_mu": self.network.edges["ROAD_2"].friction_mu, 
                        "c_rr": self.network.edges["ROAD_2"].c_rr, 
                        "curve_radius_m": 50.0, "speed_limit_mps": 11.11
                    },
                    confidence_level=0.95
                )
                forecast = self.forecast_model.generate_forecast(
                    self.current_time, self.network.edges["ROAD_2"].visibility_m, self.scenario_config.get("name", "demo_06")
                )
                # Standard deviation of visibility forecast is 5.0m
                self._cached_shovel_delay = mpc.optimize_release_rate(crusher_queue_len, forecast, forecast_uncertainty_std=5.0)
            else:
                self._cached_shovel_delay = 240.0
                
        active_shovel_delay = self._cached_shovel_delay

        # 4. Process node queues (Shovel and Crusher)
        # Shovel loading queue
        shovel_discharged = self.network.nodes["SHOVEL"].queue.step(self.dt)
        for v in shovel_discharged:
            v.state = "waiting_for_release"
            v.current_node = "SHOVEL"
            self.shovel_departure_buffer.append(v)
            
        # Crusher unloading queue
        crusher_discharged = self.network.nodes["CRUSHER"].queue.step(self.dt)
        for v in crusher_discharged:
            # Send immediately onto ROAD_RETURN
            v.state = "traveling"
            v.current_edge = "ROAD_RETURN"
            v.position_s = 0.0
            v.current_node = None
            self.network.edges["ROAD_RETURN"].vehicles.append(v)

        # 5. Process Shovel Release Buffer (Arrival Shaping Execution)
        if self.shovel_departure_buffer:
            if self.current_time >= self.last_shovel_release_time + active_shovel_delay:
                # Release the front vehicle
                v = self.shovel_departure_buffer.pop(0)
                v.state = "traveling"
                v.current_edge = "ROAD_1"
                v.position_s = 0.0
                v.current_node = None
                self.network.edges["ROAD_1"].vehicles.append(v)
                self.last_shovel_release_time = self.current_time

        # 6. Process Intersection queue (Switchback slot coordinator)
        intersection_node = self.network.nodes["INTERSECTION"]
        released_from_intersection = []
        for v in list(intersection_node.queue.vehicles):
            release_t = self.intersection_pending_releases.get(v.id, 0.0)
            if self.current_time >= release_t:
                # Release vehicle from queue onto ROAD_2
                intersection_node.queue.vehicles.remove(v)
                v.state = "traveling"
                v.current_edge = "ROAD_2"
                v.position_s = 0.0
                v.current_node = None
                self.network.edges["ROAD_2"].vehicles.append(v)
                released_from_intersection.append(v.id)
                
        for vid in released_from_intersection:
            if vid in self.intersection_pending_releases:
                del self.intersection_pending_releases[vid]

        # 7. Update traveling vehicles physics and positions
        for edge_id, edge in self.network.edges.items():
            # Sort vehicles on this edge by position (descending: closest to end is first)
            edge.vehicles.sort(key=lambda x: x.position_s, reverse=True)
            
            for idx, v in enumerate(edge.vehicles):
                # Calculate vehicle-specific safe speed bounds
                phys_res = resolve_v_safe(
                    mass_kg=v.mass_kg,
                    grade_percent=edge.grade_percent,
                    friction_mu=edge.friction_mu,
                    c_rr=edge.c_rr,
                    hardware_max_brake_n=self.vehicle_config["hardware_max_brake_force_n"],
                    max_retarder_power_w=self.vehicle_config["max_retarder_power_w"],
                    curve_radius_m=edge.curve_radius_m,
                    traction_speed_factor_mps=self.vehicle_config["traction_speed_factor_mps"],
                    speed_limit_mps=edge.speed_limit_mps,
                    visibility_m=edge.visibility_m,
                    tau_total=self.vehicle_config["ecu_hydraulic_latency_s"],
                    s_margin=self.vehicle_config["safety_stop_margin_m"]
                )
                
                v.v_safe_mps = phys_res["v_safe"]
                v.stop_envelope_m = phys_res["v_safe"] * self.vehicle_config["ecu_hydraulic_latency_s"] + (phys_res["v_safe"]**2) / (2.0 * max(0.1, phys_res["a_dec"]))
                v.safe_headway_m = max(v.stop_envelope_m + self.vehicle_config["safety_headway_margin_m"], self.vehicle_config["min_static_headway_m"])
                
                # Default dispatch speed is speed limit
                v.v_dispatch_mps = edge.speed_limit_mps
                
                # Apply car-following logic to prevent collisions on the road segment
                if idx > 0:
                    front_v = edge.vehicles[idx - 1]
                    gap = front_v.position_s - v.position_s - front_v.length
                    # Adjust dispatch speed to maintain safe headway
                    min_h = self.vehicle_config["min_static_headway_m"]
                    if gap <= min_h:
                        v.v_dispatch_mps = 0.0
                    elif gap < v.safe_headway_m:
                        # Scale speed down proportionally
                        ratio = (gap - min_h) / (v.safe_headway_m - min_h)
                        v.v_dispatch_mps = min(v.v_dispatch_mps, front_v.speed_mps * ratio)
                
                if self.scenario_config.get("local_governor_active", True):
                    v.v_command_mps = min(v.v_dispatch_mps, v.v_safe_mps)
                else:
                    v.v_command_mps = v.v_dispatch_mps
                
                # Force updates based on target speed tracking
                if v.speed_mps < v.v_command_mps:
                    # Accelerate using engine drive force up to traction limit
                    F_mu = edge.friction_mu * v.mass_kg * 9.81 * np.cos(np.arctan(edge.grade_percent/100.0))
                    # Assume typical diesel-electric drive force
                    F_drive = min(150000.0, F_mu)
                    acc = calculate_acceleration(
                        v.mass_kg, edge.grade_percent, v.speed_mps,
                        F_drive, 0.0, 0.0, edge.c_rr, edge.friction_mu,
                        self.vehicle_config["drag_coefficient_cd"],
                        self.vehicle_config["cross_sectional_area_a_m2"],
                        self.vehicle_config["air_density_rho_kg_m3"]
                    )
                    v.speed_mps = min(v.v_command_mps, v.speed_mps + acc * self.dt)
                    v.acceleration_mps2 = acc
                elif v.speed_mps > v.v_command_mps:
                    # Decelerate using brakes
                    a_dec = phys_res["a_dec"]
                    v.speed_mps = max(v.v_command_mps, v.speed_mps - a_dec * self.dt)
                    v.acceleration_mps2 = -a_dec
                else:
                    v.acceleration_mps2 = 0.0
                
                # Update position
                v.position_s += v.speed_mps * self.dt
                
        # 8. Handle boundary transitions (vehicles arriving at node intersections)
        for edge_id, edge in list(self.network.edges.items()):
            # Find vehicles that have traversed past the edge length
            arrived_vehicles = [v for v in edge.vehicles if v.position_s >= edge.length_m]
            
            for v in arrived_vehicles:
                # Remove from traveling list
                edge.vehicles.remove(v)
                v.position_s = 0.0
                
                # Routing logic
                if edge.end_node == "INTERSECTION":
                    if self.scenario_config.get("slot_reservation_active", True):
                        # Check Switchback Coordinator slot reservation
                        v_safe = self.network.edges["ROAD_2"].v_safe_mps
                        duration = self.network.edges["ROAD_2"].length_m / max(1.0, v_safe)
                        t_start = self.current_time
                        t_end = self.current_time + duration
                        
                        approved, suggested_start = self.switchback_coordinator.request_slot(
                            node_id="INTERSECTION",
                            t_start=t_start,
                            t_end=t_end,
                            vehicle_id=v.id,
                            is_loaded=v.is_loaded,
                            grade_percent=self.network.edges["ROAD_2"].grade_percent,
                            speed_mps=v.speed_mps,
                            mass_kg=v.mass_kg
                        )
                        
                        if approved:
                            v.state = "traveling"
                            v.current_edge = "ROAD_2"
                            v.position_s = 0.0
                            v.current_node = None
                            self.network.edges["ROAD_2"].vehicles.append(v)
                        else:
                            v.state = "queued"
                            v.current_node = "INTERSECTION"
                            self.network.nodes["INTERSECTION"].queue.add_vehicle(v)
                            self.intersection_pending_releases[v.id] = suggested_start
                    else:
                        # Instant pass-through (ablation mode)
                        v.state = "traveling"
                        v.current_edge = "ROAD_2"
                        v.position_s = 0.0
                        v.current_node = None
                        self.network.edges["ROAD_2"].vehicles.append(v)
                elif edge.end_node == "CRUSHER":
                    # Enter crusher queue
                    self.network.nodes["CRUSHER"].queue.add_vehicle(v)
                elif edge.end_node == "SHOVEL":
                    # Enter shovel queue
                    self.network.nodes["SHOVEL"].queue.add_vehicle(v)

        # 9. Record current state vector
        current_state = TwinState.compile_state(
            timestamp=self.current_time,
            network=self.network,
            vehicles=self.vehicles,
            scenario_name=self.fog_model.scenario_name,
            arrival_shaping_active=self.shaping_active,
            shovel_delay=active_shovel_delay
        )
        self.state_history.append(current_state)
        
        # 10. Advance simulation time
        self.current_time += self.dt
