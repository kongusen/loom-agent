"""Multi-Agent 协作 - fork 机制"""

from dataclasses import dataclass
from typing import Any
from ..types import Dashboard


@dataclass
class SubAgentConfig:
    """子 Agent 配置"""
    goal: str
    depth: int
    parent_id: str
    max_depth: int = 5


class AgentFork:
    """Agent fork 机制"""

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self.active_agents: dict[str, Any] = {}

    def can_fork(self, current_depth: int) -> bool:
        """检查是否可以 fork"""
        return current_depth < self.max_depth

    def spawn(self, config: SubAgentConfig) -> str:
        """Spawn 子 Agent"""
        if not self.can_fork(config.depth):
            raise ValueError(f"Max depth {self.max_depth} reached")

        agent_id = f"agent_{config.parent_id}_{config.depth}"
        self.active_agents[agent_id] = {
            "config": config,
            "status": "running",
        }
        return agent_id

    def get_result(self, agent_id: str) -> dict | None:
        """获取子 Agent 结果"""
        return self.active_agents.get(agent_id)
