"""
测试上下文控制事件的流式输出
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent

# 设置OpenAI凭证
os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

# 上下文控制事件监听器
class ContextEventListener:
    """监听并显示上下文控制事件"""

    async def on_context_curated(self, event: CloudEvent):
        """处理策展完成事件"""
        data = event.data
        print(f"📚 [上下文策展] 选中 {data.get('items_count')} 个记忆单元", flush=True)

    async def on_context_compressing(self, event: CloudEvent):
        """处理压缩事件"""
        data = event.data
        print(f"🗜️  [上下文压缩] 原始tokens: {data.get('original_tokens')}, 阈值: {data.get('threshold')}", flush=True)

    async def on_budget_allocated(self, event: CloudEvent):
        """处理预算分配事件"""
        data = event.data
        print(f"💰 [预算分配] 最大tokens: {data.get('max_tokens')}, 可用项: {data.get('available_items')}", flush=True)

    async def on_item_loaded(self, event: CloudEvent):
        """处理项目加载事件"""
        data = event.data
        tier = data.get('tier')
        tokens = data.get('tokens')
        percent = data.get('budget_used_percent')
        print(f"  ⚡ 加载 [{tier}] +{tokens} tokens (预算使用: {percent}%)", flush=True)

    async def on_budget_finalized(self, event: CloudEvent):
        """处理预算最终化事件"""
        data = event.data
        print(f"\n✅ [预算最终化]", flush=True)
        print(f"   选中项: {data.get('selected_items')}/{data.get('total_items')}", flush=True)
        print(f"   使用tokens: {data.get('tokens_used')}/{data.get('max_tokens')}", flush=True)
        print(f"   预算使用率: {data.get('budget_used_percent')}%", flush=True)
        print(f"   跳过项: {data.get('items_skipped')}\n", flush=True)

async def test_context_control_events():
    """测试上下文控制事件"""
    print("=" * 60)
    print("测试: 上下文控制事件 - 实时监控")
    print("=" * 60)

    print("\n🔧 创建基础设施...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建并注册上下文控制事件监听器（使用通配符订阅）
    listener = ContextEventListener()
    await bus.subscribe("agent.context.curated/*", listener.on_context_curated)
    await bus.subscribe("agent.context.compressing/*", listener.on_context_compressing)
    await bus.subscribe("agent.context.budget_allocated/*", listener.on_budget_allocated)
    await bus.subscribe("agent.context.item_loaded/*", listener.on_item_loaded)
    await bus.subscribe("agent.context.budget_finalized/*", listener.on_budget_finalized)
    print("✅ 上下文控制事件监听器已注册")

    # 创建启用流式输出的OpenAI Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=True
    )
    print(f"✅ Provider创建成功 (stream=True)")

    # 创建Agent
    agent = (LoomBuilder()
        .with_id('context-test-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Context Test Assistant',
            system_prompt='You are a helpful assistant for testing context control.'
        )
        .build())
    print(f"✅ Agent创建成功\n")

    # 测试1: 简单任务（观察上下文加载）
    print(f"{'='*60}")
    print(f"📨 测试1: 简单任务")
    print(f"{'='*60}\n")

    event1 = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "What is 2+2?"}
    )

    result1 = await agent.process(event1)
    print(f"\n🤖 响应: {result1}\n")

    # 等待一下，让事件处理完成
    await asyncio.sleep(0.5)

    # 测试2: 复杂任务（观察上下文预算使用）
    print(f"{'='*60}")
    print(f"📨 测试2: 复杂任务（多轮对话）")
    print(f"{'='*60}\n")

    event2 = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "Tell me about the history of artificial intelligence in detail."}
    )

    result2 = await agent.process(event2)
    print(f"\n🤖 响应: {result2[:200]}...\n")

    # 等待一下，让事件处理完成
    await asyncio.sleep(0.5)

    return result1, result2

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_context_control_events())
    print("\n✅ 上下文控制事件测试完成\n")
