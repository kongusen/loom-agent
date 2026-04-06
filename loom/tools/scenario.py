"""场景库 Σ - 工具分类管理"""

from dataclasses import dataclass, field
from typing import Callable
from .base import Tool


@dataclass
class Scenario:
    """场景定义"""
    name: str
    tools: list[Tool] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    verify_hooks: list[Callable] = field(default_factory=list)

    def __add__(self, other: "Scenario") -> "Scenario":
        """场景组合：σ_a ⊕ σ_b"""
        return Scenario(
            name=f"{self.name}+{other.name}",
            tools=self.tools + other.tools,
            constraints=self._merge_constraints(self.constraints, other.constraints),
            verify_hooks=self.verify_hooks + other.verify_hooks,
        )

    def _merge_constraints(self, c1: dict, c2: dict) -> dict:
        """约束取交集（更严格）"""
        merged = {}
        for key in set(c1.keys()) | set(c2.keys()):
            if key in c1 and key in c2:
                merged[key] = min(c1[key], c2[key])
            else:
                merged[key] = c1.get(key, c2.get(key))
        return merged


class ScenarioLibrary:
    """场景库管理"""

    def __init__(self):
        self.scenarios: dict[str, Scenario] = {}

    def register(self, scenario: Scenario):
        """注册场景"""
        self.scenarios[scenario.name] = scenario

    def get(self, name: str) -> Scenario | None:
        """获取场景"""
        return self.scenarios.get(name)

    def compose(self, *names: str) -> Scenario:
        """组合多个场景"""
        result = self.scenarios[names[0]]
        for name in names[1:]:
            result = result + self.scenarios[name]
        return result
