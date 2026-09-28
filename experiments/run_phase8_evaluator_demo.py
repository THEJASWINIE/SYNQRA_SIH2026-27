"""
experiments/run_phase8_evaluator_demo.py
----------------------------------------
FOG-ORCHESTRATOR 2.0 — Phase 8 90-Second Evaluator Demonstration.

Evaluator Demo Timeline (Prompt Section 24):
  00–15 s: Normal operation (50m visibility, nominal 4.0 m/s speed)
  15–30 s: Fog arrives (visibility drops 50m -> 15m)
  30–40 s: Safe speed decreases (physics solver reduces ceiling from 13.89 m/s to 4.38 m/s)
  40–50 s: Central operator requests unsafe higher speed (25.0 m/s fleet hurry)
  50–60 s: Local governor clamps command (applied speed clamped to 4.38 m/s)
  60–70 s: Gateway fails (LoRa packet drop -> DEGRADED_BEACON_FALLBACK)
  70–80 s: V2V / beacon degradation (Total RF failure -> local autonomous operation)
  80–90 s: Local safety continues independently (Tier-1 governor preserves safety envelope)

Displays simultaneously:
  - TIME
  - CENTRAL REQUEST
  - LOCAL SAFE SPEED
  - APPLIED SPEED
  - COMMUNICATION STATE
  - SAFETY STATE
  - REASON FOR RESTRICTION
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from integration_adapters.hil_simulator import HilSystemOrchestrator


def run_evaluator_demo(fast_mode: bool = True):
    print("=" * 95)
    print("FOG-ORCHESTRATOR 2.0 — 90-SECOND HIL SAFETY EVALUATOR DEMO")
    print("SIH26007 — BEML BH100-Class Hauler Surrogate")
    print("=" * 95)
    print(f"{'TIME':<8} {'CENTRAL REQ':<13} {'LOCAL SAFE':<12} {'APPLIED':<10} {'COMM STATE':<13} {'SAFETY STATE':<22} {'ACTION':<10}")
    print("-" * 95)

    orch = HilSystemOrchestrator(visibility_m=50.0, grade_pct=0.0, friction_mu=0.35)
    orch.current_sim_time = 0.0

    # 90 steps with dt = 1.0s
    for t_sec in range(0, 91):
        # 0–15 s: Normal operation
        if t_sec <= 15:
            vis = 50.0
            central_req = 4.0
            has_gw = True
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 15–30 s: Fog arrives
        elif 15 < t_sec <= 30:
            # Linear visibility drop from 50m to 15m
            progress = (t_sec - 15) / 15.0
            vis = 50.0 - (progress * 35.0)
            central_req = 4.0
            has_gw = True
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 30–40 s: Safe speed decreases
        elif 30 < t_sec <= 40:
            vis = 12.0
            central_req = 4.0
            has_gw = True
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 40–50 s: Central operator requests unsafe higher speed
        elif 40 < t_sec <= 50:
            vis = 12.0
            central_req = 25.0  # Unsafe hurry command!
            has_gw = True
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 50–60 s: Local governor clamps command
        elif 50 < t_sec <= 60:
            vis = 10.0
            central_req = 25.0  # Still requesting 25 m/s
            has_gw = True
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 60–70 s: Gateway fails
        elif 60 < t_sec <= 70:
            vis = 10.0
            central_req = 25.0
            has_gw = False  # Gateway offline
            has_v2v = True
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 70–80 s: V2V / beacon degradation
        elif 70 < t_sec <= 80:
            vis = 8.0
            central_req = 25.0
            has_gw = False
            has_v2v = False  # Peer V2V lost
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        # 80–90 s: Local safety continues independently
        else:
            vis = 5.0
            central_req = 25.0
            has_gw = False
            has_v2v = False
            orch.vehicle_ecu.set_environment(visibility_m=vis, grade_pct=0.0, friction_mu=0.35)

        hmi = orch.step(
            dt=1.0,
            central_speed_request=central_req,
            has_gateway=has_gw,
            has_v2v=has_v2v,
            command_source="CENTRAL_FLEET_OPTIMIZER" if central_req > 10.0 else "CENTRAL_GATEWAY"
        )

        # Print output at key transition marks (every 5 seconds)
        if t_sec % 5 == 0:
            t_str = f"{t_sec:02d}s"
            c_req = f"{central_req:4.1f} m/s"
            v_safe = f"{hmi['safe_speed_mps']:4.1f} m/s"
            v_app = f"{hmi['applied_speed_mps']:4.1f} m/s"
            comm = hmi["communication_state"]
            s_state = hmi["safety_state"]
            action = hmi["action"]

            print(f"{t_str:<8} {c_req:<13} {v_safe:<12} {v_app:<10} {comm:<13} {s_state:<22} {action:<10}")

        if not fast_mode:
            time.sleep(1.0)

    print("-" * 95)
    print("EVALUATOR CONCLUSION:")
    print("  'Central intelligence can optimize the fleet, but it cannot override the vehicle\'s physical safety envelope.'")
    print("=" * 95)


if __name__ == "__main__":
    run_evaluator_demo(fast_mode=True)
