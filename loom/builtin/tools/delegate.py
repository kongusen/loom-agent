"""Delegate 工具 - 委托任务给团队其他成员

这个工具专为 Manager 角色设计，允许 Manager 将任务委托给
Crew 中具有特定能力的其他 Agent。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from loom.crew.crew import Crew
    from loom.crew.orchestration import Task


class DelegateInput(BaseModel):
    """Delegate 工具输入参数"""

    task_description: str = Field(
        description="Short description of the subtask to delegate (3-5 words)"
    )
    prompt: str = Field(
        description="Detailed instructions for the team member to execute"
    )
    target_role: str = Field(
        description="Target role name to delegate to (e.g., 'researcher', 'developer', 'qa_engineer')"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional context information to pass to the delegated task"
    )


class DelegateTool(BaseTool):
    """
    Delegate 工具 - 委托任务给团队成员

    这个工具允许 Manager 角色将任务委托给 Crew 中的其他专业角色。
    委托的任务会由目标角色的 Agent 执行，结果会返回给 Manager。

    使用场景：
    - Manager 需要专业能力（如代码分析、安全审计）
    - 任务需要特定工具访问权限
    - 需要并行执行多个专业子任务

    Example:
        ```python
        # 委托研究任务给 researcher
        result = await delegate(
            task_description="Research codebase",
            prompt="Analyze the authentication module and identify security issues",
            target_role="researcher"
        )
        ```
    """

    name = "delegate"
    description = (
        "Delegate a subtask to another team member with specific expertise. "
        "Use this to leverage specialized roles (researcher, developer, qa_engineer, etc.) "
        "for tasks requiring their unique capabilities or tools."
    )
    args_schema = DelegateInput
    is_concurrency_safe = True

    # Orchestration attributes
    is_read_only = False  # Delegated task may use write tools
    category = "coordination"
    requires_confirmation = False

    def __init__(self, crew: "Crew") -> None:
        """
        初始化 DelegateTool

        Args:
            crew: Crew 实例，包含所有可用的团队成员
        """
        self.crew = crew

        # Delegation statistics
        self._delegation_stats = {
            "total_delegations": 0,
            "successful_delegations": 0,
            "failed_delegations": 0,
            "delegations_by_role": {},
        }

    async def run(
        self,
        task_description: str,
        prompt: str,
        target_role: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        执行任务委托

        Args:
            task_description: 任务简短描述
            prompt: 详细的任务指令
            target_role: 目标角色名称
            context: 可选的上下文信息

        Returns:
            str: 委托任务的执行结果
        """
        try:
            # 更新统计信息（在任何检查之前）
            self._delegation_stats["total_delegations"] += 1
            role_count = self._delegation_stats["delegations_by_role"].get(target_role, 0)
            self._delegation_stats["delegations_by_role"][target_role] = role_count + 1

            # 检查目标角色是否存在
            if target_role not in self.crew.members:
                # 更新失败统计
                self._delegation_stats["failed_delegations"] += 1

                available_roles = ", ".join(self.crew.list_roles())
                return (
                    f"**Delegation Error**: Role '{target_role}' not found in crew.\n\n"
                    f"Available roles: {available_roles}"
                )

            # 创建任务对象
            from loom.crew.orchestration import Task

            task = Task(
                id=f"delegated_{uuid4().hex[:8]}",
                description=task_description,
                prompt=prompt,
                assigned_role=target_role,
                context=context or {},
            )

            # 执行委托任务
            result = await self.crew.execute_task(task, context=context)

            # 更新成功统计
            self._delegation_stats["successful_delegations"] += 1

            # 格式化返回结果
            return self._format_delegation_result(
                task_description=task_description,
                target_role=target_role,
                result=result
            )

        except Exception as e:
            # 更新失败统计
            self._delegation_stats["failed_delegations"] += 1

            return (
                f"**Delegation Error**\n\n"
                f"Task: {task_description}\n"
                f"Target Role: {target_role}\n"
                f"Error: {type(e).__name__}: {str(e)}"
            )

    def _format_delegation_result(
        self,
        task_description: str,
        target_role: str,
        result: str
    ) -> str:
        """
        格式化委托结果

        Args:
            task_description: 任务描述
            target_role: 目标角色
            result: 执行结果

        Returns:
            str: 格式化后的结果
        """
        return f"""**Delegated Task: {task_description}**
**Assigned to**: {target_role}

**Result**:
{result}
"""

    def get_delegation_stats(self) -> Dict[str, Any]:
        """
        获取委托统计信息

        Returns:
            Dict: 包含委托统计的字典
        """
        total = self._delegation_stats["total_delegations"]
        success_rate = (
            self._delegation_stats["successful_delegations"] / total
            if total > 0 else 0
        )

        return {
            **self._delegation_stats,
            "success_rate": success_rate,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._delegation_stats = {
            "total_delegations": 0,
            "successful_delegations": 0,
            "failed_delegations": 0,
            "delegations_by_role": {},
        }

    def list_available_roles(self) -> list[str]:
        """
        列出所有可用的角色

        Returns:
            list[str]: 角色名称列表
        """
        return self.crew.list_roles()
