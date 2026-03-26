"""Scene Package types for Axiom 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class ScenePackage:
    """场景包 σ = ⟨id, tools, constraints, memory_scope, verify_hook⟩"""

    id: str
    tools: list[str]  # 工具名称列表
    constraints: dict[str, bool] = field(default_factory=dict)
    memory_scope: list[str] = field(default_factory=list)
    verify_hook: Callable[[dict], Awaitable[bool]] | None = None

    def __add__(self, other: ScenePackage) -> ScenePackage:
        """场景组合 σ_a ⊕ σ_b - 约束收窄"""
        return ScenePackage(
            id=f"{self.id}+{other.id}",
            tools=list(set(self.tools + other.tools)),
            constraints=self._merge_constraints(self.constraints, other.constraints),
            memory_scope=list(set(self.memory_scope + other.memory_scope)),
            verify_hook=self._chain_verify(other.verify_hook),
        )

    def _chain_verify(self, other_hook: Callable | None) -> Callable | None:
        """串联验证钩子"""
        current_hook = self.verify_hook
        if current_hook is None:
            return other_hook
        if not other_hook:
            return current_hook

        async def chained(state: dict) -> bool:
            return await current_hook(state) and await other_hook(state)

        return chained

    def _merge_constraints(self, c1: dict, c2: dict) -> dict:
        """合并约束 - 取更严格的值"""
        merged = {}
        all_keys = set(c1.keys()) | set(c2.keys())

        for key in all_keys:
            v1 = c1.get(key)
            v2 = c2.get(key)

            if v1 is None:
                merged[key] = v2
            elif v2 is None:
                merged[key] = v1
            else:
                # 布尔约束：两者都允许才允许
                if isinstance(v1, bool) and isinstance(v2, bool):
                    merged[key] = v1 and v2
                # 数值约束：取更小的限制
                elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    merged[key] = min(v1, v2)
                # 列表约束：取交集
                elif isinstance(v1, list) and isinstance(v2, list):
                    merged[key] = list(set(v1) & set(v2))
                else:
                    # 默认：保留第一个
                    merged[key] = v1

        return merged
