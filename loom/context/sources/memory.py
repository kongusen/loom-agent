"""
Memory Context Sources - 从 LoomMemory 获取上下文

L1RecentSource: 最近任务
L2ImportantSource: 重要任务
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory
    from loom.memory.tokenizer import TokenCounter
    from loom.runtime import Task


class L1RecentSource(ContextSource):
    """
    L1 最近任务源

    从 LoomMemory 的 L1 层获取最近的任务。
    优先级按时间衰减：越近的任务优先级越高。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L1_recent"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集最近任务"""
        # 获取 L1 任务（按时间倒序）
        tasks = self.memory.get_l1_tasks(limit=50, session_id=self.session_id)

        if not tasks:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0
        total_tasks = len(tasks)

        # 从最近的开始处理
        for idx, task in enumerate(reversed(tasks)):
            content = self._task_to_content(task)
            if not content:
                continue

            # 计算 token
            tokens = self._count_tokens(content, "assistant", token_counter)

            # 检查预算
            if current_tokens + tokens > token_budget:
                break

            # 计算优先级：最近的 = 1.0，最旧的 = 0.5
            priority = 1.0 - (idx / total_tasks) * 0.5

            block = ContextBlock(
                content=content,
                role="assistant",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={"task_id": task.task_id, "action": task.action},
            )

            blocks.append(block)
            current_tokens += tokens

        return blocks

    def _task_to_content(self, task: "Task") -> str:
        """将 Task 转换为内容字符串"""
        action = task.action
        params = task.parameters

        if action == "node.thinking":
            return str(params.get("content", ""))
        elif action == "node.tool_call":
            tool_name = params.get("tool_name", "")
            tool_args = params.get("tool_args", {})
            return f"[Tool: {tool_name}] {tool_args}"
        elif action == "node.message":
            return str(params.get("content") or params.get("message", ""))
        elif action == "execute":
            return str(params.get("content", ""))

        return ""


class L2ImportantSource(ContextSource):
    """
    L2 重要任务源

    从 LoomMemory 的 L2 层获取重要任务。
    优先级基于任务的 importance 元数据。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L2_important"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集重要任务"""
        # 获取 L2 任务（按重要性排序）
        tasks = self.memory.get_l2_tasks(limit=50, session_id=self.session_id)

        if not tasks:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for task in tasks:
            content = self._task_to_content(task)
            if not content:
                continue

            # 计算 token
            tokens = self._count_tokens(content, "assistant", token_counter)

            # 检查预算
            if current_tokens + tokens > token_budget:
                break

            # 优先级基于 importance
            importance = task.metadata.get("importance", 0.5)
            priority = min(1.0, max(0.0, importance))

            block = ContextBlock(
                content=content,
                role="assistant",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={"task_id": task.task_id, "action": task.action},
            )

            blocks.append(block)
            current_tokens += tokens

        return blocks

    def _task_to_content(self, task: "Task") -> str:
        """将 Task 转换为内容字符串"""
        action = task.action
        params = task.parameters

        if action == "node.thinking":
            return str(params.get("content", ""))
        elif action == "node.tool_call":
            tool_name = params.get("tool_name", "")
            tool_args = params.get("tool_args", {})
            return f"[Tool: {tool_name}] {tool_args}"
        elif action == "node.message":
            return str(params.get("content") or params.get("message", ""))
        elif action == "execute":
            return str(params.get("content", ""))

        return ""
