"""
Loom Patterns Base - 模式基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Pattern(ABC):
    """
    模式基类

    模式定义了解决特定类型问题的配置组合。
    """

    name: str
    """模式名称"""

    description: str
    """模式描述"""

    @abstractmethod
    def get_config(self):
        """
        获取模式配置

        Returns:
            LoomConfig 实例
        """
        pass

    def __str__(self):
        return f"{self.name}: {self.description}"
