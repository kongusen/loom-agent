"""
Loom 错误处理

定义所有 Loom 框架使用的异常类型
"""

from __future__ import annotations
from typing import Optional, Any


class LoomError(Exception):
    """Loom 框架的基础异常类"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class AgentError(LoomError):
    """Agent 相关错误"""

    pass


class ExecutionError(AgentError):
    """Agent 执行错误"""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.agent_name = agent_name


class ToolError(AgentError):
    """工具执行错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


class RecursionError(AgentError):
    """递归深度超限错误"""

    def __init__(self, message: str, current_depth: int, max_depth: int):
        super().__init__(
            message, details={"current_depth": current_depth, "max_depth": max_depth}
        )
        self.current_depth = current_depth
        self.max_depth = max_depth


class ContextError(LoomError):
    """Context 管理错误"""

    pass


class CompressionError(ContextError):
    """Context 压缩错误"""

    pass


class MemoryError(ContextError):
    """Memory 相关错误"""

    pass


class LLMError(LoomError):
    """LLM 相关错误"""

    def __init__(
        self,
        message: str,
        llm_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.llm_name = llm_name
        self.status_code = status_code


class ValidationError(LoomError):
    """参数验证错误"""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message, details={"field": field, "value": value})
        self.field = field
        self.value = value


class ConfigurationError(LoomError):
    """配置错误"""

    pass


# 向后兼容的别名
class ToolExecutionError(ToolError):
    """工具执行错误（向后兼容）"""

    pass


class MaxRecursionDepthExceeded(RecursionError):
    """递归深度超限（向后兼容）"""

    pass
