"""
20_checkpoint.py - Checkpoint 检查点与恢复

演示：
- CheckpointData 检查点数据结构
- CheckpointManager 检查点管理（保存 / 加载 / 清理）
- MemoryStateStore 内存状态存储
- 模拟 Agent 迭代过程中的断点续跑
- 检查点自动清理（保留最近 N 个）
"""

import asyncio

from loom.runtime.checkpoint import (
    CheckpointData,
    CheckpointManager,
    CheckpointStatus,
)
from loom.runtime.state_store import MemoryStateStore


async def demo_checkpoint_basics():
    """演示 CheckpointData 数据结构"""
    print("=" * 60)
    print("[1] CheckpointData — 检查点数据结构")
    print("=" * 60)

    cp = CheckpointData(
        agent_id="agent-001",
        task_id="task-research",
        iteration=5,
        max_iterations=30,
        agent_state={
            "phase": "middle",
            "current_goal": "收集 API 文档信息",
            "tools_used": ["query", "browse_memory"],
        },
        memory_snapshot={
            "l1_count": 12,
            "l2_count": 3,
            "l1_tokens": 4500,
            "l2_tokens": 1800,
        },
        tool_history=[
            {"tool": "query", "query": "OAuth2.0 认证", "results": 3},
            {"tool": "query", "query": "API 限流策略", "results": 2},
        ],
        context_metadata={
            "budget_used_ratio": 0.45,
            "retrieval_sources": ["product_docs", "faq"],
        },
    )

    print(f"\n  Agent: {cp.agent_id}")
    print(f"  Task: {cp.task_id}")
    print(f"  迭代: {cp.iteration}/{cp.max_iterations}")
    print(f"  状态: {cp.status}")
    print(f"  Agent State: {cp.agent_state}")
    print(f"  Memory: L1={cp.memory_snapshot['l1_count']} tasks, L2={cp.memory_snapshot['l2_count']} tasks")
    print(f"  工具历史: {len(cp.tool_history)} 次调用")
    print(f"  预算使用: {cp.context_metadata['budget_used_ratio']:.0%}")

    # 序列化 / 反序列化
    data = cp.to_dict()
    restored = CheckpointData.from_dict(data)
    print(f"\n  序列化字段数: {len(data)}")
    print(f"  反序列化验证: agent_id={restored.agent_id}, iteration={restored.iteration}")
    assert restored.agent_id == cp.agent_id
    assert restored.iteration == cp.iteration
    print("  序列化/反序列化一致性: 通过")


async def demo_save_and_load():
    """演示检查点保存与加载"""
    print("\n" + "=" * 60)
    print("[2] CheckpointManager — 保存与加载")
    print("=" * 60)

    store = MemoryStateStore()
    mgr = CheckpointManager(store, max_checkpoints=5)

    agent_id = "agent-001"
    task_id = "task-analysis"

    # 模拟 Agent 执行过程，每隔几轮保存检查点
    checkpoints_saved = []
    for iteration in [3, 6, 9, 12, 15]:
        cp = CheckpointData(
            agent_id=agent_id,
            task_id=task_id,
            iteration=iteration,
            max_iterations=30,
            agent_state={"phase": "middle" if iteration < 10 else "late"},
            memory_snapshot={"l1_count": iteration * 2, "l2_count": iteration // 3},
        )
        await mgr.save(cp)
        checkpoints_saved.append(iteration)

    print(f"\n  保存了 {len(checkpoints_saved)} 个检查点: {checkpoints_saved}")

    # 列出所有检查点
    iterations = await mgr.list_checkpoints(agent_id, task_id)
    print(f"  存储中的检查点: {iterations}")

    # 加载最近的检查点
    latest = await mgr.load_latest(agent_id, task_id)
    print("\n  加载最近检查点:")
    print(f"    iteration={latest.iteration}")
    print(f"    phase={latest.agent_state['phase']}")
    print(f"    memory: L1={latest.memory_snapshot['l1_count']}, L2={latest.memory_snapshot['l2_count']}")

    # 加载指定迭代的检查点
    cp6 = await mgr.load(agent_id, task_id, 6)
    print("\n  加载迭代 6 的检查点:")
    print(f"    iteration={cp6.iteration}")
    print(f"    phase={cp6.agent_state['phase']}")


async def demo_resume_simulation():
    """模拟断点续跑场景"""
    print("\n" + "=" * 60)
    print("[3] 断点续跑模拟")
    print("=" * 60)

    store = MemoryStateStore()
    mgr = CheckpointManager(store, max_checkpoints=10)

    agent_id = "agent-002"
    task_id = "task-long-running"
    max_iter = 20

    # === 第一次运行：执行到迭代 8 后"中断" ===
    print(f"\n  [第一次运行] 开始执行，max_iterations={max_iter}")
    accumulated_results = []

    for i in range(1, 9):  # 执行到 8
        result = f"step-{i}-result"
        accumulated_results.append(result)

        # 每 3 轮保存检查点
        if i % 3 == 0:
            cp = CheckpointData(
                agent_id=agent_id,
                task_id=task_id,
                iteration=i,
                max_iterations=max_iter,
                agent_state={
                    "accumulated_results": accumulated_results.copy(),
                    "last_action": f"completed step {i}",
                },
                memory_snapshot={"l1_count": i * 3},
            )
            await mgr.save(cp)
            print(f"    迭代 {i}: 保存检查点 ✓")
        else:
            print(f"    迭代 {i}: 执行完成")

    print("  [中断] 模拟进程崩溃（迭代 8 后）")

    # === 第二次运行：从检查点恢复 ===
    print("\n  [第二次运行] 尝试恢复...")

    latest = await mgr.load_latest(agent_id, task_id)
    if latest:
        resume_iter = latest.iteration + 1
        restored_results = latest.agent_state.get("accumulated_results", [])
        print(f"    找到检查点: 迭代 {latest.iteration}")
        print(f"    恢复状态: {len(restored_results)} 个已完成结果")
        print(f"    从迭代 {resume_iter} 继续执行")

        for i in range(resume_iter, max_iter + 1):
            result = f"step-{i}-result"
            restored_results.append(result)

            if i % 3 == 0:
                cp = CheckpointData(
                    agent_id=agent_id,
                    task_id=task_id,
                    iteration=i,
                    max_iterations=max_iter,
                    agent_state={
                        "accumulated_results": restored_results.copy(),
                        "last_action": f"completed step {i}",
                    },
                    memory_snapshot={"l1_count": i * 3},
                )
                await mgr.save(cp)

            if i <= resume_iter + 2 or i >= max_iter - 1:
                print(f"    迭代 {i}: 执行完成")
            elif i == resume_iter + 3:
                print("    ... (省略中间迭代)")

        print(f"\n  任务完成，共 {len(restored_results)} 个结果")
        print("  丢失的迭代: 8 (检查点在 6，从 7 重新执行)")
    else:
        print("    无可用检查点，需要从头开始")


async def demo_cleanup():
    """演示检查点清理"""
    print("\n" + "=" * 60)
    print("[4] 检查点清理 — 自动保留最近 N 个")
    print("=" * 60)

    store = MemoryStateStore()
    mgr = CheckpointManager(store, max_checkpoints=3)

    agent_id = "agent-003"
    task_id = "task-cleanup-demo"

    # 保存 6 个检查点（max_checkpoints=3，自动清理旧的）
    for i in range(1, 7):
        cp = CheckpointData(
            agent_id=agent_id, task_id=task_id,
            iteration=i * 5, max_iterations=50,
        )
        await mgr.save(cp)
        remaining = await mgr.list_checkpoints(agent_id, task_id)
        print(f"  保存迭代 {i*5:>2} → 存储中: {remaining}")

    print("\n  max_checkpoints=3，旧检查点被自动清理")

    # 手动清理到只保留 1 个
    deleted = await mgr.cleanup(agent_id, task_id, keep_last=1)
    remaining = await mgr.list_checkpoints(agent_id, task_id)
    print(f"  手动清理 keep_last=1 → 删除 {deleted} 个，剩余: {remaining}")

    # 删除全部
    deleted = await mgr.delete_all(agent_id, task_id)
    remaining = await mgr.list_checkpoints(agent_id, task_id)
    print(f"  删除全部 → 删除 {deleted} 个，剩余: {remaining}")


async def demo_checkpoint_status():
    """演示检查点状态验证"""
    print("\n" + "=" * 60)
    print("[5] 检查点状态与验证")
    print("=" * 60)

    print("\n  CheckpointStatus 枚举:")
    for status in CheckpointStatus:
        print(f"    {status.name} = \"{status.value}\"")

    store = MemoryStateStore()
    mgr = CheckpointManager(store, auto_validate=True)

    # 保存一个正常检查点
    valid_cp = CheckpointData(
        agent_id="agent-004", task_id="task-valid",
        iteration=10, max_iterations=30,
    )
    await mgr.save(valid_cp)

    # 手动写入一个损坏的检查点
    corrupted_data = {
        "agent_id": "agent-004", "task_id": "task-valid",
        "iteration": 15, "max_iterations": 30,
        "status": CheckpointStatus.CORRUPTED.value,
        "agent_state": {}, "memory_snapshot": {},
        "tool_history": [], "context_metadata": {},
        "timestamp": 0,
    }
    await store.save("checkpoint:agent-004:task-valid:000015", corrupted_data)

    # 加载最近的 — 应该跳过损坏的，返回有效的
    loaded = await mgr.load_latest("agent-004", "task-valid")
    print("\n  存储中有 2 个检查点（迭代 10=valid, 15=corrupted）")
    print(f"  load_latest 返回: 迭代 {loaded.iteration} (跳过了损坏的)")
    assert loaded.iteration == 10, "应该跳过损坏的检查点"
    print("  验证通过: 自动跳过 CORRUPTED 状态的检查点")


async def main():
    print()
    print("Checkpoint 检查点与恢复 Demo")
    print()

    await demo_checkpoint_basics()
    await demo_save_and_load()
    await demo_resume_simulation()
    await demo_cleanup()
    await demo_checkpoint_status()

    print("\n" + "=" * 60)
    print("Demo 完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
