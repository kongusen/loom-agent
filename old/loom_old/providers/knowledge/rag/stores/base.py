"""
存储层基类
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseStore(ABC, Generic[T]):
    """
    存储层抽象基类

    定义所有存储的通用接口
    """

    @abstractmethod
    async def add(self, item: T) -> None:
        """添加单个项目"""
        pass

    @abstractmethod
    async def add_batch(self, items: list[T]) -> None:
        """批量添加"""
        pass

    @abstractmethod
    async def get(self, item_id: str) -> T | None:
        """根据ID获取"""
        pass

    @abstractmethod
    async def get_by_ids(self, item_ids: list[str]) -> list[T]:
        """批量获取"""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """删除"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """清空所有数据"""
        pass
