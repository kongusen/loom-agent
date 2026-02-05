"""
Tool Policy - 工具权限策略

提供 Protocol 接口，允许应用层控制工具执行权限：
- WhitelistPolicy: 白名单策略（仅允许指定工具）
- BlacklistPolicy: 黑名单策略（禁止指定工具）
- 自定义策略: 应用可实现 ToolPolicy Protocol

符合 Loom 框架原则：提供机制，应用选择策略
"""

from typing import Protocol


class ToolPolicy(Protocol):
    """
    工具权限策略接口（由应用层实现）

    这是一个 Protocol 接口，不提供具体实现。
    应用层可以选择：
    - WhitelistPolicy（白名单）
    - BlacklistPolicy（黑名单）
    - 自定义策略（实现 ToolPolicy Protocol）
    """

    def is_allowed(self, tool_name: str, context: dict) -> bool:
        """
        检查工具是否被允许执行

        Args:
            tool_name: 工具名称
            context: 执行上下文（可包含 task, agent 等信息）

        Returns:
            bool: True 表示允许，False 表示拒绝
        """
        ...

    def get_denial_reason(self, tool_name: str) -> str:
        """
        获取拒绝原因

        Args:
            tool_name: 工具名称

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
        """
        初始化白名单策略

        Args:
            allowed_tools: 允许的工具名称集合
        """
        self.allowed_tools = allowed_tools

    def is_allowed(self, tool_name: str, context: dict) -> bool:
        """检查工具是否在白名单中"""
        return tool_name in self.allowed_tools

    def get_denial_reason(self, tool_name: str) -> str:
        """返回白名单拒绝原因"""
        return f"Tool not in whitelist. Allowed: {sorted(self.allowed_tools)}"


class BlacklistPolicy:
    """
    黑名单策略

    禁止黑名单中的工具执行。
    适用场景：禁用危险工具、限制特定功能
    """

    def __init__(self, forbidden_tools: set[str]):
        """
        初始化黑名单策略

        Args:
            forbidden_tools: 禁止的工具名称集合
        """
        self.forbidden_tools = forbidden_tools

    def is_allowed(self, tool_name: str, context: dict) -> bool:
        """检查工具是否不在黑名单中"""
        return tool_name not in self.forbidden_tools

    def get_denial_reason(self, tool_name: str) -> str:
        """返回黑名单拒绝原因"""
        return f"Tool is forbidden. Blacklist: {sorted(self.forbidden_tools)}"
