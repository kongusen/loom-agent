"""
Provider Base - 提供者基类

定义外部服务提供者的统一接口。

设计原则：
1. 抽象优先 - 定义清晰的接口
2. 可插拔 - 易于切换不同的提供者
3. 异步支持 - 所有操作都是async
"""

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """
    提供者抽象基类

    所有外部服务提供者的基类。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化提供者

        Args:
            config: 配置字典
        """
        self.config = config or {}

    @abstractmethod
    async def initialize(self) -> None:
        """初始化提供者（连接、认证等）"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭提供者（清理资源）"""
        pass
