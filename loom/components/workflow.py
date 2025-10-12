from __future__ import annotations

from typing import Any, Dict, List


class Workflow:
    """工作流编排（DAG）- 骨架实现。"""

    def __init__(self) -> None:
        self.graph: Dict[str, Dict[str, Any]] = {}

    def add_node(self, name: str, component: Any) -> None:
        self.graph[name] = {"component": component, "deps": []}

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.graph[to_node]["deps"].append(from_node)

    async def run(self, input: Any) -> Any:
        # 最小骨架：按插入顺序运行所有无依赖节点（占位）
        result = input
        for name, node in self.graph.items():
            comp = node["component"]
            if hasattr(comp, "run"):
                result = await comp.run(result)
        return result

