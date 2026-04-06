"""Tool schema definitions - fail-closed 原则

fail-closed 设计原则：忘了声明就按最严格处理
- isReadOnly 默认 false → 走更严格的权限检查
- isConcurrencySafe 默认 false → 串行执行，避免竞争
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Tool definition schema"""
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "string"
    is_read_only: bool = False  # 默认 false，假设会写
    is_destructive: bool = False
    is_concurrency_safe: bool = False  # 默认 false，假设不安全


@dataclass
class Tool:
    """Tool implementation with fail-closed principle"""
    definition: ToolDefinition
    handler: Callable

    async def execute(self, **kwargs) -> Any:
        """Execute tool with parameters"""
        return await self.handler(**kwargs)
