"""RewardBus — EMA-based capability tracking with reward signals."""

from __future__ import annotations

import time
from typing import Any, Callable, Awaitable
from ..types import AgentNode, TaskAd, RewardSignal, RewardRecord


class RewardBus:
    """Evaluate task results, update agent capabilities via exponential moving average."""

    def __init__(self, alpha: float = 0.3, decay_rate: float = 0.01) -> None:
        self._alpha = alpha
        self._decay_rate = decay_rate
        self._llm_judge: Callable[..., Awaitable[float]] | None = None
        self._judge_interval: int = 5
        self._judge_counter: int = 0

    def set_llm_judge(self, judge_fn: Callable[..., Awaitable[float]], interval: int = 5) -> None:
        self._llm_judge = judge_fn
        self._judge_interval = interval

    def compute_signal(self, task: TaskAd, success: bool, token_cost: int, error_count: int) -> RewardSignal:
        return RewardSignal(
            quality=0.7 if success else 0.0,
            efficiency=max(0.0, 1.0 - token_cost / max(task.token_budget, 1)),
            reliability=1.0 if error_count == 0 else 0.0,
        )

    def compute_reward(self, signal: RewardSignal) -> float:
        return 0.5 * signal.quality + 0.3 * signal.efficiency + 0.2 * signal.reliability

    def evaluate(self, node: AgentNode, task: TaskAd, success: bool, token_cost: int = 0, error_count: int = 0) -> float:
        signal = self.compute_signal(task, success, token_cost, error_count)
        reward = self.compute_reward(signal)
        self._update_capability(node, task.domain, reward)
        node.reward_history.append(RewardRecord(
            task_id=task.task_id, reward=reward, domain=task.domain, token_cost=token_cost,
        ))
        node.capabilities.total_tasks += 1
        # EMA success rate (matches Amoba)
        hit = 1.0 if reward > 0.5 else 0.0
        node.capabilities.success_rate = (
            self._alpha * hit + (1 - self._alpha) * node.capabilities.success_rate
        )
        if success:
            node.consecutive_losses = 0
        else:
            node.consecutive_losses += 1
        return reward

    async def evaluate_hybrid(self, node: AgentNode, task: TaskAd, success: bool, token_cost: int = 0, error_count: int = 0) -> float:
        """Hybrid evaluation: rule-based + periodic LLM judge with bias correction."""
        rule_reward = self.evaluate(node, task, success, token_cost, error_count)
        if not self._llm_judge:
            return rule_reward
        self._judge_counter += 1
        if self._judge_counter % self._judge_interval != 0:
            return rule_reward
        try:
            llm_reward = await self._llm_judge(node, task, success)
            bias = llm_reward - rule_reward
            corrected = rule_reward + bias * 0.5
            self._update_capability(node, task.domain, corrected)
            return corrected
        except Exception:
            return rule_reward

    def decay_inactive(self, node: AgentNode) -> None:
        now = time.time()
        for domain, score in list(node.capabilities.scores.items()):
            last = next((r for r in reversed(node.reward_history) if r.domain == domain), None)
            days = (now - (last.timestamp if last and hasattr(last, 'timestamp') else 0)) / 86400
            if days > 1:
                node.capabilities.scores[domain] = score * (self._decay_rate ** days)

    def _update_capability(self, node: AgentNode, domain: str, reward: float) -> None:
        current = node.capabilities.scores.get(domain, 0.5)
        node.capabilities.scores[domain] = self._alpha * reward + (1 - self._alpha) * current
