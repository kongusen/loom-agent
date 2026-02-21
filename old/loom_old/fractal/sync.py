"""
分形记忆同步管理器 (Fractal Memory Sync Manager)

实现父子节点间的记忆同步，使用乐观锁检测冲突，提供多种冲突解决策略。

核心组件：
- MemorySyncManager: 记忆同步管理器
- ConflictResolver: 冲突解决器抽象接口
- ParentWinsResolver: 父节点优先策略
- ChildWinsResolver: 子节点优先策略
- MergeResolver: 智能合并策略
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loom.fractal.memory import FractalMemory, MemoryEntry, MemoryScope

from loom.fractal.memory import MemoryScope


class MemorySyncManager:
    """
    记忆同步管理器

    职责：
    - 实现乐观锁版本控制
    - 处理父子节点间的记忆同步
    - 检测和解决冲突
    """

    def __init__(self, memory: "FractalMemory"):
        """
        初始化同步管理器

        Args:
            memory: 要管理的FractalMemory实例
        """
        self.memory = memory

    async def write_with_version_check(
        self, entry: "MemoryEntry", expected_version: int
    ) -> tuple[bool, str | None]:
        """
        带版本检查的写入（乐观锁）

        Args:
            entry: 要写入的记忆条目
            expected_version: 期望的当前版本号

        Returns:
            (成功标志, 错误信息)
        """
        # 读取当前版本
        current = await self.memory.read(entry.id)

        # 版本冲突检测
        if current and current.version != expected_version:
            return (
                False,
                f"Version conflict: expected {expected_version}, got {current.version}",
            )

        # 更新版本号
        entry.version = expected_version + 1
        entry.updated_by = self.memory.node_id

        # 写入（保留版本信息）
        await self.memory.write_entry(entry)

        return True, None

    async def sync_from_parent(self) -> int:
        """
        从父节点同步SHARED记忆

        Returns:
            同步的记忆条目数量
        """
        if not self.memory.parent_memory:
            return 0

        synced_count = 0

        # 获取父节点的SHARED记忆
        parent_shared = await self.memory.parent_memory.list_by_scope(MemoryScope.SHARED)

        for parent_entry in parent_shared:
            # 检查本地是否已有
            local_entry = await self.memory.read(
                parent_entry.id, search_scopes=[MemoryScope.SHARED]
            )

            if not local_entry:
                # 本地没有，直接复制（保留版本信息）
                await self.memory.write_entry(parent_entry)
                synced_count += 1
            elif local_entry.version < parent_entry.version:
                # 本地版本较旧，暂时以父节点为准（后续接入冲突解决器）
                await self.memory.write_entry(parent_entry)
                synced_count += 1

        return synced_count
