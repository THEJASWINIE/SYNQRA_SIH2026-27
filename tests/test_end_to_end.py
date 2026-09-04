import pytest
from run_baseline_vs_orchestrator import load_configs, build_graph
from scenarios.demo_v01 import run_scenario


def test_full_15_step_demo_scenario():
    vehicle_cfg, roads_cfg, nodes_cfg, weather_cfg, scenario_cfg = load_configs()

    # Step 1-7: Run baseline simulation demonstrating congestion
    net_b = build_graph(nodes_cfg, roads_cfg)
    hist_b = run_scenario("DEMO_05_ARRIVAL_SHAPING_OFF", net_b, vehicle_cfg, weather_cfg, scenario_cfg)
    assert len(hist_b) == 1800

    # Step 8-15: Run Fog-Orchestrator simulation demonstrating arrival shaping
    net_o = build_graph(nodes_cfg, roads_cfg)
    hist_o = run_scenario("DEMO_05_ARRIVAL_SHAPING_ON", net_o, vehicle_cfg, weather_cfg, scenario_cfg)
    assert len(hist_o) == 1800

    # Verify queue reduction in orchestrator run
    q_b = max(next(n["queue_length"] for n in f["node_states"] if n["node_id"] == "CRUSHER") for f in hist_b)
    q_o = max(next(n["queue_length"] for n in f["node_states"] if n["node_id"] == "CRUSHER") for f in hist_o)

    assert q_o < q_b
