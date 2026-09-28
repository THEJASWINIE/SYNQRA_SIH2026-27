import pytest
from models.queue_model import ServiceQueue, calculate_next_queue_size
from models.vehicle import Vehicle
from run_baseline_vs_orchestrator import load_configs


def test_queue_mass_balance_and_growth():
    queue = ServiceQueue("CRUSHER", service_rate_vph=10.0)
    assert queue.length == 0

    vehicle_cfg = load_configs()[0]

    v1 = Vehicle("TRUCK_01", vehicle_cfg, "CRUSHER")
    v2 = Vehicle("TRUCK_02", vehicle_cfg, "CRUSHER")

    queue.add_vehicle(v1)
    queue.add_vehicle(v2)
    assert queue.length == 2

    # Step service by 360 seconds (service time = 3600 / 10 = 360s)
    discharged = queue.step(dt=360.0)
    assert len(discharged) == 1
    assert queue.length == 1


def test_analytical_queue_dynamics_equation():
    # Q(t+dt) = max(0, Q(t) + arrivals - departures)
    q_next = calculate_next_queue_size(q_current=2.0, arrivals=5.0, departures=3.0)
    assert q_next == 4.0

    q_empty = calculate_next_queue_size(q_current=1.0, arrivals=0.0, departures=3.0)
    assert q_empty == 0.0
