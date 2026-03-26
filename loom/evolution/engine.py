"""Evolution Engine for Axiom 4."""

from __future__ import annotations

import math

from ..types.evolution import FailureRecord, Pattern, TaskResult
from ..types.skill import Skill


class EvolutionEngine:
    """进化引擎 - 实现 E1-E4"""

    def __init__(self, theta_crystal: int = 3, tau_skill: float = 0.8) -> None:
        self.theta_crystal = theta_crystal  # 结晶频率阈值
        self.tau_skill = tau_skill  # 成功率阈值
        self.patterns: dict[str, Pattern] = {}
        self.failures: list[FailureRecord] = []

    async def e1_retrospect(self, result: TaskResult) -> None:
        """E1: 回顾蒸馏"""
        if result.success:
            await self._extract_pattern(result)
        else:
            await self._extract_failure(result)

    async def _extract_pattern(self, result: TaskResult) -> None:
        """提取成功模式"""
        pattern_key = result.task[:50]
        if pattern_key in self.patterns:
            p = self.patterns[pattern_key]
            p.frequency += 1
        else:
            self.patterns[pattern_key] = Pattern(
                name=pattern_key, frequency=1, success_rate=1.0, steps=result.trace
            )

    async def _extract_failure(self, result: TaskResult) -> None:
        """提取失败记录"""
        failure = FailureRecord(
            task=result.task, reason=result.metadata.get("error", "Unknown"), trace=result.trace
        )
        self.failures.append(failure)

    async def e2_crystallize(self) -> list[Skill]:
        """E2: 模式结晶 - 高频模式转化为 Skill（SKILL.md 格式）"""
        new_skills = []
        for pattern in self.patterns.values():
            if pattern.frequency >= self.theta_crystal and pattern.success_rate >= self.tau_skill:
                # 生成 SKILL.md 格式的 instructions
                instructions = f"""# {pattern.name}

## Pattern Description
This skill captures a frequently successful pattern observed in task execution.

## Steps
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(pattern.steps))}

## Metrics
- Frequency: {pattern.frequency}
- Success Rate: {pattern.success_rate:.1%}
"""
                skill = Skill(
                    name=f"pattern_{pattern.name[:20].replace(' ', '_').lower()}",
                    description=f"Apply the {pattern.name} pattern. Use when encountering similar tasks.",
                    instructions=instructions,
                )
                new_skills.append(skill)
        return new_skills

    async def e2_crystallize_adaptive(self) -> list[Skill]:
        """P1: 预测性技能结晶 - 动态阈值."""
        new_skills = []
        for pattern in self.patterns.values():
            # 计算置信度
            confidence = pattern.success_rate * math.log(pattern.frequency + 1)

            # 动态阈值：高置信度可以更早结晶
            threshold = self.theta_crystal / (1 + confidence)

            if pattern.frequency >= threshold and pattern.success_rate >= self.tau_skill:
                instructions = f"""# {pattern.name}

## Pattern Description
High-confidence pattern (confidence={confidence:.2f}).

## Steps
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(pattern.steps))}

## Metrics
- Frequency: {pattern.frequency}
- Success Rate: {pattern.success_rate:.1%}
- Confidence: {confidence:.2f}
"""
                skill = Skill(
                    name=f"pattern_{pattern.name[:20].replace(' ', '_').lower()}",
                    description=f"Apply {pattern.name} pattern (adaptive threshold).",
                    instructions=instructions,
                )
                new_skills.append(skill)
        return new_skills

    async def e3_solidify_constraints(self) -> list[str]:
        """E3: 约束固化 - 从失败中提取约束"""
        constraints = []
        for failure in self.failures:
            if "permission" in failure.reason.lower():
                constraints.append(f"禁止: {failure.task}")
        return constraints
