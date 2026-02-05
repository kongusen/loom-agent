"""
Tool Policy - 工具权限策略

提供 Protocol 接口，允许应用层控制工具执行权限：
- WhitelistPolicy: 白名单策略（仅允许指定工具）
- BlacklistPolicy: 黑名单策略（禁止指定工具）
- SafeBashPolicy: 安全 Bash 策略（限制危险命令）
- 自定义策略: 应用可实现 ToolPolicy Protocol

符合 Loom 框架原则：提供机制，应用选择策略
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolContext:
    """
    工具执行上下文

    提供丰富的上下文信息，支持复杂的权限控制策略。
    """

    # 工具信息
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)

    # Agent 信息
    agent_id: str = ""
    recursive_depth: int = 0

    # 任务信息
    task_id: str = ""
    session_id: str = ""

    # 调用统计
    call_count: int = 0  # 当前工具在本次任务中的调用次数


class ToolPolicy(Protocol):
    """
    工具权限策略接口（由应用层实现）

    这是一个 Protocol 接口，不提供具体实现。
    应用层可以选择：
    - WhitelistPolicy（白名单）
    - BlacklistPolicy（黑名单）
    - SafeBashPolicy（安全Bash）
    - 自定义策略（实现 ToolPolicy Protocol）
    """

    def is_allowed(self, context: ToolContext) -> bool:
        """
        检查工具是否被允许执行

        Args:
            context: 执行上下文（包含工具名称、参数、agent信息、任务信息等）

        Returns:
            bool: True 表示允许，False 表示拒绝
        """
        ...

    def get_denial_reason(self, context: ToolContext) -> str:
        """
        获取拒绝原因

        Args:
            context: 执行上下文

        Returns:
            str: 拒绝原因说明
        """
        ...


class WhitelistPolicy:
    """
    白名单策略

    仅允许白名单中的工具执行。
    适用场景：生产环境、受限环境、安全敏感场景
    """

    def __init__(self, allowed_tools: set[str]):
        self.allowed_tools = allowed_tools

    def is_allowed(self, context: ToolContext) -> bool:
        """检查工具是否在白名单中"""
        return context.tool_name in self.allowed_tools

    def get_denial_reason(self, context: ToolContext) -> str:
        """返回白名单拒绝原因"""
        return f"Tool '{context.tool_name}' not in whitelist. Allowed: {sorted(self.allowed_tools)}"


class BlacklistPolicy:
    """
    黑名单策略

    禁止黑名单中的工具执行。
    适用场景：禁用危险工具、限制特定功能
    """

    def __init__(self, forbidden_tools: set[str]):
        self.forbidden_tools = forbidden_tools

    def is_allowed(self, context: ToolContext) -> bool:
        """检查工具是否不在黑名单中"""
        return context.tool_name not in self.forbidden_tools

    def get_denial_reason(self, context: ToolContext) -> str:
        """返回黑名单拒绝原因"""
        return f"Tool '{context.tool_name}' is forbidden."


class SafeBashPolicy:
    """
    安全 Bash 策略

    检查 bash/shell 工具的命令参数，阻止危险命令。
    适用场景：允许 bash 但限制危险操作

    示例危险命令：
    - rm -rf /
    - sudo rm
    - chmod 777
    - curl | bash
    """

    # 默认危险模式
    DEFAULT_DANGEROUS_PATTERNS: set[str] = {
        "rm -rf /",
        "rm -rf /*",
        "sudo rm",
        "chmod 777",
        "curl | bash",
        "wget | bash",
        "> /dev/sda",
        "mkfs.",
        "dd if=",
        ":(){:|:&};:",  # fork bomb
    }

    def __init__(
        self,
        dangerous_patterns: set[str] | None = None,
        bash_tool_names: set[str] | None = None,
    ):
        """
        初始化安全 Bash 策略

        Args:
            dangerous_patterns: 危险命令模式集合（默认使用内置模式）
            bash_tool_names: bash 工具名称集合（默认 {"bash", "shell", "execute"}）
        """
        self.dangerous_patterns = dangerous_patterns or self.DEFAULT_DANGEROUS_PATTERNS
        self.bash_tool_names = bash_tool_names or {"bash", "shell", "execute"}
        self._last_matched_pattern: str = ""

    def is_allowed(self, context: ToolContext) -> bool:
        """检查 bash 命令是否安全"""
        # 非 bash 工具直接允许
        if context.tool_name not in self.bash_tool_names:
            return True

        # 获取命令参数
        command = context.tool_args.get("command", "")
        if not command:
            return True

        # 检查危险模式
        command_lower = command.lower()
        for pattern in self.dangerous_patterns:
            if pattern.lower() in command_lower:
                self._last_matched_pattern = pattern
                return False

        return True

    def get_denial_reason(self, context: ToolContext) -> str:
        """返回安全拒绝原因"""
        command = context.tool_args.get("command", "")
        return (
            f"Dangerous bash command detected in '{command[:50]}...'. "
            f"Pattern matched: '{self._last_matched_pattern}'"
        )
