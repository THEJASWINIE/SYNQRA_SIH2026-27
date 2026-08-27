"""
Documented interfaces and state schemas for the FOG-ORCHESTRATOR 2.0 Task 2 Digital Twin.
These act as the API contract for the Task-1 HMI and Task-3 telemetry integration.
"""

HMI_STATE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Task 2 Digital Twin HMI State Vector",
    "type": "object",
    "properties": {
        "timestamp": {"type": "number", "description": "Simulation time in seconds"},
        "scenario": {"type": "string", "description": "Active simulation scenario name"},
        "vehicle_states": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "timestamp": {"type": "number"},
                    "position_s": {"type": "number", "description": "Position along edge (m)"},
                    "road_edge": {"type": "string", "description": "Current edge ID"},
                    "speed_v": {"type": "number", "description": "Current velocity (m/s)"},
                    "acceleration_a": {"type": "number", "description": "Current acceleration (m/s^2)"},
                    "mass_m": {"type": "number", "description": "Total vehicle mass (kg)"},
                    "payload": {"type": "number", "description": "Payload weight (kg)"},
                    "is_loaded": {"type": "boolean"},
                    "state": {"type": "string", "enum": ["idle", "traveling", "queued", "loading", "dumping"]},
                    "v_safe": {"type": "number", "description": "Safety speed ceiling (m/s)"},
                    "v_command": {"type": "number", "description": "Commanded speed (m/s)"},
                    "v_dispatch": {"type": "number", "description": "Central target speed (m/s)"},
                    "safe_headway": {"type": "number", "description": "Safe headway distance (m)"},
                    "stop_envelope": {"type": "number", "description": "Stopping distance (m)"},
                    "warning_fault": {"type": "boolean"},
                    "total_tonnes_hauled": {"type": "number"}
                },
                "required": ["id", "timestamp", "position_s", "speed_v", "mass_m", "v_safe", "v_command", "state"]
            }
        },
        "road_states": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "road_id": {"type": "string"},
                    "start_node": {"type": "string"},
                    "end_node": {"type": "string"},
                    "length_m": {"type": "number"},
                    "grade_pct": {"type": "number"},
                    "curve_radius_m": {"type": "number"},
                    "visibility_m": {"type": "number"},
                    "friction_mu": {"type": "number"},
                    "safe_speed_mps": {"type": "number"},
                    "safe_headway_m": {"type": "number"},
                    "capacity_vph": {"type": "number"},
                    "queue_count": {"type": "integer"},
                    "vehicles_present": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["road_id", "length_m", "visibility_m", "friction_mu", "safe_speed_mps", "capacity_vph"]
            }
        },
        "node_states": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "type": {"type": "string"},
                    "service_rate_vph": {"type": "number"},
                    "queue_length": {"type": "integer"},
                    "criticality": {"type": "number"}
                },
                "required": ["node_id", "type", "service_rate_vph", "queue_length"]
            }
        },
        "control_state": {
            "type": "object",
            "properties": {
                "arrival_shaping_active": {"type": "boolean"},
                "shovel_release_delay_s": {"type": "number"}
            },
            "required": ["arrival_shaping_active", "shovel_release_delay_s"]
        },
        "warning_fault": {"type": "boolean"}
    },
    "required": ["timestamp", "scenario", "vehicle_states", "road_states", "node_states", "control_state", "warning_fault"]
}

VEHICLE_TELEMETRY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Task 3 Inbound Telemetry State from ESP32",
    "type": "object",
    "properties": {
        "vehicle_id": {"type": "string"},
        "timestamp": {"type": "number"},
        "speed_mps": {"type": "number"},
        "acceleration_mps2": {"type": "number"},
        "position_gps": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"}
            }
        },
        "heading_rad": {"type": "number"},
        "grade_rad": {"type": "number"},
        "brake_state": {"type": "boolean", "description": "True if brakes are engaged"},
        "retarder_state": {"type": "boolean", "description": "True if retarder is engaged"},
        "comm_confidence": {"type": "number", "description": "0.0 to 1.0 packet success rate"}
    },
    "required": ["vehicle_id", "timestamp", "speed_mps", "brake_state"]
}
