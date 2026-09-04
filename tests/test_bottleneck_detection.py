from models.bottleneck import calculate_bottleneck_score


def test_bottleneck_score_calculation():
    # lambda = 15, mu = 10, queue = 4, max_q = 5, criticality = 4.0
    score = calculate_bottleneck_score(arrival_rate_vph=15.0, service_rate_vph=10.0, queue_length=4, criticality=4.0)
    # rho = 1.5, multiplier = 1 + 4/5 = 1.8, score = 1.5 * 1.8 * 4 = 10.8
    assert score > 5.0


def test_dynamic_bottleneck_shift():
    nodes = {
        "SHOVEL": {"lambda": 15.0, "mu": 15.0, "queue": 0, "criticality": 1.0},
        "INTERSECTION": {"lambda": 15.0, "mu": 60.0, "queue": 0, "criticality": 2.0},
        "CRUSHER": {"lambda": 15.0, "mu": 10.0, "queue": 4, "criticality": 4.0}
    }
    
    score_shovel = calculate_bottleneck_score(15.0, 15.0, 0, 1.0)
    score_intersection = calculate_bottleneck_score(15.0, 60.0, 0, 2.0)
    score_crusher = calculate_bottleneck_score(15.0, 10.0, 4, 4.0)

    # Crusher must be identified as primary bottleneck
    assert score_crusher > score_intersection
    assert score_crusher > score_shovel
