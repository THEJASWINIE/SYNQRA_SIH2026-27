import json
from jsonschema import validate
from interfaces.task2_state_schema import VEHICLE_TELEMETRY_SCHEMA

class TelemetryAdapter:
    """
    Ingests and parses inbound Task-3 telemetry packets from physical ESP32 controllers.
    Synchronizes physical vehicle states with the Digital Twin simulator representation.
    """
    def __init__(self, simulator, stale_threshold_s: float = 5.0):
        self.sim = simulator
        self.stale_threshold_s = stale_threshold_s
        self.last_telemetry_timestamps = {}

    def ingest_telemetry(self, telemetry_json: str) -> bool:
        """
        Parse and validate a Task-3 telemetry JSON packet.
        Updates the corresponding simulator vehicle's state variables.
        """
        try:
            telemetry = json.loads(telemetry_json)
            # Validate schema contract
            validate(instance=telemetry, schema=VEHICLE_TELEMETRY_SCHEMA)
            
            vehicle_id = telemetry["vehicle_id"]
            timestamp = telemetry["timestamp"]
            
            # Find the vehicle in the simulator fleet
            vehicle = next((v for v in self.sim.vehicles if v.id == vehicle_id), None)
            if not vehicle:
                return False
                
            # Update telemetry timestamp and check staleness
            self.last_telemetry_timestamps[vehicle_id] = timestamp
            
            # Apply physical state updates to the vehicle model
            vehicle.speed_mps = float(telemetry["speed_mps"])
            if "acceleration_mps2" in telemetry:
                vehicle.acceleration_mps2 = float(telemetry["acceleration_mps2"])
                
            # Simulate GPS location mapping to road coordinate if traveling
            if "heading_rad" in telemetry:
                vehicle.heading_rad = float(telemetry["heading_rad"])
                
            # Enforce local brake states
            if telemetry["brake_state"]:
                vehicle.state = "idle" if vehicle.speed_mps <= 0.1 else "traveling"
                
            # Update comm confidence
            comm_confidence = float(telemetry.get("comm_confidence", 1.0))
            setattr(vehicle, "comm_confidence", comm_confidence)
            
            return True
            
        except Exception as e:
            # Schema validation error or parse error
            return False

    def verify_communication_liveness(self, current_sim_time: float) -> list[str]:
        """
        Check for telemetry staleness across all vehicles in the fleet.
        Returns a list of vehicle IDs that are currently stale/unresponsive.
        """
        stale_vehicles = []
        for v in self.sim.vehicles:
            last_t = self.last_telemetry_timestamps.get(v.id, 0.0)
            if last_t > 0.0 and (current_sim_time - last_t) > self.stale_threshold_s:
                stale_vehicles.append(v.id)
                if v.v_safe_mps > 0.0:
                    v.v_safe_mps = min(v.v_safe_mps, 2.78)
                else:
                    v.v_safe_mps = 2.78
                setattr(v, "comm_loss_active", True)
        return stale_vehicles
