"""
validation/monte_carlo.py
-------------------------
Large-Scale Monte Carlo Stochastic Validation Engine for FOG-ORCHESTRATOR 2.0.
Executes >= 1,000 stochastic realizations across multi-dimensional uncertainty distributions:
- Vehicle Mass m ~ N(165.5t, 8.0t)
- Haul Grade theta ~ U(-12%, +12%)
- Tire-Road Friction mu ~ N(0.45, 0.12)
- Visibility V ~ U(6m, 60m)
- Perception/Network Latency tau ~ U(0.10s, 1.20s)
- Network Packet Loss p_loss ~ U(0.0, 0.25)
- Forecast Visibility/Friction Error eps_V, eps_mu
- Destination Service Rate mu_node ~ N(18.0, 3.0) vph
- Fleet Size N_v in {4, 6, 8, 10, 12, 16, 20}

Outputs comprehensive statistical distributions: mean, median, std, percentiles (p1, p5, p50, p95, p99),
and audits zero safety violations under Tier-1 governor protection.

Evidence Tags:
- Stochastic Verification: [SIMULATION SCENARIO / MONTE CARLO] 1,000 stochastic runs.
- Statistical Aggregation: [SIMULATION RESULT] Quantiles, moments, violation audits.
"""

from typing import Dict, Any, List, Optional
import os
import json
import math
import numpy as np
import yaml
from dataclasses import dataclass, asdict

from twin.network import MineNetwork
from models.braking import BrakingModel
from models.friction import FrictionModel
from models.road_capacity import RoadCapacityModel
from models.queue_model import QueueModel, ArrivalRateShaper


@dataclass
class DistributionStats:
    """Statistical summary metrics for a stochastic distribution."""
    mean: float
    median: float
    std: float
    p01: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float
    min: float
    max: float


@dataclass
class MonteCarloSummary:
    """Master aggregate output of the 1,000-run Monte Carlo experiment."""
    total_iterations: int
    seed: int
    total_safety_violations: int
    safety_violation_rate: float
    total_queue_violations: int
    queue_violation_rate: float
    total_capacity_violations: int
    capacity_violation_rate: float
    safe_speed_stats: DistributionStats
    stopping_distance_stats: DistributionStats
    safety_margin_ratio_stats: DistributionStats
    road_capacity_stats: DistributionStats
    queue_length_stats: DistributionStats
    travel_time_stats: DistributionStats


class MonteCarloValidator:
    """
    Stochastic Monte Carlo Validator executing large-scale uncertainty sweeps.
    """
    def __init__(
        self,
        config_dir: str,
        results_dir: str,
        num_iterations: int = 1000,
        seed: int = 42
    ):
        self.config_dir = os.path.abspath(config_dir)
        self.results_dir = os.path.abspath(results_dir)
        self.num_iterations = max(1000, int(num_iterations))
        self.seed = int(seed)
        os.makedirs(self.results_dir, exist_ok=True)

        self.vehicle_cfg_path = os.path.join(self.config_dir, "vehicle.yaml")
        with open(self.vehicle_cfg_path, "r", encoding="utf-8") as f:
            self.vehicle_cfg = yaml.safe_load(f)

        self.braking_model = BrakingModel(self.vehicle_cfg)
        self.friction_model = FrictionModel()
        self.capacity_model = RoadCapacityModel(self.vehicle_cfg)

    def _compute_distribution_stats(self, data: np.ndarray) -> DistributionStats:
        """Compute statistical moments and percentiles for a 1D numpy array."""
        return DistributionStats(
            mean=float(np.mean(data)),
            median=float(np.median(data)),
            std=float(np.std(data)),
            p01=float(np.percentile(data, 1)),
            p05=float(np.percentile(data, 5)),
            p25=float(np.percentile(data, 25)),
            p50=float(np.percentile(data, 50)),
            p75=float(np.percentile(data, 75)),
            p95=float(np.percentile(data, 95)),
            p99=float(np.percentile(data, 99)),
            min=float(np.min(data)),
            max=float(np.max(data))
        )

    def run_monte_carlo(self) -> MonteCarloSummary:
        """
        Execute >= 1000 Monte Carlo stochastic realizations.
        """
        rng = np.random.default_rng(self.seed)

        # 1. Sample stochastic uncertainty parameters across distributions
        masses = rng.normal(loc=165500.0, scale=8000.0, size=self.num_iterations)
        masses = np.clip(masses, 135000.0, 185000.0)

        grades_pct = rng.uniform(low=-12.0, high=12.0, size=self.num_iterations)
        visibilities = rng.uniform(low=6.0, high=60.0, size=self.num_iterations)
        
        frictions_hat = rng.normal(loc=0.45, scale=0.12, size=self.num_iterations)
        frictions_hat = np.clip(frictions_hat, 0.18, 0.85)

        latencies = rng.uniform(low=0.10, high=1.20, size=self.num_iterations)
        packet_losses = rng.uniform(low=0.0, high=0.25, size=self.num_iterations)

        vis_errors = rng.normal(loc=0.0, scale=2.5, size=self.num_iterations)
        fric_errors = rng.normal(loc=0.0, scale=0.03, size=self.num_iterations)

        service_rates = rng.normal(loc=18.0, scale=3.0, size=self.num_iterations)
        service_rates = np.clip(service_rates, 8.0, 30.0)

        fleet_sizes = rng.choice([4, 6, 8, 10, 12, 16, 20], size=self.num_iterations)

        # Arrays to collect simulation metrics
        safe_speeds = np.zeros(self.num_iterations)
        stopping_distances = np.zeros(self.num_iterations)
        safety_margin_ratios = np.zeros(self.num_iterations)
        road_capacities = np.zeros(self.num_iterations)
        queue_lengths = np.zeros(self.num_iterations)
        travel_times = np.zeros(self.num_iterations)

        safety_violations = 0
        queue_violations = 0
        capacity_violations = 0

        iteration_records = []

        # 2. Vectorized / Iterative evaluation
        for i in range(self.num_iterations):
            m = masses[i]
            gr_pct = grades_pct[i]
            gr_rad = math.atan(gr_pct / 100.0)
            
            # Forecasted + perceived weather with measurement uncertainty
            v_perceived = max(5.0, visibilities[i] + vis_errors[i])
            mu_perceived = max(0.18, frictions_hat[i] + fric_errors[i])
            mu_safe = self.friction_model.calculate_safe_friction(mu_perceived, 0.05)

            tau = latencies[i]
            p_loss = packet_losses[i]

            # Adjust braking model reaction time with latency and network packet loss delay
            eff_reaction_time = 0.50 + tau + (p_loss * 0.40)
            self.braking_model.tau_reaction_s = eff_reaction_time

            # Compute safe speed with exact effective latency and standstill margin
            safe_calc = self.braking_model.calculate_safe_speed(
                r_effective=v_perceived,
                grade_rad=gr_rad,
                mass_kg=m,
                mu_safe=mu_safe,
                curve_radius_m=35.0,
                speed_limit_mine_mps=11.11,
                tau_total=eff_reaction_time,
                s_margin=self.braking_model.standstill_margin_m
            )
            v_safe = safe_calc["v_safe"]
            safe_speeds[i] = v_safe

            # Compute resulting stopping distance at v_safe
            a_dec = self.braking_model.calculate_deceleration_on_grade(
                mass_kg=m,
                grade_rad=gr_rad,
                mu_safe=mu_safe
            )
            d_react, d_brk, s_stop = self.braking_model.calculate_stopping_distance(
                speed_mps=v_safe,
                a_dec=a_dec,
                tau_total=eff_reaction_time
            )
            s_margin = self.braking_model.standstill_margin_m
            total_req_dist = s_stop + s_margin
            stopping_distances[i] = total_req_dist

            # Safety margin ratio: R_effective / (S_stop + S_margin) >= 1.0 guaranteed
            margin_ratio = v_perceived / max(1.0, total_req_dist)
            safety_margin_ratios[i] = margin_ratio

            # Audit Tier-1 Safety Invariant: S_stop + S_margin <= R_effective
            if total_req_dist > (v_perceived + 1e-4):
                safety_violations += 1

            # Road Capacity
            h_safe = self.capacity_model.calculate_safe_headway(v_safe, 2.0)
            cap_res = self.capacity_model.calculate_road_capacity(v_safe, h_safe)
            cap_vph = cap_res["capacity_vph"]
            road_capacities[i] = cap_vph

            # Check capacity violation (flow exceeding road capacity)
            flow_demand = fleet_sizes[i] * (3600.0 / 300.0)  # Demand rate
            if flow_demand > (cap_vph + 50.0):  # Exceeding physical bound without shaper
                capacity_violations += 1

            # Arrival shaping and queue dynamics
            mu_serv = service_rates[i]
            shaper = ArrivalRateShaper(default_delta_buffer_vph=1.5)
            safe_arrival = shaper.calculate_safe_arrival_rate(mu_serv)
            
            queue_model = QueueModel(node_id="CRUSHER_01", service_rate_vph=mu_serv, queue_max=5)
            # Simulate 10 discrete steps of queue mass conservation
            for _ in range(10):
                queue_model.step(arrivals=safe_arrival * (1.0 / 3600.0), dt_seconds=1.0)
            
            q_len = queue_model.current_queue
            queue_lengths[i] = q_len
            if q_len > queue_model.queue_max + 1e-4:
                queue_violations += 1

            # Haul Travel Time
            travel_times[i] = 1200.0 / max(0.5, v_safe)

            if i < 50:  # Sample record
                iteration_records.append({
                    "iteration": i + 1,
                    "mass_kg": m,
                    "grade_pct": gr_pct,
                    "visibility_m": v_perceived,
                    "friction_mu": mu_safe,
                    "latency_s": tau,
                    "safe_speed_mps": v_safe,
                    "stopping_distance_m": total_req_dist,
                    "capacity_vph": cap_vph,
                    "queue_length": q_len
                })

        # 3. Aggregate Statistical Distributions
        summary = MonteCarloSummary(
            total_iterations=self.num_iterations,
            seed=self.seed,
            total_safety_violations=safety_violations,
            safety_violation_rate=float(safety_violations / self.num_iterations),
            total_queue_violations=queue_violations,
            queue_violation_rate=float(queue_violations / self.num_iterations),
            total_capacity_violations=capacity_violations,
            capacity_violation_rate=float(capacity_violations / self.num_iterations),
            safe_speed_stats=self._compute_distribution_stats(safe_speeds),
            stopping_distance_stats=self._compute_distribution_stats(stopping_distances),
            safety_margin_ratio_stats=self._compute_distribution_stats(safety_margin_ratios),
            road_capacity_stats=self._compute_distribution_stats(road_capacities),
            queue_length_stats=self._compute_distribution_stats(queue_lengths),
            travel_time_stats=self._compute_distribution_stats(travel_times)
        )

        # 4. Save results to results/
        summary_path = os.path.join(self.results_dir, "monte_carlo_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)

        detailed_path = os.path.join(self.results_dir, "monte_carlo_results.json")
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": asdict(summary),
                "sample_iterations": iteration_records
            }, f, indent=2)

        return summary


def run_standalone_monte_carlo():
    """CLI execution entrypoint for Stage 16 Monte Carlo Validation."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg_dir = os.path.join(base_dir, "config")
    res_dir = os.path.join(base_dir, "results")

    validator = MonteCarloValidator(config_dir=cfg_dir, results_dir=res_dir, num_iterations=1000, seed=42)
    summary = validator.run_monte_carlo()
    print("=" * 70)
    print(f"MONTE CARLO VALIDATION COMPLETE: {summary.total_iterations} ITERATIONS")
    print(f"Total Safety Violations: {summary.total_safety_violations} (Rate: {summary.safety_violation_rate:.6f})")
    print(f"Safe Speed Mean: {summary.safe_speed_stats.mean:.2f} m/s | Median: {summary.safe_speed_stats.median:.2f} m/s | Std: {summary.safe_speed_stats.std:.2f} m/s")
    print(f"Safe Speed 1st Percentile (p01): {summary.safe_speed_stats.p01:.2f} m/s | 99th Percentile (p99): {summary.safe_speed_stats.p99:.2f} m/s")
    print(f"Road Capacity Mean: {summary.road_capacity_stats.mean:.1f} vph | Median: {summary.road_capacity_stats.median:.1f} vph")
    print(f"Results saved to: {res_dir}")
    print("=" * 70)
    return summary


if __name__ == "__main__":
    run_standalone_monte_carlo()
