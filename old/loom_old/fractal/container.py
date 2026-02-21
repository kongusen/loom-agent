"""
Node Container - 节点容器

基于公理A3（分形自相似公理）：
∀node ∈ System: structure(node) ≅ structure(System)

实现节点的递归组合能力。

设计原则：
1. 组合模式 - 节点可以包含其他节点
2. 递归结构 - 容器本身也是节点
3. 透明性 - 容器和叶子节点实现相同接口
"""

from loom.agent.card import AgentCard, NodeProtocol
from loom.runtime import Task


class NodeContainer:
    """
    节点容器 - 实现分形组合

    基于递归状态机设计：容器本身是节点，可包含一个子节点。
    遵循最简原则：只提供核心的包装能力，不实现复杂的编排逻辑。

    注意：容器只支持单个子节点。多节点编排请使用 Orchestrator。

    属性：
        node_id: 容器唯一标识
        source_uri: 容器URI
        agent_card: 容器能力声明
        child: 子节点（单个）
    """

    def __init__(
        self,
        node_id: str,
        agent_card: AgentCard,
        child: NodeProtocol | None = None,
        max_depth: int = 100,
    ):
        """
        初始化节点容器

        Args:
            node_id: 容器ID
            agent_card: 能力声明
            child: 子节点（可选）
            max_depth: 最大递归深度限制（默认100）
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.agent_card = agent_card
        self.child: NodeProtocol | None = child
        self.max_depth = max_depth

    def set_child(self, child: NodeProtocol) -> None:
        """
        设置子节点

        Args:
            child: 子节点
        """
        self.child = child

    async def execute_task(self, task: Task) -> Task:
        """
        执行任务（委托给子节点）

        Args:
            task: 任务对象

        Returns:
            更新后的任务
        """
        # 检查递归深度（防止栈溢出）
        current_depth = task.metadata.get("_container_depth", 0)

        if current_depth >= self.max_depth:
            from loom.runtime import TaskStatus

            task.status = TaskStatus.FAILED
            task.error = f"Container recursion depth exceeded: {current_depth} >= {self.max_depth}"
            return task

        # 委托给子节点
        if self.child:
            # 增加深度计数
            task.metadata["_container_depth"] = current_depth + 1
            result = await self.child.execute_task(task)
            # 恢复深度计数
            task.metadata["_container_depth"] = current_depth
            return result

        # 无子节点时设置失败状态
        from loom.runtime import TaskStatus

        task.status = TaskStatus.FAILED
        task.error = "No child to execute task"
        return task

    def get_capabilities(self) -> AgentCard:
        """
        获取能力声明

        Returns:
            AgentCard对象
        """
        return self.agent_card
