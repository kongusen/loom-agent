"""StepExecutor - 统一的工具调用执行入口"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .constraint_validator import ConstraintValidator
    from .core import Agent
    from .resource_guard import ResourceGuard
    from ..tools import ToolRegistry
    from ..types import ToolCall, ToolContext

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """步骤执行结果"""

    output: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None


class StepExecutor:
    """统一的步骤执行器 - 所有工具调用的唯一入口"""

    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
        constraint_validator: ConstraintValidator,
        resource_guard: ResourceGuard,
    ):
        self.agent = agent
        self.tools = tool_registry
        self.validator = constraint_validator
        self.guard = resource_guard

    async def execute_step(self, tool_call: ToolCall, ctx: ToolContext) -> StepResult:
        """执行单步 - 集成所有检查和更新"""

        # 1. 资源配额检查
        within_quota, msg = self.guard.check_quota()
        if not within_quota:
            logger.error(f"Resource quota exceeded: {msg}")
            return StepResult(error=f"Resource quota exceeded: {msg}")

        # 2. 约束验证（L2）
        is_valid, error_msg = self.validator.validate_before_call(tool_call)
        if not is_valid:
            logger.warning(f"Constraint violation: {error_msg}")
            return StepResult(error=error_msg)

        # 3. 执行工具
        try:
            result = await self.tools.execute(tool_call, ctx)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return StepResult(error=f"Tool execution error: {str(e)}")

        # 4. 记录轨迹
        self.agent._execution_trace.append(
            f"{tool_call.name}({tool_call.arguments[:50]}) → {result[:100]}"
        )

        # 5. 更新 working 分区
        working_content = self.agent._build_working_state()
        self.agent.partition_mgr.update_partition("working", working_content)

        # 6. 过滤输出（信息增益）
        filtered_result = await self._filter_output(tool_call.name, result)

        return StepResult(output=filtered_result)

    async def _filter_output(self, tool_name: str, raw_output: str) -> str:
        """过滤工具输出的冗余信息"""
        context = self.agent.partition_mgr.get_context()
        delta_h = self.agent.event_bus.info_calc.calculate_delta_h(raw_output, context)

        # 低增益：截断
        if delta_h < 0.1:
            return f"[Tool {tool_name} executed, output redundant]"

        # 中等增益：总结
        if delta_h < 0.3:
            return self._summarize_output(raw_output, max_tokens=200)

        # 高增益：完整保留
        return raw_output

    def _summarize_output(self, text: str, max_tokens: int) -> str:
        """总结输出（简单截断）"""
        truncated = self.agent.tokenizer.truncate(text, max_tokens)
        if len(truncated) < len(text):
            return truncated + "\n[... output truncated for brevity]"
        return text
