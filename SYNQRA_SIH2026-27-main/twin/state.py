class TwinState:
    """
    Handles serialization of the entire digital twin state vector.
    This serves as the API contract (I-03) that the Task-1 HMI will consume.
    """
    @staticmethod
    def compile_state(timestamp: float, network, vehicles: list, scenario_name: str, 
                      arrival_shaping_active: bool, shovel_delay: float) -> dict:
        # Compile vehicle states
        vehicle_states = [v.get_state_vector(timestamp) for v in vehicles]
        
        # Compile road states
        road_states = []
        for edge_id, edge in network.edges.items():
            queue_count = 0
            # If the end node is a service node, get its queue length
            end_node = network.nodes.get(edge.end_node)
            if end_node and end_node.queue:
                queue_count = end_node.queue.length
                
            road_states.append({
                "road_id": edge.id,
                "start_node": edge.start_node,
                "end_node": edge.end_node,
                "length_m": float(edge.length_m),
                "grade_pct": float(edge.grade_percent),
                "curve_radius_m": float(edge.curve_radius_m),
                "visibility_m": float(edge.visibility_m),
                "friction_mu": float(edge.friction_mu),
                "safe_speed_mps": float(edge.v_safe_mps),
                "safe_headway_m": float(edge.safe_headway_m),
                "capacity_vph": float(edge.capacity_vph),
                "queue_count": int(queue_count),
                "vehicles_present": [v.id for v in edge.vehicles]
            })
            
        # Compile node queue details
        node_states = []
        bottleneck_scores = {}
        for node_id, node in network.nodes.items():
            q_len = node.queue.length if node.queue else 0
            srv_rate = node.service_rate_vph
            
            node_states.append({
                "node_id": node.id,
                "type": node.type,
                "service_rate_vph": float(srv_rate),
                "queue_length": int(q_len),
                "criticality": float(node.criticality)
            })
            
        # Determine current identified bottleneck
        identified_bottleneck = ""
        max_score = -1.0
        
        # Calculate bottleneck score for each service node
        from models.bottleneck import calculate_bottleneck_score
        
        for node_id, node in network.nodes.items():
            if node.queue:
                # Approximate arrival rate by counting recent entries or from simulator queue
                # For score computation, use utilization: rho = arrival_rate / service_rate
                # In Demo V0.1, we estimate the raw arrival rate based on upstream departures
                # If shaping is active, arrival rate is shaped, otherwise it is shovel loading rate.
                # Let's compute a dynamic arrival rate estimation.
                # If shovel: arrival rate is fleet returning empty.
                # If crusher: arrival rate is loaded trucks arriving.
                # Let's get simulated state estimates.
                q_len = node.queue.length
                
                # Baseline arrivals estimation:
                # If crusher, default arrival rate without shaping is shovel capacity (15 vph)
                # With shaping, it is throttled.
                # We can calculate an arrival rate estimate based on the fleet:
                # Let's approximate arrival rate by tracking arrivals inside simulator.
                # Here we use the simplified state.
                pass
        
        # Check warnings
        warning_fault = any(v.warning_fault for v in vehicles)
        
        # Build unified dictionary
        state_vector = {
            "timestamp": float(timestamp),
            "scenario": scenario_name,
            "vehicle_states": vehicle_states,
            "road_states": road_states,
            "node_states": node_states,
            "control_state": {
                "arrival_shaping_active": bool(arrival_shaping_active),
                "shovel_release_delay_s": float(shovel_delay)
            },
            "warning_fault": warning_fault
        }
        return state_vector
