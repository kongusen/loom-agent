"""
ExecutorMixin - 执行循环

处理任务执行、LLM交互、消息过滤等功能。

从 core.py 拆分，遵循单一职责原则。
"""

import json
from typing import TYPE_CHECKING, Any

from loom.exceptions import TaskComplete
from loom.protocol import Task, TaskStatus

if TYPE_CHECKING:
    pass


class ExecutorMixin:
    """
    执行处理混入类

    提供执行相关的所有功能：
    - 任务执行循环
    - LLM 交互
    - 消息过滤
    - 自我评估
    """

    # 类型提示（由 Agent 类提供）
    node_id: str
    llm_provider: Any
    memory: Any
    event_bus: Any
    all_tools: list[dict[str, Any]]
    max_iterations: int
    require_done_tool: bool
    _ephemeral_tool_config: dict[str, int]

    def _get_tool_ephemeral_count(self, tool_name: str) -> int:
        """获取工具的 ephemeral 消息保留数量"""
        return self._ephemeral_tool_config.get(tool_name, 0)

    def _filter_ephemeral_messages(
        self,
        messages: list[dict[str, Any]],
        tool_call_counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        """
        过滤 ephemeral 工具消息

        对于配置了 ephemeral 的工具，只保留最近 N 次调用的消息。
        """
        if not self._ephemeral_tool_config:
            return messages

        # 收集需要过滤的工具调用
        tool_messages: dict[str, list[int]] = {}
        for idx, msg in enumerate(messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_name = tc.get("function", {}).get("name", "")
                    if tool_name in self._ephemeral_tool_config:
                        if tool_name not in tool_messages:
                            tool_messages[tool_name] = []
                        tool_messages[tool_name].append(idx)

        # 确定要移除的消息索引
        indices_to_remove: set[int] = set()
        for tool_name, indices in tool_messages.items():
            keep_count = self._ephemeral_tool_config[tool_name]
            if len(indices) > keep_count:
                for idx in indices[:-keep_count]:
                    indices_to_remove.add(idx)
                    # 同时移除对应的 tool 响应
                    if idx + 1 < len(messages) and messages[idx + 1].get("role") == "tool":
                        indices_to_remove.add(idx + 1)

        return [msg for idx, msg in enumerate(messages) if idx not in indices_to_remove]

    async def _self_evaluate(self, task: Task) -> None:
        """
        自我评估 - 检查任务是否真正完成

        在 require_done_tool=False 时，LLM 可能过早结束。
        此方法让 LLM 自我检查是否真正完成了任务。
        """
        evaluation_prompt = f"""Review your response to the user's request.

Original request: {task.parameters.get('content', '')}

Did you fully address the request? If not, what's missing?
If complete, respond with "TASK_COMPLETE".
If incomplete, explain what still needs to be done."""

        try:
            response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": evaluation_prompt}],
                max_tokens=500,
            )

            if "TASK_COMPLETE" not in response.content:
                # 任务未完成，继续执行
                pass
        except Exception:
            pass
