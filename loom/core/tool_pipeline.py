from __future__ import annotations

import time
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Iterable, List

from loom.core.errors import PermissionDeniedError, ToolNotFoundError, ToolValidationError
from loom.core.types import ToolCall, ToolResult
from loom.interfaces.tool import BaseTool
from loom.core.scheduler import Scheduler
from loom.core.permissions import PermissionManager, PermissionAction
from loom.callbacks.metrics import MetricsCollector


class ExecutionStage(str, Enum):
    DISCOVER = "discover"
    VALIDATE = "validate"
    AUTHORIZE = "authorize"
    CHECK_CANCEL = "check_cancel"
    EXECUTE = "execute"
    FORMAT = "format"


class ToolExecutionPipeline:
    """最小可用的六阶段工具执行流水线（Discover→...→Format）。"""

    def __init__(
        self,
        tools: Dict[str, BaseTool],
        scheduler: Scheduler | None = None,
        permission_manager: PermissionManager | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self.tools = tools
        self.scheduler = scheduler or Scheduler()
        self._stage_metrics: Dict[str, float] = {}
        self.permission_manager = permission_manager or PermissionManager(policy={"default": "allow"})
        self.metrics = metrics or MetricsCollector()

    async def execute_calls(self, tool_calls: Iterable[ToolCall]) -> AsyncGenerator[ToolResult, None]:
        for call in tool_calls:
            try:
                tool = await self._stage_discover(call)
                args = await self._stage_validate(tool, call)
                await self._stage_authorize(tool, call, args)
                # check_cancel: 由上层 EventBus 注入，此处留空
                result = await self._stage_execute(tool, args, call)
                tr = await self._stage_format(result, call)
                self.metrics.metrics.tool_calls += 1
                yield tr
            except Exception as e:  # 简化：归一化错误
                self.metrics.metrics.tool_calls += 1
                self.metrics.metrics.total_errors += 1
                yield ToolResult(
                    tool_call_id=call.id,
                    status="error",
                    content=str(e),
                    metadata={"stage_breakdown": self._stage_metrics.copy()},
                )
            finally:
                self._stage_metrics.clear()

    async def _stage_discover(self, tool_call: ToolCall) -> BaseTool:
        start = time.time()
        if tool_call.name not in self.tools:
            raise ToolNotFoundError(f"Tool '{tool_call.name}' not registered")
        tool = self.tools[tool_call.name]
        self._stage_metrics[ExecutionStage.DISCOVER.value] = time.time() - start
        return tool

    async def _stage_validate(self, tool: BaseTool, tool_call: ToolCall) -> Dict[str, Any]:
        start = time.time()
        if not getattr(tool, "args_schema", None):
            args = tool_call.arguments
        else:
            try:
                args_model = tool.args_schema(**tool_call.arguments)
                args = args_model.model_dump()
            except Exception as e:  # pydantic 验证错误
                raise ToolValidationError(str(e))
        self._stage_metrics[ExecutionStage.VALIDATE.value] = time.time() - start
        return args

    async def _stage_authorize(self, tool: BaseTool, tool_call: ToolCall, args: Dict[str, Any]) -> None:
        start = time.time()
        action = self.permission_manager.check(tool.name, tool_call.arguments)
        if action == PermissionAction.DENY:
            raise PermissionDeniedError(f"Permission denied for tool '{tool.name}'")
        if action == PermissionAction.ASK:
            confirmed = self.permission_manager.confirm(tool.name, args)
            if not confirmed:
                raise PermissionDeniedError(f"User denied permission for tool '{tool.name}'")
        self._stage_metrics[ExecutionStage.AUTHORIZE.value] = time.time() - start

    async def _stage_execute(self, tool: BaseTool, args: Dict[str, Any], call: ToolCall) -> Any:
        start = time.time()
        # 使用调度器包装执行
        result = None
        async for r in self.scheduler.schedule_batch([(tool, args)]):
            result = r
        self._stage_metrics[ExecutionStage.EXECUTE.value] = time.time() - start
        return result

    async def _stage_format(self, result: Any, call: ToolCall) -> ToolResult:
        start = time.time()
        tr = ToolResult(
            tool_call_id=call.id,
            status="success",
            content=str(result) if result is not None else "",
            metadata={"stage_breakdown": self._stage_metrics.copy()},
        )
        self._stage_metrics[ExecutionStage.FORMAT.value] = time.time() - start
        return tr
