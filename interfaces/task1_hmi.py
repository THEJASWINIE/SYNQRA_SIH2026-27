import json
from jsonschema import validate
from interfaces.task2_state_schema import HMI_STATE_SCHEMA

class HMIInterface:
    """
    Exposes the compiled digital-twin state vector to the Task-1 HMI.
    Validates state against the schema contract to guarantee formatting consistency.
    """
    @staticmethod
    def package_hmi_state(timestamp: float, scenario_name: str, network, vehicles, 
                           shaping_active: bool, shovel_delay: float) -> dict:
        # 1. Compile vehicle states
        vehicle_states = []
        for v in vehicles:
            vehicle_states.append({
                "id": v.id,
                "timestamp": timestamp,
                "position_s": float(v.position_s),
                "road_edge": v.current_edge if v.current_edge else "",
                "speed_v": float(v.speed_mps),
                "acceleration_a": float(v.acceleration_mps2),
                "mass_m": float(v.mass_kg),
                "payload": float(v.mass_kg - 74000.0) if v.is_loaded else 0.0,
                "is_loaded": v.is_loaded,
                "state": "queued" if v.state == "waiting_for_release" else v.state,
                "v_safe": float(v.v_safe_mps),
                "v_command": float(v.v_command_mps),
                "v_dispatch": float(getattr(v, "v_dispatch_mps", v.speed_mps)),
                "safe_headway": float(getattr(v, "safe_headway_m", 15.5)),
                "stop_envelope": float(getattr(v, "stop_envelope_m", 0.0)),
                "warning_fault": False,
                "total_tonnes_hauled": float(getattr(v, "total_tonnes_hauled", 0.0))
            })
            
        # 2. Compile road states
        road_states = []
        for edge_id, edge in network.edges.items():
            road_states.append({
                "road_id": edge_id,
                "start_node": edge.start_node,
                "end_node": edge.end_node,
                "length_m": float(edge.length_m),
                "grade_pct": float(edge.grade_percent),
                "curve_radius_m": float(edge.curve_radius_m),
                "visibility_m": float(edge.visibility_m),
                "friction_mu": float(edge.friction_mu),
                "safe_speed_mps": float(edge.v_safe_mps),
                "safe_headway_m": float(edge.v_safe_mps * 0.25 + 15.5), # approximation
                "capacity_vph": float(edge.capacity_vph),
                "queue_count": len(edge.vehicles),
                "vehicles_present": [v.id for v in edge.vehicles]
            })
            
        # 3. Compile node states
        node_states = []
        for node_id, node in network.nodes.items():
            node_states.append({
                "node_id": node_id,
                "type": node.type,
                "service_rate_vph": float(node.service_rate_vph),
                "queue_length": int(node.queue.length) if node.queue is not None else 0,
                "criticality": float(getattr(node, "criticality", 1.0))
            })
            
        # 4. Compile control state
        control_state = {
            "arrival_shaping_active": bool(shaping_active),
            "shovel_release_delay_s": float(shovel_delay)
        }
        
        # 5. Short-horizon predictions (FTR-024)
        trajectory_predictions = []
        for v in vehicles:
            # Extrapolate positions for next 3 steps (e.g. 10s, 20s, 30s)
            future_pos = [float(v.position_s + v.speed_mps * 10.0 * k) for k in [1, 2, 3]]
            trajectory_predictions.append({
                "vehicle_id": v.id,
                "future_positions": future_pos
            })
            
        crusher_node = network.nodes.get("CRUSHER")
        crusher_q = crusher_node.queue.length if crusher_node and crusher_node.queue else 0
        crusher_service = crusher_node.service_rate_vph if crusher_node else 10.0
        # Simple queue prediction extrapolation
        q_pred = [float(max(0.0, crusher_q + (15.0 - crusher_service)/3600.0 * 10.0 * k)) for k in [1, 2, 3]]
        
        total_tonnes = sum(getattr(v, "total_tonnes_hauled", 0.0) for v in vehicles)
        predictions = {
            "trajectory_predictions": trajectory_predictions,
            "predicted_crusher_queue": q_pred,
            "predicted_production_tonnes": float(total_tonnes)
        }
        
        state_vector = {
            "timestamp": timestamp,
            "scenario": scenario_name,
            "vehicle_states": vehicle_states,
            "road_states": road_states,
            "node_states": node_states,
            "control_state": control_state,
            "predictions": predictions,
            "warning_fault": False
        }
        
        # Validate against schema contract
        validate(instance=state_vector, schema=HMI_STATE_SCHEMA)
        
        return state_vector
