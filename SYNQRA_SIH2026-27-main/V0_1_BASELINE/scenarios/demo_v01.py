from twin.simulator import Simulator
from twin.network import MineNetwork
import copy

def run_scenario(scenario_name: str, base_network: MineNetwork, vehicle_config: dict, 
                 weather_config: dict, scenario_config: dict) -> list:
    """
    Executes a specific simulation scenario and returns the detailed step history.
    """
    # Create an independent copy of the network to prevent scenario cross-pollution
    network = copy.deepcopy(base_network)
    
    # 1. Handle scenario-specific overrides
    shaping_active = False
    crusher_rate_vph = 18.0  # baseline
    
    if scenario_name == "DEMO_01_CLEAR":
        weather_scenario = "clear"
        shaping_active = False
        
    elif scenario_name == "DEMO_02_DENSE_FOG":
        weather_scenario = "dense_fog"
        shaping_active = False
        
    elif scenario_name == "DEMO_03_FOG_RECOVERY":
        weather_scenario = "fog_recovery"
        shaping_active = False
        
    elif scenario_name == "DEMO_04_CRUSHER_BOTTLENECK":
        weather_scenario = "clear"
        shaping_active = False
        crusher_rate_vph = 10.0  # Constrain crusher capacity to induce bottleneck
        
    elif scenario_name == "DEMO_05_ARRIVAL_SHAPING_OFF":
        weather_scenario = "clear"
        shaping_active = False
        crusher_rate_vph = 10.0  # Crusher constrained
        
    elif scenario_name == "DEMO_05_ARRIVAL_SHAPING_ON":
        weather_scenario = "clear"
        shaping_active = True    # Enable arrival shaping
        crusher_rate_vph = 10.0  # Crusher constrained
        
    elif scenario_name == "DEMO_06_FULL_VERTICAL_SLICE":
        # Custom time-varying scenario. We will start with "clear" configurations.
        weather_scenario = "clear"
        shaping_active = False   # Set initially to False; will be activated dynamically
        crusher_rate_vph = 10.0  # Crusher starts constrained to highlight bottleneck
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    # Set crusher rate in network
    network.nodes["CRUSHER"].service_rate_vph = crusher_rate_vph
    if network.nodes["CRUSHER"].queue:
        network.nodes["CRUSHER"].queue.service_rate_vph = crusher_rate_vph

    # 2. Instantiate simulator
    sim = Simulator(network, vehicle_config, weather_config, scenario_config)
    sim.fog_model.set_scenario(weather_scenario)
    sim.shaping_active = shaping_active

    # 3. Execution loop
    duration = scenario_config["run_duration_s"]
    steps = int(duration / scenario_config["timestep_s"])
    
    print(f"Running {scenario_name} for {duration} seconds ({steps} steps)...")
    
    for step in range(steps):
        # Handle dynamic weather/control events in DEMO_06_FULL_VERTICAL_SLICE
        if scenario_name == "DEMO_06_FULL_VERTICAL_SLICE":
            current_time = sim.current_time
            # Dynamic stages:
            # 0 to 300s: Clear dry (visibility 50m, friction 0.60)
            if current_time < 300:
                sim.fog_model.current_visibility = 50.0
                sim.fog_model.current_friction = 0.60
                sim.fog_model.current_rr = 0.02
                sim.fog_model.current_state = "dry"
                sim.shaping_active = False
            # 300 to 450s: Gradual fog onset (50m -> 15m, friction 0.60 -> 0.25)
            elif 300 <= current_time < 450:
                frac = (current_time - 300.0) / 150.0
                sim.fog_model.current_visibility = 50.0 - frac * (50.0 - 15.0)
                sim.fog_model.current_friction = 0.60 - frac * (0.60 - 0.25)
                sim.fog_model.current_rr = 0.02 + frac * (0.03 - 0.02)
                sim.fog_model.current_state = "damp"
                sim.shaping_active = False
            # 450 to 900s: Heavy dense fog (visibility 15m, friction 0.25)
            elif 450 <= current_time < 900:
                sim.fog_model.current_visibility = 15.0
                sim.fog_model.current_friction = 0.25
                sim.fog_model.current_rr = 0.03
                sim.fog_model.current_state = "wet"
                sim.shaping_active = False
            # 900 to 1300s: Heavy fog + Activate Arrival-Rate Shaping to stabilize queues
            elif 900 <= current_time < 1300:
                sim.fog_model.current_visibility = 15.0
                sim.fog_model.current_friction = 0.25
                sim.fog_model.current_rr = 0.03
                sim.fog_model.current_state = "wet"
                sim.shaping_active = True  # Enable arrival shaping
            # 1300 to 1800s: Fog clears (recovery 15m -> 50m, friction 0.25 -> 0.60)
            else:
                frac = (current_time - 1300.0) / 500.0
                sim.fog_model.current_visibility = 15.0 + frac * (50.0 - 15.0)
                sim.fog_model.current_friction = 0.25 + frac * (0.60 - 0.25)
                sim.fog_model.current_rr = 0.03 - frac * (0.03 - 0.02)
                sim.fog_model.current_state = "damp" if frac < 0.5 else "dry"
                # Keep shaping active during clearing to prevent release surges
                sim.shaping_active = True
                
        sim.run_step()
        
    print(f"Scenario {scenario_name} complete. Generated {len(sim.state_history)} history frames.")
    return sim.state_history
