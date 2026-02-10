"""
07_memory_scope.py - 记忆作用域与隔离

演示：
- Session 级别的记忆隔离
- L1-L2 层级记忆作用域
- 跨 Session 记忆共享
- ContextController 统一管理
"""

import asyncio
from loom.api import (
    ContextController,
    Session,
    Task,
)


async def main():
    print("=" * 60)
    print("记忆作用域与隔离 Demo")
    print("=" * 60)

    # 1. 创建 ContextController（统一管理多个 Session）
    controller = ContextController()
    print("\n[1] 创建 ContextController")

    # 2. 创建两个独立的 Session（各自有独立的记忆空间）
    session_parent = Session(session_id="parent-session")
    session_child = Session(session_id="child-session")

    controller.register_session(session_parent)
    controller.register_session(session_child)
    print(f"[2] 注册 {len(controller.session_ids)} 个 Session: {controller.session_ids}")

    # 3. 向 parent-session 写入记忆（Session 私有）
    await demo_session_private_scope(session_parent)

    # 4. 向 child-session 写入记忆（Session 私有）
    await demo_session_private_scope_child(session_child)

    # 5. 演示记忆隔离
    await demo_memory_isolation(session_parent, session_child)

    # 6. 演示跨 Session 共享
    await demo_cross_session_sharing(controller)

    # 7. 统计信息
    demo_memory_stats(controller)

    print("\n" + "=" * 60)
    print("Demo 完成!")
    print("=" * 60)


async def demo_session_private_scope(session: Session):
    """演示 Session 私有作用域"""
    print("\n" + "-" * 40)
    print("[3] Parent Session 写入记忆（私有作用域）")
    print("-" * 40)

    # 添加多个任务到 parent-session
    tasks_data = [
        ("node.message", "父节点本地数据 - 仅本 Session 可见"),
        ("node.message", "共享数据 - 可通过 Controller 共享"),
        ("node.message", "全局数据 - 可提升到 L3/L4"),
    ]

    for action, content in tasks_data:
        task = Task(action=action, parameters={"content": content})
        session.add_task(task)
        print(f"    写入: {content[:30]}...")

    print(f"    Parent Session L1 任务数: {len(session.get_l1_tasks(limit=10))}")


async def demo_session_private_scope_child(session: Session):
    """演示子 Session 私有作用域"""
    print("\n" + "-" * 40)
    print("[4] Child Session 写入记忆（私有作用域）")
    print("-" * 40)

    task = Task(
        action="node.message",
        parameters={"content": "子节点本地数据 - 仅本 Session 可见"},
    )
    session.add_task(task)
    print(f"    写入: 子节点本地数据")
    print(f"    Child Session L1 任务数: {len(session.get_l1_tasks(limit=10))}")


async def demo_memory_isolation(parent: Session, child: Session):
    """演示记忆隔离 - 各 Session 记忆互不可见"""
    print("\n" + "-" * 40)
    print("[5] 记忆隔离演示")
    print("-" * 40)

    parent_tasks = parent.get_l1_tasks(limit=10)
    child_tasks = child.get_l1_tasks(limit=10)

    print(f"    Parent Session 可见任务: {len(parent_tasks)} 个")
    for t in parent_tasks:
        content = t.parameters.get("content", "")[:35]
        print(f"      - {content}...")

    print(f"    Child Session 可见任务: {len(child_tasks)} 个")
    for t in child_tasks:
        content = t.parameters.get("content", "")[:35]
        print(f"      - {content}...")

    print("\n    结论: 各 Session 的记忆默认是隔离的")


async def demo_cross_session_sharing(controller: ContextController):
    """演示跨 Session 记忆共享"""
    print("\n" + "-" * 40)
    print("[6] 跨 Session 记忆共享")
    print("-" * 40)

    # 从 parent-session 共享到 child-session
    result = await controller.share_context(
        from_session_id="parent-session",
        to_session_ids=["child-session"],
        task_limit=2,
    )

    print("    从 parent-session 共享到 child-session:")
    for sid, count in result.items():
        print(f"      → {sid}: 共享了 {count} 个任务")

    # 验证共享结果
    child = controller.get_session("child-session")
    child_tasks = child.get_l1_tasks(limit=10)
    print(f"\n    共享后 Child Session 任务数: {len(child_tasks)}")


def demo_memory_stats(controller: ContextController):
    """显示记忆统计"""
    print("\n" + "-" * 40)
    print("[7] 记忆统计")
    print("-" * 40)

    for sid in controller.session_ids:
        session = controller.get_session(sid)
        stats = session.get_stats()
        print(f"    {sid}:")
        print(f"      状态: {stats['status']}")
        print(f"      L1 任务: {len(session.get_l1_tasks(limit=100))} 个")


if __name__ == "__main__":
    asyncio.run(main())
