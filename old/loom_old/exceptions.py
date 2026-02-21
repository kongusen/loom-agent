"""
Loom Agent Exceptions

增强版异常体系：
- 每个异常携带结构化上下文（agent_id, iteration, tool_name 等）
- 提供 suggested_fix 字段引导开发者快速定位
- 支持 to_dict() 序列化，便于日志和可观测性集成
"""

from __future__ import annotations

from typing import Any


class LoomError(Exception):
    """
    Base exception for all Loom errors.

    所有 Loom 异常的基类，携带结构化上下文信息。
    """

    def __init__(
        self,
        message: str,
        *,
        agent_id: str = "",
        iteration: int = -1,
        context: dict[str, Any] | None = None,
        suggested_fix: str = "",
    ):
        self.agent_id = agent_id
        self.iteration = iteration
        self.context = context or {}
        self.suggested_fix = suggested_fix
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error_type": type(self).__name__,
            "message": str(self),
        }
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.iteration >= 0:
            result["iteration"] = self.iteration
        if self.context:
            result["context"] = self.context
        if self.suggested_fix:
            result["suggested_fix"] = self.suggested_fix
        return result


class TaskComplete(LoomError):
    """
    Raised when a task is completed by the agent using the 'done' tool.

    Attributes:
        message: The completion message summarizing what was accomplished.
        output: Optional structured data to pass to downstream nodes.
    """

    def __init__(self, message: str, output: Any = None, **kwargs: Any):
        self.message = message
        self.output = output
        super().__init__(f"Task completed: {message}", **kwargs)


class PermissionDenied(LoomError):
    """
    Raised when a tool execution is denied by the ToolPolicy.

    Attributes:
        tool_name: The name of the tool that was denied.
        reason: The reason for denial.
    """

    def __init__(self, tool_name: str, reason: str = "", **kwargs: Any):
        self.tool_name = tool_name
        self.reason = reason
        msg = f"PERMISSION_MISSING: Tool '{tool_name}' is not allowed"
        if reason:
            msg += f" - {reason}"
        kwargs.setdefault(
            "suggested_fix",
            f"Add '{tool_name}' to the tool policy whitelist, "
            "or use Agent.create(..., tool_policy=ToolPolicy(mode='allow_all'))",
        )
        super().__init__(msg, **kwargs)


# ============ 工具相关异常 ============


class ToolExecutionError(LoomError):
    """工具执行失败"""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        **kwargs: Any,
    ):
        self.tool_name = tool_name
        self.reason = reason
        kwargs.setdefault("context", {})["tool_name"] = tool_name
        kwargs.setdefault(
            "suggested_fix",
            f"Check the implementation of tool '{tool_name}'. "
            "Ensure the tool function handles edge cases and returns a string result. "
            "Use Agent.create(..., tool_policy=ToolPolicy(mode='log')) to debug tool calls.",
        )
        super().__init__(
            f"Tool '{tool_name}' execution failed: {reason}",
            **kwargs,
        )


class ToolNotFoundError(LoomError):
    """工具未注册"""

    def __init__(self, tool_name: str, available: list[str] | None = None, **kwargs: Any):
        self.tool_name = tool_name
        self.available = available or []
        hint = ""
        if self.available:
            hint = f" Available tools: {', '.join(self.available[:5])}"
        kwargs.setdefault(
            "suggested_fix",
            f"Register '{tool_name}' via Agent.create(tools=[...]) or AgentBuilder().with_tools([...])",
        )
        super().__init__(
            f"Tool '{tool_name}' not found.{hint}",
            **kwargs,
        )


# ============ 记忆相关异常 ============


class MemoryError(LoomError):
    """记忆系统错误基类"""

    pass


class MemoryBudgetExceeded(MemoryError):
    """记忆预算超限"""

    def __init__(
        self,
        tier: str,
        used: int,
        limit: int,
        **kwargs: Any,
    ):
        self.tier = tier
        self.used = used
        self.limit = limit
        kwargs.setdefault(
            "suggested_fix",
            f"Increase {tier} budget via memory_config, "
            "or enable compaction to auto-compress older entries.",
        )
        super().__init__(
            f"Memory budget exceeded for {tier}: {used} tokens used / {limit} limit",
            **kwargs,
        )


# ============ 上下文相关异常 ============


class ContextBuildError(LoomError):
    """上下文构建失败"""

    def __init__(self, source: str, reason: str, **kwargs: Any):
        self.source = source
        self.reason = reason
        kwargs.setdefault("context", {})["source"] = source
        kwargs.setdefault(
            "suggested_fix",
            f"Context source '{source}' failed during collection. "
            "Check that memory and knowledge base providers are properly initialized. "
            "Try reducing max_context_tokens or disabling the failing source.",
        )
        super().__init__(
            f"Context build failed for source '{source}': {reason}",
            **kwargs,
        )


# ============ Agent 运行时异常 ============


class MaxIterationsExceeded(LoomError):
    """Agent 达到最大迭代次数"""

    def __init__(self, max_iterations: int, **kwargs: Any):
        self.max_iterations = max_iterations
        kwargs.setdefault(
            "suggested_fix",
            "Increase max_iterations in Agent.create(), "
            "or break the task into smaller sub-tasks via delegation.",
        )
        super().__init__(
            f"Agent reached max iterations ({max_iterations})",
            **kwargs,
        )


class DelegationError(LoomError):
    """子 Agent 委派失败"""

    def __init__(
        self,
        target_agent: str,
        reason: str,
        **kwargs: Any,
    ):
        self.target_agent = target_agent
        self.reason = reason
        kwargs.setdefault("context", {})["target_agent"] = target_agent
        kwargs.setdefault(
            "suggested_fix",
            f"Delegation to '{target_agent}' failed. "
            "Ensure the target agent is registered in available_agents, "
            "shares the same EventBus, and has not exceeded its recursion depth limit.",
        )
        super().__init__(
            f"Delegation to '{target_agent}' failed: {reason}",
            **kwargs,
        )


class LLMProviderError(LoomError):
    """LLM 提供者调用失败"""

    def __init__(
        self,
        provider: str,
        reason: str,
        **kwargs: Any,
    ):
        self.provider = provider
        self.reason = reason
        kwargs.setdefault(
            "suggested_fix",
            "Check API key, network connectivity, and rate limits. "
            "Consider adding retry logic via interceptors.",
        )
        super().__init__(
            f"LLM provider '{provider}' error: {reason}",
            **kwargs,
        )


class ConfigurationError(LoomError):
    """配置错误"""

    def __init__(self, param: str, reason: str, **kwargs: Any):
        self.param = param
        self.reason = reason
        kwargs.setdefault(
            "suggested_fix",
            f"Check the value of '{param}'. "
            "Refer to ToolConfig, ContextConfig, or MemoryConfig documentation for valid options. "
            "Use Agent.create() with keyword arguments for the simplest configuration.",
        )
        super().__init__(
            f"Invalid configuration for '{param}': {reason}",
            **kwargs,
        )
