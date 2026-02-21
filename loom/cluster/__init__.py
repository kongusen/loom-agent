"""ClusterManager — auction-based task allocation."""

from __future__ import annotations

import logging

from ..config import ClusterConfig
from ..types import AgentNode, Bid, TaskAd

logger = logging.getLogger(__name__)


class ClusterManager:
    """Maintains agent nodes, runs auctions, selects winners."""

    def __init__(self, config: ClusterConfig | None = None) -> None:
        self.config = config or ClusterConfig()
        self._nodes: dict[str, AgentNode] = {}

    @property
    def nodes(self) -> list[AgentNode]:
        return list(self._nodes.values())

    def add_node(self, node: AgentNode) -> None:
        self._nodes[node.id] = node

    def remove_node(self, node_id: str) -> AgentNode | None:
        return self._nodes.pop(node_id, None)

    def get_node(self, node_id: str) -> AgentNode | None:
        return self._nodes.get(node_id)

    def compute_bid(self, node: AgentNode, task: TaskAd) -> Bid:
        w = self.config.bid_weights
        cap = node.capabilities.scores.get(task.domain, 0.5)
        avail = 1.0 - node.load
        history = node.capabilities.success_rate
        tool_overlap = (
            len(set(task.required_tools) & set(node.capabilities.tools))
            / max(len(task.required_tools), 1)
            if task.required_tools
            else 1.0
        )
        score = (
            w["capability"] * cap
            + w["availability"] * avail
            + w["history"] * history
            + w["tools"] * tool_overlap
        )
        return Bid(
            agent_id=node.id,
            task_id=task.task_id,
            score=score,
            breakdown={
                "capability": cap,
                "availability": avail,
                "history": history,
                "tools": tool_overlap,
            },
        )

    def collect_bids(self, task: TaskAd) -> list[tuple[AgentNode, Bid]]:
        """Collect bids from all available nodes (idle + busy), matching Amoba."""
        available = [n for n in self._nodes.values() if n.status in ("idle", "busy")]
        return [(n, self.compute_bid(n, task)) for n in available]

    def select_winner(self, task: TaskAd) -> AgentNode | None:
        bids = self.collect_bids(task)
        if not bids:
            return None
        min_bids = getattr(self.config, "min_bids", 1)
        if len(bids) < min_bids:
            fallback = getattr(self.config, "fallback_strategy", "best_available")
            if fallback == "none":
                return None
        bids.sort(key=lambda x: x[1].score, reverse=True)
        # Prefer idle nodes over busy ones at similar scores
        for node, _bid in bids:
            if node.status == "idle":
                return node
        return bids[0][0]

    def find_idle(self) -> AgentNode | None:
        for n in self._nodes.values():
            if n.status == "idle":
                return n
        return None

    def update_load(self, node_id: str, load: float) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.load = max(0.0, min(1.0, load))
