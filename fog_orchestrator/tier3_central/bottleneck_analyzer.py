"""
Tier 3: Bottleneck Analyzer & Migration Detector for FOG-ORCHESTRATOR 2.0
Computes dynamic bottleneck scores and tracks bottleneck migration timelines.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from fog_orchestrator.core.graph_network import MineNetwork, MineNode

@dataclass
class BottleneckScore:
    node_id: str
    score: float
    utilization_rho: float
    queue_length: float
    criticality: float
    is_primary_bottleneck: bool


class BottleneckAnalyzer:
    """Bottleneck scoring engine evaluating equal, domain, and data-driven weight models."""

    def __init__(self, scoring_version: str = "VERSION_B_DOMAIN"):
        self.scoring_version = scoring_version  # 'VERSION_A_EQUAL', 'VERSION_B_DOMAIN', 'VERSION_C_DATA_DRIVEN'
        self.history: List[Dict[str, float]] = []

    def compute_node_bottleneck_score(
        self,
        node: MineNode,
        arrival_rate_vph: float
    ) -> BottleneckScore:
        """
        Computes Bottleneck Score: B_j = (w1 * rho_j) * (w2 * Q_j) * (w3 * Criticality_j)
        where utilization rho_j = lambda_j / mu_j.
        """
        mu_j = max(0.1, node.service_rate_vph)
        rho_j = arrival_rate_vph / mu_j
        q_j = node.current_queue
        crit_j = node.criticality

        if self.scoring_version == "VERSION_A_EQUAL":
            w1, w2, w3 = 1.0, 1.0, 1.0
        elif self.scoring_version == "VERSION_B_DOMAIN":
            w1, w2, w3 = 2.0, 1.5, 1.0
        else: # VERSION_C_DATA_DRIVEN
            w1, w2, w3 = 2.5, 1.8, 1.2

        score = (w1 * rho_j) * (1.0 + w2 * q_j) * (w3 * crit_j)

        return BottleneckScore(
            node_id=node.node_id,
            score=score,
            utilization_rho=rho_j,
            queue_length=q_j,
            criticality=crit_j,
            is_primary_bottleneck=False
        )

    def evaluate_network_bottlenecks(
        self,
        network: MineNetwork,
        arrival_rates_vph: Dict[str, float]
    ) -> Tuple[List[BottleneckScore], str]:
        """
        Evaluates bottleneck scores across all network nodes.
        Returns sorted scores list and primary bottleneck node_id.
        """
        scores: List[BottleneckScore] = []
        for node_id, node in network.nodes.items():
            arr_rate = arrival_rates_vph.get(node_id, 10.0)
            bs = self.compute_node_bottleneck_score(node, arr_rate)
            scores.append(bs)

        scores.sort(key=lambda s: s.score, reverse=True)
        primary_node_id = ""
        if scores:
            scores[0].is_primary_bottleneck = True
            primary_node_id = scores[0].node_id

        # Track history for bottleneck migration timeline
        history_entry = {s.node_id: s.score for s in scores}
        self.history.append(history_entry)

        return scores, primary_node_id
