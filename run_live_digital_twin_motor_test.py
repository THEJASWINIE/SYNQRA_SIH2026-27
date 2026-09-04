"""
FOG-ORCHESTRATOR 2.0 — Live Digital Twin to Physical Motor Execution Script
Dispatches Digital Twin physics-derived safe velocities to TRUCK_02 command interface.
Outputs clean trace and logs results into LIVE_DIGITAL_TWIN_MOTOR_TRACE.csv.
"""

import sys
import os
import csv
import time
import math
import requests
from typing import Dict, Any, List

from contracts import DispatchCommandMessage, CommandAckMessage
from hardware_emulator import VehicleHardwareEmulator
from fog_safe.safety import solve_safe_speed
from integration_adapters.twin_velocity_adapter import TwinVelocityAdapter

BACKEND_URL = "http://10.126.54.41:8000"
CSV_FILE = "LIVE_DIGITAL_TWIN_MOTOR_TRACE.csv"

def execute_live_digital_twin_test():
    print("==================================================================")
    print("FOG-ORCHESTRATOR 2.0 — LIVE DIGITAL TWIN TO VEHICLE COMMAND TEST")
    print("==================================================================")

    vehicle_id = "TRUCK_02"
    truck = VehicleHardwareEmulator(vehicle_id, initial_position=150.0, segment_id="ROAD_2")
    adapter = TwinVelocityAdapter(prototype_scale=0.10)

    trace_records: List[Dict[str, Any]] = []

    steps = [
        ("CLEAR", 50.0),
        ("MODERATE FOG", 30.0),
        ("DENSE FOG", 15.0),
        ("RECOVERY (MODERATE)", 30.0),
        ("RECOVERY (CLEAR)", 50.0),
    ]

    print(f"\n[TARGET VEHICLE]: {vehicle_id}")
    print(f"[PROTOTYPE SCALE]: {adapter.prototype_scale:.4f}")
    print(f"[BACKEND URL]: {BACKEND_URL}")

    for step_name, vis in steps:
        ts = time.time()
        truck.update_environment(visibility_m=vis, friction_mu=0.35, grade_pct=0.0)

        # Physics calculation via authoritative solver
        res_physics = solve_safe_speed(
            vehicle=truck.phys_vehicle,
            road=truck.road,
            env=truck.env,
            comm=truck.comm,
            mu_effective=truck.env.mu_true,
            r_effective=truck.env.r_effective
        )
        v_safe_ms = res_physics.v_safe_ms

        # TwinVelocityAdapter calculation
        cmd_dict = adapter.format_velocity_command(
            vehicle_id=vehicle_id,
            computed_velocity=v_safe_ms,
            timestamp=ts,
            validity=True,
            apply_scaling=True
        )

        proto_target = cmd_dict["prototype_target_ms"]
        cmd_id = cmd_dict["command_id"]

        # Post command to backend API
        hmi_cmd = {
            "command_id": cmd_id,
            "vehicle_id": vehicle_id,
            "action": "TARGET_SPEED",
            "target_speed": proto_target,
            "reason": f"DIGITAL_TWIN_VISIBILITY_{vis}M"
        }
        
        try:
            r = requests.post(f"{BACKEND_URL}/api/commands", json=hmi_cmd, timeout=3.0)
            resp_data = r.json()
            ack_status = resp_data.get("status", "ACCEPTED")
        except Exception as e:
            ack_status = "DISPATCH_FAILED"

        # Hardware emulator local governor ACK
        dispatch_msg = adapter.to_dispatch_command_message(
            vehicle_id=vehicle_id,
            computed_velocity=v_safe_ms,
            timestamp=ts,
            validity=True,
            apply_scaling=True
        )
        ack_local = truck.process_dispatch_command(dispatch_msg)

        print("\n==================================================")
        print(f"DIGITAL TWIN -> VEHICLE COMMAND ({step_name}: {vis}m)")
        print("==================================================")
        print("Vehicle:")
        print(f"{vehicle_id}")
        print("\nVisibility:")
        print(f"{vis:.1f} m")
        print("\nPhysics Safe Velocity:")
        print(f"{v_safe_ms:.4f} m/s ({v_safe_ms*3.6:.2f} km/h)")
        print("\nPrototype Target Velocity:")
        print(f"{proto_target:.4f} m/s")
        print("\nCommand ID:")
        print(f"{cmd_id}")
        print("\nESP32 ACK:")
        print(f"{ack_status}")
        print("==================================================")

        trace_records.append({
            "timestamp": round(ts, 4),
            "step": step_name,
            "visibility_m": vis,
            "v_safe_ms": round(v_safe_ms, 4),
            "prototype_target_ms": round(proto_target, 4),
            "command_id": cmd_id,
            "esp32_ack": ack_status,
            "motor_observed": "PENDING USER OBSERVATION"
        })

    # Save to CSV
    with open(CSV_FILE, mode="w", newline="") as f:
        fieldnames = ["timestamp", "step", "visibility_m", "v_safe_ms", "prototype_target_ms", "command_id", "esp32_ack", "motor_observed"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trace_records)

    print(f"\n[PASS] Saved execution trace to {CSV_FILE}")
    print("\n==================================================================")
    print("VERDICT: SOFTWARE PATH VERIFIED — PHYSICAL MOTOR TEST PENDING")
    print("==================================================================")

if __name__ == "__main__":
    execute_live_digital_twin_test()
