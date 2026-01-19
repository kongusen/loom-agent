"""
State Store - 状态存储抽象

定义状态存储的统一接口和实现。

设计原则：
1. 抽象统一 - 统一的存储接口
2. 可插拔 - 支持多种存储实现
3. 异步优先 - 所有操作都是async
"""

from abc import ABC, abstractmethod
from typing import Any


class StateStore(ABC):
    """
    状态存储抽象接口

    所有状态存储实现必须继承此接口。
    """

    @abstractmethod
    async def save(self, key: str, value: Any) -> None:
        """
        保存状态

        Args:
            key: 状态键
            value: 状态值
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        获取状态

        Args:
            key: 状态键

        Returns:
            状态值，如果不存在返回None
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        删除状态

        Args:
            key: 状态键
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        列出所有键

        Args:
            prefix: 键前缀（可选）

        Returns:
            键列表
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """清空所有状态"""
        pass


class MemoryStateStore(StateStore):
    """
    内存状态存储

    使用dict在内存中存储状态。
    适用于单机部署和测试环境。
    """

    def __init__(self):
        """初始化内存存储"""
        self._store: dict[str, Any] = {}

    async def save(self, key: str, value: Any) -> None:
        """保存状态到内存"""
        self._store[key] = value

    async def get(self, key: str) -> Any | None:
        """从内存获取状态"""
        return self._store.get(key)

    async def delete(self, key: str) -> None:
        """从内存删除状态"""
        if key in self._store:
            del self._store[key]

    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出所有键"""
        if not prefix:
            return list(self._store.keys())
        return [k for k in self._store if k.startswith(prefix)]

    async def clear(self) -> None:
        """清空所有状态"""
        self._store.clear()
