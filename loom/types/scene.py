"""Scene Package types for Axiom 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Awaitable


@dataclass
class ScenePackage:
    """场景包 σ = ⟨id, tools, constraints, memory_scope, verify_hook⟩"""

    id: str
    tools: list[str]  # 工具名称列表
    constraints: dict[str, bool] = field(default_factory=dict)
    memory_scope: list[str] = field(default_factory=list)
    verify_hook: Callable[[dict], Awaitable[bool]] | None = None

    def __add__(self, other: ScenePackage) -> ScenePackage:
        """场景组合 σ_a ⊕ σ_b"""
        return ScenePackage(
            id=f"{self.id}+{other.id}",
            tools=list(set(self.tools + other.tools)),
            constraints={**self.constraints, **other.constraints},
            memory_scope=list(set(self.memory_scope + other.memory_scope)),
            verify_hook=self._chain_verify(other.verify_hook),
        )

    def _chain_verify(self, other_hook: Callable | None) -> Callable | None:
        """串联验证钩子"""
        if not self.verify_hook:
            return other_hook
        if not other_hook:
            return self.verify_hook

        async def chained(state: dict) -> bool:
            return await self.verify_hook(state) and await other_hook(state)

        return chained
