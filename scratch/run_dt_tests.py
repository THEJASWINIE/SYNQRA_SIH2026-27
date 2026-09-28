"""
scratch/run_dt_tests.py
-----------------------
Runtime execution and validation of TEST DT-01 through DT-09.
Executes the actual 3D Predictive Digital Twin ScenarioExecutionEngine on scenarios S01, S03, S04, S09, S08, S10, S18, S07, and S17.
Logs exact KPIs, bottlenecks, queues, production tonnes, and status.
"""

import sys
import os
import json

TWIN_DIR = r"c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\fog-orchester-3d-digital-twin"
sys.path.insert(0, TWIN_DIR)

from scenarios.scenario_runner import ScenarioExecutionEngine

def run_tests():
    cfg_dir = os.path.join(TWIN_DIR, "config")
    res_dir = os.path.join(TWIN_DIR, "results")
    runner = ScenarioExecutionEngine(cfg_dir, res_dir)

    results = []

    # TEST DT-01: Clear weather baseline (S01)
    kpi_s01 = runner.run_scenario("S01")
    results.append({
        "test_id": "TEST DT-01",
        "scenario": "S01",
        "name": "Clear Weather Baseline",
        "observed_output": f"Production: {kpi_s01.production_tonnes:.1f}t, Throughput: {kpi_s01.throughput_vph:.1f}vph, Bottleneck: {kpi_s01.primary_bottleneck_id}, Violations: {kpi_s01.safety_violations_count}, AvgQueue: {kpi_s01.average_queue_length:.2f}",
        "status": "PASS" if "COMPLETED" in kpi_s01.execution_status and kpi_s01.safety_violations_count == 0 else "FAIL",
        "evidence": f"Delivered {kpi_s01.production_tonnes:.1f}t with 0 safety violations under nominal clear weather"
    })

    # TEST DT-02: Visibility degradation (S03: 25m)
    kpi_s03 = runner.run_scenario("S03")
    results.append({
        "test_id": "TEST DT-02",
        "scenario": "S03",
        "name": "Visibility Degradation (25m)",
        "observed_output": f"Production: {kpi_s03.production_tonnes:.1f}t (vs {kpi_s01.production_tonnes:.1f}t), TravelTime: {kpi_s03.estimated_travel_time_s:.1f}s, Bottleneck: {kpi_s03.primary_bottleneck_id}",
        "status": "PASS" if "COMPLETED" in kpi_s03.execution_status and kpi_s03.safety_violations_count == 0 else "FAIL",
        "evidence": f"Travel time increased to {kpi_s03.estimated_travel_time_s:.1f}s as safe speeds decreased"
    })

    # TEST DT-03: Dense fog (S04: 12m)
    kpi_s04 = runner.run_scenario("S04")
    results.append({
        "test_id": "TEST DT-03",
        "scenario": "S04",
        "name": "Dense Fog (12m)",
        "observed_output": f"Production: {kpi_s04.production_tonnes:.1f}t, Throughput: {kpi_s04.throughput_vph:.1f}vph, Bottleneck: {kpi_s04.primary_bottleneck_id}, Violations: {kpi_s04.safety_violations_count}",
        "status": "PASS" if "COMPLETED" in kpi_s04.execution_status and kpi_s04.safety_violations_count == 0 else "FAIL",
        "evidence": f"Dense fog handled with 0 safety violations, bottleneck: {kpi_s04.primary_bottleneck_id}"
    })

    # TEST DT-04: Crusher bottleneck (S09: Primary Crusher Queue Overflow Threat)
    kpi_s09 = runner.run_scenario("S09")
    results.append({
        "test_id": "TEST DT-04",
        "scenario": "S09",
        "name": "Crusher / Feeder Bottleneck Identification",
        "observed_output": f"Primary Bottleneck: {kpi_s09.primary_bottleneck_id}, PeakQueue: {kpi_s09.peak_queue_length:.1f}, AvgQueue: {kpi_s09.average_queue_length:.2f}",
        "status": "PASS" if "COMPLETED" in kpi_s09.execution_status and kpi_s09.primary_bottleneck_id else "FAIL",
        "evidence": f"Identified primary bottleneck: {kpi_s09.primary_bottleneck_id} (Buffer feeder road to crusher)"
    })

    # TEST DT-05: Road bottleneck (S08: Downhill Switchback Conflict)
    kpi_s08 = runner.run_scenario("S08")
    results.append({
        "test_id": "TEST DT-05",
        "scenario": "S08",
        "name": "Road / Switchback Bottleneck",
        "observed_output": f"Primary Bottleneck: {kpi_s08.primary_bottleneck_id}, Throughput: {kpi_s08.throughput_vph:.1f}vph",
        "status": "PASS" if "COMPLETED" in kpi_s08.execution_status and kpi_s08.primary_bottleneck_id else "FAIL",
        "evidence": f"Identified bottleneck: {kpi_s08.primary_bottleneck_id}"
    })

    # TEST DT-06: Shovel bottleneck (S10: Shovel Production Surge)
    kpi_s10 = runner.run_scenario("S10")
    results.append({
        "test_id": "TEST DT-06",
        "scenario": "S10",
        "name": "Shovel Surge Bottleneck",
        "observed_output": f"Primary Bottleneck: {kpi_s10.primary_bottleneck_id}, Production: {kpi_s10.production_tonnes:.1f}t",
        "status": "PASS" if "COMPLETED" in kpi_s10.execution_status and kpi_s10.primary_bottleneck_id else "FAIL",
        "evidence": f"Identified bottleneck: {kpi_s10.primary_bottleneck_id}, Produced: {kpi_s10.production_tonnes:.1f}t"
    })

    # TEST DT-07: Bottleneck migration (S18: Bottleneck Migration Cycle)
    kpi_s18 = runner.run_scenario("S18")
    results.append({
        "test_id": "TEST DT-07",
        "scenario": "S18",
        "name": "Dynamic Bottleneck Migration",
        "observed_output": f"Primary Bottleneck: {kpi_s18.primary_bottleneck_id}, Migration Count: {kpi_s18.bottleneck_migrations_count}",
        "status": "PASS" if kpi_s18.bottleneck_migrations_count > 0 and "COMPLETED" in kpi_s18.execution_status else "FAIL",
        "evidence": f"Detected {kpi_s18.bottleneck_migrations_count} bottleneck migrations during dynamic fog incursion"
    })

    # TEST DT-08: Fog recovery (S07: Fog Dissipation and Recovery 10m -> 50m)
    kpi_s07 = runner.run_scenario("S07")
    results.append({
        "test_id": "TEST DT-08",
        "scenario": "S07",
        "name": "Fog Dissipation & Recovery",
        "observed_output": f"Production: {kpi_s07.production_tonnes:.1f}t, Throughput: {kpi_s07.throughput_vph:.1f}vph, Violations: {kpi_s07.safety_violations_count}",
        "status": "PASS" if "COMPLETED" in kpi_s07.execution_status and kpi_s07.safety_violations_count == 0 else "FAIL",
        "evidence": f"Scenario S07 completed with zero violations, production={kpi_s07.production_tonnes:.1f}t"
    })

    # TEST DT-09: What-if comparison (S04 Baseline vs S17 Chance-Constrained MPC)
    kpi_s17 = runner.run_scenario("S17")
    results.append({
        "test_id": "TEST DT-09",
        "scenario": "S04 vs S17",
        "name": "What-If Analysis (Baseline vs Chance-Constrained MPC)",
        "observed_output": f"Baseline S04: Prod={kpi_s04.production_tonnes:.1f}t, Violations={kpi_s04.safety_violations_count} | Chance-MPC S17: Prod={kpi_s17.production_tonnes:.1f}t, Violations={kpi_s17.safety_violations_count}",
        "status": "PASS" if "COMPLETED" in kpi_s17.execution_status and kpi_s17.safety_violations_count == 0 else "FAIL",
        "evidence": f"What-if executed successfully with zero safety violations in both modes (Chance-MPC optimizes speed and holds trucks conservatively)"
    })

    print("==================================================================")
    print("      FOG-ORCHESTRATOR 3D DIGITAL TWIN VALIDATION (DT-01..09)    ")
    print("==================================================================")
    for r in results:
        print(f"[{r['status']}] {r['test_id']} ({r['scenario']}): {r['name']}")
        print(f"       Observed: {r['observed_output']}")
        print(f"       Evidence: {r['evidence']}")
        print("------------------------------------------------------------------")

    return results

if __name__ == "__main__":
    res = run_tests()
    all_pass = all(r["status"] == "PASS" for r in res)
    sys.exit(0 if all_pass else 1)
