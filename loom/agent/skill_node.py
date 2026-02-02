"""
Skill Agent Node - Form 3 实例化形态

用于需要独立多轮 LLM 交互的 Skill（极少数，约 2%）
使用简化的执行路径，不是完整的四范式循环。

遵循修订后的设计（AGENTNODE_REFACTOR_DESIGN.md 11.5）：
- 继承 BaseNode
- 只重写 _execute_impl(task) -> Task
- 委派走 EventBus（A2 公理）
"""

from typing import Any

from loom.agent.base import BaseNode
from loom.protocol.task import Task, TaskStatus
from loom.providers.llm.interface import LLMProvider
from loom.skills.models import SkillDefinition


class SkillAgentNode(BaseNode):
    """
    Skill Agent Node - 实例化的 Skill 节点

    用于需要独立多轮 LLM 交互的 Skill（极少数场景）。
    使用简化的执行路径，不包含完整的四范式循环。

    特点：
    - 继承 BaseNode，遵循 NodeProtocol
    - 实现 _execute_impl(task) -> Task（A1 公理）
    - 使用 Skill 的 instructions 作为 system prompt
    - 支持多轮 LLM 交互
    - 委派通过 EventBus（A2 公理）
    """

    def __init__(
        self,
        skill_id: str,
        skill_definition: SkillDefinition,
        llm_provider: LLMProvider,
        event_bus: Any | None = None,
        **kwargs,
    ):
        """
        初始化 Skill Agent Node

        Args:
            skill_id: Skill 唯一标识
            skill_definition: Skill 定义
            llm_provider: LLM 提供者
            event_bus: 事件总线（用于委派）
            **kwargs: 传递给 BaseNode 的其他参数
        """
        super().__init__(
            node_id=f"skill_{skill_id}", node_type="skill", event_bus=event_bus, **kwargs
        )
        self.skill_id = skill_id
        self.skill_definition = skill_definition
        self.llm_provider = llm_provider

        # 构建 system prompt（使用 Skill 的完整指令）
        self.system_prompt = skill_definition.get_full_instructions()

    async def _execute_impl(self, task: Task) -> Task:
        """
        简化的执行实现 - 不是完整的四范式循环

        执行流程：
        1. 使用 Skill 的 instructions 作为 system prompt
        2. 执行 LLM 交互（支持多轮）
        3. 返回结果

        Args:
            task: 输入任务

        Returns:
            完成的任务（包含结果）
        """
        try:
            # 1. 提取任务参数
            task_description = task.parameters.get("task", "")
            if not task_description:
                task.status = TaskStatus.FAILED
                task.result = {"error": "No task description provided"}
                return task

            # 2. 构建消息列表
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task_description},
            ]

            # 3. 调用 LLM（简化版本，不包含工具调用循环）
            response = await self.llm_provider.chat(messages)

            # 4. 设置任务结果
            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": response.content,
                "skill_id": self.skill_id,
                "skill_name": self.skill_definition.name,
            }

            return task

        except Exception as e:
            # 错误处理
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e), "skill_id": self.skill_id}
            return task
