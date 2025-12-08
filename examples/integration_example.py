"""
集成示例：展示如何使用 loom-agent 2.0 的新架构

这个文件展示了完整的集成流程，包括：
- ExecutionFrame
- EventJournal
- ContextDebugger
- LifecycleHooks
- 可视化

你可以参考这个示例，逐步将功能集成到现有的 AgentExecutor 中。
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any

# 新架构导入
from loom.core.execution_frame import ExecutionFrame, ExecutionPhase
from loom.core.event_journal import EventJournal, EventJournalContext
from loom.core.context_debugger import ContextDebugger
from loom.core.lifecycle_hooks import LifecycleHook, HITLHook, LoggingHook, MetricsHook
from loom.core.state_reconstructor import StateReconstructor
from loom.visualization import visualize_execution_from_events

# 旧架构（兼容）
from loom.core.agent_executor import AgentExecutor
from loom.core.execution_context import ExecutionContext
from loom.core.events import AgentEventType


# ========================================
# 示例 1: 基本使用 - 带持久化
# ========================================

async def example_basic_with_persistence():
    """展示基本用法：启用 EventJournal 和 ContextDebugger"""

    from loom.builtin.llms import MockLLM
    from loom import tool

    # 创建工具
    @tool(description="搜索文档")
    async def search(query: str) -> str:
        return f"找到关于 '{query}' 的 5 个文档"

    # 🆕 创建 EventJournal
    journal = EventJournal(storage_path=Path("./logs"))
    await journal.start()

    # 🆕 创建 ContextDebugger
    debugger = ContextDebugger(enable_auto_export=True)

    # 创建 Agent（使用新参数）
    agent = AgentExecutor(
        llm=MockLLM(),
        tools={"search": search()},
        max_iterations=10,
        # 🆕 新参数
        event_journal=journal,
        context_debugger=debugger,
        thread_id="user-123"
    )

    # 执行
    from loom.core.turn_state import TurnState
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [{"role": "user", "content": "搜索 Python 文档"}]

    print("🚀 执行 Agent...")
    async for event in agent.tt(messages, turn_state, context):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✅ 完成: {event.content}")

    await journal.stop()

    # 🆕 查看上下文调试信息
    print("\n" + "="*60)
    print(debugger.generate_summary())

    return journal, debugger


# ========================================
# 示例 2: 崩溃恢复
# ========================================

async def example_crash_recovery():
    """展示崩溃恢复：从 EventJournal 重建状态"""

    # 假设之前执行崩溃了，现在重启
    journal = EventJournal(storage_path=Path("./logs"))

    # 🆕 重放事件
    print("🔄 重放事件以恢复状态...")
    events = await journal.replay(thread_id="user-123")

    print(f"找到 {len(events)} 个事件")

    # 🆕 重建状态
    reconstructor = StateReconstructor()
    frame, metadata = await reconstructor.reconstruct(events)

    print(f"✅ 状态重建完成:")
    print(f"  - 迭代次数: {frame.depth}")
    print(f"  - 处理事件: {metadata.total_events}")
    print(f"  - 最终阶段: {metadata.final_phase}")
    print(f"  - 警告: {metadata.warnings}")

    print("\n" + frame.summary())

    # 现在可以从 frame 继续执行
    # agent.tt(..., frame=frame)  # 从断点继续

    return frame


# ========================================
# 示例 3: HITL (Human-in-the-Loop)
# ========================================

async def example_hitl():
    """展示 HITL：用户确认危险操作"""

    from loom.builtin.llms import MockLLM
    from loom import tool

    # 定义危险工具
    @tool(description="删除文件")
    async def delete_file(path: str) -> str:
        return f"删除文件: {path}"

    @tool(description="发送邮件")
    async def send_email(to: str, subject: str) -> str:
        return f"发送邮件到 {to}"

    # 🆕 创建 HITL 钩子
    def ask_user(message: str) -> bool:
        print(f"\n⚠️  {message}")
        response = input("是否允许? (y/n): ")
        return response.lower() == "y"

    hitl_hook = HITLHook(
        dangerous_tools=["delete_file", "send_email"],
        ask_user_callback=ask_user
    )

    # 创建 Agent（带 HITL）
    agent = AgentExecutor(
        llm=MockLLM(),
        tools={"delete": delete_file(), "send": send_email()},
        # 🆕 添加钩子
        hooks=[hitl_hook, LoggingHook(verbose=True)]
    )

    # 执行（会在危险操作前暂停）
    # ...（实际执行代码）

    print("✅ HITL 演示完成")


# ========================================
# 示例 4: 自定义钩子
# ========================================

class CustomAnalyticsHook:
    """自定义钩子：收集分析数据"""

    def __init__(self):
        self.token_usage = []
        self.tool_usage = {}

    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        # 记录 token 使用
        self.token_usage.append({
            "iteration": frame.depth,
            "tokens": context_metadata.get("total_tokens", 0)
        })
        return None

    async def after_tool_execution(self, frame, tool_result):
        # 统计工具使用
        tool_name = tool_result["tool_name"]
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None

    def get_report(self):
        return {
            "total_tokens": sum(t["tokens"] for t in self.token_usage),
            "tool_usage": self.tool_usage
        }


async def example_custom_hooks():
    """展示自定义钩子"""

    # 创建自定义钩子
    analytics = CustomAnalyticsHook()
    logging = LoggingHook(verbose=False)
    metrics = MetricsHook()

    # 使用多个钩子
    agent = AgentExecutor(
        llm=...,
        tools=...,
        hooks=[analytics, logging, metrics]
    )

    # 执行后查看统计
    # ... 执行 ...

    print("📊 分析报告:")
    print(analytics.get_report())
    print(metrics.get_metrics())


# ========================================
# 示例 5: 完整工作流
# ========================================

async def example_complete_workflow():
    """完整工作流：集成所有功能"""

    from loom.builtin.llms import MockLLM
    from loom import tool

    @tool(description="搜索")
    async def search(query: str) -> str:
        return f"搜索结果: {query}"

    # 🆕 设置所有组件
    journal = EventJournal(storage_path=Path("./logs"))
    await journal.start()

    debugger = ContextDebugger(enable_auto_export=True)

    hitl_hook = HITLHook(
        dangerous_tools=["delete_file"],
        ask_user_callback=lambda msg: True  # 自动批准（演示用）
    )

    analytics = CustomAnalyticsHook()
    logging_hook = LoggingHook()

    # 创建 Agent
    agent = AgentExecutor(
        llm=MockLLM(),
        tools={"search": search()},
        max_iterations=10,
        # 🆕 所有新功能
        event_journal=journal,
        context_debugger=debugger,
        hooks=[hitl_hook, analytics, logging_hook],
        thread_id="complete-demo"
    )

    # 执行
    from loom.core.turn_state import TurnState
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [{"role": "user", "content": "搜索 Python 文档"}]

    print("🚀 完整工作流演示...")
    async for event in agent.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ {event.content}")

    await journal.stop()

    # 🆕 生成报告
    print("\n" + "="*60)
    print("📊 执行报告")
    print("="*60)

    print("\n1. 上下文管理:")
    print(debugger.generate_summary())

    print("\n2. 性能分析:")
    print(analytics.get_report())

    print("\n3. 可视化:")
    events = await journal.replay(thread_id="complete-demo")
    visualize_execution_from_events(events, mode="timeline")

    return agent, journal, debugger


# ========================================
# 示例 6: Time Travel 调试
# ========================================

async def example_time_travel():
    """Time Travel 调试：回溯到特定迭代"""

    journal = EventJournal(storage_path=Path("./logs"))
    events = await journal.replay(thread_id="user-123")

    # 🆕 回到第 3 次迭代
    reconstructor = StateReconstructor()
    frame_at_3, _ = await reconstructor.reconstruct_at_iteration(events, target_iteration=3)

    print("🕐 时光倒流到第 3 次迭代:")
    print(frame_at_3.summary())

    # 查看那时的上下文
    debugger = ContextDebugger()
    # ... 从事件重建 debugger 状态 ...
    print(debugger.explain_iteration(3))


# ========================================
# 示例 7: 策略升级
# ========================================

async def example_strategy_upgrade():
    """策略升级：用新压缩算法重放旧事件"""

    from loom.core.compression_manager import CompressionManager

    journal = EventJournal(storage_path=Path("./logs"))
    events = await journal.replay(thread_id="user-123")

    # 创建新的压缩策略
    new_compression = CompressionManager(...)  # 新版本算法

    # 🆕 用新策略重放
    reconstructor = StateReconstructor()
    frame, metadata = await reconstructor.reconstruct_with_new_strategy(
        events,
        compression_strategy=new_compression
    )

    print("✨ 使用新策略重建状态:")
    print(f"  - 事件数: {metadata.total_events}")
    print(f"  - 重建时间: {metadata.reconstruction_time_ms:.2f}ms")
    print(f"  - 警告: {metadata.warnings}")


# ========================================
# 主函数
# ========================================

async def main():
    """运行所有示例"""

    print("="*60)
    print("loom-agent 2.0 集成示例")
    print("="*60)

    # 示例 1: 基本用法
    print("\n\n📝 示例 1: 基本用法（带持久化）")
    print("-" * 60)
    journal, debugger = await example_basic_with_persistence()

    # 示例 2: 崩溃恢复
    print("\n\n📝 示例 2: 崩溃恢复")
    print("-" * 60)
    frame = await example_crash_recovery()

    # 示例 3: HITL
    print("\n\n📝 示例 3: HITL (Human-in-the-Loop)")
    print("-" * 60)
    await example_hitl()

    # 示例 6: Time Travel
    print("\n\n📝 示例 6: Time Travel 调试")
    print("-" * 60)
    await example_time_travel()

    print("\n\n✅ 所有示例完成!")


if __name__ == "__main__":
    asyncio.run(main())
