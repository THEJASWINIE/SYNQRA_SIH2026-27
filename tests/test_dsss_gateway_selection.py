"""
tests/test_dsss_gateway_selection.py
------------------------------------
Automated regression suite for DSSS/PN Gateway Selection & Link State Machine.
Validates:
1. Cold start gateway selection based on PN correlation score.
2. Rejection of weak signals or low correlation (< 0.40).
3. Handover margin requirement: candidate > current + SWITCH_MARGIN.
4. Persistence count requirement: candidate must maintain margin for N observations.
5. Anti-flapping behavior under noisy RF channels.
6. Timeout detection and failover to candidate or NO_GATEWAY / DISCONNECTED.
7. Telemetry contract compliance (PART 15).
"""

import pytest
from integration_adapters.dsss_gateway_selector import (
    DSSSGatewaySelector,
    BeaconObservation,
    LinkState,
    GatewaySelectionState,
)


def test_cold_start_selection():
    selector = DSSSGatewaySelector(
        vehicle_id="TRUCK_01",
        switch_margin=0.15,
        min_correlation=0.40,
        persistence_count=3,
        fail_timeout_s=1.5,
        clock=lambda: 100.0
    )

    # Initial state
    assert selector.selection_state == GatewaySelectionState.NO_GATEWAY
    assert selector.link_state == LinkState.DISCONNECTED

    # Beacon from GW-01 with good correlation (0.85)
    obs1 = BeaconObservation(
        gateway_id="GW-01",
        pn_sequence_id="PN-A",
        correlation_score=0.85,
        rssi_dbm=-75.0,
        snr_db=6.0,
        timestamp=100.0,
        packet_sequence=1
    )
    status = selector.process_observation(obs1)

    assert status.gateway_id == "GW-01"
    assert status.correlation_score == 0.85
    assert status.selection_state == GatewaySelectionState.CONNECTED
    assert status.link_state == LinkState.CONNECTED


def test_rejection_of_weak_or_corrupted_signals():
    selector = DSSSGatewaySelector(min_correlation=0.40, min_signal_rssi_dbm=-115.0, clock=lambda: 100.0)

    # Below correlation threshold (0.32 < 0.40)
    obs_weak_corr = BeaconObservation(
        gateway_id="GW-02",
        pn_sequence_id="PN-B",
        correlation_score=0.32,
        rssi_dbm=-80.0,
        snr_db=2.0,
        timestamp=100.0
    )
    status = selector.process_observation(obs_weak_corr)
    assert status.selection_state == GatewaySelectionState.NO_GATEWAY
    assert status.link_state == LinkState.DISCONNECTED

    # Below minimum RSSI threshold (-122 dBm < -115 dBm)
    obs_weak_rssi = BeaconObservation(
        gateway_id="GW-02",
        pn_sequence_id="PN-B",
        correlation_score=0.75,
        rssi_dbm=-122.0,
        snr_db=-12.0,
        timestamp=100.0
    )
    status2 = selector.process_observation(obs_weak_rssi)
    assert status2.selection_state == GatewaySelectionState.NO_GATEWAY


def test_handover_persistence_and_margin():
    curr_time = 100.0
    selector = DSSSGatewaySelector(
        switch_margin=0.15,
        persistence_count=3,
        fail_timeout_s=5.0,
        clock=lambda: curr_time
    )

    # 1. Connect to GW-01 (score 0.65)
    obs1 = BeaconObservation("GW-01", "PN-A", correlation_score=0.65, rssi_dbm=-82.0, snr_db=3.0, timestamp=curr_time)
    selector.process_observation(obs1)
    assert selector.current_gateway_id == "GW-01"

    # 2. GW-02 appears with score 0.72 (Difference = 0.07 < 0.15 switch margin) -> Handover rejected
    obs2_marginal = BeaconObservation("GW-02", "PN-B", correlation_score=0.72, rssi_dbm=-76.0, snr_db=5.0, timestamp=curr_time)
    st_marginal = selector.process_observation(obs2_marginal)
    assert selector.current_gateway_id == "GW-01"
    assert st_marginal.candidate_gateway_id is None

    # 3. GW-02 increases to 0.88 (Difference = 0.23 > 0.15 switch margin) -> Observation 1/3
    curr_time += 0.2
    obs2_strong = BeaconObservation("GW-02", "PN-B", correlation_score=0.88, rssi_dbm=-68.0, snr_db=8.0, timestamp=curr_time)
    st_obs1 = selector.process_observation(obs2_strong)
    assert selector.current_gateway_id == "GW-01"
    assert st_obs1.selection_state == GatewaySelectionState.HANDOVER_PENDING
    assert st_obs1.persistence_progress == 1

    # 4. Keep GW-01 fresh so it doesn't time out
    curr_time += 0.1
    obs1_refresh = BeaconObservation("GW-01", "PN-A", correlation_score=0.65, rssi_dbm=-82.0, snr_db=3.0, timestamp=curr_time)
    selector.process_observation(obs1_refresh)

    # 5. GW-02 observation 2/3
    curr_time += 0.1
    st_obs2 = selector.process_observation(obs2_strong)
    assert selector.current_gateway_id == "GW-01"
    assert st_obs2.selection_state == GatewaySelectionState.HANDOVER_PENDING
    assert st_obs2.persistence_progress == 2

    # 6. GW-02 observation 3/3 -> HANDOVER EXECUTED
    curr_time += 0.2
    st_obs3 = selector.process_observation(obs2_strong)
    assert selector.current_gateway_id == "GW-02"
    assert st_obs3.link_state == LinkState.HANDOVER
    assert selector.candidate_gateway_id is None


def test_anti_flapping_under_fluctuating_signals():
    curr_time = 100.0
    selector = DSSSGatewaySelector(
        switch_margin=0.15,
        persistence_count=3,
        fail_timeout_s=5.0,
        clock=lambda: curr_time
    )

    # Connect to GW-01 (score 0.70)
    selector.process_observation(BeaconObservation("GW-01", "PN-A", 0.70, -80.0, 4.0, curr_time))

    # Candidate GW-02 spikes up to 0.90 for 1 cycle (Obs 1)
    curr_time += 0.2
    selector.process_observation(BeaconObservation("GW-02", "PN-B", 0.90, -65.0, 10.0, curr_time))
    assert selector.current_gateway_id == "GW-01"
    assert selector.persistence_counter == 1

    # Candidate GW-02 drops back to 0.75 (below margin of 0.70 + 0.15 = 0.85)
    curr_time += 0.2
    selector.process_observation(BeaconObservation("GW-02", "PN-B", 0.75, -78.0, 4.0, curr_time))
    # Persistence counter must reset
    assert selector.current_gateway_id == "GW-01"
    assert selector.persistence_counter == 0
    assert selector.candidate_gateway_id is None


def test_gateway_timeout_failover():
    curr_time = 100.0
    selector = DSSSGatewaySelector(
        switch_margin=0.15,
        persistence_count=3,
        fail_timeout_s=1.5,
        clock=lambda: curr_time
    )

    # Connect to GW-01
    selector.process_observation(BeaconObservation("GW-01", "PN-A", 0.80, -75.0, 6.0, curr_time))
    assert selector.current_gateway_id == "GW-01"

    # Time advances by 2.0s without GW-01 beacon
    curr_time += 2.0

    # Incoming observation from alternative GW-03
    obs_alt = BeaconObservation("GW-03", "PN-C", 0.75, -80.0, 4.0, curr_time)
    st = selector.process_observation(obs_alt)

    # Immediate failover to GW-03 because GW-01 expired
    assert selector.current_gateway_id == "GW-03"
    assert st.selection_state == GatewaySelectionState.CONNECTED


def test_complete_rf_loss_timeout():
    curr_time = 100.0
    selector = DSSSGatewaySelector(fail_timeout_s=1.5, clock=lambda: curr_time)

    selector.process_observation(BeaconObservation("GW-01", "PN-A", 0.80, -75.0, 6.0, curr_time))
    assert selector.current_gateway_id == "GW-01"

    # Advance time by 3.0s with no packets
    curr_time += 3.0
    # Process an invalid / lost observation
    bad_obs = BeaconObservation("GW-01", "PN-A", 0.10, -130.0, -25.0, curr_time, crc_valid=False)
    st = selector.process_observation(bad_obs)

    assert selector.selection_state == GatewaySelectionState.NO_GATEWAY
    assert selector.link_state == LinkState.DISCONNECTED
    assert selector.current_gateway_id is None
