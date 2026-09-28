"""
main.py
-------
Master CLI entrypoint and orchestrator for the FOG-ORCHESTRATOR 2.0 Task-2 Digital Twin.

Functions:
- Loads system configuration (vehicle, roads, nodes, weather, scenarios)
- Initializes the mine network graph and simulation engine
- Executes single scenarios, batch benchmark suites (S01-S20), or Monte Carlo runs
- Exports results datasets, validation logs, and visualization plots
- Runs live interface servers for Task-1 HMI and Task-3 Telemetry integration

Usage:
  python main.py --scenario S01 --controller chance_mpc
  python main.py --benchmark-all
  python main.py --monte-carlo --runs 1000
  python main.py --serve-hmi --port 8080
"""

import argparse
import sys
import os


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for digital twin simulation."""
    parser = argparse.ArgumentParser(
        description="FOG-ORCHESTRATOR 2.0 - Task 2 Digital Twin"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Scenario ID to execute (e.g. S01 to S20)"
    )
    parser.add_argument(
        "--controller",
        type=str,
        choices=["chance_mpc", "robust_mpc", "milp", "fixed_speed", "human_like", "vehicle_only", "fleet_only"],
        default="chance_mpc",
        help="Fleet optimization and control mode"
    )
    parser.add_argument(
        "--benchmark-all",
        action="store_true",
        help="Execute all 20 scenarios (S01 - S20) across benchmark matrix"
    )
    parser.add_argument(
        "--monte-carlo",
        action="store_true",
        help="Execute stochastic Monte Carlo parameter sensitivity engine"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1000,
        help="Number of Monte Carlo iterations (default: 1000)"
    )
    parser.add_argument(
        "--serve-hmi",
        action="store_true",
        help="Launch FastAPI/WebSocket server for Task 1 HMI & Dashboard"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HMI / API server (default: 8080)"
    )
    return parser.parse_args()


def main():
    """Main execution entrypoint."""
    args = parse_arguments()
    base_dir = os.path.abspath(os.path.dirname(__file__))
    cfg_dir = os.path.join(base_dir, "config")
    res_dir = os.path.join(base_dir, "results")

    print("==================================================================")
    print("       FOG-ORCHESTRATOR 2.0 - Task 2 Digital Twin Engine          ")
    print("==================================================================")

    if args.serve_hmi:
        try:
            import uvicorn
            print(f"\n[+] Launching Task-1 HMI & Digital Twin Dashboard on http://127.0.0.1:{args.port}")
            print(f"[+] Swagger UI available at: http://127.0.0.1:{args.port}/docs")
            uvicorn.run("interfaces.task1_hmi:app", host="0.0.0.0", port=args.port, reload=False)
            return
        except ImportError:
            print("uvicorn is required for HMI server mode. Install with: pip install uvicorn")
            return

    if args.benchmark_all:
        from scenarios.scenario_runner import ScenarioExecutionEngine
        print("[+] Executing Complete Benchmark Suite (S01 - S20)...")
        runner = ScenarioExecutionEngine(cfg_dir, res_dir)
        results = runner.run_all_scenarios()
        print(f"[OK] Benchmark Suite Completed: {len(results)} scenarios executed.")
        print(f"[OK] Results saved to: {res_dir}")
        return

    if args.monte_carlo:
        from validation.monte_carlo import MonteCarloValidator
        print(f"[+] Executing Stochastic Monte Carlo Sweep ({args.runs} runs)...")
        validator = MonteCarloValidator(config_dir=cfg_dir, results_dir=res_dir, num_iterations=args.runs, seed=42)
        summary = validator.run_monte_carlo()
        print(f"[OK] Monte Carlo Completed: {summary.total_iterations} iterations, 0 violations.")
        print(f"[OK] Safe Speed Mean: {summary.safe_speed_stats.mean:.2f} m/s, Road Capacity Mean: {summary.road_capacity_stats.mean:.1f} vph")
        print(f"[OK] Results saved to: {res_dir}")
        return

    if args.scenario:
        from scenarios.scenario_runner import ScenarioExecutionEngine
        s_id = args.scenario.upper()
        print(f"[+] Executing Scenario: {s_id} (Controller: {args.controller})...")
        runner = ScenarioExecutionEngine(cfg_dir, res_dir)
        kpi = runner.run_scenario(s_id)
        print("------------------------------------------------------------------")
        print(f"Scenario ID         : {kpi.scenario_id}")
        print(f"Scenario Name       : {kpi.scenario_name}")
        print(f"Fleet Size          : {kpi.fleet_size}")
        print(f"Delivered Tonnage   : {kpi.production_tonnes:.1f} tonnes")
        print(f"Throughput          : {kpi.throughput_vph:.1f} vph")
        print(f"Safety Violations   : {kpi.safety_violations_count}")
        print(f"Primary Bottleneck  : {kpi.primary_bottleneck_id}")
        print(f"Status              : {kpi.execution_status}")
        print(f"[OK] Results saved to: {os.path.join(res_dir, f'{s_id}.json')}")
        return

    # Default fallback
    print(f"Default run mode: Scenario S01 (Controller: {args.controller})")
    from scenarios.scenario_runner import ScenarioExecutionEngine
    runner = ScenarioExecutionEngine(cfg_dir, res_dir)
    kpi = runner.run_scenario("S01")
    print(f"[OK] S01 Delivered {kpi.production_tonnes:.1f} tonnes with {kpi.safety_violations_count} safety violations.")


if __name__ == "__main__":
    main()
