"""
FOG-ORCHESTRATOR 2.0 — Hardware Interface Emulator (HIL Bridge)
Emulates physical Vehicle A and Vehicle B microcontrollers (ESP32) and LoRa telemetry streams.
Enforces non-negotiable local safety governor clamping and fault injection capabilities.
"""

import time
import random
import math
from typing import Dict, Optional, Tuple
from contracts import (
    VehicleStateMessage, SafetyStateMessage, HealthMessage,
    DispatchCommandMessage, CommandAckMessage
)
from fog_safe.safety import solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel


class VehicleHardwareEmulator:
    """
    Software HIL emulator representing a physical mining truck equipped with ESP32, IMU, and LoRa.
    """
    def __init__(self, vehicle_id: str, initial_position: float = 0.0, segment_id: str = "ROAD_1"):
        self.vehicle_id = vehicle_id
        self.position = initial_position
        self.segment_id = segment_id
        self.speed_mps = 0.0
        self.acceleration_mps2 = 0.0
        self.is_loaded = False
        self.heading = 0.0
        self.mode = "traveling"
        
        # Telemetry & Network Health
        self.comm_state = "HEALTHY"
        self.latency_ms = 15.0
        self.packet_loss_rate = 0.0
        self.telemetry_active = True
        self.last_update_timestamp = time.time()
        self.stale_timeout_s = 5.0
        
        # Physics Vehicle & Env models
        self.phys_vehicle = MiningVehicle(is_loaded=self.is_loaded)
        self.env = EnvironmentState(r_effective=50.0)
        self.road = RoadSegment(percent_grade=0.0, speed_limit_kmh=50.0)
        self.comm = CommunicationModel()

    def update_environment(self, visibility_m: float, friction_mu: float, grade_pct: float, curve_radius_m: float = float('inf')):
        """Updates local environment parameters perceived by vehicle sensors."""
        self.env.r_effective = max(0.1, visibility_m)
        self.env.mu_true = max(0.05, min(0.85, friction_mu))
        self.road.percent_grade = grade_pct
        self.road.curve_radius = curve_radius_m

    def compute_local_safety_state(self) -> SafetyStateMessage:
        """
        Runs the non-negotiable Tier 1 local safety governor.
        Returns SafetyStateMessage with complete constraint breakdown.
        """
        # If communication is lost or telemetry is stale, fallback to LOCAL_SAFE mode
        now = time.time()
        is_stale = (now - self.last_update_timestamp) > self.stale_timeout_s
        
        if self.comm_state in ["LOST", "DISCONNECTED"] or not self.telemetry_active or is_stale:
            v_safe_fallback = 2.78  # 10 km/h safe fallback speed
            return SafetyStateMessage(
                vehicle_id=self.vehicle_id,
                timestamp=now,
                actual_speed=min(self.speed_mps, v_safe_fallback),
                v_safe=v_safe_fallback,
                h_safe=20.0,
                risk_level=0.5,
                active_constraint="COMMUNICATION_DEGRADED_FALLBACK",
                v_stop=v_safe_fallback,
                v_retarder=15.0,
                v_curve=15.0,
                v_mine=13.89,
                a_dec=2.0,
                s_stop=10.0,
                s_margin=5.0,
                is_safe=True
            )

        self.phys_vehicle.is_loaded = self.is_loaded
        res = solve_safe_speed(
            vehicle=self.phys_vehicle,
            road=self.road,
            env=self.env,
            comm=self.comm,
            mu_effective=self.env.mu_true,
            r_effective=self.env.r_effective
        )
        
        risk = 1.0 - min(1.0, max(0.0, self.env.r_effective - res.s_stop) / 50.0)

        return SafetyStateMessage(
            vehicle_id=self.vehicle_id,
            timestamp=now,
            actual_speed=self.speed_mps,
            v_safe=res.v_safe_ms,
            h_safe=res.s_stop + res.s_margin,
            risk_level=float(risk),
            active_constraint=res.primary_constraint,
            v_stop=res.candidate_limits_ms.get("v_stop", 0.0),
            v_retarder=res.candidate_limits_ms.get("v_retarder", 15.0),
            v_curve=res.candidate_limits_ms.get("v_curve", 15.0),
            v_mine=res.candidate_limits_ms.get("v_mine", 13.89),
            a_dec=res.a_dec,
            s_stop=res.s_stop,
            s_margin=res.s_margin,
            is_safe=res.is_safe
        )

    def process_dispatch_command(self, cmd: DispatchCommandMessage) -> CommandAckMessage:
        """
        Ingests a central optimizer DispatchCommand.
        ENFORCES NON-NEGOTIABLE LOCAL SAFETY CLAMP:
        applied_speed = min(v_command, v_safe)
        """
        now = time.time()
        
        # Simulate packet loss
        if random.random() < self.packet_loss_rate or self.comm_state in ["LOST", "DISCONNECTED"]:
            return CommandAckMessage(
                command_id=cmd.command_id,
                vehicle_id=self.vehicle_id,
                timestamp=now,
                status="REJECTED",
                applied_speed=self.speed_mps,
                reason="Packet dropped or communication lost"
            )

        safety = self.compute_local_safety_state()
        v_safe = safety.v_safe

        if cmd.action in ["HOLD", "STOP"]:
            target = 0.0
            status = "ACCEPTED"
            reason = "Hold/Stop executed by vehicle local control"
        else:
            cmd_target = cmd.target_speed
            if cmd_target > v_safe:
                target = v_safe
                status = "CLAMPED"
                reason = f"Command speed ({cmd_target:.2f} m/s) exceeded safe ceiling ({v_safe:.2f} m/s). Clamped by local governor."
            else:
                target = cmd_target
                status = "ACCEPTED"
                reason = "Command within safe envelope"

        # Apply speed change
        self.speed_mps = target
        self.last_update_timestamp = now

        return CommandAckMessage(
            command_id=cmd.command_id,
            vehicle_id=self.vehicle_id,
            timestamp=now,
            status=status,
            applied_speed=target,
            reason=reason
        )

    def step_simulation(self, dt: float = 1.0):
        """Advances vehicle motion equations for time step dt."""
        now = time.time()
        safety = self.compute_local_safety_state()
        
        # Enforce speed clamp continuously
        if self.speed_mps > safety.v_safe:
            self.speed_mps = safety.v_safe
            
        self.position += self.speed_mps * dt
        self.last_update_timestamp = now

    def get_telemetry_messages(self) -> Tuple[VehicleStateMessage, SafetyStateMessage, HealthMessage]:
        """Generates outgoing telemetry packets for central digital twin / HMI."""
        now = time.time()
        safety = self.compute_local_safety_state()
        
        v_msg = VehicleStateMessage(
            vehicle_id=self.vehicle_id,
            timestamp=now,
            position=self.position,
            segment_id=self.segment_id,
            speed_mps=self.speed_mps,
            acceleration_mps2=self.acceleration_mps2,
            heading=self.heading,
            mode=self.mode,
            communication_state=self.comm_state,
            is_loaded=self.is_loaded
        )
        
        age_ms = (now - self.last_update_timestamp) * 1000.0
        h_msg = HealthMessage(
            component_id=f"VEHICLE_EMULATOR_{self.vehicle_id}",
            timestamp=now,
            state=self.comm_state if self.telemetry_active else "OFFLINE",
            latency_ms=self.latency_ms,
            age_ms=age_ms,
            error_code=0 if self.comm_state == "HEALTHY" else 101
        )

        return v_msg, safety, h_msg
