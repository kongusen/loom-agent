#!/usr/bin/env python3
"""Loom 0.0.3 API 演示

展示 Loom 0.0.3 的完整 API 暴露和使用方式。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import loom
from loom.builtin.llms import MockLLM
from loom.builtin.tools import Calculator
from loom.core.types import Message


async def demo_basic_loom_agent():
    """演示基础 Loom 0.0.3 Agent 使用"""
    print("🎯 演示 1: 基础 Loom 0.0.3 Agent")
    print("=" * 60)
    
    # 创建 Loom 0.0.3 Agent
    agent = loom.loom_agent(
        llm=MockLLM(responses=["The answer is 42"]),
        tools={"calculator": Calculator()},
        max_iterations=10
    )
    
    print("✅ Loom 0.0.3 Agent 创建成功")
    print(f"   - 统一协调: {agent.executor.enable_unified_coordination}")
    print(f"   - 智能协调器: {agent.get_coordinator() is not None}")
    print(f"   - 统一上下文: {agent.get_unified_context() is not None}")
    
    # 运行 Agent
    result = await agent.run("What is the meaning of life?")
    print(f"✅ 执行结果: {result}")
    
    return agent


async def demo_streaming_execution():
    """演示流式执行"""
    print("\n🎯 演示 2: 流式执行")
    print("=" * 60)
    
    agent = loom.loom_agent(
        llm=MockLLM(responses=["Hello", " from", " Loom", " 0.0.3!"]),
        max_iterations=5
    )
    
    print("🔄 开始流式执行...")
    
    async for event in agent.stream("Say hello"):
        if event.type == loom.AgentEventType.LLM_DELTA:
            print(event.content or "", end="", flush=True)
        elif event.type == loom.AgentEventType.AGENT_FINISH:
            print(f"\n✅ 流式执行完成: {event.content}")
        elif event.type == loom.AgentEventType.ERROR:
            print(f"\n❌ 执行错误: {event.error}")


async def demo_unified_executor():
    """演示直接使用统一协调 AgentExecutor"""
    print("\n🎯 演示 3: 直接使用统一协调 AgentExecutor")
    print("=" * 60)
    
    # 创建统一协调配置
    config = loom.CoordinationConfig(
        deep_recursion_threshold=3,
        high_complexity_threshold=0.7,
        context_cache_size=100,
        event_batch_size=10,
        event_batch_timeout=0.05
    )
    
    # 创建统一协调 AgentExecutor
    executor = loom.unified_executor(
        llm=MockLLM(responses=["Direct execution result"]),
        tools={"calculator": Calculator()},
        config=config,
        execution_id="demo_executor"
    )
    
    print("✅ 统一协调 AgentExecutor 创建成功")
    print(f"   - 统一协调: {executor.enable_unified_coordination}")
    print(f"   - 智能协调器: {executor.coordinator is not None}")
    print(f"   - 配置: {executor.unified_context.config}")
    
    # 使用 TT 递归执行
    turn_state = loom.TurnState.initial(max_iterations=5)
    context = loom.ExecutionContext.create(correlation_id="demo_tt")
    messages = [Message(role="user", content="Execute directly")]
    
    print("🔄 使用 TT 递归执行...")
    
    async for event in executor.tt(messages, turn_state, context):
        print(f"   Event: {event.type}")
        if event.type == loom.AgentEventType.AGENT_FINISH:
            print(f"✅ TT 执行完成: {event.content}")
            break
        elif event.type == loom.AgentEventType.ERROR:
            print(f"❌ TT 执行错误: {event.error}")
            break


async def demo_advanced_configuration():
    """演示高级配置"""
    print("\n🎯 演示 4: 高级配置")
    print("=" * 60)
    
    # 创建高级配置
    config = loom.CoordinationConfig(
        deep_recursion_threshold=5,
        high_complexity_threshold=0.8,
        context_cache_size=200,
        event_batch_size=15,
        event_batch_timeout=0.03,
        subagent_pool_size=8,
        max_execution_time=300,
        max_token_usage=50000,
        min_cache_hit_rate=0.8,
        max_subagent_count=5
    )
    
    # 创建高级 Agent
    agent = loom.loom_agent(
        llm=MockLLM(responses=["Advanced configuration result"]),
        tools={"calculator": Calculator()},
        config=config,
        execution_id="advanced_demo",
        max_iterations=20,
        system_instructions="You are an advanced AI assistant with unified coordination."
    )
    
    print("✅ 高级配置 Agent 创建成功")
    print(f"   - 深度递归阈值: {config.deep_recursion_threshold}")
    print(f"   - 复杂度阈值: {config.high_complexity_threshold}")
    print(f"   - 上下文缓存大小: {config.context_cache_size}")
    print(f"   - 事件批处理大小: {config.event_batch_size}")
    print(f"   - 事件批处理超时: {config.event_batch_timeout}")
    
    # 运行高级 Agent
    result = await agent.run("Demonstrate advanced capabilities")
    print(f"✅ 高级执行结果: {result}")


async def demo_event_processing():
    """演示事件处理"""
    print("\n🎯 演示 5: 事件处理")
    print("=" * 60)
    
    agent = loom.loom_agent(
        llm=MockLLM(responses=["Event processing demo"]),
        tools={"calculator": Calculator()},
        max_iterations=5
    )
    
    print("🔄 收集所有执行事件...")
    
    events = await agent.execute_with_events("Process events")
    
    print(f"✅ 收集到 {len(events)} 个事件:")
    for i, event in enumerate(events, 1):
        print(f"   {i}. {event.type}")
        if event.content:
            print(f"      内容: {event.content[:50]}...")
        if event.metadata:
            print(f"      元数据: {event.metadata}")


async def demo_progress_callback():
    """演示进度回调"""
    print("\n🎯 演示 6: 进度回调")
    print("=" * 60)
    
    agent = loom.loom_agent(
        llm=MockLLM(responses=["Progress callback demo"]),
        max_iterations=3
    )
    
    async def progress_callback(event):
        """进度回调函数"""
        if event.type == loom.AgentEventType.ITERATION_START:
            print(f"🔄 迭代开始: {event.metadata.get('iteration', 0)}")
        elif event.type == loom.AgentEventType.LLM_DELTA:
            print(f"📝 LLM 输出: {event.content}")
        elif event.type == loom.AgentEventType.TOOL_EXECUTION_START:
            print(f"🛠️ 工具执行: {event.tool_call.name if event.tool_call else 'Unknown'}")
        elif event.type == loom.AgentEventType.AGENT_FINISH:
            print(f"✅ 执行完成: {event.content}")
    
    print("🔄 使用进度回调执行...")
    result = await agent.run_with_progress("Use progress callback", progress_callback)
    print(f"✅ 最终结果: {result}")


async def demo_api_comparison():
    """演示 API 对比"""
    print("\n🎯 演示 7: API 对比")
    print("=" * 60)
    
    print("📊 Loom 0.0.3 API 对比:")
    print()
    
    print("1. 传统 Agent API:")
    print("   agent = loom.agent(provider='openai', model='gpt-4o')")
    print("   result = await agent.run('Hello')")
    print()
    
    print("2. Loom 0.0.3 统一协调 API:")
    print("   agent = loom.loom_agent(llm=llm, tools=tools)")
    print("   result = await agent.run('Hello')")
    print()
    
    print("3. 直接使用 AgentExecutor:")
    print("   executor = loom.unified_executor(llm=llm, tools=tools)")
    print("   async for event in executor.tt(messages, turn_state, context):")
    print("       print(event)")
    print()
    
    print("✅ Loom 0.0.3 提供:")
    print("   - 统一协调机制")
    print("   - 智能上下文组装")
    print("   - 事件流处理")
    print("   - 性能优化")
    print("   - 简化的 API")


async def main():
    """主函数"""
    print("🎯 Loom 0.0.3 API 完整演示")
    print("=" * 80)
    print("展示 Loom 0.0.3 的完整 API 暴露和使用方式")
    print("=" * 80)
    
    try:
        # 演示 1: 基础使用
        await demo_basic_loom_agent()
        
        # 演示 2: 流式执行
        await demo_streaming_execution()
        
        # 演示 3: 直接使用 AgentExecutor
        await demo_unified_executor()
        
        # 演示 4: 高级配置
        await demo_advanced_configuration()
        
        # 演示 5: 事件处理
        await demo_event_processing()
        
        # 演示 6: 进度回调
        await demo_progress_callback()
        
        # 演示 7: API 对比
        await demo_api_comparison()
        
        print("\n" + "=" * 80)
        print("🎉 Loom 0.0.3 API 演示完成！")
        print("=" * 80)
        print("📋 总结:")
        print("✅ Loom 0.0.3 核心能力已完全暴露给开发者")
        print("✅ 提供简化的 API 接口")
        print("✅ 支持统一协调机制")
        print("✅ 支持事件流处理")
        print("✅ 支持性能优化配置")
        print("✅ 向后兼容现有 API")
        print()
        print("🚀 开发者现在可以:")
        print("   - 使用 loom.loom_agent() 创建统一协调 Agent")
        print("   - 使用 loom.unified_executor() 直接控制执行")
        print("   - 配置 CoordinationConfig 优化性能")
        print("   - 处理 AgentEvent 事件流")
        print("   - 享受智能上下文组装和缓存优化")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
