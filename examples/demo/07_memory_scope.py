"""
07_memory_scope.py - 分形记忆作用域

演示：
- MemoryScope 四种作用域
- LOCAL/SHARED/INHERITED/GLOBAL
- 父子节点记忆继承
"""

import asyncio
from loom.fractal.memory import MemoryScope
from loom.memory import MemoryManager


async def main():
    # 1. 创建父节点记忆管理器
    parent_memory = MemoryManager(node_id="parent-agent")

    # 2. 创建子节点记忆管理器（关联父节点）
    child_memory = MemoryManager(node_id="child-agent", parent=parent_memory)

    # 3. 在父节点写入不同作用域的记忆
    print("=== 父节点写入记忆 ===")

    # LOCAL - 节点私有（子节点不可见）
    await parent_memory.write(
        "parent-local",
        "父节点本地数据",
        scope=MemoryScope.LOCAL,
    )
    print("父节点写入 LOCAL: parent-local")

    # SHARED - 父子双向共享
    await parent_memory.write(
        "shared-data",
        "共享数据 - 父子节点都可见",
        scope=MemoryScope.SHARED,
    )
    print("父节点写入 SHARED: shared-data")

    # GLOBAL - 全局可见
    await parent_memory.write(
        "global-data",
        "全局数据 - 所有节点可见",
        scope=MemoryScope.GLOBAL,
    )
    print("父节点写入 GLOBAL: global-data")

    # 4. 在子节点写入本地记忆
    print("\n=== 子节点写入记忆 ===")
    await child_memory.write(
        "child-local",
        "子节点本地数据",
        scope=MemoryScope.LOCAL,
    )
    print("子节点写入 LOCAL: child-local")

    # 5. 从子节点读取记忆（演示继承）
    print("\n=== 子节点读取记忆 ===")

    # 子节点读取自己的本地数据
    child_local = await child_memory.read("child-local")
    print(f"子节点读取 child-local: {child_local.content if child_local else 'None'}")

    # 子节点无法读取父节点的 LOCAL 数据
    parent_local = await child_memory.read("parent-local")
    print(f"子节点读取 parent-local: {parent_local.content if parent_local else 'None (父节点私有)'}")

    # 子节点可以读取 SHARED 数据（通过 INHERITED 机制）
    shared = await child_memory.read("shared-data")
    print(f"子节点读取 shared-data: {shared.content if shared else 'None'}")

    # 子节点可以读取 GLOBAL 数据
    global_data = await child_memory.read("global-data")
    print(f"子节点读取 global-data: {global_data.content if global_data else 'None'}")

    # 6. 列出各作用域的记忆条目数
    print("\n=== 父节点记忆统计 ===")
    for scope in MemoryScope:
        entries = await parent_memory.list_by_scope(scope)
        print(f"  {scope.name}: {len(entries)} 条")

    print("\n=== 子节点记忆统计 ===")
    for scope in MemoryScope:
        entries = await child_memory.list_by_scope(scope)
        print(f"  {scope.name}: {len(entries)} 条")


if __name__ == "__main__":
    asyncio.run(main())
