"""
Orchestrator Base - 编排器基类

基于公理A5（认知调度公理）：
Cognition = Orchestration(N1, N2, ..., Nk)

定义编排器的统一接口。

设计原则：
1. 编排优先 - 认知通过编排涌现
2. 模式多样 - 支持多种编排模式
3. 可扩展 - 易于添加新的编排策略
"""

from abc import ABC, abstractmethod

from loom.protocol import NodeProtocol, Task


class Orchestrator(ABC):
    """
    编排器抽象基类

    定义所有编排器必须实现的接口。
    """

    def __init__(self, nodes: list[NodeProtocol] | None = None):
        """
        初始化编排器

        Args:
            nodes: 可用的节点列表
        """
        self.nodes: list[NodeProtocol] = nodes or []

    def add_node(self, node: NodeProtocol) -> None:
        """
        添加节点

        Args:
            node: 要添加的节点
        """
        self.nodes.append(node)

    def remove_node(self, node_id: str) -> bool:
        """
        移除节点

        Args:
            node_id: 节点ID

        Returns:
            是否成功移除
        """
        for i, node in enumerate(self.nodes):
            if node.node_id == node_id:
                self.nodes.pop(i)
                return True
        return False

    @abstractmethod
    async def orchestrate(self, task: Task) -> Task:
        """
        编排执行任务

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        pass
