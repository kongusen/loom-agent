"""
冲突解决器 (Conflict Resolvers)

提供多种策略解决父子节点间的记忆冲突。

策略：
- ParentWinsResolver: 父节点优先
- ChildWinsResolver: 子节点优先
- MergeResolver: 智能合并
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.fractal.memory import MemoryEntry


class ConflictResolver(ABC):
    """冲突解决器抽象接口"""

    @abstractmethod
    async def resolve(
        self, parent_entry: "MemoryEntry", child_entry: "MemoryEntry"
    ) -> "MemoryEntry":
        """
        解决冲突

        Args:
            parent_entry: 父节点的记忆条目
            child_entry: 子节点的记忆条目

        Returns:
            解决后的记忆条目
        """
        pass


class ParentWinsResolver(ConflictResolver):
    """父节点优先策略"""

    async def resolve(
        self, parent_entry: "MemoryEntry", child_entry: "MemoryEntry"
    ) -> "MemoryEntry":
        """父节点的版本覆盖子节点"""
        return parent_entry


class ChildWinsResolver(ConflictResolver):
    """子节点优先策略"""

    async def resolve(
        self, parent_entry: "MemoryEntry", child_entry: "MemoryEntry"
    ) -> "MemoryEntry":
        """子节点的版本覆盖父节点"""
        return child_entry


class MergeResolver(ConflictResolver):
    """智能合并策略"""

    async def resolve(
        self, parent_entry: "MemoryEntry", child_entry: "MemoryEntry"
    ) -> "MemoryEntry":
        """智能合并两个版本"""
        from loom.fractal.memory import MemoryEntry

        # 如果内容是字典，进行深度合并
        if isinstance(parent_entry.content, dict) and isinstance(
            child_entry.content, dict
        ):
            merged_content = self._merge_dicts(parent_entry.content, child_entry.content)
        else:
            # 其他类型，使用子节点版本
            merged_content = child_entry.content

        # 创建新的合并版本
        merged_entry = MemoryEntry(
            id=parent_entry.id,
            content=merged_content,
            scope=parent_entry.scope,
            version=max(parent_entry.version, child_entry.version) + 1,
            created_by=parent_entry.created_by,
            updated_by=f"{parent_entry.updated_by}+{child_entry.updated_by}",
        )

        return merged_entry

    def _merge_dicts(self, parent_dict: dict, child_dict: dict) -> dict:
        """深度合并字典"""
        result = parent_dict.copy()
        for key, value in child_dict.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result

