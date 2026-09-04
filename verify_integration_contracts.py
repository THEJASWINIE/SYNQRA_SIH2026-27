"""
FOG-ORCHESTRATOR 2.0 — Integration Contract Verification Suite (Validation Stage 2)

Verifies 15 contract validation checks across Vehicle ID mapping, unit conversion,
kinematic scaling, IMU processing, position estimation, quality filtering, time alignment,
and safety non-bypass.
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration_sandbox import IntegrationSandbox
from integration_adapters.vehicle_id_mapper import VehicleIDMapper
from integration_adapters.unit_converter import UnitConverter
from integration_adapters.kinematic_scale import KinematicScaleAdapter
from integration_adapters.imu_processor import IMUProcessor
from integration_adapters.time_adapter import TimeAdapter
from integration_adapters.coordinate_mapper import CoordinateMapper
from integration_adapters.telemetry_quality_filter import TelemetryQualityFilter
from integration_adapters.command_adapter import CommandAdapter


def run_contract_verification() -> bool:
    print("====================================================")
    print("INTEGRATION CONTRACT VERIFICATION (STAGE 2)")
    print("====================================================")

    results = {}
    sandbox = IntegrationSandbox()

    # CHECK 1: Physical vehicle ID maps correctly
    id_map = VehicleIDMapper()
    results["CHECK 1"] = "PASS" if id_map.to_twin_id("TRUCK_01") == "vehicle_1" else "FAIL"

    # CHECK 2: Unknown vehicle rejected
    results["CHECK 2"] = "PASS" if id_map.to_twin_id("TRUCK_99") is None else "FAIL"

    # CHECK 3: RPM converts correctly
    unit_conv = UnitConverter()
    spd = unit_conv.rpm_to_speed_mps("TRUCK_01", 240.0)
    results["CHECK 3"] = "PASS" if spd is not None and abs(spd - 1.2566) < 0.05 else "FAIL"

    # CHECK 4: Raw physical speed is preserved
    kin = KinematicScaleAdapter()
    res_kin = kin.physical_to_twin_speed(1.5)
    results["CHECK 4"] = "PASS" if res_kin["physical_speed_mps"] == 1.5 else "FAIL"

    # CHECK 5: Twin-equivalent speed is separately represented
    results["CHECK 5"] = "PASS" if "twin_equivalent_speed_mps" in res_kin and res_kin["twin_equivalent_speed_mps"] > 1.5 else "FAIL"

    # CHECK 6: Invalid units rejected
    results["CHECK 6"] = "PASS" if unit_conv.rpm_to_speed_mps("TRUCK_01", -10.0) is None else "FAIL"

    # CHECK 7: Raw IMU is not directly injected into physics
    imu_proc = IMUProcessor()
    proc_imu = imu_proc.process({"AcX": 0, "AcY": 0, "AcZ": 16384, "GyX": 0, "GyY": 0, "GyZ": 0})
    results["CHECK 7"] = "PASS" if "acceleration_mps2" in proc_imu and proc_imu["acceleration_mps2"]["z"] == 9.81 else "FAIL"

    # CHECK 8: Position is marked ESTIMATED
    coord_map = CoordinateMapper()
    pose = coord_map.update_pose("TRUCK_01", speed_mps=1.0, yaw_rate_rads=0.0, dt_s=0.5)
    results["CHECK 8"] = "PASS" if pose.get("position_quality") == "ESTIMATED" else "FAIL"

    # CHECK 9: Stale telemetry is rejected
    t_filter = TelemetryQualityFilter(stale_threshold_s=1.0)
    now = time.time()
    stale_res = t_filter.filter_telemetry({"vehicle_id": "TRUCK_01", "source_timestamp": now - 3.0, "sequence_number": 1})
    results["CHECK 9"] = "PASS" if stale_res.get("should_update_twin") is False and stale_res.get("data_quality") == "STALE" else "FAIL"

    # CHECK 10: Duplicate telemetry is handled
    t_adapter = TimeAdapter()
    pkt = {"vehicle_id": "TRUCK_01", "sequence_number": 5, "timestamp": now}
    t_adapter.process_telemetry(pkt)
    dup_res = t_adapter.process_telemetry(pkt)
    results["CHECK 10"] = "PASS" if dup_res.get("is_duplicate") is True else "FAIL"

    # CHECK 11: Out-of-order telemetry is handled
    pkt_ooo = {"vehicle_id": "TRUCK_01", "sequence_number": 3, "timestamp": now}
    ooo_res = t_adapter.process_telemetry(pkt_ooo)
    results["CHECK 11"] = "PASS" if ooo_res.get("is_out_of_order") is True else "FAIL"

    # CHECK 12: Twin recommendations expire
    results["CHECK 12"] = "PASS" if t_adapter.is_recommendation_expired(now - 10.0) is True else "FAIL"

    # CHECK 13: Recommendation does not bypass safety
    cmd_adapter = CommandAdapter()
    twin_adv = {"vehicle_id": "vehicle_1", "recommended_speed": 11.11, "action": "TARGET_SPEED", "timestamp": now}
    cmd_req = cmd_adapter.translate_twin_advisory(twin_adv)
    # Requested speed is scaled to 3.0 m/s max prototype speed
    results["CHECK 13"] = "PASS" if cmd_req is not None and cmd_req.get("requested_value") <= 3.0 else "FAIL"

    # CHECK 14: ACK returns actual applied value
    ack_res = cmd_adapter.process_vehicle_ack({"command_id": cmd_req["command_id"], "vehicle_id": "TRUCK_01", "status": "CLAMPED", "applied_speed": 2.5})
    results["CHECK 14"] = "PASS" if ack_res.get("ack_status") == "CLAMPED" and ack_res.get("applied_value") == 2.5 else "FAIL"

    # CHECK 15: Vehicle isolation remains intact
    twin_adv_b = {"vehicle_id": "vehicle_2", "recommended_speed": 5.0, "action": "TARGET_SPEED", "timestamp": now}
    cmd_req_b = cmd_adapter.translate_twin_advisory(twin_adv_b)
    results["CHECK 15"] = "PASS" if cmd_req_b is not None and cmd_req_b.get("vehicle_id") == "TRUCK_02" and cmd_req_b.get("vehicle_id") != cmd_req.get("vehicle_id") else "FAIL"

    # Print output matrix
    for check_id, status in results.items():
        print(f"{check_id} .................... {status}")

    all_passed = all(st == "PASS" for st in results.values())
    print("====================================================")
    print(f"STAGE 2 CONTRACT VERIFICATION: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


if __name__ == "__main__":
    success = run_contract_verification()
    sys.exit(0 if success else 1)
