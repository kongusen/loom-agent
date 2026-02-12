"""
21_fractal_delegation.py - 分形委派（Fractal Delegation）

演示：
- 使用 Agent.delegate() API 进行分形委派
- 自动创建子节点（target_node_id=None）
- 多层分形委派（Level 0 → Level 1 → Level 2）
- 记忆继承和同步
- EventBus → Memory → Context 数据流

场景：研究任务的多层分解
- Level 0 (Root): 研究 Python 异步编程最佳实践
  - Level 1 (Child 1): 研究 asyncio 核心概念（自动创建子节点）
  - Level 1 (Child 2): 研究实际应用案例（自动创建子节点）
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from loom.agent import Agent
from loom.config.llm import LLMConfig
from loom.events.event_bus import EventBus
from loom.providers.llm.openai import OpenAIProvider
from loom.runtime import Task, TaskStatus

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def demo_auto_delegation():
    """演示自动委派（自动创建子节点）"""
    print("=" * 70)
    print("自动委派演示（Agent.delegate() with target_node_id=None）")
    print("=" * 70)

    # 1. 创建 LLM Provider
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("\n[警告] 未设置 OPENAI_API_KEY")
        print("请设置环境变量后运行此 demo")
        return

    config = LLMConfig(
        provider="openai",
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
    )
    llm_provider = OpenAIProvider(config)

    # 2. 创建 EventBus
    event_bus = EventBus()

    # 3. 创建根节点 Agent
    print("\n[1] 创建根节点 Agent")
    root_agent = Agent(
        node_id="root_researcher",
        llm_provider=llm_provider,
        system_prompt="你是一个研究助手，负责将复杂任务分解为子任务。",
        event_bus=event_bus,
        max_iterations=10,
        require_done_tool=True,
        recursive_depth=0,
    )
    print("    ✓ 根节点创建完成")

    # 4. 使用 Agent.delegate() 自动创建子节点
    print("\n[2] 使用 Agent.delegate() 自动委派子任务")
    print("    " + "-" * 50)
    
    # 委派第一个子任务（target_node_id=None 会自动创建子节点）
    print("\n    [委派 1] 研究 asyncio 核心概念...")
    start_time = datetime.now()
    result1 = await root_agent.delegate(
        subtask="研究 asyncio 的核心概念（event loop, coroutines）",
        target_node_id=None,  # None 表示自动创建子节点
    )
    duration1 = (datetime.now() - start_time).total_seconds()
    print(f"    ✓ 完成（耗时: {duration1:.2f} 秒）")
    if isinstance(result1.result, dict):
        print(f"    结果: {result1.result.get('content', '')[:100]}...")

    # 委派第二个子任务
    print("\n    [委派 2] 研究实际应用案例...")
    start_time = datetime.now()
    result2 = await root_agent.delegate(
        subtask="研究 Python 异步编程的实际应用案例（Web 框架、数据库操作等）",
        target_node_id=None,  # None 表示自动创建子节点
    )
    duration2 = (datetime.now() - start_time).total_seconds()
    print(f"    ✓ 完成（耗时: {duration2:.2f} 秒）")
    if isinstance(result2.result, dict):
        print(f"    结果: {result2.result.get('content', '')[:100]}...")

    print("    " + "-" * 50)

    # 5. 检查 Memory 数据流
    print("\n[3] 检查 Memory 数据流")
    memory = root_agent.memory

    # L1: 最近任务
    l1_tasks = memory.get_l1_tasks(limit=50)
    print(f"    L1 Memory: {len(l1_tasks)} 个任务")

    # 检查是否有 thinking 事件
    thinking_tasks = [t for t in l1_tasks if t.action == "node.thinking"]
    print(f"    Thinking 事件: {len(thinking_tasks)} 个")

    # 检查是否有 tool_call 事件
    tool_call_tasks = [t for t in l1_tasks if t.action == "node.tool_call"]
    print(f"    Tool Call 事件: {len(tool_call_tasks)} 个")

    # L2: 重要任务
    l2_tasks = memory.get_l2_tasks(limit=50)
    print(f"    L2 Memory: {len(l2_tasks)} 个重要任务")

    # 6. 验证 Context 构建
    print("\n[4] 验证 Context 构建")
    context_messages = await root_agent.context_orchestrator.build_context(
        "根据之前的研究，总结3个关键要点"
    )

    print(f"    Context 消息数量: {len(context_messages)}")
    print(
        f"    包含历史消息: {len([m for m in context_messages if m.get('role') == 'assistant'])} 条"
    )

    print("\n" + "=" * 70)
    print("✅ 自动委派演示完成!")
    print("=" * 70)


async def demo_multi_level_delegation():
    """演示多层分形委派（递归委派）"""
    print("\n" + "=" * 70)
    print("多层分形委派演示（递归委派）")
    print("=" * 70)

    # 1. 创建 LLM Provider
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("\n[警告] 未设置 OPENAI_API_KEY")
        print("请设置环境变量后运行此 demo")
        return

    config = LLMConfig(
        provider="openai",
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
    )
    llm_provider = OpenAIProvider(config)

    # 2. 创建 EventBus
    event_bus = EventBus()

    # 3. 创建根节点
    print("\n[1] 创建根节点 Agent")
    root_agent = Agent(
        node_id="root_planner",
        llm_provider=llm_provider,
        system_prompt="你是一个任务规划助手，负责将复杂任务分解为多个子任务。",
        event_bus=event_bus,
        max_iterations=10,
        require_done_tool=True,
        recursive_depth=0,
    )
    print("    ✓ 根节点创建完成")

    # 4. 第一层委派：研究 Web 应用构建
    print("\n[2] 第一层委派：研究 Web 应用构建")
    print("    " + "-" * 50)
    
    print("\n    [Level 0 → Level 1] 委派 Web 应用研究任务...")
    start_time = datetime.now()
    level1_result = await root_agent.delegate(
        subtask="""研究"如何构建一个高性能的 Python Web 应用"。

这个任务需要分解为多个子任务：
1. 研究 Web 框架选择（FastAPI vs Flask vs Django）
2. 研究性能优化技术（异步、缓存、数据库优化）
3. 研究部署方案（Docker、K8s、云服务）""",
        target_node_id=None,  # 自动创建子节点
    )
    duration = (datetime.now() - start_time).total_seconds()
    print(f"    ✓ 完成（耗时: {duration:.2f} 秒）")
    
    if isinstance(level1_result.result, dict):
        result_content = level1_result.result.get("content", "")
        print(f"    结果长度: {len(result_content)} 字符")
        print(f"    结果预览:\n{result_content[:300]}...")

    print("    " + "-" * 50)

    # 5. 检查委派情况
    print("\n[3] 检查委派情况")
    memory = root_agent.memory
    l1_tasks = memory.get_l1_tasks(limit=100)

    # 查找委派相关的事件
    delegate_events = [
        t
        for t in l1_tasks
        if t.action == "delegation.started" or t.action == "delegation.completed"
    ]

    print(f"    委派事件: {len(delegate_events)} 个")

    print("\n" + "=" * 70)
    print("✅ 多层分形委派演示完成!")
    print("=" * 70)


async def main():
    """主入口"""
    # 演示1: 自动委派（使用 Agent.delegate() API）
    await demo_auto_delegation()

    # 演示2: 多层分形委派（递归委派）
    await demo_multi_level_delegation()


if __name__ == "__main__":
    asyncio.run(main())
