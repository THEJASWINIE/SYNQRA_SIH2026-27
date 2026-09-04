"""
FOG-ORCHESTRATOR 2.0 — Digital Twin Execution & Fog Visibility Experiment Runner
Runs the existing Digital Twin physics engine, tests 50m -> 30m -> 15m fog visibility degradation and recovery,
passes computed V_SAFE through TwinVelocityAdapter, and verifies command generation for TRUCK_02.
"""

import sys
import os
import time
import math
import requests
from typing import Dict, Any

from contracts import DispatchCommandMessage, CommandAckMessage
from hardware_emulator import VehicleHardwareEmulator
from fog_safe.safety import solve_safe_speed
from integration_adapters.twin_velocity_adapter import TwinVelocityAdapter

BACKEND_URL = "http://10.126.54.41:8000"

def run_digital_twin_demo():
    print("============================================================")
    print("FOG-ORCHESTRATOR 2.0 — DIGITAL TWIN FOG EXPERIMENT RUNNER")
    print("============================================================")

    # 1. Component setup
    vehicle_id = "TRUCK_02"
    truck = VehicleHardwareEmulator(vehicle_id, initial_position=150.0, segment_id="ROAD_2")
    adapter = TwinVelocityAdapter(prototype_scale=0.10)

    # 2. Test steps: 50m -> 30m -> 15m -> 30m -> 50m
    test_visibilities = [50.0, 30.0, 15.0, 30.0, 50.0]
    experiment_results = []

    print(f"\n[DIGITAL TWIN TARGET VEHICLE]: {vehicle_id}")
    print(f"[AUTHORITATIVE PHYSICS SOLVER]: fog_safe.safety.solve_safe_speed")
    print(f"[TWIN VELOCITY ADAPTER]: integration_adapters.twin_velocity_adapter (Scale: {adapter.prototype_scale})")

    for vis in test_visibilities:
        ts = time.time()
        # Set environment visibility state
        truck.update_environment(visibility_m=vis, friction_mu=0.35, grade_pct=0.0)

        # Existing Digital Twin physics solver calculates V_SAFE
        res_physics = solve_safe_speed(
            vehicle=truck.phys_vehicle,
            road=truck.road,
            env=truck.env,
            comm=truck.comm,
            mu_effective=truck.env.mu_true,
            r_effective=truck.env.r_effective
        )
        v_safe_ms = res_physics.v_safe_ms
        v_safe_kmh = res_physics.v_safe_kmh

        # TwinVelocityAdapter transports V_SAFE into target velocity command
        cmd_dict = adapter.format_velocity_command(
            vehicle_id=vehicle_id,
            computed_velocity=v_safe_ms,
            timestamp=ts,
            validity=True,
            apply_scaling=True
        )

        proto_target = cmd_dict["prototype_target_ms"]
        cmd_id = cmd_dict["command_id"]

        dispatch_msg = adapter.to_dispatch_command_message(
            vehicle_id=vehicle_id,
            computed_velocity=v_safe_ms,
            timestamp=ts,
            validity=True,
            apply_scaling=True
        )

        # Ingest into vehicle local safety governor
        ack = truck.process_dispatch_command(dispatch_msg)

        experiment_results.append({
            "visibility_m": vis,
            "v_safe_ms": round(v_safe_ms, 4),
            "v_safe_kmh": round(v_safe_kmh, 2),
            "prototype_target_ms": round(proto_target, 4),
            "command_id": cmd_id,
            "ack_status": ack.status,
            "applied_speed": round(ack.applied_speed, 4)
        })

    # Print requested physics table
    print("\n+------------+-------------------+----------------+")
    print("| Visibility | Physics V_SAFE    | Command Speed  |")
    print("+------------+-------------------+----------------+")
    for r in experiment_results[:3]: # 50m, 30m, 15m
        print(f"| {r['visibility_m']:<10.1f} | {r['v_safe_ms']:<6.4f} m/s      | {r['prototype_target_ms']:<6.4f} m/s    |")
    print("+------------+-------------------+----------------+")

    # Print recovery step table
    print("\n[RECOVERY STEP CHAIN: 15m -> 30m -> 50m]")
    print("+------------+-------------------+----------------+")
    print("| Visibility | Physics V_SAFE    | Command Speed  |")
    print("+------------+-------------------+----------------+")
    for r in experiment_results[2:]: # 15m, 30m, 50m
        print(f"| {r['visibility_m']:<10.1f} | {r['v_safe_ms']:<6.4f} m/s      | {r['prototype_target_ms']:<6.4f} m/s    |")
    print("+------------+-------------------+----------------+")

    # Print TRUCK_02 Target Summary
    print(f"\nVehicle:\n{vehicle_id}")
    print(f"\nVisibility:\n{experiment_results[2]['visibility_m']} m (Dense Fog)")
    print(f"\nPhysics V_SAFE:\n{experiment_results[2]['v_safe_ms']} m/s ({experiment_results[2]['v_safe_kmh']} km/h)")
    print(f"\nPrototype / vehicle target:\n{experiment_results[2]['prototype_target_ms']} m/s")
    print(f"\nCommand ID:\n{experiment_results[2]['command_id']}")

    return experiment_results

if __name__ == "__main__":
    run_digital_twin_demo()
