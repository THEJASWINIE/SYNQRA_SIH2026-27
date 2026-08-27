class FogModel:
    """
    Manages spatiotemporal visibility and friction values during the simulation.
    Handles static clear/fog scenarios and dynamic fog recovery transitions.
    """
    def __init__(self, config: dict):
        self.scenarios = config["scenarios"]
        self.current_visibility = 50.0
        self.current_friction = 0.60
        self.current_rr = 0.02
        self.current_state = "dry"
        self.scenario_name = "clear"

    def set_scenario(self, scenario_name: str):
        self.scenario_name = scenario_name
        if scenario_name in ["clear", "dense_fog", "extreme_fog"]:
            s_cfg = self.scenarios[scenario_name]
            self.current_visibility = s_cfg["visibility_m"]
            self.current_friction = s_cfg["friction_mu"]
            self.current_rr = s_cfg["rolling_resistance_crr"]
            self.current_state = s_cfg["surface_state"]
        elif scenario_name == "fog_recovery":
            s_cfg = self.scenarios["fog_recovery"]
            self.current_visibility = s_cfg["initial_visibility_m"]
            self.current_friction = s_cfg["initial_friction_mu"]
            self.current_rr = self.scenarios["dense_fog"]["rolling_resistance_crr"]
            self.current_state = self.scenarios["dense_fog"]["surface_state"]

    def update(self, t_seconds: float):
        """
        Updates visibility and friction over time.
        In fog_recovery, visibility linearly increases from 15m to 50m.
        Friction linearly increases from 0.25 to 0.60.
        """
        if self.scenario_name == "fog_recovery":
            s_cfg = self.scenarios["fog_recovery"]
            t_start = s_cfg["transition_start_s"]
            t_dur = s_cfg["transition_duration_s"]
            
            if t_seconds < t_start:
                # Pre-recovery: still dense fog
                self.current_visibility = s_cfg["initial_visibility_m"]
                self.current_friction = s_cfg["initial_friction_mu"]
                self.current_rr = self.scenarios["dense_fog"]["rolling_resistance_crr"]
                self.current_state = self.scenarios["dense_fog"]["surface_state"]
            elif t_seconds >= t_start + t_dur:
                # Post-recovery: fully clear
                self.current_visibility = s_cfg["target_visibility_m"]
                self.current_friction = s_cfg["target_friction_mu"]
                self.current_rr = self.scenarios["clear"]["rolling_resistance_crr"]
                self.current_state = self.scenarios["clear"]["surface_state"]
            else:
                # Active recovery transition (linear interpolation)
                fraction = (t_seconds - t_start) / t_dur
                
                v_diff = s_cfg["target_visibility_m"] - s_cfg["initial_visibility_m"]
                mu_diff = s_cfg["target_friction_mu"] - s_cfg["initial_friction_mu"]
                
                self.current_visibility = s_cfg["initial_visibility_m"] + fraction * v_diff
                self.current_friction = s_cfg["initial_friction_mu"] + fraction * mu_diff
                
                rr_dense = self.scenarios["dense_fog"]["rolling_resistance_crr"]
                rr_clear = self.scenarios["clear"]["rolling_resistance_crr"]
                self.current_rr = rr_dense + fraction * (rr_clear - rr_dense)
                self.current_state = "damp" if fraction < 0.5 else "dry"
