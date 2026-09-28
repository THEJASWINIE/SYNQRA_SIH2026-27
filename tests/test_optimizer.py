import pytest
from control.arrival_shaping import ArrivalShaper


def test_arrival_shaper_optimization_decision():
    shaper = ArrivalShaper(target_node_id="CRUSHER", base_shovel_service_rate_vph=15.0)

    # Inactive shaping -> Nominal release delay (240s)
    delay_inactive = shaper.update_release_delay(shaping_active=False, downstream_queue_len=1, downstream_service_rate_vph=10.0, delta_buffer_vph=0.0)
    assert delay_inactive == 240.0

    # Active shaping with queue buildup -> Throttled release delay (>= 600s)
    delay_active = shaper.update_release_delay(shaping_active=True, downstream_queue_len=3, downstream_service_rate_vph=10.0, delta_buffer_vph=0.0)
    assert delay_active >= 600.0
    assert delay_active > delay_inactive
