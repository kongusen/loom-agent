"""Cluster configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClusterConfig:
    min_nodes: int = 1
    max_nodes: int = 10
    max_depth: int = 2
    mitosis_threshold: float = 0.6
    apoptosis_threshold: float = 0.3
    idle_timeout: float = 300.0
    consecutive_loss_limit: int = 20
    bid_weights: dict[str, float] = field(
        default_factory=lambda: {
            "capability": 0.4,
            "availability": 0.25,
            "history": 0.2,
            "tools": 0.15,
        }
    )
    # Blueprint Forge
    blueprint_forge_enabled: bool = True
    blueprint_evolve_threshold: float = 0.35
    blueprint_evolve_window: int = 5
    blueprint_prune_min_reward: float = 0.2
    blueprint_prune_min_tasks: int = 3
    blueprint_max_count: int = 50
