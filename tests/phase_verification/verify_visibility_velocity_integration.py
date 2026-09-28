"""
FOG-ORCHESTRATOR 2.0 — Automated Visibility-to-Velocity Integration Verification
Validates:
Digital Twin Visibility -> Fog/Visibility Physics Engine -> Computed Safe Velocity -> Adapter -> Vehicle Command -> Local Safety Governor
Generates VISIBILITY_VELOCITY_TEST_RESULTS.csv and prints explicit execution logs.
"""

import sys
import os
import csv
import time
import math
from typing import List, Dict, Any

from contracts import DispatchCommandMessage, CommandAckMessage
from hardware_emulator import VehicleHardwareEmulator
from fog_safe.safety import solve_safe_speed
from integration_adapters.twin_velocity_adapter import TwinVelocityAdapter

# Import regression suites
from verify_phase1 import verify_phase1_hardware_hmi
from verify_phase2 import verify_phase2_digital_twin
from verify_wireless_hmi import run_wireless_hmi_verification

CSV_FILENAME = "VISIBILITY_VELOCITY_TEST_RESULTS.csv"

def run_visibility_velocity_verification() -> bool:
    print("==================================================================")
    print("FOG-ORCHESTRATOR 2.0 — VISIBILITY TO VELOCITY INTEGRATION VERIFIER")
    print("==================================================================")

    # 1. Gated Prerequisite Checks
    print("\n[STEP 1] Running Standalone Gated Phase Verification...")
    if not verify_phase1_hardware_hmi():
        print("[FAIL] Phase 1 verification failed!")
        return False

    if not verify_phase2_digital_twin():
        print("[FAIL] Phase 2 verification failed!")
        return False

    if not run_wireless_hmi_verification():
        print("[FAIL] Wireless HMI verification failed!")
        return False

    print("[PASS] Phase 1, Phase 2, and HMI prerequisite suites PASSED!")

    # 2. Component Setup
    vehicle_id = "TRUCK_01"
    truck = VehicleHardwareEmulator(vehicle_id, initial_position=0.0, segment_id="ROAD_1")
    adapter = TwinVelocityAdapter()

    csv_rows: List[Dict[str, Any]] = []

    # 3. Visibility Tests Execution (50m, 30m, 15m, step-down, step-up, invalid)
    test_visibilities = [50.0, 30.0, 15.0, 30.0, 50.0]

    print("\n[STEP 2] Running Closed-Loop Visibility -> Physics -> Command Experiments...")

    for vis in test_visibilities:
        ts = time.time()
        # Update vehicle environment perception
        truck.update_environment(visibility_m=vis, friction_mu=0.35, grade_pct=0.0)

        # Compute safe speed directly from authoritative physics solver
        res_physics = solve_safe_speed(
            vehicle=truck.phys_vehicle,
            road=truck.road,
            env=truck.env,
            comm=truck.comm,
            mu_effective=truck.env.mu_true,
            r_effective=truck.env.r_effective
        )
        v_computed = res_physics.v_safe_ms

        # Transport through TwinVelocityAdapter
        cmd_dict = adapter.format_velocity_command(
            vehicle_id=vehicle_id,
            computed_velocity=v_computed,
            timestamp=ts,
            validity=True
        )

        dispatch_msg = adapter.to_dispatch_command_message(
            vehicle_id=vehicle_id,
            computed_velocity=v_computed,
            timestamp=ts,
            validity=True
        )

        # Ingest command into vehicle hardware emulator local safety governor
        ack = truck.process_dispatch_command(dispatch_msg)

        # Trace Log
        print("\n==================================================")
        print("VISIBILITY -> VELOCITY TRACE")
        print("==================================================")
        print(f"Vehicle:              {vehicle_id}")
        print(f"Visibility:           {vis:.1f} m")
        print(f"Physics Safe Speed:   {v_computed:.4f} m/s ({v_computed * 3.6:.2f} km/h)")
        print(f"Command Velocity:     {dispatch_msg.target_speed:.4f} m/s ({cmd_dict['unit']})")
        print(f"Local Safety Limit:   {truck.compute_local_safety_state().v_safe:.4f} m/s")
        print(f"Applied Speed / Status: {ack.applied_speed:.4f} m/s ({ack.status})")
        print("==================================================")

        # Assertions
        assert abs(dispatch_msg.target_speed - v_computed) < 1e-4, "Command velocity must match computed physics velocity"
        assert ack.applied_speed <= v_computed + 1e-4, "Applied speed must not exceed physics safety limit"
        assert ack.status in ["ACCEPTED", "CLAMPED"], f"Unexpected ACK status: {ack.status}"

        csv_rows.append({
            "visibility": vis,
            "computed_safe_velocity": round(v_computed, 4),
            "vehicle_id": vehicle_id,
            "command_velocity": round(dispatch_msg.target_speed, 4),
            "command_status": ack.status,
            "timestamp": round(ts, 4)
        })

    # 4. Test T7: Invalid/Unavailable Visibility Handling
    print("\n[STEP 3] Testing T7: Invalid Physics Velocity Fallback...")
    ts_invalid = time.time()
    cmd_invalid = adapter.format_velocity_command(
        vehicle_id=vehicle_id,
        computed_velocity=float('nan'),
        timestamp=ts_invalid,
        validity=False
    )
    assert cmd_invalid["status"] == "INVALID_FALLBACK", "Invalid velocity must generate fallback status"
    assert cmd_invalid["velocity"] == 0.0, "Invalid velocity must generate 0.0 m/s safe fallback speed"
    print("  [PASS] Invalid velocity fallback safely executed (0.0 m/s STOP command emitted)")

    # 5. Test T8: Local Safety Governor Clamping (Authoritative Local Boundary)
    print("\n[STEP 4] Testing T8: Local Safety Governor Clamping Authority...")
    truck.update_environment(visibility_m=15.0, friction_mu=0.35, grade_pct=0.0)
    safety_15m = truck.compute_local_safety_state()

    # Create dispatch message exceeding 15m safe ceiling (e.g. 12.0 m/s > ~5.4 m/s)
    unsafe_cmd = DispatchCommandMessage(
        command_id="CMD_TEST_UNSAFE_01",
        vehicle_id=vehicle_id,
        timestamp=time.time(),
        target_speed=12.0,
        action="TARGET_SPEED",
        reason_code="TEST_UNSAFE"
    )
    ack_unsafe = truck.process_dispatch_command(unsafe_cmd)
    assert ack_unsafe.status == "CLAMPED", f"Expected CLAMPED, got {ack_unsafe.status}"
    assert ack_unsafe.applied_speed <= safety_15m.v_safe + 1e-4, "Applied speed must be clamped to local governor ceiling"
    print(f"  [PASS] Local safety governor authority verified: Unsafe command (12.0 m/s) clamped to local limit ({ack_unsafe.applied_speed:.2f} m/s)")

    # 6. Save VISIBILITY_VELOCITY_TEST_RESULTS.csv
    print(f"\n[STEP 5] Saving results to {CSV_FILENAME}...")
    with open(CSV_FILENAME, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["visibility", "computed_safe_velocity", "vehicle_id", "command_velocity", "command_status", "timestamp"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  [PASS] Experiment dataset successfully saved to {CSV_FILENAME}")

    print("\n==================================================================")
    print("VERDICT: SOFTWARE VERIFIED — HARDWARE TEST PENDING")
    print("==================================================================")
    return True

if __name__ == "__main__":
    success = run_visibility_velocity_verification()
    sys.exit(0 if success else 1)
