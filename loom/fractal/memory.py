"""
分形记忆系统 (Fractal Memory System)

基于科赫雪花的分形理念：在有限时间距离下实现无限思考。

核心组件：
- MemoryScope: 记忆作用域枚举
- MemoryAccessPolicy: 记忆访问策略
- MemoryEntry: 记忆条目数据结构
- FractalMemory: 分形记忆管理器

设计原则：
1. 最小必要原则 - 子节点只接收完成任务所需的最小上下文
2. 分层可见性 - 不同层级的记忆有不同的可见范围
3. 按需加载 - 上下文和记忆按需传递，而非全量复制
4. 双向流动 - 信息可以从父到子，也可以从子到父
5. 冲突可解 - 提供多种策略解决记忆冲突
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


class MemoryScope(Enum):
    """
    记忆作用域

    定义记忆在分形节点树中的可见性和访问权限。
    """

    LOCAL = "local"  # 节点私有，不共享
    SHARED = "shared"  # 父子双向共享
    INHERITED = "inherited"  # 从父节点继承（只读）
    GLOBAL = "global"  # 全局共享（所有节点）


@dataclass
class MemoryAccessPolicy:
    """
    记忆访问策略

    定义每种作用域的访问权限和传播规则。
    """

    scope: MemoryScope
    readable: bool  # 是否可读
    writable: bool  # 是否可写
    propagate_up: bool  # 是否向上传播（子→父）
    propagate_down: bool  # 是否向下传播（父→子）


# 预定义的访问策略
ACCESS_POLICIES = {
    MemoryScope.LOCAL: MemoryAccessPolicy(
        scope=MemoryScope.LOCAL,
        readable=True,
        writable=True,
        propagate_up=False,
        propagate_down=False,
    ),
    MemoryScope.SHARED: MemoryAccessPolicy(
        scope=MemoryScope.SHARED,
        readable=True,
        writable=True,
        propagate_up=True,
        propagate_down=True,
    ),
    MemoryScope.INHERITED: MemoryAccessPolicy(
        scope=MemoryScope.INHERITED,
        readable=True,
        writable=False,  # 只读
        propagate_up=False,
        propagate_down=True,
    ),
    MemoryScope.GLOBAL: MemoryAccessPolicy(
        scope=MemoryScope.GLOBAL,
        readable=True,
        writable=True,
        propagate_up=True,
        propagate_down=True,
    ),
}


@dataclass
class MemoryEntry:
    """
    记忆条目

    存储单个记忆项的完整信息，包括内容、作用域、版本控制等元数据。
    """

    id: str  # 唯一标识
    content: Any  # 记忆内容
    scope: MemoryScope  # 作用域
    version: int = 1  # 版本号（用于冲突检测）
    created_by: str = ""  # 创建者节点ID
    updated_by: str = ""  # 最后更新者节点ID
    parent_version: int | None = None  # 父版本号（用于追踪）
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据

    def __post_init__(self):
        """初始化后处理：确保metadata不为None"""
        if self.metadata is None:
            self.metadata = {}


class FractalMemory:
    """
    分形记忆管理器

    职责：
    - 管理不同作用域的记忆
    - 处理父子节点间的记忆共享
    - 提供统一的读写接口
    - 使用LoomMemory作为底层存储
    """

    def __init__(
        self,
        node_id: str,
        parent_memory: Optional["FractalMemory"] = None,
        base_memory: Optional["LoomMemory"] = None,
    ):
        """
        初始化分形记忆管理器

        Args:
            node_id: 节点唯一标识
            parent_memory: 父节点的记忆管理器（用于建立父子关系）
            base_memory: 底层LoomMemory存储（如果为None，将在需要时创建）
        """
        self.node_id = node_id
        self.parent_memory = parent_memory
        self.base_memory = base_memory

        # 按作用域组织的记忆索引（轻量级，只存储元数据）
        self._memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """
        写入记忆

        Args:
            entry_id: 记忆ID
            content: 记忆内容
            scope: 作用域

        Returns:
            创建的记忆条目

        Raises:
            PermissionError: 如果作用域不可写
        """
        # 检查写权限
        policy = ACCESS_POLICIES[scope]
        if not policy.writable:
            raise PermissionError(f"Scope {scope} is read-only")

        # 创建记忆条目
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            scope=scope,
            created_by=self.node_id,
            updated_by=self.node_id,
        )

        # 存储到对应作用域
        self._memory_by_scope[scope][entry_id] = entry

        return entry

    async def read(
        self,
        entry_id: str,
        search_scopes: list[MemoryScope] | None = None,
    ) -> MemoryEntry | None:
        """
        读取记忆

        Args:
            entry_id: 记忆ID
            search_scopes: 搜索的作用域列表（None表示搜索所有）

        Returns:
            记忆条目，如果不存在返回None
        """
        if search_scopes is None:
            search_scopes = list(MemoryScope)

        # 按优先级搜索：LOCAL > SHARED > INHERITED > GLOBAL
        for scope in search_scopes:
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 如果是INHERITED作用域，尝试从父节点读取
        if MemoryScope.INHERITED in search_scopes and self.parent_memory:
            parent_entry = await self.parent_memory.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED],
            )
            if parent_entry:
                # 创建只读副本
                inherited_entry = MemoryEntry(
                    id=parent_entry.id,
                    content=parent_entry.content,
                    scope=MemoryScope.INHERITED,
                    version=parent_entry.version,
                    created_by=parent_entry.created_by,
                    updated_by=parent_entry.updated_by,
                    parent_version=parent_entry.version,
                )
                # 缓存到本地
                self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
                return inherited_entry

        return None

    async def list_by_scope(self, scope: MemoryScope) -> list[MemoryEntry]:
        """
        列出指定作用域的所有记忆

        Args:
            scope: 记忆作用域

        Returns:
            该作用域下的所有记忆条目列表
        """
        return list(self._memory_by_scope[scope].values())
