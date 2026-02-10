"""
事实提取器 - Fact Extractor

从Task中自动提取可复用的原子知识。
基于优化分析文档的改进5。
"""

from typing import TYPE_CHECKING

from .types import Fact, FactType

if TYPE_CHECKING:
    from loom.runtime import Task


class FactExtractor:
    """
    从Task中提取事实

    根据Task的action和status自动识别并提取关键知识点。
    """

    async def extract_facts(self, task: "Task") -> list[Fact]:
        """
        提取事实

        Args:
            task: Task对象

        Returns:
            提取的Fact列表
        """
        facts: list[Fact] = []

        # 根据action类型分发
        action_lower = task.action.lower()

        if "api" in action_lower or "call" in action_lower:
            facts.extend(self._extract_api_facts(task))

        if "user" in action_lower or "interaction" in action_lower:
            facts.extend(self._extract_preference_facts(task))

        if "tool" in action_lower:
            facts.extend(self._extract_tool_facts(task))

        # 根据status提取
        if task.status.value == "failed":
            facts.extend(self._extract_error_facts(task))

        return facts

    def _extract_api_facts(self, task: "Task") -> list[Fact]:
        """提取API相关事实"""
        facts = []

        endpoint = task.parameters.get("endpoint")
        method = task.parameters.get("method")

        if endpoint and method:
            fact = Fact(
                fact_id=f"api_{endpoint.replace('/', '_')}_{method}",
                content=f"API {endpoint} 支持 {method} 方法",
                fact_type=FactType.API_SCHEMA,
                source_task_ids=[task.task_id],
                confidence=0.9,
                tags=["api", endpoint, method],
                created_at=task.created_at,
                session_id=task.session_id,
            )
            facts.append(fact)

        return facts

    def _extract_preference_facts(self, task: "Task") -> list[Fact]:
        """提取用户偏好事实"""
        facts = []

        choice = task.parameters.get("user_choice")
        if choice:
            fact = Fact(
                fact_id=f"pref_{task.task_id}",
                content=f"用户偏好: {choice}",
                fact_type=FactType.USER_PREFERENCE,
                source_task_ids=[task.task_id],
                confidence=0.8,
                tags=["preference", str(choice)],
                created_at=task.created_at,
                session_id=task.session_id,
            )
            facts.append(fact)

        return facts

    def _extract_tool_facts(self, task: "Task") -> list[Fact]:
        """提取工具使用事实"""
        facts = []

        tool_name = task.parameters.get("tool")
        if tool_name and task.result:
            fact = Fact(
                fact_id=f"tool_{tool_name}_{task.task_id}",
                content=f"工具 {tool_name} 的使用方法和结果",
                fact_type=FactType.TOOL_USAGE,
                source_task_ids=[task.task_id],
                confidence=0.7,
                tags=["tool", tool_name],
                created_at=task.created_at,
                session_id=task.session_id,
            )
            facts.append(fact)

        return facts

    def _extract_error_facts(self, task: "Task") -> list[Fact]:
        """提取错误模式事实"""
        facts = []

        if task.error:
            error_summary = str(task.error)[:100]
            fact = Fact(
                fact_id=f"error_{task.task_id}",
                content=f"错误模式: {task.action} 失败 - {error_summary}",
                fact_type=FactType.ERROR_PATTERN,
                source_task_ids=[task.task_id],
                confidence=0.7,
                tags=["error", task.action],
                created_at=task.created_at,
                session_id=task.session_id,
            )
            facts.append(fact)

        return facts
