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
from typing import Any, Optional


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
    parent_version: Optional[int] = None  # 父版本号（用于追踪）
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据

    def __post_init__(self):
        """初始化后处理：确保metadata不为None"""
        if self.metadata is None:
            self.metadata = {}
