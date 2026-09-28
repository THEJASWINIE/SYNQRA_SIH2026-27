"""
integration_adapters/dsss_gateway_selector.py
---------------------------------------------
FOG-ORCHESTRATOR 2.0 — DSSS / PN Gateway Selection & Link State Tracking.

IMPORTANT ENGINEERING DISCLAIMER (PART 12):
The DSSS/PN correlation model implemented here is an ARCHITECTURAL RESEARCH AND
SIMULATION MODEL. The physical prototype currently operates on Semtech SX1278
CSS-LoRa hardware at 433 MHz. This module models the planned multi-gateway
pseudo-noise (PN) signature synchronization, correlation scoring, anti-flapping
hysteresis, and handover logic. It does NOT claim that the physical SX1278 Ra-02
chip is executing physical DSSS chipping sequences.

Gateway Selection States:
  - CONNECTED: Operating reliably with primary gateway.
  - DEGRADED: Operating with primary gateway, but correlation or packet loss degraded.
  - HANDOVER_PENDING: Candidate gateway has met switch margin, accumulating persistence count.
  - NO_GATEWAY: No gateway meets minimum correlation/signal threshold, or timeout expired.

Link States (PART 15):
  - CONNECTED: Valid packet flow and high correlation.
  - DEGRADED: Signal or packet loss within degraded thresholds.
  - HANDOVER: Actively transitioning between gateways.
  - DISCONNECTED: No valid gateway link.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("DSSSGayewaySelector")


class LinkState(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    HANDOVER = "HANDOVER"
    DISCONNECTED = "DISCONNECTED"


class GatewaySelectionState(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    HANDOVER_PENDING = "HANDOVER_PENDING"
    NO_GATEWAY = "NO_GATEWAY"


@dataclass
class BeaconObservation:
    """Represents a received gateway PN beacon or RF telemetry frame."""
    gateway_id: str
    pn_sequence_id: str
    correlation_score: float      # Normalized [0.0, 1.0] PN sequence correlation
    rssi_dbm: float               # Received Signal Strength Indicator (dBm)
    snr_db: float                 # Signal-to-Noise Ratio (dB)
    timestamp: float              # Observation epoch seconds
    packet_sequence: int = 0
    crc_valid: bool = True


@dataclass
class DSSSTelemetryStatus:
    """Standard telemetry output payload per PART 15."""
    gateway_id: str
    correlation_score: float
    rssi_dbm: float
    snr_db: float
    packet_sequence: int
    packet_loss_rate: float
    last_valid_packet_timestamp: float
    link_state: LinkState
    selection_state: GatewaySelectionState
    candidate_gateway_id: Optional[str] = None
    persistence_progress: int = 0


class DSSSGatewaySelector:
    """
    Evaluates multi-gateway PN beacon correlation and manages gateway selection
    with anti-flapping hysteresis and persistence checking.
    """

    def __init__(
        self,
        vehicle_id: str = "TRUCK_01",
        config_path: Optional[str] = None,
        switch_margin: float = 0.15,
        min_correlation: float = 0.40,
        degraded_correlation: float = 0.60,
        fail_timeout_s: float = 1.50,
        persistence_count: int = 3,
        min_signal_rssi_dbm: float = -115.0,
        clock=time.time
    ):
        self.vehicle_id = vehicle_id
        self.clock = clock

        # Default configuration
        self.switch_margin = switch_margin
        self.min_correlation = min_correlation
        self.degraded_correlation = degraded_correlation
        self.fail_timeout_s = fail_timeout_s
        self.persistence_count = persistence_count
        self.min_signal_rssi_dbm = min_signal_rssi_dbm

        # Load from config file if available
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)

        # Internal state machine
        self.current_gateway_id: Optional[str] = None
        self.candidate_gateway_id: Optional[str] = None
        self.selection_state: GatewaySelectionState = GatewaySelectionState.NO_GATEWAY
        self.link_state: LinkState = LinkState.DISCONNECTED

        # Observation tracking
        self.last_observations: Dict[str, BeaconObservation] = {}
        self.persistence_counter: int = 0
        self.last_valid_packet_time: float = 0.0
        self.latest_sequence: int = 0
        self.packet_loss_window: List[bool] = []  # True = received, False = lost
        self.max_window_size = 20

    def _load_config(self, path: str):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            p = data.get("parameters", {})
            self.switch_margin = p.get("switch_margin_score", self.switch_margin)
            self.min_correlation = p.get("min_correlation_threshold", self.min_correlation)
            self.degraded_correlation = p.get("degraded_correlation_threshold", self.degraded_correlation)
            self.fail_timeout_s = p.get("fail_timeout_seconds", self.fail_timeout_s)
            self.persistence_count = p.get("persistence_count", self.persistence_count)
            self.min_signal_rssi_dbm = p.get("min_signal_rssi_dbm", self.min_signal_rssi_dbm)
        except Exception as e:
            logger.warning(f"Could not load gateway config {path}: {e}")

    def update_packet_loss(self, delivered: bool):
        self.packet_loss_window.append(delivered)
        if len(self.packet_loss_window) > self.max_window_size:
            self.packet_loss_window.pop(0)

    @property
    def current_packet_loss_rate(self) -> float:
        if not self.packet_loss_window:
            return 0.0
        lost_count = sum(1 for d in self.packet_loss_window if not d)
        return float(lost_count) / float(len(self.packet_loss_window))

    def process_observation(self, obs: BeaconObservation) -> DSSSTelemetryStatus:
        """
        Ingests a new gateway beacon/packet observation, updates the state machine,
        and returns the current link and selection telemetry.
        """
        now = self.clock()
        obs_time = obs.timestamp if obs.timestamp > 0 else now

        # 1. Basic validity check
        is_physically_valid = (
            obs.crc_valid
            and obs.rssi_dbm >= self.min_signal_rssi_dbm
            and obs.correlation_score >= self.min_correlation
            and not math.isnan(obs.correlation_score)
        )

        if is_physically_valid:
            self.last_observations[obs.gateway_id] = obs
            self.update_packet_loss(delivered=True)
            self.last_valid_packet_time = obs_time
            if obs.packet_sequence > self.latest_sequence:
                self.latest_sequence = obs.packet_sequence
        else:
            self.update_packet_loss(delivered=False)

        # 2. Check for timeout on current gateway
        current_timed_out = False
        if self.current_gateway_id:
            last_current = self.last_observations.get(self.current_gateway_id)
            if not last_current or (now - last_current.timestamp) > self.fail_timeout_s:
                current_timed_out = True

        # 3. Evaluate best viable gateway candidate
        best_gw_id: Optional[str] = None
        best_score = -1.0

        for gw_id, last_obs in list(self.last_observations.items()):
            # Expire stale observations
            if (now - last_obs.timestamp) > self.fail_timeout_s:
                continue
            if last_obs.correlation_score > best_score:
                best_score = last_obs.correlation_score
                best_gw_id = gw_id

        # 4. State Machine Transition Logic
        if self.current_gateway_id is None:
            # Cold start: select best gateway if it satisfies min correlation
            if best_gw_id and best_score >= self.min_correlation:
                self.current_gateway_id = best_gw_id
                self.candidate_gateway_id = None
                self.persistence_counter = 0
                self._update_connected_or_degraded(best_score)
            else:
                self.selection_state = GatewaySelectionState.NO_GATEWAY
                self.link_state = LinkState.DISCONNECTED

        elif current_timed_out:
            # Immediate failover if current gateway disappeared
            logger.info(f"Gateway {self.current_gateway_id} timed out on {self.vehicle_id}")
            if best_gw_id and best_gw_id != self.current_gateway_id and best_score >= self.min_correlation:
                self.current_gateway_id = best_gw_id
                self.candidate_gateway_id = None
                self.persistence_counter = 0
                self._update_connected_or_degraded(best_score)
            else:
                self.current_gateway_id = None
                self.candidate_gateway_id = None
                self.persistence_counter = 0
                self.selection_state = GatewaySelectionState.NO_GATEWAY
                self.link_state = LinkState.DISCONNECTED

        else:
            # Current gateway is active. Evaluate potential handover to candidate
            current_obs = self.last_observations[self.current_gateway_id]
            current_score = current_obs.correlation_score

            # Check if an alternative gateway beats current by switch margin
            if (
                best_gw_id
                and best_gw_id != self.current_gateway_id
                and best_score > (current_score + self.switch_margin)
            ):
                if obs.gateway_id == best_gw_id:
                    if self.candidate_gateway_id == best_gw_id:
                        self.persistence_counter += 1
                    else:
                        self.candidate_gateway_id = best_gw_id
                        self.persistence_counter = 1

                if self.persistence_counter >= self.persistence_count:
                    # Execute Handover
                    logger.info(
                        f"Handover {self.vehicle_id}: {self.current_gateway_id} -> "
                        f"{self.candidate_gateway_id} (score {current_score:.2f} -> {best_score:.2f})"
                    )
                    self.current_gateway_id = self.candidate_gateway_id
                    self.candidate_gateway_id = None
                    self.persistence_counter = 0
                    self.link_state = LinkState.HANDOVER
                    self.selection_state = GatewaySelectionState.CONNECTED
                else:
                    # Handover Pending
                    self.selection_state = GatewaySelectionState.HANDOVER_PENDING
                    self.link_state = LinkState.DEGRADED if current_score < self.degraded_correlation else LinkState.CONNECTED
            else:
                # No handover candidate satisfies switch margin; reset candidate tracking
                self.candidate_gateway_id = None
                self.persistence_counter = 0
                self._update_connected_or_degraded(current_score)

        # 5. Build Telemetry Response
        active_gw = self.current_gateway_id or "NONE"
        active_obs = self.last_observations.get(self.current_gateway_id) if self.current_gateway_id else None

        active_corr = active_obs.correlation_score if active_obs else 0.0
        active_rssi = active_obs.rssi_dbm if active_obs else -120.0
        active_snr = active_obs.snr_db if active_obs else -20.0
        active_seq = active_obs.packet_sequence if active_obs else self.latest_sequence

        return DSSSTelemetryStatus(
            gateway_id=active_gw,
            correlation_score=round(active_corr, 4),
            rssi_dbm=round(active_rssi, 2),
            snr_db=round(active_snr, 2),
            packet_sequence=active_seq,
            packet_loss_rate=round(self.current_packet_loss_rate, 4),
            last_valid_packet_timestamp=self.last_valid_packet_time,
            link_state=self.link_state,
            selection_state=self.selection_state,
            candidate_gateway_id=self.candidate_gateway_id,
            persistence_progress=self.persistence_counter
        )

    def _update_connected_or_degraded(self, score: float):
        loss_rate = self.current_packet_loss_rate
        if score < self.degraded_correlation or loss_rate >= 0.25:
            self.selection_state = GatewaySelectionState.DEGRADED
            self.link_state = LinkState.DEGRADED
        else:
            self.selection_state = GatewaySelectionState.CONNECTED
            self.link_state = LinkState.CONNECTED


# ==============================================================================
# PHASE 9 INTEGRATION LAYER: CLEAN DSSS / PN & LORA RF HARDWARE ABSTRACTION
# ==============================================================================

class CarrierModulation(str, Enum):
    CSS_LORA = "CSS_LORA"                   # Physical hardware prototype (Semtech SX1278 @ 433 MHz)
    DSSS_PN_SIMULATED = "DSSS_PN_SIMULATED" # Research & target military/mining PN spread-spectrum model


@dataclass
class CommunicationLink:
    """Standardized physical or emulated link carrier state."""
    gateway_id: str
    rssi_dbm: float
    snr_db: float
    packet_loss_rate: float
    carrier_type: CarrierModulation
    timestamp: float
    raw_payload: str = ""
    is_crc_valid: bool = True


class RFHardwareAdapter:
    """
    Hardware abstraction layer bridging physical SX1278 CSS LoRa packets
    and simulated DSSS PN sequence frames into a uniform CommunicationLink.
    """
    def __init__(self, carrier_type: CarrierModulation = CarrierModulation.CSS_LORA):
        self.carrier_type = carrier_type

    def adapt_physical_lora_frame(
        self,
        raw_packet: str,
        rssi_dbm: float,
        snr_db: float,
        gateway_id: str = "GW_RAMP_01",
        timestamp: Optional[float] = None
    ) -> CommunicationLink:
        ts = timestamp if timestamp is not None else time.time()
        return CommunicationLink(
            gateway_id=gateway_id,
            rssi_dbm=rssi_dbm,
            snr_db=snr_db,
            packet_loss_rate=0.0,
            carrier_type=CarrierModulation.CSS_LORA,
            timestamp=ts,
            raw_payload=raw_packet,
            is_crc_valid=True
        )


class GatewayCorrelationEngine:
    """
    Evaluates correlation score from RF link metrics or PN chipping sequence.
    """
    def __init__(self, min_rssi: float = -115.0, min_snr: float = -10.0):
        self.min_rssi = min_rssi
        self.min_snr = min_snr

    def evaluate_correlation(self, link: CommunicationLink) -> float:
        if link.carrier_type == CarrierModulation.DSSS_PN_SIMULATED:
            return max(0.0, min(1.0, 1.0 - link.packet_loss_rate))
        # For CSS LoRa prototype: compute normalized link quality correlation proxy
        rssi_norm = max(0.0, min(1.0, (link.rssi_dbm - self.min_rssi) / 65.0))
        snr_norm = max(0.0, min(1.0, (link.snr_db - self.min_snr) / 20.0))
        corr_proxy = 0.6 * rssi_norm + 0.4 * snr_norm
        return round(max(0.10, min(1.0, corr_proxy)), 4)


class GatewaySelectionStateMachine:
    """
    Wraps DSSSGatewaySelector to manage state transitions:
    NO_GATEWAY, CONNECTED, DEGRADED, HANDOVER_PENDING, DISCONNECTED.
    Logs every gateway transition with complete audit trail.
    """
    def __init__(self, selector: Optional[DSSSGatewaySelector] = None, clock: Callable[[], float] = time.time):
        self.selector = selector or DSSSGatewaySelector(clock=clock)
        self.clock = clock
        self.transition_log: List[Dict[str, Any]] = []

    def update(self, link: CommunicationLink, correlation_score: float) -> DSSSTelemetryStatus:
        obs = BeaconObservation(
            gateway_id=link.gateway_id,
            pn_sequence_id=f"PN_{link.gateway_id}",
            correlation_score=correlation_score,
            rssi_dbm=link.rssi_dbm,
            snr_db=link.snr_db,
            timestamp=link.timestamp,
            crc_valid=link.is_crc_valid
        )
        prev_state = self.selector.selection_state
        prev_gw = self.selector.current_gateway_id
        status = self.selector.process_observation(obs)

        # Log state transition if changed
        if status.selection_state != prev_state or status.gateway_id != prev_gw:
            self.transition_log.append({
                "timestamp": link.timestamp,
                "old_gateway": prev_gw,
                "candidate_gateway": status.candidate_gateway_id,
                "correlation_current": status.correlation_score,
                "correlation_candidate": correlation_score if status.candidate_gateway_id else 0.0,
                "RSSI": link.rssi_dbm,
                "SNR": link.snr_db,
                "packet_loss": status.packet_loss_rate,
                "reason": f"Transition from {prev_state.value if hasattr(prev_state, 'value') else prev_state} to {status.selection_state.value if hasattr(status.selection_state, 'value') else status.selection_state}",
                "new_state": status.selection_state.value if hasattr(status.selection_state, "value") else str(status.selection_state)
            })
        return status


class SafetyOrchestratorLink:
    """
    Safety Orchestrator bridge receiving chosen gateway, link quality,
    and enforcing fallback when DISCONNECTED or NO_GATEWAY.
    """
    def __init__(self, state_machine: GatewaySelectionStateMachine):
        self.state_machine = state_machine

    def get_orchestrator_comms_status(self) -> Dict[str, Any]:
        sel = self.state_machine.selector
        return {
            "active_gateway": sel.current_gateway_id or "NONE",
            "selection_state": sel.selection_state.value if hasattr(sel.selection_state, "value") else str(sel.selection_state),
            "link_state": sel.link_state.value if hasattr(sel.link_state, "value") else str(sel.link_state),
            "packet_loss_rate": sel.current_packet_loss_rate,
            "is_connected": sel.link_state == LinkState.CONNECTED,
            "is_degraded": sel.link_state == LinkState.DEGRADED,
            "is_disconnected": sel.link_state in [LinkState.DISCONNECTED, LinkState.HANDOVER]
        }

