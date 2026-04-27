"""Tool 接口标准化 - fail-closed 原则"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolMetadata:
    """工具元数据"""

    name: str
    description: str
    is_read_only: bool = False  # 默认 false，假设会写
    is_destructive: bool = False
    is_concurrency_safe: bool = False  # 默认 false，假设不安全
    requires_permission: bool = True


class Tool(ABC):
    """Tool 基类 - fail-closed 设计"""

    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata

    @abstractmethod
    def call(self, **kwargs) -> dict[str, Any]:
        """执行工具，返回 Effect"""
        pass

    @abstractmethod
    def input_schema(self) -> dict:
        """返回输入 schema"""
        pass

    def validate_input(self, input_data: dict) -> tuple[bool, str]:
        """细粒度输入校验

        Args:
            input_data: 输入数据（预留参数，子类可重写进行校验）
        """
        _ = input_data  # 预留参数，子类可重写
        return True, ""

    def check_permissions(self, context: dict) -> tuple[bool, str]:
        """权限检查

        Args:
            context: 上下文信息（预留参数，子类可重写进行权限检查）
        """
        _ = context  # 预留参数，子类可重写
        if not self.metadata.requires_permission:
            return True, ""
        return True, ""  # 默认允许，交给通用权限系统

    def prompt(self) -> str:
        """动态生成工具描述"""
        return self.metadata.description
