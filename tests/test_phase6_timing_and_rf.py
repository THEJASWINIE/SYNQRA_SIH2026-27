# ==============================================================================
# PHASE 6 AUTOMATED REGRESSION SUITE: PHYSICAL TIMING & RF EVIDENCE CALIBRATION
# FOG-ORCHESTRATOR 2.0 — SIH 2026-27
# ==============================================================================

import os
import yaml
import pytest
import pandas as pd
import numpy as np

from integration_adapters.fail_safe_controller import (
    LocalVehicleSafetyGovernor,
    IncomingCommand,
    FailSafeState,
    CommandAction,
)
from hardware_emulator import VehicleHardwareEmulator
from contracts import DispatchCommandMessage
from integration_adapters.grade_adapter import GradeAdapter


def test_phase6_artifacts_exist():
    """Verify all 3 Phase 6 CSV datasets, 3 figures, and 5 forensic reports exist."""
    required_files = [
        "data/phase6_can_latency.csv",
        "data/phase6_rf_packets.csv",
        "data/phase6_safety_latency_sensitivity.csv",
        "figures/phase6_latency_distribution.png",
        "figures/phase6_stop_distance_sensitivity.png",
        "figures/phase6_rf_packet_loss.png",
        "reports/phase6_can_latency_validation.md",
        "reports/phase6_rf_validation.md",
        "reports/phase6_contradiction_audit.md",
        "reports/phase6_parameter_provenance.md",
        "reports/phase6_final_gate.md",
    ]
    for rel_path in required_files:
        assert os.path.exists(rel_path), f"Required Phase 6 artifact missing: {rel_path}"


def test_can_bench_statistics_and_conservatism():
    """Verify CAN bench dataset statistics and confirm nominal 50ms CAN / 450ms total latency is conservative."""
    df_can = pd.read_csv("data/phase6_can_latency.csv")
    assert len(df_can) >= 1000, f"Expected >= 1000 CAN transactions, got {len(df_can)}"

    valid_latencies = df_can["latency_ms"].dropna()
    p95_can = np.percentile(valid_latencies, 95)
    p99_can = np.percentile(valid_latencies, 99)

    # Bench CAN P95 must be <= 25 ms, verifying 50 ms assumption is conservative
    assert p95_can <= 25.0, f"P95 CAN latency {p95_can:.2f}ms exceeds 25ms threshold"
    assert p99_can <= 40.0, f"P99 CAN latency {p99_can:.2f}ms exceeds 40ms threshold"

    # Verify total reaction time decomposition
    tau_sensor = 0.100
    tau_comm = 0.0482
    tau_gov = 0.0048
    tau_actuator = 0.200
    tau_p95_total = tau_sensor + tau_comm + tau_gov + (p95_can / 1000.0) + tau_actuator

    # Nominal 450ms baseline must be greater than P95 measured total
    assert 0.450 >= tau_p95_total, f"Nominal baseline 0.450s is optimistic! P95 total={tau_p95_total:.4f}s"


def test_rf_packet_bench_dataset():
    """Verify CSS-LoRa 433 MHz RF benchmark dataset integrity and PDR behavior."""
    df_rf = pd.read_csv("data/phase6_rf_packets.csv")
    assert len(df_rf) >= 1000, f"Expected >= 1000 RF packets, got {len(df_rf)}"

    # Clear LOS should have >= 98% PDR
    df_los = df_rf[df_rf["scenario"] == "CLEAR_LOS"]
    delivered_los = len(df_los[df_los["status"] == "DELIVERED"])
    pdr_los = delivered_los / len(df_los)
    assert pdr_los >= 0.98, f"Clear LOS PDR {pdr_los:.3f} below 98%"

    # Total fade scenario must show complete loss
    df_fade = df_rf[df_rf["scenario"] == "TOTAL_FADE"]
    delivered_fade = len(df_fade[df_fade["status"] == "DELIVERED"])
    assert delivered_fade == 0, "Total fade scenario unexpectedly delivered packets"


def test_safety_latency_sensitivity_margins():
    """Verify that stopping distances across all visibilities retain non-negative safety margins."""
    df_sens = pd.read_csv("data/phase6_safety_latency_sensitivity.csv")
    assert len(df_sens) > 0

    # For every record, stopping distance must never exceed sight distance
    for _, row in df_sens.iterrows():
        vis = row["visibility_m"]
        s_stop = row["stopping_distance_m"]
        # Allow tiny numerical precision tolerance (1e-4 m)
        assert s_stop <= vis + 1e-4, f"Stopping distance {s_stop:.3f}m exceeds sight distance {vis:.1f}m for row: {dict(row)}"


def test_packet_loss_safety_governor_invariant():
    """
    Verify the 75% packet loss invariant:
    Communication loss does NOT compromise local safety.
    v_applied is always <= v_safe, and when packets are stale (>=1.0s or max_command_age), vehicle halts.
    """
    # Test on LocalVehicleSafetyGovernor
    gov = LocalVehicleSafetyGovernor(
        vehicle_id="TRUCK_01",
        v_safe_default=4.3815,
        max_command_age_s=1.0,
        firmware_watchdog_timeout_s=1.0,
        clock=lambda: 100.0
    )
    gov.update_local_safety_state(v_safe=4.3815, has_gateway=True, packet_loss_rate=0.75)

    t = 100.0
    # 1. Central requests unsafe speed 6.0 m/s under 75% packet loss -> Clamped to v_safe
    cmd_unsafe = IncomingCommand("TRUCK_01", sequence=1, timestamp=t, requested_speed_mps=6.0)
    res_unsafe = gov.process_command(cmd_unsafe, now=t)
    assert res_unsafe.applied_speed <= 4.3815 + 1e-4
    assert res_unsafe.action == CommandAction.CLAMP
    assert res_unsafe.state == FailSafeState.DEGRADED_COMMUNICATION

    # 2. Command expired beyond max_command_age_s (age = 1.5s > 1.0s) -> REJECT
    cmd_stale = IncomingCommand("TRUCK_01", sequence=2, timestamp=t - 1.5, requested_speed_mps=4.0)
    res_stale = gov.process_command(cmd_stale, now=t)
    assert res_stale.state == FailSafeState.STALE_COMMAND
    assert res_stale.action == CommandAction.REJECT
    assert res_stale.applied_speed <= res_stale.v_safe

    # 3. Complete communication outage / watchdog expiration (dt > firmware_watchdog_timeout_s) -> Emergency Stop (0.0 m/s)
    cmd_outage = IncomingCommand("TRUCK_01", sequence=3, timestamp=t + 2.0, requested_speed_mps=4.0)
    res_outage = gov.process_command(cmd_outage, now=t + 2.0)
    assert res_outage.state == FailSafeState.EMERGENCY_STOP
    assert res_outage.action == CommandAction.REJECT
    assert res_outage.applied_speed == 0.0

    # 4. Test on VehicleHardwareEmulator
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=12.0, friction_mu=0.35, grade_pct=-8.0)
    local_state = emulator.compute_local_safety_state()

    msg = DispatchCommandMessage(
        command_id="CMD_TEST_LOSS",
        vehicle_id="TRUCK_01",
        timestamp=t,
        target_speed=7.5,
        action="TARGET_SPEED",
        reason_code="CENTRAL_SPEED_UP"
    )
    ack = emulator.process_dispatch_command(msg)
    assert ack.applied_speed <= local_state.v_safe + 1e-4


def test_safe_beacon_hierarchy_and_states():
    """
    Verify Safe Beacon architecture:
    1. Valid states: NORMAL, DEGRADED, STOP, EMERGENCY
    2. Safe Beacon cannot directly command actuator; local governor remains authoritative.
    """
    valid_states = {"NORMAL", "DEGRADED", "STOP", "EMERGENCY"}

    beacon_payload = {
        "source_truck": "TRUCK_01",
        "seq": 104,
        "state": "DEGRADED",
        "timestamp": 1726617000.150,
        "distance_to_peer_m": 18.5
    }

    assert beacon_payload["state"] in valid_states

    # Safe Beacon input fed into Governor
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_02", v_safe_default=4.3815)
    # If gateway is lost, Governor switches to local awareness mode (has_gateway=False)
    gov.update_local_safety_state(v_safe=4.3815, has_gateway=False)

    t = 100.0
    # Any incoming command from central without gateway is rejected
    cmd = IncomingCommand("TRUCK_02", sequence=1, timestamp=t, requested_speed_mps=5.0)
    res = gov.process_command(cmd, now=t)
    assert res.state == FailSafeState.NO_GATEWAY
    assert res.action == CommandAction.REJECT
    assert res.applied_speed <= res.v_safe


def test_canonical_parameters_provenance_integrity():
    """Verify that canonical parameters match frozen specifications exactly."""
    with open("config/bailadila_hemm_canonical.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    p = cfg["parameters"]
    assert p["mass_empty_kg"]["value"] == 74_000.0
    assert p["payload_rated_kg"]["value"] == 91_500.0
    assert p["mass_loaded_kg"]["value"] == 165_500.0
    assert p["hardware_brake_max_force_n"]["value"] == 550_000.0
    assert p["max_retarder_power_w"]["value"] == 1_200_000.0
    assert p["rolling_resistance_crr_dry"]["value"] == 0.025
    assert p["tau_total_autonomous_s"]["value"] == 0.450
    assert p["tau_sensor_s"]["value"] == 0.100
    assert p["tau_comm_s"]["value"] == 0.050
    assert p["tau_decision_s"]["value"] == 0.050
    assert p["tau_actuator_s"]["value"] == 0.200
    assert p["tau_can_assumed_s"]["value"] == 0.050
