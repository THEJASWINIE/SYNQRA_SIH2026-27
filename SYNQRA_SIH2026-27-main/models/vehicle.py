class Vehicle:
    """
    Represents a virtual mining truck (BEML BH100-class).
    Tracks positions, states, mass changes, and controller targets.
    """
    def __init__(self, vehicle_id: str, config: dict, initial_node: str):
        self.id = vehicle_id
        
        # Load from config (REFERENCE parameters)
        self.tare_mass = config["tare_mass_kg"]
        self.payload_capacity = config["payload_mass_kg"]
        self.length = config["length_m"]
        self.width = config["width_m"]
        self.wheelbase = config["wheelbase_m"]
        
        # Dynamic states
        self.position_s = 0.0          # meters from start of road edge
        self.current_edge = None       # ID of current road segment (if traveling)
        self.speed_mps = 0.0
        self.acceleration_mps2 = 0.0
        self.payload_kg = 0.0          # Current cargo weight
        self.mass_kg = self.tare_mass  # Total mass (tare + payload)
        self.is_loaded = False
        
        # Location/Operational states
        self.current_node = initial_node  # ID of node if parked/queued/loading
        self.state = "idle"            # "idle", "traveling", "queued", "loading", "dumping"
        
        # Speed targets
        self.v_safe_mps = 0.0          # Tier-1 safe speed
        self.v_dispatch_mps = 0.0      # Tier-3 dispatch target speed
        self.v_command_mps = 0.0       # Final commanded speed = min(v_dispatch, v_safe)
        
        # Diagnostics
        self.warning_fault = False     # Fault indicator (e.g. if safe speed calculation fails)
        self.stop_envelope_m = 0.0     # stopping distance S_stop
        self.safe_headway_m = 0.0      # safe headway H_safe
        
        # Performance KPIs
        self.time_in_state = 0.0
        self.total_tonnes_hauled = 0.0

    def get_state_vector(self, timestamp: float) -> dict:
        """
        Produce state dictionary for HMI and JSON summaries.
        """
        return {
            "id": self.id,
            "timestamp": timestamp,
            "position_s": float(self.position_s),
            "road_edge": self.current_edge if self.current_edge else "",
            "speed_v": float(self.speed_mps),
            "acceleration_a": float(self.acceleration_mps2),
            "mass_m": float(self.mass_kg),
            "payload": float(self.payload_kg),
            "is_loaded": self.is_loaded,
            "state": "queued" if self.state == "waiting_for_release" else self.state,
            "v_safe": float(self.v_safe_mps),
            "v_command": float(self.v_command_mps),
            "v_dispatch": float(self.v_dispatch_mps),
            "safe_headway": float(self.safe_headway_m),
            "stop_envelope": float(self.stop_envelope_m),
            "warning_fault": self.warning_fault,
            "total_tonnes_hauled": float(self.total_tonnes_hauled)
        }

    def load_cargo(self):
        """Load truck to full rated capacity (mass transition)."""
        self.is_loaded = True
        self.payload_kg = self.payload_capacity
        self.mass_kg = self.tare_mass + self.payload_kg

    def unload_cargo(self):
        """Unload truck (mass transition) and record performance tonnage."""
        if self.is_loaded:
            self.total_tonnes_hauled += self.payload_capacity / 1000.0  # converted to metric tonnes
        self.is_loaded = False
        self.payload_kg = 0.0
        self.mass_kg = self.tare_mass
