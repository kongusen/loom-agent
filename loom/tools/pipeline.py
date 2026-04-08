"""14 步工具治理 Pipeline"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .base import Tool


@dataclass
class ToolExecutionContext:
    """工具执行上下文"""
    tool: Tool
    input_data: dict
    user_context: dict
    hooks: dict[str, list[Callable]] | None = None


class ToolPipeline:
    """14 步治理 Pipeline"""

    def __init__(self):
        self.pre_hooks: list[Callable] = []
        self.post_hooks: list[Callable] = []
        self.post_failure_hooks: list[Callable] = []

    def execute(self, ctx: ToolExecutionContext) -> dict[str, Any]:
        """执行完整 Pipeline"""

        # ① 查找工具（已在 ctx 中）
        tool = ctx.tool

        # ② 解析 MCP 元数据（如果是 MCP 工具）
        # 跳过，非 MCP 工具

        # ③ Schema 校验
        schema = tool.input_schema()
        if not self._validate_schema(ctx.input_data, schema):
            return {"error": "Schema validation failed"}

        # ④ validateInput() 细粒度校验
        valid, msg = tool.validate_input(ctx.input_data)
        if not valid:
            return {"error": f"Input validation failed: {msg}"}

        # ⑤ Speculative Classifier（预判风险）
        self._classify_risk(tool, ctx.input_data)

        # ⑥ PreToolUse hooks
        for hook in self.pre_hooks:
            result = hook(ctx)
            if result.get("block"):
                return {"error": "Blocked by pre-hook"}

        # ⑦ resolveHookPermissionDecision
        # hook allow ≠ 绕过 settings deny

        # ⑧ 权限最终决策
        allowed, reason = tool.check_permissions(ctx.user_context)
        if not allowed:
            return {"error": f"Permission denied: {reason}"}

        # ⑨ 修正输入（若被 hook 修改）
        final_input = ctx.input_data

        try:
            # ⑩ tool.call() 执行
            result = tool.call(**final_input)

            # ⑪ analytics / tracing
            self._log_execution(tool, final_input, result)

            # ⑫ PostToolUse hooks
            for hook in self.post_hooks:
                hook(ctx, result)

            # ⑬ 结构化输出
            return {"success": True, "result": result}

        except Exception as e:
            # ⑭ PostToolUseFailure hooks
            for hook in self.post_failure_hooks:
                hook(ctx, e)
            return {"error": str(e)}

    def _validate_schema(self, data: dict, schema: dict) -> bool:
        """Schema 校验

        Args:
            data: 数据（预留参数）
            schema: Schema 定义（预留参数）
        """
        _ = data  # 预留参数，未来用于数据校验
        _ = schema  # 预留参数，未来用于 schema 校验
        return True  # 简化实现

    def _classify_risk(self, tool: Tool, input_data: dict) -> str:
        """风险分类

        Args:
            tool: 工具实例
            input_data: 输入数据（预留参数）
        """
        _ = input_data  # 预留参数，未来用于基于输入的风险评估
        if tool.metadata.is_destructive:
            return "high"
        return "low"

    def _log_execution(self, tool: Tool, input_data: dict, result: Any):
        """记录执行日志"""
        pass
