"""L* main execution loop - (Reason → Act → Observe → Δ)*"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..context import ContextPartitions
from ..types import LoopState


@dataclass
class LoopConfig:
    """L* loop configuration"""
    max_iterations: int = 100
    d_max: int = 5  # 最大递归深度
    rho_threshold: float = 1.0  # 强制 renew 阈值


class AgentLoop:
    """L* main execution loop"""

    def __init__(self, config: LoopConfig):
        self.config = config
        self.state = LoopState.REASON
        self.iteration = 0

    def run(
        self,
        goal: str,
        context: ContextPartitions,
        reason_fn: Callable,
        act_fn: Callable,
        observe_fn: Callable,
        delta_fn: Callable,
    ) -> dict[str, Any]:
        """Run L* loop until goal reached or max iterations"""

        while self.iteration < self.config.max_iterations:
            self.iteration += 1

            # Reason: 读取 C，制定/更新计划
            if self.state == LoopState.REASON:
                context = reason_fn(goal, context)
                self.state = LoopState.ACT

            # Act: 调用工具，执行操作
            elif self.state == LoopState.ACT:
                effect = act_fn(context)
                self.state = LoopState.OBSERVE

            # Observe: 读取 Effect，更新 dashboard
            elif self.state == LoopState.OBSERVE:
                context = observe_fn(effect, context)

                # 物理硬约束：ρ = 1.0 强制 renew
                if context.working.rho >= self.config.rho_threshold:
                    self.state = LoopState.RENEW
                else:
                    self.state = LoopState.DELTA

            # Δ: LLM 自主决策下一步
            elif self.state == LoopState.DELTA:
                decision = delta_fn(context)

                if decision == "goal_reached":
                    return {"status": "success", "context": context}
                elif decision == "renew":
                    self.state = LoopState.RENEW
                elif decision == "continue":
                    self.state = LoopState.REASON
                elif decision == "decompose":
                    return {"status": "decompose", "context": context}
                elif decision == "harness":
                    return {"status": "harness", "context": context}

            # Renew: 压缩重建 C
            elif self.state == LoopState.RENEW:
                from ..context import ContextRenewer
                renewer = ContextRenewer()
                context = renewer.renew(context, goal)
                self.state = LoopState.REASON

        return {"status": "max_iterations", "context": context}
