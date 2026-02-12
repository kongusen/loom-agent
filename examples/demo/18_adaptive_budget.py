"""
18_adaptive_budget.py - Context 动态预算与任务阶段

演示：
- TaskPhase 任务阶段推断（EARLY / MIDDLE / LATE）
- AdaptiveBudgetManager 自适应预算分配
- 各阶段预算比例变化（固定区 / 对话区 / 检索区）
- BudgetManager 基础预算计算
"""

import asyncio

from loom.context.budget import (
    DEFAULT_ALLOCATION_RATIOS,
    PHASE_ALLOCATION_TEMPLATES,
    AdaptiveBudgetManager,
    BudgetManager,
    TaskPhase,
)
from loom.memory import EstimateCounter


async def demo_task_phase():
    """演示 TaskPhase 阶段推断"""
    print("=" * 60)
    print("[1] TaskPhase — 任务阶段推断")
    print("=" * 60)

    max_iter = 30
    samples = [
        (0, "刚开始"),
        (5, "前期"),
        (9, "接近 30% 边界"),
        (10, "进入中期"),
        (15, "中期执行"),
        (20, "接近 70% 边界"),
        (21, "进入后期"),
        (28, "即将结束"),
    ]

    print(f"\n  max_iterations = {max_iter}")
    print(f"  {'迭代':>6}  {'进度':>6}  {'阶段':<8}  说明")
    print(f"  {'─' * 6}  {'─' * 6}  {'─' * 8}  {'─' * 12}")

    for iteration, desc in samples:
        phase = TaskPhase.from_progress(iteration, max_iter)
        ratio = iteration / max_iter
        print(f"  {iteration:>6}  {ratio:>5.0%}   {phase:<8}  {desc}")


async def demo_budget_basics():
    """演示 BudgetManager 基础预算计算"""
    print("\n" + "=" * 60)
    print("[2] BudgetManager — 基础预算计算")
    print("=" * 60)

    counter = EstimateCounter()
    manager = BudgetManager(
        token_counter=counter,
        model_context_window=8000,
        output_reserve_ratio=0.25,
    )

    budget = manager.create_budget("你是一个产品助手，基于知识库回答用户问题。")
    print(f"\n  模型窗口: {budget.total} tokens")
    print(f"  输出预留: {budget.reserved_output} tokens (25%)")
    print(f"  系统提示: {budget.system_prompt} tokens")
    print(f"  可用预算: {budget.available} tokens")

    # 全量分配
    allocation = manager.allocate(budget)
    print("\n  默认分配（两级分配模型）:")
    for source, tokens in sorted(allocation.allocations.items(), key=lambda x: -x[1]):
        ratio = DEFAULT_ALLOCATION_RATIOS.get(source, 0)
        print(f"    {source:<16} {tokens:>5} tokens  ({ratio:.0%})")
    print(f"    {'─' * 40}")
    print(f"    {'总计':<16} {allocation.total_allocated:>5} tokens")

    # 按需分配（只给指定源）
    sources = ["L1_recent", "L2_important", "retrieval"]
    partial = manager.allocate_for_sources(budget, sources)
    print(f"\n  按需分配（仅 {sources}）:")
    for source, tokens in sorted(partial.allocations.items(), key=lambda x: -x[1]):
        print(f"    {source:<16} {tokens:>5} tokens")


async def demo_adaptive_budget():
    """演示 AdaptiveBudgetManager 自适应预算"""
    print("\n" + "=" * 60)
    print("[3] AdaptiveBudgetManager — 自适应预算分配")
    print("=" * 60)

    counter = EstimateCounter()
    manager = AdaptiveBudgetManager(
        token_counter=counter,
        model_context_window=128000,
        output_reserve_ratio=0.25,
    )

    max_iter = 30
    phases_to_show = [
        (2, "初期：侧重 system_prompt + skills（理解任务）"),
        (15, "中期：侧重 L1/L2 工作记忆（执行任务）"),
        (25, "后期：侧重 INHERITED 历史摘要（保持一致性）"),
    ]

    sources = [
        "system_prompt",
        "tools",
        "skills",
        "L1_recent",
        "L2_important",
        "retrieval",
        "INHERITED",
    ]

    for iteration, desc in phases_to_show:
        phase = manager.update_phase(iteration, max_iter)
        budget = manager.create_budget("你是一个助手。")
        allocation = manager.allocate_for_sources(budget, sources)

        print(f"\n  迭代 {iteration}/{max_iter} → 阶段: {phase}")
        print(f"  策略: {desc}")
        print(f"  可用预算: {budget.available} tokens")

        # 按区域分组显示
        fixed = ["system_prompt", "tools", "skills"]
        dialog = ["L1_recent", "L2_important"]
        retrieval = ["retrieval", "INHERITED"]

        fixed_total = sum(allocation.get(s) for s in fixed)
        dialog_total = sum(allocation.get(s) for s in dialog)
        retrieval_total = sum(allocation.get(s) for s in retrieval)

        print(f"    固定区: {fixed_total:>6} tokens  ", end="")
        print(" | ".join(f"{s}={allocation.get(s)}" for s in fixed))
        print(f"    对话区: {dialog_total:>6} tokens  ", end="")
        print(" | ".join(f"{s}={allocation.get(s)}" for s in dialog))
        print(f"    检索区: {retrieval_total:>6} tokens  ", end="")
        print(" | ".join(f"{s}={allocation.get(s)}" for s in retrieval))


async def demo_phase_templates():
    """演示各阶段预算模板对比"""
    print("\n" + "=" * 60)
    print("[4] 阶段预算模板对比")
    print("=" * 60)

    sources = sorted({k for t in PHASE_ALLOCATION_TEMPLATES.values() for k in t})

    # 表头
    header = f"  {'源':<16}"
    for phase in [TaskPhase.EARLY, TaskPhase.MIDDLE, TaskPhase.LATE]:
        header += f" {phase:>8}"
    header += "  变化趋势"
    print(f"\n{header}")
    print(f"  {'─' * 16} {'─' * 8} {'─' * 8} {'─' * 8}  {'─' * 10}")

    for source in sources:
        row = f"  {source:<16}"
        values = []
        for phase in [TaskPhase.EARLY, TaskPhase.MIDDLE, TaskPhase.LATE]:
            val = PHASE_ALLOCATION_TEMPLATES[phase].get(source, 0)
            values.append(val)
            row += f" {val:>7.0%}"

        # 趋势
        if values[0] < values[2]:
            trend = "↑ 递增"
        elif values[0] > values[2]:
            trend = "↓ 递减"
        else:
            trend = "— 稳定"
        row += f"  {trend}"
        print(row)


async def main():
    print()
    print("Context 动态预算与任务阶段 Demo")
    print()

    await demo_task_phase()
    await demo_budget_basics()
    await demo_adaptive_budget()
    await demo_phase_templates()

    print("\n" + "=" * 60)
    print("Demo 完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
