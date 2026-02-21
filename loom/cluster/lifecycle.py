"""Lifecycle — mitosis (agent splitting) and apoptosis (agent death)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Literal

from ..config import ClusterConfig
from ..errors import ApoptosisRejectedError
from ..types import AgentNode, CapabilityProfile, TaskAd

logger = logging.getLogger(__name__)

HealthStatus = Literal["healthy", "warning", "dying"]


@dataclass
class HealthReport:
    node_id: str
    status: HealthStatus
    recent_avg_reward: float
    idle_ms: float
    recommendation: Literal["keep", "merge", "recycle"]


class LifecycleManager:
    """Manages agent birth (mitosis) and death (apoptosis)."""

    def __init__(self, config: ClusterConfig | None = None) -> None:
        self.config = config or ClusterConfig()

    def should_split(self, task: TaskAd, node: AgentNode) -> bool:
        return (
            task.estimated_complexity > self.config.mitosis_threshold
            and node.depth < self.config.max_depth
        )

    def check_health(self, node: AgentNode) -> HealthReport:
        recent = node.reward_history[-10:]
        avg = sum(r.reward for r in recent) / len(recent) if recent else 0.0
        idle_ms = (time.time() - node.last_active_at) * 1000

        if (
            node.consecutive_losses >= self.config.consecutive_loss_limit
            or avg < self.config.apoptosis_threshold
            or idle_ms / 1000 > self.config.idle_timeout
        ):
            status: HealthStatus = "dying"
            rec = "recycle" if not recent else "merge"
        elif node.consecutive_losses >= self.config.consecutive_loss_limit // 2:
            status, rec = "warning", "merge"
        else:
            status, rec = "healthy", "keep"  # type: ignore[assignment]

        return HealthReport(
            node_id=node.id,
            status=status,
            recent_avg_reward=avg,
            idle_ms=idle_ms,
            recommendation=rec,  # type: ignore[arg-type]
        )

    def find_merge_target(self, dying: AgentNode, candidates: list[AgentNode]) -> AgentNode | None:
        """Find most complementary agent, weighted by load (matches Amoba)."""
        best, best_score = None, -1.0
        for c in candidates:
            if c.id == dying.id:
                continue
            complementarity = sum(
                abs(dying.capabilities.scores.get(d, 0) - c.capabilities.scores.get(d, 0))
                for d in set(dying.capabilities.scores) | set(c.capabilities.scores)
            )
            score = complementarity * (1 - c.load * 0.5)
            if score > best_score:
                best, best_score = c, score
        return best

    def apoptosis(self, node: AgentNode, cluster) -> None:
        """Remove a dying node with Amoba-style guards."""
        if len(cluster.nodes) <= getattr(cluster.config, "min_nodes", 1):
            raise ApoptosisRejectedError(node.id, "at minimum node count")
        if node.status == "busy":
            raise ApoptosisRejectedError(node.id, "node is busy")
        candidates = [n for n in cluster.nodes if n.id != node.id and n.status == "idle"]
        target = self.find_merge_target(node, candidates)
        if target:
            self.merge_capabilities(node, target)
        cluster.remove_node(node.id)

    def merge_capabilities(self, source: AgentNode, target: AgentNode) -> None:
        """Merge source capabilities into target, weighted by task count. Also merges tools."""
        sw = source.capabilities.total_tasks
        tw = target.capabilities.total_tasks
        total = max(sw + tw, 1)
        for domain, score in source.capabilities.scores.items():
            existing = target.capabilities.scores.get(domain, 0.5)
            target.capabilities.scores[domain] = existing * tw / total + score * sw / total
        # Merge tools list (Amoba merges tools on capability merge)
        existing_tools = set(target.capabilities.tools)
        for tool in source.capabilities.tools:
            if tool not in existing_tools:
                target.capabilities.tools.append(tool)

    def mitosis(self, parent: AgentNode, task: TaskAd, agent_factory) -> AgentNode:
        """Split a parent node into a child specialized for the task (matches Amoba)."""
        from ..errors import MitosisError

        if parent.depth >= self.config.max_depth:
            raise MitosisError(parent.id, f"max depth {self.config.max_depth} reached")
        child_agent = agent_factory(depth=parent.depth + 1)
        child = AgentNode(
            id=child_agent.id,
            depth=parent.depth + 1,
            capabilities=CapabilityProfile(
                scores={task.domain: 0.5},
                tools=list(parent.capabilities.tools),
            ),
            agent=child_agent,
        )
        return child
